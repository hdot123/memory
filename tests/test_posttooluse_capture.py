"""Tests for PostToolUse real-time knowledge capture (Layer 2)."""
from __future__ import annotations

from pathlib import Path

from memory_core.tools.posttooluse_capture import (
    _parse_global_kb_config,
    capture_to_global_kb,
    should_capture,
)

# ---------------------------------------------------------------------------
# should_capture
# ---------------------------------------------------------------------------

class TestShouldCapture:
    def test_write_to_lessons_matches(self, tmp_path: Path) -> None:
        project_root = tmp_path
        lessons_dir = project_root / "memory" / "kb" / "lessons"
        lessons_dir.mkdir(parents=True)
        target = lessons_dir / "test-lesson.md"
        target.write_text("# Test")

        payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
        result = should_capture(payload, project_root)
        assert result == target

    def test_write_to_decisions_matches(self, tmp_path: Path) -> None:
        project_root = tmp_path
        decisions_dir = project_root / "memory" / "kb" / "decisions"
        decisions_dir.mkdir(parents=True)
        target = decisions_dir / "d001.md"
        target.write_text("# Decision")

        payload = {"tool_name": "Edit", "tool_input": {"file_path": str(target)}}
        result = should_capture(payload, project_root)
        assert result == target

    def test_write_to_projects_no_match(self, tmp_path: Path) -> None:
        project_root = tmp_path
        projects_dir = project_root / "memory" / "kb" / "projects"
        projects_dir.mkdir(parents=True)
        target = projects_dir / "foo.md"
        target.write_text("# Foo")

        payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
        result = should_capture(payload, project_root)
        assert result is None

    def test_write_outside_memory_no_match(self, tmp_path: Path) -> None:
        project_root = tmp_path
        target = project_root / "src" / "main.py"
        target.parent.mkdir(parents=True)
        target.write_text("print('hi')")

        payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
        result = should_capture(payload, project_root)
        assert result is None

    def test_nonexistent_file_no_match(self, tmp_path: Path) -> None:
        project_root = tmp_path
        (project_root / "memory" / "kb" / "lessons").mkdir(parents=True)
        target = project_root / "memory" / "kb" / "lessons" / "ghost.md"

        payload = {"tool_name": "Write", "tool_input": {"file_path": str(target)}}
        result = should_capture(payload, project_root)
        assert result is None

    def test_no_file_path(self, tmp_path: Path) -> None:
        payload = {"tool_name": "Write", "tool_input": {}}
        result = should_capture(payload, tmp_path)
        assert result is None

    def test_top_level_file_path(self, tmp_path: Path) -> None:
        """Payload without tool_input wrapper (standalone format)."""
        project_root = tmp_path
        lessons_dir = project_root / "memory" / "kb" / "lessons"
        lessons_dir.mkdir(parents=True)
        target = lessons_dir / "x.md"
        target.write_text("x")

        payload = {"tool_name": "Write", "file_path": str(target)}
        result = should_capture(payload, project_root)
        assert result == target


# ---------------------------------------------------------------------------
# _parse_global_kb_config
# ---------------------------------------------------------------------------

