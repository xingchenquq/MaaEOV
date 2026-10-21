# -*- coding: utf-8 -*-
"""按判据为"真风险"节点批量补 `timeout`（计划 P0-2）。

**默认只读**：不带 `--apply` 时只打印将要做的改动（含样例 diff），不写任何文件。
写盘用**文本级插入**（在节点对象的 `{` 之后插入一行），因此 JSONC 注释、键顺序、
空行与缩进全部保留——与 `migrate_layout.py` 同一路数。

判据与档位全部来自 `scripts/pj.py`，与 `verify_feature.py` 第 12 段共用同一份实现，
避免"校验口径"与"修补口径"漂移（Maadori 在 check_closure 上踩过这个坑）。

用法：
    python scripts/fill_timeouts.py                      # 只读：统计 + 每档样例
    python scripts/fill_timeouts.py --diff -n 3          # 额外打印 3 个文件的 unified diff
    python scripts/fill_timeouts.py --file Shared.json --apply
    python scripts/fill_timeouts.py --tier nav --apply   # 只补某一档
"""
from __future__ import annotations

import argparse
import difflib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import pj  # noqa: E402

PIPELINE_DIR = os.path.join(ROOT, "resource", "base", "pipeline")


# ----------------------------------------------------------------------
# JSONC 结构扫描（只为定位节点对象的 `{`，不做语法树）
# ----------------------------------------------------------------------
def line_indent(text: str, pos: int) -> str:
    """返回 pos 所在行的前导空白。"""
    start = text.rfind("\n", 0, pos) + 1
    end = start
    while end < len(text) and text[end] in " \t":
        end += 1
    return text[start:end]


def node_brace_map(text: str) -> dict:
    """扫描顶层节点，返回 `{节点名: (左花括号下标, 键所在行缩进)}`。"""
    out: dict[str, tuple[int, str]] = {}
    i, n = 0, len(text)
    depth = 0
    in_str = False
    esc = False
    last_key = None
    last_indent = ""
    while i < n:
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            j = i + 1
            buf = []
            while j < n:
                c = text[j]
                if c == "\\":
                    buf.append(text[j:j + 2])
                    j += 2
                    continue
                if c == '"':
                    break
                buf.append(c)
                j += 1
            if depth == 1:
                k = j + 1
                while k < n and text[k] in " \t":
                    k += 1
                if k < n and text[k] == ":":
                    last_key = "".join(buf)
                    last_indent = line_indent(text, i)
            i = j + 1
            continue
        if ch == "{":
            depth += 1
            if depth == 2 and last_key is not None:
                out[last_key] = (i, last_indent)
                last_key = None
            i += 1
            continue
        if ch == "}":
            depth -= 1
            i += 1
            continue
        i += 1
    return out


def plan_file(path: str, nodes: dict, only_tier: str | None = None):
    """为一个文件生成插入计划：[(节点名, 插入位置, 插入文本, 值, 档位)]。"""
    text = open(path, encoding="utf-8").read()
    data = pj.load_jsonc(path)
    braces = node_brace_map(text)
    plan = []
    for name, node in data.items():
        if not isinstance(node, dict) or not pj.is_timeout_risk(node, nodes):
            continue
        tier = pj.classify_timeout_tier(name, node)
        if only_tier and tier != only_tier:
            continue
        if name not in braces:
            print(f"  !! 定位失败（跳过）: {name}")
            continue
        brace, indent = braces[name]
        value = pj.suggest_timeout(name, node, nodes)
        child_indent = indent + "    "
        # 空对象 `{}` 不能留尾逗号
        k = brace + 1
        while k < len(text) and text[k] in " \t\r\n":
            k += 1
        if k < len(text) and text[k] == "}":
            piece = f'\n{child_indent}"timeout": {value}\n{indent}'
        else:
            piece = f'\n{child_indent}"timeout": {value},'
        plan.append((name, brace + 1, piece, value, tier))
    return text, plan


