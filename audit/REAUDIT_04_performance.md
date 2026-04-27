# Re-Audit 04: Performance (Compare with Independent Audit 07)

**Scope:** All Python files in `workspace/tools/` (14 files, ~8,000 lines)
**Reference:** `audit/INDEPENDENT_07_performance.md`
**Date:** 2026-04-27

---

## 1. Hot Path Efficiency

**Verdict: FAIL** (unchanged from Independent Audit 07)

The critical path `build_context_package()` → `build_context_package_from_config()` → `build_context_package_core()` still exhibits the same structural issues.

### 1.1 `_get_gateway_business_policy()` — still uncached

No change. The function at line ~120 of `memory_hook_gateway.py` retains the exact same comment and behavior:

```python
def _get_gateway_business_policy() -> GatewayBusinessPolicy:
    # No singleton caching here so tests and runtime can monkeypatch constants
    # and immediately observe fresh adapter config injection.
    return _build_gateway_business_policy()
```

Every `build_context_package()` call reconstructs the full `GatewayBusinessPolicyConfig` (~35 fields) and a new `GatewayBusinessPolicyImpl` / `WorkbotGatewayBusinessPolicy` instance. The other three facades (`_get_policy_registry`, `_get_route_policy`, `_get_write_policy`) still cache via module-level singletons — this one remains the outlier.

### 1.2 `git_registration_probe()` — still 3 subprocesses per invocation

No change. `_git_registration_probe()` in `memory_hook_gateway.py` still runs three separate `subprocess.run` calls:
- `git status --short -- …`
- `git rev-parse HEAD`
- `git diff-tree --no-commit-id --name-only -r HEAD -- …`

This remains the most expensive single operation on the hot path.

### 1.3 `truth_basis_for_scope()` — still 5+ file reads per call

No change. `GatewayBusinessPolicyImpl.truth_basis_for_scope()` iterates over all global canonical files (5 files) and calls `_truth_basis_errors_for()` on each, which does `path.read_text()` + full parse. The project canonical file adds a 6th read.

### 1.4 `CoreConfig` still carries callback-heavy payload

No change. `CoreConfig` still carries 14+ callback references plus 40+ config fields. `dataclasses.asdict()` on this in `to_gateway_kwargs()` still performs a deep copy if the bridge path is used.

### 1.5 No O(n²) patterns — still clean

Confirmed: set intersections, list comprehensions, and dict constructions remain linear. No nested loops over unbounded collections were found.

---

## 2. I/O Patterns

**Verdict: FAIL** (unchanged, but stale date bug partially fixed)

### 2.1 File reads per invocation — unchanged

The estimated worst-case remains ~25–30 file reads + 3 git subprocesses + 3 file writes per invocation. No batching, caching, or parallelization was added to any of the file-reading paths (`validate_project_map_files()`, `validate_unique_legal_system_contract()`, `governance_frozen_tuple_blocker_errors()`, `event_contract_blocker_errors()`, `truth_basis_for_scope()`).

### 2.2 Stale date bug — partially fixed

| Component | Status in Audit 07 | Current Status |
|---|---|---|
| `RouteTargetPolicyImpl._routes["fact"]` | Stale (computed at `__init__`) | **FIXED** — stored as `None`, computed at `resolve()` call time via `datetime.now().date().isoformat()` |
| `WriteTargetPolicyImpl._targets["fact"]` | Stale (computed at `__init__`) | **STILL BROKEN** — `datetime.now().date().isoformat()` is still computed once in `__init__` and stored in `self._targets["fact"]` |
| `write_targets()` fallback in gateway | Stale (noted) | Fixed — computes at call time |
| `PathUtilsImpl.write_targets()` | N/A | Correct — computes at call time |

`WriteTargetPolicyImpl.__init__()` in `memory_hook_impls.py` (~line 470) still does:

```python
self._targets: dict[str, Any] = {
    "fact": str(workspace_root / "memory" / "log" / f"{datetime.now().date().isoformat()}.md"),
    ...
}
```

This means if the process lives past midnight, the "fact" route silently points to yesterday's log file. `WriteTargetPolicyImpl.get_targets()` returns `dict(self._targets)` — a shallow copy — which does not re-evaluate the date.

### 2.3 `cmux_hook_state.py` — fsync still present

No change. `_write_hook_state_unlocked()` still uses `tempfile.mkstemp` + `os.fsync()` + `Path.replace()`. This is correct for crash safety but remains a blocking syscall on every `record_hook_event()` call.

### 2.4 Redundant path reconstruction

No change. `_get_gateway_business_policy()` rebuilds all Path objects and collections from scratch on every call, even though they are effectively constant during a process lifetime.

---

## 3. Memory Usage

**Verdict: PASS** (unchanged)

No regressions detected. The memory profile remains clean:

- `CoreConfig` is still a `dataclass(frozen=True)` with no mutable state accumulating across calls.
- The three module-level singletons (`_default_policy_registry`, `_default_route_policy`, `_default_write_policy`) are set once and never grow.
- `PolicyRegistryImpl._load_dynamic_policy_pack()` reads a JSON file once at `__init__` and stores policies in a plain dict.
- `ArtifactSinkImpl.write()` writes to disk and releases references.
- No circular references, closure traps, or unbounded growth patterns were found.
- Per-call allocations (`GatewayBusinessPolicyConfig`, `GatewayBusinessPolicyImpl`) are short-lived and GC'd normally.

