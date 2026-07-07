#!/usr/bin/env python3
"""PostToolUse real-time knowledge capture (Layer 2).

Triggered by the gateway on every post-tool-use event. When the Agent writes
to ``memory/kb/lessons/`` or ``memory/kb/decisions/``, this module reads the
project's ``adapter.toml [global_kb]`` routing configuration and copies the
file to ``~/.memory/global-kb/pending/`` immediately — without waiting for
session-end.

This is the second defense layer: even if SessionEnd never fires (idle
timeout, SIGTERM, platform issue), knowledge is captured at write time.

Usage (called from memory_hook_gateway.py main):
    python posttooluse_capture.py < stdin JSON payload

The payload is the raw Factory PostToolUse hook payload:
    {
        "tool_name": "Write",
        "tool_input": {"file_path": "/path/to/file.md", ...},
        ...
    }
"""
from __future__ import annotations

import json
import os
import re
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Match lessons/ and decisions/ subdirectories under memory/kb/
_CAPTURE_PATTERN = re.compile(r"memory/kb/(lessons|decisions)/.+\.md$")

TIMEOUT_SECONDS = 2


def _set_timeout(seconds: int) -> None:
    def _handler(signum: int, frame: Any) -> None:
        sys.exit(0)

    signal.signal(signal.SIGALRM, _handler)
    signal.alarm(seconds)


def _load_project_root() -> Path | None:
    original_cwd = os.environ.get("MEMORY_HOOK_ORIGINAL_CWD")
    if original_cwd:
        return Path(original_cwd).expanduser().resolve()
    factory_dir = os.environ.get("FACTORY_PROJECT_DIR")
    if factory_dir:
        return Path(factory_dir).expanduser().resolve()
    try:
        return Path.cwd().resolve()
    except Exception:
        return None


def should_capture(payload: dict[str, Any], project_root: Path) -> Path | None:
    """Check if a PostToolUse payload wrote to memory/kb/lessons/ or decisions/.

    Returns the absolute file path if it should be captured, None otherwise.
    """
    # Normalize Factory payload: merge tool_input into top level
    if "tool_input" in payload:
        tool_input = payload.get("tool_input", {})
        for k, v in tool_input.items():
            payload.setdefault(k, v)

    file_path = payload.get("file_path", "")

    if not file_path:
        return None

    # Resolve to absolute path
    p = Path(file_path)
    if not p.is_absolute():
        p = project_root / p
    p = p.resolve()

    # Check if path matches memory/kb/lessons/ or decisions/
    try:
        rel = str(p.relative_to(project_root))
    except ValueError:
        return None

    if not _CAPTURE_PATTERN.search(rel):
        return None

    # File must exist on disk (PostToolUse = after tool completed)
    if not p.exists():
        return None

    return p


def _parse_global_kb_config(adapter_path: Path) -> tuple[bool, str | None]:
    """Parse [global_kb] section from adapter.toml.

    Returns (enabled, root_path). If section missing or disabled, returns
    (False, None).
    """
    if not adapter_path.exists():
        return False, None

    try:
        text = adapter_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False, None

    # Find [global_kb] section
    in_section = False
    enabled = False
    root = None

    for line in text.splitlines():
        stripped = line.strip()

        # Section header
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped == "[global_kb]"
            continue

        if not in_section:
            continue

        # enabled = true/false
        m = re.match(r"^enabled\s*=\s*(true|false)", stripped, re.IGNORECASE)
        if m:
            enabled = m.group(1).lower() == "true"
            continue

        # root = "path"
        m = re.match(r'^root\s*=\s*"([^"]+)"', stripped)
        if m:
            root = m.group(1)
            continue

    if not enabled:
        return False, None

    # Expand ~ in root
    if root:
        root = os.path.expanduser(root)

    return enabled, root


def capture_to_global_kb(
    file_path: Path,
    project_root: Path,
) -> dict[str, Any]:
    """Read project adapter.toml routing config and capture file to pending/.

    Returns a result dict with status: captured / idempotent / skipped / error.
    """
    adapter_path = project_root / "memory" / "system" / "adapter.toml"
    enabled, root = _parse_global_kb_config(adapter_path)

    if not enabled or not root:
        return {"status": "skipped", "reason": "global_kb not enabled or root missing"}

    global_kb_root = Path(root)
    pending_dir = global_kb_root / "pending"

    # Generate pending filename
    project_name = project_root.name
    category = file_path.parent.name  # "lessons" or "decisions"
    pending_filename = f"{project_name}_{category}_{file_path.name}"
    pending_path = pending_dir / pending_filename

    # Idempotent: skip if already exists
    if pending_path.exists():
        return {"status": "idempotent", "path": str(pending_path)}

    # Read source content
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return {"status": "error", "reason": str(e)}

    # Build metadata frontmatter
    captured_at = datetime.now().isoformat()
    metadata_lines = [
        "---",
        f"source_project: {project_root}",
        f"source_file: {file_path.relative_to(project_root)}",
        f"captured_at: {captured_at}",
        "capture_layer: posttooluse",
        "---",
        "",
    ]

    # Ensure pending dir exists
    pending_dir.mkdir(parents=True, exist_ok=True)

    # Write to pending/
    try:
        with pending_path.open("w", encoding="utf-8") as f:
            f.write("\n".join(metadata_lines))
            f.write(content)
    except OSError as e:
        return {"status": "error", "reason": str(e)}

    return {"status": "captured", "path": str(pending_path)}


def main() -> int:
    """PostToolUse capture entry point.

    Reads stdin JSON payload, checks if write targets lessons/decisions,
    and if so captures to global KB pending/ via routing config.
    """
    _set_timeout(TIMEOUT_SECONDS)

    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return 0

    project_root = _load_project_root()
    if project_root is None:
        return 0

    # Not a memory-managed project
    if not (project_root / "memory" / "system").exists():
        return 0

    file_path = should_capture(payload, project_root)
    if file_path is None:
        return 0

    result = capture_to_global_kb(file_path, project_root)

    # Log result to stderr for debugging (stdout stays clean for Factory)
    if result.get("status") == "captured":
        print(
            f"[posttooluse-capture] captured {file_path.name} -> {result['path']}",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
