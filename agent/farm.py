# -*- coding: utf-8 -*-
"""清体力（Farm）自定义识别。

FarmStaminaShort：关卡详情页判「当前体力 < 本次消耗」→ 命中，交给 pipeline 收尾。

背景（2026-11-13 实机复现，debug/task_runs/清体力_fail.png）：
  `FarmOutOfStamina` 的判据是 OCR 顶部「下次恢复时间」倒计时，只覆盖体力见底（0 附近）的情况。
  「有体力但不够打这一把」——实测体力 14、关卡消耗 20——游戏**不显示倒计时**，
  于是原判据 miss，`FarmFromLevel.next` 全部未命中，扫荡完一轮后空转 130s 判 failed。

判据取两处读数做比较，任一读不出就不判定（宁可 miss 也不误判提前收尾）：
  · 右上角当前体力（紧邻「+」按钮）
  · 右下「出发 ⚡N」的消耗值
"""
import re

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JRecognitionType, JOCR

from auto_battle import _screencap
from mfalog import mfa_log, mfa_warn

_MODULE = "Farm"


@AgentServer.custom_recognition("FarmStaminaShort")
class FarmStaminaShort(CustomRecognition):
    """体力不足（但没见底）→ 命中。

    只在关卡详情页有意义：那里才有「出发 ⚡N」。其它界面读不出消耗值 → 自然 miss。
    """

    # 右上角当前体力「⚡17」。2026-11-13 20:49 全屏 OCR 实测：'17' @ [1169,29,25,16]，
    # 左边的资源数 '20,300' @ [1020,22,69,28]，ROI 左边界必须 >1090 才不会读成 20300。
    STAMINA_ROI = (1163, 22, 42, 30)
    # 右下「出发 ⚡20」。实测 '⚡20' @ [1181,653,64,39]，OCR 会把闪电当成数字读成 '920'，
    # 所以读数后要按 mod100 归一（见 _read_first_number 的 mod100 参数）。
    COST_ROI = (1178, 648, 78, 50)
    ZOOM = 4

    # 合理性区间：读超范围说明框到了相邻数字（如把 20,300 读成 20300），整条作废
    STAMINA_RANGE = (1, 999)
    COST_RANGE = (1, 99)

    def analyze(self, context, argv):
        img = getattr(argv, "image", None)
        if img is None:
            img = _screencap(context)
        if img is None:
            mfa_warn(_MODULE, "stamina_short", "取帧失败（argv.image 与 adb 均不可用）→ 不判定")
            return None

        cur = self._read_first_number(context, img, self.STAMINA_ROI)
        cost = self._read_first_number(context, img, self.COST_ROI, mod100=True)
        if cur is None or cost is None:
            mfa_warn(_MODULE, "stamina_short",
                     f"读数不全（体力={cur} 消耗={cost}）"
                     f" roi={self.STAMINA_ROI}/{self.COST_ROI} → 不判定")
            return None

        lo, hi = self.STAMINA_RANGE
        if not (lo <= cur <= hi):
            mfa_warn(_MODULE, "stamina_short", f"体力读数越界={cur} → 不判定")
            return None
        lo, hi = self.COST_RANGE
        if not (lo <= cost <= hi):
            mfa_warn(_MODULE, "stamina_short", f"消耗读数越界={cost} → 不判定")
            return None

        if cur >= cost:
            return None

        mfa_log(_MODULE, "stamina_short", "ok",
                f"体力 {cur} < 本次消耗 {cost} → 收尾（不再空转等超时）")
        return CustomRecognition.AnalyzeResult(
            box=tuple(self.STAMINA_ROI), detail=f"stamina={cur},cost={cost}")

    # ------------------------------------------------------------------
    @classmethod
    def _read_first_number(cls, context, img, roi, mod100=False):
        """裁 ROI → 放大 ZOOM 倍 → OCR → 取第一个整数。读不出返回 None。

        放大是因为 720p 下的资源数字字高只有 ~18px，直接 OCR 基本返回空
        （同认知海域读券数的处理）。

        mod100：OCR 会把「⚡20」里的闪电当成数字，读出 '920'。关卡消耗都是两位数，
        所以 >99 时对 100 取模把前缀噪音削掉。
        """
        try:
            import numpy as np
            x, y, w, h = roi
            crop = np.asarray(img)[y:y + h, x:x + w]
            if crop.size == 0:
                mfa_warn(_MODULE, "stamina_short", f"ROI 越界 {roi}")
                return None
            big = np.repeat(np.repeat(crop, cls.ZOOM, axis=0), cls.ZOOM, axis=1)
            r = context.run_recognition_direct(
                JRecognitionType.OCR,
                JOCR(expected=[r".+"], roi=(0, 0, big.shape[1], big.shape[0]), threshold=0.2),
                big,
            )
        except Exception as e:
            mfa_warn(_MODULE, "stamina_short", f"OCR 异常 roi={roi}: {e!r}")
            return None

        if r is None or not r.hit:
            return None
        for res in (getattr(r, "all_results", None) or []):
            text = str(getattr(res, "text", "") or "").replace(",", "").strip()
            m = re.search(r"\d+", text)
            if m:
                val = int(m.group(0))
                if mod100 and val > 99:
                    val %= 100          # '920'（⚡20）→ 20
                return val
        return None
