#!/usr/bin/env python3
"""VAL-M2-009: Gateway no longer dual-writes full events.jsonl.

After processing a hook event, events/<today>.jsonl gains one line;
top-level events.jsonl gains zero lines. metrics.jsonl still works.
"""
from __future__ import annotations

import ast
import inspect
import textwrap
from pathlib import Path

import pytest

from memory_core.tools.memory_hook_impls import ArtifactSinkImpl

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fixed_datetime():
    """Return a datetime class that always returns a fixed time."""
    from datetime import datetime as real_datetime

    class FixedDatetime:
        @staticmethod
        def now():
            return real_datetime(2026, 7, 7, 12, 0, 0, 0)

    return FixedDatetime


# ---------------------------------------------------------------------------
# ArtifactSinkImpl tests
# ---------------------------------------------------------------------------

class TestArtifactSinkNoDualWrite:
    """VAL-M2-009: ArtifactSinkImpl only writes to daily sharded event log."""

    def test_daily_event_log_gets_line(self, tmp_path: Path) -> None:
        """VAL-M2-009: After sink.write(), events/<today>.jsonl gains one line."""
        sink = ArtifactSinkImpl(
            tmp_path / "contexts",
            tmp_path / "events.jsonl",
            datetime_module=_fixed_datetime(),
        )
        package = {"host": "factory", "event": "session-start", "status": "ok"}
        sink.write(package)

        daily_log = tmp_path / "events" / "2026-07-07.jsonl"
        assert daily_log.exists(), "daily sharded event log should exist"
        lines = daily_log.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1, f"expected 1 line in daily log, got {len(lines)}"

    def test_full_events_jsonl_not_written(self, tmp_path: Path) -> None:
        """VAL-M2-009: After sink.write(), top-level events.jsonl is NOT created."""
        sink = ArtifactSinkImpl(
            tmp_path / "contexts",
            tmp_path / "events.jsonl",
            datetime_module=_fixed_datetime(),
        )
        package = {"host": "factory", "event": "prompt-submit", "status": "ok"}
        sink.write(package)

        full_log = tmp_path / "events.jsonl"
        assert not full_log.exists(), (
            "full events.jsonl should NOT be created after sink.write()"
        )

    def test_full_events_jsonl_not_appended_if_preexists(self, tmp_path: Path) -> None:
        """VAL-M2-009: If events.jsonl pre-exists, sink.write() does NOT append."""
        full_log = tmp_path / "events.jsonl"
        full_log.write_text("", encoding="utf-8")
        original_size = full_log.stat().st_size

        sink = ArtifactSinkImpl(
            tmp_path / "contexts",
            tmp_path / "events.jsonl",
            datetime_module=_fixed_datetime(),
        )
        package = {"host": "factory", "event": "session-start", "status": "ok"}
        sink.write(package)

        after_size = full_log.stat().st_size
        assert after_size == original_size, (
            f"events.jsonl should not grow: before={original_size}, after={after_size}"
        )

    def test_multiple_writes_only_in_daily(self, tmp_path: Path) -> None:
        """VAL-M2-009: Multiple writes accumulate in daily log only."""
        sink = ArtifactSinkImpl(
            tmp_path / "contexts",
            tmp_path / "events.jsonl",
            datetime_module=_fixed_datetime(),
        )

        for i in range(3):
            sink.write({"host": "factory", "event": f"event-{i}", "status": "ok"})

        daily_log = tmp_path / "events" / "2026-07-07.jsonl"
        daily_lines = daily_log.read_text(encoding="utf-8").strip().splitlines()
        assert len(daily_lines) == 3, f"expected 3 lines in daily log, got {len(daily_lines)}"

        full_log = tmp_path / "events.jsonl"
        assert not full_log.exists(), "full events.jsonl should not exist"

    def test_legacy_event_log_ref_still_in_artifact_refs(self, tmp_path: Path) -> None:
        """legacy_event_log key still present in artifact_refs for backward compat."""
        sink = ArtifactSinkImpl(
            tmp_path / "contexts",
            tmp_path / "events.jsonl",
            datetime_module=_fixed_datetime(),
        )
        package = {"host": "factory", "event": "session-start", "status": "ok"}
        sink.write(package)

        # The package should still contain artifact_refs with legacy_event_log key
        assert "artifact_refs" in package
        assert "legacy_event_log" in package["artifact_refs"]

    def test_context_snapshot_still_written(self, tmp_path: Path) -> None:
        """Context snapshots should still be written normally."""
        sink = ArtifactSinkImpl(
            tmp_path / "contexts",
            tmp_path / "events.jsonl",
            datetime_module=_fixed_datetime(),
        )
        package = {"host": "factory", "event": "session-start", "status": "ok"}
        result = sink.write(package)

        assert "snapshot" in result
        snapshot_path = Path(result["snapshot"])
        assert snapshot_path.exists()


