# Independent Audit 09 — Git History & Release Hygiene

**Date:** 2026-04-27
**Auditor:** codex/independent-audit
**Scope:** Commit quality, branch hygiene, tag correctness, merge commit descriptions, CI/CD readiness

---

## 1. Commit Quality

**Verdict: PASS (minor notes)**

### Findings

- **Conventional commit format used consistently** — non-merge commits follow `type(scope): description` or `type: description` patterns:
  - `feat(core):`, `feat(gateway):`, `feat(policy):`, `feat(api):`, `feat(config):`, `feat(schema):`, `feat(package):`
  - `fix:`, `refactor(gateway):`, `refactor(core):`, `test:`, `docs:`, `chore:`, `audit:`, `validation:`
- **Messages are descriptive** — most commits explain *what* and *why*, not just *what changed*.
- **Chinese acceptance commits** (e.g., `验收通过：...`) include detailed bullet-point summaries of all sub-agent work bundled into the merge — this is good practice for audit trail.

### Minor Notes

- `ef2c89d merge: Noether version bump from parallel branch` — terse; does not state what changed or why the merge was needed. Same pattern for `7509965 merge: Turing test commit from parallel branch` and `a28daff merge: Aristotle CoreConfig commit from parallel branch`. These are acceptable for small parallel merges but lack context for future reviewers.

---

## 2. Branch Hygiene

**Verdict: FAIL**

### Findings

- **Local branches:** clean — only `main` and `codex/independent-audit` (current working branch).
- **Remote branches with stale status:**
  - `origin/codex/acceptance-audit` — fully merged into `origin/main`
  - `origin/codex/memory-modularization-batch` — fully merged into `origin/main`
- Both are merged and should be pruned from the remote. Per repo policy (AGENTS.md §7), branch-2 branches must be deleted or retired immediately after merging to branch-1.

### Recommended Cleanup

```bash
git push origin --delete codex/acceptance-audit
git push origin --delete codex/memory-modularization-batch
git remote prune origin
```

---

## 3. Tag Correctness

**Verdict: PASS (minor notes)**

### Findings

| Tag | Type | Points To | Notes |
|-----|------|-----------|-------|
| `v0.1.0` | Lightweight | `4e5f340` (M7 remediation baseline) | Correct content, but lightweight — no tagger signature |
| `v0.2.0` | Annotated | `3904d8d` (M8 API completion merge) | Properly annotated with tagger info and message |

- `v0.2.0` is an annotated tag with message `memory-core v0.2.0 — M8 API completion` — this is correct practice.
- `v0.1.0` is a lightweight tag (no `tag v0.1.0` header in `git show` output). Lightweight tags lack tagger metadata and should be converted to annotated tags for release hygiene.

### Minor Notes

- `v0.1.0` should ideally be an annotated tag. If the remote has not been force-pushed recently, it can be recreated:
  ```bash
  git tag -d v0.1.0
  git tag -a v0.1.0 4e5f340 -m "memory-core v0.1.0 — M7 independent repo remediation baseline"
  ```

---

## 4. Merge Commit Descriptions

**Verdict: PASS (minor notes)**

### Findings

- **Major merges are well-described** — acceptance merges like `3904d8d`, `5cf5a6c`, `db5068d` include comprehensive summaries with bullet points listing all sub-agent work, test results, and validation outcomes.
- **Parallel branch merges are terse** — three merges reference agent names (Noether, Turing, Aristotle) without stating what was merged or why:
  - `ef2c89d merge: Noether version bump from parallel branch`
  - `7509965 merge: Turing test commit from parallel branch`
  - `a28daff merge: Aristotle CoreConfig commit from parallel branch`

### Recommendation

For parallel agent merges, include at minimum:
- What the parallel branch changed (1 line)
- Why the merge was needed (1 line)

Example: `merge: Noether — bumped pyproject version to 0.2.0, added CoreConfig validation check`

---

## 5. CI/CD Readiness

**Verdict: FAIL**

### Critical Bug: Version Computation Logic

The workflow [`.github/workflows/release-and-dispatch.yml`](/Users/busiji/memory/.github/workflows/release-and-dispatch.yml:42) hardcodes the `v0.1.*` pattern:

```bash
last=$(git tag --list 'v0.1.*' --sort=-v:refname | head -n 1)
if [ -z "$last" ]; then
  next="v0.1.0"
else
  patch="${last##*.}"
  next="v0.1.$((patch + 1))"
fi
```

**Impact:** The last `v0.1.*` tag is `v0.1.0`. On the next CI run, this would compute `next="v0.1.1"`. But the project is already at `v0.2.0` — creating `v0.1.1` would produce a semantically earlier version than an existing release. This is a release ordering violation.

The workflow does **not** read the version from [`pyproject.toml`](/Users/busiji/memory/pyproject.toml:7) (currently `version = "0.2.0"`), so there is no cross-check between the package version and the CI-computed tag.

### Other CI Observations

| Check | Status | Notes |
|-------|--------|-------|
| Python version match | OK | Workflow uses 3.11, pyproject requires >=3.10 |
| Test execution | OK | `pytest -q tests` matches repo test structure |
| Checkout depth | OK | `fetch-depth: 0` needed for tag operations |
| Release action version | OK | `softprops/action-gh-release@v2` is current |
| Dispatch fallback | OK | Warns when `DISPATCH_TOKEN` is missing |

### Required Fix

Replace the hardcoded `v0.1.*` logic with one of:

1. **Read from pyproject.toml:**
   ```bash
   current=$(grep '^version' pyproject.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
   # bump accordingly
   ```

2. **Or compute from all version tags:**
   ```bash
   last=$(git tag --list 'v*' --sort=-v:refname | head -n 1)
   ```

---

## Overall Verdict

**FAIL** — The CI/CD version computation bug (category 5) and stale remote branches (category 2) are concrete issues that require action before the next release cycle.

| Category | Verdict | Severity |
|----------|---------|----------|
| Commit quality | PASS | — |
| Branch hygiene | FAIL | Medium — stale branches clutter remote |
| Tag correctness | PASS | Low — v0.1.0 is lightweight, not annotated |
| Merge commit descriptions | PASS | Low — 3 parallel merges lack detail |
| CI/CD readiness | FAIL | **High** — next release would produce wrong version tag |

### Priority Actions

1. **[HIGH]** Fix the version computation logic in `.github/workflows/release-and-dispatch.yml` to not hardcode `v0.1.*`.
2. **[MEDIUM]** Prune stale remote branches: `codex/acceptance-audit`, `codex/memory-modularization-batch`.
3. **[LOW]** Convert `v0.1.0` to an annotated tag.
4. **[LOW]** Add brief context lines to parallel agent merge commits going forward.
