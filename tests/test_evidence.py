# -*- coding: utf-8 -*-
"""取证链单测（计划 P0-6）。

重点不是"能写文件"，而是三条曾经出过错的性质：
1. `imwrite` 写出的**真的是 PNG**（旧实现 cv2/PIL 都不存在 → 裸字节伪装成 .png）；
2. 中文路径可写（历史 bug 记录为 `cv2.imwrite` 静默失败）；
3. `prune_evidence` 真的会删过期与超量文件（否则用户磁盘被取证图吃光）。
"""
import os
os.environ.setdefault("MFAEOV_AGENT_LOG", "off")   # 单测日志不落盘（防污染 debug/mfa_agent.log）
import shutil
import struct
import sys
import tempfile
import time
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AGENT = os.path.join(ROOT, "agent")
if AGENT not in sys.path:
    sys.path.insert(0, AGENT)

import numpy as np  # noqa: E402

import evidence  # noqa: E402
import imaging  # noqa: E402


def _img(h=4, w=6, val=0):
    return np.full((h, w, 3), val, np.uint8)


def parse_png(data: bytes):
    """极简 PNG 解析：返回 (IHDR 元组, 解压后的原始扫描行)。"""
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "PNG 签名错误"
    i, ihdr, idat = 8, None, b""
    while i < len(data):
        ln = struct.unpack(">I", data[i:i + 4])[0]
        tag = data[i + 4:i + 8]
        body = data[i + 8:i + 8 + ln]
        if tag == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat += body
        i += 12 + ln
    return ihdr, zlib.decompress(idat)


class TestPngEncoder(unittest.TestCase):
    def test_structure(self):
        ihdr, raw = parse_png(imaging.png_bytes(_img(4, 6), bgr=True))
        self.assertEqual(ihdr[0], 6)   # width
        self.assertEqual(ihdr[1], 4)   # height
        self.assertEqual(ihdr[3], 2)   # color type 2 = truecolor
        self.assertEqual(len(raw), 4 * (1 + 6 * 3))

    def test_bgr_to_rgb(self):
        img = np.zeros((2, 2, 3), np.uint8)
        img[:, :, 0] = 255            # BGR 的 B 通道拉满 = 纯蓝
        _, raw = parse_png(imaging.png_bytes(img, bgr=True))
        self.assertEqual(raw[1:4], bytes([0, 0, 255]), "蓝色应落在 RGB 末位")

    def test_bgr_false_keeps_order(self):
        img = np.zeros((2, 2, 3), np.uint8)
        img[:, :, 0] = 255
        _, raw = parse_png(imaging.png_bytes(img, bgr=False))
        self.assertEqual(raw[1:4], bytes([255, 0, 0]))


class TestImwrite(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="eov_img_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_chinese_path(self):
        p = os.path.join(self.dir, "中文 目录", "截图.png")
        self.assertTrue(imaging.imwrite(p, _img()))
        with open(p, "rb") as f:
            self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")

    def test_crop_clamps(self):
        out = imaging.crop(np.zeros((100, 100, 3), np.uint8), [90, 90, 50, 50], pad=20)
        self.assertEqual(out.shape, (30, 30, 3))
        out2 = imaging.crop(np.zeros((100, 100, 3), np.uint8), None)
        self.assertEqual(out2.shape, (100, 100, 3))


class TestEvidence(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="eov_ev_")
        self._saved = evidence.EVIDENCE_DIR
        evidence.EVIDENCE_DIR = self.dir
        evidence.set_mode("fail")

    def tearDown(self):
        evidence.EVIDENCE_DIR = self._saved
        evidence.set_mode("fail")
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_mode_gate(self):
        evidence.set_mode("off")
        self.assertIsNone(evidence.save_evidence(_img(), "x"))
        evidence.set_mode("all")
        self.assertIsNotNone(evidence.save_evidence(_img(), "x", level="info"))

    def test_saves_png_and_json(self):
        p = evidence.save_evidence(_img(), "await_battle", roi=[0, 0, 3, 3],
                                   meta={"elapsed_ms": 540000})
        self.assertIsNotNone(p)
        self.assertTrue(os.path.exists(p))
        js = p[:-4] + ".json"
        self.assertTrue(os.path.exists(js), "必须同时落一份元数据 JSON")
        with open(js, encoding="utf-8") as f:
            payload = f.read()
        self.assertIn("await_battle", payload)
        self.assertIn("540000", payload)

    def test_oversize_rejected(self):
        big = np.zeros((2000, 2000, 3), np.uint8)
        self.assertIsNone(evidence.save_evidence(big, "huge"))

    def test_prune_by_age(self):
        # 注意：先全部写入、再统一改 mtime —— save_evidence 内部会顺带 prune，
        # 边写边改会把文件提前删掉，测试就测不到 prune 本身了。
        paths = [evidence.save_evidence(_img(), f"old{k}") for k in range(3)]
        for p in paths:
            os.utime(p, (1, 1))
        self.assertEqual(evidence.prune_evidence(max_age_s=60), 3)
        self.assertEqual([f for f in os.listdir(self.dir) if f.endswith(".png")], [])

    def test_prune_by_cap_keeps_newest(self):
        paths = [evidence.save_evidence(_img(), f"cap{k}") for k in range(5)]
        now = time.time()
        for k, p in enumerate(paths):
            stamp = now - (5 - k)          # 越早写入的 mtime 越老
            os.utime(p, (stamp, stamp))
        # max_age 放大到不会按时间删，只验证"超量时保最新"
        evidence.prune_evidence(max_age_s=10 ** 9, max_pairs=2)
        left = sorted(f for f in os.listdir(self.dir) if f.endswith(".png"))
        self.assertEqual(len(left), 2, left)
        self.assertIn(os.path.basename(paths[-1]), left, "最新的应保留")


if __name__ == "__main__":
    unittest.main(verbosity=2)
