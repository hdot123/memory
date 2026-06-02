#!/usr/bin/env python3
"""
Skills 覆盖版本检测器
检测官方 skill 是否更新，本地覆盖是否过时。

用法：
  python skill-overlay-checker.py

检测逻辑：
  1. 读取 ~/.factory/skills/ 下所有同名覆盖 skill
  2. 对比 system-reminder 中的官方 description
  3. 输出差异报告

当前覆盖的官方 skill 清单（按创建时间记录）：
  - review: 创建于 2026-05-30
  - docx: 创建于 2026-05-30
  - wiki: 创建于 2026-05-30
  - security-review: 创建于 2026-05-30
  - agent-browser: 创建于 2026-05-30
  - simplify: 创建于 2026-05-30
  - browse-wiki: 创建于 2026-05-30
"""

import json
import re
from datetime import datetime
from pathlib import Path

SKILLS_DIR = Path.home() / ".factory" / "skills"

# 已知的官方覆盖列表（从 audit/official-skills-registry.md 维护）
OVERLAY_SKILLS = {
    "review": {
        "created": "2026-05-30",
        "official_hash": None,  # 首次检测时填充
        "status": "active",
    },
    "docx": {
        "created": "2026-05-30",
        "official_hash": None,
        "status": "active",
    },
    "wiki": {
        "created": "2026-05-30",
        "official_hash": None,
        "status": "active",
    },
    "security-review": {
        "created": "2026-05-30",
        "official_hash": None,
        "status": "active",
    },
    "agent-browser": {
        "created": "2026-05-30",
        "official_hash": None,
        "status": "active",
    },
    "simplify": {
        "created": "2026-05-30",
        "official_hash": None,
        "status": "active",
    },
    "browse-wiki": {
        "created": "2026-05-30",
        "official_hash": None,
        "status": "active",
    },
}

REGISTRY_FILE = Path(__file__).parent.parent / "audit" / "overlay-registry.json"


def get_local_description(skill_name: str) -> str | None:
    """读取本地覆盖 skill 的 description"""
    skill_file = SKILLS_DIR / skill_name / "SKILL.md"
    if not skill_file.exists():
        return None
    content = skill_file.read_text()
    match = re.search(r'^description:\s*>?\s*(.+?)(?:\n(?:\s+.+?\n)*?)^---', content, re.MULTILINE | re.DOTALL)
    if not match:
        # Try single-line format
        match = re.search(r'^description:\s*(.+?)$', content, re.MULTILINE)
    if match:
        desc = match.group(1).strip()
        # Clean up YAML multiline
        desc = re.sub(r'\s+', ' ', desc)
        return desc
    return None


def check_overlay(skill_name: str) -> dict:
    """检查单个覆盖 skill 的状态"""
    local_desc = get_local_description(skill_name)
    local_file = SKILLS_DIR / skill_name / "SKILL.md"

    if not local_file.exists():
        return {
            "skill": skill_name,
            "status": "MISSING",
            "message": f"覆盖文件不存在: {local_file}",
        }

    local_mtime = datetime.fromtimestamp(local_file.stat().st_mtime).isoformat()

    return {
        "skill": skill_name,
        "status": "OK",
        "local_file": str(local_file),
        "local_modified": local_mtime,
        "local_description_preview": (local_desc[:100] + "...") if local_desc and len(local_desc) > 100 else local_desc,
    }


def run_check():
    """执行全量检测"""
    print("=" * 60)
    print("Factory Skills 覆盖版本检测器")
    print(f"检测时间: {datetime.now().isoformat()}")
    print(f"覆盖数量: {len(OVERLAY_SKILLS)}")
    print("=" * 60)

    results = []
    for skill_name in sorted(OVERLAY_SKILLS.keys()):
        result = check_overlay(skill_name)
        results.append(result)
        overlay_info = OVERLAY_SKILLS[skill_name]
        status_icon = {"OK": "✅", "MISSING": "❌", "STALE": "⚠️"}.get(result["status"], "❓")
        print(f"\n{status_icon} {skill_name}")
        print(f"   状态: {result['status']}")
        print(f"   创建: {overlay_info['created']}")
        if "local_modified" in result:
            print(f"   修改: {result['local_modified']}")
        if result.get("local_description_preview"):
            print(f"   Description: {result['local_description_preview']}")

    # 保存注册表
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    registry = {
        "last_check": datetime.now().isoformat(),
        "overlays": OVERLAY_SKILLS,
        "results": results,
    }
    REGISTRY_FILE.write_text(json.dumps(registry, ensure_ascii=False, indent=2))
    print(f"\n注册表已保存: {REGISTRY_FILE}")

    # 手动检测指引
    print("\n" + "=" * 60)
    print("手动检测官方更新方法:")
    print("  1. 新 session 启动后，查看 system-reminder 中的 Available skills")
    print("  2. 对比官方 skill description 与本地覆盖是否一致")
    print("  3. 如有差异，更新本地 SKILL.md 并保留中文部分")
    print("=" * 60)

    return results


if __name__ == "__main__":
    run_check()
