# Independent Audit 8: Type Safety and Data Contracts

**Date:** 2026-04-27
**Scope:** All Python files in `workspace/tools/` (13 files, ~2800 lines)
**Files reviewed:**

| File | Lines |
|---|---|
| `tools/__init__.py` | 24 |
| `tools/cmux_hook_state.py` | 221 |
| `tools/memory_hook_adapters/__init__.py` | 0 (empty) |
| `tools/memory_hook_adapters/neutral_policy.py` | 22 |
| `tools/memory_hook_adapters/workbot_policy.py` | 75 |
| `tools/memory_hook_adapters/workbot_runtime_profile.py` | 242 |
| `tools/memory_hook_config.py` | 162 |
| `tools/memory_hook_core.py` | 279 |
| `tools/memory_hook_gateway.py` | 898 |
| `tools/memory_hook_impls.py` | 1233 |
| `tools/memory_hook_interfaces.py` | 251 |
| `tools/memory_hook_provider_rollback.py` | 54 |
| `tools/memory_hook_schema.py` | 63 |
| `tools/validate_memory_system.py` | 241 |

---

## 1. Type Annotation Completeness

### Verdict: FAIL

The codebase uses `from __future__ import annotations` consistently, which is good. Most public-facing methods on classes are annotated. However, there are notable gaps:

### Module-level functions missing return types

`memory_hook_gateway.py` — 9 functions:

- `_build_gateway_business_policy()` → missing `-> GatewayBusinessPolicy`
- `_get_gateway_business_policy()` → missing `-> GatewayBusinessPolicy`
- `_load_external_core_builder()` → missing `-> CoreBuilder` (type alias exists but not used on return)
- `_get_policy_registry()` → missing `-> PolicyRegistry`
- `_get_route_policy()` → missing `-> RouteTargetPolicy`
- `_get_write_policy()` → missing `-> WriteTargetPolicy`
- `_get_artifact_sink()` → missing `-> ArtifactSink`
- `_get_error_sink()` → missing `-> ErrorSink`
- `determine_project_scope(cwd: Path)` → missing `-> str`

`cmux_hook_state.py` — 1 function:

- `_exclusive_hook_state_lock(path: Path)` → missing `-> Iterator[None]` (or `Generator[None, None, None]`)

`__init__.py` — 1 function:

- `__getattr__(name: str)` → missing `-> Any`

### Parameter type gaps

`memory_hook_impls.py` — `GatewayBusinessPolicyImpl.resolve_conflict()`:

```python
def resolve_conflict(self, policy_key: str, values: list[str], strategy: str) -> str:
```

The protocol declares `strategy: str | None` but the implementation uses `strategy: str`. The implementation body handles `strategy or self._conflict_strategies.get(...)`, implying `None` is expected, but the signature rejects it.

`memory_hook_impls.py` — `ClaudeDelegate.__init__`:

```python
state_recorder: Callable[..., Any] | None = None,
```

The `Callable[..., Any]` on `state_recorder` is too broad — it accepts any callable with any signature, making it impossible for the type checker to verify correct usage.

### Summary count

| Category | Count |
|---|---|
| Functions missing return type | 11 |
| Parameter type mismatch with protocol | 1 |
| Overly-broad Callable types | 2 |

The 11 missing return types are all on module-level internal functions (prefixed `_`), which lowers the severity. All public API functions (`build_context_package`, `build_context_package_simple`) are fully annotated. The single protocol mismatch on `resolve_conflict` is a real type safety gap.

---

## 2. Dict Key Contracts

### Verdict: FAIL

This is the most fragile area of the codebase. `dict[str, Any]` is used extensively with implicit key contracts that are neither typed nor validated.

### High-fragility contracts

**`truth_basis` dict** — returned by `truth_basis_for_scope_fn()` and consumed in `memory_hook_core.py`:

The core builder immediately indexes into this dict with 6+ keys (`"refs"`, `"errors"`, `"validation"`, `"policy"`, `"project_ref"`, `"source_refs"`, `"authority_refs"`, `"evidence_refs"`, `"conflict_status"`) without any type enforcement:

```python
# memory_hook_core.py — direct key access with no isinstance guard
truth_basis_refs = truth_basis["refs"]
truth_basis_errors = list(truth_basis["errors"])
# ... and 7 more direct key accesses in the same function
```

The stub in `PolicyRegistryImpl` returns `{}` for `truth_basis_for_scope()`, which would cause `KeyError` at runtime if used without the real implementation.

**`registration_commit_gate` dict** — returned by `git_registration_probe()` and consumed in `memory_hook_core.py`:

