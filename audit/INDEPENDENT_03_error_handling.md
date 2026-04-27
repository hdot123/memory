# Independent Audit 3: Error Handling & Defensive Coding

**Date:** 2026-04-27
**Scope:** All Python files in `workspace/tools/` and `tests/`
**Auditor:** Codex (GPT-5)
**Rule:** Read-only audit — no code modified.

---

## 1. Exception Handling

**Verdict: FAIL**

### Findings

| # | Severity | File | Line(s) | Description |
|---|----------|------|---------|-------------|
| 1.1 | Medium | `memory_hook_impls.py` | ~1116-1117 | `ArtifactWriter.write()` catches `except Exception` and only logs to file. The error is never surfaced to the caller — if artifact writing fails (e.g. disk full, permission denied), the caller receives `None` and has no way to know. This is a **silent failure** on a critical write path. |
| 1.2 | Medium | `memory_hook_gateway.py` | ~817-834 | `MEMORY_HOOK_SHADOW_RUN` block catches `except Exception` in shadow provider execution. The result is stored in `system_context["shadow_run"]` but never logged or raised. If the shadow provider fails, it is silently recorded as `ok=False` without any external signal (stderr, error log, or return code change). |
| 1.3 | Low | `memory_hook_core.py` | ~197-200 | `get_policy_pack_fn` is wrapped in `try/except Exception` — good defensive practice. However, the error message uses `str(exc)` which for some exception types (e.g. `subprocess.CalledProcessError`) may be less informative than the exception's own attributes. |
| 1.4 | Low | `memory_hook_impls.py` | ~250-263 | `PolicyRegistryImpl._load_dynamic_policy_pack()` catches `OSError` and `json.JSONDecodeError` and returns silently. No warning is emitted. This is intentional graceful degradation, but a **debug-level log** would help diagnose corrupt policy pack files in production. |
| 1.5 | Low | `cmux_hook_state.py` | ~93-96 | `load_hook_state()` catches `OSError` and `json.JSONDecodeError` and returns `_base_payload()` with no signal. If the hook state file becomes corrupt, the system silently operates on stale/empty data. This is acceptable for a cache-like file but should be documented. |
| 1.6 | Info | `memory_hook_core.py` | ~187 | `policy_validate_fn` wrapped in `try/except Exception` with `# pragma: no cover`. The comment acknowledges this is defensive and untestable by design. Acceptable. |

### Strengths

- No bare `except:` clauses found anywhere in the codebase.
- `HookStateError` is a well-defined custom exception with descriptive messages.
- `load_hook_state_strict()` correctly uses `raise ... from exc` for exception chaining.
- `CodexDelegate.execute()` and `ClaudeDelegate.execute()` validate preconditions (`cmux` in PATH, env vars) and raise `RuntimeError` with actionable messages.
- `DelegateRouter.route()` and `DelegateRouter.noop()` raise `ValueError` for unknown hosts with the invalid value included.

---

## 2. Error Messages

**Verdict: FAIL**

### Findings

| # | Severity | File | Line(s) | Description |
|---|----------|------|---------|-------------|
| 2.1 | Medium | `memory_hook_impls.py` | ~72, 74, 130-134 | `RuntimeError("cmux not found in PATH")` and `RuntimeError("missing required env: CMUX_SURFACE_ID")` are clear but **do not include actionable guidance** (e.g., which PATH was searched, which env vars were checked). The message `require_env()` at line ~913 similarly just names the variable without context about where it should come from. |
| 2.2 | Medium | `memory_hook_impls.py` | ~327 | `resolve_conflict()` raises `ValueError(f"no values provided for conflict resolution: {policy_key}")` — clear, but the "fail-fast" conflict message at line ~338-339 includes raw `values!r` which may contain sensitive data in a real deployment. |
| 2.3 | Low | `memory_hook_gateway.py` | ~971-976 | The degraded status stderr message prints `missing_paths` and `validation_errors` joined by `, `. When many paths are missing, this produces a **wall of text** on stderr that is hard to parse programmatically. |
| 2.4 | Low | `memory_hook_core.py` | ~211 | `policy_errors.append(f"unsupported project_scope: {project_scope}")` — clear, but the fallback path (line 212) then constructs a default path silently. A caller inspecting `validation_errors` would see this, but a caller only checking `status` might miss it. |
| 2.5 | Low | `memory_hook_schema.py` | — | `convert_to_v1()` performs no validation on its input. If `package` is not a dict or is missing expected keys, the function silently produces an incomplete v1 package with no error. No error messages are possible because none are generated. |

### Strengths

