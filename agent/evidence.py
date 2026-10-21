# -*- coding: utf-8 -*-
"""判据取证：失败现场落盘（截图 + 结构化元数据）。

动机（2026-10-21）：`debug/on_error/` 只有框架自动截图，**有图无判据**——看不出
当时 OCR 命中什么、模板得分多少、阈值是多少、等了多久。排障只能翻日志猜。

设计取舍（与原计划的差异已实测校准）：
* 只存 **ROI + 四周 40px 上下文**，不存全帧：单张从 0.3–1 MB 降到 20–60 KB。
* **同步写**，不做异步队列：只在失败路径调用（`fail` 档），实测 ROI 编码 < 5 ms；
  异步会引入线程生命周期与队列丢弃计数，收益不抵复杂度。若将来接进 60Hz 循环再改。
* 自动清理：TTL 24h + 上限 200 对，避免用户磁盘被取证图吃掉。
* 三档开关：`off` / `fail`（默认）/ `all`，通过 custom_action_param 或 set_mode 调整。

同目录输出两个文件：`<名>_<时间戳>.png` + 同名 `.json`。
"""
from __future__ import annotations

import json
import os
import time

import imaging  # agent/ 为平铺模块（无 __init__.py），直接绝对导入

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_DIR = os.path.join(_ROOT, "debug", "evidence")

#: 关闭级别阈值：off 全关；fail 只存失败；all 全存
_ORDER = {"off": 99, "fail": 2, "all": 0}
_MODE = "fail"

MAX_AGE_S = 24 * 3600
MAX_PAIRS = 200
#: 单张上限（像素），超过则拒绝编码——避免误传整屏 4K 拖慢失败路径
MAX_PIXELS = 1280 * 720 * 2


def set_mode(mode: str) -> None:
    global _MODE
    _MODE = mode if mode in _ORDER else "fail"


def get_mode() -> str:
    return _MODE


def _level_ok(level: str) -> bool:
    return _ORDER.get(level, 2) >= _ORDER.get(_MODE, 2)


def _tag() -> str:
    return time.strftime("%Y%m%d_%H%M%S") + f"_{int(time.time() * 1000) % 1000:03d}"


def prune_evidence(dirpath: str = None, max_age_s: int = MAX_AGE_S,
                   max_pairs: int = MAX_PAIRS) -> int:
    """删除过期与超量的取证对，返回删除的 png 数量。"""
    d = dirpath or EVIDENCE_DIR
    if not os.path.isdir(d):
        return 0
    now = time.time()
    pngs = [f for f in os.listdir(d) if f.endswith(".png")]
    stamped = []
    removed = 0
    for fn in pngs:
        p = os.path.join(d, fn)
        try:
            age = now - os.path.getmtime(p)
        except OSError:
            continue
        if age > max_age_s:
            _drop(p)
            removed += 1
            continue
        stamped.append((os.path.getmtime(p), p))
    stamped.sort()
    while len(stamped) > max_pairs:
        _, p = stamped.pop(0)
        _drop(p)
        removed += 1
    return removed


def _drop(png_path: str) -> None:
    for p in (png_path, png_path[:-4] + ".json"):
        try:
            os.remove(p)
        except OSError:
            pass


def save_evidence(img, name: str, roi=None, meta: dict = None,
                  level: str = "fail", bgr: bool = True) -> str | None:
    """保存一次取证。

    :param img: 截图（numpy 数组）
    :param name: 事件名，会进文件名与 JSON（用 ASCII，便于 grep）
    :param roi: [x,y,w,h]；给了就只存该区域 + 上下文，不给则存整帧
    :return: png 路径；未启用/失败时返回 None
    """
    if img is None or not _level_ok(level):
        return None
    try:
        shot = imaging.crop(img, roi) if roi is not None else img
        shape = getattr(shot, "shape", None)
        if shape and shape[0] * shape[1] > MAX_PIXELS:
            return None
        os.makedirs(EVIDENCE_DIR, exist_ok=True)
        base = f"{name}_{_tag()}"
        png = os.path.join(EVIDENCE_DIR, base + ".png")
        ok = imaging.imwrite(png, shot, bgr=bgr)
        if not ok:
            _warn(f"取证图写入失败: {png}")
            return None
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "event": name,
            "level": level,
            "roi": list(roi) if roi is not None else None,
            "shape": list(shape) if shape else None,
            "meta": meta or {},
        }
        with open(os.path.join(EVIDENCE_DIR, base + ".json"), "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, default=str)
        prune_evidence()
        return png
    except Exception as e:  # 取证失败绝不能影响主流程
        _warn(f"取证异常（已忽略）: {e!r}")
        return None


def _warn(msg: str) -> None:
    try:
        from mfalog import mfa_warn
        mfa_warn("取证", "evidence", msg)
    except Exception:
        pass
