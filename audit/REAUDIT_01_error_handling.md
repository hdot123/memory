# Re-Audit 1: Error Handling (After Fixes)

**Date:** 2026-04-27
**Original Audit:** `audit/INDEPENDENT_03_error_handling.md`
**Scope:** Re-evaluate the SAME 5 categories against the CURRENT code in `workspace/tools/`
**Auditor:** Codex (GPT-5)
**Rule:** Read-only audit — no code modified.

---

## Executive Summary

| Category | Original Verdict | Re-Audit Verdict | Trend |
|----------|-----------------|------------------|-------|
| 1. Exception Handling | FAIL | **FAIL** | Improved (partial fix) |
| 2. Error Messages | FAIL | **FAIL** | No change |
| 3. Input Validation | FAIL | **FAIL** | Improved (partial fix) |
| 4. Graceful Degradation | PASS | **PASS** | No change (still good) |
| 5. Logging/Diagnostics | FAIL | **FAIL** | No change |

**Overall Verdict: FAIL** — same as original, though two categories show meaningful incremental improvement.

---

## 1. Exception Handling

**Verdict: FAIL** (was FAIL — partial improvement)

### Finding-by-Finding Comparison

#### 1.1 `ArtifactWriter.write()` swallows exceptions

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Medium | Medium |
| **File** | `memory_hook_impls.py` ~1116-1117 | `memory_hook_impls.py` 1114-1128 |
| **Status** | FAIL | **PARTIALLY FIXED** |

**Before:** `write()` caught `Exception`, logged to file, returned `None`. Caller had zero visibility into failures.

**After:** `write()` now returns `bool` (True/False) and exposes a `last_error` property (line 1130-1132). The mechanism for callers to detect failures **exists**.

**Remaining gap:** In `main()` at line 958, the return value is captured but **never checked**:
```python
artifact_paths = writer.write(args.host, args.event, package)
# artifact_paths used later only for logging context when delegate fails (line 1004)
# — NOT used to detect artifact write failures themselves.
```
The failure is still invisible at the system level. The fix is incomplete without a caller-side check.

#### 1.2 `MEMORY_HOOK_SHADOW_RUN` silently swallowed

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Medium | Medium |
| **File** | `memory_hook_gateway.py` ~817-834 | `memory_hook_gateway.py` 816-835 |
| **Status** | FAIL | **PARTIALLY FIXED** |

**Before:** Shadow run errors stored in `system_context["shadow_run"]` as `ok=False`, but never logged or raised.

**After:** Same behavior — the `system_context["shadow_run"]` dict now includes `"error": str(exc)` on failure (line 832). The error is **visible in the output package** but still not logged to stderr or the error log.

**Remaining gap:** Shadow run failures produce no external signal (no stderr, no error log entry). A caller must inspect the JSON output to discover them.

#### 1.3 `get_policy_pack_fn` defensive wrapper

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Low | Low |
| **File** | `memory_hook_core.py` ~197-200 | `memory_hook_core.py` 196-200 |
| **Status** | Info | **UNCHANGED** (acceptable) |

No change. Still wrapped in `try/except Exception` with `str(exc)`. This is acceptable defensive coding.

#### 1.4 `_load_dynamic_policy_pack()` silent discard

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Low | Low |
| **File** | `memory_hook_impls.py` ~250-263 | `memory_hook_impls.py` 254-268 |
| **Status** | FAIL | **UNCHANGED** |

Still catches `OSError` and `json.JSONDecodeError` and returns with no diagnostic. No warning emitted for corrupt policy pack files.

#### 1.5 `load_hook_state()` silent discard

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Low | Low |
| **File** | `cmux_hook_state.py` ~93-96 | `cmux_hook_state.py` 89-98 |
| **Status** | Info | **UNCHANGED** (acceptable) |

Same behavior — returns `_base_payload()` on corrupt/missing file. Acceptable for cache-like semantics, but no diagnostic signal.

#### 1.6 `policy_validate_fn` pragma wrapper

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Info | Info |
| **File** | `memory_hook_core.py` ~187 | `memory_hook_core.py` 178-188 |
| **Status** | Info | **UNCHANGED** (acceptable) |

No change. Still acceptable.

---

## 2. Error Messages

**Verdict: FAIL** (was FAIL — no change)

### Finding-by-Finding Comparison

#### 2.1 Error messages lack actionable guidance

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Medium | Medium |
| **File** | `memory_hook_impls.py` ~72, 74, 913 | `memory_hook_impls.py` 76-78, 133-138, 910-914 |
| **Status** | FAIL | **UNCHANGED** |

