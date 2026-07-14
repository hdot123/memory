"""Tests for telemetry fixes - VAL-EVENT-001 and VAL-EVENT-002.

Verifies:
- session_end_logger.py writes 'session-end' (kebab-case) not 'session_ended' (snake_case)
- No snake_case event names remain in memory_core/tools/ source code
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

repo_root = Path(__file__).resolve().parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))


class TestSessionEndEventNaming:
    """VAL-EVENT-001: Session-end event uses kebab-case."""

    def test_session_end_event_uses_kebab_case(self):
        """Verify metrics record event field is 'session-end' not 'session_ended'.

        This test mocks append_metrics_record and verifies the event field
        uses kebab-case naming convention.
        """
        from memory_core.tools import session_end_logger

        # Mock the streaming extraction to return sample session info
        sample_info = {
            "session_id": "test-session-123",
            "duration_seconds": 120.5,
            "input_tokens": 5000,
            "output_tokens": 3000,
            "total_tool_calls": 15,
        }

        captured_records = []

        def capture_metrics_record(path, record):
            captured_records.append(record)
            return True

        with patch.object(
            session_end_logger,
            "_extract_session_info_streaming",
            return_value=sample_info,
        ), patch.object(
            session_end_logger,
            "_write_daily_log",
        ), patch.object(
            session_end_logger,
            "append_metrics_record",
            side_effect=capture_metrics_record,
        ), patch.object(
            session_end_logger,
            "_resolve_metrics_path",
            return_value=Path("/tmp/test_metrics.jsonl"),
        ), patch.object(
            session_end_logger,
            "_set_timeout",
        ):
            # Call main with minimal args
            test_args = [
                "session_end_logger.py",
                "--session-dir", "/tmp/test-session",
                "--session-id", "test-session-123",
                "--project-root", "/tmp/test-project",
            ]

            with patch.object(sys, "argv", test_args):
                # Create dummy session dir and jsonl file for the test
                session_dir = Path("/tmp/test-session")
                session_dir.mkdir(parents=True, exist_ok=True)
                jsonl_path = session_dir / "test-session-123.jsonl"
                jsonl_path.write_text("{}\n")

                try:
                    session_end_logger.main()
                finally:
                    # Cleanup
                    if jsonl_path.exists():
                        jsonl_path.unlink()
                    if session_dir.exists():
                        session_dir.rmdir()

        # Verify append_metrics_record was called
        assert len(captured_records) > 0, "append_metrics_record should have been called"

        # Verify the event field is 'session-end' (kebab-case)
        event_value = captured_records[0].get("event")
        assert event_value == "session-end", (
            f"Event field should be 'session-end' (kebab-case), "
            f"but got '{event_value}' (snake_case)"
        )


class TestNoSnakeCaseEventNames:
    """VAL-EVENT-002: No snake_case event names in codebase."""

    def test_no_snake_case_event_names_in_source(self):
        """Grep-verify no snake_case event names exist in memory_core/tools/.

        Searches for patterns like:
        - "event": "session_ended"
        - "event": "session_started"
        - "event": "pre_tool_use"
        """
        tools_dir = repo_root / "memory_core" / "tools"

        snake_case_patterns = [
            '"event": "session_ended"',
            '"event": "session_started"',
            '"event": "pre_tool_use"',
            '"event":"session_ended"',
            '"event":"session_started"',
            '"event":"pre_tool_use"',
        ]

        violations = []

        for py_file in tools_dir.glob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for pattern in snake_case_patterns:
                if pattern in content:
                    violations.append(f"{py_file.name}: found {pattern}")

        assert len(violations) == 0, (
            "Found snake_case event names in source code:\n"
            + "\n".join(violations)
            + "\nAll event names should use kebab-case (e.g., 'session-end')"
        )
