#!/usr/bin/env python3
"""PreToolUse guard for memory-core ownership protection.

Reads stdin JSON payload, classifies the target path, and outputs
{"decision":"block"/"allow","reason":"..."} JSON to stdout.

Exit codes:
- 0: allow
- 2: block
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from memory_core.ownership import (
    classify_agents_md_block,
    classify_owned_path,
    load_memory_ownership,
)

# ---------------------------------------------------------------------------
# 文件类型黑名单常量
# ---------------------------------------------------------------------------

FORBIDDEN_SUFFIXES: tuple[str, ...] = (
    ".sql",
    ".bak",
    ".sqlite",
    ".db",
    ".dump",
    ".sql.gz",
)

FORBIDDEN_DIRS: frozenset[str] = frozenset({"backups"})

# ---------------------------------------------------------------------------
# M2: 只读命令放行常量
# ---------------------------------------------------------------------------

READONLY_WHITELIST: frozenset[str] = frozenset({
    "grep", "cat", "ls", "du", "find", "wc", "head", "tail",
    "file", "stat", "diff", "rg", "ruff", "python3", "pytest",
    "memory-validate", "memory-verify-consumer",
})

WRITE_KEYWORDS: tuple[str, ...] = (
    ">", ">>", "tee", "sed -i", "cp", "mv", "rm", "mkdir",
    "touch", "chmod", "chown", "eval", "bash", "sh",
)


def _is_readonly_command(command: str) -> bool:
    """判断命令是否为纯只读操作（M2 只读放行）。

    返回 True 表示是只读命令，可以放行。
    条件：
    1. 首 token 在 READONLY_WHITELIST 中
    2. 命令中不含 WRITE_KEYWORDS
    """
    cmd_stripped = command.strip()
    if not cmd_stripped:
        return False

    # 提取首 token
    first_token = cmd_stripped.split()[0]

    # 检查首 token 是否在白名单中
    if first_token not in READONLY_WHITELIST:
        return False

    # 管道符检测：含管道的命令不判定为只读
    # 防止 cat f | python3 -c "open('x','w')" 等管道写绕过
    if "|" in cmd_stripped:
        return False

    # 特殊处理：python3/python -c 命令需要检测代码中的写操作
    if first_token in ("python3", "python"):
        if " -c " in cmd_stripped or cmd_stripped.endswith(" -c"):
            # 检测 Python 写操作模式
            python_write_patterns = [
                r'open\s*\([^)]*["\']w["\']',  # open(..., "w")
                r'open\s*\([^)]*["\']a["\']',  # open(..., "a")
                r'\.write_text\s*\(',          # Path.write_text()
                r'\.write_bytes\s*\(',         # Path.write_bytes()
                r'\.unlink\s*\(',              # Path.unlink()
                r'\.rmdir\s*\(',               # Path.rmdir()
                r'os\.remove\s*\(',            # os.remove()
                r'os\.unlink\s*\(',            # os.unlink()
                r'shutil\.rmtree\s*\(',        # shutil.rmtree()
            ]
            for pattern in python_write_patterns:
                if re.search(pattern, cmd_stripped):
                    return False
            # 如果没有检测到写操作模式，认为是只读
            return True

    # 检查是否包含写操作关键词
    cmd_lower = cmd_stripped.lower()

    # 先检查重定向操作符（> 和 >>）
    # 简单检查：只要包含 > 或 >> 就认为是写操作
    if ">>" in cmd_lower or ">" in cmd_lower:
        return False

    # 检查其他写操作关键词
    for keyword in WRITE_KEYWORDS:
        if keyword in (">", ">>"):
            continue  # 已经在上面处理过
        elif keyword == "sed -i":
            # 匹配 sed 后跟 -i（可能有空格）
            if re.search(r'\bsed\s+-i\b', cmd_lower):
                return False
        elif keyword == "tee":
            # 匹配 tee 命令（作为独立命令，不是其他命令的一部分）
            if re.search(r'\btee\b', cmd_lower):
                return False
        elif keyword == "sh":
            # sh 作为独立命令，排除 -sh 等 flag 后缀（如 du -sh）
            if re.search(r'(?<!-)\bsh\b', cmd_lower):
                return False
        else:
            # 其他关键词：使用词边界匹配
            if re.search(rf'\b{keyword}\b', cmd_lower):
                return False

    return True


def _check_file_type_block(file_path: str) -> dict[str, str] | None:
    """检查文件路径是否命中文件类型黑名单。

    返回 block 结果 dict 表示被拦截，返回 None 表示放行。
    MEMORY_HOOK_FORCE=1 时跳过检查。
    """
    if os.environ.get("MEMORY_HOOK_FORCE") == "1":
        return None

    p = Path(file_path)
    name = p.name.lower()

    # 检查目录黑名单
    for part in p.parts:
        if part.lower() in FORBIDDEN_DIRS:
            return {
                "decision": "block",
                "reason": f"文件类型禁止入库：目录 {part} 被禁止",
            }

    # 检查后缀黑名单（.sql.gz 需要先匹配复合后缀）
    if name.endswith(".sql.gz"):
        return {
            "decision": "block",
            "reason": "文件类型禁止入库：.sql.gz",
        }
    for suffix in FORBIDDEN_SUFFIXES:
        if suffix == ".sql.gz":
            continue  # 已处理
        if name.endswith(suffix):
            return {
                "decision": "block",
                "reason": f"文件类型禁止入库：{suffix}",
            }

    return None


def _load_project_root() -> Path | None:
    """Determine project root from environment."""
    # Try FACTORY_PROJECT_DIR first
    factory_dir = os.environ.get("FACTORY_PROJECT_DIR")
    if factory_dir:
        return Path(factory_dir).expanduser().resolve()

    # Try MEMORY_HOOK_ORIGINAL_CWD
    original_cwd = os.environ.get("MEMORY_HOOK_ORIGINAL_CWD")
    if original_cwd:
        return Path(original_cwd).expanduser().resolve()

    # Fallback to current working directory
    try:
        return Path.cwd().resolve()
    except Exception:
        return None


def _extract_path_from_execute(command: str) -> list[str]:
    """Extract target paths from Execute command.

    Statically parses various command patterns:
    - mv/git mv → destination
    - rm → target
    - cp → destination
    - mkdir/touch → target
    - python -c → look for open() calls
    - shell redirect (> >>) → target
    - heredoc/tee → target
    - rsync → destination
    - node -e → look for write operations
    - shell glob patterns → extract literal portions
    - relative paths → resolved against project root later
    """
    paths: list[str] = []
    command = command.strip()

    # Skip empty commands
    if not command:
        return paths

    # mv / git mv: target is the last argument
    mv_match = re.match(r"^(?:git\s+)?mv\s+(.+)$", command, re.IGNORECASE)
    if mv_match:
        args = _split_shell_args(mv_match.group(1))
        if len(args) >= 2:
            paths.append(args[-1])  # destination is last
        return paths

    # rm: targets are all arguments
    rm_match = re.match(r"^rm\s+(?:-[a-zA-Z]+\s+)?(.+)$", command, re.IGNORECASE)
    if rm_match:
        args = _split_shell_args(rm_match.group(1))
        for arg in args:
            if not arg.startswith("-"):
                paths.append(arg)
        return paths

    # cp: target is the last argument
    cp_match = re.match(r"^cp\s+(?:-[a-zA-Z]+\s+)?(.+)$", command, re.IGNORECASE)
    if cp_match:
        args = _split_shell_args(cp_match.group(1))
        if len(args) >= 2:
            paths.append(args[-1])  # destination is last
        return paths

    # rsync: target is the last argument
    rsync_match = re.match(r"^rsync\s+(?:-[a-zA-Z]+\s+)*(.+)$", command, re.IGNORECASE)
    if rsync_match:
        args = _split_shell_args(rsync_match.group(1))
        if len(args) >= 2:
            paths.append(args[-1])  # destination is last
        return paths

    # mkdir: targets are all non-flag arguments
    mkdir_match = re.match(r"^mkdir\s+(?:-[a-zA-Z]+\s+)?(.+)$", command, re.IGNORECASE)
    if mkdir_match:
        args = _split_shell_args(mkdir_match.group(1))
        for arg in args:
            if not arg.startswith("-"):
                paths.append(arg)
        return paths

    # touch: targets are all non-flag arguments
    touch_match = re.match(r"^touch\s+(?:-[a-zA-Z]+\s+)?(.+)$", command, re.IGNORECASE)
    if touch_match:
        args = _split_shell_args(touch_match.group(1))
        for arg in args:
            if not arg.startswith("-"):
                paths.append(arg)
        return paths

    # python -c: look for open() calls
    python_match = re.match(r"^python\d*\s+(?:-[a-zA-Z]+\s+)*-c\s+['\"]?(.+)$", command, re.IGNORECASE | re.DOTALL)
    if python_match:
        code = python_match.group(1)
        # Find open() calls with file paths
        open_matches = re.findall(r"open\s*\(\s*['\"]([^'\"]+)['\"]", code)
        paths.extend(open_matches)
        # Also check for pathlib Path writes
        path_write_matches = re.findall(r"Path\s*\(\s*['\"]([^'\"]+)['\"]\)", code)
        paths.extend(path_write_matches)
        return paths

    # node -e: look for write operations (fs.writeFileSync, fs.writeFileSync, etc.)
    node_match = re.match(r"^node\s+(?:-[a-zA-Z]+\s+)*-e\s+['\"]?(.+)$", command, re.IGNORECASE | re.DOTALL)
    if node_match:
        code = node_match.group(1)
        # fs.writeFileSync('path', ...) / fs.writeFileSync('path', ...)
        fs_write_matches = re.findall(
            r"(?:writeFileSync|writeFile|appendFileSync|appendFile)\s*\(\s*['\"]([^'\"]+)['\"]",
            code,
        )
        paths.extend(fs_write_matches)
        # require('fs').writeFileSync patterns
        req_matches = re.findall(
            r"require\s*\(\s*['\"]fs['\"]\s*\)\s*\.\s*(?:writeFileSync|writeFile)\s*\(\s*['\"]([^'\"]+)['\"]",
            code,
        )
        paths.extend(req_matches)
        return paths

    # shell redirect (> >>): target file
    redirect_match = re.search(r"[12]?>[>]?\s*['\"]?([^\s;|&<>'\"]+)['\"]?", command)
    if redirect_match:
        paths.append(redirect_match.group(1))
        return paths

    # tee: look for file arguments after tee
    tee_match = re.match(r".*tee\s+(?:-[a-zA-Z]+\s+)?([^|&;]+)", command, re.IGNORECASE)
    if tee_match:
        args = _split_shell_args(tee_match.group(1))
        for arg in args:
            if not arg.startswith("-"):
                paths.append(arg)
        return paths

    # heredoc: look for cat << EOF patterns
    heredoc_match = re.match(r".*cat\s+.*<<\s*\w+\s*>?\s*([^|&;]+)", command, re.IGNORECASE)
    if heredoc_match:
        target = heredoc_match.group(1).strip()
        if target:
            paths.append(target)
        return paths

    # dd: look for of= target
    dd_match = re.match(r"^dd\s+.*of=['\"]?([^'\"\s]+)['\"]?", command, re.IGNORECASE)
    if dd_match:
        paths.append(dd_match.group(1))
        return paths

    # install command: target is last argument
    install_match = re.match(r"^install\s+(?:-[a-zA-Z]+\s+)*(.+)$", command, re.IGNORECASE)
    if install_match:
        args = _split_shell_args(install_match.group(1))
        if len(args) >= 2:
            paths.append(args[-1])  # destination is last
        return paths

    # ln/symlink: target is last argument
    ln_match = re.match(r"^ln\s+(?:-[a-zA-Z]+\s+)*(.+)$", command, re.IGNORECASE)
    if ln_match:
        args = _split_shell_args(ln_match.group(1))
        if len(args) >= 2:
            paths.append(args[-1])  # destination is last
        return paths

    return paths


def _split_shell_args(arg_string: str) -> list[str]:
    """Split shell argument string, respecting quoted strings.

    Handles:
    - Double-quoted strings
    - Single-quoted strings
    - Simple space separation
    - Glob characters preserved as-is (handled later by _is_uncertain_path)
    """
    args: list[str] = []
    current: list[str] = []
    in_quote: str | None = None
    i = 0
    while i < len(arg_string):
        ch = arg_string[i]
        if in_quote:
            if ch == in_quote:
                in_quote = None
            else:
                current.append(ch)
        elif ch in ('"', "'"):
            in_quote = ch
        elif ch in (' ', '\t'):
            if current:
                args.append("".join(current))
                current = []
        else:
            current.append(ch)
        i += 1
    if current:
        args.append("".join(current))
    return args


def _contains_owned_root_string(command: str) -> bool:
    """Check if command contains strings that might target owned paths."""
    owned_indicators = [
        "memory/",
        "memory/system/",
        "memory\\",
        "AGENTS.md",
    ]
    cmd_lower = command.lower()
    return any(indicator in cmd_lower for indicator in owned_indicators)


def _is_uncertain_path(path: str) -> bool:
    """Check if path is uncertain (contains wildcards, variables, etc.)."""
    uncertain_patterns = [
        r"\*",  # wildcards
        r"\?",
        r"\$",  # variables
        r"`",   # command substitution
        r"\$\(",
        r"\{",  # brace expansion
        r"\[",  # bracket expansion
    ]
    return any(re.search(p, path) for p in uncertain_patterns)


def _expand_env_vars(path: str) -> str:
    """Expand common environment variables in path strings.

    Only expands known safe variables; unknown $VAR patterns are left as-is.
    """
    env_map = {
        "$HOME": os.environ.get("HOME", ""),
        "$PWD": "",
        "$PROJECT_DIR": os.environ.get("FACTORY_PROJECT_DIR", ""),
        "~": os.environ.get("HOME", ""),
    }
    result = path
    for var, value in env_map.items():
        if var in result:
            result = result.replace(var, value)
    return result


def _parse_multiedit_paths(payload: dict[str, Any]) -> list[str]:
    """Extract file paths from MultiEdit payload."""
    paths: list[str] = []
    edits = payload.get("edits", [])
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict):
                file_path = edit.get("file_path")
                if file_path:
                    paths.append(file_path)
    return paths


def _parse_task_paths(payload: dict[str, Any]) -> list[str]:
    """Extract potential owned path references from Task payload."""
    paths: list[str] = []
    prompt = payload.get("prompt", "")
    if not isinstance(prompt, str):
        return paths

    # Look for owned path patterns in the prompt
    patterns = [
        r"memory/[\w\-/]+",
        r"AGENTS\.md",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, prompt)
        paths.extend(matches)

    return paths


def _build_ownership_policy_block(project_root: Path) -> str:
    """Build ownership policy block for Task tool injection.

    Returns a markdown block listing protected domains, resources,
    and forbidden instructions that should be injected into the
    task prompt to enforce ownership policy on sub-agents.
    """
    ownership = load_memory_ownership(project_root)

    lines: list[str] = [
        "<!-- ownership-policy-injection -->",
        "## Ownership Protection Policy (auto-injected)",
        "",
        "The following domains and resources are protected by ownership policy.",
        "Do NOT modify, move, rename, delete, or overwrite any of these.",
        "",
        "### Protected Domains",
    ]
    for domain in ownership.domains:
        lines.append(f"- `{domain.path}/` ({domain.level.name}) — {domain.description}")
    lines.append("")
    lines.append("### Protected Resources")
    for resource in ownership.resources:
        lines.append(f"- `{resource.path}` ({resource.level.name}) — {resource.description}")
    lines.append("")
    lines.append("### Forbidden Instructions")
    lines.append("- Do not modify, move, rename, delete, or overwrite any protected domain or resource.")
    lines.append("- Do not attempt to weaken ownership protection (e.g., editing ownership.toml).")
    lines.append("- Do not bypass this policy via shell commands, scripts, or indirect writes.")
    lines.append("<!-- /ownership-policy-injection -->")
    return "\n".join(lines)


def _get_project_root_for_task(project_root: Path) -> Path:
    """Get the fixed project root for Task tool handling.

    Always returns the project root from environment, not PWD.
    This prevents cwd drift when sub-agents change directories.
    """
    # Always use the resolved project root from _load_project_root
    # Never follow PWD changes that may happen during task execution
    return project_root.resolve()


def _classify_tool_use(payload: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Classify a tool use and return decision."""
    # Normalize payload: Factory hooks wrap tool params in tool_input, standalone tests don't
    if "tool_input" in payload:
        # Factory hook format: merge tool_input into top-level for convenience
        tool_input = payload.get("tool_input", {})
        for k, v in tool_input.items():
            payload.setdefault(k, v)

    tool_name = payload.get("tool_name", "")
    file_path = payload.get("file_path")

    if not tool_name:
        return {"decision": "allow", "reason": "No tool_name specified"}

    ownership = load_memory_ownership(project_root)

    # Handle different tool types
    if tool_name in ("Write", "Edit"):
        if not file_path:
            return {"decision": "allow", "reason": f"{tool_name} without file_path"}

        # Special handling for AGENTS.md (5b.4: diff-aware)
        if Path(file_path).name == "AGENTS.md":
            # Try content_before/content_after first, fall back to old_str/new_str
            content_before = payload.get("content_before") or payload.get("old_str")
            # Write tool uses 'content', Edit tool uses 'content_after' or 'new_str'
            content_after = payload.get("content_after") or payload.get("content") or payload.get("new_str")

            # Check if AGENTS.md already exists
            full_path = project_root / file_path
            file_exists = full_path.exists()

            # If file exists and no content_before, it's a full overwrite (scenario 4)
            if file_exists and content_before is None:
                return {
                    "decision": "block",
                    "reason": "Cannot determine modification scope - full overwrite uncertain (AGENTS.md exists)",
                    "scenario": 4,
                }

            agents_result = classify_agents_md_block(file_path, content_before, content_after)
            return {
                "decision": agents_result["decision"],
                "reason": agents_result["reason"],
                "scenario": agents_result.get("scenario"),
            }

        # 文件类型黑名单检查（优先于路径归属检查）
        ft_block = _check_file_type_block(file_path)
        if ft_block is not None:
            return ft_block

        result = classify_owned_path(file_path, ownership, project_root)
        if hasattr(result, "level"):
            return {
                "decision": "block",
                "reason": f"Protected {result.level.name} path: {result.reason}",
            }
        return {"decision": "allow", "reason": result.reason}

    elif tool_name == "MultiEdit":
        paths = _parse_multiedit_paths(payload)
        if not paths:
            return {"decision": "allow", "reason": "MultiEdit with no file paths"}

        # 5b.5: Check each path individually and collect per-item results
        item_results: list[dict[str, Any]] = []
        has_block = False

        edits = payload.get("edits", [])
        for i, edit in enumerate(edits):
            if not isinstance(edit, dict):
                continue
            path = edit.get("file_path", "")
            if not path:
                continue

            # 5b.4: AGENTS.md diff-aware for MultiEdit items
            if Path(path).name == "AGENTS.md":
                content_before = edit.get("content_before") or edit.get("old_str")
                content_after = edit.get("content_after") or edit.get("new_str")

                # Check if AGENTS.md exists on disk
                full_path = project_root / path
                file_exists = full_path.exists()

                if file_exists and content_before is None:
                    item_results.append({
                        "path": path,
                        "decision": "block",
                        "reason": "Cannot determine modification scope - full overwrite uncertain (AGENTS.md exists)",
                        "scenario": 4,
                    })
                    has_block = True
                    continue

                agents_result = classify_agents_md_block(path, content_before, content_after)
                item_results.append({
                    "path": path,
                    "decision": agents_result["decision"],
                    "reason": agents_result["reason"],
                    "scenario": agents_result.get("scenario"),
                })
                if agents_result["decision"] == "block":
                    has_block = True
                continue

            # 文件类型黑名单检查（优先于路径归属检查）
            ft_block = _check_file_type_block(path)
            if ft_block is not None:
                item_results.append({
                    "path": path,
                    "decision": "block",
                    "reason": ft_block["reason"],
                })
                has_block = True
                continue

            # Normal path classification
            result = classify_owned_path(path, ownership, project_root)
            if hasattr(result, "level"):
                item_results.append({
                    "path": path,
                    "decision": "block",
                    "reason": f"Protected {result.level.name} path: {result.reason}",
                })
                has_block = True
            else:
                item_results.append({
                    "path": path,
                    "decision": "allow",
                    "reason": result.reason,
                })

        if has_block:
            blocked = [r for r in item_results if r["decision"] == "block"]
            blocked_paths = [r["path"] for r in blocked]
            return {
                "decision": "block",
                "reason": f"MultiEdit blocked items: {', '.join(blocked_paths)}",
                "item_results": item_results,
            }
        return {
            "decision": "allow",
            "reason": "No owned paths in MultiEdit",
            "item_results": item_results,
        }

    elif tool_name == "NotebookEdit":
        notebook_path = payload.get("notebook_path")
        if not notebook_path:
            return {"decision": "allow", "reason": "NotebookEdit without notebook_path"}

        result = classify_owned_path(notebook_path, ownership, project_root)
        if hasattr(result, "level"):
            return {
                "decision": "block",
                "reason": f"Protected notebook: {result.reason}",
            }
        return {"decision": "allow", "reason": result.reason}

    elif tool_name == "Execute":
        command = payload.get("command", "")
        if not command:
            return {"decision": "allow", "reason": "Execute without command"}

        # Git operations: allow git add/commit/push for GitHub workflow
        cmd_parts = command.strip().split()
        if cmd_parts and cmd_parts[0] == "git":
            if len(cmd_parts) >= 2 and cmd_parts[1] in ("add", "commit", "push"):
                return {
                    "decision": "allow",
                    "reason": "Git operations (add/commit/push) are allowed for GitHub workflow",
                }

        # M2: 只读命令放行检查
        # 首 token 在白名单且无写操作 → 放行
        # 首 token 在白名单但含写操作 → 拦截（防止绕过保护）
        first_token = command.strip().split()[0] if command.strip() else ""
        if first_token in READONLY_WHITELIST:
            if _is_readonly_command(command):
                return {
                    "decision": "allow",
                    "reason": "Read-only command with whitelisted first token and no write operations",
                }
            else:
                # 白名单首 token 但含写操作关键词，直接拦截
                return {
                    "decision": "block",
                    "reason": f"Read-whitelisted command '{first_token}' contains write operation keywords",
                }

        # Extract target paths from command
        paths = _extract_path_from_execute(command)

        if paths:
            # Check each extracted path
            for path in paths:
                # Check for uncertainty on the raw path BEFORE expansion
                if _is_uncertain_path(path):
                    # Check if command contains owned root strings
                    if _contains_owned_root_string(command):
                        return {
                            "decision": "block",
                            "reason": f"Uncertain path '{path}' targeting owned resources",
                        }
                    continue

                # Expand environment variables for classification
                expanded = _expand_env_vars(path)

                # 文件类型黑名单检查（优先于路径归属检查）
                ft_block = _check_file_type_block(expanded)
                if ft_block is not None:
                    return ft_block

                # Handle relative paths: resolve against project root
                check_path = expanded
                if not Path(expanded).is_absolute():
                    check_path = expanded

                result = classify_owned_path(check_path, ownership, project_root)
                if hasattr(result, "level"):
                    return {
                        "decision": "block",
                        "reason": f"Execute targets protected path '{path}': {result.reason}",
                    }
            return {"decision": "allow", "reason": "No owned paths in Execute targets"}
        else:
            # Could not parse - check if command contains owned root strings
            if _contains_owned_root_string(command):
                return {
                    "decision": "block",
                    "reason": "Cannot parse Execute command but contains owned resource references",
                }
            return {"decision": "allow", "reason": "No owned paths detected in Execute"}

    elif tool_name == "Task":
        # Task tool: no path pre-scan. Sub-agent file operations are guarded
        # by their own PreToolUse events. Scanning prompt text for keywords
        # causes false positives (e.g. mentioning AGENTS.md in instructions).
        return {"decision": "allow", "reason": "Task tool — sub-agent operations guarded individually"}

    # Unknown tool - allow
    return {"decision": "allow", "reason": f"Unknown tool: {tool_name}"}


def main() -> int:
    """Main entry point for PreToolUse guard."""
    # MEMORY_HOOK_FORCE does NOT bypass PreToolUse guard
    # This is intentional - PreToolUse is a hard guard

    # Read JSON payload from stdin
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    except Exception:
        return 0

    # Normalize payload: Factory hooks wrap tool params in tool_input
    # Standalone tests pass fields at top level
    if "tool_input" in payload:
        tool_input = payload.get("tool_input", {})
        for k, v in tool_input.items():
            payload.setdefault(k, v)

    # Get project root
    project_root = _load_project_root()
    if project_root is None:
        return 0

    # Check if memory/system exists (if not, this isn't a memory-managed project)
    if not (project_root / "memory" / "system").exists():
        return 0

    # Classify the tool use
    result = _classify_tool_use(payload, project_root)

    # Output: always output JSON so Factory and tests can parse it.
    # Allow = minimal, Block = full reason.
    print(json.dumps(result))

    if result["decision"] == "block":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
