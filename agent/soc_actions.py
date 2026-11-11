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
import re
import subprocess
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

# ---------------------------------------------------------------------------
# 全局 Buff 选卡：标签词表
# ---------------------------------------------------------------------------
# 可点击（未固化）的卡
_UNSELECTED_WORDS = ("未激发", "未激活", "可激发", "待激发")
# 已固化的卡。⚠️ 2026-11-09 实机：已固化的卡描述区里**仍会**被 OCR 读到「未激发」
#   （实测 x=136、x=380 两张已固化的卡都读出了「未激发」），
#   所以不能只靠「未激发」筛候选，必须用本列表把同 x 带的卡剔掉。
_FIXED_WORDS = ("固化灵感", "已固化", "固化")

# 缓存 adb 可执行文件与序列号（从 config/instances/default.json 的 AdbDevice 读）
_adb_cache: dict = {}

# ---------------------------------------------------------------------------
# 自由探索轮次状态（券不足时的「免费轮」）
# ---------------------------------------------------------------------------
# 状态机（2026-11-10 设计）：
#   picked=False → SoCTicketLow 判定「券不足且补不满」→ 放行并占位 →
#   SoCTicketFreeGate 命中 → pipeline 走「自由探索」卡（不耗券）→
#   SoCGBPickAvailable 选卡时置 picked=True → 探索进行中 →
#   探索打完回选层 → SoCTicketLow 再次命中且 picked=True → **收工**（自然终态）。
# 30 分钟过期：一轮探索实测 8~19 分钟；过期视为新的一轮/任务，重新放行。
# agent 重启后状态归零：最多多打一轮免费探索，无害。
_FREE_ROUND = {"picked": False, "at": 0.0}
_FREE_ROUND_TTL = 30 * 60      # 秒

# 战斗失败累计次数（模块级：跨 pipeline 重开保持）。
# v2.0.0 只实现了「胜利结算」一条出口，失败页会白等满 max_wait（实测 541s）后中止任务。
# 现在失败即退出本轮并重开；累计到 MAX 次说明是练度/阵容问题，重开也打不过 → 收工，
# 避免无限「失败→重开→失败」烧时间（11-09 那次同一界面循环 8 次烧掉 9 张券就是没上限）。
# 📌 用户确认（2026-11-11）：「终止下潜」**不会清零**已积累的意识碎片 → 失败后终止重开
#    只损失重打的时间，碎片继续累计。所以不需要「先试重新开始节省进度」的软化策略。
_BATTLE_FAILS = {"n": 0}
MAX_BATTLE_FAILS = 2


def _adb_target():
    """解析 (adb 可执行文件, 序列号)；任一项缺失返回 ("", "")。

    优先级：环境变量 MAAEOV_ADB / MAAEOV_ADB_SERIAL → config/instances/default.json
    → config/instances/ 下第一个含 AdbDevice 的实例。
    """
    if _adb_cache.get("resolved"):
        return _adb_cache.get("path", ""), _adb_cache.get("serial", "")

    path = os.environ.get("MAAEOV_ADB", "")
    serial = os.environ.get("MAAEOV_ADB_SERIAL", "")

    if not path or not serial:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        inst_dir = os.path.join(root, "config", "instances")
        candidates = [os.path.join(inst_dir, "default.json")]
        try:
            for name in sorted(os.listdir(inst_dir)):
                if name.endswith(".json"):
                    candidates.append(os.path.join(inst_dir, name))
        except OSError:
            pass
        for cfg in candidates:
            try:
                with open(cfg, encoding="utf-8") as f:
                    dev = (json.load(f) or {}).get("AdbDevice") or {}
            except Exception:
                continue
            path = path or (dev.get("AdbPath") or "")
            serial = serial or (dev.get("AdbSerial") or "")
            if path and serial:
                break

    _adb_cache.update(resolved=True, path=path or "", serial=serial or "")
    return _adb_cache["path"], _adb_cache["serial"]


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
# 战斗失败界面：「战斗失败」标题（2026-11-11 用户实测，简繁两种文案，布局不随角色/关卡变化）
_BATTLE_FAIL_ROI = (872, 186, 270, 72)


