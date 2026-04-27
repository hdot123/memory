# Independent Audit 4: Documentation Accuracy

**Date:** 2026-04-27
**Auditor:** codex
**Scope:** All design docs (DES-001 through DES-010), README.md, workspace/NOW.md, workspace/INDEX.md
**Method:** Cross-referenced doc claims against actual source code via AST analysis, `wc -l`, `rg`, and manual inspection.
**Working branch:** `codex/independent-audit`

---

## Verdict Summary

| Category | Verdict | Severity |
|----------|---------|----------|
| 1. DES docs vs code (5 spot-checks) | **FAIL** | High |
| 2. README accuracy | **FAIL** | Medium |
| 3. NOW.md currency | **FAIL** | Medium |
| 4. Docstring coverage | **FAIL** | Low |
| 5. Missing docs | **FAIL** | High |
| **Overall** | **FAIL** | |

---

## 1. DES Docs vs Code — Spot-Check Results

Five specific claims from the design documents were verified against actual source code. All five failed.

### Claim 1: File line counts (DES-001 §2.2, DES-002 header)

DES-001 claims specific line counts for every Python file. Actual counts:

| File | DES-001 Claim | Actual (`wc -l`) | Delta | Status |
|------|--------------|-------------------|-------|--------|
| `memory_hook_interfaces.py` | 242 | **308** | +66 | **FAIL** |
| `memory_hook_impls.py` | 1040 | **1233** | +193 | **FAIL** |
| `memory_hook_core.py` | 271 | **379** | +108 | **FAIL** |
| `memory_hook_gateway.py` | 981 | **1021** | +40 | **FAIL** |
| `cmux_hook_state.py` | 225 | 225 | 0 | PASS |
| `memory_hook_provider_rollback.py` | 60 | 60 | 0 | PASS |
| `validate_memory_system.py` | **12** | **270** | +258 | **FAIL** |
| `neutral_policy.py` | 22 | 22 | 0 | PASS |
| `workbot_policy.py` | 82 | 82 | 0 | PASS |
| `workbot_runtime_profile.py` | 267 | 267 | 0 | PASS |

**Critical finding:** `validate_memory_system.py` is documented as "12 lines — 验证桩（当前为空操作）" (validation stub, currently no-op). It is actually 270 lines with a `ValidateResult` class and 12 functions including `check_gateway_import`, `check_core_builder_resolve`, `check_context_package`, `check_core_config_path`, `check_v1_schema`, and `check_package_imports`. This is a complete mischaracterization.

### Claim 2: `build_context_package_core` definition location (DES-001 §3.3, DES-003 §1)

- **DES-001 claims:** `build_context_package_core()` at L69-L271
- **DES-003 claims:** function definition at L69-108, body from L114 to L271
- **Actual:** function defined at **L129**, body runs to approximately **L332**. The function still has 37 keyword-only args (confirmed), but the line references are off by ~60 lines.
- **Status:** **FAIL** — line numbers incorrect.

### Claim 3: Interface count (DES-004 §1)

- **DES-004 claims:** 7 abstract classes (HostDelegate, PolicyRegistry, RouteTargetPolicy, WriteTargetPolicy, GatewayBusinessPolicy, ArtifactSink, ErrorSink)
- **Actual:** **8 abstract classes** — the docs miss the `PathUtils` interface (L297 in `memory_hook_interfaces.py`), which defines `extract_excerpt` and `write_targets` abstract methods.
- **PolicyRegistry methods:** DES-004 §2.2 lists 4 methods (`get_policy`, `validate`, `get_policy_pack`, `resolve_conflict`). Actual: **13 methods** — 9 additional methods were added (`validate_project_map`, `validate_unique_legal_system_contract`, `governance_frozen_tuple_errors`, `event_contract_blocker_errors`, `git_registration_probe`, `truth_basis_for_scope`, `decision_refs_for_scope`, `lesson_refs_for_scope`, `docs_refs_for_scope`).
- **Status:** **FAIL** — missing interface and method count wrong.

