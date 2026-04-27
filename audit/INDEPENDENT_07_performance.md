# Independent Audit 07: Performance and Scalability

**Scope:** All Python files in `workspace/tools/` (14 files, ~8,000 lines)
**Constraint:** Read-only audit — no code modifications.
**Date:** 2026-04-27

---

## 1. Hot Path Efficiency

**Verdict: FAIL**

The critical path is `build_context_package()` → `build_context_package_from_config()` → `build_context_package_core()`. Several issues:

### 1.1 No caching on the business policy builder

`_get_gateway_business_policy()` in `memory_hook_gateway.py` deliberately has **no singleton caching** (comment: "No singleton caching here so tests and runtime can monkeypatch constants"). Every `build_context_package()` call reconstructs the full `GatewayBusinessPolicyConfig` dataclass (~35 fields) and a new `GatewayBusinessPolicyImpl` instance. Other facades (`_get_policy_registry`, `_get_route_policy`, `_get_write_policy`) **do** cache — this one is the outlier.

### 1.2 `git_registration_probe()` spawns 3 subprocesses per invocation

In `memory_hook_gateway.py`, `git_registration_probe()` runs three separate `subprocess.run` calls every time:
- `git status --short -- …`
- `git rev-parse HEAD`
- `git diff-tree --no-commit-id --name-only -r HEAD -- …`

This is the most expensive single operation on the hot path. At typical hook frequency (every session-start, prompt-submit, stop, notification), this adds measurable latency even on local SSD.

### 1.3 Repeated file reads in `truth_basis_errors_for()`

`GatewayBusinessPolicyImpl._truth_basis_errors_for()` reads the target file via `path.read_text()` at entry, then calls `_truth_basis_sections_for()` which re-parses the same text. This is fine per-call, but `truth_basis_for_scope()` iterates over **all** global canonical files (5 files) and calls `_truth_basis_errors_for()` on each one. That's 5+ full file reads + parse per hook event.

### 1.4 `CoreConfig.from_gateway_kwargs()` calls `dataclasses.asdict()`

In `memory_hook_config.py`, `to_gateway_kwargs()` does `asdict(self)` which performs a deep copy of all 40+ fields including callbacks. This is called only if the bridge path is used, but worth noting.

### 1.5 No O(n²) patterns detected

Set intersections (`read_set`, `truth_basis_set`, `decisions & truth_basis_set`, etc.) are all O(n) or O(n log n). List comprehensions and dict constructions are linear. No nested loops over unbounded collections were found.

---

## 2. I/O Patterns

**Verdict: FAIL**

### 2.1 File reads per invocation (estimated worst case)

| Source | File reads | Notes |
|---|---|---|
| `validate_project_map_files()` | 3–7 | project-map INDEX, legal-core-map, ingestion-registry-map, etc. |
| `validate_unique_legal_system_contract()` | 7 | workspace INDEX, global INDEX, docs INDEX, truth model, overview doc, hook contract, legal-core-map + registry |
| `governance_frozen_tuple_blocker_errors()` | 4 | governance frozen tuple files |
| `event_contract_blocker_errors()` | 5 | upstream_standard, upstream_mapping, formal_contract, upstream_samples, downstream_samples |
| `truth_basis_for_scope()` | 5–6 | global canonical files + project canonical |
| `extract_excerpt(NOW.md)` | 1 | always called |
| `git_registration_probe()` | 0 (subprocess) | 3 git subprocesses instead |
| `write_artifacts_via_sink()` | 2 writes + 1 append | snapshot JSON, latest JSON, events.jsonl append |

**Total: ~25–30 file reads + 3 git subprocesses + 3 file writes per invocation.**

### 2.2 Redundant file access

- `write_targets()` and `WriteTargetPolicyImpl.get_targets()` both compute `datetime.now().date().isoformat()` for the "fact" log path, but the value is **captured at construction time** in `RouteTargetPolicyImpl` and `WriteTargetPolicyImpl`, not at call time. This means the date is stale if the process lives past midnight.
- `_get_gateway_business_policy()` creates a new `GatewayBusinessPolicyConfig` on every call, which means all path lists and sets are rebuilt from scratch — even though they're effectively constant during a process lifetime.

### 2.3 `cmux_hook_state.py` — atomic writes are correct but costly

`_write_hook_state_unlocked()` uses `tempfile.mkstemp` + `fsync` + `Path.replace()` for atomic writes. This is **correct** (crash-safe), but the `fsync` on every `record_hook_event()` call is a blocking syscall that forces data to disk. Under high frequency this becomes a bottleneck.

---

## 3. Memory Usage

**Verdict: PASS**

### 3.1 No obvious memory leaks

- `CoreConfig` is a `dataclass(kw_only=True)` with `frozen=True` config — no mutable state accumulates across calls.
- The three module-level singletons (`_default_policy_registry`, `_default_route_policy`, `_default_write_policy`) are set once and never grow.
- `PolicyRegistryImpl._load_dynamic_policy_pack()` reads a JSON file once at `__init__` and stores the policies in a plain dict. No unbounded growth.
- `ArtifactSinkImpl.write()` writes to disk and releases references.

### 3.2 Large objects held per-call

- The context package dict returned by `build_context_package_core()` is ~10–20KB (JSON-serialized). It contains `system_context`, `project_context`, `task_context`, `allowed_reads`, `allowed_writes`, and `evidence_refs`. This is expected and proportional to the configuration size.
- `GatewayBusinessPolicyConfig` holds `set[Path]`, `list[Path]`, `dict[str, Path]`, and `dict[str, list[Path]]` — several hundred `Path` objects total. These are rebuilt every call (see §1.1) but are short-lived and GC'd normally.

### 3.3 No circular references or closure traps

