# Independent Audit 6 — API Surface & Backward Compatibility

**Date:** 2026-04-27
**Scope:** `workspace/tools/` Python modules (memory-hook-core system)
**Constraint:** Read-only audit. No code modified.

---

## 1. API Stability

**Verdict: FAIL**

### 1.1 Declared public API (`workspace.tools.__all__`)

The package `workspace.tools.__init__.py` declares exactly four public symbols via `__all__`:

| Symbol | Source module | Role |
|---|---|---|
| `build_context_package` | `memory_hook_gateway` | Primary 3-param entry point (v2 output) |
| `build_context_package_simple` | `memory_hook_gateway` | Simplified entry point (v1 output) |
| `CoreConfig` | `memory_hook_config` | Structured config dataclass |
| `build_context_package_from_config` | `memory_hook_core` | Core assembly from `CoreConfig` |

These four are the intended consumer-facing API. They are stable and well-scoped.

### 1.2 `memory_hook_gateway.__all__`

The gateway module declares a separate `__all__`:

```python
__all__ = ['build_context_package', 'build_context_package_simple', 'ArtifactWriter', 'DelegateRouter']
```

`ArtifactWriter` and `DelegateRouter` are exported at the gateway level but **not** at the package level (`workspace.tools`). This creates ambiguity — a consumer importing `from workspace.tools.memory_hook_gateway import ArtifactWriter` gets access, but `from workspace.tools import ArtifactWriter` fails. This is an inconsistency but not a breaking issue if the package-level `__all__` is treated as the canonical contract.

### 1.3 Functions and classes that should be private

The following are currently public (no `_` prefix) but are internal implementation details that no test or external consumer references:

| Name | Module | Reason to privatize |
|---|---|---|
| `registration_phase_from_policy_pack` | `memory_hook_core` | Pure internal helper, only called by `evaluate_registration_commit_gate` |
| `evaluate_registration_commit_gate` | `memory_hook_core` | Called only inside `build_context_package_core` |
| `_resolve_callbacks` | `memory_hook_core` | Already private (correct) |
| `resolve_route_target_via_policy` | `memory_hook_gateway` | IF-5 facade, only used internally |
| `write_targets_via_policy` | `memory_hook_gateway` | IF-5 facade, only used internally |
| `get_policy_pack_via_registry` | `memory_hook_gateway` | IF-5 facade, only used internally |
| `resolve_policy_conflict_via_registry` | `memory_hook_gateway` | IF-5 facade, never called by any test or consumer |
| `write_artifacts_via_sink` | `memory_hook_gateway` | IF-5 facade, only used internally |
| `append_error_log_via_sink` | `memory_hook_gateway` | IF-5 facade, only used internally |
| `execute_delegate_via_facade` | `memory_hook_gateway` | IF-5 facade, only used internally |
| `_build_gateway_business_policy` | `memory_hook_gateway` | Already private (correct) |
| `_get_gateway_business_policy` | `memory_hook_gateway` | Already private (correct) |
| `_load_external_core_builder` | `memory_hook_gateway` | Already private (correct) |
| `_resolve_core_builder` | `memory_hook_gateway` | Already private (correct) |
| `_apply_artifact_compaction` | `memory_hook_gateway` | Already private (correct) |
| `_delegate_noop_response` | `memory_hook_gateway` | Already private (correct) |
| `parse_args` | `memory_hook_gateway` | CLI-only, used only in `main()` |
| `require_env` | `memory_hook_gateway` | CLI-only helper |
| `section_bullets`, `section_body` | `memory_hook_gateway` | Text-parsing helpers used by `GatewayBusinessPolicyImpl` |
| `markdown_code_tokens`, `json_string_values`, `json_object_keys` | `memory_hook_gateway` | Text-parsing helpers used by `GatewayBusinessPolicyImpl` |
| `path_is_under`, `classify_truth_ref`, `authority_ref_allowed`, `lower_evidence_ref` | `memory_hook_gateway` | Classification helpers |
| `truth_basis_sections_for`, `truth_basis_errors_for` | `memory_hook_gateway` | Truth-basis parsing, used by `GatewayBusinessPolicyImpl` |
| `existing_paths` | `memory_hook_gateway` | Tiny helper |
| `normalize_repo_scope_entry`, `registration_payload_paths` | `memory_hook_gateway` | Git-registration helpers |
| `git_name_only`, `path_matches_scope` | `memory_hook_gateway` | Git subprocess helpers |
| `read_text_if_exists` | `memory_hook_gateway` | I/O helper, passed as callback into config |
| `determine_project_scope` | `memory_hook_gateway` | Used in `build_context_package`, not directly by tests |
| `discover_cwd`, `payload_cwd`, `environment_cwd`, `path_within_repo` | `memory_hook_gateway` | CWD resolution helpers |
| `should_noop_for_external_context` | `memory_hook_gateway` | No-op gate logic |
| `delegate_codex`, `delegate_claude` | `memory_hook_gateway` | Delegate wrappers used only in `main()` |
| `main` | `memory_hook_gateway` | CLI entry point |

