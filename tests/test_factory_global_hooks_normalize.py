"""Tests for factory_global_hooks.py hooks.json normalization."""
from __future__ import annotations

import json
from pathlib import Path

from memory_core.tools.factory_global_hooks import (
    _normalize_hooks_json,
    merge_hooks_json,
    _load_hooks_json,
)


class TestNormalizeHooksJson:
    def test_unwrap_hooks_wrapper(self) -> None:
        raw = {
            "hooks": {
                "SessionEnd": [{"hooks": [{"type": "command", "command": "test"}]}],
                "PostToolUse": [{"hooks": [{"type": "command", "command": "test2"}]}],
            }
        }
        result = _normalize_hooks_json(raw)
        assert "hooks" not in result
        assert "SessionEnd" in result
        assert "PostToolUse" in result

    def test_no_wrapper_unchanged(self) -> None:
        raw = {
            "SessionEnd": [{"hooks": [{"type": "command", "command": "test"}]}],
        }
        result = _normalize_hooks_json(raw)
        assert "hooks" not in result
        assert "SessionEnd" in result

    def test_empty_dict(self) -> None:
        result = _normalize_hooks_json({})
        assert result == {}


class TestMergeHooksJsonNormalize:
    def test_merge_with_wrapped_existing(self) -> None:
        """Existing hooks.json has wrapper, desired does not — should merge cleanly."""
        existing = {"hooks": {"SessionEnd": [{"hooks": [{"type": "command", "command": "old"}]}]}}
        desired = {"hooks": {"SessionEnd": [{"hooks": [{"type": "command", "command": "new"}]}]}}
        result = merge_hooks_json(existing, desired)
        assert "hooks" not in result or len([k for k in result if k != "hooks"]) > 0
        assert "SessionEnd" in result

    def test_merge_no_wrapper_leak(self) -> None:
        """Merging should never produce a hooks wrapper key."""
        existing = {"SessionEnd": [{"hooks": [{"type": "command", "command": "old"}]}]}
        desired = {"hooks": {"PostToolUse": [{"hooks": [{"type": "command", "command": "new"}]}]}}
        result = merge_hooks_json(existing, desired)
        assert "hooks" not in result
        assert "SessionEnd" in result
        assert "PostToolUse" in result


class TestLoadHooksJsonNormalize:
    def test_load_unwraps_wrapper(self, tmp_path: Path) -> None:
        hooks_file = tmp_path / "hooks.json"
        hooks_file.write_text(json.dumps({
            "hooks": {
                "SessionEnd": [{"hooks": [{"type": "command", "command": "test"}]}]
            }
        }))
        warnings: list[str] = []
        result = _load_hooks_json(hooks_file, warnings)
        assert "hooks" not in result
        assert "SessionEnd" in result
        assert any("wrapper" in w for w in warnings)

    def test_load_no_wrapper(self, tmp_path: Path) -> None:
        hooks_file = tmp_path / "hooks.json"
        hooks_file.write_text(json.dumps({
            "SessionEnd": [{"hooks": [{"type": "command", "command": "test"}]}]
        }))
        warnings: list[str] = []
        result = _load_hooks_json(hooks_file, warnings)
        assert "SessionEnd" in result
        assert not any("wrapper" in w for w in warnings)
