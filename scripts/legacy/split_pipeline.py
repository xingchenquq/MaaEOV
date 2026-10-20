# -*- coding: utf-8 -*-
"""把 Tasks.json 按「功能入口」拆分为多个独立 pipeline 文件（预览产物，不触碰线上目录）。

规则
----
- 入口（顶层 ``#X`` 节点）各成一份文件：从每个入口沿 ``next`` 做可达性 BFS。
- 仅被**单一入口**可达的节点 -> 归该入口文件。
- 被 **0 个或多个入口**可达（孤儿 / 共享）的节点 -> ``Shared.json``。
- 每个节点名在全部文件中**只定义一次**（消除 MaaFw 跨文件静默覆盖）。

实现要点
--------
- 采用**花括号深度扫描**定位顶层节点，而不依赖缩进（原文件存在缩进不一致的区块）。
- 保留原文件的行注释（``//``）与块注释（``/* */``），按节点随行搬移。
- 产出到 ``temp/pipeline_split/pipeline/``，另写 ``_REPORT.md`` 与 ``_manifest.json``。

控制台仅输出 ASCII，详细报告写 UTF-8 文件。
"""
import json
import os
import re
import sys
import collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DEFAULT = os.path.join(ROOT, "resource", "base", "pipeline", "Tasks.json")


def resolve_src():
    """Tasks.json 若已迁移删除，则回退到 temp/_pipeline_backup 下最新的一份。"""
    if os.path.exists(SRC_DEFAULT):
        return SRC_DEFAULT
    backups_root = os.path.join(ROOT, "temp", "_pipeline_backup")
    cands = []
    if os.path.isdir(backups_root):
        for d in os.listdir(backups_root):
            p = os.path.join(backups_root, d, "Tasks.json")
            if os.path.exists(p):
                cands.append(p)
    return sorted(cands)[-1] if cands else SRC_DEFAULT

IFACE = os.path.join(ROOT, "interface.json")
OUT_BASE = os.path.join(ROOT, "temp", "pipeline_split")
OUT_PIPE = os.path.join(OUT_BASE, "pipeline")

ENTRY_FILE = {
    "#StartUp": "Startup",
    "#ShutDown": "ShutDown",
    "#ExitApp": "ExitApp",
    "#Farm": "Farm",
    "#CrisisMissionTickets": "CrisisMissionTickets",
    "#LiminalZone": "LiminalZone",
    "#JointBlockade": "JointBlockade",
    "#TheRoom": "TheRoom",
    "#Supplies": "Supplies",
    "#UrbanPatrol": "UrbanPatrol",
    "#CollectRewards": "CollectRewards",
    "#CountermeasureProtocol": "CountermeasureProtocol",
    "#Mailbox": "Mailbox",
    "#ExternalRecruit": "ExternalRecruit",
    "#DailyStaminaBonus": "DailyStaminaBonus",
    "#ShortTermCheckIn": "ShortTermCheckIn",
    "#当期活动": "CurrentEvent",
    "#往期活动": "PastEvent",
}
SHARED = "Shared"
NODE_PREFIXES = ("[JumpBack]", "[Anchor]")


def strip_jsonc(text):
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = []
    for line in text.split("\n"):
        if "//" in line and "http://" not in line and "https://" not in line:
            line = line[: line.find("//")]
        out.append(line)
    return "\n".join(out)


def load_jsonc(path):
    with open(path, encoding="utf-8") as f:
        return json.loads(strip_jsonc(f.read()))


def scan_top_nodes(lines):
    """花括号深度扫描，返回按出现顺序的顶层节点 [(name, start_line, end_line)]。

    对字符串 / 行注释 / 块注释均做规避，缩进无关。
    """
    results = []
    depth = 0
    in_str = False
    in_block = False
    esc = False
    cur_key = None
    cur_start = None
    for i, line in enumerate(lines):
        j = 0
        n = len(line)
        while j < n:
            c = line[j]
            if in_block:
                if c == "*" and j + 1 < n and line[j + 1] == "/":
                    in_block = False
                    j += 2
                    continue
                j += 1
                continue
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
                j += 1
                continue
            if c == "/" and j + 1 < n and line[j + 1] == "/":
                break  # 行注释，忽略本行余下部分
            if c == "/" and j + 1 < n and line[j + 1] == "*":
                in_block = True
                j += 2
                continue
            if c == '"':
                if depth == 1:
                    k = j + 1
                    buf = []
                    while k < n:
                        ch = line[k]
                        if ch == "\\":
                            buf.append(line[k:k + 2])
                            k += 2
                            continue
                        if ch == '"':
                            break
                        buf.append(ch)
                        k += 1
                    name = "".join(buf)
                    m = k + 1
                    while m < n and line[m] in " \t":
                        m += 1
                    if m < n and line[m] == ":":
                        cur_key = name
                        cur_start = i
                    j = k + 1
                    continue
                in_str = True
                j += 1
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 1 and cur_key is not None:
                    results.append((cur_key, cur_start, i))
                    cur_key = None
            j += 1
    return results