Error messages like `"cmux not found in PATH"` and `"missing required env: CMUX_SURFACE_ID"` still provide no guidance about which PATH was searched or where the env var should come from. No line in the codebase changed these messages.

#### 2.2 `resolve_conflict()` may expose sensitive data

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Medium | Medium |
| **File** | `memory_hook_impls.py` ~338-339 | `memory_hook_impls.py` 341-344 |
| **Status** | FAIL | **UNCHANGED** |

The fail-fast message still includes raw `values!r`:
```python
f"conflict on {policy_key} with values {values!r}: strategy={effective_strategy}"
```

#### 2.3 Degraded status stderr wall of text

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Low | Low |
| **File** | `memory_hook_gateway.py` ~971-976 | `memory_hook_gateway.py` 971-976 |
| **Status** | FAIL | **UNCHANGED** |

Still joins `missing_paths` and `validation_errors` with `, ` producing a wall of text when many items are present.

#### 2.4 Unsupported project_scope fallback

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Low | Low |
| **File** | `memory_hook_core.py` ~211-212 | `memory_hook_core.py` 209-212 |
| **Status** | FAIL | **UNCHANGED** |

Still appends error then constructs fallback path silently.

#### 2.5 `convert_to_v1()` no validation, no errors

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Low | Low |
| **File** | `memory_hook_schema.py` | `memory_hook_schema.py` 30-64 |
| **Status** | FAIL | **UNCHANGED** |

Zero validation. If `package` is not a dict or missing keys, the function silently produces incomplete output. No error messages are possible because none are generated.

---

## 3. Input Validation

**Verdict: FAIL** (was FAIL — partial improvement)

### Finding-by-Finding Comparison

#### 3.1 `CoreConfig.__post_init__` validates only 4 of ~37 fields

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Medium | Medium |
| **File** | `memory_hook_config.py` ~90-104 | `memory_hook_config.py` 90-135 |
| **Status** | FAIL (4/37 fields) | **IMPROVED** (~12/37 fields) |

**Before:** Validated `host`, `event`, `workspace_root`, `repo_root` — 4 fields.

**After:** Now validates approximately 12 fields across `__post_init__`:

| Field | Check | Line |
|-------|-------|------|
| `host` | Must be `'codex'` or `'claude'` | 91-94 |
| `event` | Non-empty string | 95-96 |
| `workspace_root` | Must be `Path` | 97-100 |
| `repo_root` | Must be `Path` | 101-104 |
| `payload` | Must be `dict` | 105-108 |
| `cwd` | Must be `Path` | 109-112 |
| `project_scope` | Non-empty string | 113-114 |
| `required_canonical` | Must be `list` | 115-118 |
| `project_map_refs` | Must be `list` | 119-122 |
| `now_iso_fn` | Must be callable | 123-127 |
| `write_targets_fn` | Must be callable | 123-127 |
| `extract_excerpt_fn` | Must be callable | 123-127 |
| `surface_id` | Must be `str` | 128-131 |
| `workspace_id` | Must be `str` | 132-135 |

**Remaining gaps (~25 fields still unvalidated):**
- 10 other callback fields: `validate_project_map_fn`, `validate_unique_legal_system_contract_fn`, `policy_validate_fn`, `get_policy_pack_fn`, `governance_frozen_tuple_errors_fn`, `event_contract_blocker_errors_fn`, `git_registration_probe_fn`, `truth_basis_for_scope_fn`, `decision_refs_for_scope_fn`, `lesson_refs_for_scope_fn`, `docs_refs_for_scope_fn`
- Path collections: `project_canonical`, `project_runtime_root`, `global_canonical`, `project_map_governance`, `event_log`, `hook_contract_path`
- Policy strings: `legality_source_policy`, `registration_commit_policy`, `registration_commit_phase`
- Optional collections: `governance_blocker_scopes`, `event_contract_blocker_scopes`, `core_evidence_refs`
- Interface objects: `policy_registry`, `path_utils`

**Assessment:** This is a **meaningful improvement**. The three most dangerous callback fields (`now_iso_fn`, `write_targets_fn`, `extract_excerpt_fn`) are now checked for callability at construction time. But ~25 of 37 fields still receive no runtime validation.

#### 3.2 `convert_to_v1()` zero validation

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Medium | Medium |
| **File** | `memory_hook_schema.py` ~30-64 | `memory_hook_schema.py` 30-64 |
| **Status** | FAIL | **UNCHANGED** |

Still accepts any `dict[str, Any]` with no validation. Unchanged.

