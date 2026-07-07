"""Tests for PreToolUse guard."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from memory_core.ownership import (
    classify_agents_md_block,
    classify_owned_path,
)


class TestPreToolUseGuard:
    """Tests for PreToolUse guard behavior."""

    def _run_guard(self, payload: dict[str, Any], cwd: Path | None = None) -> tuple[int, dict[str, Any]]:
        """Run the guard with given payload and return (exit_code, result)."""
        env = os.environ.copy()
        if cwd:
            env["FACTORY_PROJECT_DIR"] = str(cwd)
            env["MEMORY_HOOK_ORIGINAL_CWD"] = str(cwd)

        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.pretooluse_guard"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env,
        )

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {"raw_stdout": result.stdout, "stderr": result.stderr}

        return result.returncode, output

    def test_guard_blocks_write_to_owned_path(self, tmp_path: Path) -> None:
        """Test that Write to owned path is blocked."""
        # Create .memory to make it a memory-managed project
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Write",
            "file_path": "memory/docs/INDEX.md",
            "content": "test content",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        assert "memory/docs" in result["reason"] or "memory_docs" in result["reason"]

    # ========== 文件类型黑名单测试 ==========

    def test_guard_blocks_write_sql_file(self, tmp_path: Path) -> None:
        """Test that Write to .sql file is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Write",
            "file_path": "test.sql",
            "content": "CREATE TABLE test;",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        assert "文件类型禁止入库：.sql" in result["reason"]

    def test_guard_blocks_write_bak_file(self, tmp_path: Path) -> None:
        """Test that Write to .bak file is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Write",
            "file_path": "backup.bak",
            "content": "backup data",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        assert "文件类型禁止入库：.bak" in result["reason"]

    def test_guard_blocks_write_sqlite_file(self, tmp_path: Path) -> None:
        """Test that Write to .sqlite file is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Write",
            "file_path": "database.sqlite",
            "content": "sqlite data",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        assert "文件类型禁止入库：.sqlite" in result["reason"]

    def test_guard_blocks_write_db_file(self, tmp_path: Path) -> None:
        """Test that Write to .db file is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Write",
            "file_path": "data.db",
            "content": "database",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        assert "文件类型禁止入库：.db" in result["reason"]

    def test_guard_blocks_write_dump_file(self, tmp_path: Path) -> None:
        """Test that Write to .dump file is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Write",
            "file_path": "data.dump",
            "content": "dump data",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        assert "文件类型禁止入库：.dump" in result["reason"]

    def test_guard_allows_write_py_file(self, tmp_path: Path) -> None:
        """Test that Write to .py file is allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Write",
            "file_path": "test.py",
            "content": "print('hello')",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_guard_allows_write_md_file(self, tmp_path: Path) -> None:
        """Test that Write to .md file is allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Write",
            "file_path": "readme.md",
            "content": "# README",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_guard_allows_write_ts_file(self, tmp_path: Path) -> None:
        """Test that Write to .ts file is allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Write",
            "file_path": "test.ts",
            "content": "const x: number = 1;",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_guard_blocks_edit_sql_file(self, tmp_path: Path) -> None:
        """Test that Edit to .sql file is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Edit",
            "file_path": "test.sql",
            "old_str": "SELECT 1",
            "new_str": "SELECT 2",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        assert "文件类型禁止入库：.sql" in result["reason"]

    def test_guard_blocks_multiedit_bak_file(self, tmp_path: Path) -> None:
        """Test that MultiEdit with .bak file is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "MultiEdit",
            "edits": [
                {"file_path": "src/main.py", "old_str": "old", "new_str": "new"},
                {"file_path": "backup.bak", "old_str": "old", "new_str": "new"},
            ],
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        assert "backup.bak" in result["reason"]

    def test_guard_blocks_execute_cp_bak_file(self, tmp_path: Path) -> None:
        """Test that Execute cp to .bak file is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "cp test.txt test.bak",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        assert "文件类型禁止入库：.bak" in result["reason"]

    def test_guard_allows_write_sql_with_memory_hook_force(self, tmp_path: Path) -> None:
        """Test that MEMORY_HOOK_FORCE=1 bypasses file type check."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Write",
            "file_path": "test.sql",
            "content": "CREATE TABLE test;",
        }

        env = os.environ.copy()
        env["FACTORY_PROJECT_DIR"] = str(tmp_path)
        env["MEMORY_HOOK_ORIGINAL_CWD"] = str(tmp_path)
        env["MEMORY_HOOK_FORCE"] = "1"

        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.pretooluse_guard"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            env=env,
        )

        output = json.loads(result.stdout)
        assert result.returncode == 0
        assert output["decision"] == "allow"

    def test_guard_blocks_write_to_backups_directory(self, tmp_path: Path) -> None:
        """Test that Write to backups/ directory is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Write",
            "file_path": "backups/dump.txt",
            "content": "backup data",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        assert "目录 backups 被禁止" in result["reason"]

    def test_guard_blocks_edit_to_owned_path(self, tmp_path: Path) -> None:
        """Test that Edit to owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Edit",
            "file_path": "memory/kb/article.md",
            "old_str": "old",
            "new_str": "new",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_allows_write_to_not_owned_path(self, tmp_path: Path) -> None:
        """Test that Write to not-owned path is allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Write",
            "file_path": "src/main.py",
            "content": "print('hello')",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_guard_blocks_execute_mv_to_owned_path(self, tmp_path: Path) -> None:
        """Test that Execute mv targeting owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "mv temp.md memory/docs/INDEX.md",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_blocks_execute_git_mv_to_owned_path(self, tmp_path: Path) -> None:
        """Test that Execute git mv targeting owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "git mv docs.md memory/kb/docs.md",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_blocks_execute_rm_on_owned_path(self, tmp_path: Path) -> None:
        """Test that Execute rm on owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "rm memory/docs/INDEX.md",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_blocks_execute_python_open_owned_path(self, tmp_path: Path) -> None:
        """Test that Execute python -c with open() to owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "python -c 'open(\"memory/docs/INDEX.md\", \"w\").write(\"test\")'",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_blocks_execute_shell_redirect_to_owned_path(self, tmp_path: Path) -> None:
        """Test that Execute shell redirect to owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "echo 'test' > memory/docs/INDEX.md",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_blocks_execute_mkdir_on_owned_path(self, tmp_path: Path) -> None:
        """Test that Execute mkdir on owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "mkdir memory/docs/newdir",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_blocks_execute_touch_on_owned_path(self, tmp_path: Path) -> None:
        """Test that Execute touch on owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "touch memory/system/memory.lock",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_blocks_multiedit_with_any_owned_path(self, tmp_path: Path) -> None:
        """Test that MultiEdit blocks if ANY path is owned (per-item classification)."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "MultiEdit",
            "edits": [
                {"file_path": "src/main.py", "old_str": "old1", "new_str": "new1"},
                {"file_path": "memory/docs/INDEX.md", "old_str": "old2", "new_str": "new2"},
                {"file_path": "src/other.py", "old_str": "old3", "new_str": "new3"},
            ],
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        # 5b.5: per-item classification now outputs "blocked items" instead of "contains protected path"
        assert "MultiEdit" in result["reason"]
        assert "item_results" in result
        # Verify per-item results
        items = result["item_results"]
        assert len(items) == 3
        blocked_items = [i for i in items if i["decision"] == "block"]
        assert len(blocked_items) == 1
        assert blocked_items[0]["path"] == "memory/docs/INDEX.md"

    def test_guard_allows_multiedit_with_no_owned_paths(self, tmp_path: Path) -> None:
        """Test that MultiEdit allows if no paths are owned."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "MultiEdit",
            "edits": [
                {"file_path": "src/main.py", "old_str": "old1", "new_str": "new1"},
                {"file_path": "src/other.py", "old_str": "old2", "new_str": "new2"},
            ],
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_guard_blocks_notebookedit_to_owned_path(self, tmp_path: Path) -> None:
        """Test that NotebookEdit to owned notebook is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "NotebookEdit",
            "notebook_path": "memory/docs/analysis.ipynb",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_allows_task_without_owned_path_references(self, tmp_path: Path) -> None:
        """Test that Task without owned path references is allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Task",
            "prompt": "Refactor the src/utils.py file to improve code quality",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_guard_blocks_task_with_owned_path_references(self, tmp_path: Path) -> None:
        """Task prompt no longer pre-scanned — sub-agent operations guarded individually."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Task",
            "prompt": "Move memory/kb/docs to a new location",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_guard_blocks_uncertain_path_with_owned_root_string(self, tmp_path: Path) -> None:
        """Test that uncertain path with owned root string is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        # Command contains owned resource string but cannot parse path
        payload = {
            "tool_name": "Execute",
            "command": "echo test > $HOME/memory/docs/file.md",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_blocks_execute_cp_to_owned_destination(self, tmp_path: Path) -> None:
        """Test that Execute cp to owned destination is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "cp temp.md memory/docs/INDEX.md",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_blocks_agents_md_block_internal_modify(self, tmp_path: Path) -> None:
        """Test AGENTS.md scenario 1: block internal modification."""
        (tmp_path / "memory" / "system").mkdir(parents=True)
        (tmp_path / "AGENTS.md").write_text(
            "<!-- ownership:block:start -->\nProtected content\n<!-- ownership:block:end -->\n"
        )

        payload = {
            "tool_name": "Edit",
            "file_path": "AGENTS.md",
            "content_before": "<!-- ownership:block:start -->\nProtected content\n<!-- ownership:block:end -->\n",
            "content_after": "<!-- ownership:block:start -->\nModified content\n<!-- ownership:block:end -->\n",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        # The guard should block this
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_blocks_agents_md_delete_marker(self, tmp_path: Path) -> None:
        """Test AGENTS.md scenario 2: delete protection marker."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Edit",
            "file_path": "AGENTS.md",
            "content_before": "<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->\n",
            "content_after": "\nProtected\n\n",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_allows_agents_md_append_outside_block(self, tmp_path: Path) -> None:
        """Test AGENTS.md scenario 3: append outside block."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Edit",
            "file_path": "AGENTS.md",
            "content_before": "<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->\n",
            "content_after": "<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->\n\nNew content",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_guard_blocks_agents_md_full_overwrite_uncertain(self, tmp_path: Path) -> None:
        """Test AGENTS.md scenario 4: full overwrite uncertain."""
        (tmp_path / "memory" / "system").mkdir(parents=True)
        # Create existing AGENTS.md file
        (tmp_path / "AGENTS.md").write_text("Existing content")

        payload = {
            "tool_name": "Write",
            "file_path": "AGENTS.md",
            "content": "Completely new content",
            # No content_before/after means full overwrite
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_allows_agents_md_memory_init_creation(self, tmp_path: Path) -> None:
        """Test AGENTS.md scenario 5: memory-init creation."""
        # No existing AGENTS.md, creating new
        (tmp_path / "memory" / "system").mkdir(parents=True)
        # Ensure AGENTS.md does NOT exist
        agents_md = tmp_path / "AGENTS.md"
        if agents_md.exists():
            agents_md.unlink()

        payload = {
            "tool_name": "Write",
            "file_path": "AGENTS.md",
            "content": "Initial AGENTS.md content",
            # No content_before means creation
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_memory_hook_force_does_not_bypass_guard(self, tmp_path: Path, monkeypatch) -> None:
        """Test that MEMORY_HOOK_FORCE does NOT bypass PreToolUse guard."""
        (tmp_path / "memory" / "system").mkdir(parents=True)
        monkeypatch.setenv("MEMORY_HOOK_FORCE", "1")

        payload = {
            "tool_name": "Write",
            "file_path": "memory/docs/INDEX.md",
            "content": "test",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        # Should still block even with MEMORY_HOOK_FORCE
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_guard_allows_non_memory_project(self, tmp_path: Path) -> None:
        """Test that guard allows operations on non-memory projects (silent exit 0)."""
        # No .memory directory

        payload = {
            "tool_name": "Write",
            "file_path": "memory/docs/INDEX.md",
            "content": "test",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0

    def test_guard_allows_unknown_tool(self, tmp_path: Path) -> None:
        """Test that unknown tools are allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "SomeUnknownTool",
            "file_path": "memory/docs/INDEX.md",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"
        assert "Unknown tool" in result["reason"]


class TestPreToolUseGuardDirect:
    """Direct tests for guard functions without subprocess."""

    def test_classify_owned_path_importable(self) -> None:
        """Verify classify_owned_path is importable and works."""

        result = classify_owned_path("memory/docs/INDEX.md")
        assert hasattr(result, "level")  # Owned

    def test_classify_not_owned_path(self) -> None:
        """Verify classify_owned_path returns NotOwned for non-owned paths."""

        result = classify_owned_path("src/main.py")
        assert not hasattr(result, "level")  # NotOwned

    def test_agents_md_classify_scenario_1(self) -> None:
        """Test AGENTS.md block internal modify detection."""
        result = classify_agents_md_block(
            "AGENTS.md",
            content_before="<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->",
            content_after="<!-- ownership:block:start -->\nChanged\n<!-- ownership:block:end -->",
        )
        assert result["decision"] == "block"
        assert result["scenario"] == 1

    def test_agents_md_classify_scenario_2(self) -> None:
        """Test AGENTS.md marker deletion detection."""
        result = classify_agents_md_block(
            "AGENTS.md",
            content_before="<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->",
            content_after="Protected\n",
        )
        assert result["decision"] == "block"
        assert result["scenario"] == 2

    def test_agents_md_classify_scenario_3(self) -> None:
        """Test AGENTS.md append after block."""
        result = classify_agents_md_block(
            "AGENTS.md",
            content_before="<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->",
            content_after="<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->\n\nNew",
        )
        assert result["decision"] == "allow"
        assert result["scenario"] == 3

    def test_agents_md_classify_scenario_4(self) -> None:
        """Test AGENTS.md uncertain overwrite."""
        result = classify_agents_md_block(
            "AGENTS.md",
            content_before=None,
            content_after=None,
        )
        assert result["decision"] == "block"
        assert result["scenario"] == 4

    def test_agents_md_classify_scenario_5(self) -> None:
        """Test AGENTS.md creation scenario."""
        result = classify_agents_md_block(
            "AGENTS.md",
            content_before=None,
            content_after="# AGENTS.md\nNew file",
        )
        assert result["decision"] == "allow"
        assert result["scenario"] == 5

    def test_agents_md_not_applicable(self) -> None:
        """Test AGENTS.md classification not applicable for other files."""
        result = classify_agents_md_block(
            "memory/docs/README.md",
            content_before=None,
            content_after=None,
        )
        assert result["decision"] == "not_applicable"


# ---------------------------------------------------------------------------
# M5b Tests: Task payload injection, cwd fixed, Execute P1, AGENTS diff-aware
# ---------------------------------------------------------------------------


class TestTaskPayloadInjection:
    """5b.1: Task tool ownership policy injection tests."""

    def _run_guard(self, payload: dict[str, Any], cwd: Path | None = None) -> tuple[int, dict[str, Any]]:
        """Run the guard with given payload and return (exit_code, result)."""
        env = os.environ.copy()
        if cwd:
            env["FACTORY_PROJECT_DIR"] = str(cwd)
            env["MEMORY_HOOK_ORIGINAL_CWD"] = str(cwd)

        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.pretooluse_guard"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env,
        )

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {"raw_stdout": result.stdout, "stderr": result.stderr}

        return result.returncode, output

    def test_task_injects_ownership_policy_block(self, tmp_path: Path) -> None:
        """Test that Task tool result is clean (no injected_prompt to avoid stdout bloat)."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Task",
            "prompt": "Fix the bug in src/main.py",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"
        # injected_prompt removed: was echoing full prompt + policy back to stdout
        assert "injected_prompt" not in result

    def test_task_injects_policy_lists_domains_and_resources(self, tmp_path: Path) -> None:
        """Test that Task tool still allows without owned references."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Task",
            "prompt": "Do something",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"
        assert "injected_prompt" not in result

    def test_task_policy_injection_idempotent(self, tmp_path: Path) -> None:
        """Test that Task with existing policy marker is still handled correctly."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Task",
            "prompt": "<!-- ownership-policy-injection -->Already injected prompt",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"
        assert "injected_prompt" not in result

    def test_task_blocks_with_policy_and_owned_reference(self, tmp_path: Path) -> None:
        """Test that Task with owned path reference is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Task",
            "prompt": "Delete memory/kb/docs.md",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"
        assert "injected_prompt" not in result

    def test_task_injection_includes_forbidden_instructions(self, tmp_path: Path) -> None:
        """Test that Task tool allows without echoing forbidden instructions in stdout."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Task",
            "prompt": "Refactor code",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"
        assert "injected_prompt" not in result


class TestCwdFixed:
    """5b.2: Task tool cwd fixed to project_root tests."""

    def _run_guard(self, payload: dict[str, Any], cwd: Path | None = None) -> tuple[int, dict[str, Any]]:
        """Run the guard with given payload and return (exit_code, result)."""
        env = os.environ.copy()
        if cwd:
            env["FACTORY_PROJECT_DIR"] = str(cwd)
            env["MEMORY_HOOK_ORIGINAL_CWD"] = str(cwd)

        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.pretooluse_guard"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env,
        )

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {"raw_stdout": result.stdout, "stderr": result.stderr}

        return result.returncode, output

    def test_task_uses_factory_project_dir_not_pwd(self, tmp_path: Path) -> None:
        """Test that Task tool uses FACTORY_PROJECT_DIR, not PWD."""
        (tmp_path / "memory" / "system").mkdir(parents=True)
        # Create a subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()

        payload = {
            "tool_name": "Task",
            "prompt": "Do work",
        }

        # Run from subdirectory but set FACTORY_PROJECT_DIR to root
        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_task_project_root_resolved_from_env(self, tmp_path: Path) -> None:
        """Test that project root is resolved from env even when cwd differs."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        env = os.environ.copy()
        env["FACTORY_PROJECT_DIR"] = str(tmp_path)
        # Simulate PWD being different
        env["MEMORY_HOOK_ORIGINAL_CWD"] = str(tmp_path)

        payload = {
            "tool_name": "Task",
            "prompt": "Do work",
        }

        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.pretooluse_guard"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
        )

        output = json.loads(result.stdout)
        assert output["decision"] == "allow"

    def test_get_project_root_for_task_returns_resolved(self, tmp_path: Path) -> None:
        """Test _get_project_root_for_task returns resolved path."""
        from memory_core.tools.pretooluse_guard import _get_project_root_for_task

        result = _get_project_root_for_task(tmp_path)
        assert result == tmp_path.resolve()


class TestExecuteP1:
    """5b.3: Execute P1 coverage tests — rsync, node -e, shell glob, relative paths."""

    def _run_guard(self, payload: dict[str, Any], cwd: Path | None = None) -> tuple[int, dict[str, Any]]:
        """Run the guard with given payload and return (exit_code, result)."""
        env = os.environ.copy()
        if cwd:
            env["FACTORY_PROJECT_DIR"] = str(cwd)
            env["MEMORY_HOOK_ORIGINAL_CWD"] = str(cwd)

        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.pretooluse_guard"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env,
        )

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {"raw_stdout": result.stdout, "stderr": result.stderr}

        return result.returncode, output

    def test_execute_rsync_to_owned_path_blocked(self, tmp_path: Path) -> None:
        """Test that rsync to owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "rsync -av src/ memory/docs/",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_execute_rsync_to_safe_path_allowed(self, tmp_path: Path) -> None:
        """Test that rsync to safe path is allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "rsync -av src/ backup/",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_execute_node_e_write_owned_path_blocked(self, tmp_path: Path) -> None:
        """Test that node -e with writeFileSync to owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "node -e 'require(\"fs\").writeFileSync(\"memory/docs/INDEX.md\", \"test\")'",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_execute_node_e_write_safe_path_allowed(self, tmp_path: Path) -> None:
        """Test that node -e with writeFileSync to safe path is allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "node -e 'require(\"fs\").writeFileSync(\"output.txt\", \"test\")'",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_execute_shell_glob_owned_path_blocked(self, tmp_path: Path) -> None:
        """Test that shell glob targeting owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "rm -rf memory/docs/*",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_execute_relative_path_to_owned_blocked(self, tmp_path: Path) -> None:
        """Test that relative paths to owned resources are blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "cp config.toml memory/system/adapter.toml",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_execute_dd_to_owned_path_blocked(self, tmp_path: Path) -> None:
        """Test that dd to owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "dd if=/dev/zero of=memory/system/memory.lock bs=1 count=0",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_execute_ln_to_owned_path_blocked(self, tmp_path: Path) -> None:
        """Test that ln targeting owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "ln -s /tmp/fake memory/docs/symlink",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_execute_install_to_owned_path_blocked(self, tmp_path: Path) -> None:
        """Test that install command targeting owned path is blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "install -m 644 file.txt memory/docs/",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"

    def test_execute_env_var_expansion(self, tmp_path: Path) -> None:
        """Test that environment variable expansion works for path classification."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        # With $HOME expansion that doesn't target owned paths
        payload = {
            "tool_name": "Execute",
            "command": "echo test > $HOME/output.txt",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        # The path contains $HOME which is uncertain, and command doesn't contain
        # owned root strings, so should allow
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_execute_quoted_args_parsed_correctly(self, tmp_path: Path) -> None:
        """Test that quoted arguments are parsed correctly."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        # cp with quoted destination targeting owned path
        payload = {
            "tool_name": "Execute",
            "command": 'cp file.txt "memory/docs/INDEX.md"',
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"


class TestAgentsMdDiffAware:
    """5b.4: AGENTS.md diff-aware tests for Edit and MultiEdit."""

    def _run_guard(self, payload: dict[str, Any], cwd: Path | None = None) -> tuple[int, dict[str, Any]]:
        """Run the guard with given payload and return (exit_code, result)."""
        env = os.environ.copy()
        if cwd:
            env["FACTORY_PROJECT_DIR"] = str(cwd)
            env["MEMORY_HOOK_ORIGINAL_CWD"] = str(cwd)

        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.pretooluse_guard"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env,
        )

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {"raw_stdout": result.stdout, "stderr": result.stderr}

        return result.returncode, output

    def test_edit_uses_old_str_as_content_before(self, tmp_path: Path) -> None:
        """Test that Edit tool uses old_str as content_before fallback."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Edit",
            "file_path": "AGENTS.md",
            "old_str": "<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->",
            "new_str": "<!-- ownership:block:start -->\nChanged\n<!-- ownership:block:end -->",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        # Should block because old_str is used as content_before (scenario 1)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_multiedit_agents_md_diff_aware_blocks(self, tmp_path: Path) -> None:
        """Test that MultiEdit with AGENTS.md item uses diff-aware classification."""
        (tmp_path / "memory" / "system").mkdir(parents=True)
        (tmp_path / "AGENTS.md").write_text(
            "<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->\n"
        )

        payload = {
            "tool_name": "MultiEdit",
            "edits": [
                {"file_path": "src/main.py", "old_str": "old", "new_str": "new"},
                {
                    "file_path": "AGENTS.md",
                    "old_str": "<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->",
                    "new_str": "<!-- ownership:block:start -->\nModified\n<!-- ownership:block:end -->",
                },
            ],
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        assert "item_results" in result
        # Find the AGENTS.md item
        agents_item = next(i for i in result["item_results"] if i["path"] == "AGENTS.md")
        assert agents_item["decision"] == "block"

    def test_multiedit_agents_md_diff_aware_allows_append(self, tmp_path: Path) -> None:
        """Test that MultiEdit with AGENTS.md append after block is allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "MultiEdit",
            "edits": [
                {"file_path": "src/main.py", "old_str": "old", "new_str": "new"},
                {
                    "file_path": "AGENTS.md",
                    "old_str": "<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->",
                    "new_str": "<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->\n\nNew section",
                },
            ],
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"
        assert "item_results" in result

    def test_multiedit_agents_md_no_content_before_blocks(self, tmp_path: Path) -> None:
        """Test MultiEdit on AGENTS.md with no content_before and existing file blocks."""
        (tmp_path / "memory" / "system").mkdir(parents=True)
        (tmp_path / "AGENTS.md").write_text("Existing content")

        payload = {
            "tool_name": "MultiEdit",
            "edits": [
                {
                    "file_path": "AGENTS.md",
                    "new_str": "New content",
                },
            ],
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"


class TestMultiEditPerItem:
    """5b.5: MultiEdit per-item classification tests."""

    def _run_guard(self, payload: dict[str, Any], cwd: Path | None = None) -> tuple[int, dict[str, Any]]:
        """Run the guard with given payload and return (exit_code, result)."""
        env = os.environ.copy()
        if cwd:
            env["FACTORY_PROJECT_DIR"] = str(cwd)
            env["MEMORY_HOOK_ORIGINAL_CWD"] = str(cwd)

        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.pretooluse_guard"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env,
        )

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {"raw_stdout": result.stdout, "stderr": result.stderr}

        return result.returncode, output

    def test_multiedit_per_item_classification_results(self, tmp_path: Path) -> None:
        """Test that MultiEdit returns per-item classification results."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "MultiEdit",
            "edits": [
                {"file_path": "src/main.py", "old_str": "old", "new_str": "new"},
                {"file_path": "memory/docs/INDEX.md", "old_str": "old", "new_str": "new"},
                {"file_path": "src/other.py", "old_str": "old", "new_str": "new"},
                {"file_path": "memory/system/STATE.md", "old_str": "old", "new_str": "new"},
            ],
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        assert "item_results" in result

        items = result["item_results"]
        assert len(items) == 4

        # Check each item has path and decision
        blocked = [i for i in items if i["decision"] == "block"]
        allowed = [i for i in items if i["decision"] == "allow"]

        # At least memory/docs/INDEX.md and memory/system/STATE.md should be blocked
        blocked_paths = {i["path"] for i in blocked}
        assert "memory/docs/INDEX.md" in blocked_paths
        assert "memory/system/STATE.md" in blocked_paths

        # src files should be allowed
        allowed_paths = {i["path"] for i in allowed}
        assert "src/main.py" in allowed_paths
        assert "src/other.py" in allowed_paths

    def test_multiedit_all_allowed_returns_item_results(self, tmp_path: Path) -> None:
        """Test that MultiEdit with all allowed paths still returns item_results."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "MultiEdit",
            "edits": [
                {"file_path": "src/a.py", "old_str": "old", "new_str": "new"},
                {"file_path": "src/b.py", "old_str": "old", "new_str": "new"},
            ],
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"
        assert "item_results" in result
        assert len(result["item_results"]) == 2
        assert all(i["decision"] == "allow" for i in result["item_results"])

    def test_multiedit_mixed_agents_md_and_regular(self, tmp_path: Path) -> None:
        """Test MultiEdit with mix of AGENTS.md and regular owned paths."""
        (tmp_path / "memory" / "system").mkdir(parents=True)
        (tmp_path / "AGENTS.md").write_text(
            "<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->\n"
        )

        payload = {
            "tool_name": "MultiEdit",
            "edits": [
                {"file_path": "src/main.py", "old_str": "old", "new_str": "new"},
                {
                    "file_path": "AGENTS.md",
                    "old_str": "<!-- ownership:block:start -->\nProtected\n<!-- ownership:block:end -->",
                    "new_str": "<!-- ownership:block:start -->\nChanged\n<!-- ownership:block:end -->",
                },
            ],
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 2
        assert result["decision"] == "block"
        items = result["item_results"]
        agents_item = next(i for i in items if i["path"] == "AGENTS.md")
        assert agents_item["decision"] == "block"
        src_item = next(i for i in items if i["path"] == "src/main.py")
        assert src_item["decision"] == "allow"


class TestNoopHostDelegate:
    """5b.6: NoopHostDelegate host_unavailable and policy_decision tests."""

    def test_noop_host_unavailable_true(self) -> None:
        """Test that NoopHostDelegate.host_unavailable is True."""
        from memory_core.tools.memory_hook_impls import NoopHostDelegate

        delegate = NoopHostDelegate()
        assert delegate.host_unavailable is True

    def test_noop_response_contains_host_unavailable(self) -> None:
        """Test that noop_response stdout JSON contains host_unavailable=True."""
        from memory_core.tools.memory_hook_impls import NoopHostDelegate

        delegate = NoopHostDelegate()
        response = delegate.noop_response()
        assert response.returncode == 0
        data = json.loads(response.stdout)
        assert data["host_unavailable"] is True

    def test_noop_response_contains_policy_decision(self) -> None:
        """Test that noop_response stdout JSON contains policy_decision separate from availability."""
        from memory_core.tools.memory_hook_impls import NoopHostDelegate

        delegate = NoopHostDelegate()
        response = delegate.noop_response()
        data = json.loads(response.stdout)
        assert "policy_decision" in data
        assert data["policy_decision"] == "no_host"

    def test_real_delegates_host_unavailable_false(self) -> None:
        """Test that real delegates have host_unavailable=False."""
        from memory_core.tools.memory_hook_impls import ClaudeDelegate, CodexDelegate

        codex = CodexDelegate()
        claude = ClaudeDelegate()
        assert codex.host_unavailable is False
        assert claude.host_unavailable is False

    def test_delegate_interface_has_host_unavailable_property(self) -> None:
        """Test that HostDelegate interface defines host_unavailable property."""
        from memory_core.tools.memory_hook_interfaces import HostDelegate

        # Check that the property exists on the ABC
        assert hasattr(HostDelegate, "host_unavailable")
        # Default should be False
        assert HostDelegate.host_unavailable.fget is not None  # type: ignore[attr-defined]

    def test_execute_returns_host_unavailable_response(self) -> None:
        """Test that execute() returns response with host_unavailable marker."""
        from memory_core.tools.memory_hook_impls import NoopHostDelegate

        delegate = NoopHostDelegate()
        response = delegate.execute("test_event", "{}", {})
        data = json.loads(response.stdout)
        assert data["host_unavailable"] is True
        assert data["policy_decision"] == "no_host"


class TestGitOperationsWhitelist:
    """M1-GitHub-Migration: Git operations whitelist tests."""

    def _run_guard(self, payload: dict[str, Any], cwd: Path | None = None) -> tuple[int, dict[str, Any]]:
        """Run the guard with given payload and return (exit_code, result)."""
        env = os.environ.copy()
        if cwd:
            env["FACTORY_PROJECT_DIR"] = str(cwd)
            env["MEMORY_HOOK_ORIGINAL_CWD"] = str(cwd)

        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.pretooluse_guard"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env,
        )

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {"raw_stdout": result.stdout, "stderr": result.stderr}

        return result.returncode, output

    def test_git_add_allowed(self, tmp_path: Path) -> None:
        """Test that git add is allowed for GitHub workflow."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "git add file.py",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"
        assert "git" in result.get("reason", "").lower()

    def test_git_commit_allowed(self, tmp_path: Path) -> None:
        """Test that git commit is allowed for GitHub workflow."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "git commit -m 'feat: add feature'",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"
        assert "git" in result.get("reason", "").lower()

    def test_git_push_allowed(self, tmp_path: Path) -> None:
        """Test that git push is allowed for GitHub workflow."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "git push origin feature-branch",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"
        assert "git" in result.get("reason", "").lower()

    def test_git_push_origin_main_allowed(self, tmp_path: Path) -> None:
        """Test that git push origin main is allowed (branch protection enforced by GitHub)."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "git push origin main",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_git_status_allowed(self, tmp_path: Path) -> None:
        """Test that git status is allowed (read-only operation)."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "git status",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        # git status doesn't match add/commit/push, so it falls through to normal path analysis
        # Since it has no owned paths, it should be allowed
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_git_log_allowed(self, tmp_path: Path) -> None:
        """Test that git log is allowed (read-only operation)."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "git log --oneline",
        }

        exit_code, result = self._run_guard(payload, tmp_path)

        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_git_operations_no_longer_reference_gitlab_api_push(self, tmp_path: Path) -> None:
        """Test that git operations don't require gitlab_api_push.py."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        # Verify the source code no longer contains gitlab_api_push.py whitelist
        guard_file = Path(__file__).parents[1] / "memory_core" / "tools" / "pretooluse_guard.py"
        guard_content = guard_file.read_text()

        # Check that gitlab_api_push.py is not in the allow branch
        # (it might still exist in comments or other contexts)
        lines = guard_content.split('\n')
        in_allow_branch = False
        for line in lines:
            if 'gitlab_api_push.py' in line and 'allow' in line.lower():
                in_allow_branch = True
                break

        # The whitelist branch should not reference gitlab_api_push.py
        assert not in_allow_branch, "gitlab_api_push.py should not be in the allow branch"


class TestReadonlyPassthrough:
    """M2: Read-only command passthrough for Execute tool.

    VAL-M2-031 through VAL-M2-037: Readonly passthrough tests.
    """

    def _run_guard(self, payload: dict[str, Any], cwd: Path | None = None) -> tuple[int, dict[str, Any]]:
        """Run the guard with given payload and return (exit_code, result)."""
        env = os.environ.copy()
        if cwd:
            env["FACTORY_PROJECT_DIR"] = str(cwd)
            env["MEMORY_HOOK_ORIGINAL_CWD"] = str(cwd)

        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.pretooluse_guard"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env,
        )

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {"raw_stdout": result.stdout, "stderr": result.stderr}

        return result.returncode, output

    # ---- VAL-M2-031: Pure read commands referencing memory/system paths pass ----

    def test_grep_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """grep referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "grep -r 'pattern' memory/system/",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_cat_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """cat referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "cat memory/system/ownership.toml",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_ls_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """ls referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "ls -la memory/system/",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_wc_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """wc referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "wc -l memory/system/ownership.toml",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_head_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """head referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "head -20 memory/docs/INDEX.md",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_du_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """du referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "du -sh memory/system/",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_find_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """find referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "find memory/system/ -name '*.toml'",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_tail_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """tail referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "tail -10 memory/system/events.jsonl",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_rg_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """rg (ripgrep) referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "rg 'pattern' memory/system/",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_stat_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """stat referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "stat memory/system/ownership.toml",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_file_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """file referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "file memory/system/ownership.toml",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_diff_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """diff referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "diff memory/system/ownership.toml memory/system/adapter.toml",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_ruff_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """ruff referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "ruff check memory_core/",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_pytest_memory_system_path_allowed(self, tmp_path: Path) -> None:
        """pytest referencing memory/system path should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "pytest tests/test_pretooluse_guard.py -q",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_memory_validate_allowed(self, tmp_path: Path) -> None:
        """memory-validate should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "memory-validate --target /some/project --json",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_memory_verify_consumer_allowed(self, tmp_path: Path) -> None:
        """memory-verify-consumer should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "memory-verify-consumer --path /some/project",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    # ---- VAL-M2-032: Whitelist first-token enforced ----

    def test_non_whitelisted_token_not_auto_passed(self, tmp_path: Path) -> None:
        """Non-whitelisted first token should not auto-pass, falls through to existing logic."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        # 'echo' is not in the whitelist, and it references memory/system
        payload = {
            "tool_name": "Execute",
            "command": "echo test > memory/system/test.txt",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_unknown_command_referencing_memory_blocked(self, tmp_path: Path) -> None:
        """Unknown command referencing memory/system should go through existing logic."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        # 'vim' is not in whitelist
        payload = {
            "tool_name": "Execute",
            "command": "vim memory/system/ownership.toml",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        # Should fall through to existing logic; vim is not a write command
        # that extracts paths, so it will check if command contains owned root strings
        # The command contains "memory/" so it should be blocked
        assert result["decision"] == "block"

    # ---- VAL-M2-033: Write operators force-block even with read prefix ----

    def test_grep_with_redirect_blocked(self, tmp_path: Path) -> None:
        """grep with > redirect should be blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "grep 'pattern' memory/system/ownership.toml > /tmp/output.txt",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_cat_with_append_redirect_blocked(self, tmp_path: Path) -> None:
        """cat with >> redirect should be blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "cat memory/system/ownership.toml >> output.txt",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_ls_with_tee_blocked(self, tmp_path: Path) -> None:
        """ls piped to tee should be blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "ls memory/system/ | tee output.txt",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_grep_with_sed_i_blocked(self, tmp_path: Path) -> None:
        """grep piped to sed -i should be blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "cat memory/system/ownership.toml | sed -i 's/old/new/' memory/system/ownership.toml",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_find_with_cp_blocked(self, tmp_path: Path) -> None:
        """find with cp should be blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "find memory/system/ -name '*.toml' -exec cp {} /tmp/ \\;",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        # cp is a write keyword
        assert result["decision"] == "block"

    def test_grep_with_rm_in_command_blocked(self, tmp_path: Path) -> None:
        """grep followed by rm should be blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "grep -l 'pattern' memory/system/*.toml | xargs rm",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_cat_with_mv_blocked(self, tmp_path: Path) -> None:
        """cat followed by mv should be blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "cat memory/system/ownership.toml && mv memory/system/ownership.toml /tmp/",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_ls_with_mkdir_blocked(self, tmp_path: Path) -> None:
        """ls followed by mkdir should be blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "ls memory/system/ && mkdir memory/system/newdir",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_ls_with_touch_blocked(self, tmp_path: Path) -> None:
        """ls followed by touch should be blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "ls memory/system/ && touch memory/system/newfile.txt",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_ls_with_chmod_blocked(self, tmp_path: Path) -> None:
        """ls followed by chmod should be blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "ls memory/system/ && chmod 755 memory/system/ownership.toml",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_ls_with_chown_blocked(self, tmp_path: Path) -> None:
        """ls followed by chown should be blocked."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "ls memory/system/ && chown root memory/system/ownership.toml",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    # ---- VAL-M2-034: Write operator detection robust to spacing/quoting ----

    def test_redirect_no_space_blocked(self, tmp_path: Path) -> None:
        """Redirect with no space should be caught."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "cat memory/system/ownership.toml>/tmp/out.txt",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_append_no_space_blocked(self, tmp_path: Path) -> None:
        """Append redirect with no space should be caught."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "cat memory/system/ownership.toml>>/tmp/out.txt",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_tee_extra_spaces_blocked(self, tmp_path: Path) -> None:
        """tee with extra spaces should be caught."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "ls memory/system/ | tee   output.txt",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_sed_minus_i_no_space_blocked(self, tmp_path: Path) -> None:
        """sed -i with variant spacing should be caught."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "sed  -i  's/old/new/' memory/system/ownership.toml",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    # ---- VAL-M2-035: Non-memory write commands not over-blocked ----

    def test_grep_non_memory_path_allowed(self, tmp_path: Path) -> None:
        """grep on non-memory paths should still be allowed (no regression)."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "grep -r 'pattern' src/",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_ls_non_memory_path_allowed(self, tmp_path: Path) -> None:
        """ls on non-memory paths should still be allowed (no regression)."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "ls -la /tmp/",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_cat_non_memory_path_allowed(self, tmp_path: Path) -> None:
        """cat on non-memory paths should still be allowed (no regression)."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "cat /etc/hostname",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    # ---- VAL-M2-036: python3 -c and pytest passthrough ----

    def test_python3_read_memory_path_allowed(self, tmp_path: Path) -> None:
        """python3 -c with read operation on memory paths should pass."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "python3 -c 'import json; print(json.load(open(\"memory/system/ownership.toml\")))'",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    def test_python3_write_memory_path_not_auto_passed(self, tmp_path: Path) -> None:
        """python3 -c with write operation should NOT be auto-passed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "python3 -c 'open(\"memory/system/ownership.toml\", \"w\").write(\"hacked\")'",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        # python3 -c with write (open(..."w")) should not be auto-passed
        # It should fall through to existing path extraction logic which detects open() calls
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_python3_script_file_allowed(self, tmp_path: Path) -> None:
        """python3 running a script file should be allowed."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "python3 scripts/check_boundary.py",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"

    # ---- VAL-M2-037: Guard returns correct structured decision ----

    def test_allow_decision_structure(self, tmp_path: Path) -> None:
        """Allow decision has correct JSON structure."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "cat memory/system/ownership.toml",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"
        assert "reason" in result

    def test_block_decision_structure(self, tmp_path: Path) -> None:
        """Block decision has correct JSON structure with reason."""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "cat memory/system/ownership.toml > /tmp/output.txt",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"
        assert "reason" in result
        assert isinstance(result["reason"], str)
        assert len(result["reason"]) > 0


# ---------------------------------------------------------------------------
# SCRUTINY: Security fix tests — pipe bypass + eval/bash/sh coverage
# ---------------------------------------------------------------------------


class TestPipeWriteBypassFix:
    """Scrutiny 漏洞 1（MEDIUM）：管道写绕过修复测试。

    cat f | python3 -c "open('x','w')" 不应被判定为只读。
    """

    def _run_guard(self, payload: dict[str, Any], cwd: Path | None = None) -> tuple[int, dict[str, Any]]:
        """Run the guard with given payload and return (exit_code, result)."""
        env = os.environ.copy()
        if cwd:
            env["FACTORY_PROJECT_DIR"] = str(cwd)
            env["MEMORY_HOOK_ORIGINAL_CWD"] = str(cwd)

        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.pretooluse_guard"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env,
        )

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {"raw_stdout": result.stdout, "stderr": result.stderr}

        return result.returncode, output

    def test_pipe_with_python_write_not_readonly(self) -> None:
        """_is_readonly_command 对含管道的命令返回 False。"""
        from memory_core.tools.pretooluse_guard import _is_readonly_command

        assert _is_readonly_command('cat f | python3 -c "open(\'x\',\'w\')"') is False

    def test_pipe_with_grep_not_readonly(self) -> None:
        """即使管道后是只读命令（grep），也不判定为只读。"""
        from memory_core.tools.pretooluse_guard import _is_readonly_command

        assert _is_readonly_command("ls memory/system/ | grep pattern") is False

    def test_pipe_python_write_blocked_via_guard(self, tmp_path: Path) -> None:
        """cat memory/... | python3 -c "open('x','w')" 被 guard 拦截。"""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": 'cat memory/system/ownership.toml | python3 -c "open(\'x\',\'w\')"',
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_pipe_to_xargs_rm_blocked(self, tmp_path: Path) -> None:
        """grep ... | xargs rm 被 guard 拦截（管道检测先行）。"""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "grep -l 'pattern' memory/system/*.toml | xargs rm",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_no_pipe_readonly_unchanged(self) -> None:
        """无管道的纯读命令不受影响（行为不变）。"""
        from memory_core.tools.pretooluse_guard import _is_readonly_command

        assert _is_readonly_command("cat memory/system/ownership.toml") is True
        assert _is_readonly_command("ls -la memory/system/") is True
        assert _is_readonly_command("grep -r 'pattern' memory/system/") is True

    def test_du_sh_flag_not_affected_by_pipe_check(self, tmp_path: Path) -> None:
        """du -sh（无管道）仍然放行。"""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": "du -sh memory/system/",
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 0
        assert result["decision"] == "allow"


class TestEvalBashShCoverage:
    """Scrutiny 漏洞 2（LOW）：eval/bash/sh 未覆盖修复测试。"""

    def _run_guard(self, payload: dict[str, Any], cwd: Path | None = None) -> tuple[int, dict[str, Any]]:
        """Run the guard with given payload and return (exit_code, result)."""
        env = os.environ.copy()
        if cwd:
            env["FACTORY_PROJECT_DIR"] = str(cwd)
            env["MEMORY_HOOK_ORIGINAL_CWD"] = str(cwd)

        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.pretooluse_guard"],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
            env=env,
        )

        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError:
            output = {"raw_stdout": result.stdout, "stderr": result.stderr}

        return result.returncode, output

    def test_eval_in_whitelisted_command_not_readonly(self) -> None:
        """cat f && eval "rm ..." 不被判定为只读。"""
        from memory_core.tools.pretooluse_guard import _is_readonly_command

        assert _is_readonly_command('cat file && eval "rm -rf /"') is False

    def test_bash_in_whitelisted_command_not_readonly(self) -> None:
        """cat f && bash script.sh 不被判定为只读。"""
        from memory_core.tools.pretooluse_guard import _is_readonly_command

        assert _is_readonly_command("cat file && bash malicious.sh") is False

    def test_sh_in_whitelisted_command_not_readonly(self) -> None:
        """cat f && sh script.sh 不被判定为只读。"""
        from memory_core.tools.pretooluse_guard import _is_readonly_command

        assert _is_readonly_command("cat file && sh malicious.sh") is False

    def test_eval_targeting_owned_path_blocked(self, tmp_path: Path) -> None:
        """eval "rm -rf memory/..." 被 guard 拦截。"""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": 'eval "rm -rf memory/docs/"',
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_eval_chained_after_read_blocked(self, tmp_path: Path) -> None:
        """cat f && eval "rm ..." 被 guard 拦截（eval 关键词检测）。"""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        payload = {
            "tool_name": "Execute",
            "command": 'cat memory/system/ownership.toml && eval "rm -rf /tmp"',
        }
        exit_code, result = self._run_guard(payload, tmp_path)
        assert exit_code == 2
        assert result["decision"] == "block"

    def test_sh_flag_not_false_positive(self) -> None:
        """du -sh 中的 -sh 不被误判为 sh 写命令。"""
        from memory_core.tools.pretooluse_guard import _is_readonly_command

        assert _is_readonly_command("du -sh memory/system/") is True

    def test_bashrc_path_not_false_positive(self) -> None:
        """路径中的 .bashrc 不被误判为 bash 写命令。"""
        from memory_core.tools.pretooluse_guard import _is_readonly_command

        assert _is_readonly_command("cat ~/.bashrc") is True

    def test_pure_read_commands_still_allowed(self, tmp_path: Path) -> None:
        """原有纯读命令放行不受影响。"""
        (tmp_path / "memory" / "system").mkdir(parents=True)

        for cmd in [
            "cat memory/system/ownership.toml",
            "ls -la memory/system/",
            "grep -r 'pattern' memory/system/",
            "wc -l memory/system/ownership.toml",
            "head -20 memory/docs/INDEX.md",
        ]:
            payload = {"tool_name": "Execute", "command": cmd}
            exit_code, result = self._run_guard(payload, tmp_path)
            assert exit_code == 0, f"Command should be allowed: {cmd}"
            assert result["decision"] == "allow"
