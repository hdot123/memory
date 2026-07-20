# Vulture whitelist - marks false positive unused code.
# These items appear unused to static analysis but are actually referenced
# via dynamic dispatch, protocols, TypedDict fields, or public API exports.

from memory_core.compat import check_compatibility, format_report
from memory_core.ownership import DOMAIN, RESOURCE, OwnershipKind
from memory_core.tools import __getattr__
from memory_core.tools._rule_errors import (
    GuardBlockError,
    OwnershipError,
    PolicyViolationError,
    RuleViolationError,
)
from memory_core.tools._rule_types import RuleEvaluator
from memory_core.tools.audit_project_layout import plan_main
from memory_core.tools.auto_capture import capture_candidates
from memory_core.tools.business_policy_checks import (
    LegalContractChecker,
    ScopeResolver,
)
from memory_core.tools.cmux_hook_state import reset_hook_state
from memory_core.tools.feature_flags import is_enabled, register_flag, reset_flags
from memory_core.tools.global_kb_init import is_global_kb_initialized
from memory_core.tools.hook_event import (
    from_claude_payload,
    parse_hook_event,
    to_context_package_input,
)
from memory_core.tools.hook_event_stats import _find_context_snapshots
from memory_core.tools.init_project_memory import generate_hooks_json
from memory_core.tools.log_utils import get_sanitized_logger
from memory_core.tools.memory_hook_adapters.default_runtime_profile import (
    build_default_runtime_profile,
)
from memory_core.tools.memory_hook_config import MemoryHookConfig
from memory_core.tools.memory_hook_gateway import (
    ARTIFACT_COMPACTION,
    CLAUDE_HOOK_STATE_FILE,
    GATEWAY_POLICY_CLASS,
    GLOBAL_KB_ENABLED,
    MEMORY_SYSTEM_PATH,
    _canonicalize_cmux_refs,
    _collect_changed_paths,
    _configured_invalid_memory_root,
    _require_env,
    _resolve_policy_conflict_via_registry,
    get_config,
    get_config_dict,
    resolve_route_target,
    write_artifacts,
)
from memory_core.tools.memory_hook_impls import (
    ClaudeDelegate,
    CodexDelegate,
    PathUtilsImpl,
)
from memory_core.tools.memory_hook_integrity_keys import key_info
from memory_core.tools.memory_hook_integrity_manifest import _hmac_sha256
from memory_core.tools.memory_hook_integrity_verify import quick_check
from memory_core.tools.memory_hook_interfaces import (
    conflict_status,
    enforcement_result,
    global_refs,
    project_ref,
    triggered_on_current_event,
)
from memory_core.tools.memory_hook_schema import is_lossless, is_v2
from memory_core.tools.observability import ErrorTracker, MetricsRegistry, TraceContext, MetricsTimer
from memory_core.tools.project_probe import git_branch
from memory_core.tools.prompt_validator import check_prompt_or_raise
from memory_core.tools.resilient_orchestrator import ResilientOrchestrator
from memory_core.tools.telemetry_bridge import safe_capture
from memory_core.tools.validate_project_memory import _parse_frontmatter

# Reference classes and functions to suppress vulture warnings
_ = (
    check_compatibility,
    format_report,
    DOMAIN,
    RESOURCE,
    OwnershipKind,
    __getattr__,
    GuardBlockError,
    OwnershipError,
    PolicyViolationError,
    RuleViolationError,
    RuleEvaluator,
    plan_main,
    capture_candidates,
    LegalContractChecker,
    ScopeResolver,
    reset_hook_state,
    is_enabled,
    register_flag,
    reset_flags,
    is_global_kb_initialized,
    from_claude_payload,
    parse_hook_event,
    to_context_package_input,
    _find_context_snapshots,
    generate_hooks_json,
    get_sanitized_logger,
    build_default_runtime_profile,
    MemoryHookConfig,
    ARTIFACT_COMPACTION,
    CLAUDE_HOOK_STATE_FILE,
    GATEWAY_POLICY_CLASS,
    GLOBAL_KB_ENABLED,
    MEMORY_SYSTEM_PATH,
    _canonicalize_cmux_refs,
    _collect_changed_paths,
    _configured_invalid_memory_root,
    _require_env,
    _resolve_policy_conflict_via_registry,
    get_config,
    get_config_dict,
    resolve_route_target,
    write_artifacts,
    ClaudeDelegate,
    CodexDelegate,
    PathUtilsImpl,
    key_info,
    _hmac_sha256,
    quick_check,
    conflict_status,
    enforcement_result,
    global_refs,
    project_ref,
    triggered_on_current_event,
    is_lossless,
    is_v2,
    ErrorTracker,
    MetricsRegistry,
    TraceContext,
    MetricsTimer,
    git_branch,
    check_prompt_or_raise,
    ResilientOrchestrator,
    safe_capture,
    _parse_frontmatter,
)

# Reference methods (vulture needs actual attribute access)
_ = (
    RuleEvaluator.evaluate,
    LegalContractChecker.evaluate,
    ScopeResolver.evaluate,
    MemoryHookConfig.uses_interfaces,
    MemoryHookConfig.to_gateway_kwargs,
    MemoryHookConfig.from_gateway_kwargs,
    CodexDelegate.host_unavailable,
    ClaudeDelegate.host_unavailable,
    CodexDelegate.get_policy,
    CodexDelegate.resolve_kb_file,
    CodexDelegate.route,
    MetricsRegistry.publish,
    ErrorTracker.recent,
    ResilientOrchestrator.dispatch_task,
    TraceContext.child_span,
    TraceContext.record_span,
    MetricsTimer.measure,
)
