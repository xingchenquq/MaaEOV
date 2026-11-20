"""把任务图标统一刷成方案 A 的深蓝灰底色（白符号保留）。

背景：16 色相各自为战被用户判定为「太乱」，改为统一单色 + 靠图形区分。
本地没有 PIL/cv2，所以用 ffmpeg 解码 + numpy 处理 + 最小 PNG 编码器写回。

用法：
    python scripts/apply_icon_color.py             # 应用
    python scripts/apply_icon_color.py --dry-run   # 只报告将改动哪些
"""
import os
import struct
import subprocess
import sys
import zlib

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICON_DIR = os.path.join(ROOT, 'resource', 'base', 'image', 'ui', 'icons')

# 统一配色（界面是浅色主题 BaseTheme=Light）：
#   底 = 浅灰蓝，和白色卡片有区分但不抢眼；符号 = 深蓝灰，对比约 7:1。
# 早前试过「深底 + 白符号」，在浅色列表里像一排黑痣，压过任务文字，已弃用。
BG = (0xE3, 0xE8, 0xEF)
FG = (0x3D, 0x4A, 0x5C)
# 三通道都 >= 该值视作「白色符号笔画」，保持原样
WHITE_MIN = 235


def load_rgba(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', path,
                          '-f', 'rawvideo', '-pix_fmt', 'rgba', '-'],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.uint8)
    side = int((a.size // 4) ** 0.5)
    return a.reshape(side, side, 4).copy()


def write_png(path, arr):
    h, w, _ = arr.shape
    raw = b''.join(b'\x00' + arr[y].tobytes() for y in range(h))

    def chunk(typ, data):
        return (struct.pack('>I', len(data)) + typ + data
                + struct.pack('>I', zlib.crc32(typ + data) & 0xFFFFFFFF))

    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 9))
           + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)


def recolor(arr):
    """背景 -> BG，白色笔画 -> FG。"""
    out = arr.copy()
    is_white = out[:, :, :3].astype(np.int16).min(axis=2) >= WHITE_MIN
    opaque = out[:, :, 3] > 0
    bgm = opaque & (~is_white)
    fgm = opaque & is_white
    out[bgm, 0], out[bgm, 1], out[bgm, 2] = BG
    out[fgm, 0], out[fgm, 1], out[fgm, 2] = FG
    return out


def main(argv):
    dry = '--dry-run' in argv
    files = sorted(f for f in os.listdir(ICON_DIR) if f.lower().endswith('.png'))
    hexs = '底 #%02X%02X%02X / 符号 #%02X%02X%02X' % (BG + FG)
    print(f'目标 {hexs}，共 {len(files)} 张')
    for f in files:
        p = os.path.join(ICON_DIR, f)
        img = load_rgba(p)
        old = tuple(int(v) for v in img[img.shape[0] // 2, 6, :3])
        if tuple(old) == BG:
            print(f'  [跳过] {f}（已是目标色）')
            continue
        if dry:
            print(f'  [将改] {f}: #{old[0]:02X}{old[1]:02X}{old[2]:02X} -> {hexs}')
            continue
        write_png(p, recolor(img))
        print(f'  [OK] {f}: #{old[0]:02X}{old[1]:02X}{old[2]:02X} -> {hexs}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