Keys accessed: `"phase"`, `"enforced"`, `"gate_event"`, `"triggered_on_current_event"`, `"status"`, `"enforcement_result"`. The `evaluate_registration_commit_gate` function in `memory_hook_core.py` does copy into a new dict before adding keys, which is defensive. But the initial probe from `PolicyRegistryImpl.git_registration_probe()` returns `{}`, which causes `.get()` to return `None` — not a crash, but silent incorrectness.

**`policy_pack` dict** — returned by `get_policy_pack_fn()`:

Expected keys: `"policies"`, `"schema_version"`, `"scope"`, `"conflict_strategies"`, `"default_strategy"`, `"inherits"`. The code in `memory_hook_core.py` does wrap the call in `try/except` and does `isinstance(policy_pack, dict)` checks, which provides partial protection.

**`package` context dict** — the return value of `build_context_package_core`:

This dict has ~25 top-level keys and deeply nested sub-dicts. It is passed through `write_artifacts_via_sink`, `_apply_artifact_compaction`, and `convert_to_v1` — all of which index specific keys without validation.

### Medium-fragility contracts

| Dict | Location | Keys accessed | Guard type |
|---|---|---|---|
| `payload` | `memory_hook_gateway.py` | `"cwd"`, `"task_ref"`, `"session_id"`, `"registration_paths"` | `.get()` with `isinstance` checks |
| `system_context` sub-dict | `memory_hook_gateway.py` | `"core_provider"`, `"shadow_run"`, etc. | `.setdefault()` / `.get()` |
| `surface_state` dict | `cmux_hook_state.py` | 8 hardcoded keys | `.setdefault()` with full defaults |
| `event_contract_files` dict | `memory_hook_impls.py` | `"upstream_standard"`, `"upstream_mapping"`, etc. | direct key access after iteration |

### Assessment

The hook-state module (`cmux_hook_state.py`) handles dict contracts best — it uses `.setdefault()` with complete default dicts. The core builder (`memory_hook_core.py`) is the most fragile — it does direct `dict[key]` access on externally-produced dicts. If any callback returns a malformed dict, the core builder crashes with `KeyError`.

---

## 3. Optional / None Handling

### Verdict: FAIL (2 risky patterns found)

### Issue A: `ClaudeDelegate.execute()` — potential `TypeError`

In `memory_hook_impls.py`, the `execute` method:

```python
if self._state_path_factory is None:
    ...
    state_file = str(default_hook_state_path(self._repo_root or Path.cwd()))
else:
    state_file = str(self._state_path_factory(self._repo_root or Path.cwd()))
```

If `_repo_root` is `None` (which it can be — it defaults to `None` in `__init__`), the fallback is `Path.cwd()`. This is technically safe but sematically wrong: the hook state would be written to the wrong project's runtime directory.

### Issue B: `truth_basis` direct key access without None guard

In `memory_hook_core.py`:

```python
truth_basis = truth_basis_for_scope_fn(project_scope)
truth_basis_refs = truth_basis["refs"]          # KeyError if missing
truth_basis_errors = list(truth_basis["errors"])  # KeyError if missing
```

