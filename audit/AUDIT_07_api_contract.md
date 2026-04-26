# Audit 07: API Contract Verification

## Test 1: v1 Schema (context-package-v1)
**Command:**
```python
from workspace.tools import build_context_package_simple
pkg = build_context_package_simple('codex', 'session-start', {})
```
**Assertions:**
- `schema_version == 'context-package-v1'` ✓
- `'paths' in pkg` ✓
- `'project' in pkg` ✓
- `'task' in pkg` ✓
- `'system_context' not in pkg` ✓

**Result: PASS**

## Test 2: v2 Backward Compatibility (wb-hook-v2)
**Command:**
```python
from memory_hook_gateway import build_context_package
pkg = build_context_package('codex', 'session-start', {})
```
**Assertions:**
- `schema_version == 'wb-hook-v2'` ✓
- `'system_context' in pkg` ✓
- `'project_context' in pkg` ✓

**Result: PASS**

## Test 3: 3-Parameter API
**Command:**
```python
p1 = build_context_package_simple('codex', 'test')
p2 = build_context_package_simple('codex', 'test', {'key': 'val'})
p3 = build_context_package_simple('claude', 'session-start')
```
**Assertions:**
- All three calls succeed (payload defaults to `{}` when omitted) ✓
- All return `status` in `('ok', 'degraded')` ✓

**Result: PASS**

## Verdict: PASS

All three API contract checks passed:
1. `build_context_package_simple` correctly returns `context-package-v1` schema with `paths`, `project`, `task` fields and no `system_context`.
2. `build_context_package` (internal v2) correctly returns `wb-hook-v2` schema with `system_context` and `project_context` fields intact.
3. The 3-parameter API (`host`, `event`, `payload=None`) works correctly with and without explicit payload, for both `codex` and `claude` hosts.

The schema conversion pipeline (`wb-hook-v2 → context-package-v1`) in `memory_hook_schema.py` is functioning as designed: field renaming (`project_context→project`, `task_context→task`), path nesting, and `system_context` stripping all verified.
