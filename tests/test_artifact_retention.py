"""Tests for artifact_retention module (VAL-M2-001 to VAL-M2-011, VAL-M2-042)."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _backdate(path: Path, days: int) -> None:
    """Set mtime of *path* to *days* days ago."""
    ts = time.time() - days * 86400
    os.utime(str(path), (ts, ts))


def _seed_artifact_tree(root: Path) -> Path:
    """Create a realistic memory-hook artifact tree under *root*.

    Layout::

        root/
          artifacts/memory-hook/
            contexts/YYYY-MM-DD/      (day dirs)
            events/YYYY-MM-DD.jsonl   (day files)
            events.jsonl              (lifecycle)
            metrics.jsonl
          kb/decisions/dec1.md        (must never be touched)
          docs/design/spec.md         (must never be touched)
    """
    hook = root / "artifacts" / "memory-hook"
    ctx = hook / "contexts"
    evt = hook / "events"

    today = date.today()

    # Fresh dir (today)
    _make_dir(ctx / today.isoformat())
    (ctx / today.isoformat() / "snap.json").write_text("{}")

    # Old dir (60 days ago)
    old_date = (today - timedelta(days=60)).isoformat()
    _make_dir(ctx / old_date)
    (ctx / old_date / "snap.json").write_text("{}")
    _backdate(ctx / old_date, 60)

    # Create events dir
    _make_dir(evt)

    # Fresh event file
    (evt / f"{today.isoformat()}.jsonl").write_text('{"ts": "now"}\n')

    # Old event file
    old_evt = evt / f"{old_date}.jsonl"
    old_evt.write_text('{"ts": "old"}\n')
    _backdate(old_evt, 60)

    # Lifecycle files
    (hook / "events.jsonl").write_text('{"lifecycle": true}\n')
    (hook / "metrics.jsonl").write_text('{"metric": 1}\n')

    # KB/docs (must never be touched)
    kb_dir = root / "kb" / "decisions"
    _make_dir(kb_dir)
    (kb_dir / "dec1.md").write_text("# Decision 1\n")

    docs_dir = root / "docs" / "design"
    _make_dir(docs_dir)
    (docs_dir / "spec.md").write_text("# Spec\n")

    return hook


def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# VAL-M2-002: clean_artifacts removes aged context day-dirs
# ---------------------------------------------------------------------------

class TestCleanArtifactsContextDirs:
    def test_removes_old_context_dir_keeps_fresh(self, tmp_path):
        from memory_core.tools.artifact_retention import clean_artifacts

        hook = _seed_artifact_tree(tmp_path)
        today = date.today().isoformat()
        old_date = (date.today() - timedelta(days=60)).isoformat()

        report = clean_artifacts(hook, days=30)

        assert not (hook / "contexts" / old_date).exists(), "old dir should be removed"
        assert (hook / "contexts" / today).exists(), "fresh dir should remain"
        assert any("contexts" in str(r) for r in report.removed)

    def test_removes_old_event_file_keeps_fresh(self, tmp_path):
        """VAL-M2-003: clean_artifacts removes aged event day-files."""
        from memory_core.tools.artifact_retention import clean_artifacts

        hook = _seed_artifact_tree(tmp_path)
        today = date.today().isoformat()
        old_date = (date.today() - timedelta(days=60)).isoformat()

        report = clean_artifacts(hook, days=30)

        assert not (hook / "events" / f"{old_date}.jsonl").exists()
        assert (hook / "events" / f"{today}.jsonl").exists()
        assert any("events" in str(r) for r in report.removed)


# ---------------------------------------------------------------------------
# VAL-M2-004: Boundary — exactly N days old is retained
# ---------------------------------------------------------------------------

class TestBoundaryExactlyNDays:
    def test_exactly_n_days_old_is_retained(self, tmp_path):
        from memory_core.tools.artifact_retention import clean_artifacts

        hook = _seed_artifact_tree(tmp_path)
        today = date.today()

        # Create a dir exactly 30 days old
        boundary_date = (today - timedelta(days=30)).isoformat()
        boundary_dir = hook / "contexts" / boundary_date
        _make_dir(boundary_dir)
        (boundary_dir / "snap.json").write_text("{}")
        _backdate(boundary_dir, 30)

        report = clean_artifacts(hook, days=30)

        assert boundary_dir.exists(), "exactly 30-day-old artifact must be retained"
        assert not any(boundary_date in str(r) for r in report.removed)

    def test_31_days_old_is_removed(self, tmp_path):
        from memory_core.tools.artifact_retention import clean_artifacts

        hook = _seed_artifact_tree(tmp_path)
        today = date.today()

        old_date = (today - timedelta(days=31)).isoformat()
        old_dir = hook / "contexts" / old_date
        _make_dir(old_dir)
        (old_dir / "snap.json").write_text("{}")
        _backdate(old_dir, 31)

        clean_artifacts(hook, days=30)

        assert not old_dir.exists(), "31-day-old artifact must be removed"


# ---------------------------------------------------------------------------
# VAL-M2-005: --dry-run makes zero filesystem mutations
# ---------------------------------------------------------------------------

class TestDryRun:
    def test_dry_run_no_filesystem_changes(self, tmp_path):
        from memory_core.tools.artifact_retention import clean_artifacts

        hook = _seed_artifact_tree(tmp_path)
        old_date = (date.today() - timedelta(days=60)).isoformat()

        old_ctx = hook / "contexts" / old_date
        old_evt = hook / "events" / f"{old_date}.jsonl"
        assert old_ctx.exists()
        assert old_evt.exists()

        report = clean_artifacts(hook, days=30, dry_run=True)

        # Report should list what would be removed
        assert len(report.removed) > 0
        # But nothing actually deleted
        assert old_ctx.exists(), "dry-run must not delete context dir"
        assert old_evt.exists(), "dry-run must not delete event file"


# ---------------------------------------------------------------------------
# VAL-M2-006 / VAL-M2-042: KB/docs/decisions never in cleanup scope
# ---------------------------------------------------------------------------

class TestKBDocsNeverTouched:
    def test_kb_docs_sha256_unchanged(self, tmp_path):
        from memory_core.tools.artifact_retention import clean_artifacts

        hook = _seed_artifact_tree(tmp_path)

        kb_file = tmp_path / "kb" / "decisions" / "dec1.md"
        docs_file = tmp_path / "docs" / "design" / "spec.md"
        kb_hash_before = _sha256(kb_file)
        docs_hash_before = _sha256(docs_file)

        clean_artifacts(hook, days=30)

        assert _sha256(kb_file) == kb_hash_before
        assert _sha256(docs_file) == docs_hash_before


# ---------------------------------------------------------------------------
# VAL-M2-007: Lifecycle events.jsonl rotation at >50MB
# ---------------------------------------------------------------------------

class TestLifecycleRotation:
    def test_rotation_when_over_50mb(self, tmp_path):
        from memory_core.tools.artifact_retention import (
            ROTATION_THRESHOLD,
            clean_artifacts,
        )

        hook = _seed_artifact_tree(tmp_path)
        events_file = hook / "events.jsonl"

        # Write >50MB of data
        with open(events_file, "wb") as f:
            f.write(b"x" * (ROTATION_THRESHOLD + 1))

        clean_artifacts(hook, days=30)

        assert not events_file.exists() or events_file.stat().st_size == 0, \
            "original events.jsonl should be rotated (gone or empty)"
        # Check archive exists
        archives = list(hook.glob("events-*.jsonl"))
        assert len(archives) >= 1, "at least one archive should exist"

    def test_no_rotation_when_under_threshold(self, tmp_path):
        from memory_core.tools.artifact_retention import clean_artifacts

        hook = _seed_artifact_tree(tmp_path)
        events_file = hook / "events.jsonl"
        original_size = events_file.stat().st_size

        clean_artifacts(hook, days=30)

        assert events_file.exists()
        assert events_file.stat().st_size == original_size


# ---------------------------------------------------------------------------
# VAL-M2-008: Lifecycle rotation is idempotent / non-clobbering
# ---------------------------------------------------------------------------

class TestRotationIdempotent:
    def test_rotation_does_not_overwrite_existing_archive(self, tmp_path):
        from memory_core.tools.artifact_retention import (
            ROTATION_THRESHOLD,
            clean_artifacts,
        )

        hook = _seed_artifact_tree(tmp_path)
        events_file = hook / "events.jsonl"

        # First rotation
        with open(events_file, "wb") as f:
            f.write(b"A" * (ROTATION_THRESHOLD + 1))

        clean_artifacts(hook, days=30)
        archives_first = list(hook.glob("events-*.jsonl"))
        assert len(archives_first) >= 1
        first_archive = archives_first[0]
        first_archive_hash = _sha256(first_archive)
        first_archive_name = first_archive.name

        # Second rotation with different content
        with open(events_file, "wb") as f:
            f.write(b"B" * (ROTATION_THRESHOLD + 1))

        clean_artifacts(hook, days=30)
        archives_second = list(hook.glob("events-*.jsonl"))
        assert len(archives_second) >= 2, "should have two archives (non-clobbering)"

        # First archive must be preserved (find by name, not index)
        first_archive_after = hook / first_archive_name
        assert first_archive_after.exists()
        assert _sha256(first_archive_after) == first_archive_hash, \
            "existing archive must not be overwritten"


# ---------------------------------------------------------------------------
# VAL-M2-010: metrics.jsonl is retained
# ---------------------------------------------------------------------------

class TestMetricsRetained:
    def test_metrics_jsonl_not_deleted(self, tmp_path):
        from memory_core.tools.artifact_retention import clean_artifacts

        hook = _seed_artifact_tree(tmp_path)
        metrics_file = hook / "metrics.jsonl"
        assert metrics_file.exists()

        clean_artifacts(hook, days=30)

        assert metrics_file.exists(), "metrics.jsonl must not be deleted"


# ---------------------------------------------------------------------------
# VAL-M2-011: Empty/missing target does not crash
# ---------------------------------------------------------------------------

class TestEmptyMissingTarget:
    def test_nonexistent_path_returns_empty_report(self, tmp_path):
        from memory_core.tools.artifact_retention import clean_artifacts

        nonexistent = tmp_path / "does_not_exist"
        report = clean_artifacts(nonexistent, days=30)

        assert report.removed == []
        assert report.rotated == []

    def test_empty_dir_returns_empty_report(self, tmp_path):
        from memory_core.tools.artifact_retention import clean_artifacts

        empty = tmp_path / "empty"
        empty.mkdir()

        report = clean_artifacts(empty, days=30)

        assert report.removed == []
        assert report.rotated == []


# ---------------------------------------------------------------------------
# VAL-M2-001: CLI entry point
# ---------------------------------------------------------------------------

class TestCLI:
    def test_cli_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.artifact_retention",
             "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "--target" in result.stdout
        assert "--days" in result.stdout
        assert "--dry-run" in result.stdout

    def test_cli_dry_run_on_tmp(self, tmp_path):
        hook = _seed_artifact_tree(tmp_path)
        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.artifact_retention",
             "--target", str(hook), "--days", "30", "--dry-run"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

    def test_cli_nonexistent_target_exits_zero(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-m", "memory_core.tools.artifact_retention",
             "--target", str(tmp_path / "nope"), "--days", "30"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Additional edge-case tests
# ---------------------------------------------------------------------------

class TestCleanupReport:
    def test_report_is_dataclass_like(self):
        from memory_core.tools.artifact_retention import CleanupReport

        report = CleanupReport(removed=["a", "b"], rotated=["c"], errors=[])
        assert report.removed == ["a", "b"]
        assert report.rotated == ["c"]
        assert report.errors == []


class TestNonDateContextDirs:
    def test_non_date_dir_not_removed(self, tmp_path):
        """Context subdirs that don't match YYYY-MM-DD pattern should be kept."""
        from memory_core.tools.artifact_retention import clean_artifacts

        hook = _seed_artifact_tree(tmp_path)
        custom_dir = hook / "contexts" / "custom-snapshot"
        _make_dir(custom_dir)
        _backdate(custom_dir, 90)

        clean_artifacts(hook, days=30)

        assert custom_dir.exists(), "non-date context dirs must not be removed"


class TestEventTypeFiltering:
    def test_non_jsonl_event_files_not_removed(self, tmp_path):
        """Event files not matching YYYY-MM-DD.jsonl should be kept."""
        from memory_core.tools.artifact_retention import clean_artifacts

        hook = _seed_artifact_tree(tmp_path)
        events_dir = hook / "events"

        # Create a non-date-pattern event file
        other_file = events_dir / "summary.txt"
        other_file.write_text("summary")
        _backdate(other_file, 90)

        clean_artifacts(hook, days=30)

        assert other_file.exists(), "non-date-pattern event files must not be removed"
