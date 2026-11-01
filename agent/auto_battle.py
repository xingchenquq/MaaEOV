"""自动推图 CustomAction（MaaEOV1）

提供的 CustomAction：
- 播报进度：任务开始提醒 + 关卡进度（第 N 关 开始/结束、已完成 M 关、战斗失败停止）
- 连点退出：结算界面连点 (640,30) 若干次以退出

【经验】agent 侧 `context.run_recognition("OCR", img, ...)` 的 `entry` 必须是
pipeline 里**已存在**的节点名；否则识别压根不启动、返回 None / 空结果
（本例就踩过：项目里没有名为 "OCR" 的节点）。所以选队伍等识别都改用
pipeline 内联识别（TemplateMatch / OCR）+ Click 的 target_offset 偏移点击。
"""
import json
import struct
import time
import zlib
from pathlib import Path

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from mfalog import mfa_log, mfa_err, mfa_warn

_MODULE = "自动推图"

# 诊断截图输出目录（与 main.py 的 agent.log 同处：<MaaEOV1>/debug）
_DEBUG_DIR = Path(__file__).resolve().parent.parent / "debug"


def _parse_param(raw):
    """把 custom_action_param 解析成 dict，兼容已解析 dict / 字符串 / 双重 JSON 编码。"""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            val = json.loads(raw or "{}")
            # 某些运行器会对字符串再次 JSON 编码，导致第一次 loads 后还是字符串
            if isinstance(val, str):
                val = json.loads(val)
            return val if isinstance(val, dict) else {}
        except Exception:
            pass
    return {}


# 关卡进度计数（agent 生命周期内累计；每次"加载项目"归零）
_PROGRESS = {"current": 0, "done": 0}


@AgentServer.custom_action("播报进度")
class ReportProgress(CustomAction):
    """打印关卡进度，让 exe 日志更直观。

    参数（JSON）stage: "notice" | "start" | "win" | "nostar" | "fail" | "done"
      - notice: 任务开始前的前提提醒
      - start : 第 N 关 开始
      - win   : 第 N 关 结束（战斗胜利），已完成 +1
      - nostar: 第 N 关 结束（未满星），已完成 +1
      - fail  : 第 N 关 结束（战斗失败），不计入已完成，任务停止
      - done  : 未找到未完成关卡（已全部推完），任务正常结束
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        stage = str(_parse_param(argv.custom_action_param).get("stage", "start"))
        if stage == "notice":
            msg = "未做自动吃体力配置，请确保体力充足。"
        elif stage == "start":
            _PROGRESS["current"] += 1
            msg = f"===== 第 {_PROGRESS['current']} 关 · 开始 ====="
        elif stage == "done":
            msg = (
                f"===== 未找到未完成关卡，推图完成！"
                f"本次共完成 {_PROGRESS['done']} 关 ====="
            )
        elif stage == "fail":
            msg = (
                f"===== 第 {_PROGRESS['current']} 关 · 战斗失败！"
                f"已完成 {_PROGRESS['done']} 关，任务已停止 ====="
            )
        else:
            label = "战斗胜利" if stage == "win" else "未满星"
            _PROGRESS["done"] += 1
            msg = (
                f"===== 第 {_PROGRESS['current']} 关 · 结束（{label}）"
                f"｜已完成 {_PROGRESS['done']} 关 ====="
            )
        mfa_log(_MODULE, "report_progress", "info", msg)
        return True


@AgentServer.custom_action("连点退出")
class ClickTopToExit(CustomAction):
    """连续点击屏幕中上方（默认 (640,30)）N 次、每次间隔秒数，用于退出结算界面。

    参数（JSON）：
        times: int, 点击次数，默认 8
        interval: float, 每次间隔秒，默认 1.0
        x / y: int, 点击坐标，默认 640 / 30
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = _parse_param(argv.custom_action_param)
        try:
            times = max(1, int(param.get("times", 8)))
        except Exception:
            times = 8
        try:
            interval = float(param.get("interval", 1.0))
        except Exception:
            interval = 1.0
        try:
            x = int(param.get("x", 640))
            y = int(param.get("y", 30))
        except Exception:
            x, y = 640, 30

        for i in range(times):
            try:
                context.tasker.controller.post_click(x, y).wait()
            except Exception as e:
                mfa_err(_MODULE, "click_exit", "连点退出 点击失败", error=e)
            mfa_log(_MODULE, "click_exit", "info", f"连点退出 ({x},{y}) {i + 1}/{times}", idx=i + 1, total=times)
            if i < times - 1:
                time.sleep(interval)
        return True


