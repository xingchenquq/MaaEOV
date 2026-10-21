# -*- coding: utf-8 -*-
"""图像读写（零第三方依赖）。

背景（2026-10-21 实测）：项目自带解释器里 **既没有 cv2 也没有 PIL**，只有 numpy。
所以 `soc_actions._save_gb_diag` 里 `try: import cv2 / except ImportError` 的兜底
一直在跑，写出的是**裸 BGR 字节却命名 .png** 的假图（评审已记录该现象，本次定位到
真因：不是路径编码问题，是编码器根本不存在）。

因此这里提供一个纯 stdlib + numpy 的 PNG 编码器（zlib + IHDR/IDAT/IEND），
并把 `imwrite` 做成三级回退：cv2 → PIL → 内置编码器。三级都失败才返回 False，
且**不再谎称保存成功**。

只做写入：取证图是给人看的，运行期不需要读回；`imread` 仅供调试，缺库时返回 None。
"""
from __future__ import annotations

import os
import struct
import zlib

try:  # 可选加速路径
    import numpy as np
except Exception:  # pragma: no cover - numpy 是硬依赖，仅极端环境缺失
    np = None

_PNG_SIG = b"\x89PNG\r\n\x1a\n"


def _as_uint8(img):
    """统一成 uint8 的 HxWx3 数组（BGR 原样保留，转换由调用方决定）。"""
    if np is None:
        raise RuntimeError("numpy 不可用")
    a = np.asarray(img)
    if a.dtype != np.uint8:
        a = np.clip(a, 0, 255).astype(np.uint8)
    if a.ndim == 2:
        a = np.stack([a, a, a], axis=-1)
    elif a.ndim == 3 and a.shape[2] == 4:
        a = a[:, :, :3]
    elif a.ndim != 3 or a.shape[2] != 3:
        raise ValueError(f"不支持的图像形状: {a.shape}")
    return np.ascontiguousarray(a)


def _chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def png_bytes(img, bgr: bool = True) -> bytes:
    """把 HxWx3 图像编码为 PNG 字节。`bgr=True` 时把 BGR 转成 RGB 写入。

    只用 filter type 0（None），牺牲约 10-20% 体积换取零依赖与可读性。
    """
    a = _as_uint8(img)
    if bgr:
        a = a[:, :, ::-1]
    h, w = a.shape[:2]
    raw = b"".join(b"\x00" + a[y].tobytes() for y in range(h))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8bit truecolor
    return _PNG_SIG + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw, 6)) \
        + _chunk(b"IEND", b"")


def imwrite(path: str, img, bgr: bool = True) -> bool:
    """写图。优先 cv2 / PIL（若环境里有），否则用内置 PNG 编码器。

    返回 **真实** 写盘结果；不再出现"打印已保存但文件是裸字节"的情况。
    """
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    data = None
    try:  # 1) cv2（最快，但注意 cv2.imwrite 对中文路径会失败）
        import cv2  # noqa: F401
        a = _as_uint8(img)
        ok, buf = cv2.imencode(".png", a)
        if ok:
            data = buf.tobytes()
    except Exception:
        data = None
    if data is None:
        try:  # 2) PIL
            from PIL import Image
            a = _as_uint8(img)
            if bgr:
                a = a[:, :, ::-1]
            import io
            buf = io.BytesIO()
            Image.fromarray(a).save(buf, format="PNG")
            data = buf.getvalue()
        except Exception:
            data = None
    if data is None:
        try:  # 3) 内置编码器
            data = png_bytes(img, bgr=bgr)
        except Exception:
            return False
    try:
        with open(path, "wb") as f:  # builtins.open 对中文路径安全
            f.write(data)
        return True
    except Exception:
        return False


def imread(path: str, bgr: bool = True):
    """调试用读取；缺少 cv2/PIL 时返回 None（运行期不需要读回）。"""
    if np is None or not os.path.exists(path):
        return None
    try:
        import cv2
        buf = np.fromfile(path, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is not None:
            return img
    except Exception:
        pass
    try:
        from PIL import Image
        a = np.array(Image.open(path).convert("RGB"))
        return a[:, :, ::-1] if bgr else a
    except Exception:
        return None


def crop(img, roi, pad: int = 40):
    """按 [x, y, w, h] 裁剪，并向四周扩 `pad` 像素上下文（越界自动夹紧）。"""
    if roi is None or np is None:
        return img
    a = np.asarray(img)
    h, w = a.shape[:2]
    x, y, rw, rh = (int(v) for v in roi)
    x0 = max(0, x - pad)
    y0 = max(0, y - pad)
    x1 = min(w, x + max(rw, 0) + pad)
    y1 = min(h, y + max(rh, 0) + pad)
    if x1 <= x0 or y1 <= y0:
        return a
    return a[y0:y1, x0:x1]
