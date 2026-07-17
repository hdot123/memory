"""Tests for feature_flags module."""
from __future__ import annotations

import os

import pytest

from memory_core.tools.feature_flags import (
    FeatureFlag,
    FeatureFlagRegistry,
    _global_registry,
    _parse_value,
    is_enabled,
    register_flag,
    list_flags,
)


class TestParseValue:
    """Test _parse_value function."""

    def test_parse_value_truthy(self) -> None:
        """Truthy values return True."""
        for val in ("1", "true", "TRUE", "True", "yes", "YES", "on", "ON"):
            assert _parse_value(val) is True, f"Expected True for {val!r}"

    def test_parse_valuefalsy(self) -> None:
        """Falsy values return False."""
        for val in ("0", "false", "FALSE", "False", "no", "NO", "off", "OFF"):
            assert _parse_value(val) is False, f"Expected False for {val!r}"

    def test_parse_value_none(self) -> None:
        """None or empty string returns None."""
        assert _parse_value(None) is None
        assert _parse_value("") is None

    def test_parse_value_unknown(self) -> None:
        """Unknown values return False (logged at debug)."""
        assert _parse_value("maybe") is False
        assert _parse_value("2") is False
        assert _parse_value("invalid") is False

    def test_parse_value_whitespace(self) -> None:
        """Whitespace around valid values is stripped."""
        assert _parse_value("  true  ") is True
        assert _parse_value(" false ") is False
        assert _parse_value("\ton\n") is True


class TestFeatureFlagRegistry:
    """Test FeatureFlagRegistry class."""

    @pytest.fixture(autouse=True)
    def reset_registry(self) -> None:
        """Reset global registry before each test."""
        _global_registry.clear()
        yield
        _global_registry.clear()

    def test_register_flag(self) -> None:
        """register_flag creates and returns a FeatureFlag."""
        flag = register_flag("NEW_UI", default=True, description="New UI experiment")
        assert flag.name == "NEW_UI"
        assert flag.default is True
        assert flag.description == "New UI experiment"
        assert flag in list_flags()

    def test_register_flag_case_insensitive(self) -> None:
        """register_flag normalizes name to uppercase."""
        flag = register_flag("new_ui", default=False)
        assert flag.name == "NEW_UI"

    def test_register_flag_invalid_name(self) -> None:
        """register_flag rejects invalid flag names."""
        with pytest.raises(ValueError, match="Invalid flag name"):
            register_flag("123_INVALID")
        with pytest.raises(ValueError, match="Invalid flag name"):
            register_flag("invalid-name")
        with pytest.raises(ValueError, match="Invalid flag name"):
            register_flag("")

    def test_list_flags_sorted(self) -> None:
        """list_flags returns flags sorted by name."""
        register_flag("ZEBRA")
        register_flag("APPLE")
        register_flag("MANGO")
        flags = list_flags()
        assert [f.name for f in flags] == ["APPLE", "MANGO", "ZEBRA"]

    def test_registry_get(self) -> None:
        """Registry.get returns the flag or None."""
        register_flag("TEST_FLAG", default=True)
        assert _global_registry.get("TEST_FLAG") is not None
        assert _global_registry.get("TEST_FLAG").default is True
        assert _global_registry.get("NONEXISTENT") is None

    def test_registry_len_and_contains(self) -> None:
        """Registry supports len and 'in' operator."""
        register_flag("A")
        register_flag("B")
        assert len(_global_registry) == 2
        assert "A" in _global_registry
        assert "a" in _global_registry  # case-insensitive
        assert "C" not in _global_registry

    def test_registry_clear(self) -> None:
        """Registry.clear removes all flags."""
        register_flag("X")
        assert len(_global_registry) == 1
        _global_registry.clear()
        assert len(_global_registry) == 0


