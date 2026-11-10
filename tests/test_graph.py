# -*- coding: utf-8 -*-
"""P0-4 护栏自测：`scripts/check_graph.py` 与 `scripts/pj.py` 的判据。

设计取舍：
* 用 **stdlib unittest** 而非 pytest —— 本项目 `python/` 是随完整包分发的运行
  环境，往里装 pytest 会被打进发版包（体积 + 无谓依赖）。unittest 零依赖，
  且 pytest 若日后安装也能直接收集本文件（class-based 兼容）。
* 每个用例都构造最小 pipeline 目录，**不依赖真实 resource/**，因此可离线跑。

运行：
    python\\python.exe -m unittest discover -s tests -v
"""
import contextlib
import io
import json
import os
os.environ.setdefault("MFAEOV_AGENT_LOG", "off")   # 单测日志不落盘（防污染 debug/mfa_agent.log）
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import check_graph as cg  # noqa: E402
import pj  # noqa: E402


def _write(dirpath, name, nodes):
    with open(os.path.join(dirpath, name), "w", encoding="utf-8") as f:
        json.dump(nodes, f, ensure_ascii=False)


class TempProject:
    """临时 pipeline 目录 + 临时 interface.json 的上下文管理器。"""

    def __init__(self, files, tasks=None, options=None):
        self.files = files
        self.tasks = tasks or []
        self.options = options or {}

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = self._tmp.name
        pdir = os.path.join(root, "pipeline")
        os.makedirs(pdir)
        for name, nodes in self.files.items():
            _write(pdir, name, nodes)
        iface = {"task": self.tasks, "option": self.options}
        with open(os.path.join(root, "interface.json"), "w", encoding="utf-8") as f:
            json.dump(iface, f, ensure_ascii=False)
        self._saved = (cg.PIPELINE_DIR, cg.INTERFACE)
        cg.PIPELINE_DIR = pdir
        cg.INTERFACE = os.path.join(root, "interface.json")
        return self

    def __exit__(self, *exc):
        cg.PIPELINE_DIR, cg.INTERFACE = self._saved
        self._tmp.cleanup()
        return False


