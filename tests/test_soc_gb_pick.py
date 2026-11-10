# -*- coding: utf-8 -*-
"""全局 Buff 选卡（SoCGBPickAvailable）纯函数 + 假设备行为测试。

背景（2026-11-09 实机反馈）：
  · 日志 `已点=8` 但一张都没选中 → 原实现 `self._click()` **连调两次**，
    若卡片是「点击切换选中」，双击等于选中后立刻取消，8 次点击 = 4 轮抵消 = 0。
  · 「剩余可选灵感 N」数字 OCR 读不出；「固化灵感」计数不随选中变化 →
    「是否选中」只能靠**像素差分**判断。
  · 已固化的卡描述区里仍会被读到「未激发」→ 必须按「固化灵感」标签的 x 带剔除。

本测试用假 Context / 假截图跑完整 `run()`，锁住三件事：
  1. 每张卡**只点一次**（回归双击）
  2. 差分判定生效 → 计入已选；判定无效 → 不重复点、累计失败后收敛退出
  3. 与「固化灵感」同 x 带的「未激发」误读框会被剔除

运行：python\\python.exe -m unittest tests.test_soc_gb_pick -v
"""
import os
os.environ.setdefault("MFAEOV_AGENT_LOG", "off")   # 单测日志不落盘（防污染 debug/mfa_agent.log）
import sys
import unittest
from unittest import mock

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AGENT = os.path.join(ROOT, "agent")
if AGENT not in sys.path:
    sys.path.insert(0, AGENT)

import soc_actions  # noqa: E402


# ---------------------------------------------------------------------------
# 假设备
# ---------------------------------------------------------------------------
class _Job:
    def wait(self):
        return self

    def get(self, wait=False):
        return None


class _World:
    """一张 1280×720 的假屏幕：被点中的卡会「亮起」（金边），用于制造真实差分。"""

    def __init__(self, pickable=True):
        self.clicks = []            # 每次 post_click 的坐标
        self.pickable = pickable    # False = 点了没反应（名额满/卡不可点）
        self.picked = set()         # 已亮起的卡中心 x
        self.frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    def on_click(self, x, y):
        if not self.pickable:
            return
        # 把点击点所在卡片整块刷成金色（模拟金边+✓）
        self.picked.add(x)
        x0, x1 = max(0, x - 118), min(1280, x + 118)
        y0, y1 = 100, 470
        self.frame[y0:y1, x0:x1] = (40, 200, 240)   # BGR 金

    def screencap(self):
        return self.frame.copy()


class _Controller:
    def __init__(self, world):
        self.world = world

    def post_click(self, x, y):
        self.world.clicks.append((int(x), int(y)))
        self.world.on_click(int(x), int(y))
        return _Job()

    def post_swipe(self, *a, **k):
        return _Job()


class _Tasker:
    stopping = False

    def __init__(self, world):
        self.controller = _Controller(world)


class _Ctx:
    def __init__(self, world):
        self.tasker = _Tasker(world)

    def run_recognition_direct(self, *a, **k):
        return None


class _Arg:
    def __init__(self, param):
        self.custom_action_param = param


# 实机 OCR 结果（2026-11-09 §3.2 原样）：5 个「未激发」等间距 244px，y 全 463
_UNSEL = [
    (136, 463, 60, 23),
    (380, 463, 59, 23),
    (624, 463, 59, 23),
    (867, 463, 61, 22),
    (1111, 463, 60, 23),
]
# 左侧两张已固化 → 同时也被读出「固化灵感」
_FIXED = [(136, 300, 90, 24), (380, 300, 88, 24)]


def _blocks_from(unsel, fixed):
    """按 roi 把标签框映射回 (box, text)，供 _ocr_blocks 假实现使用。"""
    def _impl(context, img, roi, threshold=0.3):
        out = []
        rx, ry, rw, rh = roi
        for b in unsel:
            if rx <= b[0] <= rx + rw and ry <= b[1] <= ry + rh:
                out.append((b, "未激发"))
        for b in fixed:
            if rx <= b[0] <= rx + rw and ry <= b[1] <= ry + rh:
                out.append((b, "固化灵感"))
        return out
    return _impl