Of these, `resolve_policy_conflict_via_registry` is never called anywhere in the codebase — dead code.

The interface classes in `memory_hook_interfaces.py` (`HostDelegate`, `PolicyRegistry`, `RouteTargetPolicy`, `WriteTargetPolicy`, `GatewayBusinessPolicy`, `ArtifactSink`, `ErrorSink`, `PathUtils`) are correctly public — they form the M2 abstraction layer and are consumed by implementations and tests.

The implementation classes in `memory_hook_impls.py` (`CodexDelegate`, `ClaudeDelegate`, `PolicyRegistryImpl`, `RouteTargetPolicyImpl`, `WriteTargetPolicyImpl`, `GatewayBusinessPolicyConfig`, `GatewayBusinessPolicyImpl`, `ArtifactSinkImpl`, `ErrorSinkImpl`, `ArtifactWriter`, `DelegateRouter`, `PathUtilsImpl`) are **not** in any `__all__` but are importable. Tests import several of them directly (`GatewayBusinessPolicyConfig`, `GatewayBusinessPolicyImpl`, `PathUtilsImpl`, `PolicyRegistryImpl`), so they are de facto public.

### 1.4 Environment variable contract

The module reads several env vars that form part of the implicit API:

| Env var | Purpose |
|---|---|
| `MEMORY_HOOK_ADAPTER` | Adapter selection (default: `workbot`) |
| `MEMORY_HOOK_EXTERNAL_CORE_MODULE` | External core builder module |
| `MEMORY_HOOK_EXTERNAL_CORE_FUNC` | External core builder function |
| `MEMORY_HOOK_CORE_PROVIDER` | Provider selection (`legacy` / `external-core`) |
| `MEMORY_HOOK_SHADOW_RUN` | Enable shadow-mode dual-provider comparison |
| `MEMORY_HOOK_POLICY_PACK_PATH` | Policy pack file path |
| `MEMORY_HOOK_SCOPE_CONFIG_PATH` | Scope config path |
| `MEMORY_HOOK_FORCE` / `WORKBOT_FORCE_HOOK` | Force hook execution outside repo |
| `CMUX_SURFACE_ID` | Surface identifier |
| `CMUX_WORKSPACE_ID` | Workspace identifier |
| `CMUX_HOOK_STATE_FILE` | Claude hook state file path |

These are undocumented but functionally part of the public contract.

---

## 2. Breaking Change Risk

**Verdict: FAIL**

### 2.1 High-risk areas

