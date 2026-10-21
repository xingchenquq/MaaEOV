# -*- coding: utf-8 -*-
"""危机行动 —— 危机行动调令计数检测 + 战斗次数设置（与往期活动同范式，见 past_event.py）。

流程：
- pipeline 节点「识别危机行动调令数」用 OCR 识别界面右上角的危机行动调令数量，
  由 CustomAction 通过 argv.reco_detail 读取识别结果并写入模块全局。
- CustomRecognition「危机行动调令为零」在已记录数量 <= 0 时命中，
  pipeline 据此走「CrisisMissionTicketsSkipped」直接成功结束（跳过全部后续流程，
  不触发任何战斗）；> 0 时返回 None，pipeline 落到 next 的后续项进入正常扫荡。
- 进入关卡详情页后，CustomAction「设置危机行动战斗次数」在扫荡弹窗内按已记录调令数
  设置战斗次数（滑块拉到最左归 1，再点加号 N-1 次），随后由 Shared 的「点击出发」
  一次性确认，一次扫完所有次数后返回主界面（与往期活动「一次完成」同范式，而非逐次循环）。
"""

import re
import time

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition

from mfalog import mfa_log, mfa_err, mfa_warn

_MODULE = "危机行动"

# 模块级状态：在 agent 子进程内持久，记录最近一次识别到的危机行动调令数
_TICKET_COUNT: int = 0

# OCR 常把 0 读成字母 O/o 或全角 〇/０ —— 统一归一化为 '0'
_ZERO_LOOKALIKES = str.maketrans({"O": "0", "o": "0", "〇": "0", "０": "0"})


#: 调令数量上限。pipeline 注释（CrisisMissionTickets.json「识别危机行动调令数」）
#: 明确 OCR roi 覆盖「调令数 0-6」，且下游按 N-1 次点加号设战斗次数。
_MAX_TICKETS = 6


def _parse_ticket(text: str) -> int:
    """从 OCR 文本里解析出非负整数；失败返回 0。**不做钳制**（见 _clamp_tickets）。"""
    if not text:
        return 0
    text = text.strip().translate(_ZERO_LOOKALIKES)
    m = re.search(r"\d+", text)
    return int(m.group(0)) if m else 0


def _clamp_tickets(n) -> int:
    """把调令数钳到 0.._MAX_TICKETS。

    OCR 把「5」读成「50」时，若不设上限会按 49 次点加号（v1.14.7 前的缺陷，
    见 2026-10-20 代码评审第 1 条）。按上限截断是"多按几次无害加号"的最优降级，
    比直接判失败（跳过整个任务）损失更小。
    """
    try:
        n = int(n)
    except (TypeError, ValueError):
        return 0
    return max(0, min(_MAX_TICKETS, n))