- `CoreConfig.__post_init__()` error messages are excellent: they include the invalid value via `!r` formatting and name the exact field (e.g., `host must be 'codex' or 'claude', got 'bad-host'`).
- `HookStateError` messages consistently include the file path in context.
- `memory_hook_provider_rollback.py` returns structured JSON with `status`, `errors`, and `ok` booleans — very actionable.

---

## 3. Input Validation

**Verdict: FAIL**

### Findings

| # | Severity | File | Line(s) | Description |
|---|----------|------|---------|-------------|
| 3.1 | Medium | `memory_hook_config.py` | ~90-104 | `CoreConfig.__post_init__` validates only 4 of ~37 fields: `host`, `event`, `workspace_root`, `repo_root`. The remaining 33 fields (including all 13 callback fields, path collections, policy strings, and scope configs) receive **zero validation**. A `None` passed for `extract_excerpt_fn` or a non-callable for `now_iso_fn` would cause an `AttributeError` deep in the call stack rather than a clear validation error at construction time. |
| 3.2 | Medium | `memory_hook_schema.py` | ~30-64 | `convert_to_v1(package)` accepts any `dict[str, Any]` with no validation. If called with an empty dict or a dict missing required keys like `host` or `event`, it returns a structurally incomplete v1 package silently. The caller (e.g., `build_context_package_simple`) relies on upstream validation, but `convert_to_v1` itself has no guard rails. |
| 3.3 | Medium | `memory_hook_gateway.py` | ~311-318 | `read_payload()` silently returns `{}` on JSON decode errors. This is intentional but means **malformed input is indistinguishable from empty input**. A caller cannot tell whether the payload was genuinely empty or corrupt. |
| 3.4 | Low | `memory_hook_core.py` | ~129-168 | `build_context_package_core()` accepts 37 individual kwargs with no type enforcement beyond type hints. If a caller passes `event=None` or `payload="not a dict"`, the function proceeds until a downstream operation fails with a cryptic error. The `CoreConfig` wrapper partially addresses this but is optional. |
| 3.5 | Low | `memory_hook_impls.py` | ~1107 | `ArtifactWriter.write()` does not validate that `package` is a dict or contains `host`/`event` keys before writing. If `package` is malformed, the write succeeds but produces invalid artifacts. |
| 3.6 | Info | `memory_hook_gateway.py` | ~918-936 | `canonicalize_cmux_refs()` runs a `subprocess.run` with `check=False` and silently falls back to the original values on non-zero return code or JSON decode error. This is appropriate for a canonicalization helper, but the fallback is invisible to the caller. |

### Strengths

- `CoreConfig.__post_init__` is a solid pattern for validation-at-construction.
- `PolicyRegistryImpl.get_policy_pack()` validates scope against `allowed_scopes` and raises `ValueError` for unknown scopes.
- `RouteTargetPolicyImpl.resolve()` raises `ValueError` for unknown route kinds.
- `require_env()` provides a clear error for missing environment variables.

---

## 4. Graceful Degradation

**Verdict: PASS**

### Assessment

The codebase demonstrates a **strong pattern of graceful degradation** across all major failure modes:

| Scenario | Behavior | File | Verdict |
|----------|----------|------|---------|
| Missing hook state JSON | Returns `_base_payload()` | `cmux_hook_state.py:91-96` | Good |
| Corrupt hook state JSON | Returns `_base_payload()` | `cmux_hook_state.py:93-96` | Good |
| Missing policy pack file | Falls back to `DEFAULT_POLICIES` | `memory_hook_impls.py:256-258` | Good |
| Malformed policy pack JSON | Falls back to `DEFAULT_POLICIES` | `memory_hook_impls.py:259-263` | Good |
| External core builder unavailable | Falls back to legacy builder | `memory_hook_gateway.py:181-189` | Good |
| Policy pack resolution fails | Records error, continues with empty pack | `memory_hook_core.py:196-200` | Good |
| Policy validation callback raises | Catches exception, records error | `memory_hook_core.py:178-188` | Good |
| Write target policy fails | Falls back to hardcoded default dict | `memory_hook_gateway.py:687-708` | Good |
| Route target policy fails | Falls back to hardcoded route map | `memory_hook_gateway.py:711-733` | Good |
| Artifact sink fails | Falls back to direct file writes | `memory_hook_gateway.py:884-907` | Good |
| Error sink fails | Falls back to direct file append | `memory_hook_gateway.py:874-881` | Good |
| Unsupported project scope | Adds error, uses fallback path | `memory_hook_core.py:210-212` | Good |
| `cmux` binary missing | Delegate raises `RuntimeError` (caller handles) | `memory_hook_impls.py:71-74` | Acceptable |
| Missing NOW.md for excerpt | Returns `[]` | `memory_hook_gateway.py:379-380` | Good |

