# Re-Audit 3 — API Surface & Backward Compatibility

**Date:** 2026-04-27
**Scope:** `workspace/tools/` Python modules (memory-hook-core system)
**Constraint:** Read-only audit. No code modified.
**Reference:** `audit/INDEPENDENT_06_api_surface.md` (original audit)

---

## 1. API Stability

**Original verdict: FAIL** (~25 internal functions without `_` prefix)
**Re-audit verdict: PASS**

### 1.1 What changed

The original audit listed ~25 public functions that were internal implementation details. Nearly all of them have been prefixed with `_`:

| Originally public | Now | Status |
|---|---|---|
| `resolve_route_target_via_policy` | `_resolve_route_target_via_policy` | Fixed |
| `write_targets_via_policy` | `_write_targets_via_policy` | Fixed |
| `get_policy_pack_via_registry` | `_get_policy_pack_via_registry` | Fixed |
| `resolve_policy_conflict_via_registry` | `_resolve_policy_conflict_via_registry` | Fixed (also dead code) |
| `write_artifacts_via_sink` | `_write_artifacts_via_sink` | Fixed |
| `append_error_log_via_sink` | `_append_error_log_via_sink` | Fixed |
| `execute_delegate_via_facade` | `_execute_delegate_via_facade` | Fixed |
| `parse_args` | `_parse_args` | Fixed |
| `require_env` | `_require_env` | Fixed |
| `section_bullets`, `section_body` | `_section_bullets`, `_section_body` | Fixed |
| `markdown_code_tokens`, `json_string_values`, `json_object_keys` | `_markdown_code_tokens`, `_json_string_values`, `_json_object_keys` | Fixed |
| `path_is_under`, `classify_truth_ref`, `authority_ref_allowed`, `lower_evidence_ref` | `_path_is_under`, `_classify_truth_ref`, `_authority_ref_allowed`, `_lower_evidence_ref` | Fixed |
| `truth_basis_sections_for`, `truth_basis_errors_for` | `_truth_basis_sections_for`, `_truth_basis_errors_for` | Fixed |
| `existing_paths` | `_existing_paths` | Fixed |
| `normalize_repo_scope_entry`, `registration_payload_paths` | `_normalize_repo_scope_entry`, `_registration_payload_paths` | Fixed |
| `git_name_only`, `path_matches_scope` | `_git_name_only`, `_path_matches_scope` | Fixed |
| `discover_cwd`, `payload_cwd`, `environment_cwd`, `path_within_repo` | `_discover_cwd`, `_payload_cwd`, `_environment_cwd`, `_path_within_repo` | Fixed |
| `should_noop_for_external_context` | `_should_noop_for_external_context` | Fixed |
| `delegate_codex`, `delegate_claude` | `_delegate_codex`, `_delegate_claude` | Fixed |

### 1.2 Remaining public symbols not in `__all__`

The following functions remain public (no `_` prefix) but are **not** in `workspace.tools.__all__`. They fall into two categories:

**Callback interface functions** (referenced by tests, impls, and interfaces — de facto public API):
- `determine_project_scope`, `governance_frozen_tuple_blocker_errors`, `event_contract_blocker_errors`
- `project_map_refs`, `validate_project_map_files`, `validate_unique_legal_system_contract`
- `decision_refs_for_scope`, `lesson_refs_for_scope`, `docs_refs_for_scope`, `truth_basis_for_scope`
- `write_targets`

These are used by `GatewayBusinessPolicyImpl` and referenced in `memory_hook_interfaces.py` as callback targets. Their public visibility is justified by their role in the interface contract.

**Clearly internal** (only referenced within gateway itself):
- `now_iso` — helper, only called inside gateway
- `read_text_if_exists` — I/O helper, referenced only internally
- `resolve_route_target` — thin wrapper, only called inside gateway
- `append_error_log`, `write_artifacts` — gateway-level operations, only called internally
- `main` — CLI entry point

These 6 could be prefixed with `_` for full cleanliness, but they represent a small residual surface compared to the original ~25.

### 1.3 `__all__` consistency