The stub `PolicyRegistryImpl.truth_basis_for_scope()` returns `{}`, which means any code path using the stub (e.g., tests that don't override) would crash with `KeyError`. The validation test in `validate_memory_system.py` works around this with `_empty_truth_basis()` — a separate function that mirrors the expected shape. This duplication is itself a risk: if the core builder's expected keys change, `_empty_truth_basis` must be updated manually.

### Positive patterns

- `payload_cwd()`, `environment_cwd()`: properly return `Path | None` and all callers handle `None`
- `should_noop_for_external_context()`: uses `bool(env_cwd and path_within_repo(...))` — correct None-safe boolean
- `record_hook_event()` in `cmux_hook_state.py`: uses `str(payload.get("session_id") or "")` — safe
- `read_payload()`: checks `isinstance(loaded, dict)` before returning — safe

---

## 4. Dataclass Field Ordering

### Verdict: PASS

`CoreConfig` in `memory_hook_config.py` uses `@dataclass(kw_only=True)`:

```python
@dataclass(kw_only=True)
class CoreConfig:
    # Group 1: Environment (7 required fields)
    host: str
    event: str
    payload: dict[str, Any]
    cwd: Path
    project_scope: str
    workspace_root: Path
    repo_root: Path

    # Group 2: Paths (7 required fields)
    required_canonical: list[Path]
    # ...

    # Group 3: Policy config (8 fields, last 3 optional)
    legality_source_policy: str
    # ...
    governance_blocker_scopes: Collection[str] | None = field(default=None)
    event_contract_blocker_scopes: Collection[str] | None = field(default=None)
    core_evidence_refs: list[str] | None = field(default=None)

    # Group 4: Callbacks (13 required fields)
    # ...

    # Group 5: Interface objects (2 optional fields)
    policy_registry: PolicyRegistry | None = field(default=None)
    path_utils: PathUtils | None = field(default=None)
```

`kw_only=True` is necessary and correct here. Without it, Python would reject the dataclass because optional fields (with defaults) appear after required fields within Group 3 and Group 5. The grouping by concern area is well-organized, and the `__post_init__` validation correctly guards `host` and path types.

`GatewayBusinessPolicyConfig` in `memory_hook_impls.py` does NOT use `kw_only=True`:

```python
@dataclass(frozen=True)
class GatewayBusinessPolicyConfig:
    # ... 33 required fields ...
    policy_pack_path: Path | None = None
```

This works because the single optional field (`policy_pack_path`) is the last field. This is technically correct but fragile — adding another optional field anywhere but the end would require `kw_only=True`.

---

## 5. Protocol Compliance

### Verdict: PASS (with 1 minor deviation)

All concrete implementations satisfy their ABC protocols at the method-signature level:

| Protocol | Implementation | Compliant? |
|---|---|---|
| `HostDelegate` | `CodexDelegate` | Yes — all 3 abstract methods implemented |
| `HostDelegate` | `ClaudeDelegate` | Yes — all 3 abstract methods implemented |
| `PolicyRegistry` | `PolicyRegistryImpl` | Yes — all 11 abstract methods implemented |
| `RouteTargetPolicy` | `RouteTargetPolicyImpl` | Yes — `resolve()` implemented |
| `WriteTargetPolicy` | `WriteTargetPolicyImpl` | Yes — `get_targets()` implemented |
| `GatewayBusinessPolicy` | `GatewayBusinessPolicyImpl` | Yes — all 14 abstract methods implemented |
| `GatewayBusinessPolicy` | `NeutralGatewayBusinessPolicy` | Yes — inherits from `GatewayBusinessPolicyImpl` |
| `GatewayBusinessPolicy` | `WorkbotGatewayBusinessPolicy` | Yes — inherits from `NeutralGatewayBusinessPolicy` |
| `ArtifactSink` | `ArtifactSinkImpl` | Yes — `write()` and `ensure_dirs()` implemented |
| `ErrorSink` | `ErrorSinkImpl` | Yes — `log()` implemented |
| `PathUtils` | `PathUtilsImpl` | Yes — `extract_excerpt()` and `write_targets()` implemented |

### Minor deviation

`PolicyRegistryImpl.resolve_conflict(self, policy_key: str, values: list[str], strategy: str)` vs protocol `resolve_conflict(self, policy_key: str, values: list[str], strategy: str | None)`:

The implementation's `strategy: str` is stricter than the protocol's `str | None`. Since the implementation provides a default (`strategy or self._conflict_strategies.get(...)`), the body is None-tolerant, but the signature rejects `None` at the type level. A type checker like mypy would flag this as a protocol violation (contravariant parameter type).

### Stub compliance concern

`PolicyRegistryImpl` implements 7 stub methods (e.g., `validate_project_map`, `truth_basis_for_scope`) that return empty collections. These satisfy the protocol signature but do not perform any real work. The `_resolve_callbacks()` function in `memory_hook_core.py` correctly falls back to flat callback fields when `policy_registry` is `None`, so the stubs are only used when the registry is present but not fully wired. This is documented as intentional ("Stub: return empty list. Real impl delegates to GatewayBusinessPolicy"), but it means `PolicyRegistryImpl` as a standalone class is not functionally complete.

---

## Overall Verdict: FAIL

| Category | Verdict | Severity |
|---|---|---|
| Type annotation completeness | FAIL | Medium |
| Dict key contracts | FAIL | High |
| Optional / None handling | FAIL | Medium |
| Dataclass field ordering | PASS | — |
| Protocol compliance | PASS | Low deviation |

### Key risks

1. **Dict key contracts** are the highest-risk area. The core builder directly indexes into externally-produced dicts with no validation. A single malformed callback return causes `KeyError` at runtime. Introducing `TypedDict` for the 4+ dict contracts (truth_basis, policy_pack, registration_gate, context_package) would catch these errors at type-check time.

2. **Missing return types** on 11 internal functions means IDE tooling and static analysis cannot catch regressions when these functions are refactored.

3. **Protocol deviation** on `resolve_conflict` would be caught by `mypy --strict-optional` but is currently silent.

### Suggested remediation (not part of this audit)

- Add `TypedDict` definitions for `TruthBasis`, `RegistrationGate`, and `PolicyPack` contracts
- Annotate return types on all module-level functions in `memory_hook_gateway.py`
- Fix `resolve_conflict` signature to match protocol: `strategy: str | None = None`
- Add `isinstance` guards before direct key access on externally-produced dicts in `memory_hook_core.py`