---

## 4. Import Cost

**Verdict: PASS** (unchanged)

No regressions detected:

- Module-level imports remain standard library only (`argparse`, `json`, `os`, `re`, `shutil`, `subprocess`, `sys`, `datetime`, `pathlib`, `typing`).
- `workspace/tools/__init__.py` still uses `__getattr__` for lazy public API imports.
- The adapter bootstrap (`build_workbot_runtime_profile()`) still runs once on first import with ~50ms estimated startup cost on Apple Silicon.
- Try/except import fallbacks remain unchanged.

---

## 5. Scalability Limits

**Verdict: FAIL** (unchanged)

### 5.1 What breaks at 1,000 calls/second — same failure modes

| Component | Failure mode | Status |
|---|---|---|
| `git_registration_probe()` (3 subprocesses/call) | **3,000 git processes/sec** — fork/exec overhead, process table exhaustion | Unchanged |
| `_exclusive_hook_state_lock()` (fcntl advisory lock) | Single lock file contention, serializes all state writes | Unchanged |
| `_get_gateway_business_policy()` (uncached) | ~35-field dataclass allocation per call → GC pressure | Unchanged |
| `ArtifactSinkImpl.write()` (2 writes + 1 append) | **3,000 file operations/sec** — IOPS saturation | Unchanged |
| `fsync` in `_write_hook_state_unlocked()` | Each `record_hook_event()` forces disk flush — hard bottleneck at scale | Unchanged |
| `snapshot_path` collision loop | `while snapshot_path.exists()` becomes O(n) per call at high write rates | Unchanged |

### 5.2 Global state conflicts — partially improved

- `RouteTargetPolicyImpl._routes["fact"]` stale date bug is **fixed** — now computed at `resolve()` call time.
- `WriteTargetPolicyImpl._targets["fact"]` stale date bug is **still present** — computed at `__init__` time.
- Module-level singletons remain non-thread-safe, but the hook runs in a single-threaded subprocess model (low-risk).

### 5.3 No rate limiting or backpressure — unchanged

No mechanism exists to detect or throttle rapid-fire hook invocations. A burst of 100 prompt-submit events in 1 second still triggers 100 full validation chains.

### 5.4 No async / parallelization — unchanged

All I/O is synchronous and sequential. `truth_basis_for_scope()` reads 5+ files one at a time. `validate_unique_legal_system_contract()` reads 7 files one at a time. These could be parallelized for meaningful latency reduction.

---

## Summary

| Category | Audit 07 | Re-Audit 04 | Change |
|---|---|---|---|
| Hot Path Efficiency | **FAIL** | **FAIL** | No change |
| I/O Patterns | **FAIL** | **FAIL** | Stale date in RouteTargetPolicyImpl fixed; WriteTargetPolicyImpl still broken |
| Memory Usage | **PASS** | **PASS** | No change |
| Import Cost | **PASS** | **PASS** | No change |
| Scalability Limits | **FAIL** | **FAIL** | RouteTargetPolicyImpl stale date fixed; WriteTargetPolicyImpl still broken; all other issues unchanged |

### Overall Verdict: **FAIL** (3 of 5 categories failed — unchanged)

### What changed since Independent Audit 07

1. **`RouteTargetPolicyImpl` stale date bug fixed** — `"fact"` route is now stored as `None` in `_routes` and computed at `resolve()` call time. This eliminates the midnight-crossing stale path bug for the route policy.

### What remains unfixed

1. **`WriteTargetPolicyImpl` stale date bug** — `"fact"` target is still computed at `__init__` time. If the process lives past midnight, `get_targets()` returns yesterday's log path.
2. **`_get_gateway_business_policy()` uncached** — every call rebuilds the full config and policy instance.
3. **`git_registration_probe()` 3 subprocesses** — no memoization or event-aware skipping.
4. **~25-30 file reads per invocation** — no batching, caching, or parallelization.
5. **`fsync` on every state write** — crash-safe but blocks under high frequency.
6. **No rate limiting or backpressure** — burst events trigger full validation chains.
7. **Synchronous sequential I/O** — no asyncio or ThreadPoolExecutor usage.

### Recommended improvements (same priority order as Audit 07)

1. **Fix `WriteTargetPolicyImpl._targets["fact"]`** — store `None` and compute at `get_targets()` call time, matching the `RouteTargetPolicyImpl` pattern. (Smallest fix, immediate correctness win.)
2. **Cache `_get_gateway_business_policy()`** with invalidation on env/config change. Single largest win for hot path.
3. **Memoize `git_registration_probe()`** results for the duration of a single hook event cycle, or skip it for non-"stop" events.
4. **Batch file reads** in `validate_unique_legal_system_contract()` and `truth_basis_for_scope()` using `concurrent.futures.ThreadPoolExecutor`.
5. **Add a lightweight rate limiter** in `main()` to detect and collapse rapid-fire events.