#### 3.3 `read_payload()` conflates corrupt with empty

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Medium | Medium |
| **File** | `memory_hook_gateway.py` ~311-318 | `memory_hook_gateway.py` 311-318 |
| **Status** | FAIL | **UNCHANGED** |

Still silently returns `{}` on JSON decode errors. Malformed input is indistinguishable from genuinely empty input.

#### 3.4 `build_context_package_core()` 37 kwargs no type enforcement

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Low | Low |
| **File** | `memory_hook_core.py` ~129-168 | `memory_hook_core.py` 129-168 |
| **Status** | FAIL | **PARTIALLY MITIGATED** |

The function signature is unchanged, but `CoreConfig.__post_init__` now provides partial mitigation through its expanded validation (see 3.1 above). The `build_context_package_from_config()` path (line 334-379) benefits from this.

#### 3.5 `ArtifactWriter.write()` no package validation

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Low | Low |
| **File** | `memory_hook_impls.py` ~1107 | `memory_hook_impls.py` 1114-1128 |
| **Status** | FAIL | **UNCHANGED** |

Still does not validate that `package` is a dict or contains expected keys before writing. Keys `host` and `event` are injected at lines 1121-1122, so malformed packages produce invalid artifacts.

#### 3.6 `canonicalize_cmux_refs()` invisible fallback

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Info | Info |
| **File** | `memory_hook_gateway.py` ~918-936 | `memory_hook_gateway.py` 917-936 |
| **Status** | Info | **UNCHANGED** (acceptable) |

Still falls back silently on non-zero return code or JSON decode error. Appropriate for a canonicalization helper.

---

## 4. Graceful Degradation

**Verdict: PASS** (was PASS — no change, still strong)

### Assessment

The graceful degradation patterns remain **unchanged and solid**. All 14+ degradation paths from the original audit are still present and functional:

| Scenario | Behavior | File | Verdict |
|----------|----------|------|---------|
| Missing hook state JSON | Returns `_base_payload()` | `cmux_hook_state.py:89-92` | Good |
| Corrupt hook state JSON | Returns `_base_payload()` | `cmux_hook_state.py:93-96` | Good |
| Missing policy pack file | Falls back to `DEFAULT_POLICIES` | `memory_hook_impls.py:261-262` | Good |
| Malformed policy pack JSON | Falls back to `DEFAULT_POLICIES` | `memory_hook_impls.py:263-268` | Good |
| External core builder unavailable | Falls back to legacy builder | `memory_hook_gateway.py:181-189` | Good |
| Policy pack resolution fails | Records error, continues with empty pack | `memory_hook_core.py:196-200` | Good |
| Policy validation callback raises | Catches exception, records error | `memory_hook_core.py:178-188` | Good |
| Write target policy fails | Falls back to hardcoded default dict | `memory_hook_gateway.py:686-708` | Good |
| Route target policy fails | Falls back to hardcoded route map | `memory_hook_gateway.py:711-733` | Good |
| Artifact sink fails | Falls back to direct file writes | `memory_hook_gateway.py:884-907` | Good |
| Error sink fails | Falls back to direct file append | `memory_hook_gateway.py:873-881` | Good |
| Unsupported project scope | Adds error, uses fallback path | `memory_hook_core.py:209-212` | Good |
| `cmux` binary missing | Delegate raises `RuntimeError` (caller handles) | `memory_hook_impls.py:75-78` | Acceptable |
| Missing NOW.md for excerpt | Returns `[]` | `memory_hook_gateway.py:379-380` | Good |

**No regressions detected.** The degradation layer is one of the strongest aspects of this codebase.

---

## 5. Logging & Diagnostics

**Verdict: FAIL** (was FAIL — no change)

### Finding-by-Finding Comparison

#### 5.1 `ArtifactWriter._log_error()` timezone inconsistency

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Medium | Medium |
| **File** | `memory_hook_impls.py` ~1119-1133 | `memory_hook_impls.py` 1134-1148 |
| **Status** | FAIL | **UNCHANGED** |

Still uses `strftime("%Y%m%dT%H%M%S")` with no timezone information (line 1143). By contrast, `ErrorSinkImpl` uses `isoformat(timespec="seconds")` which includes timezone (line 1078). Impossible to correlate errors across systems in different timezones.

#### 5.2 `load_hook_state()` no diagnostic signal

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Medium | Medium |
| **File** | `cmux_hook_state.py` ~93-96 | `cmux_hook_state.py` 89-98 |
| **Status** | FAIL | **UNCHANGED** |

No diagnostic signal emitted on corrupt/unreadable file. Caller cannot distinguish "file not found" from "file corrupt" from "healthy empty state".

