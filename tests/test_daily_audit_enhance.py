"""Tests for daily_kb_audit enhancements (VAL-M2-012 to VAL-M2-017, VAL-M2-040, VAL-M2-041, VAL-CROSS-002).

Tests per-project memory-validate, retention cleanup integration, empty registry
graceful degradation, and missing path skip behavior.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_path_index(tmp_path: Path, projects: dict[str, str]) -> Path:
    """Create a path-index.json with the given {path: project_name} mapping."""
    lifecycle_dir = tmp_path / ".memory-core" / "project-lifecycle"
    lifecycle_dir.mkdir(parents=True)
    index_path = lifecycle_dir / "path-index.json"
    paths_dict = {}
    for path_str, name in projects.items():
        paths_dict[path_str] = {"project_name": name}
    index_data = {"schema_version": "project-lifecycle-path-index-v1", "paths": paths_dict}
    index_path.write_text(json.dumps(index_data, ensure_ascii=False, indent=2))
    return index_path


def _mock_validate_success() -> dict:
    """Return a successful memory-validate JSON result."""
    return {
        "status": "ok",
        "target": "/some/path",
        "checks": {
            "ownership": {"ok": True, "violations": []},
            "manifest": {"ok": True, "violations": []},
        },
    }


def _mock_validate_failure(errors: list[str]) -> dict:
    """Return a failed memory-validate JSON result."""
    return {
        "status": "fail",
        "target": "/some/path",
        "checks": {
            "ownership": {"ok": False, "violations": errors},
        },
    }


# ---------------------------------------------------------------------------
# VAL-M2-012: Per-project validate iterates lifecycle registry
# ---------------------------------------------------------------------------

class TestPerProjectValidateIteration:
    """Audit reads project list from path-index.json and runs memory-validate against each."""

    def test_validate_called_for_each_registered_project(self, tmp_path: Path) -> None:
        """Exactly registry projects validated, each once."""
        from memory_core.tools.daily_kb_audit import (
            run_per_project_validate,
        )

        # Create fake project directories
        proj_a = tmp_path / "project_a"
        proj_a.mkdir()
        proj_b = tmp_path / "project_b"
        proj_b.mkdir()

        projects = [
            ("project_a", proj_a),
            ("project_b", proj_b),
        ]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(_mock_validate_success()),
                stderr="",
            )

            results = run_per_project_validate(projects)

            # Should be called exactly twice (once per project)
            assert mock_run.call_count == 2
            # Both projects should be in results
            assert "project_a" in results
            assert "project_b" in results

    def test_validate_called_with_correct_target(self, tmp_path: Path) -> None:
        """Each validate call uses the correct --target path."""
        from memory_core.tools.daily_kb_audit import run_per_project_validate

        proj_a = tmp_path / "project_a"
        proj_a.mkdir()
        projects = [("project_a", proj_a)]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(_mock_validate_success()),
                stderr="",
            )

            run_per_project_validate(projects)

            # Check the command includes --target <path>
            call_args = mock_run.call_args[0][0]
            # Command uses python -m memory_core.tools.validate_project_memory
            assert "-m" in call_args
            assert "memory_core.tools.validate_project_memory" in call_args
            assert "--target" in call_args
            assert str(proj_a) in call_args
            assert "--json" in call_args


# ---------------------------------------------------------------------------
# VAL-M2-013: Validate failures surface in report
# ---------------------------------------------------------------------------

class TestValidateFailuresInReport:
    """A project whose memory-validate fails is captured in the audit report."""

    def test_failing_project_in_report(self, tmp_path: Path) -> None:
        """Report contains failing project with detail."""
        from memory_core.tools.daily_kb_audit import run_per_project_validate

        proj_fail = tmp_path / "failing_project"
        proj_fail.mkdir()
        projects = [("failing_project", proj_fail)]

        errors = ["manifest.json missing", "ownership.toml version mismatch"]
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout=json.dumps(_mock_validate_failure(errors)),
                stderr="",
            )

            results = run_per_project_validate(projects)

            assert "failing_project" in results
            result = results["failing_project"]
            assert result["status"] == "fail"
            assert "errors" in result or "violations" in result

    def test_passing_project_not_flagged(self, tmp_path: Path) -> None:
        """Passing project not falsely flagged as failing."""
        from memory_core.tools.daily_kb_audit import run_per_project_validate

        proj_ok = tmp_path / "passing_project"
        proj_ok.mkdir()
        projects = [("passing_project", proj_ok)]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout=json.dumps(_mock_validate_success()),
                stderr="",
            )

            results = run_per_project_validate(projects)

            assert "passing_project" in results
            result = results["passing_project"]
            assert result["status"] == "ok"


# ---------------------------------------------------------------------------
# VAL-M2-014: Feishu notification on validate failure
# ---------------------------------------------------------------------------

class TestFeishuNotificationOnValidateFailure:
    """With --notify and >=1 failing project, Feishu message sent."""

    def test_notify_called_when_validate_fails(self, tmp_path: Path) -> None:
        """Send call count and payload match expectations."""
        from memory_core.tools.daily_kb_audit import (
            notify_via_lark,
            run_per_project_validate,
        )

        proj_fail = tmp_path / "failing_project"
        proj_fail.mkdir()
        projects = [("failing_project", proj_fail)]

        with patch("subprocess.run") as mock_run:
            # First call: memory-validate (fails)
            # Subsequent calls: lark-cli (for notification)
            validate_result = subprocess.CompletedProcess(
                args=[],
                returncode=1,
                stdout=json.dumps(_mock_validate_failure(["error1"])),
                stderr="",
            )
            lark_result = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout='{"ok": true}',
                stderr="",
            )
            mock_run.side_effect = [validate_result, lark_result]

            # Run validate
            validate_results = run_per_project_validate(projects)

            # Build report with validate results
            report = {
                "audit_date": "2024-01-01",
                "projects_checked": 1,
                "total_violations": 1,
                "projects": {},
                "validate_results": validate_results,
            }

            # Notify
            with patch.dict("os.environ", {"LARK_AUDIT_CHAT_ID": "test-chat-id"}):
                success = notify_via_lark(report)

            # Should have called lark-cli
            assert success is True
            assert mock_run.call_count == 2
            # Second call should be lark-cli
            lark_call_args = mock_run.call_args_list[1][0][0]
            assert "lark-cli" in lark_call_args[0]

    def test_notify_includes_failing_project_names(self, tmp_path: Path) -> None:
        """Feishu message contains failing project names."""
        from memory_core.tools.daily_kb_audit import notify_via_lark

        report = {
            "audit_date": "2024-01-01",
            "projects_checked": 2,
            "total_violations": 1,
            "projects": {},
            "validate_results": {
                "project_a": {"status": "ok"},
                "project_b": {
                    "status": "fail",
                    "errors": ["manifest missing"],
                },
            },
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = subprocess.CompletedProcess(
                args=[],
                returncode=0,
                stdout='{"ok": true}',
                stderr="",
            )

            with patch.dict("os.environ", {"LARK_AUDIT_CHAT_ID": "test-chat-id"}):
                notify_via_lark(report)

            # Check that the message includes the failing project name
            call_args = mock_run.call_args[0][0]
            message = " ".join(str(arg) for arg in call_args)
            assert "project_b" in message


# ---------------------------------------------------------------------------
# VAL-M2-015: Audit invokes retention cleanup
# ---------------------------------------------------------------------------

class TestAuditInvokesRetentionCleanup:
    """Daily audit calls clean_artifacts() for both repo and registered projects."""

    def test_clean_artifacts_called_for_repo_and_projects(self, tmp_path: Path) -> None:
        """clean_artifacts call list covers expected targets."""
        from memory_core.tools.daily_kb_audit import run_retention_cleanup

        # Create fake project directories with artifact trees
        proj_a = tmp_path / "project_a" / "artifacts" / "memory-hook"
        proj_a.mkdir(parents=True)
        proj_b = tmp_path / "project_b" / "artifacts" / "memory-hook"
        proj_b.mkdir(parents=True)

        repo_root = tmp_path / "memory-core-repo"
        repo_hook = repo_root / "memory" / "artifacts" / "memory-hook"
        repo_hook.mkdir(parents=True)

        projects = [
            ("project_a", tmp_path / "project_a"),
            ("project_b", tmp_path / "project_b"),
        ]

        with patch(
            "memory_core.tools.daily_kb_audit.clean_artifacts"
        ) as mock_clean:
            from memory_core.tools.artifact_retention import CleanupReport
            mock_clean.return_value = CleanupReport()

            run_retention_cleanup(projects, repo_root)

            # Should be called for repo + 2 projects = 3 times
            assert mock_clean.call_count == 3

    def test_clean_artifacts_uses_correct_paths(self, tmp_path: Path) -> None:
        """clean_artifacts called with correct target paths."""
        from memory_core.tools.daily_kb_audit import run_retention_cleanup

        proj_a = tmp_path / "project_a"
        proj_a.mkdir()
        hook_a = proj_a / "artifacts" / "memory-hook"
        hook_a.mkdir(parents=True)

        repo_root = tmp_path / "repo"
        repo_hook = repo_root / "memory" / "artifacts" / "memory-hook"
        repo_hook.mkdir(parents=True)

        projects = [("project_a", proj_a)]

        with patch(
            "memory_core.tools.daily_kb_audit.clean_artifacts"
        ) as mock_clean:
            from memory_core.tools.artifact_retention import CleanupReport
            mock_clean.return_value = CleanupReport()

            run_retention_cleanup(projects, repo_root)

            # Check that correct paths were used
            call_targets = [call[0][0] for call in mock_clean.call_args_list]
            # Should include repo hook path and project hook path
            assert any("memory" in str(p) and "artifacts" in str(p) for p in call_targets)


# ---------------------------------------------------------------------------
# VAL-M2-016: Empty registry degrades gracefully
# ---------------------------------------------------------------------------

class TestEmptyRegistryGracefulDegradation:
    """Empty path-index.json -> audit completes exit 0, no exceptions."""

    def test_empty_registry_exits_zero(self, tmp_path: Path) -> None:
        """Exit 0, no traceback."""
        from memory_core.tools.daily_kb_audit import main

        # Create empty path-index.json
        lifecycle_dir = tmp_path / ".memory-core" / "project-lifecycle"
        lifecycle_dir.mkdir(parents=True)
        index_path = lifecycle_dir / "path-index.json"
        index_path.write_text(json.dumps({"paths": {}}))

        with patch("memory_core.tools.daily_kb_audit.LIFECYCLE_INDEX", index_path):
            with patch("memory_core.tools.daily_kb_audit.AUDIT_DIR", tmp_path / "audit"):
                with patch("memory_core.tools.daily_kb_audit.check_infrastructure") as mock_infra:
                    mock_infra.return_value = {"servers": {}, "databases": {}, "violations": []}

                    exit_code = main(["--no-write", "--no-infra"])

                    assert exit_code == 0

    def test_missing_path_index_exits_zero(self, tmp_path: Path) -> None:
        """Missing path-index.json -> exit 0, no crash."""
        from memory_core.tools.daily_kb_audit import main

        nonexistent_index = tmp_path / "does_not_exist" / "path-index.json"

        with patch("memory_core.tools.daily_kb_audit.LIFECYCLE_INDEX", nonexistent_index):
            with patch("memory_core.tools.daily_kb_audit.AUDIT_DIR", tmp_path / "audit"):
                with patch("memory_core.tools.daily_kb_audit.check_infrastructure") as mock_infra:
                    mock_infra.return_value = {"servers": {}, "databases": {}, "violations": []}

                    exit_code = main(["--no-write", "--no-infra"])

                    assert exit_code == 0


# ---------------------------------------------------------------------------
# VAL-M2-017: Project with missing on-disk path is skipped
# ---------------------------------------------------------------------------

class TestMissingProjectPathSkipped:
    """Registry entry whose path no longer exists is skipped with warning, not crash."""

    def test_missing_path_skipped_no_crash(self, tmp_path: Path) -> None:
        """No exception, report notes stale entry."""
        from memory_core.tools.daily_kb_audit import run_per_project_validate

        nonexistent = tmp_path / "does_not_exist"
        projects = [("ghost_project", nonexistent)]

        # Should not raise
        results = run_per_project_validate(projects)

        # Should be in results with skipped status
        assert "ghost_project" in results
        result = results["ghost_project"]
        assert result.get("status") == "skipped" or result.get("skipped") is True

    def test_missing_path_in_retention_cleanup(self, tmp_path: Path) -> None:
        """Missing project path doesn't crash retention cleanup."""
        from memory_core.tools.daily_kb_audit import run_retention_cleanup

        nonexistent = tmp_path / "does_not_exist"
        projects = [("ghost_project", nonexistent)]
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        with patch(
            "memory_core.tools.daily_kb_audit.clean_artifacts"
        ) as mock_clean:
            from memory_core.tools.artifact_retention import CleanupReport
            mock_clean.return_value = CleanupReport()

            # Should not raise
            run_retention_cleanup(projects, repo_root)


