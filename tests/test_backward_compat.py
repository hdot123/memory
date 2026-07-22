"""VAL-COMPAT-001 & VAL-COMPAT-002: 向后兼容性测试

验证 0.7 项目(无 [global_kb] 段)仍能正常工作:
- memory-validate 版本检查通过,不强制升级
- 路由正常工作(只是没有全局 fallback)
"""
from pathlib import Path

from memory_core.tools.adapter_toml_schema import (
    AdapterConfig,
    load_adapter_toml,
)
from memory_core.tools.validate_project_memory import (
    CheckResult,
    check_adapter_version,
    check_lock_version,
)


class TestVALCompat001ValidateWithoutGlobalKB:
    """VAL-COMPAT-001: 0.7 项目(无 [global_kb]) memory-validate 版本检查通过"""

    def test_check_lock_version_07_accepted(self, tmp_path: Path):
        """0.7.0 lock version 被接受,不强制升级"""
        memory_root = tmp_path / "memory" / "system"
        memory_root.mkdir(parents=True)

        # 0.7.0 lock file (canonical format with [memory] section)
        lock_content = '''[memory]
memory_version = "0.7.0"
'''
        (memory_root / "memory.lock").write_text(lock_content, encoding="utf-8")

        result = CheckResult()
        passed = check_lock_version(memory_root, result)

        assert passed, "0.7.0 lock version should be accepted"
        checks = [c for c in result.checks if c["name"] == "lock_version"]
        assert len(checks) == 1
        assert checks[0]["passed"] is True

    def test_check_adapter_version_07_without_global_kb_accepted(self, tmp_path: Path):
        """0.7 项目(无 [global_kb] 段) adapter version 被接受,不强制升级"""
        memory_root = tmp_path / "memory" / "system"
        memory_root.mkdir(parents=True)

        # 0.7 风格 adapter.toml (无 [global_kb] 段)
        adapter_content = """[core]
version = "0.7.0"
adapter = "default"

[policy]
legality_source_policy = "map-only"
registration_commit_policy = "same-commit"
registration_commit_phase = "post"

[routing]
project_name = "test-project"
project_scope = "test"
host = "factory"
canonical_files = []
"""
        (memory_root / "adapter.toml").write_text(adapter_content, encoding="utf-8")

        result = CheckResult()
        passed = check_adapter_version(memory_root, result)

        assert passed, "0.7.0 adapter without [global_kb] should be accepted"
        checks = [c for c in result.checks if c["name"] == "adapter_version"]
        assert len(checks) == 1
        assert checks[0]["passed"] is True

    def test_check_lock_version_06_also_accepted(self, tmp_path: Path):
        """0.6.0 lock version 也被接受(向后兼容)"""
        memory_root = tmp_path / "memory" / "system"
        memory_root.mkdir(parents=True)

        lock_content = '''[memory]
memory_version = "0.6.0"
'''
        (memory_root / "memory.lock").write_text(lock_content, encoding="utf-8")

        result = CheckResult()
        passed = check_lock_version(memory_root, result)
        assert passed

    def test_check_adapter_version_06_also_accepted(self, tmp_path: Path):
        """0.6.0 adapter 也被接受(向后兼容)"""
        memory_root = tmp_path / "memory" / "system"
        memory_root.mkdir(parents=True)

        adapter_content = """[core]
version = "0.6.0"
adapter = "default"

[routing]
project_name = "test"
project_scope = "test"
host = "factory"
canonical_files = []
"""
        (memory_root / "adapter.toml").write_text(adapter_content, encoding="utf-8")

        result = CheckResult()
        passed = check_adapter_version(memory_root, result)
        assert passed


class TestVALCompat002RoutingWithoutGlobalKB:
    """VAL-COMPAT-002: 无 [global_kb] 的项目路由正常工作"""

    def test_load_adapter_toml_without_global_kb_uses_defaults(self, tmp_path: Path):
        """adapter.toml 无 [global_kb] 段时,使用默认值不报错"""
        adapter_content = """[core]
version = "0.7.0"
adapter = "default"

[routing]
project_name = "test-project"
project_scope = "test"
host = "factory"
canonical_files = []
"""
        adapter_path = tmp_path / "adapter.toml"
        adapter_path.write_text(adapter_content, encoding="utf-8")

        # 应该成功加载,不报错
        config = load_adapter_toml(adapter_path)

        # global_kb 字段应该使用默认值
        assert config.global_kb_enabled is True
        assert "global-kb" in config.global_kb_root

    def test_load_adapter_toml_legacy_format_uses_defaults(self, tmp_path: Path):
        """Legacy [adapter] 格式也使用默认 global_kb 值"""
        adapter_content = """[adapter]
project_name = "legacy-project"
project_scope = "legacy"
host = "factory"
adapter_version = "0.6.0"
"""
        adapter_path = tmp_path / "adapter.toml"
        adapter_path.write_text(adapter_content, encoding="utf-8")

        config = load_adapter_toml(adapter_path)

        # 应该使用默认值
        assert config.global_kb_enabled is True
        assert "global-kb" in config.global_kb_root

    def test_load_adapter_toml_nonexistent_file_uses_defaults(self, tmp_path: Path):
        """不存在的 adapter.toml 使用默认值(包括 global_kb)"""
        adapter_path = tmp_path / "nonexistent.toml"
        config = load_adapter_toml(adapter_path)

        assert config.global_kb_enabled is True
        assert "global-kb" in config.global_kb_root


class TestVALCompat003NoRegression:
    """确保不破坏现有行为"""

    def test_08_project_version_checks_pass(self, tmp_path: Path):
        """0.8 项目(有 [global_kb])版本检查仍然正常"""
        memory_root = tmp_path / "memory" / "system"
        memory_root.mkdir(parents=True)

        # memory.lock (0.8.0 版本, canonical format with [memory] section)
        (memory_root / "memory.lock").write_text(
            '[memory]\nmemory_version = "0.8.0"\n', encoding="utf-8"
        )

        # adapter.toml (0.8 风格,有 [global_kb] 段)
        adapter_content = """[core]
version = "0.8.0"
adapter = "default"

[routing]
project_name = "test-project"
project_scope = "test"
host = "factory"
canonical_files = []

[global_kb]
enabled = true
root = "~/.memory/global-kb"
"""
        (memory_root / "adapter.toml").write_text(adapter_content, encoding="utf-8")

        result = CheckResult()
        lock_passed = check_lock_version(memory_root, result)
        adapter_passed = check_adapter_version(memory_root, result)

        assert lock_passed
        assert adapter_passed

    def test_adapter_config_global_kb_fields_present(self):
        """AdapterConfig 包含 global_kb 字段"""
        config = AdapterConfig(
            project_name="test",
            project_scope="test",
            global_kb_enabled=True,
            global_kb_root="/test/global-kb",
        )
        assert config.global_kb_enabled is True
        assert config.global_kb_root == "/test/global-kb"

    def test_compat_matrix_contains_070_and_080(self):
        """compat matrix 包含 0.7.0 和 0.8.0"""
        from memory_core.compat import _COMPAT_MATRIX

        assert "0.7.0" in _COMPAT_MATRIX
        assert "0.8.0" in _COMPAT_MATRIX
