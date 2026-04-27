# R5: Bug Review — ops tooling + adapters

## Findings

### 1. `validate_memory_system.py:187-188` — degraded context packages are reported as healthy

- File: `/Users/busiji/memory/workspace/tools/validate_memory_system.py`
- Lines: 187-188
- Trigger condition: the gateway/core builder returns a structurally valid package with `status: "degraded"`. This happens for real broken states, including missing required canonical paths, project-map/contract/policy/truth-basis errors, governance/event blockers, or provider fallback errors. The core explicitly sets `status` to `"degraded"` when any of those failures exist (`memory_hook_core.py:250-257`), and the gateway can also degrade an otherwise-ok package when provider fallback occurs (`memory_hook_gateway.py:828-834`).
- Expected behavior: The health validator should fail when the package status is not healthy, because its contract is to validate that the memory hook system is healthy and operational.
- Actual behavior: `check_context_package()` reads `status = package.get("status")` but unconditionally records the check as passed after shape validation. A broken system can therefore pass the validator as long as the degraded package still contains the required top-level keys.

## Non-findings Checked

- `cmux_hook_state.py`: `_exclusive_hook_state_lock()` releases the `flock` in a `finally` block, and `_write_hook_state_unlocked()` writes a temp file in the target directory, fsyncs it, then replaces the target path. I did not find a concrete exception-path lock leak or cross-filesystem non-atomic replace.
- `memory_hook_provider_probe.py` vs `memory_hook_provider_rollback.py`: the probe preserves the same provider checks, result keys, exit-code behavior, and backwards-compatible `run_rollback_drill` alias. I did not find a migration bug.
- `workbot_runtime_profile.py`: the runtime profile provides the gateway-consumed adapter keys, including policy, routing, blocker scopes, evidence refs, Claude hook state file, scope inheritance, and artifact compaction keys. I did not find a concrete misspelled or missing key against current gateway usage.
- `workbot_policy.py`: adapter policy values override pack-level values in `inject_policy_pack_config()` as written. I did not find a concrete incorrect override path in the current gateway call chain.
- `neutral_policy.py`: `NeutralGatewayBusinessPolicy` only forwards `config` and `scope_config_path` to `GatewayBusinessPolicyImpl`; I did not find an accidental filtering behavior.