| Risk | Detail | Severity |
|---|---|---|
| **Gateway module globals** | Constants like `REPO_ROOT`, `WORKSPACE_ROOT`, `REQUIRED_CANONICAL`, `PROJECT_CANONICAL`, etc. are populated by adapter injection (`globals().update(_fn(...))`) at import time. Any change to adapter output key names silently breaks downstream code. | High |
| **`_resolve_core_builder` fallback logic** | The provider resolution has implicit fallback: `external-core` → `legacy` with error logging. A change to error handling in this path could alter whether `build_context_package` returns `status="ok"` or `"degraded"`. | High |
| **`_apply_artifact_compaction`** | Reads `ARTIFACT_COMPACTION` from `globals()` — an undocumented dict. If an adapter stops providing it, compaction silently becomes a no-op (safe). If the dict shape changes, behavior is undefined. | Medium |
| **`build_context_package_simple` → v1 conversion** | Drops `system_context` and `missing_paths` entirely. Consumers relying on any field within `system_context` (e.g., `core_provider`, `policy_pack`, `registration_commit_gate`) will silently lose that data in v1. | High |
| **Interface method stubs** | `PolicyRegistryImpl` has stub methods (`validate_project_map`, `git_registration_probe`, etc.) that return empty lists/dicts. If a consumer switches from the full `GatewayBusinessPolicy` to the bare `PolicyRegistryImpl`, validation silently passes. | Medium |
| **`write_targets()` date-dependent path** | The `"fact"` target includes today's date. Any consumer caching write-targets across midnight will get stale paths. | Low |
| **`RouteTargetPolicyImpl` routes set at `__init__`** | The `"fact"` route embeds `datetime.now().date()`, so route targets are fixed at construction time. Reusing a singleton across days gives wrong paths. | Medium |
| **`CoreConfig.__post_init__` validation** | Only validates `host`, `event`, `workspace_root`, `repo_root`. All 30+ other fields are unvalidated at construction. A caller passing `None` for a callback will get `TypeError` deep inside `build_context_package_core`. | Low |
| **`delegate_codex` / `delegate_claude`** | These hardcode `payload={}` for Codex but pass the real payload for Claude. Asymmetry could confuse consumers who expect symmetric signatures. | Low |

### 2.2 Safe areas

- The v2 output schema keys are stable and well-structured.
- `CoreConfig.from_gateway_kwargs()` provides a complete bridge from 37 kwargs to dataclass.
- Interface classes (ABC) are stable — method signatures are contract-bound.

---

## 3. Parameter Evolution: 37 flat params → CoreConfig

**Verdict: PASS**

### 3.1 Completeness check

`build_context_package_core()` accepts 37 keyword-only parameters. `CoreConfig` has:
- 35 direct fields matching those 37 parameters (all present)
- Plus 2 optional interface objects: `policy_registry` and `path_utils`

`CoreConfig.from_gateway_kwargs()` accepts all 37 original kwargs plus the 2 interface objects — the mapping is 1:1 and complete.

### 3.2 `_resolve_callbacks` correctness

The `_resolve_callbacks` function in `memory_hook_core.py` correctly:
1. Checks for `policy_registry` interface object first; if present, extracts 11 bound methods from it
2. Checks for `path_utils` interface object; if present, extracts 2 bound methods from it
3. Falls back to flat callback fields on `CoreConfig` when interface objects are absent

The fallback covers all 13 callback fields. The mapping is correct.

### 3.3 `build_context_package_from_config` wiring

This function calls `_resolve_callbacks(config)` and passes all 37 resolved values to `build_context_package_core()`. The parameter names and order match exactly. No data loss.

### 3.4 Backward compatibility path

`CoreConfig.to_gateway_kwargs()` uses `dataclasses.asdict()` to flatten back to a dict. This works for simple fields but would include `policy_registry` and `path_utils` interface objects in the output — callers expecting only the 37 legacy kwargs would get two extra keys. This is a minor asymmetry but not a break since the legacy builder ignores extra kwargs.

---

## 4. Schema Versioning: v1 ↔ v2

**Verdict: PASS (with caveats)**

### 4.1 Conversion correctness

`convert_to_v1()` in `memory_hook_schema.py` performs these transformations:

| v2 source | v1 destination | Notes |
|---|---|---|
| `schema_version: "wb-hook-v2"` | `schema_version: "context-package-v1"` | Correct |
| `repo_root`, `workspace_root`, `cwd` (top-level) | `paths.{repo_root, workspace_root, cwd}` | Correct nesting |
| `project_context` | `project` | Rename only |
| `task_context` | `task` | Rename only |
| `system_context` | **dropped** | Documented as intentional |
| `missing_paths` | **dropped** | Documented as intentional |
| All `_KEEP_KEYS` | copied as-is | Correct |

### 4.2 Data loss analysis

**Intentional drops:**
- `system_context`: Contains `boot_entry`, `state_summary`, `project_map_refs`, `legality_contract_validation`, `registration_commit_gate`, `policy_pack`, `truth_basis_refs`, `governance_frozen_tuple_*`, `event_contract_alignment_*`, `decision_refs`, `lesson_refs`, `docs_refs`, `hook_contract`, `core_provider`, `core_provider_requested`, `core_provider_fallback_errors`, `shadow_run`. This is a large amount of diagnostic data. For v1 consumers that only need paths/project/task, this is acceptable. For consumers that needed registration gate status or policy pack details, this is silent data loss.
- `missing_paths`: Already merged into `validation_errors` upstream, so no real loss.

