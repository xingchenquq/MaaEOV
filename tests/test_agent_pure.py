# -*- coding: utf-8 -*-
"""agent 纯函数单测（计划 P0-5）。

只测**不依赖设备、不依赖截图、不写盘**的函数——这是能离线锁住的契约部分。
行为验证仍靠 `verify_feature.py` + 实机回归，二者分工不同。

覆盖：
* `crisis_mission._parse_ticket` / `_clamp_tickets` —— OCR 误读兜底（本次修复的缺陷）
* `auto_battle._parse_param` —— custom_action_param 的四种形态
* `mfalog._redact` / `_redact_str` —— 凭证打码（日志是唯一明细载体，打码失效等于泄漏）

运行：python\\python.exe -m unittest discover -s tests -v
"""
import os
os.environ.setdefault("MFAEOV_AGENT_LOG", "off")   # 单测日志不落盘（防污染 debug/mfa_agent.log）
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
AGENT = os.path.join(ROOT, "agent")
for p in (AGENT, os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

import auto_battle  # noqa: E402
import crisis_mission  # noqa: E402
import mfalog  # noqa: E402


class TestParseTicket(unittest.TestCase):
    """`_parse_ticket` 只做解析，不负责钳制；钳制在 `_clamp_tickets`。"""

    def test_normal(self):
        self.assertEqual(crisis_mission._parse_ticket("3"), 3)
        self.assertEqual(crisis_mission._parse_ticket("调令 5"), 5)
        self.assertEqual(crisis_mission._parse_ticket(" 6 "), 6)

    def test_zero_lookalikes(self):
        self.assertEqual(crisis_mission._parse_ticket("O"), 0)
        self.assertEqual(crisis_mission._parse_ticket("o"), 0)
        self.assertEqual(crisis_mission._parse_ticket("〇"), 0)
        self.assertEqual(crisis_mission._parse_ticket("０"), 0)

    def test_empty_and_garbage(self):
        self.assertEqual(crisis_mission._parse_ticket(""), 0)
        self.assertEqual(crisis_mission._parse_ticket(None), 0)
        self.assertEqual(crisis_mission._parse_ticket("调令"), 0)

    def test_raw_value_not_clamped(self):
        # 解析层如实返回，钳制交给 _clamp_tickets（两层职责分开才好测）
        self.assertEqual(crisis_mission._parse_ticket("50"), 50)


class TestClampTickets(unittest.TestCase):
    """钳制到 0..6：OCR 把 5 读成 50 时，原实现会点 49 次加号。"""

    def test_upper_bound(self):
        self.assertEqual(crisis_mission._clamp_tickets(50), 6)
        self.assertEqual(crisis_mission._clamp_tickets(7), 6)
        self.assertEqual(crisis_mission._clamp_tickets(6), 6)

    def test_lower_bound(self):
        self.assertEqual(crisis_mission._clamp_tickets(0), 0)
        self.assertEqual(crisis_mission._clamp_tickets(-3), 0)

    def test_type_tolerance(self):
        self.assertEqual(crisis_mission._clamp_tickets("5"), 5)
        self.assertEqual(crisis_mission._clamp_tickets(None), 0)
        self.assertEqual(crisis_mission._clamp_tickets("x"), 0)

    def test_end_to_end(self):
        # 真实链路：OCR 文本 -> 解析 -> 钳制
        self.assertEqual(crisis_mission._clamp_tickets(crisis_mission._parse_ticket("50")), 6)
        self.assertEqual(crisis_mission._clamp_tickets(crisis_mission._parse_ticket("O")), 0)


class TestParseParam(unittest.TestCase):
    """`_parse_param` 必须对四种输入形态都返回 dict，绝不抛异常。"""

    def test_dict_passthrough(self):
        p = {"max_wait": 10}
        self.assertIs(auto_battle._parse_param(p), p)

    def test_json_string(self):
        self.assertEqual(auto_battle._parse_param('{"poll": 5}'), {"poll": 5})

    def test_double_encoded(self):
        self.assertEqual(auto_battle._parse_param('"{\\"poll\\": 5}"'), {"poll": 5})

    def test_invalid_returns_empty(self):
        for raw in (None, "", "oops", "[1,2]", 123):
            self.assertEqual(auto_battle._parse_param(raw), {}, f"raw={raw!r}")


class TestRedact(unittest.TestCase):
    """日志落盘是唯一明细载体，凭证必须在写盘前打码。"""

    def test_sensitive_key_masked(self):
        out = mfalog._redact({"token": "abc123", "n": 1})
        self.assertEqual(out["token"], "****(redacted)****")
        self.assertEqual(out["n"], 1)

    def test_inline_secret_masked(self):
        out = mfalog._redact_str("Authorization: Bearer abcdefgh")
        self.assertNotIn("abcdefgh", out)

    def test_jwt_masked(self):
        jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijklmnop"
        self.assertNotIn(jwt, mfalog._redact_str(f"tok={jwt}"))

    def test_nested_list(self):
        out = mfalog._redact({"items": [{"password": "p@ss"}, "api_key=xyz"]})
        self.assertEqual(out["items"][0]["password"], "****(redacted)****")
        self.assertNotIn("xyz", out["items"][1])

    def test_normal_text_untouched(self):
        self.assertEqual(mfalog._redact_str("已进入危机行动界面，调令数 = 3"),
                         "已进入危机行动界面，调令数 = 3")


if __name__ == "__main__":
    unittest.main(verbosity=2)
