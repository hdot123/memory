# RE-AUDIT 07: Test Coverage and Quality

**Date:** 2026-04-27
**Branch:** codex/re-audit
**Audit scope:** `tests/` vs `workspace/tools/`

---

## 1. Coverage Completeness

194 tests across 18 test files. Below maps each source module to its test coverage.

### Tested modules

| Source module | Lines | Direct test file(s) | Coverage level |
|---|---|---|---|
| `memory_hook_schema.py` | 74 | `test_api_completion.py` (TestSchemaConversion) | Good |
| `memory_hook_config.py` | 227 | `test_refactoring.py` (TestCoreConfig), `test_core_config_path.py`, `test_policy_delegation.py` | Good |
| `memory_hook_core.py` | 379 | `test_core_config_path.py`, `test_memory_hook_core_m5_adapter_slimming.py`, `test_m7_p4_gateway_integration.py` | Partial |
| `memory_hook_impls.py` | 1248 | `test_api_completion.py`, `test_m2_adapter_extraction.py`, `test_refactoring.py`, `test_policy_delegation.py` | Partial |
| `memory_hook_gateway.py` | 1021 | `test_m7_p2_gateway_decoupling.py`, `test_m7_p4_gateway_integration.py`, `test_m2_adapter_extraction.py`, `test_memory_hook_core_m5_adapter_slimming.py`, `test_memory_hook_gateway_m6_*.py` | Partial |
| `memory_hook_provider_rollback.py` | 60 | `test_memory_hook_gateway_m6_batch3_structure_and_rollback.py` | Partial |
| `memory_hook_interfaces.py` | 335 | Indirectly via impl tests in `test_policy_delegation.py` | Indirect only |
| `validate_memory_system.py` | 270 | `test_validate_memory_system.py` | Good |
| `__init__.py` | 25 | `test_api_completion.py` (TestPackageAPI) | Good |
| `memory_hook_adapters/workbot_runtime_profile.py` | 267 | `test_m2_adapter_extraction.py`, `test_m3_policy_pack_wiring.py` | Good |
| `memory_hook_adapters/workbot_policy.py` | 82 | `test_memory_hook_gateway_m6_batch3_structure_and_rollback.py`, `test_m7_p2_gateway_decoupling.py` | Partial |
| `memory_hook_adapters/neutral_policy.py` | 22 | `test_m3_consumer_truth_cleanup.py` (import only) | Minimal |

### Untested modules

| Source module | Lines | Notes |
|---|---|---|
| `cmux_hook_state.py` | **225** | **Zero test coverage.** Entire module untested: HookStateError, _exclusive_hook_state_lock, runtime_state_dir, default_*_path helpers, reset_hook_state, load_hook_state, write_hook_state, get_surface_hook_state, record_hook_event. |

### Untested classes in tested modules

| Class / Function | Module | Notes |
|---|---|---|
| `RouteTargetPolicyImpl` | `memory_hook_impls.py` | No direct tests. Only called indirectly through gateway wrappers. |
| `WriteTargetPolicyImpl` | `memory_hook_impls.py` | No direct tests. |
| `ArtifactSinkImpl` | `memory_hook_impls.py` | No direct tests. Indirectly exercised via ArtifactWriter but not verified in isolation. |
| `ErrorSinkImpl` | `memory_hook_impls.py` | No direct tests. |
| `GatewayBusinessPolicyConfig` | `memory_hook_impls.py` | Used as a dataclass in `test_memory_hook_gateway_m6_batch2_adapter_policy.py` but not validated for field defaults or type coercion. |
| `GatewayBusinessPolicyImpl` | `memory_hook_impls.py` | Partially tested via subclass in test files but not directly instantiated. |
| All ABCs in `memory_hook_interfaces.py` | `memory_hook_interfaces.py` | HostDelegate, PolicyRegistry, RouteTargetPolicy, WriteTargetPolicy, GatewayBusinessPolicy, ArtifactSink, ErrorSink, PathUtils — no direct tests for the interface contracts themselves. |

### Untested functions in tested modules

