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
import json
import os
import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition
from maa.context import Context
from maa.pipeline import JRecognitionType, JOCR, JTemplateMatch

import evidence
from auto_battle import _parse_param, _screencap
from mfalog import mfa_log, mfa_err, mfa_warn

_MODULE = "SoC"

# ---------------------------------------------------------------------------
# 灵感优先级表（resource/base/data/soc/buff_priority.json）
# ---------------------------------------------------------------------------
_PRIORITY_REL = os.path.join("resource", "base", "data", "soc", "buff_priority.json")
_GLOBAL_FALLBACK_SCORE = 15   # 全局灵感未知卡的保底分：低于表内最低分(20)，但仍会被选中凑满名额
_priority_cache: dict = {}
# 已选过的全局灵感标题键。**必须是模块级**：`SoCGBPickAvailable.run()` 每轮都会被 pipeline
# 重新调用，如果放在 run() 内部就会每次重置 → 反复选同一张卡（实测空转 12 分钟）。
_PICKED_TITLES: set = set()


def _strip_jsonc(text: str) -> str:
    """去掉 // 行注释（本文件字符串内不含 //，简易实现即可）。"""
    out = []
    for line in text.splitlines():
        in_str = esc = False
        cut = None
        for i, ch in enumerate(line):
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = not in_str
            elif not in_str and ch == "/" and i + 1 < len(line) and line[i + 1] == "/":
                cut = i
                break
        out.append(line if cut is None else line[:cut])
    return "\n".join(out)


def _load_priority(profile: str = ""):
    """读优先级表，返回该 profile 的字典；失败返回 {}（调用方退化为盲选）。"""
    key = profile or "_default"
    if key in _priority_cache:
        return _priority_cache[key]
    table = {}
    try:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(root, _PRIORITY_REL)
        with open(path, encoding="utf-8") as f:
            data = json.loads(_strip_jsonc(f.read()))
        profiles = data.get("profiles") or {}
        table = profiles.get(profile) or profiles.get(data.get("default_profile")) or {}
    except Exception as e:
        mfa_warn(_MODULE, "priority", f"优先级表不可用（退化为盲选）: {e!r}")
        table = {}
    _priority_cache[key] = table
    return table


def _score_global(full: str, titles, table: dict):
    """全局灵感打分 → (score, 命中的条目名)。

    ⚠️ 只用整卡文字匹配 `keywords`，**不靠自动提取的标题候选**。
    实测原因：卡片区域附近会混进 UI 文字（继续 / 剩余可选灵感 / 下一节点 / 推荐等级），
    自动提取的「2~6 字中文块」会把它们当成卡名，反过来污染去重和打分。
    known 卡名都是专有名词，直接在全文中 `in` 匹配足够，且不会误命中 UI 词。
    """
    if not table:
        return _GLOBAL_FALLBACK_SCORE, ""
    for item in table.get("global") or []:
        name = item.get("name") or ""
        for kw in (item.get("keywords") or [name]):
            if kw and kw in (full or ""):
                return int(item.get("score", 0)), name
    return _GLOBAL_FALLBACK_SCORE, ""


def _score_in_battle(full: str, titles, table: dict):
    """局内灵感打分 → (score, 命中的条目名/分类)。

    顺序：known 标题精确 → known 全文包含 → categories 关键词 → default。
    categories 只做兜底：描述里单个词（如「恢复」）很容易把输出卡误判成生存卡，
    所以 known 表要尽量覆盖，categories 只在完全没见过的新卡上用。
    """
    ib = (table or {}).get("in_battle") or {}
    default = int(ib.get("default", 30))
    if not ib:
        return default, ""
    known = ib.get("known") or []
    for item in known:
        name = item.get("name") or ""
        if not name:
            continue
        for t in (titles or []):
            if name in t or t in name:
                return int(item.get("score", 0)), name
    for item in known:
        name = item.get("name") or ""
        if name and name in (full or ""):
            return int(item.get("score", 0)), name
    for cat in ib.get("categories") or []:
        for kw in cat.get("keywords") or []:
            if kw and kw in (full or ""):
                return int(cat.get("score", 0)), str(cat.get("key", ""))
    return default, ""


