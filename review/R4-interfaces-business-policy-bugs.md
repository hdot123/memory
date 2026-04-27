# R4 Bug Review — interfaces.py + business_policy_checks.py

Scope:
- `/Users/busiji/memory/workspace/tools/memory_hook_interfaces.py`
- `/Users/busiji/memory/workspace/tools/business_policy_checks.py`

## Findings

### 1. `TruthBasisResolver` ignores scope override config when resolving `project_ref`

- Severity: Medium
- File: `/Users/busiji/memory/workspace/tools/business_policy_checks.py`
- Lines: 413-414, 541-543

`TruthBasisResolver.truth_basis_for_scope()` calls its local `get_project_canonical()`, but that method only returns `dict(self._config.project_canonical)`. In the original `GatewayBusinessPolicyImpl`, `truth_basis_for_scope()` calls `self.get_project_canonical()`, and that method merges `MEMORY_HOOK_SCOPE_CONFIG_PATH` / `scope_config_path` overrides before selecting the project canonical file.

After the split, `ScopeResolver.get_project_canonical()` still applies overrides, but `TruthBasisResolver` has no access to those overrides and silently falls back to the static config map. In any runtime using the split checker classes, `get_project_canonical()` and `truth_basis_for_scope()` can disagree for the same scope: the former returns an overridden canonical path, while the latter validates and reports the old path in `project_ref`, `refs`, and truth-basis errors.

Original behavior reference:
- `/Users/busiji/memory/workspace/tools/memory_hook_impls.py`: lines 813-818 merge `_scope_overrides` into `project_canonical`.
- `/Users/busiji/memory/workspace/tools/memory_hook_impls.py`: lines 1056-1058 use that merged map inside `truth_basis_for_scope()`.

Split behavior:
- `/Users/busiji/memory/workspace/tools/business_policy_checks.py`: lines 413-414 return only the static config map.
- `/Users/busiji/memory/workspace/tools/business_policy_checks.py`: lines 541-543 use that unmerged map.

### 2. `business_policy_checks.py` imports the config dataclass from the implementation module it was extracted from

- Severity: Medium
- File: `/Users/busiji/memory/workspace/tools/business_policy_checks.py`
- Lines: 16-18, 42-44

The extracted module imports `GatewayBusinessPolicyConfig` from `memory_hook_impls.py`. That creates a reverse dependency from the new split-out module back into the original implementation module. If `memory_hook_impls.py` is updated to import and wire these checker classes during module initialization, the import order will be circular: `memory_hook_impls` imports `business_policy_checks`, and `business_policy_checks` immediately tries to import `GatewayBusinessPolicyConfig` from the partially initialized `memory_hook_impls` module before the dataclass is defined.

This prevents the split from being safely wired back into `GatewayBusinessPolicyImpl` at normal top-level import time. The config contract needs to live in an import-neutral module, or the extracted checker module must avoid importing the implementation module at runtime.

## Non-Findings

- `TruthBasis.global_refs` matches the actual dictionaries returned by both the current implementation and the extracted resolver.
- The reviewed `Protocol` method signatures match the corresponding `PolicyRegistryImpl` methods.
- The reviewed `GatewayBusinessPolicy` ABC abstract method set matches `GatewayBusinessPolicyImpl`; no missing or extra abstract methods were found in this pass.
