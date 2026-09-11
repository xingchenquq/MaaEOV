# -*- coding: utf-8 -*-
"""往期活动 —— 往日行动调令计数与战斗次数设置（MaaEOV 整合版，兼容 MaaFw 4.5.6）。

与 MaaEOV1 原版的关键修正：
- 移除 context.run_recognition("OCR"/"TemplateMatch", ...) 调用。
  原写法依赖名为 "OCR"/"TemplateMatch" 的 pipeline 节点，而 MaaEOV 没有这类节点，
  会导致 run_recognition 返回 None（开发记忆踩坑点 #3）。
- 调令数改为在 pipeline 节点「记录往日行动调令数」上直接用 OCR 识别，
  由 CustomAction 通过 argv.reco_detail 读取识别结果。
- 加号按钮改用固定坐标点击（已校准的快速完成弹窗坐标），不再做 TemplateMatch。

坐标基于 1280×720 基准分辨率。
"""

import re
import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition


# 模块级状态：在 agent 子进程内持久，记录最近一次识别到的往日行动调令数
_TICKET_COUNT: int = 0

# ROI：往期活动卡片界面显示"往日行动调令"数字的区域
_TICKET_ROI = [351, 92, 173, 48]

# 快速完成弹窗：滑块最左端坐标（点一下次数默认归为 1）
_SLIDER_LEFT_X, _SLIDER_LEFT_Y = 575, 457

# 加号固定坐标（从 1280×720 快速完成弹窗实测；TemplateMatch 失败时兜底）
_PLUS_X, _PLUS_Y = 1000, 458

# 点击节奏（秒）—— 太快会导致界面来不及响应 / 次数点错
_SLIDER_SETTLE_SEC = 1.0    # 点滑块最左后，等界面把次数归 1
_PLUS_INTERVAL_SEC = 0.8    # 相邻两次「点加号」之间的间隔
_AFTER_SET_SEC = 0.8        # 设置完成后、进入下一步（点击出发）前的缓冲

# OCR 常把 0 读成字母 O/o 或全角 〇/０ —— 统一归一化为 '0'
_ZERO_LOOKALIKES = str.maketrans({"O": "0", "o": "0", "〇": "0", "０": "0"})


def _click(context: Context, x: int, y: int):
    try:
        context.tasker.controller.post_click(int(x), int(y)).wait()
    except Exception as e:
        print(f"[往期活动] 点击失败 ({x},{y}): {e}")


def _parse_ticket(text: str) -> int:
    """从 OCR 文本里解析出 0~6 的整数；失败返回 0。"""
    if not text:
        return 0
    text = text.strip().translate(_ZERO_LOOKALIKES)
    m = re.search(r"\d+", text)
    return int(m.group(0)) if m else 0


@AgentServer.custom_action("记录往日行动调令数")
class RecordPastEventTickets(CustomAction):
    """在往期活动卡片界面 OCR 调令数并写入模块全局，供后续节点使用。

    识别在 pipeline 节点「记录往日行动调令数」上完成（OCR），
    这里通过 argv.reco_detail 读取结果，无需再调用 run_recognition。
    OCR 把 0 读成 O/o 时按 0 处理（见 _parse_ticket 的归一化）。
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        global _TICKET_COUNT
        n = 0
        try:
            detail = argv.reco_detail
            if detail and detail.best_result:
                n = _parse_ticket(detail.best_result.text or "")
        except Exception as e:
            print(f"[往期活动] 读取调令 OCR 结果失败: {e}")
        _TICKET_COUNT = max(0, min(6, n))
        print(f"[往期活动] 记录到往日行动调令数: {_TICKET_COUNT}")
        return True


@AgentServer.custom_recognition("调令为零")
class NoPastEventTickets(CustomRecognition):
    """战斗前检测：已记录的「往日行动调令」<= 0 时命中（0 或 OCR 读成 O 都算 0）。

    命中 → pipeline 直接走「退出往期活动失败」两下返回主界面并结束任务；
    未命中（>0）→ 返回 None，pipeline 落到 next 的第二项「选择往期活动」正常流程。
    """

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        global _TICKET_COUNT
        if _TICKET_COUNT <= 0:
            print(f"[往期活动] 战斗前检测：调令数={_TICKET_COUNT}（0 或 O）→ 返回主界面，结束")
            return CustomRecognition.AnalyzeResult(
                box=(0, 0, 1, 1), detail=f"tickets={_TICKET_COUNT}"
            )
        print(f"[往期活动] 战斗前检测：调令数={_TICKET_COUNT} > 0 → 继续扫荡")
        return None


@AgentServer.custom_action("设置往期活动战斗次数")
class SetPastEventSweepCount(CustomAction):
    """在快速完成弹窗内按已记录的调令数设置战斗次数。

    - 先点滑块最左端，使次数默认=1。
    - 再点"加号"(N-1)次，使次数=N。
    - 若 N==0，返回 False，由 pipeline 的 next-fallback 结束任务。
    加号用固定坐标点击（已校准），不依赖 TemplateMatch。
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        global _TICKET_COUNT
        n = _TICKET_COUNT
        print(f"[往期活动] 开始设置战斗次数，当前调令数={n}")

        if n <= 0:
            print("[往期活动] 无可用调令，停止扫荡")
            return False

        # 1) 滑块拉到最左，次数默认归 1（等界面刷新）
        _click(context, _SLIDER_LEFT_X, _SLIDER_LEFT_Y)
        time.sleep(_SLIDER_SETTLE_SEC)

        # 2) 点击加号 (n-1) 次（每次之间留足间隔，避免点太快漏计）
        for i in range(n - 1):
            print(f"[往期活动] 第 {i + 1}/{n - 1} 次点击加号 @({_PLUS_X},{_PLUS_Y})")
            _click(context, _PLUS_X, _PLUS_Y)
            time.sleep(_PLUS_INTERVAL_SEC)

        # 3) 留一点缓冲再交给下一步（点击出发）
        time.sleep(_AFTER_SET_SEC)
        print(f"[往期活动] 战斗次数已设置为 {n}")
        return True
