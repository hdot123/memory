# R3: Bug Review — core.py + config.py + schema.py

## Findings

### 1. `memory_hook_core.py:22-55` — interface object partially supplied causes `AttributeError` instead of falling back to configured callbacks

- File: `/Users/busiji/memory/workspace/tools/memory_hook_core.py`
- Lines: 22-55
- Trigger condition: `build_context_package_from_config(config)` receives a `CoreConfig` where `policy_registry` or `path_utils` is non-`None`, but the object is missing any method that `_resolve_callbacks()` reads directly. For example, a partial/fine-grained policy object that has `validate()` and `get_policy_pack()` but not `validate_project_map()`, or a path utility object that has `extract_excerpt()` but not `write_targets()`.
- Expected behavior: Missing interface methods should either be validated as a clear configuration error before execution, or fall back to the corresponding flat callback fields already present on `CoreConfig`, because the docstring says interface objects are used when present and the flat callbacks are the fallback.
- Actual behavior: `_resolve_callbacks()` directly dereferences every method on the non-`None` interface object (`pr.validate_project_map`, `pu.write_targets`, etc.). If any method is absent, Python raises `AttributeError` before the core package can be built, even when the flat fallback callback exists and is callable.

### 2. `memory_hook_schema.py:23-27,59-64` — v2 missing-path failures are dropped from v1 output instead of being preserved in `validation_errors`

- File: `/Users/busiji/memory/workspace/tools/memory_hook_schema.py`
- Lines: 23-27, 59-64
- Trigger condition: `convert_to_v1()` converts a v2 package produced by `build_context_package_core()` when one or more required/project canonical files are missing. In v2, those paths are stored in top-level `missing_paths` and `status` becomes `degraded`.
- Expected behavior: The v1 package should still expose the concrete missing-path failures to downstream parsers, either by preserving them or by merging them into `validation_errors`, matching the function comment that `missing_paths` is "merged into validation_errors upstream".
- Actual behavior: `build_context_package_core()` does not add `missing_paths` to `validation_errors`; it returns them only in the top-level `missing_paths` field. `convert_to_v1()` then drops `missing_paths` and only carries existing `validation_errors`. A package can therefore become `status: degraded` with no missing-path details in v1, causing downstream consumers that rely on `validation_errors` to lose the reason for the degraded state.

## Non-findings Checked

- `memory_hook_config.py:190-274` `from_gateway_kwargs()` maps all current constructor fields, including `hook_contract_path`, `surface_id`, `workspace_id`, optional blocker scopes, evidence refs, and interface objects. I did not find a concrete missing field or type mismatch in this method.
- `memory_hook_schema.py:67-74` `is_v1()` / `is_v2()` compare exact `schema_version` strings and did not show a concrete false positive/false negative for dict packages produced by this code.
- `memory_hook_config.py:90-181` `CoreConfig.__post_init__()` runs for normal dataclass construction and `from_gateway_kwargs()`. I did not find an in-repo construction path that bypasses it without deliberately using Python object-allocation internals.