@AgentServer.custom_recognition("SoCTicketLow")
class SoCTicketLow(CustomRecognition):
    """剩余入场券不足以打满 1000 分时命中 → 收尾结束。

    为什么阈值是 2：一层只有 500 分，打满 1000 需要 **2 轮 = 2 张券**。
    券只剩 1 张时开始新一轮必然打不满，纯亏券和 8~19 分钟，不如直接收。
    （实测 2026-11-01：券 10 → 打满用掉 2 张，验证了「2 张/满额」这个换算。）

    ⚠️ 2026-11-09 修正（原实现是纯固定阈值，会误伤）：
      只按「券 < 2 就收工」判会漏掉「券 1 张但只差一点点就满」的情况。
      现在券数不足时**再读左下角当前积分**，按每轮保守 `MIN_GAIN`(=355，实测最差一轮)
      折算：只要 `券数 × 355 ≥ 1000 − 当前分` 就放行，继续打。
      读不到积分时退回原行为（收工），不会因为新增判据变得更冒险。

    券数的显示：选层界面**右上角**「券图标 + 数字」（约 1280×720 的 (1114, 36)）。
    只有选层界面才有这个数字，所以本节点只挂在进选层之后的位置，不在 Resume 首位——
    否则在其它界面（主界面右上角是资源数）可能误读成 1 而提前收工。
    """

    # 券图标 + 数字只在右上角这么一小块（实测原图约 (1175,28)-(1225,52)，数字高仅 ~18px）
    TICKET_ROI = (1168, 20, 76, 40)
    MIN_TICKETS = 2
    # 本期入场券上限（实测一期 10 张）。留一倍余量：读到比这更大的数，
    # 说明 ROI 框到了相邻的资源数字（实机 2026-11-11 读到过 20290 / 81），整条作废。
    MAX_SANE_TICKETS = 20
    # 单轮保守得分：实测一轮 355~500 分，取最差值做下界，避免高估导致白跑一轮
    MIN_GAIN = 355
    # 左下角「意识碎片 N/1000」（与 _SoCScoreFull 同一 ROI，该区域已实测可读）
    SCORE_ROI = (20, 630, 250, 82)
    ZOOM = 4          # 小字直接 OCR 读不出（实测返回空），先放大再识别

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        roi = self.TICKET_ROI
        img = getattr(argv, "image", None)
        if img is None:
            img = _screencap(context)
        if img is None:
            return None

        # min_tickets 可由 pipeline 的 recognition.param 覆盖
        #（实机测试券 1 张时传 1 放行自由探索；发版默认仍为 2，不进任何文件）
        min_tickets = self.MIN_TICKETS
        try:
            extra = json.loads(getattr(argv, "custom_recognition_param", "") or "{}")
            if isinstance(extra, dict) and "min_tickets" in extra:
                min_tickets = max(0, int(extra["min_tickets"]))
        except Exception:
            pass

        n, text = self._read_tickets(context, img)
        if n is None:
            if text is not None:
                mfa_warn(_MODULE, "ticket_low", f"券数读不到（roi={roi}，OCR={text!r}）→ 不判定")
            return None
        mfa_log(_MODULE, "ticket_low", "info", f"券数读数={n}（阈值 {min_tickets}，OCR={text!r}）")
        if n >= min_tickets:
            return None

        # --- 券不足：先看「剩下的券够不够补满」，够就放行 ---
        score = self._read_score(context, img)
        if score is not None:
            cur, full = score
            need = full - cur
            gain = n * self.MIN_GAIN
            mfa_log(_MODULE, "ticket_low", "info",
                    f"券 {n} 张 × 每轮 {self.MIN_GAIN} = {gain} 分，还需 {need} 分（{cur}/{full}）")
            if need <= 0:
                # 已满：交给 _SoCScoreFull 收工，这里不重复判
                return None
            if gain >= need:
                mfa_log(_MODULE, "ticket_low", "info",
                        f"券不足 {min_tickets} 但可补满（{gain} ≥ {need}）→ 放行继续打")
                return None
        else:
            mfa_warn(_MODULE, "ticket_low", "积分读不到 → 无法折算，按免费轮处理")

        # --- 补不满：自由探索轮次状态机 ---
        # picked=False（还没进过免费轮）→ 放行，由 SoCTicketFreeGate 引导走自由探索；
        # picked=True（免费轮已打完回选层，或探索异常超时）→ 收工，这是券不足任务的**自然终态**。
        if _FREE_ROUND["picked"]:
            overtime = time.time() - _FREE_ROUND["at"] >= _FREE_ROUND_TTL
            _FREE_ROUND.update(picked=False, at=0.0)
            mfa_log(_MODULE, "ticket_low", "ok",
                    "自由探索一轮已完成" + ("（超 30 分钟，异常兜底）" if overtime else "")
                    + " → 券不足且补不满，结束任务返回主界面")
            return CustomRecognition.AnalyzeResult(
                box=tuple(roi), detail=f"tickets={n},free_round_done"
            )

        _FREE_ROUND.update(picked=False, at=time.time())
        mfa_log(_MODULE, "ticket_low", "info",
                "券不足且补不满 → 放行走一轮自由探索（不耗券，探索完成后再收工）")
        return None

    @classmethod
    def _read_tickets(cls, context, img):
        """读右上角券数 → (数字|None, 原始文本)。识别异常返回 (None, None)。

        ⚠️ 2026-11-11 实机（用户反馈 §9）：`TICKET_ROI=(1168,20,76,40)` 会框到**相邻字符**，
        原实现把所有数字字符直接拼接，于是：
          OCR='20,290'（框到了主界面资源数）→ 读成 20290
          OCR='8 1'                          → 读成 81   → 误判「券够」→ 走深潜烧券
          OCR='电 1'                         → 读成 1    （侥幸正确）
        修法：按独立数字段解析 + **上界校验**，任何一个数字段超过本期上限就整条作废
        （说明框到了别的数字），否则取最右一段（券图标在左、数字在右）。
        """
        roi = cls.TICKET_ROI
        try:
            import numpy as np
            x, y, w, h = roi
            crop = np.asarray(img)[y:y + h, x:x + w]
            if crop.size == 0:
                mfa_warn(_MODULE, "ticket_low", f"券数区域越界 roi={roi}")
                return None, None
            big = np.repeat(np.repeat(crop, cls.ZOOM, axis=0), cls.ZOOM, axis=1)
            zoom_roi = (0, 0, big.shape[1], big.shape[0])
            blocks = SoCGBPickAvailable._ocr_blocks(context, big, zoom_roi, threshold=0.2)
        except Exception as e:
            mfa_err(_MODULE, "ticket_low", "券数识别异常", error=e)
            return None, None

        text = " ".join(t for _b, t in blocks).strip()
        vals = [int(t) for t in re.findall(r"\d+", text)]
        if not vals:
            return None, text
        if any(v > cls.MAX_SANE_TICKETS for v in vals):
            mfa_warn(_MODULE, "ticket_low",
                     f"券数区域读到超上限数字 {vals}（上限 {cls.MAX_SANE_TICKETS}，OCR={text!r}）"
                     f"→ 判为框错，不判定")
            return None, text
        return vals[-1], text

    @classmethod
    def _read_score(cls, context, img):
        """读左下角「意识碎片 N/1000」→ (当前, 上限)；读不到返回 None。"""
        try:
            r = context.run_recognition_direct(
                JRecognitionType.OCR,
                JOCR(expected=[r"\d+\s*[/／]\s*\d+"], roi=cls.SCORE_ROI, threshold=0.5),
                img,
            )
        except Exception as e:
            mfa_warn(_MODULE, "ticket_low", f"积分识别异常: {e!r}")
            return None
        if r is None or not r.hit:
            return None
        results = (getattr(r, "filtered_results", None)
                   or getattr(r, "all_results", None) or [])
        for res in results:
            text = str(getattr(res, "text", "") or "")
            m = re.search(r"(\d{1,4})\s*[/／]\s*(\d{3,4})", text)
            if m:
                cur, full = int(m.group(1)), int(m.group(2))
                if 0 <= cur <= full:
                    return cur, full
        return None


