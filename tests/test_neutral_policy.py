"""Tests for memory_hook_adapters.neutral_policy.NeutralGatewayBusinessPolicy."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from memory_core.tools.memory_hook_adapters.neutral_policy import (
    NeutralGatewayBusinessPolicy,
)


@pytest.fixture
def mock_config():
    """Build a minimal GatewayBusinessPolicyConfig mock."""
    cfg = MagicMock()
    cfg.repo_root = Path("/fake/repo")
    cfg.default_project_scope = "default"
    cfg.scope_match_hints = {}
    cfg.project_canonical = {}
    cfg.project_runtime_root = {}
    cfg.required_canonical = []
    cfg.global_canonical = []
    cfg.project_map_files = []
    return cfg


class TestNeutralGatewayBusinessPolicy:
    def test_inherits_from_gateway_impl(self, mock_config):
        from memory_core.tools.memory_hook_impls import GatewayBusinessPolicyImpl

        policy = NeutralGatewayBusinessPolicy(mock_config)
        assert isinstance(policy, GatewayBusinessPolicyImpl)

    def test_init_with_scope_config_path(self, mock_config, tmp_path):
        scope_path = tmp_path / "scope.json"
        policy = NeutralGatewayBusinessPolicy(
            mock_config, scope_config_path=scope_path
        )
        assert policy is not None

    def test_init_without_scope_config_path(self, mock_config):
        policy = NeutralGatewayBusinessPolicy(mock_config)
        assert policy is not None