class TestIsEnabled:
    """Test is_enabled function."""

    @pytest.fixture(autouse=True)
    def reset_registry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Reset global registry and env before each test."""
        import os as _os
        _global_registry.clear()
        # Remove any MEMORY_FEATURE_* vars that might leak
        for key in list(_os.environ.keys()):
            if key.startswith("MEMORY_FEATURE_"):
                monkeypatch.delenv(key, raising=False)
        yield
        _global_registry.clear()

    def test_is_enabled_env_truthy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Env var truthy value returns True."""
        monkeypatch.setenv("MEMORY_FEATURE_TEST", "1")
        assert is_enabled("TEST") is True

    def test_is_enabled_env_falsy(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Env var falsy value returns False."""
        monkeypatch.setenv("MEMORY_FEATURE_TEST", "0")
        assert is_enabled("TEST") is False

    def test_is_enabled_env_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Env var is case-insensitive."""
        monkeypatch.setenv("MEMORY_FEATURE_TEST", "TRUE")
        assert is_enabled("TEST") is True
        monkeypatch.setenv("MEMORY_FEATURE_TEST", "False")
        assert is_enabled("TEST") is False

    def test_is_enabled_registry_default(self) -> None:
        """When env var not set, uses registered default."""
        register_flag("MY_FLAG", default=True)
        assert is_enabled("MY_FLAG") is True

    def test_is_enabled_registry_default_false(self) -> None:
        """Registered default False works."""
        register_flag("MY_FLAG", default=False)
        assert is_enabled("MY_FLAG") is False

    def test_is_enabled_env_overrides_registry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Env var overrides registered default."""
        register_flag("MY_FLAG", default=True)
        monkeypatch.setenv("MEMORY_FEATURE_MY_FLAG", "0")
        assert is_enabled("MY_FLAG") is False

    def test_is_enabled_param_default(self) -> None:
        """When env var not set and not registered, uses param default."""
        assert is_enabled("UNREGISTERED", default=True) is True
        assert is_enabled("UNREGISTERED", default=False) is False

    def test_is_enabled_priority_order(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Priority: env > registry > param default > False."""
        # Unregistered, no env -> param default
        assert is_enabled("X", default=True) is True
        assert is_enabled("X") is False

        # Registered, no env -> registry default
        register_flag("X", default=False, description="test")
        assert is_enabled("X", default=True) is False  # registry wins over param

        # Env set -> env wins over all
        monkeypatch.setenv("MEMORY_FEATURE_X", "1")
        assert is_enabled("X", default=False) is True  # env wins over registry

    def test_is_enabled_name_case_insensitive(self) -> None:
        """is_enabled name is case-insensitive."""
        register_flag("my_flag", default=True)
        assert is_enabled("my_flag") is True
        assert is_enabled("MY_FLAG") is True
        assert is_enabled("My_Flag") is True

    def test_is_enabled_empty_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Empty env var is treated as unset."""
        monkeypatch.setenv("MEMORY_FEATURE_TEST", "")
        register_flag("TEST", default=True)
        assert is_enabled("TEST") is True  # falls through to registry default

    def test_is_enabled_unknown_env_value(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unknown env value is treated as falsy."""
        monkeypatch.setenv("MEMORY_FEATURE_TEST", "maybe")
        assert is_enabled("TEST") is False


class TestFeatureFlagDataclass:
    """Test FeatureFlag dataclass."""

    def test_featureflag_fields(self) -> None:
        """FeatureFlag has name, default, description fields."""
        flag = FeatureFlag(name="TEST", default=True, description="A test flag")
        assert flag.name == "TEST"
        assert flag.default is True
        assert flag.description == "A test flag"

    def test_featureflag_frozen(self) -> None:
        """FeatureFlag is immutable (frozen dataclass)."""
        flag = FeatureFlag(name="TEST")
        with pytest.raises(AttributeError):
            flag.name = "OTHER"  # type: ignore[misc]

    def test_featureflag_defaults(self) -> None:
        """FeatureFlag defaults: default=False, description=''."""
        flag = FeatureFlag(name="TEST")
        assert flag.default is False
        assert flag.description == ""