#### 5.3 `_load_dynamic_policy_pack()` silent discard

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Medium | Medium |
| **File** | `memory_hook_impls.py` ~250-263 | `memory_hook_impls.py` 254-268 |
| **Status** | FAIL | **UNCHANGED** |

Still silently discards all errors. Corrupt policy pack files produce no indication.

#### 5.4 Shadow run failures not logged

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Low | Low |
| **File** | `memory_hook_gateway.py` ~817-834 | `memory_hook_gateway.py` 816-835 |
| **Status** | FAIL | **UNCHANGED** |

Shadow run results stored in `system_context["shadow_run"]` but never written to error log or stderr. The only way to discover a shadow run failure is to inspect the JSON output package.

#### 5.5 Truth basis integrity checks only in `validation_errors`

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Low | Low |
| **File** | `memory_hook_core.py` ~235-242 | `memory_hook_core.py` 234-242 |
| **Status** | FAIL | **UNCHANGED** |

No separate diagnostic event or log entry created.

#### 5.6 `git_registration_probe()` stderr never logged

| | Original Audit | Re-Audit |
|--|---------------|----------|
| **Severity** | Low | Low |
| **File** | `memory_hook_gateway.py` ~604-649 | `memory_hook_gateway.py` 604-649 |
| **Status** | FAIL | **UNCHANGED** |

Still includes `stderr` in returned dict but never logs it when probe fails.

---

## Scorecard: Before vs After

| Category | Original | Re-Audit | Change |
|----------|----------|----------|--------|
| 1. Exception Handling | FAIL | FAIL | Partial improvement (bool return + last_error, but unused) |
| 2. Error Messages | FAIL | FAIL | No change |
| 3. Input Validation | FAIL | FAIL | Partial improvement (4 → ~12 fields validated) |
| 4. Graceful Degradation | PASS | PASS | No change (still strong) |
| 5. Logging/Diagnostics | FAIL | FAIL | No change |
| **Overall** | **FAIL** | **FAIL** | **Incremental progress, not resolved** |

---

## Original Recommendations — Status Check

| # | Priority | Recommendation | Status |
|---|----------|---------------|--------|
| 1 | P1 | Add explicit error signaling to `ArtifactWriter.write()` | **PARTIAL** — returns `bool` + `last_error`, but `main()` never checks the return value |
| 2 | P1 | Add validation in `CoreConfig.__post_init__` for callback fields | **PARTIAL** — 3 callbacks validated (`now_iso_fn`, `write_targets_fn`, `extract_excerpt_fn`), but 10 other callbacks still unchecked |
| 3 | P2 | Emit diagnostic warning in `load_hook_state()` when file is corrupt | **NOT DONE** |
| 4 | P2 | Normalize timestamp in `_log_error()` to use `isoformat()` with timezone | **NOT DONE** |
| 5 | P3 | Add input validation to `convert_to_v1()` | **NOT DONE** |
| 6 | P3 | Log shadow run failures to error sink | **NOT DONE** |

**Summary:** 2 of 6 recommendations have partial implementation. 0 of 6 are fully resolved. 4 of 6 are untouched.

---

## New Findings (Not in Original Audit)

### N.1 `main()` ignores `ArtifactWriter.write()` return value [Medium]

**File:** `memory_hook_gateway.py` 958
**Description:** The code improvement to `ArtifactWriter.write()` (returns `bool`, exposes `last_error`) is wasted because `main()` captures the return value but never inspects it:
```python
artifact_paths = writer.write(args.host, args.event, package)
```
If artifact writing fails (disk full, permission denied), `main()` proceeds to delegate execution and may return exit code 0, giving a false impression of success. This is the single biggest gap preventing finding 1.1 from being truly fixed.

### N.2 `convert_to_v1()` will crash on non-dict input [Low]

**File:** `memory_hook_schema.py` 45-47
**Description:** If `package` is not a dict (e.g., `None`, a list, or a string), the `key in package` checks at lines 46, 52, 56, 61 will raise `TypeError` rather than produce a meaningful error. No try/except guards exist.

---

## Conclusion

The codebase has seen **incremental improvements** in exception handling (ArtifactWriter return value) and input validation (CoreConfig field coverage expanded 3×), but the **structural issues** that caused the original FAIL verdict remain:

- Silent failures on critical write paths are still invisible at the system level
- Error messages still lack actionable guidance
- ~25 of 37 config fields still lack runtime validation
- Logging diagnostics still have timezone inconsistency and silent error paths
- 4 of 6 original P2/P3 recommendations are completely untouched

**The codebase is better than it was, but not yet good enough to pass an error-handling audit.**