**Structural changes:**
- Path fields moved from top-level to `paths.*`. Any v1 consumer expecting `package["repo_root"]` directly will break. This is the v1 contract, so it is correct by definition, but migration from pre-v1 would require updates.

### 4.3 Schema detection

`is_v1()` and `is_v2()` are simple string checks on `schema_version`. Correct and sufficient.

### 4.4 Caveat

The v1 output does NOT include `repo_root`, `workspace_root`, `cwd` if they are absent from the v2 input (guarded by `if key in package`). The v2 builder always provides them, so this is safe in practice. The conditional is defensive but could hide a bug if the v2 builder regressed.

---

## 5. Consumer Onboarding

**Verdict: FAIL**

### 5.1 Minimum integration path

To use memory-core as a consumer, the shortest path is:

```python
from workspace.tools import build_context_package_simple

package = build_context_package_simple("codex", "session-start", {"cwd": "/path/to/project"})
```

This returns a v1 context package. It works because:
1. The adapter is loaded at import time via `MEMORY_HOOK_ADAPTER` env var (default: `workbot`)
2. All constants are injected into the module's globals
3. `build_context_package_simple` handles everything internally

### 5.2 Barriers to entry

| Barrier | Detail |
|---|---|
| **No installation package** | The module is not a pip-installable package. It must be cloned and placed on `sys.path` with the exact `workspace/tools/` directory structure. |
| **Adapter coupling** | The default `workbot` adapter hardcodes paths to this specific repository's `memory/kb/`, `project-map/`, `projects/`, etc. A new project would need to write its own runtime profile adapter. |
| **Env var dependency** | `CMUX_SURFACE_ID` and `CMUX_WORKSPACE_ID` must be set for delegate execution. No defaults provided. |
| **`cmux` CLI dependency** | Host delegates require the `cmux` binary to be in PATH for non-noop execution. |
| **Filesystem assumptions** | The system expects a specific directory layout: `workspace/memory/kb/`, `workspace/project-map/`, `workspace/projects/`, `artifacts/memory-hook/contexts/`. No configuration layer to remap these. |
| **No documentation** | There is no README, docstring guide, or usage examples beyond the code itself. |
| **Python path gymnastics** | The module uses dual import styles (dotted `workspace.tools.*` and bare `memory_hook_*`) with try/except fallbacks. Consumers must match this pattern. |

### 5.3 What would make onboarding easier

1. A `pyproject.toml` with proper package metadata and entry points
2. A neutral/empty adapter that requires zero filesystem structure
3. A configuration layer (YAML/env) to remap canonical paths
4. A `README.md` with a 5-line getting-started example
5. Type stubs or a typed API surface documented in docstrings

---

## Summary Verdicts

| Category | Verdict |
|---|---|
| **API Stability** | **FAIL** — Too many internal functions exposed without `_` prefix; `__all__` inconsistency between package and module; dead code (`resolve_policy_conflict_via_registry`) |
| **Breaking Change Risk** | **FAIL** — Global injection at import time, v1→v2 data loss in `system_context`, date-dependent singleton targets, unvalidated `CoreConfig` fields |
| **Parameter Evolution** | **PASS** — `CoreConfig` is a complete and correct replacement for 37 flat params; bridge methods are bidirectional |
| **Schema Versioning** | **PASS** — v1↔v2 conversion is correct and documented; `system_context` drop is intentional; detection functions work |
| **Consumer Onboarding** | **FAIL** — Not installable, tightly coupled to workbot adapter's filesystem, no docs, requires `cmux` binary and specific env vars |

### Overall: **FAIL** (3 of 5 categories failing)

The core design is sound — the M2 interface abstraction, CoreConfig dataclass, and v1/v2 schema separation are all well-executed. The failures are primarily in surface hygiene (too many public internals, no installation story) and implicit contracts (global injection, env vars, filesystem assumptions). These are fixable without architectural changes.
