"""agent 各模块共用的基础设施。

2026-11-20 从 auto_battle.py 迁出：这两个函数原本挂在「自动推图」模块下，
但 farm.py（清体力体力判据）与 soc_actions.py（认知海域）都在用，
功能移除时不能连带删掉，否则两个模块直接 ImportError。
"""
import json

from maa.context import Context

from mfalog import mfa_err

_MODULE = "common"


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


def _screencap(context: Context):
    """拿最新截图（numpy BGR 数组）。

    ⚠️ 2026-10-31 修正（重大）：`post_screencap()` 返回的是 `JobWithResult[numpy.ndarray]`，
    而 `JobWithResult.wait()` 返回**它自己**（Job 对象），不是结果！必须走 `.get()` 才拿得到 numpy。
    原实现 `img = job.wait()` 于是把 Job 对象当成图像返回，随后 `job.get()` 抛异常又被
    `except: pass` 吞掉 —— 结果所有调用方拿到的都是 Job 对象，识别一律失败、动作空转且
    **不打任何错误日志**。

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