class TestParseGlobalKbConfig:
    def test_enabled_with_root(self, tmp_path: Path) -> None:
        adapter = tmp_path / "adapter.toml"
        adapter.write_text(
            '[core]\nversion = "0.8.0"\n\n'
            '[global_kb]\nenabled = true\nroot = "/tmp/gkb"\n'
        )
        enabled, root = _parse_global_kb_config(adapter)
        assert enabled is True
        assert root == "/tmp/gkb"

    def test_disabled(self, tmp_path: Path) -> None:
        adapter = tmp_path / "adapter.toml"
        adapter.write_text('[global_kb]\nenabled = false\nroot = "/tmp/gkb"\n')
        enabled, root = _parse_global_kb_config(adapter)
        assert enabled is False
        assert root is None

    def test_no_global_kb_section(self, tmp_path: Path) -> None:
        adapter = tmp_path / "adapter.toml"
        adapter.write_text('[core]\nversion = "0.8.0"\n')
        enabled, root = _parse_global_kb_config(adapter)
        assert enabled is False
        assert root is None

    def test_file_not_exists(self, tmp_path: Path) -> None:
        enabled, root = _parse_global_kb_config(tmp_path / "nonexistent.toml")
        assert enabled is False
        assert root is None

    def test_root_with_tilde(self, tmp_path: Path) -> None:
        adapter = tmp_path / "adapter.toml"
        adapter.write_text(
            '[global_kb]\nenabled = true\nroot = "~/.memory/global-kb"\n'
        )
        enabled, root = _parse_global_kb_config(adapter)
        assert enabled is True
        assert root is not None
        assert "~" not in root  # tilde expanded


# ---------------------------------------------------------------------------
# capture_to_global_kb
# ---------------------------------------------------------------------------

class TestCaptureToGlobalKb:
    def test_capture_success(self, tmp_path: Path) -> None:
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        system_dir = project_root / "memory" / "system"
        system_dir.mkdir(parents=True)
        lessons_dir = project_root / "memory" / "kb" / "lessons"
        lessons_dir.mkdir(parents=True)

        # adapter.toml with global_kb enabled
        (system_dir / "adapter.toml").write_text(
            '[global_kb]\nenabled = true\nroot = "{}"\n'.format(tmp_path / "gkb")
        )

        # Source file
        src = lessons_dir / "lesson1.md"
        src.write_text("# Lesson 1\n\nContent here.")

        result = capture_to_global_kb(src, project_root)
        assert result["status"] == "captured"
        pending = Path(result["path"])
        assert pending.exists()
        assert pending.name == "myproject_lessons_lesson1.md"
        content = pending.read_text()
        assert "source_project:" in content
        assert "capture_layer: posttooluse" in content
        assert "# Lesson 1" in content

    def test_capture_idempotent(self, tmp_path: Path) -> None:
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        system_dir = project_root / "memory" / "system"
        system_dir.mkdir(parents=True)
        lessons_dir = project_root / "memory" / "kb" / "lessons"
        lessons_dir.mkdir(parents=True)

        (system_dir / "adapter.toml").write_text(
            '[global_kb]\nenabled = true\nroot = "{}"\n'.format(tmp_path / "gkb")
        )

        src = lessons_dir / "lesson2.md"
        src.write_text("# Lesson 2")

        # First capture
        r1 = capture_to_global_kb(src, project_root)
        assert r1["status"] == "captured"

        # Second capture — idempotent
        r2 = capture_to_global_kb(src, project_root)
        assert r2["status"] == "idempotent"

    def test_capture_disabled_skipped(self, tmp_path: Path) -> None:
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        system_dir = project_root / "memory" / "system"
        system_dir.mkdir(parents=True)
        lessons_dir = project_root / "memory" / "kb" / "lessons"
        lessons_dir.mkdir(parents=True)

        (system_dir / "adapter.toml").write_text(
            '[global_kb]\nenabled = false\nroot = "{}"\n'.format(tmp_path / "gkb")
        )

        src = lessons_dir / "lesson3.md"
        src.write_text("# Lesson 3")

        result = capture_to_global_kb(src, project_root)
        assert result["status"] == "skipped"

    def test_capture_no_adapter_skipped(self, tmp_path: Path) -> None:
        project_root = tmp_path / "myproject"
        project_root.mkdir()
        (project_root / "memory" / "system").mkdir(parents=True)
        lessons_dir = project_root / "memory" / "kb" / "lessons"
        lessons_dir.mkdir(parents=True)

        src = lessons_dir / "lesson4.md"
        src.write_text("# Lesson 4")

        result = capture_to_global_kb(src, project_root)
        assert result["status"] == "skipped"
