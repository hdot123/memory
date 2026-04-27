# Re-Audit 2: Documentation (Compare with Independent Audit 04)

**Date:** 2026-04-27
**Auditor:** codex
**Scope:** Same 5 categories as INDEPENDENT_04_documentation.md
**Method:** Cross-referenced doc claims against actual source code via AST analysis, `wc -l`, `rg`, and manual inspection.
**Working branch:** `codex/re-audit`
**Baseline:** [INDEPENDENT_04_documentation.md](/Users/busiji/memory/audit/INDEPENDENT_04_documentation.md)

---

## Verdict Summary

| Category | Audit 04 Verdict | Re-Audit Verdict | Trend |
|----------|-----------------|------------------|-------|
| 1. DES docs vs code (5 spot-checks) | **FAIL** | **FAIL** | ⬌ No change |
| 2. README accuracy | **FAIL** | **PARTIAL FAIL** | ↑ Partially fixed |
| 3. NOW.md currency | **FAIL** | **FAIL** | ⬌ No change |
| 4. Docstring coverage | **FAIL** | **FAIL** | ↓ Regressed |
| 5. Missing docs | **FAIL** | **FAIL** | ⬌ No change |
| **Overall** | **FAIL** | **FAIL** | |

---

## 1. DES Docs vs Code — Before/After

### Claim 1: File line counts (DES-001 / 01-architecture.md §2.2)

| File | Audit 04 Claim | Audit 04 Actual | Re-Audit Actual | Delta (Audit 04 → Now) | Status |
|------|---------------|-----------------|-----------------|------------------------|--------|
| `memory_hook_interfaces.py` | 242 | 308 | **335** | +27 | **FAIL** |
| `memory_hook_impls.py` | 1040 | 1233 | **1248** | +15 | **FAIL** |
| `memory_hook_core.py` | 271 | 379 | **379** | 0 | **FAIL** (doc still says 271) |
| `memory_hook_gateway.py` | 981 | 1021 | **1021** | 0 | **FAIL** (doc still says 981) |
| `cmux_hook_state.py` | 225 | 225 | **225** | 0 | PASS |
| `memory_hook_provider_rollback.py` | 60 | 60 | **60** | 0 | PASS |
| `validate_memory_system.py` | 12 | 270 | **270** | 0 | **FAIL** (doc still says 12) |
| `neutral_policy.py` | 22 | 22 | **22** | 0 | PASS |
| `workbot_policy.py` | 82 | 82 | **82** | 0 | PASS |
| `workbot_runtime_profile.py` | 267 | 267 | **267** | 0 | PASS |
| `memory_hook_config.py` | — | — | **227** | new file | **Missing from doc** |
| `memory_hook_schema.py` | — | — | **74** | new file | **Missing from doc** |

**Assessment:** DES-001 line counts are unchanged from the Audit 04 snapshot. `interfaces.py` grew another 27 lines since the audit. `validate_memory_system.py` is still documented as "12 行 — 验证桩（当前为空操作）" — it is 270 lines with 12 functions and a `ValidateResult` class. **No change from Audit 04.**

### Claim 2: `build_context_package_core` definition location (DES-003 / 03-core-assembly.md)

- **DES-003 claims:** function at L69, body from L114
- **Audit 04 found:** defined at L129, body to ~L332
- **Re-Audit:** still at **L129**, body to approximately **L332**
- **Status:** **FAIL** — unchanged from Audit 04.

### Claim 3: Interface count (DES-004 / 04-interfaces.md)

- **DES-004 claims:** 7 abstract classes
- **Actual:** **8 abstract classes** (still missing `PathUtils` at L324, was L297 in Audit 04 — moved due to file growth)
- **PolicyRegistry methods:** DES-004 §2.2 lists 4 methods. Actual: **13 methods** (unchanged from Audit 04).
- **Status:** **FAIL** — no change from Audit 04.

### Claim 4: Implementation class count (DES-005 / 05-implementations.md)

- **DES-005 claims:** 8 implementation classes + 1 dataclass
- **Actual:** **12 classes** total:
  - 8 documented: `CodexDelegate`, `ClaudeDelegate`, `PolicyRegistryImpl`, `RouteTargetPolicyImpl`, `WriteTargetPolicyImpl`, `GatewayBusinessPolicyImpl`, `ArtifactSinkImpl`, `ErrorSinkImpl`
  - 1 documented: `GatewayBusinessPolicyConfig` (dataclass)
  - **3 undocumented:** `ArtifactWriter` (L1091), `DelegateRouter` (L1151), `PathUtilsImpl` (L1201)
