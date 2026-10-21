# -*- coding: utf-8 -*-
"""pipeline 公共解析层（MaaEOV 开发工具共用）。

抽出的动机（2026-10-21）：同一套 JSONC 解析与"引用前缀剥离"逻辑此前散在
`verify_feature.py`、`migrate_layout.py`、`gen_flow_doc.py` 三处；本轮新增
`check_graph.py`、`fill_timeouts.py`（计划 P0-4 / P0-2）后会出现第五、第六份
实现。**判据只写一份**是硬要求——否则"校验口径"与"修补口径"漂移，会出现
Maadori 踩过的假绿灯（两套判据各说各话）。

本模块只做纯函数与只读加载，不做任何写盘动作。

判据说明（重要）：
* `is_instant_match` —— MaaFramework 的 `recognition` 缺省即 `DirectHit`。
  某节点的 `next` 中若存在即时命中候选，扫描会在第一个候选立刻返回，**不吃
  `timeout` 预算**；因此这类节点即使不写 `timeout` 也不构成真风险。
* `is_timeout_risk` —— 真风险 = 非终端 + 无 `timeout` + `next` 中无即时命中
  候选。本仓库 2026-10-21 实测：356 非终端 / 316 无 timeout / **221 真风险**。
"""
from __future__ import annotations

import json
import os
import re

#: next / on_error 里的引用前缀修饰（MaaFramework v5）
REF_PREFIX_RE = re.compile(r"^\[(?:JumpBack|Anchor|JumpBackAnchor)\]\s*")

#: 视为"即时命中"的识别器类型（缺省也算，见模块 docstring）
INSTANT_RECOGNITION = {"DirectHit", "directhit"}

#: timeout 档位：(下限, 建议值)。建议值一律取上界，避免把长等待掐断。
TIMEOUT_TIERS = {
    "probe": (1000, 3000),
    "nav": (20000, 60000),
    "wait": (600000, 900000),
}

_PROBE_KEYWORDS = ("探测", "检查", "Check", "Is", "Detect", "Probe")
_WAIT_KEYWORDS = ("战斗", "结算", "扫荡", "加载", "推图", "等待", "Sweep", "Battle")
_WAIT_CUSTOM_ACTIONS = ("SoCAwaitBattle", "SoCAwait", "SoCBattle")


# ----------------------------------------------------------------------
# JSONC 解析
# ----------------------------------------------------------------------
def strip_jsonc(text: str) -> str:
    """剥离 `//` 与 `/* */` 注释，得到标准 JSON 文本。

    用字符扫描而非按行 `find("//")`：旧实现靠"整行含 http 就跳过"来保护 URL，
    一旦出现 `"url": "https://x",  // 说明` 这种**同行 URL + 注释**，
    注释就删不掉、JSON 解析直接失败（本函数由 `tests/test_graph.py` 暴露）。
    扫描器只在字符串字面量之外识别注释，URL 与模板名中的斜杠都不受影响。
    """
    out = []
    i, n = 0, len(text)
    in_str = False
    esc = False
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == "/" and i + 1 < n:
            nxt = text[i + 1]
            if nxt == "/":
                j = text.find("\n", i)
                if j == -1:
                    break
                i = j          # 保留换行，行号不变
                continue
            if nxt == "*":
                j = text.find("*/", i + 2)
                if j == -1:
                    break
                out.append("\n" * text.count("\n", i, j + 2))  # 保留行数
                i = j + 2
                continue
        out.append(ch)
        i += 1
    return "".join(out)


def load_jsonc(path: str):
    """按 JSONC 语义加载单个文件。"""
    with open(path, encoding="utf-8") as f:
        return json.loads(strip_jsonc(f.read()))


def load_pipelines(pipeline_dir: str):
    """加载目录下全部 `*.json`。

    :return: (files_map, errors)
        ``files_map``: 文件名 -> 节点字典（仅成功解析的文件）
        ``errors``:     [(文件名, 异常信息), ...]
    """
    files_map: dict[str, dict] = {}
    errors: list[tuple[str, str]] = []
    if not os.path.isdir(pipeline_dir):
        return files_map, [("<dir>", f"目录不存在: {pipeline_dir}")]
    for fn in sorted(os.listdir(pipeline_dir)):
        if not fn.endswith(".json"):
            continue
        try:
            d = load_jsonc(os.path.join(pipeline_dir, fn))
        except Exception as e:  # noqa: BLE001 - 校验脚本需要吞掉并汇报
            errors.append((fn, str(e)))
            continue
        if not isinstance(d, dict):
            errors.append((fn, f"顶层不是对象，实为 {type(d).__name__}"))
            continue
        files_map[fn] = d
    return files_map, errors