@AgentServer.custom_action("记录危机行动调令数")
class RecordCrisisMissionTickets(CustomAction):
    """在危机行动关卡界面 OCR 右上角调令数并写入模块全局，供后续节点使用。

    识别在 pipeline 节点「识别危机行动调令数」上完成（OCR），
    这里通过 argv.reco_detail 读取结果，无需再调用 run_recognition。
    OCR 把 0 读成 O/o 时按 0 处理（见 _parse_ticket 的归一化）。
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        global _TICKET_COUNT
        n = 0
        try:
            detail = argv.reco_detail
            if detail and detail.best_result:
                raw = _parse_ticket(detail.best_result.text or "")
                n = _clamp_tickets(raw)
                if raw > _MAX_TICKETS:
                    mfa_warn(_MODULE, "read_ticket",
                             f"OCR 读数 {raw} 超出合理范围 0-{_MAX_TICKETS}，按上限处理（疑误读）",
                             raw=raw, phase="读取调令")
        except Exception as e:
            mfa_err(_MODULE, "read_ticket", "危机行动调令 OCR 读取失败", error=e, phase="读取调令")
        _TICKET_COUNT = max(0, n)
        mfa_log(_MODULE, "read_ticket", "ok", f"已进入危机行动界面，识别到调令数 = {_TICKET_COUNT}", count=_TICKET_COUNT, phase="读取调令")
        return True


@AgentServer.custom_recognition("危机行动调令为零")
class NoCrisisMissionTickets(CustomRecognition):
    """战斗前检测：已记录的「危机行动调令」<= 0 时命中（0 或 OCR 读成 O 都算 0）。

    命中 → pipeline 走「CrisisMissionTicketsSkipped」直接成功结束（跳过全部后续流程）；
    未命中（>0）→ 返回 None，pipeline 落到 next 的后续项进入正常扫荡流程。
    """

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        global _TICKET_COUNT
        if _TICKET_COUNT <= 0:
            mfa_log(_MODULE, "check_ticket", "skip", f"调令为 0（含读成 O / 识别失败兜底），不触发战斗，直接跳过并退出到主界面", count=_TICKET_COUNT, phase="判定")
            return CustomRecognition.AnalyzeResult(
                box=(0, 0, 1, 1), detail=f"tickets={_TICKET_COUNT}"
            )
        mfa_log(_MODULE, "check_ticket", "ok", f"调令 = {_TICKET_COUNT} > 0，进入扫荡流程", count=_TICKET_COUNT, phase="判定")
        return None


# 快速完成弹窗：滑块最左端坐标（点一下次数默认归为 1）。
# 与往期活动 past_event.py 同款游戏 UI，坐标通用。
_SLIDER_LEFT_X, _SLIDER_LEFT_Y = 575, 457

# 加号固定坐标（1280×720 快速完成弹窗实测；TemplateMatch 失败时兜底）。
_PLUS_X, _PLUS_Y = 1000, 458

# 点击节奏（秒）—— 太快会导致界面来不及响应 / 次数点错
_SLIDER_SETTLE_SEC = 1.0    # 点滑块最左后，等界面把次数归 1
_PLUS_INTERVAL_SEC = 0.8     # 相邻两次「点加号」之间的间隔
_AFTER_SET_SEC = 0.8         # 设置完成后、点击出发前的缓冲


def _click(context: Context, x: int, y: int):
    try:
        context.tasker.controller.post_click(int(x), int(y)).wait()
    except Exception as e:
        mfa_err(_MODULE, "click", f"点击失败 ({x},{y})", error=e)


@AgentServer.custom_action("设置危机行动战斗次数")
class SetCrisisMissionSweepCount(CustomAction):
    """在快速完成弹窗内按已记录的调令数设置战斗次数（与往期活动同范式）。

    - 先点滑块最左端，使次数默认=1。
    - 再点"加号"(N-1)次，使次数=N（N = 已记录的危机行动调令数）。
    - 若 N<=0，返回 False，由 pipeline 的 next-fallback 直接结束任务（跳过扫荡）。
    加号用固定坐标点击（已校准），不依赖 TemplateMatch。
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        global _TICKET_COUNT
        n = _TICKET_COUNT
        mfa_log(_MODULE, "set_sweep", "info", f"开始设置战斗次数：调令数 = {n}，滑块归 1 后点加号 {max(0, n - 1)} 次", count=n, phase="扫荡设置")

        if n <= 0:
            mfa_warn(_MODULE, "set_sweep", "调令数 <= 0，停止扫荡并退出到主界面", phase="扫荡设置")
            return False

        # 1) 滑块拉到最左，次数默认归 1（等界面刷新）
        _click(context, _SLIDER_LEFT_X, _SLIDER_LEFT_Y)
        time.sleep(_SLIDER_SETTLE_SEC)

        # 2) 点击加号 (n-1) 次（每次之间留足间隔，避免点太快漏计）
        for i in range(n - 1):
            mfa_log(_MODULE, "set_sweep", "info", f"点击加号 {i + 1}/{n - 1} 次 @({_PLUS_X},{_PLUS_Y})", idx=i + 1, total=n - 1, phase="扫荡设置")
            _click(context, _PLUS_X, _PLUS_Y)
            time.sleep(_PLUS_INTERVAL_SEC)

        # 3) 留一点缓冲再交给下一步（点击出发）
        time.sleep(_AFTER_SET_SEC)
        mfa_log(_MODULE, "set_sweep", "ok", f"战斗次数已设置为 {n}，随后点击出发", count=n, phase="扫荡设置")
        return True