| Function | Module | Notes |
|---|---|---|
| `main()` | `memory_hook_gateway.py` | CLI entry point untested. Only rollback's main() is tested. |
| `_parse_args()` | `memory_hook_gateway.py` | Argparse logic untested. |
| `_delegate_codex()` / `_delegate_claude()` | `memory_hook_gateway.py` | Direct subprocess delegation untested. |
| `_execute_delegate_via_facade()` | `memory_hook_gateway.py` | Untested. |
| `_read_payload()` | `memory_hook_gateway.py` | JSON parsing untested. |
| `_environment_cwd()` / `_path_within_repo()` | `memory_hook_gateway.py` | Untested in isolation. |
| `_discover_cwd()` | `memory_hook_gateway.py` | Only tested via monkeypatch override in `test_m7_p4_gateway_integration.py`, never exercised directly. |
| `append_error_log()` / `write_artifacts()` / `_ensure_artifact_dirs()` | `memory_hook_gateway.py` | Untested. |
| `resolve_route_target()` | `memory_hook_gateway.py` | Untested. |

---

## 2. Test Isolation

### Potential issues

**sys.modules manipulation (moderate risk)**

- `test_m7_p2_gateway_decoupling.py` and `test_m7_p4_gateway_integration.py` both use `_clear_gateway_cache()` + `importlib.import_module()` + `patch.dict(os.environ, ...)` to reload the gateway under different env conditions.
- `_clear_gateway_cache()` is a plain function, not a pytest fixture with teardown. If a test crashes mid-way, modules may remain deleted, affecting subsequent tests.
- `test_policy_delegation.py` injects a mock `memory_hook_gateway` into `sys.modules` via an autouse fixture with proper cleanup (yield + pop). This is well-isolated.

**Environment variable mutation (low risk)**

- Multiple tests use `monkeypatch.setenv()` and `monkeypatch.delenv()` for `MEMORY_HOOK_ADAPTER`, `MEMORY_HOOK_FORCE`, `MEMORY_HOOK_POLICY_PACK_PATH`, `MEMORY_HOOK_CORE_PROVIDER`, `CMUX_HOOK_STATE_FILE`.
- pytest's `monkeypatch` fixture handles cleanup, so these are safe.

**Filesystem state (low risk)**

- Tests use `tmp_path` fixtures consistently. No shared filesystem state detected.

**Module-level constant caching (low-moderate risk)**

- The gateway module computes `_ADAPTER_NAME`, `_ADAPTER_REGISTRY`, `GATEWAY_POLICY_CLASS` at import time. Tests that reload the gateway rely on `_clear_gateway_cache()` doing a thorough job. If any other test holds a reference to a previously-loaded gateway module, it may see stale constants.

### Verdict

Tests run cleanly 3x3 = all 194 pass consistently. No order-dependency observed in practice. The sys.modules manipulation pattern is fragile in principle but currently stable because pytest runs these test files in a predictable order.

---

## 3. Assertion Quality

### Strong assertions (meaningful)

Most tests in this suite use high-quality assertions:

- `test_core_config_path.py`: Equality comparisons of full result dicts, `pytest.raises(ValueError, match="...")` with regex matching.
- `test_m7_p4_policy_pack_edge_cases.py`: `pytest.raises(ValueError, match="conflict on.*strategy=fail-fast")` with pattern matching.
- `test_refactoring.py`: Mock verification with `assert_called_once_with()`, specific value checks on dict keys.
- `test_m2_adapter_extraction.py`: Checks specific dict keys and values in runtime profiles.

### Trivial assertions

Counted assertions with low informational value:

| Pattern | Occurrences | Files |
|---|---|---|
| `isinstance(result, list/dict)` without value check | ~15 | `test_api_completion.py`, `test_policy_delegation.py` |
| `assert X is not None` | 4 | `test_m2_adapter_extraction.py`, `test_m3_consumer_truth_cleanup.py`, `test_m7_p2_gateway_decoupling.py`, `test_refactoring.py` |
| `assert callable(X)` | 5 | `test_api_completion.py`, `test_m3_consumer_truth_cleanup.py` |
| `assert X == []` or `assert result == []` | ~8 | Multiple files |

Total trivial assertions: **~32 of ~338 total assert statements (~9.5%)**.

These are not harmful but are low-signal. A `isinstance(result, dict)` without checking the dict's content tells us only that the function didn't crash and returned the right type — not that it returned the right value.

### Assertion coverage gap

Several test files contain only `isinstance` / `== []` / `== {}` checks:

- `test_api_completion.py::TestExtendedPolicyRegistry` — 6 methods tested, all return-type checks only.
- `test_policy_delegation.py::TestPolicyRegistryDelegation` — 8 tests, all type checks.

These tests verify the delegation stubs return the correct type but do not verify any behavioral contract.

---

## 4. Edge Case Coverage

### Important untested edge cases

1. **`convert_to_v1` with empty or minimal input** — `test_api_completion.py` tests v2→v1 conversion but does not test with an empty dict `{}`, a dict with only `schema_version`, or a dict with all keys simultaneously.

