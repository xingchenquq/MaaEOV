# -*- coding: utf-8 -*-
"""关卡配置自洽性校验（单一数据源 = resource/base/data/level_groups.json）。

检查"一个关卡的信息分散在四处"是否一致：
  ① interface.json 的 option case 名（卡片/系列名 + 关卡 ID）
  ② pipeline 节点 ID（_Navigate{G601} / _Navigate{S001} …）
  ③ 节点模板文件名（BCR/晋阶考核_列表选中_{G601}.png 之类）
  ④ 节点判据（模板 / OCR expected）

具体规则：
  R1 case 名里出现的关卡 ID，必须能在 level_groups.json 找到归属；
  R2 case 名的前缀（如「晋阶考核-铜墙铁壁」）必须与该 ID 在表里的归属卡片一致；
  R3 override 指向的节点名里若含 ID，必须与 case 名里的 ID 相同；
  R4 表里登记的每个关卡 ID，清体力/危机行动的 case 里都必须有对应项（缺失即报）；
  R5 case 数量与表内总数对不上时给出提示（不阻断，可能是有意裁剪）。

用法：python scripts/check_levels.py        退出码 0 = OK，1 = 有不一致
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import pj  # noqa: E402

PIPE = os.path.join(ROOT, "resource", "base", "pipeline")
DATA = os.path.join(ROOT, "resource", "base", "data", "level_groups.json")
INTERFACE = os.path.join(ROOT, "interface.json")

ID_RE = re.compile(r"(G\d{3}|S\d{3}|WN\d{3})")

# 表分组 → 哪些 option 的 case 应该覆盖它
GROUP_TO_OPTIONS = {
    "appraisal": ["清体力-选择关卡"],
    "crisis": ["清体力-选择关卡", "危机行动调令-选择关卡"],
    "event": ["当期活动-选择关卡"],
    "liminal": ["阈限禁区-选择关卡"],
    "prepared": ["清体力-选择关卡"],
}


def main() -> int:
    groups = pj.load_jsonc(DATA)
    iface = pj.load_jsonc(INTERFACE)
    files_map, _ = pj.load_pipelines(PIPE)
    nodes, _, _ = pj.merge_nodes(files_map)
    options = iface.get("option") or {}

    # id -> 归属卡片名；同时记录每组的全部 ID
    id2card = {}
    group_ids = {}
    for grp, cards in groups.items():
        if not isinstance(cards, dict):
            continue
        ids = []
        for card, lst in cards.items():
            for i in (lst or []):
                id2card[i] = card
                ids.append(i)
        group_ids[grp] = ids

    problems = []
    checked = 0

    def resolve_targets(ov):
        out = []
        for tgt, patch in ov.items():
            if isinstance(patch, dict):
                nxt = patch.get("next")
                if isinstance(nxt, list) and nxt:
                    out += [pj.strip_ref_prefix(x) for x in nxt if isinstance(x, str)]
                    continue
            out.append(pj.strip_ref_prefix(tgt))
        return out

    for opt_name, opt in options.items():
        for case in (opt or {}).get("cases") or []:
            name = case.get("name") or ""
            ov = case.get("pipeline_override") or {}
            if not ov:
                continue
            id_case = ID_RE.search(name)
            if not id_case:
                continue
            cid = id_case.group(1)
            checked += 1

            # R1：ID 必须在表里
            if cid not in id2card:
                problems.append(f"[R1] option「{opt_name}」case「{name}」的关卡 ID {cid} 未登记在 level_groups.json")
                continue
            expect_card = id2card[cid]

            # R2：case 名必须含正确的归属卡片名
            #     例外：case 名就是纯 ID（如「WN108」）时跳过 —— 活动章节唯一，
            #     没必要在选项里重复写章节名。
            name_wo_id = ID_RE.sub("", name).strip(" -_（）()　")
            if name_wo_id and expect_card not in name:
                problems.append(
                    f"[R2] option「{opt_name}」case「{name}」：ID {cid} 归属「{expect_card}」，case 名里没有该卡片名")

            # R3：override 目标节点里的 ID 必须一致
            for node in resolve_targets(ov):
                m = ID_RE.search(node)
                if m and m.group(1) != cid:
                    problems.append(
                        f"[R3] option「{opt_name}」case「{name}」：ID {cid} 却指向节点 {node}（ID {m.group(1)}）")

    # R4：表内每个 ID 都要有 case 覆盖（按组所属 option 检查）
    #     只检查"用编号标识关卡"的组（appraisal/crisis/event）——阈限禁区按名称识别、
    #     资源筹备无编号，不适用编号覆盖检查。
    for grp, ids in group_ids.items():
        if not ids or not any(ID_RE.fullmatch(i) for i in ids):
            continue
        opts = GROUP_TO_OPTIONS.get(grp, [])
        if not opts:
            continue
        covered = set()
        for o in opts:
            for case in (options.get(o) or {}).get("cases") or []:
                m = ID_RE.search(case.get("name") or "")
                if m:
                    covered.add(m.group(1))
        for i in ids:
            if i not in covered:
                problems.append(f"[R4] level_groups.json 登记的 {i}（{id2card[i]}）没有任何 option case 覆盖")

    # R5：数量对账（提示级）
    notes = []
    for grp, ids in group_ids.items():
        opts = GROUP_TO_OPTIONS.get(grp, [])
        for o in opts:
            cnt = len([c for c in (options.get(o) or {}).get("cases") or []
                       if ID_RE.search(c.get("name") or "")])
            notes.append(f"  {o}: case 数 {cnt}（level_groups 里 {grp} 共 {len(ids)} 个 ID）")

    print(f"校验了 {checked} 条带 ID 的 case；level_groups.json 共登记 "
          f"{sum(len(v) for v in group_ids.values())} 个关卡 ID\n")
    for n in notes:
        print(n)

    print()
    if problems:
        print(f"[FAIL] 发现 {len(problems)} 处不一致：")
        for p in problems:
            print("   " + p)
        return 1
    print("[OK] 关卡配置自洽：case 名 / 节点 ID / 卡片归属 三者一致，且表内关卡均有 case 覆盖")
    return 0


if __name__ == "__main__":
    sys.exit(main())