### Claim 4: Implementation class count (DES-005 §1)

- **DES-005 claims:** 8 implementation classes + 1 dataclass
- **Actual:** **12 classes** in `memory_hook_impls.py`:
  - 8 documented: `CodexDelegate`, `ClaudeDelegate`, `PolicyRegistryImpl`, `RouteTargetPolicyImpl`, `WriteTargetPolicyImpl`, `GatewayBusinessPolicyImpl`, `ArtifactSinkImpl`, `ErrorSinkImpl`
  - 1 documented: `GatewayBusinessPolicyConfig` (dataclass)
  - **4 undocumented:** `ArtifactWriter` (L1085), `DelegateRouter` (L1136), `PathUtilsImpl` (L1186), and `GatewayBusinessPolicyConfig` moved from L425 to L464
- **Class line numbers shifted significantly:** e.g., `GatewayBusinessPolicyImpl` at L506 (doc says L448), `ArtifactSinkImpl` at L1022 (doc says L984)
- **Status:** **FAIL** — missing classes and wrong line numbers.

### Claim 5: `main()` return codes (DES-002 §5.1)

- **DES-002 claims:** `main()` returns 0 on success, 1 on degraded/error
- **Actual:** `main()` has return points at lines 954, 977, 981, 992, 1017 — returns `proc.returncode` at L1017, which can be any subprocess exit code, not just 0 or 1.
- **Status:** **PARTIAL FAIL** — basic 0/1 semantics exist but the actual delegate return code propagation is not documented.

---

## 2. README Accuracy

### Accurate claims:
- "CoreConfig dataclass: 37 parameter structured config object" — **PASS**. `CoreConfig` exists at `workspace/tools/memory_hook_config.py:18` as a `@dataclass(kw_only=True)` with 37+ fields grouped into 5 concern areas.
- "build_context_package_simple(host, event, payload): 3 parameter simplified entry" — **PASS**. Exists at `memory_hook_gateway.py:841`.
- "context-package-v1: new output format" — **PASS**. Schema conversion exists at `memory_hook_schema.py` with `convert_to_v1()`, `is_v1()`, `is_v2()` functions.
- "ArtifactWriter + DelegateRouter: gateway responsibility separation" — **PASS**. `ArtifactWriter` (L1085) and `DelegateRouter` (L1136) exist in `memory_hook_impls.py`.
- "pip package entry points: memory-validate, memory-rollback" — **PASS**. Defined in `pyproject.toml` as `[project.scripts]`.

### Inaccurate claims:
- "179+ tests passed" — **FAIL**. Actual: **194 tests passed**. Outdated by 15 tests.
- "77 条测试全量通过" (77 tests all pass) in the "当前状态" section — **FAIL**. This is from an older milestone and contradicts the 179+ claim in the same file.
- "Core 组装逻辑：`workspace/tools/memory_hook_core.py`" — **PARTIAL**. Does not mention `memory_hook_config.py` (CoreConfig) or `memory_hook_schema.py` (schema conversion), which are now part of the core assembly surface.

### Missing from README:
- `memory_hook_config.py` — the CoreConfig dataclass file
- `memory_hook_schema.py` — the v1/v2 schema conversion module
- `PathUtils` interface and `PathUtilsImpl` implementation
- `build_context_package_from_config()` — config-based entry point at `memory_hook_core.py:334`

---

## 3. NOW.md Currency

### Accurate claims:
- M7 completion status — **PASS** (consistent with git history)
- M3 policy-pack adapter wiring — **PASS**
- "根级 workspace/ 已建立为新的总控工作区" — **PASS**

### Inaccurate claims:
- "179 tests passed" — **FAIL**. Actual: **194 tests passed**.
- "validate 6/6" — needs verification. `validate_memory_system.py` has 6 check functions (`check_gateway_import`, `check_core_builder_resolve`, `check_context_package`, `check_core_config_path`, `check_v1_schema`, `check_package_imports`), so this is likely accurate but should be re-run.
- "M8 API 完成" — **PARTIAL**. The M8 features listed in README exist, but the M8 section in README references things like "179+ tests" which are outdated. The NOW.md claim is technically correct about feature completion, but the test count is wrong.