def merge_nodes(files_map: dict[str, dict]):
    """跨文件合并节点，并检测同名冲突。

    :return: (nodes, owner, conflicts)
        ``nodes``:     节点名 -> 节点字典（后者覆盖前者，与 MaaFw 行为一致）
        ``owner``:     节点名 -> 首次定义它的文件名
        ``conflicts``: 节点名 -> [定义它的文件名, ...]（长度 >1 即冲突）
    """
    seen: dict[str, list[str]] = {}
    nodes: dict[str, dict] = {}
    owner: dict[str, str] = {}
    for fn, d in files_map.items():
        for name, node in d.items():
            seen.setdefault(name, []).append(fn)
            owner.setdefault(name, fn)
            nodes[name] = node if isinstance(node, dict) else {}
    conflicts = {n: fs for n, fs in seen.items() if len(fs) > 1}
    return nodes, owner, conflicts


# ----------------------------------------------------------------------
# 字段工具
# ----------------------------------------------------------------------
def iter_templates(tpl):
    """`template` 可能是字符串或字符串列表，统一成可迭代。"""
    if isinstance(tpl, str):
        return [tpl]
    if isinstance(tpl, list):
        return [t for t in tpl if isinstance(t, str)]
    return []


def strip_ref_prefix(ref: str) -> str:
    """剥离 `[JumpBack]` / `[Anchor]` / `[JumpBackAnchor]` 前缀。"""
    return REF_PREFIX_RE.sub("", (ref or "").strip())


def node_refs(node: dict):
    """产出 (字段名, 引用字符串)：next / on_error / interrupt（历史字段）。"""
    for key in ("next", "on_error", "interrupt"):
        v = (node or {}).get(key)
        if isinstance(v, str):
            yield key, v
        elif isinstance(v, list):
            for t in v:
                if isinstance(t, str) and t:
                    yield key, t


def custom_action_name(node: dict) -> str:
    act = (node or {}).get("action")
    if isinstance(act, dict):
        return ((act.get("param") or {}).get("custom_action") or "")
    return ""


# ----------------------------------------------------------------------
# 判据（唯一事实源）
# ----------------------------------------------------------------------
def is_instant_match(node: dict) -> bool:
    """该节点是否"即时命中"（不需要等待画面变化）。

    缺省 `recognition` 即 DirectHit；显式 DirectHit 同理。
    """
    rec = (node or {}).get("recognition")
    if rec is None:
        return True
    if isinstance(rec, dict):
        return rec.get("type") in INSTANT_RECOGNITION
    return False


def is_timeout_risk(node: dict, nodes: dict) -> bool:
    """真风险：非终端 + 无 timeout + next 中无即时命中候选。

    `nodes` 为全库节点表（用于解析 next 目标）；目标不存在时按"非即时"计。
    """
    if not isinstance(node, dict):
        return False
    nxt = node.get("next")
    if not isinstance(nxt, list) or not nxt:
        return False
    if "timeout" in node:
        return False
    for ref in nxt:
        if not isinstance(ref, str) or not ref:
            continue
        target = nodes.get(strip_ref_prefix(ref))
        if target is not None and is_instant_match(target):
            return False
    return True


def classify_timeout_tier(name: str, node: dict) -> str:
    """给节点归入 timeout 档位：probe / nav / wait。"""
    ca = custom_action_name(node)
    if any(k in ca for k in _WAIT_CUSTOM_ACTIONS):
        return "wait"
    if any(k in (name or "") for k in _WAIT_KEYWORDS):
        return "wait"
    if any(k in (name or "") for k in _PROBE_KEYWORDS):
        return "probe"
    return "nav"


def recommended_timeout(name: str, node: dict) -> int:
    """建议的 timeout 值（取档位上界，防掐断）。"""
    return TIMEOUT_TIERS[classify_timeout_tier(name, node)][1]


def is_trap_self_loop(name: str, node: dict) -> bool:
    """陷阱自环：next 只指向自己（去掉自身与 [JumpBack] 前缀后无候选），
    且既无 on_error 也无 timeout —— 这类节点一旦匹配不到就会空转到任务超时。
    """
    nxt = (node or {}).get("next")
    if not isinstance(nxt, list):
        return False
    targets = [strip_ref_prefix(t) for t in nxt if isinstance(t, str) and t]
    if name not in targets:
        return False
    others = [t for t in targets if t != name]
    return not others and "on_error" not in node and "timeout" not in node