# ---------------------------------------------------------------------------
# VAL-M2-040: Cron wiring (documentation test)
# ---------------------------------------------------------------------------

class TestCronWiring:
    """Cron entry for daily audit is documented (not a runtime test)."""

    def test_audit_main_accepts_notify_flag(self) -> None:
        """memory-audit-daily --notify is a valid CLI flag."""
        from memory_core.tools.daily_kb_audit import _parse_args

        args = _parse_args(["--notify"])
        assert args.notify is True

    def test_audit_main_accepts_no_infra_flag(self) -> None:
        """memory-audit-daily --no-infra is a valid CLI flag."""
        from memory_core.tools.daily_kb_audit import _parse_args

        args = _parse_args(["--no-infra"])
        assert args.no_infra is True


# ---------------------------------------------------------------------------
# VAL-M2-041: No regression to existing daily-audit checks
# ---------------------------------------------------------------------------

class TestNoRegressionToExistingChecks:
    """Legacy checks (global-kb pending, INDEX sync) still run and report."""

    def test_existing_audit_project_still_works(self, tmp_path: Path) -> None:
        """audit_project() still runs all 5 checks for non-source repos."""
        from memory_core.tools.daily_kb_audit import audit_project

        # Create a minimal project structure
        manifest_dir = tmp_path / "memory" / "system"
        manifest_dir.mkdir(parents=True)
        (manifest_dir / "manifest.json").write_text('{"entries": []}')

        with patch(
            "memory_core.tools.daily_kb_audit.check_manifest_integrity"
        ) as mock_c1:
            mock_c1.return_value = []
            with patch(
                "memory_core.tools.daily_kb_audit.check_unsigned_files"
            ) as mock_c2:
                mock_c2.return_value = []
                with patch(
                    "memory_core.tools.daily_kb_audit.check_global_residue"
                ) as mock_c3:
                    mock_c3.return_value = []
                    with patch(
                        "memory_core.tools.daily_kb_audit.check_large_or_db_files"
                    ) as mock_c4:
                        mock_c4.return_value = []
                        with patch(
                            "memory_core.tools.daily_kb_audit.check_version_consistency"
                        ) as mock_c5:
                            mock_c5.return_value = []

                            audit_project("test-project", tmp_path, {})

                            # All 5 checks should have been called
                            mock_c1.assert_called_once()
                            mock_c2.assert_called_once()
                            mock_c3.assert_called_once()
                            mock_c4.assert_called_once()
                            mock_c5.assert_called_once()