2. **`CoreConfig` with boundary values** — No tests for `event` values other than valid strings. No tests for `payload` being `None` (gateway accepts `{}`). No tests for callback fields being `None` or non-callable.

3. **`PolicyRegistryImpl.resolve_conflict` with unknown strategy** — Only `fail-fast`, `prefer-strict`, and `preserve-and-escalate` are tested. No test for an unknown strategy string.

4. **`PolicyRegistryImpl.resolve_conflict` with single value** — All tests pass 2+ values. No test for a single-value list (trivial case).

5. **`ArtifactWriter` with deeply nested package** — Only tested with flat dict packages. No test for nested structures.

6. **`build_context_package` with `None` payload** — `test_core_config_path.py` tests with `payload={}` but `build_context_package_simple` tests `payload=None`. The full `build_context_package` path with `None` is not covered.

7. **Gateway CLI `main()` exit codes** — Only the rollback `main()` is tested. Gateway's `main()` with various argparse inputs (including `--noop`, `--dump`, `--shadow-run`) is untested.

8. **Delegate execute() with real subprocess failure** — `CodexDelegate.execute` and `ClaudeDelegate.execute` are never called in tests. Error handling for subprocess failures is untested.

9. **`cmux_hook_state.py` all functions** — 225-line module with zero test coverage. Critical functions like `write_hook_state` (with file locking), `load_hook_state_strict`, `record_hook_event` are completely untested.

10. **`_apply_artifact_compaction` with missing keys** — Tests only cover packages that have all compaction keys. No test for a package missing some keys.

---

## 5. Test Naming

### Strengths

- Class names are descriptive: `TestSchemaConversion`, `TestPathUtils`, `TestDelegateRouter`, `TestPolicyPackInjection`, `TestAdapterDiscovery`.
- Most method names follow `test_<what>_<condition>` pattern: `test_config_rejects_invalid_host`, `test_malformed_json_silent_fallback`, `test_env_var_selects_adapter`.
- Docstrings on test classes and methods provide clear descriptions of what is being tested.

### Weaknesses

- `test_api_completion.py` has a misleading module name — it tests schema conversion, PathUtils, package API, and PolicyRegistry stubs, not "API completion".
- Some test methods are generic: `test_produces_same_result_as_kwargs_path` (which result? which kwargs?).
- `test_m3_doc_scope_coverage.py` has 18 assertions that are all essentially the same pattern (`assert "Scope: adapter" in text`, `assert "不是模块默认" in text`). These could be parameterized.
- No parameterized tests (`@pytest.mark.parametrize`) found anywhere in the suite. Many repetitive assertions could be condensed.

---

## 6. Stability Verification

Ran `python3 -m pytest -q tests` three times:

| Run | Result | Time |
|---|---|---|
| 1 | 194 passed | 2.60s |
| 2 | 194 passed | 2.74s |
| 3 | 194 passed | 2.93s |

**Stable. No flaky tests detected.**

---

## Summary

| Metric | Value |
|---|---|
| Total tests | 194 |
| Test files | 18 |
| Source modules in `workspace/tools/` | 12 (including subpackages) |
| Modules with zero coverage | **1** (`cmux_hook_state.py`, 225 lines) |
| Classes with zero direct coverage | 4 (`RouteTargetPolicyImpl`, `WriteTargetPolicyImpl`, `ArtifactSinkImpl`, `ErrorSinkImpl`) |
| ABC interfaces with zero direct coverage | 8 (all in `memory_hook_interfaces.py`) |
| Gateway functions with zero coverage | ~9 |
| Trivial assertions (~type-only checks) | ~32 of ~338 (~9.5%) |
| Parameterized tests | 0 |
| Stability (3 runs) | 100% pass |

### Top Recommendations

1. **Add tests for `cmux_hook_state.py`** — 225 lines of critical state management code with zero coverage is the single biggest gap.
2. **Test `CodexDelegate.execute` and `ClaudeDelegate.execute`** — These are the primary runtime delegation paths but never called in tests.
3. **Parameterize repetitive string-matching tests** in `test_m3_doc_scope_coverage.py` and `test_m3_consumer_truth_cleanup.py` (36 similar assertions across 2 files).
4. **Add edge case tests** for `convert_to_v1`, `resolve_conflict`, and `build_context_package` with boundary inputs.
5. **Convert `_clear_gateway_cache` to a pytest fixture** with proper setup/teardown to eliminate sys.modules leak risk.