def _advance_depth(line, depth, in_block):
    """按行更新 brace/bracket 深度；跳过字符串与注释。返回 (depth, in_block)。"""
    i = 0
    n = len(line)
    in_str = False
    esc = False
    while i < n:
        c = line[i]
        if in_block:
            if c == "*" and i + 1 < n and line[i + 1] == "/":
                in_block = False
                i += 2
                continue
            i += 1
            continue
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == "/" and i + 1 < n and line[i + 1] == "/":
            break
        if c == "/" and i + 1 < n and line[i + 1] == "*":
            in_block = True
            i += 2
            continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if c in "{[": 
            depth += 1
        elif c in "}]":
            depth -= 1
        i += 1
    return depth, in_block


def reindent_block(block_lines, start_depth=1):
    """把一段顶层节点（含其上方注释）按 4 空格/层级重新缩进。

    只改前导空白，不动行内容与行尾；对已规范的块是幂等的。
    """
    out = []
    depth = start_depth
    in_block = False
    for raw in block_lines:
        if raw.strip() == "":
            out.append("")
            continue
        content = raw.lstrip(" \t")
        if in_block or content.startswith("//") or content.startswith("/*"):
            eff = depth
        else:
            eff = depth - 1 if content[0] in ("}", "]") else depth
        out.append("    " * max(eff, 0) + content)
        depth, in_block = _advance_depth(raw, depth, in_block)
    return out


def ref_targets(node):
    res = []
    if not isinstance(node, dict):
        return res
    for key in ("next", "interrupt", "on_error"):
        v = node.get(key)
        if isinstance(v, str):
            res.append(v)
        elif isinstance(v, list):
            for t in v:
                if isinstance(t, str):
                    res.append(t)
    return res


def strip_prefix(t):
    for p in NODE_PREFIXES:
        if t.startswith(p):
            return t[len(p):]
    return t