def run_main(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = cg.main(list(argv))
    return code, buf.getvalue()


class TestPjJudgement(unittest.TestCase):
    """判据函数（timeout 真风险 / 陷阱自环）——这是补 221 个节点的唯一口径。"""

    def test_instant_candidate_means_no_risk(self):
        nodes = {
            "A": {"next": ["B"]},                      # 只有等待型候选 → 真风险
            "B": {"recognition": {"type": "TemplateMatch"}, "next": ["C"]},
            "C": {"next": []},
            "D": {"next": ["E"]},                      # E 是 DirectHit → 安全
            "E": {"recognition": {"type": "DirectHit"}, "next": []},
            "F": {"next": ["G"]},                      # G 未写 recognition → 缺省即即时
            "G": {"action": {"type": "Click"}, "next": []},
        }
        self.assertTrue(pj.is_timeout_risk(nodes["A"], nodes))
        self.assertFalse(pj.is_timeout_risk(nodes["D"], nodes))
        self.assertFalse(pj.is_timeout_risk(nodes["F"], nodes))

    def test_explicit_timeout_clears_risk(self):
        nodes = {"A": {"next": ["B"], "timeout": 60000}, "B": {"next": []}}
        self.assertFalse(pj.is_timeout_risk(nodes["A"], nodes))

    def test_terminal_node_is_not_risk(self):
        nodes = {"A": {"action": {"type": "DoNothing"}}}
        self.assertFalse(pj.is_timeout_risk(nodes["A"], nodes))

    def test_trap_self_loop(self):
        self.assertTrue(pj.is_trap_self_loop("A", {"next": ["A"]}))
        self.assertTrue(pj.is_trap_self_loop("A", {"next": ["[JumpBack]A"]}))
        # 有兄弟出口 → 是"重试 + 备选"的正常写法，不是陷阱
        self.assertFalse(pj.is_trap_self_loop("A", {"next": ["A", "B"]}))
        # 有 on_error 或 timeout → 有第二出口
        self.assertFalse(pj.is_trap_self_loop("A", {"next": ["A"], "on_error": ["B"]}))
        self.assertFalse(pj.is_trap_self_loop("A", {"next": ["A"], "timeout": 3000}))

    def test_classify_timeout_tier(self):
        self.assertEqual(pj.classify_timeout_tier("SoCAwaitBattle", {"action": {}}), "wait")
        self.assertEqual(pj.classify_timeout_tier("等待结算", {}), "wait")
        self.assertEqual(pj.classify_timeout_tier("探测关卡", {}), "probe")
        self.assertEqual(pj.classify_timeout_tier("_NavigateMailbox", {}), "nav")

    def test_short_word_false_positive(self):
        """`_ShortTermCheckIn` 曾因含 "Check" 被判成 3 秒探测档（真机必掐断）。"""
        self.assertEqual(pj.classify_timeout_tier("_ShortTermCheckIn", {}), "nav")
        self.assertEqual(pj.classify_timeout_tier("CheckIn", {}), "nav")

    def test_suggest_timeout_cascade(self):
        nodes = {
            "Nav": {"next": ["BattleWait"]},
            "BattleWait": {"next": []},
        }
        # 下游是 wait 档 → 父节点必须覆盖
        self.assertEqual(pj.suggest_timeout("Nav", nodes["Nav"], nodes),
                         pj.TIMEOUT_TIERS["wait"][1] + 30000)
        # 普通导航 → 本档位建议值
        plain = {"next": ["Other"], "recognition": {"type": "TemplateMatch"}}
        nodes["Other"] = {"next": []}
        self.assertEqual(pj.suggest_timeout("Nav", plain, nodes), pj.TIMEOUT_TIERS["nav"][1])

    def test_suggest_timeout_no_cascade_for_probe_and_retry(self):
        nodes = {
            "探测关卡": {"next": ["BattleWait"]},
            "重试节点": {"next": ["BattleWait"]},
            "BattleWait": {"next": []},
        }
        # 探测档不级联（快速分支是它的职责）
        self.assertEqual(pj.suggest_timeout("探测关卡", nodes["探测关卡"], nodes),
                         pj.TIMEOUT_TIERS["probe"][1])
        # 重试节点不级联（靠 timeout 驱动节奏，拉长=放大卡死）
        self.assertEqual(pj.suggest_timeout("重试节点", nodes["重试节点"], nodes),
                         pj.TIMEOUT_TIERS["nav"][1])

    def test_jsonc_strip_keeps_url(self):
        text = '{\n  // 注释\n  "url": "https://example.com/a",  // 尾注释\n  "n": 1\n}'
        self.assertEqual(json.loads(pj.strip_jsonc(text))["url"], "https://example.com/a")


class TestCheckGraph(unittest.TestCase):
    """护栏四态：全绿 / 悬空 / 陷阱 / 路径错误。"""

    def test_clean_graph_passes(self):
        files = {"A.json": {
            "Start": {"next": ["Mid"]},
            "Mid": {"recognition": {"type": "TemplateMatch"}, "next": ["End"]},
            "End": {"next": []},
        }}
        with TempProject(files, [{"name": "t", "entry": "Start"}]):
            code, out = run_main()
        self.assertEqual(code, 0, out)
        self.assertIn("悬空引用 0 处", out)

    def test_dangling_ref_fails(self):
        files = {"A.json": {"Start": {"next": ["Ghost"]}}}
        with TempProject(files, [{"name": "t", "entry": "Start"}]):
            code, out = run_main()
        self.assertEqual(code, 1, out)
        self.assertIn("悬空引用 1 处", out)

    def test_trap_self_loop_fails(self):
        files = {"A.json": {
            "Start": {"next": ["Loop"]},
            "Loop": {"recognition": {"type": "TemplateMatch"}, "next": ["Loop"]},
            "End": {"next": []},
        }}
        with TempProject(files, [{"name": "t", "entry": "Start"}]):
            code, out = run_main()
        self.assertEqual(code, 1, out)
        self.assertIn("陷阱自环 1 个", out)

    def test_missing_dir_returns_2(self):
        with TempProject({}, []):
            cg.PIPELINE_DIR = os.path.join(cg.PIPELINE_DIR, "not-exist")
            code, out = run_main()
        self.assertEqual(code, 2, out)

    def test_strict_promotes_warn(self):
        # 存在但从入口不可达的孤立节点 → warn；--strict 时返回 1
        files = {"A.json": {"Start": {"next": []}, "Orphan": {"next": []}}}
        with TempProject(files, [{"name": "t", "entry": "Start"}]):
            code_normal, _ = run_main()
            code_strict, out = run_main("--strict")
        self.assertEqual(code_normal, 0)
        self.assertEqual(code_strict, 1, out)

    def test_override_nodes_count_as_starts(self):
        """只在 option.pipeline_override 中被挂入链路的节点，不应被判不可达。

        本仓库真实情况：76 个 override 注入点承担了 142 个节点的入口，
        若不把它们计入 BFS 起点，终止可达性检查会满屏假警报。
        """
        files = {"A.json": {
            "Start": {"next": []},
            "TaskA": {"next": ["OnlyInOverride"]},
            "OnlyInOverride": {"next": []},
        }}
        options = {"某选项": {"cases": [{
            "name": "c1",
            "pipeline_override": {"TaskA": {"next": ["OnlyInOverride"]}},
        }]}}
        # 无 override：TaskA 与 OnlyInOverride 均不可达 → warn
        with TempProject(files, [{"name": "t", "entry": "Start"}]):
            code_plain, out_plain = run_main()
        self.assertEqual(code_plain, 0)
        self.assertIn("OnlyInOverride", out_plain)

        # 有 override：两者都成为起点 → 无 warn
        with TempProject(files, [{"name": "t", "entry": "Start"}], options):
            code_ov, out_ov = run_main()
        self.assertEqual(code_ov, 0, out_ov)
        self.assertNotIn("不可达", out_ov)


if __name__ == "__main__":
    unittest.main(verbosity=2)