The package-level `__all__` in `workspace/tools/__init__.py` declares 4 symbols. The module-level `__all__` in `memory_hook_gateway.py` declares the same 2 entry points plus `ArtifactWriter` and `DelegateRouter`. This inconsistency remains but is low-risk: the package-level `__all__` is the canonical consumer contract, and `ArtifactWriter`/`DelegateRouter` are implementation classes that tests may import directly from the submodule.

**Verdict: PASS** — The vast majority of internal functions are now properly privatized. The residual public symbols are either part of the callback interface contract or are trivially internal.

---

## 2. Breaking Change Risk

**Original verdict: FAIL**
**Re-audit verdict: FAIL (improved)**

### 2.1 Still failing

| Risk | Detail | Severity | Status |
|---|---|---|---|
| **Global injection at import time** | `globals().update(_fn(REPO_ROOT, WORKSPACE_ROOT))` still injects 45+ constants from the adapter into the module namespace. Any adapter output key change silently breaks downstream. | High | Unchanged |
| **Adapter default is `workbot`** | `MEMORY_HOOK_ADAPTER` defaults to `"workbot"`. The workbot adapter hardcodes paths to this repo's filesystem structure. A new consumer importing the module gets workbot bindings unless they set the env var. | High | Unchanged |
| **v1 drops `system_context`** | `build_context_package_simple()` still drops `system_context` entirely. Documented as intentional, but consumers needing registration gate status or policy pack details lose that data. | High | Unchanged |
| **`WriteTargetPolicyImpl` date baked at `__init__`** | `_targets["fact"]` embeds `datetime.now().date()` at construction time. Reusing a singleton across midnight gives stale paths. | Medium | Unchanged |

### 2.2 What improved

| Risk | Detail | Status |
|---|---|---|
| **`RouteTargetPolicyImpl` date singleton** | `resolve()` now computes `datetime.now().date()` at call time, not at `__init__`. Reusing a singleton across days now works correctly for route targets. | Fixed |
| **`CoreConfig` validation** | `__post_init__` now validates 14 fields (was 4): `host`, `event`, `workspace_root`, `repo_root`, `payload`, `cwd`, `project_scope`, `required_canonical`, `project_map_refs`, `now_iso_fn`, `write_targets_fn`, `extract_excerpt_fn`, `surface_id`, `workspace_id`. Invalid callbacks are caught at construction time, not deep in `build_context_package_core`. | Improved |
| **Dead code removed from public surface** | `resolve_policy_conflict_via_registry` (was dead code) is now `_resolve_policy_conflict_via_registry`. Still dead, but no longer pollutes the public API. | Fixed |

### 2.3 Safe areas (unchanged)

- v2 output schema keys remain stable.
- `CoreConfig.from_gateway_kwargs()` remains a complete 37-kwarg to dataclass bridge.
- Interface ABCs remain contract-bound and stable.

**Verdict: FAIL (improved)** — The global injection pattern and workbot-default adapter remain the highest-risk items. The `RouteTargetPolicyImpl` date fix and expanded `CoreConfig` validation are meaningful improvements, but they do not eliminate the core risk that importing the module silently changes behavior based on adapter output.

---

## 3. Parameter Evolution: 37 flat params to CoreConfig

**Original verdict: PASS**
**Re-audit verdict: PASS (no regression)**

No changes to the `CoreConfig` dataclass, `_resolve_callbacks()`, or `build_context_package_from_config()` since the original audit. The mapping remains 1:1 and complete. `CoreConfig.to_gateway_kwargs()` still includes `policy_registry` and `path_utils` in the flattened output (minor asymmetry, non-breaking since the legacy builder ignores extra kwargs).

---

## 4. Schema Versioning: v1 to v2

**Original verdict: PASS (with caveats)**
**Re-audit verdict: PASS (with caveats, no change)**

`convert_to_v1()` in `memory_hook_schema.py` is unchanged. The `system_context` drop remains intentional and documented. `is_v1()` and `is_v2()` remain simple string checks on `schema_version`. No regression detected.

---

## 5. Consumer Onboarding

