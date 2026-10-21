# -*- coding: utf-8 -*-
"""启动自检单测（计划 P0-1）。

防的事故很具体：资源 OTA 全量更新若把用户 `agent/` 清空，程序不会崩，但所有任务
静默失效。自检要在启动时就报出一行明确的错，而不是让用户对着"点了没反应"猜。

这些用例只碰临时目录，不读真实工程。
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT = os.path.join(os.path.dirname(HERE), "agent")
if AGENT not in sys.path:
    sys.path.insert(0, AGENT)

import selfcheck  # noqa: E402


class TestSelfCheck(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="eov_selfcheck_")
        os.makedirs(os.path.join(self.root, "agent"))
        for fn in selfcheck.REQUIRED_AGENT_FILES:
            open(os.path.join(self.root, "agent", fn), "w").close()
        self.pdir = os.path.join(self.root, "resource", "base", "pipeline")
        os.makedirs(self.pdir)
        self.node_file = "Shared.json"
        with open(os.path.join(self.pdir, self.node_file), "w", encoding="utf-8") as f:
            f.write("{}")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write_manifest(self, files):
        with open(os.path.join(self.pdir, ".manifest.json"), "w", encoding="utf-8") as f:
            json.dump({"version": "test", "files": files}, f)

    def test_ok(self):
        self._write_manifest({"resource/base/pipeline/Shared.json": "deadbeef"})
        r = selfcheck.check(self.root)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["problems"], [])

    def test_missing_agent_module(self):
        os.remove(os.path.join(self.root, "agent", "evidence.py"))
        r = selfcheck.check(self.root)
        self.assertFalse(r["ok"])
        self.assertTrue(any("evidence.py" in p for p in r["problems"]), r["problems"])

    def test_missing_pipeline_file(self):
        self._write_manifest({"resource/base/pipeline/Gone.json": "x"})
        r = selfcheck.check(self.root)
        self.assertFalse(r["ok"])
        self.assertIn("缺 1 个文件", "、".join(r["problems"]))

    def test_no_manifest_is_note_not_problem(self):
        r = selfcheck.check(self.root)
        self.assertTrue(r["ok"], r)
        self.assertTrue(r["notes"])

    def test_broken_manifest_does_not_block(self):
        with open(os.path.join(self.pdir, ".manifest.json"), "w", encoding="utf-8") as f:
            f.write("{ not json")
        r = selfcheck.check(self.root)
        self.assertTrue(r["ok"], "清单损坏不应阻断启动")
        self.assertTrue(any("解析失败" in n for n in r["notes"]), r["notes"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