def _save_png(path, img):
    """把 ndarray(H,W,3/4) 存成 PNG —— 零第三方依赖（numpy + zlib + struct）。"""
    try:
        import numpy as np

        arr = np.asarray(img)
        if arr.ndim == 2:
            arr = arr[:, :, None]
        h, w, c = arr.shape
        if c == 1:
            arr = np.repeat(arr, 3, axis=2)
            c = 3
        color_type = 6 if c == 4 else 2
        arr = np.ascontiguousarray(arr.astype("uint8"))
        raw = b"".join(b"\x00" + arr[y].tobytes() for y in range(h))

        def _chunk(typ, data):
            return (
                struct.pack(">I", len(data))
                + typ
                + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
            )

        png = (
            b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, color_type, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(raw, 6))
            + _chunk(b"IEND", b"")
        )
        with open(path, "wb") as f:
            f.write(png)
        return True
    except Exception as e:
        mfa_err(_MODULE, "save_png", "保存 PNG 失败", error=e)
        return False


def _screencap(context: Context):
    """拿最新截图（numpy BGR 数组）。

    ⚠️ 2026-10-31 修正（重大）：`post_screencap()` 返回的是 `JobWithResult[numpy.ndarray]`，
    而 `JobWithResult.wait()` 返回**它自己**（Job 对象），不是结果！必须走 `.get()` 才拿得到 numpy。
    原实现 `img = job.wait()` 于是把 Job 对象当成图像返回，随后 `job.get()` 抛异常又被
    `except: pass` 吞掉 —— 结果所有调用方（SoCAwaitBattle / SoCGBPickAvailable / 存失败截图）
    拿到的都是 Job 对象，识别一律失败、动作空转且**不打任何错误日志**。

    正确顺序：先 get(wait=True)；拿不到再退化为 wait() 之后 get()（兼容旧版 SDK）。
    """
    try:
        job = context.tasker.controller.post_screencap()
        # 首选：直接阻塞取结果（JobWithResult.get(wait=True) → numpy.ndarray）
        try:
            img = job.get(wait=True)
            if img is not None:
                return img
        except TypeError:
            # 旧版签名 get() 无参数
            pass
        except Exception as e:
            mfa_err(_MODULE, "screencap", "get(wait=True) 失败，尝试退化路径", error=e)

        job.wait()
        img = job.get() if hasattr(job, "get") else None
        if img is None:
            mfa_err(_MODULE, "screencap", "截图返回空（Job 未产出 numpy）")
        return img
    except Exception as e:
        mfa_err(_MODULE, "screencap", "截图失败", error=e)
        return None


@AgentServer.custom_action("存失败截图")
class SaveFailShot(CustomAction):
    """把当前画面存到 debug/ 便于排查（例如"识别出发"失败时）。

    参数（JSON）：name: 文件名前缀，默认 "_fail"
    输出：debug/<name>.png（整屏） + debug/<name>_roi.png（"出发"OCR 区 [784,588,496,149]）
    """

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        name = str(_parse_param(argv.custom_action_param).get("name", "_fail"))
        img = _screencap(context)
        if img is None:
            mfa_err(_MODULE, "save_fail_shot", "存失败截图：截图失败")
            return True
        try:
            _DEBUG_DIR.mkdir(parents=True, exist_ok=True)
            _save_png(_DEBUG_DIR / f"{name}.png", img)
            x, y, w, h = 784, 588, 496, 149
            _save_png(_DEBUG_DIR / f"{name}_roi.png", img[y:y + h, x:x + w])
            msg = f"已存失败截图 {name}.png / {name}_roi.png（画面形状 {getattr(img, 'shape', None)}）"
            mfa_log(_MODULE, "save_fail_shot", "ok", msg)
        except Exception as e:
            mfa_err(_MODULE, "save_fail_shot", "存失败截图异常", error=e)
        return True