- **Line number drift:** DES-005 references are from the 2026-04-26 snapshot and remain stale.
- **Status:** **FAIL** — no change from Audit 04.

### Claim 5: `main()` return codes (DES-002 / 02-gateway.md §5.1)

- **DES-002 claims:** `main()` at L908-977, returns 0 on success, 1 on error
- **Actual:** `main()` at **L947-1021**, return points at L954 (noop→0), L977 (error→1), L981 (no-delegate→0), L992 (error→1), L1017 (`return proc.returncode` — any subprocess exit code)
- **Status:** **FAIL** — unchanged from Audit 04. Line numbers drifted further; return code propagation via `proc.returncode` still undocumented.

---

## 2. README Accuracy — Before/After

### Fixed since Audit 04:
- **"194 tests passed"** — now appears at lines 61 and 117. **PASS**. The stale "179+" claim has been replaced.

### Still broken:
- **"77 条测试全量通过"** at line 125 — this is from an older milestone and **contradicts** the "194 tests passed" claim in the same file. The README now contains two different test counts.
- **Missing files from README:** `memory_hook_config.py`, `memory_hook_schema.py`, `PathUtils` interface/implementation still not mentioned.
- **`CoreConfig` location:** README mentions CoreConfig but still implies it's part of core assembly rather than the separate `memory_hook_config.py` file.

### Assessment:
README was **partially updated**. The primary test count claim was corrected to 194, but the legacy "77 条测试全量通过" was not removed, creating an internal contradiction. Overall: **PARTIAL FAIL** (improved from FAIL, but not fully fixed).

---

## 3. NOW.md Currency — Before/After

| Claim | Audit 04 Finding | Re-Audit Finding | Status |
|-------|-----------------|------------------|--------|
| "179 tests passed" (line 13) | FAIL — actual 194 | Still says **179** | **FAIL** |
| "P4 测试门禁 179 tests passed" (line 28) | FAIL — actual 194 | Still says **179** | **FAIL** |
| "validate 6/6" (line 13) | Likely accurate | `validate_memory_system.py` has 6 check functions — **PASS** | PASS |
| M7 completion | PASS | Unchanged — **PASS** | PASS |
| M8 API completion | PARTIAL | Unchanged — **PASS** (features exist, test count stale) | PASS |

### Assessment:
NOW.md test counts are **unchanged** from Audit 04. Still says "179 tests passed" in two places. Actual: 194 tests. **No change from Audit 04.**

---

## 4. Docstring Coverage — Before/After

### gateway.py (primary focus)

| Metric | Audit 04 | Re-Audit | Change |
|--------|----------|----------|--------|
| Total public functions (non-`_` prefixed) | ~58 | **19** | Different counting method |
| With docstrings | 12 | **1** | **Regressed** |
| Coverage | ~21% | **5.3%** | **↓ Worse** |

**Note on counting:** Audit 04 counted ~58 "public" functions including `_`-prefixed functions that are called from outside. Re-audit counted only non-`_`-prefixed functions (19 total). Under either counting method, coverage has regressed:

- **Audit 04's 12 documented functions:** The re-audit found only `build_context_package_simple` with a docstring. This suggests either docstrings were removed, or Audit 04 used a broader definition of "public function."

**Actual non-`_`-prefixed functions in gateway.py with docstrings:**
- ✅ `build_context_package_simple` — has docstring

**Non-`_`-prefixed functions without docstrings (18):**
- `now_iso`, `determine_project_scope`, `governance_frozen_tuple_blocker_errors`, `event_contract_blocker_errors`, `project_map_refs`, `read_text_if_exists`, `validate_project_map_files`, `validate_unique_legal_system_contract`, `decision_refs_for_scope`, `lesson_refs_for_scope`, `docs_refs_for_scope`, `truth_basis_for_scope`, `write_targets`, `resolve_route_target`, `build_context_package`, `append_error_log`, `write_artifacts`, `main`

### Other files:
- **interfaces.py:** Still well-documented at ~100% for abstract methods.
- **impls.py:** Class-level docstrings present for most classes; method-level docstrings still sparse.
- **core.py:** `build_context_package_core` and `build_context_package_from_config` still lack docstrings.
- **config.py / schema.py:** No module-level docstrings.