# 默认坐标（1280×720 基准）
_GIFT_ROI = (380, 30, 520, 340)       # 「获取物资」标题（顶部居中，放宽高度）
_CHECK_BTN = (640, 650)               # 底部中央 ✓ 对号
_CONTINUE_ROI = (950, 600, 330, 120)  # 右下「继续」结算按钮
_CONTINUE_TPL = "SeaOfCognition/战斗完成继续.png"
_TAP = (1250, 510)                   # 跳过空白界面用的安全点击点（右下偏上，避开按钮）
_TASK_DONE_ROI = (88, 592, 247, 83)   # 左下角「意识碎片 N/1000」区域 —— 出现 "1000" 即任务完成
_LAYER_BACK_ROI = (820, 545, 460, 175)  # 选层界面右下「开始下潜／继续下潜」—— 命中即已退出战斗


@AgentServer.custom_recognition("SoCTicketLow")
class SoCTicketLow(CustomRecognition):
    """剩余入场券 < 2 时命中 → 收尾结束。

    为什么阈值是 2：一层只有 500 分，打满 1000 需要 **2 轮 = 2 张券**。
    券只剩 1 张时开始新一轮必然打不满，纯亏券和 8~19 分钟，不如直接收。
    （实测 2026-11-01：券 10 → 打满用掉 2 张，验证了「2 张/满额」这个换算。）

    券数的显示：选层界面**右上角**「券图标 + 数字」（约 1280×720 的 (1114, 36)）。
    只有选层界面才有这个数字，所以本节点只挂在进选层之后的位置，不在 Resume 首位——
    否则在其它界面（主界面右上角是资源数）可能误读成 1 而提前收工。
    """

    # 券图标 + 数字只在右上角这么一小块（实测原图约 (1175,28)-(1225,52)，数字高仅 ~18px）
    TICKET_ROI = (1168, 20, 76, 40)
    MIN_TICKETS = 2
    ZOOM = 4          # 小字直接 OCR 读不出（实测返回空），先放大再识别

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        roi = self.TICKET_ROI
        img = getattr(argv, "image", None)
        if img is None:
            img = _screencap(context)
        if img is None:
            return None

        try:
            import numpy as np
            x, y, w, h = roi
            crop = np.asarray(img)[y:y + h, x:x + w]
            if crop.size == 0:
                mfa_warn(_MODULE, "ticket_low", f"券数区域越界 roi={roi}")
                return None
            big = np.repeat(np.repeat(crop, self.ZOOM, axis=0), self.ZOOM, axis=1)
            zoom_roi = (0, 0, big.shape[1], big.shape[0])
            blocks = SoCGBPickAvailable._ocr_blocks(context, big, zoom_roi, threshold=0.2)
        except Exception as e:
            mfa_err(_MODULE, "ticket_low", "券数识别异常", error=e)
            return None

        text = " ".join(t for _b, t in blocks).strip()
        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits:
            mfa_warn(_MODULE, "ticket_low", f"券数读不到（roi={roi}，放大 {self.ZOOM}x，OCR={text!r}）→ 不判定")
            return None
        try:
            n = int(digits)
        except ValueError:
            return None
        mfa_log(_MODULE, "ticket_low", "info", f"券数读数={n}（阈值 {self.MIN_TICKETS}，OCR={text!r}）")
        if n >= self.MIN_TICKETS:
            return None

        mfa_log(_MODULE, "ticket_low", "skip",
                f"剩余入场券 {n} 张（< {self.MIN_TICKETS}）→ 无法打满 1000 分，"
                f"结束任务并返回主界面。下期入场券刷新后再跑即可。")
        return CustomRecognition.AnalyzeResult(
            box=tuple(roi), detail=f"tickets={n}"
        )


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
        # 选层界面右下「开始下潜／继续下潜」区域：命中即说明已退出战斗、本轮结束
        layer_back_roi = tuple(p.get("layer_back_roi", _LAYER_BACK_ROI))

        mfa_log(
            _MODULE, "await_battle", "info",
            f"开始等待结算（初等 {init_wait}s，轮询 {poll}s，上限 {max_wait}s）",
        )

        start = time.time()
        img = None
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

            # c2) 已退回选层界面 = 本轮最后一个节点打完了
            # 实机 2026-11-01：打完本轮最后一场后游戏**直接回选层界面**（意识碎片 500/1000、
            # 右下出现「开始下潜」），没有「继续」按钮。原实现只认「继续」→ 死等到 max_wait
            # 540s 才判失败，把一次正常完成误判成故障。
            back = context.run_recognition_direct(
                JRecognitionType.OCR,
                # ⚠️ 繁简都要覆盖：实测游戏显示的是繁体「开始下潛 / 繼續下潛」，
                #   只写简体「开始下潜」会 miss（2026-11-01 因此把一次满分完成误判成超时）。
                JOCR(expected=[r"开始下[潜潛]", r"继续下[潜潛]", r"開始下[潜潛]", r"繼續下[潜潛]"],
                     roi=layer_back_roi, threshold=0.8),
                img,
            )
            if back is not None and back.hit:
                mfa_log(_MODULE, "await_battle", "ok",
                        "已退回选层界面 → 本轮节点已全部完成，正常结束等待")
                return True

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

        # 超时 = 失败（不再 return True 假装结算完成）。
        # 历史上这里返回 True，pipeline 会认为战斗已结束并在错误界面继续点击，
        # 最终表现为"任务成功但状态错乱"（2026-10-20 评审第 2 条）。
        shot = evidence.save_evidence(
            img, "await_battle_timeout", roi=task_done_roi,
            meta={"max_wait": max_wait, "elapsed_s": round(time.time() - start, 1),
                  "init_wait": init_wait, "poll": poll},
        )
        mfa_err(_MODULE, "await_battle",
                f"超过最大等待 {max_wait}s 仍未检测到「继续」，判为失败并交 pipeline 处理"
                f"（取证: {shot or '未落盘'}）",
                max_wait=max_wait, elapsed_s=round(time.time() - start, 1))
        return False

    @staticmethod
    def _click(context, x, y):
        try:
            context.tasker.controller.post_click(int(x), int(y)).wait()
        except Exception as e:
            mfa_err(_MODULE, "await_battle_click", f"点击失败 ({x},{y})", error=e)