# ---------------------------------------------------------------------------
# VAL-CROSS-002: Retention integrates with daily audit end-to-end
# ---------------------------------------------------------------------------

class TestRetentionIntegrationEndToEnd:
    """Running memory-audit-daily executes retention + per-project validate."""

    def test_both_steps_execute_in_sequence(self, tmp_path: Path) -> None:
        """Both new steps execute and appear in report."""
        from memory_core.tools.daily_kb_audit import main

        # Create a project
        proj = tmp_path / "project"
        proj.mkdir()
        hook = proj / "artifacts" / "memory-hook"
        hook.mkdir(parents=True)

        # Create path-index.json
        lifecycle_dir = tmp_path / ".memory-core" / "project-lifecycle"
        lifecycle_dir.mkdir(parents=True)
        index_path = lifecycle_dir / "path-index.json"
        index_data = {
            "paths": {
                str(proj): {"project_name": "test_project"}
            }
        }
        index_path.write_text(json.dumps(index_data))

        with patch("memory_core.tools.daily_kb_audit.LIFECYCLE_INDEX", index_path):
            with patch("memory_core.tools.daily_kb_audit.AUDIT_DIR", tmp_path / "audit"):
                with patch("memory_core.tools.daily_kb_audit.check_infrastructure") as mock_infra:
                    mock_infra.return_value = {"servers": {}, "databases": {}, "violations": []}
                    with patch("subprocess.run") as mock_subprocess:
                        # memory-validate returns success
                        mock_subprocess.return_value = subprocess.CompletedProcess(
                            args=[],
                            returncode=0,
                            stdout=json.dumps(_mock_validate_success()),
                            stderr="",
                        )
                        with patch(
                            "memory_core.tools.daily_kb_audit.clean_artifacts"
                        ) as mock_clean:
                            from memory_core.tools.artifact_retention import CleanupReport
                            mock_clean.return_value = CleanupReport()

                            main(["--no-write", "--no-infra"])

                            # Both validate and clean should have been called
                            assert mock_subprocess.call_count >= 1
                            assert mock_clean.call_count >= 1