class TestGbPick(unittest.TestCase):
    def _run(self, world, unsel, fixed, param=None):
        p = {
            "click_sleep": 0.01,
            "swipe_sleep": 0.01,
            "adb_tap": False,      # 测试里绝不真的调 adb
            "max_iter": 6,
            "max_no_find": 2,
        }
        p.update(param or {})
        arg = _Arg(p)
        action = soc_actions.SoCGBPickAvailable()
        with mock.patch.object(soc_actions, "_screencap",
                               side_effect=lambda ctx: world.screencap()), \
             mock.patch.object(soc_actions.SoCGBPickAvailable, "_ocr_blocks",
                               staticmethod(_blocks_from(unsel, fixed))), \
             mock.patch.object(soc_actions.SoCGBPickAvailable, "_save_gb_diag",
                               staticmethod(lambda img, i: None)), \
             mock.patch.object(soc_actions, "_load_priority",
                               lambda profile="": {"mode": "left"}), \
             mock.patch.object(soc_actions.time, "sleep", lambda s: None):
            return action.run(_Ctx(world), arg)

    # -- 1. 回归「双击」----------------------------------------------------
    def test_clicks_each_card_once(self):
        """5 张未激发里，右边缘 1 张被过滤、2 张已固化被剔除 → 只剩 2 张各点 1 次。"""
        world = _World(pickable=True)
        ok = self._run(world, _UNSEL, _FIXED)

        self.assertTrue(ok, "至少选中一张时 run() 应返回 True")
        # 期望：x=653（标签 624+59/2）和 x=897（867+61/2），y=463+11.5-180≈294
        self.assertEqual(len(world.clicks), 2,
                         f"每张卡应只点一次，实际点击 {world.clicks}")
        xs = sorted(x for x, _ in world.clicks)
        self.assertEqual(xs, [653, 897], f"候选应为未被固化剔除、未被右边缘裁切的两张：{xs}")
        for x, y in world.clicks:
            self.assertTrue(285 <= y <= 300, f"y 应落在图标区（≈294），实际 {y}")

    def test_no_double_click_same_coordinate(self):
        """同一坐标连续两次点击是本轮缺陷的直接特征，必须彻底消失。"""
        world = _World(pickable=True)
        self._run(world, _UNSEL[2:3], [])
        for i in range(1, len(world.clicks)):
            self.assertNotEqual(world.clicks[i], world.clicks[i - 1],
                                "同一坐标连续点击 = 选中后立刻取消")

    def test_nearby_jitter_same_card_deduped(self):
        """实机 2026-11-10：左滑后同一张卡位置微动 16px（184→168），
        桶式 //tol 去重会把它拆进两个桶 → 第二次点击把刚选中的卡**取消**。
        必须按真实距离去重。"""
        # 两帧标签位置：第一帧 x=184，第二帧同一张卡 x=168
        frame1 = [(124, 463, 120, 23)]          # 标签中心 x=184
        frame2 = [(108, 463, 120, 23)]          # 标签中心 x=168
        frames = [frame1, frame2, frame2, frame2, frame2, frame2]

        def fake_blocks(context, img, roi, threshold=0.3):
            rx, ry, rw, rh = roi
            b = frames.pop(0)[0] if frames else frame2[0]
            return [((b), "未激发")] if rx <= b[0] <= rx + rw else []

        world = _World(pickable=True)
        arg = _Arg({
            "click_sleep": 0.01, "swipe_sleep": 0.01, "adb_tap": False,
            "max_iter": 6, "max_no_find": 2,
        })
        with mock.patch.object(soc_actions, "_screencap",
                               side_effect=lambda ctx: world.screencap()), \
             mock.patch.object(soc_actions.SoCGBPickAvailable, "_ocr_blocks",
                               staticmethod(fake_blocks)), \
             mock.patch.object(soc_actions.SoCGBPickAvailable, "_save_gb_diag",
                               staticmethod(lambda img, i: None)), \
             mock.patch.object(soc_actions, "_load_priority",
                               lambda profile="": {"mode": "left"}), \
             mock.patch.object(soc_actions.time, "sleep", lambda s: None):
            soc_actions.SoCGBPickAvailable().run(_Ctx(world), arg)

        self.assertEqual(len(world.clicks), 1,
                         f"同一张卡只应点一次（位移 16px 必须被去重），实际 {world.clicks}")

    # -- 2. 差分判据 -------------------------------------------------------
    def test_click_not_effective_stops_early(self):
        """点了没反应（名额已满）→ 失败累计到 max_fail 就收敛，不盲点到上限。"""
        world = _World(pickable=False)
        ok = self._run(world, _UNSEL, [], {"max_fail": 3, "max_iter": 12, "max_no_find": 3})

        self.assertFalse(ok, "一张都没选中时 run() 应返回 False（交给放弃激发兜底）")
        self.assertLessEqual(len(world.clicks), 3,
                             f"连续失败应提前收敛，实际点了 {len(world.clicks)} 次")
        # 同一张卡不能被反复点
        self.assertEqual(len(world.clicks), len(set(world.clicks)),
                         f"未生效的卡不应重复点击：{world.clicks}")

    def test_detects_effective_click(self):
        """正常情况应识别出「生效」，而不是把所有点击都判失败。"""
        world = _World(pickable=True)
        self._run(world, _UNSEL[2:3], [])
        self.assertEqual(len(world.clicks), 1)
        self.assertTrue(world.picked, "假屏幕上应留下被点亮的卡")

    # -- 3. 固化剔除 -------------------------------------------------------
    def test_drop_fixed_pure(self):
        out = soc_actions.SoCGBPickAvailable._drop_fixed(_UNSEL, _FIXED, 130)
        xs = sorted(b[0] for b in out)
        self.assertEqual(xs, [624, 867, 1111],
                         "与「固化灵感」同 x 带的误读框应被剔除")

    def test_drop_fixed_no_fixed(self):
        self.assertEqual(soc_actions.SoCGBPickAvailable._drop_fixed(_UNSEL, [], 130), _UNSEL)

    # -- 4. 像素差分本身 ---------------------------------------------------
    def test_diff_identical_is_zero(self):
        a = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.assertEqual(soc_actions.SoCGBPickAvailable._diff(a, a.copy(), (100, 100, 50, 50)), 0.0)

    def test_diff_change_exceeds_threshold(self):
        a = np.zeros((720, 1280, 3), dtype=np.uint8)
        b = a.copy()
        b[100:400, 500:700] = 200
        d = soc_actions.SoCGBPickAvailable._diff(a, b, (558, 194, 236, 315))
        self.assertGreater(d, 1.5, "卡片区域变化应超过默认阈值 1.5")

    def test_diff_bad_roi_returns_none(self):
        a = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.assertIsNone(soc_actions.SoCGBPickAvailable._diff(a, a, None))
        self.assertIsNone(soc_actions.SoCGBPickAvailable._diff(a, a, (5000, 5000, 10, 10)))

    # -- 5. 卡片 ROI -------------------------------------------------------
    def test_card_roi_geometry(self):
        roi = soc_actions.SoCGBPickAvailable._card_roi(676, 474, 23, 236)
        self.assertEqual(roi[0], 558)          # 676-118
        self.assertEqual(roi[2], 236)          # 整卡宽
        self.assertEqual(roi[1], 194)          # 474-280
        self.assertEqual(roi[3], 509 - 194)    # 474+23+12

    def test_card_roi_clamped(self):
        roi = soc_actions.SoCGBPickAvailable._card_roi(5, 10, 23, 236)
        self.assertEqual(roi[0], 0)
        self.assertEqual(roi[1], 0)
        self.assertLessEqual(roi[0] + roi[2], 1280)

    # -- 6. adb 目标解析 ---------------------------------------------------
    def test_adb_target_from_config(self):
        soc_actions._adb_cache.clear()
        path, serial = soc_actions._adb_target()
        self.assertTrue(path, "应从 config/instances/default.json 读到 AdbPath")
        self.assertTrue(serial, "应读到 AdbSerial")