@AgentServer.custom_recognition("SoCTicketFreeGate")
class SoCTicketFreeGate(CustomRecognition):
    """券不足且补不满 → 命中 → pipeline 跳过「深潜指引」、改走「自由探索」（不耗券）。

    挂在 SoCResume.next 里 SoCDeepDive 之前：
      · 券充足 / 能补满 → miss → 正常走深潜指引（原行为）
      · 券不足且补不满 → 命中 → next 到 SoCDeepDiveFree
    为什么不读「暂不可用」遮罩：券数 + 积分折算已实测可靠（2026-11-10），
    且二选一弹窗可能遮住券数区域——本节点**不截图读券**，复用 SoCTicketLow
    放行时设置的 `_FREE_ROUND` 占位标记，弹窗时也能命中。

    状态机（详见模块级 `_FREE_ROUND` 注释）：
      SoCTicketLow 放行（占位）→ 本节点命中 → 走 Free → 选卡置 picked →
      探索完成回选层 → SoCTicketLow 收工。收工优先于本节点（next 顺序保证）。
    """

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        # 占位标记存在（picked=False 且 at 新鲜）→ 引导走 Free；
        # picked=True（探索进行中/打完）→ miss，收工由 SoCTicketLow 负责。
        fresh = time.time() - _FREE_ROUND["at"] < _FREE_ROUND_TTL
        if not (_FREE_ROUND["at"] > 0 and fresh and not _FREE_ROUND["picked"]):
            return None

        # 加固（2026-11-10）：积分已满时**绝不**引导免费轮。
        # 防的是「SoCTicketLow 那句积分 OCR 恰好失败 → 按免费轮放行」时，
        # 实际积分已经 1000/1000 却被引去白打一轮。读不到积分不拦（那是正常路径）。
        img = getattr(argv, "image", None)
        if img is None:
            img = _screencap(context)
        if img is not None:
            score = SoCTicketLow._read_score(context, img)
            if score is not None and score[0] >= score[1]:
                mfa_log(_MODULE, "free_gate", "ok",
                        f"积分已满（{score[0]}/{score[1]}）→ 不引导自由探索，交给完成判定收工")
                return None

        mfa_log(_MODULE, "free_gate", "info",
                "券不足放行标记生效 → 引导走自由探索（跳过深潜指引）")
        return CustomRecognition.AnalyzeResult(
            box=(1100, 0, 180, 720), detail="free_round_pending"
        )