### Assessment:
NOW.md was last updated 2026-04-27. It captures the general state correctly but carries stale test counts.

---

## 4. Docstring Coverage

### interfaces.py — **PASS**
All 8 classes have docstrings. All 37 abstract methods have docstrings. Coverage: 100%.

### gateway.py — **FAIL**
Of ~58 public (non-underscore-prefixed) functions:
- **12 have docstrings**: `resolve_route_target_via_policy`, `write_targets_via_policy`, `get_policy_pack_via_registry`, `resolve_policy_conflict_via_registry`, `write_artifacts_via_sink`, `append_error_log_via_sink`, `execute_delegate_via_facade`, `build_context_package_simple`
- **46 lack docstrings**: including critical entry points like `main()`, `build_context_package()`, `parse_args()`, `read_payload()`, `discover_cwd()`, `write_artifacts()`, `delegate_codex()`, `delegate_claude()`, `git_registration_probe()`, `truth_basis_for_scope()`, and many more.
- Coverage: ~21% for public functions.

### impls.py — Mixed
Class-level docstrings present for most implementation classes. Method-level docstrings are sparse — most concrete methods lack docstrings even though their abstract counterparts in interfaces.py have them.

### core.py — Mixed
`build_context_package_core` has no module-level or function-level docstring. `build_context_package_from_config` (L334) has no docstring. `registration_phase_from_policy_pack` and `evaluate_registration_commit_gate` also lack docstrings.

### Overall assessment:
Interface definitions are well-documented. Implementation code and gateway orchestration functions are under-documented. The gap between interface docstrings and implementation docstrings means a reader of the interface cannot rely on finding matching documentation in the implementation.

---

## 5. Missing Documentation

### Entire files with no corresponding design doc:

| File | Lines | Purpose | DES Doc? |
|------|-------|---------|----------|
| `memory_hook_config.py` | ~180 | CoreConfig dataclass, 37-field structured config | **No** |
| `memory_hook_schema.py` | 75 | Schema conversion wb-hook-v2 → context-package-v1 | **No** |

### Undocumented classes in existing files:

| Class | File | Line | Purpose |
|-------|------|------|---------|
| `PathUtils` | `memory_hook_interfaces.py` | 297 | Interface for path utility callbacks |
| `ArtifactWriter` | `memory_hook_impls.py` | 1085 | Artifact writing with snapshot/latest/event_log |
| `DelegateRouter` | `memory_hook_impls.py` | 1136 | Delegate routing with host dispatch |
| `PathUtilsImpl` | `memory_hook_impls.py` | 1186 | Implementation of PathUtils interface |
| `ValidateResult` | `validate_memory_system.py` | ~15 | Validation result accumulator |

### Undocumented functions of note:

| Function | File | Line | Purpose |
|----------|------|------|---------|
| `build_context_package_simple` | `memory_hook_gateway.py` | 841 | 3-parameter simplified entry point |
| `build_context_package_from_config` | `memory_hook_core.py` | 334 | Config-based entry using CoreConfig |
| `_resolve_callbacks` | `memory_hook_core.py` | 14 | Callback resolution helper |
| `convert_to_v1` | `memory_hook_schema.py` | ~10 | Convert v2 package to v1 schema |
| `is_v1` / `is_v2` | `memory_hook_schema.py` | ~65, ~70 | Schema version detection |

### Design docs that reference non-existent or renamed items:

