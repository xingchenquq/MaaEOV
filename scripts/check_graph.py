# -*- coding: utf-8 -*-
"""任务图静态护栏（计划 P0-4，参照 Maadori `debug/check_closure.py` 扩展）。

三项检查：
1. `check_dangling`（error）—— next / on_error / interrupt 引用是否都有定义。
2. `check_traps`（error）—— 陷阱自环：`next` 去掉自身与 `[JumpBack]` 前缀后
   无剩余候选，且既无 `on_error` 也无 `timeout`。这类节点一旦识别不到就空转到
   任务超时，日志只留一句 `Task timeout`，最难定位。
3. `check_termination`（warn）—— 从 `interface.json` 的 `task[].entry` 出发，
   找出"无法到达任何终止节点（`next` 为空/缺失）"的节点。`[JumpBack]` 的弹栈
   语义会干扰建模（弹栈后沿用栈顶节点的 next），因此该项**永不阻塞**。

退出码：
* 0 = 全绿（或有 warn 但未加 `--strict`）
* 1 = 存在 error（或 `--strict` 下的 warn）
* 2 = 路径/加载错误（找不到 pipeline 或节点为空）——防止"零文件却报全绿"

判据全部来自 `scripts/pj.py`，与 `verify_feature.py` 共用，禁止在本文件另立一份。

用法：
    python scripts/check_graph.py            # 默认：error 才非 0
    python scripts/check_graph.py --strict   # warn 也非 0（CI 用）
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import pj  # noqa: E402

PIPELINE_DIR = os.path.join(ROOT, "resource", "base", "pipeline")
INTERFACE = os.path.join(ROOT, "interface.json")


# ----------------------------------------------------------------------
# 加载
# ----------------------------------------------------------------------
def load(verbose: bool = True):
    files_map, errors = pj.load_pipelines(PIPELINE_DIR)
    if errors:
        for fn, err in errors:
            print(f"!! {fn} 解析失败: {err}")
        return None, None, None, 2
    if not files_map:
        print(f"!! 未找到 pipeline 文件：{PIPELINE_DIR}")
        return None, None, None, 2
    nodes, owner, conflicts = pj.merge_nodes(files_map)
    if not nodes:
        print(f"!! pipeline 文件存在但未解析到任何节点：{PIPELINE_DIR}")
        return None, None, None, 2
    if verbose:
        total_refs = sum(1 for _, nd in nodes.items() for _ in pj.node_refs(nd))
        print(f"pipeline 文件 {len(files_map)} 个，节点 {len(nodes)} 个，引用 {total_refs} 处")
    return files_map, nodes, conflicts, 0


# ----------------------------------------------------------------------
# 检查 1：悬空引用
# ----------------------------------------------------------------------
def check_dangling(nodes: dict):
    problems = []
    for name, node in nodes.items():
        for key, ref in pj.node_refs(node):
            target = pj.strip_ref_prefix(ref)
            if not target:
                continue
            if target not in nodes:
                problems.append((name, key, ref))
    return problems


# ----------------------------------------------------------------------
# 检查 2：陷阱自环
# ----------------------------------------------------------------------
def check_traps(nodes: dict):
    return [name for name, node in nodes.items() if pj.is_trap_self_loop(name, node)]


def load_override_starts(nodes: dict = None):
    """`interface.json` 中 option.pipeline_override 注入的节点也算可达起点。

    这些节点在静态 `next` 图上没有入边（只有运行时由 option 挂入），若不计入
    BFS 起点，会被误判为"不可达"。verify 第 8 段已保证 override 键存在。
    """
    if not os.path.exists(INTERFACE):
        return set()
    try:
        iface = pj.load_jsonc(INTERFACE)
    except Exception:  # noqa: BLE001
        return set()
    starts = set()
    for opt in (iface.get("option") or {}).values():
        for case in (opt or {}).get("cases", []) or []:
            for node, ov in (case.get("pipeline_override") or {}).items():
                if nodes is not None and node not in nodes:
                    continue
                starts.add(node)
                if isinstance(ov, dict):
                    for key in ("next", "on_error"):
                        for ref in (ov.get(key) or []):
                            if isinstance(ref, str):
                                t = pj.strip_ref_prefix(ref)
                                if nodes is None or t in nodes:
                                    starts.add(t)
    return starts


# ----------------------------------------------------------------------
# 检查 3：终止可达性（warn）
# ----------------------------------------------------------------------
def load_entries(nodes: dict = None):
    """从 interface.json 读任务入口，并解析成**真实节点名**。

    本仓库的节点名可能自带 `#` 前缀（如 `#CollectRewards`），而 `entry` 字段值
    与节点名同形；因此不能一律 `lstrip('#')`，否则入口全部解析失败、可达性
    检查退化为"290 个节点全都不可达"的假警报。
    """
    if not os.path.exists(INTERFACE):
        return []
    try:
        iface = pj.load_jsonc(INTERFACE)
    except Exception:  # noqa: BLE001
        return []
    out = []
    for t in iface.get("task", []) or []:
        e = t.get("entry")
        if not (isinstance(e, str) and e):
            continue
        cands = [pj.strip_ref_prefix(e), e.lstrip("#"), e]
        resolved = next((c for c in cands if nodes and c in nodes), cands[0])
        out.append((t.get("name", "?"), resolved))
    return out


def check_termination(nodes: dict, entries, extra_starts=None):
    """返回 (unreachable_from_entry, cannot_terminate)。

    * `unreachable_from_entry`：从任务入口与 override 注入点都走不到的节点
      （多为历史残留或仅被已删链路引用）。
    * `cannot_terminate`：在可达集内，但无法到达任何终止节点（`next` 空）。
      实现为"终止节点的反向可达集"取补集——比逐点 DFS 便宜且无遗漏。
    """
    fwd = defaultdict(list)
    rev = defaultdict(list)
    for name, node in nodes.items():
        for key, ref in pj.node_refs(node):
            if key == "interrupt":
                continue
            t = pj.strip_ref_prefix(ref)
            if t in nodes:
                fwd[name].append(t)
                rev[t].append(name)

    # 可达集：任务入口 ∪ override 注入点
    starts = [t for _, t in entries if t in nodes]
    starts += sorted((extra_starts or set()) - set(starts))
    seen = set(starts)
    dq = deque(starts)
    while dq:
        cur = dq.popleft()
        for nxt in fwd[cur]:
            if nxt not in seen:
                seen.add(nxt)
                dq.append(nxt)

    # 终止节点 = next 为空或缺失
    terminals = [n for n, nd in nodes.items()
                 if not isinstance((nd or {}).get("next"), list) or not (nd or {}).get("next")]
    can_end = set(terminals)
    dq = deque(terminals)
    while dq:
        cur = dq.popleft()
        for prev in rev[cur]:
            if prev not in can_end:
                can_end.add(prev)
                dq.append(prev)

    unreachable = sorted(set(nodes) - seen)
    cannot_end = sorted(n for n in seen if n not in can_end)
    return unreachable, cannot_end


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="MaaEOV 任务图静态护栏")
    ap.add_argument("--strict", action="store_true", help="warn 也视为失败（CI 用）")
    ap.add_argument("--max-list", type=int, default=15, help="每类问题最多打印条数")
    args = ap.parse_args(argv)

    files_map, nodes, conflicts, code = load()
    if code:
        return code

    errors = 0
    warns = 0

    # 检查 0：同名节点（跨文件静默覆盖的根因，verify 第 4 段同源）
    if conflicts:
        errors += 1
        print(f"\n[FAIL] 跨文件同名节点 {len(conflicts)} 个（后者静默覆盖前者）：")
        for n, fs in list(conflicts.items())[: args.max_list]:
            print(f"   {n} <- {fs}")

    # 检查 1
    dangling = check_dangling(nodes)
    if dangling:
        errors += 1
        print(f"\n[FAIL] 悬空引用 {len(dangling)} 处：")
        for name, key, ref in dangling[: args.max_list]:
            print(f"   {name}.{key} -> {ref}")
    else:
        print("\n[OK] 悬空引用 0 处")

    # 检查 2
    traps = check_traps(nodes)
    if traps:
        errors += 1
        print(f"\n[FAIL] 陷阱自环 {len(traps)} 个（next 仅自环 + 无 on_error + 无 timeout）：")
        for n in traps[: args.max_list]:
            print(f"   {n}")
    else:
        print("[OK] 陷阱自环 0 个")

    # 检查 3（warn）
    entries = load_entries(nodes)
    if not entries:
        warns += 1
        print("\n[WARN] 未从 interface.json 读到任务入口，跳过终止可达性检查")
    else:
        ov_starts = load_override_starts(nodes)
        unreachable, cannot_end = check_termination(nodes, entries, ov_starts)
        print(f"  起点：任务入口 {len(entries)} 个 + override 注入点 {len(ov_starts)} 个")
        if unreachable:
            warns += 1
            print(f"\n[WARN] 从 {len(entries)} 个任务入口均不可达的节点 {len(unreachable)} 个：")
            for n in unreachable[: args.max_list]:
                print(f"   {n}")
        if cannot_end:
            warns += 1
            print(f"\n[WARN] 入口可达但无法到达终止节点的节点 {len(cannot_end)} 个"
                  f"（[JumpBack] 弹栈语义可能造成误报，故不阻塞）：")
            for n in cannot_end[: args.max_list]:
                print(f"   {n}")
        if not unreachable and not cannot_end:
            print(f"[OK] {len(entries)} 个入口的终止可达性检查通过（无可疑节点）")

    print("\n" + "-" * 60)
    failed = errors > 0 or (args.strict and warns > 0)
    print(f"errors={errors} warns={warns} strict={args.strict} -> "
          f"{'FAIL' if failed else 'PASS'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