@AgentServer.custom_recognition("SoCBattleFailGiveUp")
class SoCBattleFailGiveUp(CustomRecognition):
    """战斗失败累计已达上限 → 命中 → 退出本轮后**不再重开**，直接收工。

    链路（2026-11-11 新增）：
      SoCAwaitBattle 检测到失败 → 计数 +1 → return False
      → SoCAutoBattle.on_error = [_SoCBattleFailed, _StopTask]
      → _SoCBattleFailed（OCR 失败页）→ _SoCAbandonDive（终止下潜 → 确认 → 结算）
      → _SoCAbandonResult.next 里本节点排在 SoCSelectLayer 之前：
            命中（失败已达上限）→ _SoCReturnHome 收工
            miss（还能再试）    → 正常重新选层重开一轮

    上限存在的意义：失败多半是练度/阵容问题，重开也可能继续输。
    没有上限就是「失败 → 重开 → 再失败 → …」无限循环（11-09 同一界面循环 8 次
    烧掉 9 张券就是这么来的）。
    """

    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        n = _BATTLE_FAILS["n"]
        if n < MAX_BATTLE_FAILS:
            return None
        mfa_log(_MODULE, "battle_fail", "skip",
                f"战斗失败已达上限（{n}/{MAX_BATTLE_FAILS}）→ 不再重开，收工回主界面")
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 1, 1), detail=f"battle_fails={n}"
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
                # 本轮正常打完 → 失败计数归零：只有「连续/同一轮内反复失败」才该收工，
                # 上一轮失败过、这一轮打赢了不算。
                if _BATTLE_FAILS["n"]:
                    mfa_log(_MODULE, "await_battle", "info",
                            f"本轮正常结束 → 战斗失败计数 {_BATTLE_FAILS['n']} → 归零")
                    _BATTLE_FAILS["n"] = 0
                mfa_log(_MODULE, "await_battle", "ok",
                        "已退回选层界面 → 本轮节点已全部完成，正常结束等待")
                return True

            # c3) 战斗失败（2026-11-11 用户反馈 §0：v2.0.0 只有胜利出口）
            # 失败界面停在「战斗失败 / 重新开始 / 终止下潜」，下面 d) 的「继续」永远等不到，
            # 原实现会白等满 max_wait（实测 541s，占整轮 21%）后才中止任务，且失败被记成成功。
            # 这里只**检测 + 计数**，不点任何按钮：把界面留给 pipeline 的 _SoCBattleFailed
            # （点「终止下潜」→ 确认 → 结算 → 回选层），避免 agent 与 pipeline 各点一次。
            fail = context.run_recognition_direct(
                JRecognitionType.OCR,
                JOCR(expected=["战斗失败", "戰鬥失敗"], roi=_BATTLE_FAIL_ROI, threshold=0.7),
                img,
            )
            if fail is not None and fail.hit:
                _BATTLE_FAILS["n"] += 1
                n = _BATTLE_FAILS["n"]
                shot = evidence.save_evidence(
                    img, "battle_failed", roi=_BATTLE_FAIL_ROI,
                    meta={"fail_count": n, "elapsed_s": round(time.time() - start, 1),
                          "max_battle_fails": MAX_BATTLE_FAILS},
                )
                mfa_log(_MODULE, "await_battle", "skip",
                        f"检测到「战斗失败」（第 {n}/{MAX_BATTLE_FAILS} 次，已等待 "
                        f"{time.time() - start:.0f}s）→ 交 pipeline 终止下潜"
                        f"（取证: {shot or '未落盘'}）",
                        fail_count=n)
                return False

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
    """全局 Buff 选卡（OCR 定位 + 像素差分验证，内部轮询）。

    设计动机（2026-09-14 迭代历程总结）：
      · GB1~5 模板匹配已选/未选卡标题 → 已选中卡标题一致 → 误点已选卡 → 死循环
      · 218×95 标题裁切模板匹配分 0.40~0.53（阈值 0.8 全 miss / 0.5 勉强 1 张）
      · 234×160 autodori 全卡面源图匹配分 0.18~0.29（**更差**，RGBA/渲染差异）
      · fallback 点 (label_cx, label_cy-100) ≈ y=374 落在描述文字区 → 点击无效

    ✅ 当前方案（2026-11-09 重写）：
      Step 1 — 一次 OCR 拿整块标签区：matched「未激发」= 候选，「固化灵感」= 已选/不可选
      Step 2 — 按 x 带剔除已固化卡上的「未激发」误读框（那些框在描述区，点了白费）
      Step 3 — **单击一次**（原实现连点两次，在「点击切换选中」的卡上等于选中后又取消，
               这是「已点=8 却一张没选上」的直接原因），随后用**点击前/后像素差分**
               判定是否真的变了（金边+✓ 的色差足够）；判无效才换 adb tap 通道重试一次
      Step 4 — 终止：连续 max_fail 次点击不生效（名额满）/ 连续 max_no_find 轮无新候选（滑屏兜底）
               / 超 wall_cap → 结束。返回 clicked>0 让 pipeline 去点「继续」。

    ⚠️ 「是否选中」只能靠像素差分：底部「剩余可选灵感 N」的数字 OCR 读不出（文字能读到、
      数字整块丢失），「固化灵感」计数也不随选中变化 —— 这两个旧判据都已废弃。

    为什么不用模板：
      三种模板（标题裁切/全卡面源图/autodori 原图）在实机上匹配分均 < 0.53，
      且动态池大部分卡不在已知列表中 → 模板门控只会阻碍选卡。
      OCR「未激发」score 稳定 0.999、定位精确到像素 → 是唯一可靠信号。
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        p = _parse_param(argv.custom_action_param)
        # OCR：「未激发」标签所在区域
        # ⚠️ 2026-11-01 实机：标签位置**随布局变化**，不能写死。
        #   · 横排小卡：「未激发」在卡片正下方，y≈480；
        #   · 竖排大卡：「未激发」在卡片右下角，y≈153。
        # 所以仍然扫大半个屏幕；靠 expected 只匹配「未激发/未激活/可激发/待激发」，
        # 卡外误读由后面的「固化剔除 + 像素差分验证」兜住，不再靠收窄 ROI 硬挡。
        label_roi = tuple(p.get("label_roi", (30, 90, 1220, 580)))
        label = p.get("label", list(_UNSELECTED_WORDS))
        fixed_label = p.get("fixed_label", list(_FIXED_WORDS))
        max_look = int(p.get("max_iter", 12))       # 最多几轮（每轮=一次 OCR+至多一次点击）
        max_no_find = int(p.get("max_no_find", 3))  # 连续几轮无候选 → 判定选满
        swipe_begin = tuple(p.get("swipe_begin", (1270, 360)))
        swipe_end = tuple(p.get("swipe_end", (870, 360)))
        # 点击偏移：标签中心向上多少像素。
        # ⚠️ 2026-11-09：标签在 y≈463~486，原来 -60 落在 **描述文字区（y≈414）**，
        #   实测点了没反应（旧 fallback 点 y≈374 同样无效）。
        #   卡片图标区在 y≈190~300，取 -180 → y≈294（adb 手点验证过这个高度有效）。
        click_y_offset = int(p.get("click_y_offset", -180))
        click_sleep = float(p.get("click_sleep", 0.55))
        swipe_sleep = float(p.get("swipe_sleep", 1.0))
        # 去重容差（卡片宽 ~236，相邻卡间距 ~400）
        dedup_tol = int(p.get("dedup_tol", 60))
        wall_cap = float(p.get("wall_cap", 60))     # 硬上限秒：杜绝「观感卡死」
        # 点击生效判据：点前/点后裁同一张卡做平均绝对差（0~255 尺度）
        # 实机 2026-11-09：真实选中的差分 9.5~22.5，阈值 1.5 余量充足
        diff_thr = float(p.get("diff_thr", 1.5))
        card_w = int(p.get("card_w", 236))          # 卡片可见宽度，用于裁差分 ROI
        # 固化剔除的 x 容差：同一张卡的「固化灵感」标签与「未激发」误读框横向距离很小，
        # 而相邻卡标签中心间距 244px（半距 122）→ 取 110 既覆盖同卡偏移，也不会误剔邻卡。
        fixed_tol = int(p.get("fixed_tol", 110))
        max_fail = int(p.get("max_fail", 3))        # 连续几次点击未生效 → 认为名额已满
        # 名额上限：成功选中数达到即停。
        # ⚠️ 实机 2026-11-09：滑屏后坐标去重失效（同一张卡换个 x 就认不出），
        #   配置一「最左」模式把已选中的卡又点了一遍 → **取消选中**，实测溢出到 8 次。
        #   名额是硬上限（一屏最多 5 张），到数就收，比任何视觉判据都可靠。
        max_picks = int(p.get("max_picks", 5))
        use_quota = bool(p.get("use_quota", False)) # 「剩余可选灵感 N」OCR 实测读不出数字，默认关
        allow_adb = bool(p.get("adb_tap", True))    # 框架点击未生效时用 adb shell input tap 兜底

        clicked = 0
        _clicked = []             # 已点过的卡（真实坐标）。⚠️ 不能用 //tol 桶：桶边界会把
        _failed = []              #   相差 16px 的同一张卡拆进两个桶（实机 2026-11-10：
        _picked_titles = _PICKED_TITLES    #   @(184,294) 与 @(168,294) 是同一张卡却各点一次，
        no_find = 0                          #   第二次点击把刚选中的卡取消掉）。用真实距离比较。
        fails = 0
        start = time.time()

        def _seen(x, y):
            return (any(abs(x - px) <= dedup_tol and abs(y - py) <= dedup_tol
                        for px, py in _clicked)
                    or any(abs(x - px) <= dedup_tol and abs(y - py) <= dedup_tol
                           for px, py in _failed))

        # 选卡发生 = 已进入一次探索（自由探索轮次状态机：picked → 回选层后收工）
        _FREE_ROUND.update(picked=True, at=time.time())

        mfa_log(
            _MODULE, "gb_pick", "info",
            f"START (OCR+差分验证) label_roi={label_roi} max_look={max_look} "
            f"click_y_offset={click_y_offset} diff_thr={diff_thr} "
            f"fixed_tol={fixed_tol} adb_tap={allow_adb} wall_cap={wall_cap}",
        )

        for i in range(max_look):
            if context.tasker.stopping:
                mfa_log(_MODULE, "gb_pick", "warn", "STOP")
                return False
            if time.time() - start > wall_cap:
                mfa_warn(_MODULE, "gb_pick", f"超 wall_cap={wall_cap}s 强制结束")
                break
            if clicked >= max_picks:
                mfa_log(_MODULE, "gb_pick", "info",
                        f"已选 {clicked} 达名额上限 {max_picks} → 结束选卡")
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
            # Step 1: OCR 整块标签区 → 未激发候选 + 已固化卡
            # ════════════════════════════════════════════
            unsel, fixed = self._scan_labels(context, img, label, fixed_label, label_roi)
            boxes = self._drop_fixed(unsel, fixed, fixed_tol)
            mfa_log(_MODULE, "gb_pick", "info",
                    f"iter{i} 未激发={len(unsel)} 已固化={len(fixed)} 有效候选={len(boxes)} "
                    f"已选={clicked} 失败={fails}")

            # 过滤出尚未点过 / 未失败的卡
            # ⚠️ 2026-10-31 实机：屏幕最右侧**被裁切的部分可见卡**点了无效
            #   （实测 @(1170,413) 名额不减 → 点「继续」仍弹「未选择灵感」→ 回环）。
            #   ⚠️ 2026-11-10 实机：左边缘同样有这个问题——左滑后部分可见卡标签 x=58 与
            #   完整卡 x=76 只差 18px，点 76 选中后再点 58 等于**取消选中**（差分照样非零，
            #   差分判据识别不出"取消"），名额白耗。两侧都要挡：
            #   标签中心必须在 [130, 1050] 内（130 ≈ 半卡宽 118 + 余量），且右边界 ≤ 1180。
            cands = []
            for box in boxes:
                lx, ly, lw, lh = self._box(box)
                cx = lx + lw / 2.0
                cy = ly + lh / 2.0
                x = int(cx)
                y = int(cy + click_y_offset)
                # 竖排大卡标签在卡片右下角（y≈153），-180 会算出 y<0 的越界点击
                #（实机 2026-11-10：@(594,6) 点在屏幕顶端，framework/adb 都无效）。
                # 夹进屏幕并保证落在卡片区，失败交给差分判据兜底。
                y = max(120, min(700, y))
                if x > 1050 or x < 130 or lx + lw > 1180:
                    continue
                if _seen(x, y):
                    continue
                cands.append((x, y, int(cx), int(cy), int(lh)))

            if not cands:
                # 本屏候选已点完/已失败（或根本没有）→ 左滑看下一批
                no_find += 1
                if no_find >= max_no_find or i >= max_look - 1:
                    mfa_log(_MODULE, "gb_pick", "info",
                            f"连续 {no_find} 轮无新候选 -> BREAK（已选 {clicked}）")
                    break
                mfa_log(_MODULE, "gb_pick", "info", "iter%d 无新候选 → 左滑" % i)
                self._swipe(context, swipe_begin, swipe_end)
                time.sleep(swipe_sleep)
                continue
            no_find = 0

            cands.sort(key=lambda c: c[0])          # 左→右
            profile_key = str(p.get("profile", ""))
            table = _load_priority(profile_key)
            if table.get("mode") == "left":
                # 配置一：原样行为——不读卡名，直接取最左一张（零 OCR 风险）
                x, y, tcx, tcy, tlh = cands[0]
                hit = ""
                mfa_log(_MODULE, "gb_pick", "info", f"#{clicked + 1} 选卡 @({x},{y}) 〔配置一·最左〕")
            else:
                # 配置二/三：先读每张卡的标题，用**标题**去重（坐标去重在滑屏后会失效），
                # 再按优先级表打分选最高。
                read = []
                for (cx_, cy_, tcx, tcy, tlh) in cands:
                    label_cy = cy_ - click_y_offset          # 还原标签中心 y
                    full, titles = self._read_title(context, img, tcx, label_cy)
                    sc_, hit_ = _score_global(full, titles, table)
                    if hit_ and hit_ in _picked_titles:
                        mfa_log(_MODULE, "gb_pick", "info",
                                f"iter{i} 跳过已选〔{hit_}〕@({cx_},{cy_})")
                        continue
                    read.append((sc_, cx_, cy_, hit_, tcx, tcy, tlh))

                if not read:
                    no_find += 1
                    if no_find >= max_no_find or i >= max_look - 1:
                        mfa_log(_MODULE, "gb_pick", "info",
                                f"本屏 {len(boxes)} 张均已选过 -> BREAK（已选 {clicked}）")
                        break
                    mfa_log(_MODULE, "gb_pick", "info",
                            f"iter{i} 本屏 {len(boxes)} 张均已选过 → 左滑")
                    self._swipe(context, swipe_begin, swipe_end)
                    time.sleep(swipe_sleep)
                    continue

                read.sort(key=lambda r: (-r[0], r[1]))     # 分高者优先，同分取左
                sc, x, y, hit, tcx, tcy, tlh = read[0]
                mfa_log(_MODULE, "gb_pick", "info",
                        f"#{clicked + 1} 选卡 @({x},{y}) 〔{hit or '未知卡'} 分={sc}〕")

            # ════════════════════════════════════════════
            # Step 2: 单击 + 像素差分验证（这是唯一可信的「选中与否」判据）
            # ⚠️ 2026-11-09 核心修正：原实现连调两次 _click（无间隔）。
            #   若卡片是「点击切换选中」，双击 = 选中后立刻取消 →
            #   8 次点击 = 4 轮选中+取消 = 一张都不剩，完美对应日志「已点=8 但未选到灵感」。
            #   改为**单击**，并用点击前后像素差分确认是否真的变了（金边+✓ 会带来明显色差）。
            # ════════════════════════════════════════════
            roi = self._card_roi(tcx, tcy, tlh, card_w)
            ok, d, via = self._tap_and_verify(
                context, img, x, y, roi, diff_thr, click_sleep, allow_adb,
            )
            mfa_log(_MODULE, "gb_pick", "info" if ok else "warn",
                    f"点击 @({x},{y}) 生效={ok} 差分={'-' if d is None else round(d, 2)} "
                    f"(阈值 {diff_thr}) 通道={via}")

            if ok:
                _clicked.append((x, y))
                if hit:
                    _picked_titles.add(hit)
                clicked += 1
                fails = 0
            else:
                # 点不动：可能这张卡已固化/名额已满/坐标落在空白 → 换下一张，不重复点
                _failed.append((x, y))
                fails += 1
                if fails >= max_fail:
                    mfa_log(_MODULE, "gb_pick", "info",
                            f"连续 {fails} 次点击未生效 → 名额已满或无可选卡，结束选卡")
                    break

            # 可选：读「剩余可选灵感 N」（实测数字 OCR 读不出，默认关闭）
            if use_quota:
                img2 = _screencap(context)
                if img2 is not None and self._quota_left(context, img2) == 0:
                    mfa_log(_MODULE, "gb_pick", "info", "剩余可选灵感 0 → 名额已满，结束选卡")
                    break

        mfa_log(
            _MODULE, "gb_pick", "ok",
            f"END 已选={clicked} (return {clicked > 0})",
        )
        return clicked > 0

    # ------------------------------------------------------------------
    # 视觉判据：点击到底有没有生效
    # ------------------------------------------------------------------
    @staticmethod
    def _card_roi(cx, label_cy, label_h, card_w):
        """由标签位置反推整卡差分区域 (x, y, w, h)，夹紧到 1280×720。

        卡片主体在标签**上方**约 280px 内；差分要覆盖卡片边缘（金边框出现在边缘），
        所以横向取整卡宽度而不是只取中心。
        """
        half = card_w / 2.0
        x0 = int(max(0, cx - half))
        x1 = int(min(1280, cx + half))
        y0 = int(max(0, label_cy - 280))
        y1 = int(min(720, label_cy + label_h + 12))
        if x1 - x0 < 8 or y1 - y0 < 8:
            return None
        return (x0, y0, x1 - x0, y1 - y0)

    @staticmethod
    def _diff(a, b, roi):
        """两帧在 roi 内的平均绝对差（0~255 尺度）；不可比时返回 None。"""
        try:
            import numpy as np
        except Exception:
            return None
        if a is None or b is None or roi is None:
            return None
        x, y, w, h = (int(v) for v in roi)
        try:
            aa = np.asarray(a)
            bb = np.asarray(b)
        except Exception:
            return None
        if aa.ndim == 3 and bb.ndim == 3 and aa.shape[2] != bb.shape[2]:
            n = min(aa.shape[2], bb.shape[2])
            aa, bb = aa[:, :, :n], bb[:, :, :n]
        try:
            aa = aa[y:y + h, x:x + w]
            bb = bb[y:y + h, x:x + w]
        except Exception:
            return None
        if aa.size == 0 or aa.shape != bb.shape:
            return None
        return float(np.abs(aa.astype(np.int16) - bb.astype(np.int16)).mean())

    def _tap_and_verify(self, context, before, x, y, roi, thr, sleep, allow_adb):
        """**单击一次** → 截图 → 差分 → 未生效才换 adb 通道重试一次。

        返回 (是否生效, 差分值, 使用的通道)。

        ⚠️ 关键：判定失败时会先多等一拍再测一次才换通道。
        因为「误判失败 → adb 再点一次」在「点击切换选中」的卡片上等于**把刚选中的卡取消掉**，
        比不点更糟。
        """
        self._click(context, x, y)          # 单击，绝不连点
        time.sleep(sleep)
        after = _screencap(context)
        d = self._diff(before, after, roi)
        if d is not None and d >= thr:
            return True, d, "framework"

        # UI 动画/淡入可能还没落定 → 再等一拍复测
        time.sleep(0.5)
        after2 = _screencap(context)
        d2 = self._diff(before, after2, roi)
        if d2 is not None and d2 >= thr:
            return True, d2, "framework"

        if allow_adb and self._adb_tap(context, x, y):
            time.sleep(sleep + 0.3)
            after3 = _screencap(context)
            d3 = self._diff(before, after3, roi)
            return bool(d3 is not None and d3 >= thr), d3, "adb"

        return False, (d2 if d2 is not None else d), "framework"

    @staticmethod
    def _adb_tap(context, x, y):
        """用 adb shell input tap 点一次（绕开 MaaFW 的 EmulatorExtras 输入通道）。

        2026-11-09 实测对照：同一坐标 adb tap 生效、post_click 无效，
        所以当框架点击被差分判定为「没生效」时，这里作为第二通道再试一次。
        任一步失败都返回 False 且不抛异常——adb 只是兜底，不能成为新的失败点。
        """
        path, serial = _adb_target()
        if not path or not serial:
            mfa_warn(_MODULE, "gb_adb", "未找到 adb 路径/序列号 → 跳过 adb 兜底")
            return False
        if not os.path.exists(path):
            mfa_warn(_MODULE, "gb_adb", f"adb 不存在: {path} → 跳过 adb 兜底")
            return False
        try:
            kwargs = {}
            if os.name == "nt":
                kwargs["creationflags"] = 0x08000000   # CREATE_NO_WINDOW
            subprocess.run(
                [path, "-s", serial, "shell", "input", "tap", str(int(x)), str(int(y))],
                capture_output=True, timeout=6, **kwargs,
            )
            return True
        except Exception as e:
            mfa_warn(_MODULE, "gb_adb", f"adb tap 失败 ({x},{y}): {e!r}")
            return False

    # ------------------------------------------------------------------
    # 标签扫描 / 固化剔除
    # ------------------------------------------------------------------
    @staticmethod
    def _scan_labels(context, img, label, fixed_label, label_roi):
        """一次 OCR 拿整个标签区 → (未激发候选框, 已固化框)。

        2026-11-09：已固化的卡**也会**在描述区被读到「未激发」，
        所以必须同时收集「固化灵感」框，交给 `_drop_fixed` 按 x 带剔除，
        否则「取最左」会反复点在已固化的卡上白耗次数。
        """
        if isinstance(label, str):
            label = [label]
        if isinstance(fixed_label, str):
            fixed_label = [fixed_label]
        blocks = SoCGBPickAvailable._ocr_blocks(context, img, label_roi)
        unsel, fixed = [], []
        for box, text in blocks:
            if any(w and w in text for w in (fixed_label or [])):
                fixed.append(box)
            elif any(w and w in text for w in (label or [])):
                unsel.append(box)
        return unsel, fixed

    @staticmethod
    def _drop_fixed(unsel, fixed, tol):
        """剔除与「固化灵感」标签同一张卡（x 中心距离 ≤ tol）的「未激发」误读框。"""
        if not fixed:
            return list(unsel)
        fcx = [b[0] + b[2] / 2.0 for b in fixed]
        out = []
        for box in unsel:
            cx = box[0] + box[2] / 2.0
            if any(abs(cx - fc) <= tol for fc in fcx):
                continue
            out.append(box)
        return out

    @staticmethod
    def _quota_left(context, img):
        """读底部「剩余可选灵感 N」。命中 N==0 返回 0；识别不到或非 0 返回 None。

        ⚠️ 2026-11-09 实测：这个数字**读不出来**（文字读到、数字整块丢失，
        ROI 480,570,320,90 与放大 3× 两种方式都返回 None）→ 默认不启用（use_quota=false），
        改用「点击前后像素差分」判断是否还有可选的卡。
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
        """【已弃用】旧版「只取标签框」的扫描入口，保留仅作历史兼容。

        现在统一走 `_scan_labels`——它一次 OCR 同时拿到「未激发」与「固化灵感」两类框，
        才能按 x 带剔除已固化卡上的「未激发」误读。

        ⚠️ 2026-11-01 关键教训（已并入 `_ocr_blocks`）：原来用 `r.box`，
        那是 `RecognitionDetail.box` —— **单个最佳框**。整屏 5 张卡都带「未激发」时
        只拿到 1 个 → 永远只认一张卡 → 反复点同一张、20 分钟空转。
        必须遍历 `filtered_results`（通过 expected 的）或 `all_results`（全部）。
        """
        if isinstance(label, str):
            label = [label]
        return [b for b, _t in SoCGBPickAvailable._ocr_blocks(context, img, label_roi)]

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