# ---------------------------------------------------------------------------
# SoCTicketLow：券不足时按「够不够补满」判，而不是固定阈值一刀切
# ---------------------------------------------------------------------------
class _OcrRes:
    def __init__(self, text):
        self.text = text


class _OcrDetail:
    def __init__(self, text, hit=True):
        self.hit = hit
        self.filtered_results = [_OcrRes(text)]
        self.all_results = self.filtered_results


class _ScoreCtx:
    def __init__(self, text, hit=True):
        self._text = text
        self._hit = hit

    def run_recognition_direct(self, *a, **k):
        return _OcrDetail(self._text, self._hit)


class _AnalyzeArg:
    def __init__(self, image):
        self.image = image


class TestTicketLow(unittest.TestCase):
    def test_read_score_parses_fraction(self):
        r = soc_actions.SoCTicketLow._read_score(_ScoreCtx("意识碎片 700/1000"), None)
        self.assertEqual(r, (700, 1000))

    def test_read_score_full_width_slash(self):
        r = soc_actions.SoCTicketLow._read_score(_ScoreCtx("500／1000"), None)
        self.assertEqual(r, (500, 1000))

    def test_read_score_miss_returns_none(self):
        self.assertIsNone(soc_actions.SoCTicketLow._read_score(_ScoreCtx("", hit=False), None))
        self.assertIsNone(soc_actions.SoCTicketLow._read_score(_ScoreCtx("意识碎片"), None))

    def _analyze(self, tickets_text, score):
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        with mock.patch.object(soc_actions.SoCGBPickAvailable, "_ocr_blocks",
                               staticmethod(lambda ctx, im, roi, threshold=0.3:
                                            [((0, 0, 10, 10), tickets_text)])), \
             mock.patch.object(soc_actions.SoCTicketLow, "_read_score",
                               classmethod(lambda cls, ctx, im: score)):
            return soc_actions.SoCTicketLow().analyze(_ScoreCtx(""), _AnalyzeArg(img))

    def test_low_ticket_but_enough_to_fill_passes(self):
        """券 1 张、只差 300 分 → 1×355 够补满 → 放行（不收工）。"""
        self.assertIsNone(self._analyze("1", (700, 1000)),
                          "券虽少但能补满时应放行，不该收工")

    def test_enough_tickets_passes(self):
        self.assertIsNone(self._analyze("3", None), "券够时不该命中")

    def test_low_ticket_first_time_passes_to_free_round(self):
        """券不足且补不满 + 未进过免费轮 → 放行并占位（走自由探索），不收工。"""
        soc_actions._FREE_ROUND.update(picked=False, at=0.0)
        self.assertIsNone(self._analyze("1", (100, 1000)),
                          "首次券不足应放行走自由探索，不该收工")
        self.assertTrue(soc_actions._FREE_ROUND["at"] > 0, "放行时应设置占位时间戳")

    def test_low_ticket_after_free_round_finishes(self):
        """免费轮已打过（picked=True，新鲜）→ 探索完成回选层 → 收工并清标记。"""
        import time as _t
        soc_actions._FREE_ROUND.update(picked=True, at=_t.time())
        res = self._analyze("1", (100, 1000))
        self.assertIsNotNone(res, "免费轮打完回选层应收工")
        self.assertIn("free_round_done", res.detail)
        self.assertFalse(soc_actions._FREE_ROUND["picked"], "收工时应清掉轮次标记")

    def test_low_ticket_free_round_overtime_still_finishes(self):
        """探索异常拖超 30 分钟 → 回选层仍收工（兜底），不落到深潜指引。"""
        import time as _t
        soc_actions._FREE_ROUND.update(picked=True, at=_t.time() - 31 * 60)
        res = self._analyze("1", (100, 1000))
        self.assertIsNotNone(res, "超时兜底也应收工")
        self.assertFalse(soc_actions._FREE_ROUND["picked"])

    def test_low_ticket_no_score_starts_free_round(self):
        """积分读不到 + 首次 → 放行走免费轮（免费轮不依赖积分），不收工。"""
        soc_actions._FREE_ROUND.update(picked=False, at=0.0)
        self.assertIsNone(self._analyze("1", None))

    def test_min_tickets_param_overrides_threshold(self):
        """pipeline recognition.param 可传 min_tickets 覆盖阈值（实机测试券 1 张时传 1）。"""
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        arg = _AnalyzeArg(img)
        arg.custom_recognition_param = '{"min_tickets": 1}'
        with mock.patch.object(soc_actions.SoCGBPickAvailable, "_ocr_blocks",
                               staticmethod(lambda ctx, im, roi, threshold=0.3:
                                            [((0, 0, 10, 10), "1")])), \
             mock.patch.object(soc_actions.SoCTicketLow, "_read_score",
                               classmethod(lambda cls, ctx, im: None)):
            res = soc_actions.SoCTicketLow().analyze(_ScoreCtx(""), arg)
        self.assertIsNone(res, "min_tickets=1 时券 1 张应放行，不该收工")

    def test_min_tickets_param_bad_json_falls_back(self):
        """param 解析失败 → 默认阈值 2；券 1 补不满 → 状态机接管（放行免费轮）。"""
        soc_actions._FREE_ROUND.update(picked=False, at=0.0)
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        arg = _AnalyzeArg(img)
        arg.custom_recognition_param = "not-json"
        with mock.patch.object(soc_actions.SoCGBPickAvailable, "_ocr_blocks",
                               staticmethod(lambda ctx, im, roi, threshold=0.3:
                                            [((0, 0, 10, 10), "1")])), \
             mock.patch.object(soc_actions.SoCTicketLow, "_read_score",
                               classmethod(lambda cls, ctx, im: None)):
            res = soc_actions.SoCTicketLow().analyze(_ScoreCtx(""), arg)
        self.assertIsNone(res, "默认阈值 2 + 券不足 → 状态机放行免费轮")


