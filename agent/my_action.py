# -*- coding: utf-8 -*-
"""通用自定义动作。

地图拖动：
    MaaFW 内置 Swipe 走 minitouch 通道，对「胜负一线 / 升腾仪式」的关卡地图拖动
    实测完全无效（Action.Succeeded 但画面不动，2026-11-24）；而 adb `input swipe`
    手动验证有效。这里用 subprocess 直接调 adb 完成拖动。
    adb 路径与地址读 config/maa_pi_config.json（MFA 实例配置，单一来源）。

pipeline 用法：
    "action": {
        "type": "Custom",
        "param": {
            "custom_action": "地图拖动",
            "begin": [1150, 400],
            "end": [480, 400],
            "duration": 600
        }
    }
坐标基于 1280×720 基准分辨率。
"""

import json
import os
import subprocess
import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from mfalog import mfa_log, mfa_err

_MODULE = "MyAction"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 地图拖动后惯性收尾的额外等待（毫秒），与节点的 post_wait_freezes 叠加
_SWIPE_SETTLE_MS = 1800


@AgentServer.custom_action("my_action_111")
class MyCustomAction(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:

        mfa_log(_MODULE, "my_action_111", "info", "my_action_111 is running!")

        return True


def _load_adb_config():
    """从 MFA 实例配置读 adb 路径与地址；失败返回 (None, None)。"""
    for name in ("config/maa_pi_config.json", "config/config.json"):
        path = os.path.join(ROOT, name)
        try:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
            adb_cfg = cfg.get("adb") or {}
            adb_path = adb_cfg.get("adb_path")
            addr = adb_cfg.get("address")
            if adb_path and addr:
                return adb_path, addr
        except Exception:  # noqa: BLE001
            continue
    return None, None


@AgentServer.custom_action("地图拖动")
class MapSwipe(CustomAction):
    """用 adb `input swipe` 拖动关卡地图（绕开 minitouch 拖动无效的问题）。"""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        param = argv.param if isinstance(argv.param, dict) else {}
        begin = param.get("begin") or [1150, 400]
        end = param.get("end") or [480, 400]
        duration = int(param.get("duration") or 600)

        adb_path, addr = _load_adb_config()
        if not adb_path or not addr:
            mfa_err(_MODULE, "地图拖动", "config/maa_pi_config.json 里缺 adb_path / address")
            return False

        # 确保 adb server 已连接该设备（沙箱里 server 可能刚被重启）
        subprocess.run([adb_path, "start-server"], capture_output=True, timeout=15)
        subprocess.run([adb_path, "connect", addr], capture_output=True, timeout=15)

        cmd = [
            adb_path, "-s", addr, "shell", "input", "swipe",
            str(int(begin[0])), str(int(begin[1])),
            str(int(end[0])), str(int(end[1])),
            str(duration),
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=duration / 1000 + 20)
        except Exception as e:  # noqa: BLE001
            mfa_err(_MODULE, "地图拖动", f"adb input swipe 执行失败: {e}")
            return False
        if r.returncode != 0:
            mfa_err(_MODULE, "地图拖动",
                    f"adb input swipe 返回 {r.returncode}: {r.stderr.decode(errors='replace')[:200]}")
            return False

        # 等惯性收尾，避免后续 OCR 抓到滑动中的糊帧
        time.sleep(_SWIPE_SETTLE_MS / 1000)
        mfa_log(_MODULE, "地图拖动", "info",
                f"swipe {begin} -> {end} ({duration}ms) done")
        return True