**Original verdict: FAIL**
**Re-audit verdict: FAIL (improved)**

### 5.1 What improved

| Barrier | Original state | Current state |
|---|---|---|
| **No installation package** | No `pyproject.toml` or packaging metadata. | `pyproject.toml` exists with `name = "memory-core"`, `version = "0.2.0"`, `requires-python = ">=3.10"`, entry points for `memory-validate` and `memory-rollback`. | Fixed |
| **No documentation** | Zero docs beyond source code. | `README.md` exists with architecture overview, directory structure, running model, consumer interface, M1-M3 changelog, and test instructions. | Fixed |
| **No docstrings on public API** | Entry points lacked docstrings. | `build_context_package_simple()` now has a full docstring with Args/Returns. `CoreConfig` has a class-level docstring. | Fixed |
| **194 tests** | Fewer tests. | 194 tests passing, covering core, gateway, interfaces, impls, adapters, schema, config, rollback, and API completion. | Improved |

### 5.2 What remains

| Barrier | Detail |
|---|---|
| **pip install blocked by system Python** | Homebrew Python 3.14 enforces PEP 668 externally managed environment. `pip install -e .` fails without `--break-system-packages` or a venv. Not a packaging defect, but a deployment friction. |
| **No neutral runtime profile** | `neutral_policy.py` exists (a neutral `GatewayBusinessPolicy`), but there is no `neutral_runtime_profile.py`. The adapter registry only includes `"workbot"`. A new consumer still needs to write a runtime profile adapter. |
| **Adapter default is `workbot`** | `MEMORY_HOOK_ADAPTER` defaults to `"workbot"`. Without setting this env var, consumers get workbot-specific paths. |
| **`cmux` binary dependency** | Host delegates still require `cmux` in PATH for non-noop execution. |
| **Filesystem assumptions** | The system still expects `workspace/memory/kb/`, `workspace/project-map/`, `workspace/projects/`, etc. No configuration layer to remap these paths. |
| **No type stubs** | No `.pyi` files or `py.typed` marker for consumers using type checkers. |

### 5.3 Minimum integration path (current)

```python
import os
os.environ["MEMORY_HOOK_ADAPTER"] = "workbot"  # or your own adapter

from workspace.tools import build_context_package_simple

package = build_context_package_simple("codex", "session-start", {"cwd": "/path/to/project"})
```

This works. The `pyproject.toml` + README + docstrings make the integration path significantly clearer than at the time of the original audit.

**Verdict: FAIL (improved)** — The packaging, documentation, and test coverage barriers have been removed. The remaining barriers (adapter coupling, filesystem assumptions, PEP 668 install friction, no neutral runtime profile) are architectural and would require non-trivial changes to resolve.

---

## Summary Verdicts

| Category | Original | Re-audit | Delta |
|---|---|---|---|
| **API Stability** | FAIL | **PASS** | Privatized ~19 internal functions |
| **Breaking Change Risk** | FAIL | **FAIL** | RouteTargetPolicy date fix + CoreConfig validation; global injection + workbot default remain |
| **Parameter Evolution** | PASS | **PASS** | No change, still correct |
| **Schema Versioning** | PASS | **PASS** | No change, still correct |
| **Consumer Onboarding** | FAIL | **FAIL** | pyproject.toml + README + docstrings added; adapter coupling + install friction remain |

### Overall: FAIL to FAIL (2 of 5 failing, down from 3)

The original audit's 3 failing categories have improved to 2. API Stability has crossed from FAIL to PASS through systematic privatization of internal functions. Breaking Change Risk and Consumer Onboarding remain FAIL but with meaningful improvements: `RouteTargetPolicyImpl` date singleton fixed, `CoreConfig` validation expanded, `pyproject.toml` created, README written, and docstrings added.

The remaining FAIL categories are tied to the global injection pattern and adapter coupling, which are architectural choices rather than surface-level defects. Resolving them would require either (a) a lazy-loading architecture that defers adapter injection until first use, or (b) a neutral default adapter with a clean runtime profile — both non-trivial refactors.