def main():
    src = resolve_src()
    print("SRC=%s" % src)
    tasks = load_jsonc(src)
    with open(src, encoding="utf-8") as f:
        lines = f.read().split("\n")

    scanned = scan_top_nodes(lines)
    scan_names = [s[0] for s in scanned]
    diag = {
        "json_keys": len(tasks),
        "scanned": len(scanned),
        "missing_from_scan": sorted(set(tasks) - set(scan_names)),
        "extra_in_scan": sorted(set(scan_names) - set(tasks)),
        "scan_duplicates": [n for n, c in collections.Counter(scan_names).items() if c > 1],
    }

    # ---- 构建图：节点 -> 后继（next / interrupt / on_error） ----
    edges = collections.defaultdict(list)
    for name, node in tasks.items():
        for t in ref_targets(node):
            tgt = strip_prefix(t)
            if tgt in tasks:
                edges[name].append(tgt)

    # interface.json 的 option.pipeline_override 会在运行期注入 next，补上这些边
    if os.path.exists(IFACE):
        iface = load_jsonc(IFACE)
        for opt_name, opt in (iface.get("option") or {}).items():
            for case in (opt.get("cases") or []):
                ov = case.get("pipeline_override") or {}
                for k, v in ov.items():
                    if not isinstance(v, dict):
                        continue
                    for t in ref_targets(v):
                        tgt = strip_prefix(t)
                        if tgt in tasks and tgt not in edges[k]:
                            edges[k].append(tgt)

    roots = [n for n in scan_names if n.startswith("#")]

    # ---- 每个入口做 BFS（注意：入口自身必须计入自己的可达集） ----
    reach = {}
    for r in roots:
        seen = {r}
        dq = collections.deque([r])
        while dq:
            cur = dq.popleft()
            for nxt in edges.get(cur, []):
                if nxt not in seen:
                    seen.add(nxt)
                    dq.append(nxt)
        reach[r] = seen

    owners = collections.defaultdict(list)
    for n in tasks:
        for r in roots:
            if n in reach[r]:
                owners[n].append(r)

    # ---- 分配节点到文件 ----
    assignment = {}      # node -> filename (no .json)
    orphan = []
    multi = []
    for n, node in tasks.items():
        if len(owners[n]) == 1:
            r = owners[n][0]
            assignment[n] = ENTRY_FILE.get(r, r.lstrip("#") or "Feature")
        else:
            assignment[n] = SHARED
            if len(owners[n]) == 0:
                orphan.append(n)
            else:
                multi.append(n)

    # ---- 按文件收集节点（保持原文件顺序） ----
    file_nodes = collections.OrderedDict()
    for name, start, end in scanned:
        fn = assignment.get(name, SHARED)
        file_nodes.setdefault(fn, []).append((name, start, end))

    # ---- 生成每个文件的正文（含随行注释） ----
    def node_snippet(name, start, end, prev_end):
        lo = prev_end + 1 if prev_end is not None else 1
        blk_lines = reindent_block(lines[lo:end + 1], 1)
        blk = "\n".join(blk_lines).rstrip()
        if blk.endswith(","):
            blk = blk[:-1].rstrip()
        return blk

    os.makedirs(OUT_PIPE, exist_ok=True)
    written = {}
    prev_end_by_order = {}
    # 记录每个顶层节点在“全文件顺序”里的前一个节点 end_line，用于取随行注释
    ordered = [(n, s, e) for n, s, e in scanned]
    for idx, (name, start, end) in enumerate(ordered):
        prev_end_by_order[idx] = ordered[idx - 1][2] if idx > 0 else None

    file_bodies = collections.OrderedDict()
    for idx, (name, start, end) in enumerate(ordered):
        fn = assignment.get(name, SHARED)
        file_bodies.setdefault(fn, []).append(
            (name, node_snippet(name, start, end, prev_end_by_order[idx])))

    def shared_deps(fn):
        local = {n for n, _, _ in file_nodes.get(fn, [])}
        deps = set()
        for name, start, end in file_nodes.get(fn, []):
            for t in ref_targets(tasks.get(name, {})):
                tgt = strip_prefix(t)
                if tgt in tasks and assignment.get(tgt) == SHARED and tgt not in local:
                    deps.add(tgt)
        return sorted(deps)

    # interface.json 元信息（中文任务名 / 简介首段），用于生成文件头中文注释
    entry_meta = {}
    if os.path.exists(IFACE):
        iface_meta = load_jsonc(IFACE)
        for t in iface_meta.get("task", []):
            e = t.get("entry")
            if e:
                doc = (t.get("doc") or "").strip()
                first = doc.split("\n\n")[0].replace("\n", " ").strip() if doc else ""
                entry_meta[e] = {"cn": t.get("name", ""), "doc": first}

    for fn, nodes_in_file in file_bodies.items():
        entry = next((k for k, v in ENTRY_FILE.items() if v == fn), None)
        meta = entry_meta.get(entry, {}) if entry else {}
        cn = meta.get("cn", "")
        doc = meta.get("doc", "")
        deps = [d for d in shared_deps(fn) if assignment.get(d) == SHARED]

        hdr = []
        hdr.append("    // " + "=" * 60)
        if fn == SHARED:
            names = [n for n, _ in nodes_in_file]
            n_tilde = sum(1 for n in names if n.startswith("~"))
            n_under = sum(1 for n in names if n.startswith("_"))
            hdr.append("    // Shared.json  |  全局共享库（跨功能复用；每个节点全局唯一定义一次）")
            hdr.append("    // 含：~ 终屏判定 %d 个  /  _ 通用与导航 %d 个" % (n_tilde, n_under))
        else:
            hdr.append("    // %s.json" % fn)
            if cn:
                hdr.append("    // 功能：%s" % cn)
            hdr.append("    // 入口节点：%s" % (entry or "-"))
            if doc:
                hdr.append("    // 说明：%s" % doc)
        hdr.append("    // 由 scripts/split_pipeline.py 从 Tasks.json 拆分生成；请勿跨文件重复定义同名节点。")
        hdr.append("    // 本文件节点数 = %d" % len(nodes_in_file))
        if deps:
            hdr.append("    // 依赖 Shared.json 节点数 = %d（示例：%s）" % (len(deps), ", ".join(deps[:6])))
        hdr.append("    // " + "=" * 60)

        parts = []
        for name, text in nodes_in_file:
            if entry and name == entry:
                tag = "（%s）" % cn if cn else ""
                parts.append("    // ---------- 任务入口：%s%s ----------\n\n%s" % (entry, tag, text))
            else:
                parts.append(text)

        out = "{\n" + "\n".join(hdr) + "\n\n" + ",\n\n".join(parts) + "\n}\n"
        path = os.path.join(OUT_PIPE, fn + ".json")
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(out)
        written[fn] = path

    # ---- 完整性自检 ----
    merged = {}
    for fn in written:
        d = load_jsonc(written[fn])
        for k in d:
            if k in merged:
                diag.setdefault("merged_dup", []).append((k, fn, merged[k]))
            merged[k] = fn
    missing_nodes = sorted(set(tasks) - set(merged))
    extra_nodes = sorted(set(merged) - set(tasks))
    dangling = []
    for k, node in merged.items():
        for t in ref_targets(tasks.get(k, {})):
            tgt = strip_prefix(t)
            if tgt not in merged:
                dangling.append((k, t))

    report = []
    report.append("# Tasks.json 拆分预览报告")
    report.append("")
    report.append("- 源文件：`resource/base/pipeline/Tasks.json`")
    report.append("- 源节点数（json）：%d" % diag["json_keys"])
    report.append("- 深度扫描节点数：%d" % diag["scanned"])
    report.append("- 入口（#）数：%d" % len(roots))
    report.append("- 产出文件数：%d（含 Shared.json）" % len(written))
    report.append("- 孤儿节点（0 入口可达，归 Shared）：%d" % len(orphan))
    report.append("- 多入口共享节点（>=2，归 Shared）：%d" % len(multi))
    report.append("")
    report.append("## 各文件节点数")
    report.append("")
    for fn in written:
        report.append("- `%s.json`：%d" % (fn, len(file_nodes.get(fn, []))))
    report.append("")
    report.append("## 完整性校验")
    report.append("")
    report.append("- json 键与深度扫描是否一致：%s" % ("是" if not diag["missing_from_scan"] and not diag["extra_in_scan"] else "否"))
    report.append("- 扫描结果内重复键：%s" % (diag["scan_duplicates"] or "无"))
    report.append("- 生成文件合并后重复定义：%s" % (len(diag.get("merged_dup", [])) or "无"))
    report.append("- 合并后缺失节点：%s" % (missing_nodes[:20] or "无"))
    report.append("- 合并后多余节点：%s" % (extra_nodes[:20] or "无"))
    report.append("- 合并后 next 死链：%s" % (dangling[:20] or "无"))
    report.append("")
    report.append("## 归入 Shared.json 的节点")
    report.append("")
    for n in file_nodes.get(SHARED, []):
        report.append("- %s" % n[0])
    report.append("")
    with open(os.path.join(OUT_BASE, "_REPORT.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(report))

    with open(os.path.join(OUT_BASE, "_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"node_to_file": assignment, "entry_to_file": ENTRY_FILE,
                   "orphan": sorted(orphan), "multi_owner": sorted(multi)},
                  f, ensure_ascii=False, indent=2)

    # 控制台 ASCII 摘要
    print("json_keys=%d scanned=%d entries=%d files=%d" % (
        diag["json_keys"], diag["scanned"], len(roots), len(written)))
    print("missing_from_scan=%d extra_in_scan=%d scan_dups=%d" % (
        len(diag["missing_from_scan"]), len(diag["extra_in_scan"]), len(diag["scan_duplicates"])))
    print("orphan=%d multi_owner=%d merged_dup=%d missing=%d extra=%d dangling=%d" % (
        len(orphan), len(multi), len(diag.get("merged_dup", [])),
        len(missing_nodes), len(extra_nodes), len(dangling)))
    print("OUT=%s" % OUT_PIPE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
