# -*- coding: utf-8 -*-
"""启动自检：资源包完整性（计划 P0-1）。

要防的具体事故：资源 OTA 走"全量删除 + 复制"分支时，若包内少了 `agent/`，用户侧
agent 会被清空 → 程序看起来正常、任务全部失效。事后排查成本极高，所以启动时先用
**stat 级检查**（不做哈希，< 5 ms）报出来，并把清单缺失落到 agent 日志。

只报告、不删除、不改动、不阻断启动——自检本身出问题不能变成新的故障源。
清单由 `scripts/build_resource_zip.py` 在打包时生成（`resource/base/pipeline/.manifest.json`）。
"""
from __future__ import annotations

import json
import os

#: 缺一不可的 agent 模块（main.py 自身不列，它正在运行）
REQUIRED_AGENT_FILES = (
    "mfalog.py", "auto_battle.py", "soc_actions.py",
    "crisis_mission.py", "past_event.py", "imaging.py", "evidence.py",
)

MANIFEST_REL = os.path.join("resource", "base", "pipeline", ".manifest.json")


def check(root: str = None) -> dict:
    """返回 {'ok': bool, 'problems': [...], 'notes': [...], 'checked': int}。"""
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    problems, notes, checked = [], [], 0

    agent_dir = os.path.join(root, "agent")
    for fn in REQUIRED_AGENT_FILES:
        checked += 1
        if not os.path.exists(os.path.join(agent_dir, fn)):
            problems.append(f"缺少 agent/{fn}")

    manifest_path = os.path.join(root, MANIFEST_REL)
    if not os.path.exists(manifest_path):
        notes.append("未找到 pipeline 清单（开发期正常，发版包应包含）")
    else:
        try:
            with open(manifest_path, encoding="utf-8") as f:
                manifest = json.load(f)
            files = manifest.get("files") or {}
            missing = [rel for rel in files
                       if not os.path.exists(os.path.join(root, *rel.split("/")))]
            checked += len(files)
            if missing:
                problems.append(
                    f"pipeline 清单缺 {len(missing)} 个文件（示例: {', '.join(missing[:3])}）")
        except Exception as e:  # 清单坏掉只提示，不影响启动
            notes.append(f"pipeline 清单解析失败: {e!r}")

    return {"ok": not problems, "problems": problems, "notes": notes, "checked": checked}


def run(root: str = None) -> dict:
    """执行自检并写日志（异常一律吞掉）。"""
    try:
        result = check(root)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "problems": [f"自检异常: {e!r}"], "notes": [], "checked": 0}
    try:
        from mfalog import mfa_err, mfa_log, mfa_warn
        if result["problems"]:
            mfa_err("自检", "selfcheck", "资源包不完整：" + "；".join(result["problems"]),
                    problems=result["problems"])
        else:
            mfa_log("自检", "selfcheck", "ok",
                    f"完整性自检通过（检查 {result['checked']} 项）")
        for n in result["notes"]:
            mfa_warn("自检", "selfcheck", n)
    except Exception:
        pass
    return result
