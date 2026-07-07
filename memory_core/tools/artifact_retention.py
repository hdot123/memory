"""Artifact retention engine for memory hook products.

Provides:
- ``clean_artifacts(target, days, dry_run)`` programmatic API
- ``memory-retention-cleanup`` CLI entry point

Rules:
- contexts/YYYY-MM-DD/: delete day dirs older than *days* (strict >)
- events/YYYY-MM-DD.jsonl: delete day files older than *days* (strict >)
- events.jsonl: rotate to events-YYYYMM.jsonl when >50 MB (non-clobbering)
- metrics.jsonl: never touched
- KB/docs/decisions: never in cleanup scope
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

# 50 MB threshold for lifecycle rotation
ROTATION_THRESHOLD: int = 50 * 1024 * 1024

# Pattern for day dirs: YYYY-MM-DD
_DAY_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Pattern for day event files: YYYY-MM-DD.jsonl
_DAY_EVT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.jsonl$")


@dataclass
class CleanupReport:
    """Summary of a cleanup run."""

    removed: list[str] = field(default_factory=list)
    rotated: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "removed": self.removed,
            "rotated": self.rotated,
            "errors": self.errors,
        }


def _parse_date(name: str) -> date | None:
    """Parse YYYY-MM-DD string, returning None on failure."""
    try:
        return date.fromisoformat(name)
    except (ValueError, TypeError):
        return None


def _file_age_days(path: Path, now: date) -> int:
    """Return age in days based on mtime."""
    try:
        mtime = path.stat().st_mtime
        from datetime import datetime, timezone
        mtime_date = datetime.fromtimestamp(mtime, tz=timezone.utc).date()
        return (now - mtime_date).days
    except OSError:
        return 0


def _rotate_lifecycle_events(hook_dir: Path, dry_run: bool, report: CleanupReport) -> None:
    """Rotate lifecycle events.jsonl if it exceeds ROTATION_THRESHOLD.

    Renames to events-YYYYMM.jsonl.  If that archive already exists,
    appends a numeric suffix to avoid overwriting.
    """
    events_file = hook_dir / "events.jsonl"
    if not events_file.is_file():
        return

    try:
        size = events_file.stat().st_size
    except OSError:
        return

    if size <= ROTATION_THRESHOLD:
        return

    # Determine archive name
    from datetime import datetime
    now = datetime.now()
    base_name = f"events-{now.strftime('%Y%m')}.jsonl"
    archive_path = hook_dir / base_name

    # Non-clobbering: if archive exists, add suffix
    if archive_path.exists():
        suffix = 1
        while True:
            candidate = hook_dir / f"events-{now.strftime('%Y%m')}-{suffix}.jsonl"
            if not candidate.exists():
                archive_path = candidate
                break
            suffix += 1

    if dry_run:
        report.rotated.append(str(events_file))
        return

    try:
        # Move events.jsonl -> archive
        events_file.rename(archive_path)
        # Create fresh empty events.jsonl
        events_file.write_text("")
        report.rotated.append(str(archive_path))
    except OSError as exc:
        report.errors.append(f"rotation failed: {exc}")


def clean_artifacts(
    target: Path,
    days: int = 30,
    dry_run: bool = False,
) -> CleanupReport:
    """Clean up aged hook artifacts under *target*.

    *target* is expected to be the ``artifacts/memory-hook`` directory
    (or any directory containing ``contexts/`` and ``events/``).

    Args:
        target: Root of the hook artifact tree.
        days: Delete artifacts strictly older than this many days.
        dry_run: If True, report what would be deleted without touching FS.

    Returns:
        A ``CleanupReport`` with removed, rotated, and errors lists.
    """
    report = CleanupReport()
    target = Path(target)

    if not target.exists():
        return report

    today = date.today()
    cutoff = today - timedelta(days=days)  # strictly older than cutoff => remove

    # --- contexts/YYYY-MM-DD/ ---
    contexts_dir = target / "contexts"
    if contexts_dir.is_dir():
        for child in sorted(contexts_dir.iterdir()):
            if not child.is_dir():
                continue
            if not _DAY_DIR_RE.match(child.name):
                continue
            parsed = _parse_date(child.name)
            if parsed is None:
                continue
            if parsed < cutoff:
                # Strictly older: parsed must be before cutoff
                if dry_run:
                    report.removed.append(str(child))
                else:
                    try:
                        shutil.rmtree(child)
                        report.removed.append(str(child))
                    except OSError as exc:
                        report.errors.append(f"rm {child}: {exc}")

    # --- events/YYYY-MM-DD.jsonl ---
    events_dir = target / "events"
    if events_dir.is_dir():
        for child in sorted(events_dir.iterdir()):
            if not child.is_file():
                continue
            if not _DAY_EVT_RE.match(child.name):
                continue
            date_part = child.stem  # YYYY-MM-DD
            parsed = _parse_date(date_part)
            if parsed is None:
                continue
            if parsed < cutoff:
                if dry_run:
                    report.removed.append(str(child))
                else:
                    try:
                        child.unlink()
                        report.removed.append(str(child))
                    except OSError as exc:
                        report.errors.append(f"rm {child}: {exc}")

    # --- lifecycle events.jsonl rotation ---
    _rotate_lifecycle_events(target, dry_run, report)

    # metrics.jsonl is intentionally never touched
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    """CLI entry point: ``memory-retention-cleanup``."""
    parser = argparse.ArgumentParser(
        prog="memory-retention-cleanup",
        description="Clean up aged hook artifacts (contexts/ day-dirs, "
                    "events/ day-files) and rotate oversized lifecycle events.jsonl.",
    )
    parser.add_argument(
        "--target",
        type=str,
        required=True,
        help="Path to the hook artifact root (e.g. artifacts/memory-hook).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Delete artifacts strictly older than this many days (default: 30).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Report what would be deleted without modifying the filesystem.",
    )

    args = parser.parse_args(argv)
    target = Path(args.target)
    report = clean_artifacts(target, days=args.days, dry_run=args.dry_run)

    # Print summary as JSON
    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