Callback lambdas in `build_context_package()` (e.g., `lambda context: _get_policy_registry().validate(context)`) capture `self` via module-level functions, not via closures over large objects. No retention chains detected.

---

## 4. Import Cost

**Verdict: PASS (with caveats)**

### 4.1 Module-level imports are standard library only

`memory_hook_gateway.py` imports: `argparse`, `json`, `os`, `re`, `shutil`, `subprocess`, `sys`, `datetime`, `pathlib`, `typing`. All are C-extension or builtin modules in CPython — fast to import.

### 4.2 Lazy public API via `__getattr__`

`workspace/tools/__init__.py` uses `__getattr__` to lazily import `build_context_package`, `build_context_package_simple`, `CoreConfig`, and `build_context_package_from_config`. This is good practice and avoids loading submodules until needed.

### 4.3 Adapter globals populated at import time

In `memory_hook_gateway.py` (~line 100-110), the adapter bootstrap code runs at module load:

```python
_mod = importlib.import_module(_mod_path, package="workspace.tools")
globals().update(_fn(REPO_ROOT, WORKSPACE_ROOT))
```

`_fn` is `build_workbot_runtime_profile()` which constructs **dozens of Path objects and collections** and injects them into the module's global namespace. This happens **once** on first import and is not repeated, so it's acceptable. However, it does mean `import workspace.tools.memory_hook_gateway` has a non-trivial startup cost (~50ms estimated on Apple Silicon).

### 4.4 Try/except import fallbacks

The try/except blocks for relative vs absolute imports (e.g., `from .memory_hook_core` → `from memory_hook_core`) add negligible overhead but make the import graph harder to reason about. Not a performance concern.

---

## 5. Scalability Limits

**Verdict: FAIL**

### 5.1 What breaks at 1,000 calls/second

| Component | Failure mode |
|---|---|
| `git_registration_probe()` (3 subprocesses/call) | **3,000 git processes/sec** — system would spend most time in fork/exec overhead. Process table exhaustion likely. |
| `_exclusive_hook_state_lock()` (fcntl advisory lock) | Contention on a single lock file. Serializes all state writes through one bottleneck. |
| `_get_gateway_business_policy()` (uncached) | ~35-field dataclass allocation per call → GC pressure. 1,000 allocations/sec is manageable, but wasteful. |
| `ArtifactSinkImpl.write()` (2 writes + 1 append) | **3,000 fsync-equivalent file operations/sec** — would saturate even NVMe IOPS if all to the same directory. |
| `fsync` in `_write_hook_state_unlocked()` | Each `record_hook_event()` forces a disk flush. At 1,000/sec this is a hard bottleneck. |
| `snapshot_path` collision loop in `ArtifactSinkImpl.write()` | Uses `while snapshot_path.exists(): suffix += 1` — at high write rates this becomes O(n) per call. |

### 5.2 Global state conflicts

- `_default_policy_registry`, `_default_route_policy`, `_default_write_policy` are module-level singletons initialized lazily. They are **not thread-safe** — two concurrent calls could create two instances. In practice, the hook runs in a single-threaded subprocess model, so this is low-risk.
- `RouteTargetPolicyImpl._routes["fact"]` uses `datetime.now().date().isoformat()` computed **once at `__init__`**. If the process lives past midnight, the "fact" route points to yesterday's log file silently.
- `WriteTargetPolicyImpl._targets["fact"]` has the same issue.

### 5.3 No rate limiting or backpressure

There is no mechanism to detect or throttle rapid-fire hook invocations. A burst of 100 prompt-submit events in 1 second would trigger 100 full validation chains with all the I/O described above.

### 5.4 No async / parallelization

All I/O is synchronous and sequential. `truth_basis_for_scope()` reads 5+ files one at a time. `validate_unique_legal_system_contract()` reads 7 files one at a time. These could be parallelized with `asyncio` or `concurrent.futures.ThreadPoolExecutor` for meaningful latency reduction.

---

## Summary

| Category | Verdict | Key Finding |
|---|---|---|
| Hot Path Efficiency | **FAIL** | Uncached business policy rebuild + 3 git subprocesses + 25+ file reads per call |
| I/O Patterns | **FAIL** | ~25-30 file reads + 3 git subprocesses + 3 writes per invocation; no caching; stale date in route targets |
| Memory Usage | **PASS** | No leaks; singletons are bounded; per-call allocations are short-lived and GC-friendly |
| Import Cost | **PASS** | Standard library only; lazy `__getattr__` API; adapter bootstrap is one-time cost |
| Scalability Limits | **FAIL** | Git subprocess explosion at scale; fcntl lock contention; fsync bottleneck; no rate limiting |

### Overall Verdict: **FAIL** (3 of 5 categories failed)

The system is designed for correctness and auditability over throughput. For its actual usage pattern (hook events a few times per minute during active sessions), the performance characteristics are acceptable. However, under sustained high frequency (>10 events/second), the git subprocess calls, uncached policy reconstruction, and synchronous fsync-heavy I/O would become bottlenecks.

### Recommended improvements (prioritized)

1. **Cache `_get_gateway_business_policy()`** with invalidation on env/config change. Single largest win for hot path.
2. **Memoize `git_registration_probe()`** results for the duration of a single hook event cycle, or skip it for non-"stop" events where registration commit is not relevant.
3. **Batch file reads** in `validate_unique_legal_system_contract()` and `truth_basis_for_scope()` using `concurrent.futures.ThreadPoolExecutor`.
4. **Add a lightweight rate limiter** in `main()` to detect and collapse rapid-fire events.
5. **Fix the stale date bug** in `RouteTargetPolicyImpl` and `WriteTargetPolicyImpl` — compute `datetime.now().date()` at call time, not at `__init__`.