class TestFreeGate(unittest.TestCase):
    """SoCTicketFreeGate：占位标记有效 → 命中引导走自由探索。"""

    def _gate(self):
        return soc_actions.SoCTicketFreeGate().analyze(_ScoreCtx(""), _AnalyzeArg(
            np.zeros((720, 1280, 3), dtype=np.uint8)))

    def test_gate_hits_when_pending(self):
        import time as _t
        soc_actions._FREE_ROUND.update(picked=False, at=_t.time())
        res = self._gate()
        self.assertIsNotNone(res, "放行占位有效时应命中，引导走自由探索")

    def test_gate_misses_when_no_marker(self):
        soc_actions._FREE_ROUND.update(picked=False, at=0.0)
        self.assertIsNone(self._gate(), "无占位标记（券充足路径）不应命中")

    def test_gate_misses_when_round_in_progress(self):
        import time as _t
        soc_actions._FREE_ROUND.update(picked=True, at=_t.time())
        self.assertIsNone(self._gate(), "免费轮进行中不应再引导（收工由 TicketLow 负责）")

    def test_gate_misses_when_stale(self):
        import time as _t
        soc_actions._FREE_ROUND.update(picked=False, at=_t.time() - 31 * 60)
        self.assertIsNone(self._gate(), "占位过期不应命中")


if __name__ == "__main__":
    unittest.main(verbosity=2)
