"""认知海域 战斗等待 CustomAction（MaaEOV）

提供的 CustomAction：
- SoCAwaitBattle：点「开始作战」后，轮询等待战斗结算，同时处理「获取物资」奖励弹窗，
  并在战斗结束后判定本次任务是否完成（意识碎片 1000/1000）。
- SoCGBPickAvailable：全局 Buff 选卡（纯 OCR 驱动，内部轮询）。

策略（按用户实测 / 2026-09-14）：
  战斗结束偶尔会弹出「获取物资」奖励界面：界面先空白、随机点一下才出现
  「获取物资」标题，再点底部中央的对号(✓)关闭，之后才会出现右下「继续」结算按钮。
  因此不能用单一模板死等「继续」，必须轮询 + 跳过空白界面 + 关闭奖励。

  SoCAwaitBattle:
  1. 进入后先静等 init_wait 秒（默认 30），不打扰战斗进行。
  2. 之后每 poll 秒（默认 5）轮询一次：
       a. 先检查 context.tasker.stopping → 用户点了停止则立即退出
       b. 双击 [1250,510] 跳过空白结束/过场界面（两次间隔 gap 秒）
       c. 截屏 → OCR 判断顶部居中的「获取物资」奖励标题；
          命中则点底部中央的对号(✓)关闭，下一轮继续找「继续」。
       d. 模板匹配右下「继续」结算按钮（战斗完成继续.png）；
          命中则再做一步任务完成判定：
          - OCR 左下角 [88,592,247,83] 区域是否出现 "1000" 或 "意识碎片"
          - 出现 → 打印 "★ 本轮认知海域已完成 ★"，返回 True
          - 未出现 → 不打印，直接返回 True，交回 pipeline 继续下一轮
       e. 以上都不在 → 等 poll 后下一轮
  3. 总等待不超过 max_wait 秒（默认 540）兜底，避免永久卡死。

  SoCGBPickAvailable（22:23 日志铁证后切换为纯 OCR 模式）：
  模板匹配在所有尝试中均失败（218×95 标题裁切 0.40~0.53、234×160 autodori 源图 0.18~0.29），
  且动态池大部分卡不在已知列表中。OCR「未激发」score 稳定 0.999 → 是唯一可靠信号。
  1. OCR 找所有「未激发」标签 → 获得每张可激活卡的精确位置
  2. 遍历每个标签，点击其上方偏移位置（卡片主体区）
  3. 连续多轮找不到未激发 → 判定选满 → 返回 False

坐标均基于 1280×720 基准，可通过 custom_action_param 覆盖以便调参。
"""
import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from maa.pipeline import JRecognitionType, JOCR, JTemplateMatch

from auto_battle import _parse_param, _screencap
from mfalog import mfa_log, mfa_err, mfa_warn

_MODULE = "SoC"

# 诊断目录（首次 OCR 全 miss 时保存截图供排查）
import os as _os
_GB_DIAG_DIR = _os.path.join(
    _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
    "debug", "gb_diag",
)

# 默认坐标（1280×720 基准）
_GIFT_ROI = (380, 30, 520, 340)       # 「获取物资」标题（顶部居中，放宽高度）
_CHECK_BTN = (640, 650)               # 底部中央 ✓ 对号
_CONTINUE_ROI = (950, 600, 330, 120)  # 右下「继续」结算按钮
_CONTINUE_TPL = "SeaOfCognition/战斗完成继续.png"
_TAP = (1250, 510)                   # 跳过空白界面用的安全点击点（右下偏上，避开按钮）
_TASK_DONE_ROI = (88, 592, 247, 83)   # 左下角「意识碎片 N/1000」区域 —— 出现 "1000" 即任务完成