The system consistently degrades rather than crashes. The `status` field (`ok` / `degraded`) provides a clear signal about system health, and `validation_errors` aggregates all detected issues.

### Minor Concern

- The `ArtifactWriter.write()` silent failure (finding 1.1) means a degradation in artifact writing is **not reflected** in the package `status`. This is the only degradation path that is completely invisible to downstream consumers.

---

## 5. Logging & Diagnostics

**Verdict: FAIL**

### Findings

| # | Severity | File | Line(s) | Description |
|---|----------|------|---------|-------------|
| 5.1 | Medium | `memory_hook_impls.py` | ~1119-1133 | `ArtifactWriter._log_error()` writes to `error_log` using `strftime("%Y%m%dT%H%M%S")` — **no timezone information**. This makes it impossible to correlate errors across systems in different timezones. By contrast, `ErrorSinkImpl` uses `isoformat(timespec="seconds")` which includes timezone. |
| 5.2 | Medium | `cmux_hook_state.py` | ~93-96 | `load_hook_state()` silently returns a default payload when the file is corrupt or unreadable. **No diagnostic signal** is emitted — neither to stderr, error log, nor the returned payload. A caller has no way to distinguish "file not found" from "file corrupt" from "healthy empty state". |
| 5.3 | Medium | `memory_hook_impls.py` | ~250-263 | `_load_dynamic_policy_pack()` silently discards all errors. If a policy pack file exists but is corrupt, the system uses stale defaults without any indication. In production, this could lead to subtle policy mismatches that are extremely difficult to trace. |
| 5.4 | Low | `memory_hook_gateway.py` | ~817-834 | Shadow run results are stored in `system_context["shadow_run"]` but **never written to the error log or stderr**. If a shadow run fails, the only way to discover this is to inspect the context package output. |
| 5.5 | Low | `memory_hook_core.py` | ~235-242 | Truth basis integrity checks (refs overlap detection) produce error strings like `"decision refs overlap with truth basis refs"` but these are only surfaced through `validation_errors`. No separate diagnostic event or log entry is created. |
| 5.6 | Low | `memory_hook_gateway.py` | ~604-649 | `git_registration_probe()` includes `stderr` in the returned dict but **never logs it** when the probe fails. The `probe_ok` boolean and `status` field provide some signal, but the actual git stderr output is lost unless the caller explicitly inspects the gate dict. |

### Strengths

- `ErrorSinkImpl.log()` produces well-structured log lines: `[timestamp] [component] [error] message | context={json}`. This is parseable and includes structured context.
- `main()` prints a clear degraded status message to stderr (line 971-976) with both missing paths and validation errors.
- `append_error_log()` has a fallback path (lines 874-881) that writes directly to file if the sink fails — this prevents error logging from being a single point of failure.
- The `validation_errors` list in the context package provides a structured aggregation of all detected issues.

---

## Overall Verdict: **FAIL**

### Scorecard

| Category | Verdict | Rationale |
|----------|---------|-----------|
| 1. Exception Handling | **FAIL** | Broad `except Exception` on critical write paths (`ArtifactWriter`); shadow run failures silently swallowed |
| 2. Error Messages | **FAIL** | Some messages lack actionable guidance; `read_payload()` conflates corrupt with empty input; `convert_to_v1()` generates no errors at all |
| 3. Input Validation | **FAIL** | `CoreConfig` validates only 4 of ~37 fields; `convert_to_v1()` has zero validation; callback fields are not checked for callable-ness |
| 4. Graceful Degradation | **PASS** | Excellent coverage — 14+ degradation paths all handled without crash; status field provides clear health signal |
| 5. Logging/Diagnostics | **FAIL** | Silent failures in `load_hook_state()` and `_load_dynamic_policy_pack()`; timezone inconsistency in error log timestamps; shadow run failures not logged |

### Priority Recommendations

1. **[P1]** Add explicit error signaling to `ArtifactWriter.write()` — either re-raise after logging, or return a status indicator so callers know when writes fail.
2. **[P1]** Add validation in `CoreConfig.__post_init__` for callback fields (`extract_excerpt_fn`, `now_iso_fn`, etc.) to catch `None` or non-callable values at construction time.
3. **[P2]** Emit a diagnostic warning in `load_hook_state()` and `_load_dynamic_policy_pack()` when a file is found but corrupt (not just missing).
4. **[P2]** Normalize timestamp format in `ArtifactWriter._log_error()` to match `ErrorSinkImpl` (use `isoformat()` with timezone).
5. **[P3]** Add input validation to `convert_to_v1()` — at minimum, check that the input is a non-empty dict.
6. **[P3]** Log shadow run failures to the error sink in addition to storing in `system_context`.
