#!/usr/bin/env python3
"""Verification script for routing rule injection feature."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.getcwd())

from memory_core.tools.init_project_memory import (
    MEMORY_HOOK_BEGIN_MARKER,
    MEMORY_HOOK_END_MARKER,
    init_project_memory,
    template_agents_md_block,
)

tmp = Path(tempfile.mkdtemp())
subprocess.run(["git", "init"], cwd=tmp, capture_output=True, check=True)

print("=== VAL-INJECT-001: Memory Hook block contains three-layer routing after create ===")
result = init_project_memory(tmp, mode="create")
assert result["success"] is True
content = (tmp / "AGENTS.md").read_text()
assert "Layer 2" in content or "~/.memory/global-kb/" in content
assert "Layer 3" in content or "<project>/memory/kb/" in content
begin = content.index(MEMORY_HOOK_BEGIN_MARKER)
end = content.index(MEMORY_HOOK_END_MARKER) + len(MEMORY_HOOK_END_MARKER)
block = content[begin:end]
assert "Layer 2" in block or "~/.memory/global-kb/" in block
assert "Layer 3" in block or "<project>/memory/kb/" in block
print("PASSED")

print("\n=== VAL-INJECT-002: Routing reference survives idempotent update ===")
assert "路由规则" in (tmp / "AGENTS.md").read_text()
result = init_project_memory(tmp, mode="update")
assert result["success"] is True
content = (tmp / "AGENTS.md").read_text()
assert "Layer 2" in content or "~/.memory/global-kb/" in content
assert "Layer 3" in content or "<project>/memory/kb/" in content
print("PASSED")

print("\n=== VAL-INJECT-003: Adopt mode preserves existing unmarked AGENTS.md ===")
tmp2 = Path(tempfile.mkdtemp())
subprocess.run(["git", "init"], cwd=tmp2, capture_output=True, check=True)
agents = tmp2 / "AGENTS.md"
agents.write_text("# Custom Agents\n\nMy custom content.")
result = init_project_memory(tmp2, mode="adopt")
assert result["success"] is True
assert agents.read_text() == "# Custom Agents\n\nMy custom content."
assert MEMORY_HOOK_BEGIN_MARKER not in agents.read_text()
print("PASSED")

print("\n=== VAL-INJECT-004: Repair mode updates marked blocks only ===")
result = init_project_memory(tmp, mode="repair")
assert result["success"] is True
content = (tmp / "AGENTS.md").read_text()
assert "Layer 2" in content or "~/.memory/global-kb/" in content
assert "Layer 3" in content or "<project>/memory/kb/" in content
begin = content.index(MEMORY_HOOK_BEGIN_MARKER)
end = content.index(MEMORY_HOOK_END_MARKER)
block = content[begin:end]
assert "Layer 2" in block or "~/.memory/global-kb/" in block
print("PASSED")

print("\n=== VAL-PATH-001: Consumer paths are three-layer architecture ===")
block = template_agents_md_block()
assert ("Layer 2" in block or "~/.memory/global-kb/" in block), "Should reference Layer 2 global-kb"
assert ("Layer 3" in block or "<project>/memory/kb/" in block), "Should reference Layer 3 project kb"
assert "memory_core/" not in block
print("PASSED")

print("\n=== VAL-PATH-002: System-level global directory exists after init ===")
assert (tmp / "memory" / "system" / "kb" / "global").exists() or (tmp / "memory" / "system" / "kb" / "global").is_dir()
assert (tmp / "project-map" / "INDEX.md").exists()
print("PASSED")

print("\n=== VAL-TEST-002: Memory Hook block contains three-layer routing reference ===")
block = template_agents_md_block()
assert ("Layer 2" in block or "~/.memory/global-kb/" in block)
assert ("Layer 3" in block or "<project>/memory/kb/" in block)
assert "project-map/INDEX.md" in block
print("PASSED")

shutil.rmtree(tmp)
shutil.rmtree(tmp2)
print("\n=== ALL VALIDATION ASSERTIONS PASSED ===")