# ---------------------------------------------------------------------------
# Gateway write_artifacts fallback tests
# ---------------------------------------------------------------------------

class TestWriteArtifactsFallbackNoDualWrite:
    """VAL-M2-009: write_artifacts fallback does not write to full events.jsonl."""

    def test_fallback_does_not_write_full_events(self, tmp_path: Path, monkeypatch) -> None:
        """When write_artifacts fallback runs, events.jsonl is not created."""
        from datetime import datetime as real_datetime

        from memory_core.tools import memory_hook_gateway as gw

        artifact_root = tmp_path / "artifacts"
        context_root = artifact_root / "contexts"
        event_log = artifact_root / "events.jsonl"

        # Monkeypatch module-level constants used by the fallback path
        monkeypatch.setattr(gw, "CONTEXT_ROOT", context_root)
        monkeypatch.setattr(gw, "EVENT_LOG", event_log)

        class FixedDatetime:
            @staticmethod
            def now():
                return real_datetime(2026, 7, 7, 12, 0, 0, 0)

        monkeypatch.setattr(gw, "datetime", FixedDatetime)

        def failing_write(package):
            raise RuntimeError("synthetic sink failure")

        monkeypatch.setattr(gw, "_write_artifacts_via_sink", failing_write)

        package = {"host": "factory", "event": "session-start", "status": "ok"}
        gw.write_artifacts(package)

        full_log = artifact_root / "events.jsonl"
        assert not full_log.exists(), (
            "fallback write_artifacts should NOT create full events.jsonl"
        )

        daily_log = artifact_root / "events" / "2026-07-07.jsonl"
        assert daily_log.exists(), "daily sharded log should still be created"


# ---------------------------------------------------------------------------
# metrics.jsonl retention test
# ---------------------------------------------------------------------------

class TestMetricsJsonlRetained:
    """VAL-M2-009: metrics.jsonl is unaffected by the dedup change."""

    def test_metrics_jsonl_still_written(self, tmp_path: Path, monkeypatch) -> None:
        """metrics.jsonl should still be written independently of events dedup."""
        from memory_core.tools import memory_hook_metrics as metrics

        monkeypatch.delenv(metrics.ENV_DISABLE, raising=False)

        artifact_root = tmp_path / "artifacts"
        artifact_root.mkdir()

        result = metrics.emit_metrics(
            artifact_root=artifact_root,
            host="factory",
            event="session-start",
            package={"status": "ok", "event_count": 1, "size_bytes": 500},
        )
        assert result is not None

        metrics_file = artifact_root / metrics.METRICS_FILENAME
        assert metrics_file.exists(), "metrics.jsonl should still be written"
        lines = metrics_file.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1


# ---------------------------------------------------------------------------
# Source-level verification
# ---------------------------------------------------------------------------

class TestSourceNoFullEventsWrite:
    """VAL-M2-009: Source code does not contain events.jsonl write path."""

    def test_artifact_sink_does_not_open_event_log_for_write(self) -> None:
        """ArtifactSinkImpl.write() does not open self._event_log for append."""
        source = inspect.getsource(ArtifactSinkImpl.write)
        # The method should not contain a pattern that opens self._event_log for append
        assert "self._event_log.open" not in source, (
            "ArtifactSinkImpl.write() should not open self._event_log for writing"
        )

    def test_no_events_jsonl_append_in_sink_write(self) -> None:
        """Verify no code path in ArtifactSinkImpl.write opens events.jsonl."""
        source = inspect.getsource(ArtifactSinkImpl.write)
        source = textwrap.dedent(source)
        tree = ast.parse(source)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Attribute) and func.attr == "open":
                    # Check if any argument to open() is an 'a' mode
                    for kw in node.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                            if kw.value.value == "a":
                                # Check if it's opening self._event_log
                                if isinstance(func.value, ast.Attribute):
                                    if func.value.attr == "_event_log":
                                        pytest.fail(
                                            "ArtifactSinkImpl.write() opens "
                                            "self._event_log in append mode"
                                        )