@AgentServer.custom_action("SoCPickInBattleBuff")
class SoCPickInBattleBuff(CustomAction):
    """局内灵感二选一：读左右卡标题 → 按优先级表打分 → 点高分那张。

    原实现是 pipeline 里写死点左卡 [472,344]（连点两次防动画），完全不看内容。
    实机几何（1280×720）：左卡标题 y≈317、卡体中心 (494,343)；右卡标题 y≈317、卡体中心 (788,343)。
    标题用 OCR 读——卡面模板匹配实测只有 0.18~0.53，不可用。

    读不到标题时退化为点左卡（与原行为一致），保证不会因为 OCR 波动而卡在选卡界面。
    """

    LEFT_TITLE_ROI = (350, 175, 295, 340)    # 左卡整卡区域（标题+描述）
    RIGHT_TITLE_ROI = (645, 175, 295, 340)   # 右卡整卡区域
    LEFT_CARD = (494, 343)
    RIGHT_CARD = (788, 343)

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        p = _parse_param(argv.custom_action_param)
        profile = str(p.get("profile", ""))
        table = _load_priority(profile)

        # 配置一：原样行为，直接点左卡（不截图、不 OCR，零失败点）
        if table.get("mode") == "left":
            mfa_log(_MODULE, "in_buff", "info", "局内灵感：配置一原样 → 点左卡")
            self._click(context, *self.LEFT_CARD)
            return True

        left_roi = tuple(p.get("left_roi", self.LEFT_TITLE_ROI))
        right_roi = tuple(p.get("right_roi", self.RIGHT_TITLE_ROI))

        img = _screencap(context)
        if img is None:
            mfa_err(_MODULE, "in_buff", "截图失败，退化为点左卡")
            self._click(context, *self.LEFT_CARD)
            return True

        # 读左右卡（整段文字 + 标题候选）：布局不稳定，靠 known 标题命中比关键词可靠
        reader = SoCGBPickAvailable
        lf, ltitles = reader._read_region(context, img, left_roi)
        rf, rtitles = reader._read_region(context, img, right_roi)

        ls, lhit = _score_in_battle(lf, ltitles, table)
        rs, rhit = _score_in_battle(rf, rtitles, table)

        target, pick = (self.RIGHT_CARD, "右") if rs > ls else (self.LEFT_CARD, "左")
        mfa_log(_MODULE, "in_buff", "info",
                f"局内灵感 左〔{lhit or '未知'} {ls}〕/ 右〔{rhit or '未知'} {rs}〕→ 选{pick}")
        # 明细另记一条，便于回看原文（截断 60 字）
        mfa_log(_MODULE, "in_buff", "info",
                f"  左文={lf[:60] or '未读出'} | 右文={rf[:60] or '未读出'}")
        self._click(context, *target)
        return True

    @staticmethod
    def _click(context, x, y):
        try:
            context.tasker.controller.post_click(int(x), int(y)).wait()
        except Exception as e:
            mfa_err(_MODULE, "in_buff_click", f"点击失败 ({x},{y})", error=e)



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
        # ⚠️ 2026-11-01 实机：标签位置**随布局变化**，不能写死。
        #   · 横排小卡：「未激发」在卡片正下方，y≈480；
        #   · 竖排大卡：「未激发」在卡片右下角，y≈153。
        # 原来写死 (40,420,1200,120) 时，竖排布局整屏只读到 1 个标签 → 反复选同一张、空转 20 分钟。
        # 现在扫大半个屏幕；靠 expected 只匹配「未激发/未激活/可激发/待激发」，不会误抓其它文字。
        label_roi = tuple(p.get("label_roi", (30, 90, 1220, 580)))
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
        wall_cap = float(p.get("wall_cap", 25))     # 硬上限秒：杜绝「观感卡死」

        clicked = 0
        _clicked = set()          # 已点过的卡（按点击坐标 ±dedup_tol 去重，仅作同屏兜底）
        _picked_titles = _PICKED_TITLES    # 模块级：跨 run() 调用保持，防重复选同一张
        edge_streak = 0           # 连续「边缘卡不可点」次数，防空滑死循环
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
                try:
                    self._save_gb_diag(img, i)   # ⚠️ 必须经 self，裸调用会 NameError
                except Exception as e:
                    mfa_err(_MODULE, "gb_pick_diag", "诊断截图异常（已跳过）", error=e)

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
            # ⚠️ 2026-10-31 实机修正：原实现「点完当前屏所有未点卡」会点到屏幕最右侧
            #   **被裁切的部分可见卡**（实测 @(1170,413) 点下去无效，名额不减 →
            #   点「继续」仍弹「未选择灵感」→ 回环）。改为每轮只点最左一张完整可见的卡，
            #   点完重新截图再判，避免在部分可见卡上做无效点击。
            cands = []
            for box in boxes:
                lx, ly, lw, lh = self._box(box)
                cx = lx + lw / 2
                cy = ly + lh / 2
                x = int(cx)
                y = int(cy + click_y_offset)
                # 右边缘被裁切的卡不点（实测点 @(1141,414) 落到空白/UI 上，无效），
                # 且它在标签附近读到的「标题」会混进右下角「下一节点/推荐等级」等 UI 文字。
                # 只处理标签中心 x ≤ 1050 的完整可见卡。
                if x > 1050 or lx + lw > 1180:
                    continue
                key = (x // dedup_tol * dedup_tol, y // dedup_tol * dedup_tol)
                if key in _clicked:
                    continue
                cands.append((x, y, key))

            if not cands:
                # 有卡但全在屏幕右边缘被裁切 → 左滑把它移到可点区域再试
                # （实机 2026-10-31：只剩一张可选卡且贴右边时，直接点 [1170,413] 无效）
                # 连续多次仍然是边缘卡说明界面上已没有可完整看到的卡，继续滑只是空转。
                if boxes and i < max_look - 1:
                    edge_streak += 1
                    if edge_streak >= 3:
                        mfa_log(_MODULE, "gb_pick", "info",
                                f"连续 {edge_streak} 次边缘卡不可点 → BREAK（已点 {clicked}）")
                        break
                    mfa_log(_MODULE, "gb_pick", "info",
                            f"iter{i} 边缘卡 {len(boxes)} 张不可点 → 左滑露出")
                    self._swipe(context, swipe_begin, swipe_end)
                    time.sleep(swipe_sleep)
                    continue
                # 视野内所有「未激发」卡都已点过
                # （选中后标签可能不消失，仅加 ✓ 金边）→ 视为选满，停止，不盲滑
                mfa_log(_MODULE, "gb_pick", "info", "视野内未激发均已点过 -> BREAK")
                break

            cands.sort(key=lambda c: c[0])          # 左→右
            profile_key = str(p.get("profile", ""))
            table = _load_priority(profile_key)
            if table.get("mode") == "left":
                # 配置一：原样行为——不读卡名，直接取最左一张（零 OCR 风险）
                x, y, key = cands[0]
                mfa_log(_MODULE, "gb_pick", "info", f"#{clicked + 1} 选卡 @({x},{y}) 〔配置一·最左〕")
            else:
                # 配置二/三：先读每张卡的标题，用**标题**去重（坐标去重在滑屏后会失效），
                # 再按优先级表打分选最高。
                read = []
                for (cx_, cy_, key_) in cands:
                    label_cy = cy_ - click_y_offset          # 还原标签中心 y
                    full, titles = self._read_title(context, img, cx_, label_cy)
                    sc_, hit_ = _score_global(full, titles, table)
                    # 用「命中的卡名」去重：同一张卡滑到哪都认得出，比坐标键可靠
                    if hit_ and hit_ in _picked_titles:
                        mfa_log(_MODULE, "gb_pick", "info",
                                f"iter{i} 跳过已选〔{hit_}〕@({cx_},{cy_})")
                        continue
                    read.append((sc_, cx_, cy_, key_, hit_))

                if not read:
                    # 本屏有卡但全是选过的 → 左滑看下一批
                    if i < max_look - 1:
                        mfa_log(_MODULE, "gb_pick", "info",
                                f"iter{i} 本屏 {len(boxes)} 张均已选过 → 左滑")
                        self._swipe(context, swipe_begin, swipe_end)
                        time.sleep(swipe_sleep)
                        continue
                    mfa_log(_MODULE, "gb_pick", "info", "视野内卡片均已选过 -> BREAK")
                    break

                read.sort(key=lambda r: (-r[0], r[1]))     # 分高者优先，同分取左
                sc, x, y, key, hit = read[0]
                if hit:
                    _picked_titles.add(hit)
                mfa_log(_MODULE, "gb_pick", "info",
                        f"#{clicked + 1} 选卡 @({x},{y}) 〔{hit or '未知卡'} 分={sc}〕")
            _clicked.add(key)
            clicked += 1
            edge_streak = 0
            self._click(context, x, y)
            self._click(context, x, y)
            time.sleep(click_sleep)

            # 检查名额是否已用完：读「剩余可选灵感 N」，N==0 立即可收
            img2 = _screencap(context)
            if img2 is not None and self._quota_left(context, img2) == 0:
                mfa_log(_MODULE, "gb_pick", "info", "剩余可选灵感 0 → 名额已满，结束选卡")
                break
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
    def _quota_left(context, img):
        """读底部「剩余可选灵感 N」。命中 N==0 返回 0；识别不到或非 0 返回 None。

        实机 2026-10-31：选中卡后「未激发」标签**不会消失**（只加金边 + ✓），
        所以「找不到未激发」不是可靠的选满信号；底部这个计数器才是。
        """
        try:
            r = context.run_recognition_direct(
                JRecognitionType.OCR,
                JOCR(expected=[r"剩余可选灵感\s*0"],
                     roi=(500, 585, 260, 70), threshold=0.6),
                img,
            )
        except Exception as e:
            mfa_err(_MODULE, "gb_quota", "名额识别异常", error=e)
            return None
        return 0 if (r is not None and r.hit) else None

    @staticmethod
    def _box_tuple(box):
        """Rect → (x, y, w, h)。兼容 dataclass 与 list/tuple。"""
        if box is None:
            return None
        if isinstance(box, (list, tuple)) and len(box) >= 4:
            return (box[0], box[1], box[2], box[3])
        try:
            return (box.x, box.y, box.w, box.h)
        except AttributeError:
            return None

    @staticmethod
    def _ocr_blocks(context, img, roi, threshold: float = 0.3):
        """一次 OCR，返回 [(box, text), ...]（含全部命中块）。

        ⚠️ 2026-11-01 踩坑：`RecognitionDetail` **没有 `.detail` 字段**。
        正确结构是 `all_results: list[RecognitionResult]` / `best_result` / `raw_detail`，
        OCR 的结果项是 `OCRResult(text, box, score)`。
        之前按 `r.detail["all"]` 取文本，拿到的一直是 None，导致卡名全部「未读出」。
        """
        try:
            r = context.run_recognition_direct(
                JRecognitionType.OCR,
                JOCR(expected=[r".+"], roi=roi, threshold=threshold),
                img,
            )
        except Exception as e:
            mfa_warn(_MODULE, "ocr_blocks", f"OCR 异常 roi={roi}: {e!r}")
            return []
        if r is None or not r.hit:
            return []
        out = []
        for res in (getattr(r, "all_results", None) or []):
            text = str(getattr(res, "text", "") or "").strip()
            box = SoCGBPickAvailable._box_tuple(getattr(res, "box", None))
            if text and box:
                out.append((box, text))
        return out

    @staticmethod
    def _read_region(context, img, roi):
        """读任意区域 → (整段文字, 标题候选列表)。标题=2~6 字纯中文块。"""
        blocks = SoCGBPickAvailable._ocr_blocks(context, img, roi)
        labels = ("未激发", "未激活", "可激发", "待激发", "已激发", "激发")
        texts = [t for _b, t in blocks if not any(k in t for k in labels)]
        full = " ".join(texts)
        titles = [t for t in texts
                  if 2 <= len(t) <= 6 and all("\u4e00" <= ch <= "\u9fa5" for ch in t)]
        return full, titles

    def _read_title(self, context, img, label_cx, label_cy):
        """读「未激发」标签所属卡片，返回 (整卡文字, 标题候选列表)。

        ⚠️ 两次实机教训叠加：
        1. 布局不稳定：横排小卡标签在卡片正下方、竖排大卡标签在右下角，固定偏移必错。
        2. 范围一旦放宽到 ±95 就会读到**相邻卡**和界面元素
           （实测出现 `梦渊层 局得分0 … 可选灵感 … 继续 身心调和` 这种混串，
           导致打分和去重全部失真）。

        现在收窄到一卡中线以内（±70），并把 2~6 字纯中文块单独抽出来当「标题候选」：
        标题是卡片上最稳定的信息，用它做 known 精确匹配和去重键，比拿整段文字可靠得多。
        """
        x0 = max(0, int(label_cx) - 70)
        y0 = max(0, int(label_cy) - 250)
        y1 = min(720, int(label_cy) + 250)
        x1 = min(1280, int(label_cx) + 70)
        if x1 <= x0 or y1 <= y0:
            return "", []
        blocks = self._ocr_blocks(context, img, (x0, y0, x1 - x0, y1 - y0))
        labels = ("未激发", "未激活", "可激发", "待激发", "已激发", "激发")
        texts = [t for _b, t in blocks if not any(k in t for k in labels)]
        full = " ".join(texts)
        titles = [t for t in texts
                  if 2 <= len(t) <= 6 and all("\u4e00" <= ch <= "\u9fa5" for ch in t)]
        return full, titles

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
        """OCR 找「未激发」类标签，返回**所有**命中框（空列表表示无）。

        ⚠️ 2026-11-01 关键 bug：原来用 `r.box`，那是 `RecognitionDetail.box` —— **单个最佳框**。
        整屏 5 张卡都带「未激发」时只拿到 1 个，于是永远只认一张卡：
        选它 → 下一轮还是它 → 名额不减 → 反复点同一张，20 分钟空转。
        必须遍历 `filtered_results`（通过 expected 的）或 `all_results`（全部）。
        """
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
        results = (getattr(r, "filtered_results", None)
                   or getattr(r, "all_results", None)
                   or [])
        out = []
        for res in results:
            b = getattr(res, "box", None)
            if b is not None:
                out.append(b)
        return out

    @staticmethod
    def _save_gb_diag(img, i):
        """首轮取证（用于「OCR 全 miss」排查）。

        旧实现走 cv2 → PIL → 裸字节三级回退，而本机两者都不存在，于是写出的
        `.png` 实际是**裸 BGR 字节**（打不开），却打印「截图已保存」。现已统一到
        `agent/evidence.py`（内置零依赖 PNG 编码器 + 元数据 JSON + TTL 清理），
        且只在真正写盘成功时才打日志。
        """
        path = evidence.save_evidence(img, "gb_pick_iter0", level="info",
                                      meta={"iter": i})
        if path:
            mfa_log(_MODULE, "gb_pick_diag", "ok", f"取证已保存: {path}")
        else:
            mfa_warn(_MODULE, "gb_pick_diag", "取证未落盘（evidence=off 或编码失败）")