@AgentServer.custom_action("SoCAwaitBattle")
class SoCAwaitBattle(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        p = _parse_param(argv.custom_action_param)
        init_wait = float(p.get("init_wait", 30))
        poll = float(p.get("poll", 5))
        gap = float(p.get("gap", 1))
        max_wait = float(p.get("max_wait", 540))
        gift_roi = tuple(p.get("gift_roi", _GIFT_ROI))
        check_btn = tuple(p.get("check_btn", _CHECK_BTN))
        tap = tuple(p.get("tap", _TAP))
        task_done_roi = tuple(p.get("task_done_roi", _TASK_DONE_ROI))

        mfa_log(
            _MODULE, "await_battle", "info",
            f"开始等待结算（初等 {init_wait}s，轮询 {poll}s，上限 {max_wait}s）",
        )

        start = time.time()
        if init_wait > 0:
            time.sleep(init_wait)

        while time.time() - start < max_wait:
            # a) 检测用户是否点了停止 → 立即退出，不再点击
            if context.tasker.stopping:
                mfa_log(_MODULE, "await_battle", "warn", "检测到任务停止请求，立即退出轮询")
                return False

            # b) 双击跳过空白结束/过场界面（两次间隔 gap 秒）
            self._click(context, *tap)
            time.sleep(gap)
            self._click(context, *tap)

            img = _screencap(context)
            if img is None:
                time.sleep(poll)
                continue

            # c) 奖励弹窗「获取物资」
            gift = context.run_recognition_direct(
                JRecognitionType.OCR,
                JOCR(expected=["获取物资"], roi=gift_roi, threshold=0.3),
                img,
            )
            if gift is not None and gift.hit:
                mfa_log(_MODULE, "await_battle", "info", "检测到「获取物资」，点 ✓ 关闭")
                self._click(context, *check_btn)
                time.sleep(1.5)
                continue

            # d) 结算「继续」+ 任务完成判定
            cont = context.run_recognition_direct(
                JRecognitionType.TemplateMatch,
                JTemplateMatch(template=[_CONTINUE_TPL], roi=_CONTINUE_ROI, threshold=[0.8]),
                img,
            )
            if cont is not None and cont.hit:
                # --- 任务完成判定：左下角意识碎片是否满 1000 ---
                done = context.run_recognition_direct(
                    JRecognitionType.OCR,
                    JOCR(expected=["1000", "意识碎片"], roi=task_done_roi, threshold=0.3),
                    img,
                )
                if done is not None and done.hit:
                    mfa_log(_MODULE, "await_battle", "ok", "★ 本轮认知海域已完成 ★（意识碎片已满 1000）")
                # 未命中不打印，直接交回 pipeline 继续下一轮
                return True

            # e) 都没有 -> 等 poll 后下一轮（下一轮开头会再次双击）
            time.sleep(poll)

        mfa_warn(_MODULE, "await_battle", "超过最大等待仍未检测到「继续」，返回交回 pipeline")
        return True

    @staticmethod
    def _click(context, x, y):
        try:
            context.tasker.controller.post_click(int(x), int(y)).wait()
        except Exception as e:
            mfa_err(_MODULE, "await_battle_click", f"点击失败 ({x},{y})", error=e)


@AgentServer.custom_action("SoCGBPickAvailable")
class SoCGBPickAvailable(CustomAction):
    """全局 Buff 选卡（纯 OCR 驱动，内部轮询）。

    设计动机（2026-09-14 迭代历程总结）：
      · GB1~5 模板匹配已选/未选卡标题 → 已选中卡标题一致 → 误点已选卡 → 死循环
      · 218×95 标题裁切模板匹配分 0.40~0.53（阈值 0.8 全 miss / 0.5 勉强 1 张）
      · 234×160 autodori 全卡面源图匹配分 0.18~0.29（**更差**，RGBA/渲染差异）
      · fallback 点 (label_cx, label_cy-100) ≈ y=374 落在描述文字区 → 点击无效

    ✅ 当前方案（22:41 收敛式重写，纯 OCR）：
      Step 1 — OCR 找「未激发」标签 → 获得每张可激活卡的精确位置
      Step 2 — 点完当前屏所有未点过的卡 → 仅左滑一次看屏外未选卡
      Step 3 — 终止条件（根治 20s 误滑）：视野内未激发卡都已点过 / 连续 2 屏空 / 超 wall_cap(15s)
               → 判定选满，立即结束（不盲滑）。返回 clicked>0 去点「继续」。

    为什么不用模板：
      三种模板（标题裁切/全卡面源图/autodori 原图）在实机上匹配分均 < 0.53，
      且动态池大部分卡不在已知列表中 → 模板门控只会阻碍选卡。
      OCR「未激发」score 稳定 0.999、定位精确到像素 → 是唯一可靠信号。
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        p = _parse_param(argv.custom_action_param)
        # OCR：「未激发」标签所在区域（卡片下半区）
        label_roi = tuple(p.get("label_roi", (40, 420, 1200, 120)))
        label = p.get("label", ["未激发", "未激活", "可激发", "待激发"])
        max_look = int(p.get("max_iter", 8))        # 最多扫几屏（每屏=OCR+点卡+左滑看更多）
        max_no_find = int(p.get("max_no_find", 2))  # 连续几屏完全无可点卡 → 判定选满
        swipe_begin = tuple(p.get("swipe_begin", (1270, 360)))
        swipe_end = tuple(p.get("swipe_end", (870, 360)))
        # 点击偏移：从标签中心向上多少像素（0=直接点标签本身）
        # 标签在 y≈462~474；卡片主体在 y≈190~450；图标区 y≈190~300
        click_y_offset = int(p.get("click_y_offset", -60))  # 默认上偏 60px 到 y≈400
        click_sleep = float(p.get("click_sleep", 0.5))
        swipe_sleep = float(p.get("swipe_sleep", 1.0))
        # 去重容差（卡片宽 ~236，相邻卡间距 ~400，±50 足够吸收点卡后 UI 轻微位移，又不会合并不同卡）
        dedup_tol = int(p.get("dedup_tol", 50))
        wall_cap = float(p.get("wall_cap", 15))     # 硬上限秒：杜绝「观感卡死」

        clicked = 0
        _clicked = set()          # 已点过的卡（按点击坐标 ±dedup_tol 去重）
        no_find = 0
        start = time.time()

        mfa_log(
            _MODULE, "gb_pick", "info",
            f"START (纯 OCR·收敛式) label_roi={label_roi} max_look={max_look} "
            f"click_y_offset={click_y_offset} dedup_tol={dedup_tol} wall_cap={wall_cap}",
        )

        for i in range(max_look):
            if context.tasker.stopping:
                mfa_log(_MODULE, "gb_pick", "warn", "STOP")
                return False
            if time.time() - start > wall_cap:
                mfa_warn(_MODULE, "gb_pick", f"超 wall_cap={wall_cap}s 强制结束")
                break

            img = _screencap(context)
            if img is None:
                time.sleep(1)
                continue

            # 首次迭代无条件保存截图供诊断
            if i == 0:
                _save_gb_diag(img, i)

            # ════════════════════════════════════════════
            # Step 1: OCR 找「未激发」标签
            # ════════════════════════════════════════════
            boxes = self._ocr_unselected(context, img, label, label_roi)
            n = len(boxes)
            mfa_log(_MODULE, "gb_pick", "info", f"iter{i} 未激发={n} 已点={clicked}")

            if n == 0:
                # 整屏无可点卡
                no_find += 1
                if no_find >= max_no_find:
                    mfa_log(_MODULE, "gb_pick", "info", f"连续 {no_find} 屏空 -> BREAK")
                    break
                self._swipe(context, swipe_begin, swipe_end)
                time.sleep(swipe_sleep)
                continue
            no_find = 0

            # 过滤出尚未点过的卡（按点击坐标 ±dedup_tol 去重）
            new_boxes = []
            for box in boxes:
                lx, ly, lw, lh = self._box(box)
                cx = lx + lw / 2
                cy = ly + lh / 2
                x = int(cx)
                y = int(cy + click_y_offset)
                key = (x // dedup_tol * dedup_tol, y // dedup_tol * dedup_tol)
                if key in _clicked:
                    continue
                _clicked.add(key)
                new_boxes.append((x, y))

            if not new_boxes:
                # 视野内所有「未激发」卡都已点过
                # （选中后标签可能不消失，仅加 ✓ 金边）→ 视为选满，停止，不盲滑
                mfa_log(_MODULE, "gb_pick", "info", "视野内未激发均已点过 -> BREAK")
                break

            # 点完当前屏所有未选卡
            for (x, y) in new_boxes:
                clicked += 1
                mfa_log(_MODULE, "gb_pick", "info", f"#{clicked} 选卡 @({x},{y})")
                self._click(context, x, y)
                time.sleep(click_sleep)
            # 给 UI 一点稳定时间，再左滑一次看是否有屏外未选卡
            time.sleep(0.4)
            self._swipe(context, swipe_begin, swipe_end)
            time.sleep(swipe_sleep)

        mfa_log(
            _MODULE, "gb_pick", "ok",
            f"END 已点={clicked} (return {clicked > 0})",
        )
        return clicked > 0

    @staticmethod
    def _box(box):
        """统一提取包围盒 (x,y,w,h)，兼容 list/tuple 和属性对象。"""
        if isinstance(box, (list, tuple)) and len(box) >= 4:
            return box[0], box[1], box[2], box[3]
        return box.x, box.y, box.w, box.h

    @staticmethod
    def _click(context, x, y):
        try:
            context.tasker.controller.post_click(int(x), int(y)).wait()
        except Exception as e:
            mfa_err(_MODULE, "gb_pick_click", f"点击失败 ({x},{y})", error=e)

    @staticmethod
    def _swipe(context, begin, end):
        try:
            context.tasker.controller.post_swipe(
                begin[0], begin[1], end[0], end[1], 800,
            ).wait()
        except Exception as e:
            mfa_err(_MODULE, "gb_pick_swipe", "左滑失败", error=e)

    @staticmethod
    def _ocr_unselected(context, img, label, label_roi):
        """OCR 找「未激发」类标签，返回所有命中 box 的列表（空列表表示无）。"""
        try:
            r = context.run_recognition_direct(
                JRecognitionType.OCR,
                JOCR(expected=label, roi=label_roi, threshold=0.3),
                img,
            )
        except Exception as e:
            mfa_err(_MODULE, "gb_pick_ocr", "OCR EXCEPT", error=e)
            return []
        if r is None or not r.hit:
            return []
        boxes = r.box
        if not isinstance(boxes, (list, tuple)):
            boxes = [boxes]
        return list(boxes)

    @staticmethod
    def _save_gb_diag(img, i):
        """首次迭代保存原始截图供排查（兼容 cv2 / PIL / 裸 RGB 字节）。"""
        try:
            _os.makedirs(_GB_DIAG_DIR, exist_ok=True)
            from datetime import datetime as _dt
            _ts = _dt.now().strftime("%Y.%m.%d-%H.%M.%S")
            _path = _os.path.join(_GB_DIAG_DIR, f"{_ts}_iter{i}_screencap.png")
            import numpy as _np
            try:
                import cv2
                cv2.imwrite(_path, img)
            except ImportError:
                try:
                    from PIL import Image as _PILImage
                    _PILImage.fromarray(img).save(_path)
                except Exception:
                    _raw = _np.ascontiguousarray(img).tobytes()
                    with open(_path, "wb") as _fh:
                        _fh.write(_raw)
            mfa_log(_MODULE, "gb_pick_diag", "ok", f"截图已保存: {_path}")
        except Exception as _ex2:
            mfa_err(_MODULE, "gb_pick_diag", "保存截图失败", error=_ex2)