def apply_plan(text: str, plan) -> str:
    """从后往前插入，保证下标不失效。"""
    out = text
    for _, pos, piece, _, _ in sorted(plan, key=lambda x: -x[1]):
        out = out[:pos] + piece + out[pos:]
    return out


# ----------------------------------------------------------------------
# main
# ----------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="为真风险节点批量补 timeout（默认只读）")
    ap.add_argument("--apply", action="store_true", help="真正写盘（缺省只读）")
    ap.add_argument("--file", action="append", default=None,
                    help="只处理指定文件（可多次），如 --file Shared.json")
    ap.add_argument("--tier", choices=sorted(pj.TIMEOUT_TIERS), default=None,
                    help="只处理某一档位")
    ap.add_argument("--dir", default=PIPELINE_DIR,
                    help="pipeline 目录（默认 resource/base/pipeline；演练时可指向副本）")
    ap.add_argument("--diff", action="store_true", help="打印 unified diff")
    ap.add_argument("-n", "--diff-files", type=int, default=2, help="打印几个文件的 diff")
    args = ap.parse_args(argv)

    files_map, errors = pj.load_pipelines(args.dir)
    for fn, err in errors:
        print(f"!! {fn} 解析失败: {err}")
    nodes, _, _ = pj.merge_nodes(files_map)

    targets = [f for f in files_map if not args.file or f in args.file]
    if args.file:
        missing = set(args.file) - set(files_map)
        for m in missing:
            print(f"!! 文件不存在: {m}")
    if not targets:
        print("没有可处理的文件")
        return 2

    total = 0
    by_tier = {k: 0 for k in pj.TIMEOUT_TIERS}
    by_value = {}
    per_file = {}
    diffs = []

    for fn in sorted(targets):
        path = os.path.join(args.dir, fn)
        text, plan = plan_file(path, nodes, args.tier)
        if not plan:
            continue
        per_file[fn] = plan
        total += len(plan)
        for _, _, _, value, tier in plan:
            by_tier[tier] += 1
            by_value[value] = by_value.get(value, 0) + 1
        if args.apply:
            new_text = apply_plan(text, plan)
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(new_text)
            if args.diff and len(diffs) < args.diff_files:
                diffs.append(difflib.unified_diff(
                    text.splitlines(True), new_text.splitlines(True),
                    fromfile=f"a/{fn}", tofile=f"b/{fn}", n=1))

    print(f"{'已写入' if args.apply else '只读预览'}：{len(per_file)} 个文件 / {total} 个节点")
    print(f"档位分布：probe {by_tier['probe']}｜nav {by_tier['nav']}｜wait {by_tier['wait']}")
    print("取值分布：" + "｜".join(
        f"{v}ms×{c}" for v, c in sorted(by_value.items())))
    print("\n按文件（降序）：")
    for fn, plan in sorted(per_file.items(), key=lambda x: (-len(x[1]), x[0])):
        tiers = {}
        for _, _, _, v, t in plan:
            tiers[t] = tiers.get(t, 0) + 1
        head = "、".join(n for n, *_ in plan[:4]) + ("…" if len(plan) > 4 else "")
        print(f"  {fn:<28}{len(plan):>4} 个  {tiers}  {head}")

    if args.diff:
        shown = diffs if args.apply else []
        if not args.apply:
            # 只读模式下也给出样例 diff（不落盘）
            for fn, plan in sorted(per_file.items(), key=lambda x: (-len(x[1]), x[0]))[:args.diff_files]:
                path = os.path.join(args.dir, fn)
                text = open(path, encoding="utf-8").read()
                shown.append(difflib.unified_diff(
                    text.splitlines(True), apply_plan(text, plan).splitlines(True),
                    fromfile=f"a/{fn}", tofile=f"b/{fn}", n=1))
        for d in shown:
            sys.stdout.writelines(d)
            print()

    if not args.apply:
        print("\n（未写盘。确认后加 --apply，建议按文件分批：先 Shared.json 单独一批）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