- DES-005 §1 table references `GatewayBusinessPolicyImpl` at L448 — actual L506
- DES-005 §1 table references `ArtifactSinkImpl` at L984 — actual L1022
- DES-005 §1 table references `ErrorSinkImpl` at L1025 — actual L1063
- DES-005 §1 table references `RouteTargetPolicyImpl` at L392 — actual L401
- DES-005 §1 table references `WriteTargetPolicyImpl` at L412 — actual L430
- DES-005 §1 table references `GatewayBusinessPolicyConfig` at L425 — actual L464
- DES-005 §3.1 claims `GatewayBusinessPolicyConfig` has 36 fields — actual has 37 fields (includes `policy_pack_path: Path | None`)
- DES-001 §2.2 directory tree shows `memory_hook_adapters/` with 3 files — actual has 3 files plus a `docs/` subdirectory (correctly shown, but line counts wrong)

---

## Detailed Findings

### F1: `validate_memory_system.py` massively understated [High]
DES-001 describes this file as "12 lines — 验证桩（当前为空操作）" (12 lines, validation stub, currently no-op). It is 270 lines with a full validation suite including schema checks, import verification, config path checks, and package import validation. The doc's characterization is completely wrong — this is not a stub.

### F2: PolicyRegistry interface expanded 3x [High]
DES-004 documents 4 methods on `PolicyRegistry`. The actual interface has 13 methods. The 9 additional methods (`validate_project_map`, `validate_unique_legal_system_contract`, `governance_frozen_tuple_errors`, `event_contract_blocker_errors`, `git_registration_probe`, `truth_basis_for_scope`, `decision_refs_for_scope`, `lesson_refs_for_scope`, `docs_refs_for_scope`) effectively merged what was previously the `GatewayBusinessPolicy` surface area into `PolicyRegistry`. No design doc captures this interface evolution.

### F3: CoreConfig exists but not in documented location [Medium]
README correctly mentions CoreConfig but implies it's part of the core assembly. The actual implementation is in a separate file `memory_hook_config.py` (not `memory_hook_core.py`). The `build_context_package_core()` function still uses 37 keyword-only args; `CoreConfig` is a parallel structured alternative with a bridge method `from_gateway_kwargs()` for compatibility.

### F4: Schema v1/v2 dual support undocumented [Medium]
`memory_hook_schema.py` provides `convert_to_v1()`, `is_v1()`, `is_v2()` for dual schema support. The README mentions "context-package-v1" but no design doc describes the schema conversion mechanism, the v1 format, or the coexistence strategy.

### F5: GatewayBusinessPolicyImpl has 37 config fields, not 36 [Low]
DES-005 §3.1 claims 36 fields. Actual count is 37 (the `policy_pack_path: Path | None` field is missing from the doc).

### F6: Test count consistently stale [Low]
README says "179+ tests", NOW.md says "179 tests passed". Actual: 194 tests. Both documents are off by 15 tests (8% error).

### F7: Line numbers drift across all design docs [Medium]
All line number references in DES-001 through DES-010 are from the 2026-04-26 snapshot. Since then, files have grown by 40-258 lines. Line references in DES-002, DES-003, DES-005, DES-008 are all unreliable. For example:
- DES-002 claims `main()` at L908-977 — actual L947-1017
- DES-002 claims `build_context_package()` at L731-823 — actual L755-839
- DES-003 claims `build_context_package_core` body from L114 — actual L174

---

## Recommendations

1. **Regenerate all line number references** in DES docs from current code. Consider adding a "last synced" date to each doc header so readers can gauge staleness.

2. **Create DES-011 (CoreConfig & Schema)** documenting:
   - `CoreConfig` dataclass structure and the 5-group organization
   - `build_context_package_from_config()` entry point
   - `memory_hook_schema.py` v1/v2 conversion mechanism
   - `PathUtils` interface and `PathUtilsImpl`

3. **Update README and NOW.md** test counts to 194.

4. **Add docstrings** to gateway.py public functions, especially `main()`, `build_context_package()`, `build_context_package_simple()`, and `write_artifacts()`.

5. **Correct `validate_memory_system.py` description** in DES-001 from "12 lines, no-op stub" to its actual 270-line validation suite.

6. **Add `PathUtils` interface** to DES-004's interface table and add the 4 new implementation classes to DES-005's class table.

---

*Audit completed 2026-04-27. All findings verified against repository state at commit `7da9850`.*