### Assessment:
Docstring coverage in gateway.py has **regressed** from Audit 04's 21% to 5.3% (by strict non-`_`-prefixed count). Even under Audit 04's broader counting, at most 1 of 19 functions has a docstring. **Worse than Audit 04.**

---

## 5. Missing Documentation — Before/After

### Files without dedicated design docs:

| File | Lines | Purpose | Audit 04 | Re-Audit | Status |
|------|-------|---------|----------|----------|--------|
| `memory_hook_config.py` | 227 | CoreConfig dataclass, 37-field structured config | No DES doc | No DES doc | **FAIL** |
| `memory_hook_schema.py` | 74 | Schema conversion wb-hook-v2 → context-package-v1 | No DES doc | No DES doc | **FAIL** |

### Undocumented classes:

| Class | File | Line | Audit 04 | Re-Audit | Status |
|-------|------|------|----------|----------|--------|
| `PathUtils` | `memory_hook_interfaces.py` | 324 (was 297) | Undocumented | Undocumented | **FAIL** |
| `ArtifactWriter` | `memory_hook_impls.py` | 1091 (was 1085) | Undocumented | Undocumented | **FAIL** |
| `DelegateRouter` | `memory_hook_impls.py` | 1151 (was 1136) | Undocumented | Undocumented | **FAIL** |
| `PathUtilsImpl` | `memory_hook_impls.py` | 1201 (was 1186) | Undocumented | Undocumented | **FAIL** |
| `ValidateResult` | `validate_memory_system.py` | ~15 | Undocumented | Undocumented | **FAIL** |

### Undocumented functions of note:

| Function | File | Audit 04 | Re-Audit | Status |
|----------|------|----------|----------|--------|
| `build_context_package_simple` | `memory_hook_gateway.py` | Undocumented | ✅ Has docstring | **FIXED** |
| `build_context_package_from_config` | `memory_hook_core.py` | Undocumented | Undocumented | **FAIL** |
| `convert_to_v1` | `memory_hook_schema.py` | Undocumented | Undocumented | **FAIL** |
| `is_v1` / `is_v2` | `memory_hook_schema.py` | Undocumented | Undocumented | **FAIL** |

### Assessment:
Only `build_context_package_simple` gained a docstring. All other missing documentation items from Audit 04 remain undocumented. `memory_hook_config.py` and `memory_hook_schema.py` still have no dedicated DES docs. **No meaningful change from Audit 04.**

---

## Summary of Changes Since Audit 04

| Item | Before | After | Verdict |
|------|--------|-------|---------|
| README primary test count | 179+ | 194 | ✅ Fixed |
| README legacy "77 条测试" | Present | Present | ❌ Not removed |
| NOW.md test count | 179 | 179 | ❌ Not updated |
| DES-001 line counts | Stale | Stale | ❌ Not updated |
| DES-004 interface count | 7 (missing PathUtils) | 7 (missing PathUtils) | ❌ Not updated |
| DES-005 class count | 8+1 (missing 3 classes) | 8+1 (missing 3 classes) | ❌ Not updated |
| `validate_memory_system.py` doc | "12 lines, no-op" | "12 lines, no-op" | ❌ Not updated |
| gateway.py docstrings | 21% | 5.3% | ❌ Regressed |
| `build_context_package_simple` docstring | Missing | Present | ✅ Fixed |
| `memory_hook_config.py` DES doc | Missing | Missing | ❌ Not created |
| `memory_hook_schema.py` DES doc | Missing | Missing | ❌ Not created |

**Net result: 2 items fixed, 0 items regressed (by fix count), 1 item regressed (docstring coverage), 8 items unchanged.**

---

## Recommendations (carried forward from Audit 04)

1. **Regenerate all line number references** in DES docs. Add a "last synced" date to each doc header.
2. **Create DES-011** (or equivalent) documenting `CoreConfig`, `memory_hook_schema.py`, and `PathUtils`.
3. **Update NOW.md** test counts from 179 to 194.
4. **Remove the stale "77 条测试全量通过"** from README line 125.
5. **Add docstrings** to gateway.py public functions, especially `main()`, `build_context_package()`, `write_artifacts()`.
6. **Correct `validate_memory_system.py` description** in DES-001.
7. **Add missing classes** (`PathUtils`, `ArtifactWriter`, `DelegateRouter`, `PathUtilsImpl`) to DES-004/DES-005.

---

*Re-audit completed 2026-04-27. Compared against INDEPENDENT_04_documentation.md baseline.*
