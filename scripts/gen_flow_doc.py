# -*- coding: utf-8 -*-
"""MaaEOV 任务流程文档生成器：从 pipeline 生成「任务流程与UI重测清单」。

输出 docs/internal/任务流程与UI重测清单.md，供游戏客户端 UI 改版后逐项重测识别依赖（内部文档，不随公开仓库分发）
（模板切图 / OCR 文案 / ROI 坐标）。**本文件为唯一权威生成入口，文档请勿手改**——
改完 pipeline 后重跑本脚本即可，CI（verify.yml）会比对文档是否与 pipeline 同步。

生成逻辑：
1. 按 interface.json 的 task 顺序，从每个 entry 节点出发深度优先展开主链路；
2. next 中 [JumpBack] 项不展开，汇总为「中断保底」清单（弹窗兜底，非正常流程）；
3. 同一节点全局只展开一次（先到先得），后续遇到显示 ↺ 引用行；
4. 文末列出被多个任务链路复用的节点（UI 改版时改一处影响多处，需重点回归）。

用法：python scripts/gen_flow_doc.py
"""
import json
import os
import re
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(_SCRIPT_DIR)                    # 仓库根目录
PIPELINE_DIR = os.path.join(ROOT, "resource", "base", "pipeline")
INTERFACE = os.path.join(ROOT, "interface.json")
OUT_DIR = os.path.join(ROOT, "docs", "internal")
os.makedirs(OUT_DIR, exist_ok=True)
OUT = os.path.join(OUT_DIR, "任务流程与UI重测清单.md")


def _ensure_inside_root(path: str) -> str:
    """写访问前校验：规范化并把目标限制在仓库根目录内，防路径逃逸。"""
    root = os.path.abspath(ROOT)
    normalized = os.path.normpath(os.path.abspath(path))
    if normalized != root and not normalized.startswith(root + os.sep):
        raise SystemExit(f"[FAIL] 路径越界，拒绝访问: {normalized}")
    return normalized


def strip_jsonc(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    out = []
    for line in text.split("\n"):
        if "//" in line and "http://" not in line and "https://" not in line:
            line = line[:line.find("//")]
        out.append(line)
    return "\n".join(out)


def load_jsonc(path: str):
    with open(path, encoding="utf-8") as f:
        return json.loads(strip_jsonc(f.read()))


def strip_prefix(t: str) -> str:
    """剥 [JumpBack] / [Anchor] 前缀，取实际节点名。"""
    for pfx in ("[JumpBack]", "[Anchor]"):
        if t.startswith(pfx):
            return t[len(pfx):]
    return t


def reco_desc(node: dict) -> str:
    """「识别方式 (UI 依赖)」列：模板/OCR/Custom/DirectHit/—。"""
    rec = node.get("recognition")
    if rec is None:
        return "—"
    if isinstance(rec, str):
        return rec
    p = rec.get("param") or {}
    roi = p.get("roi")
    roi_s = f" roi={roi}" if roi else ""
    t = rec.get("type")
    if t == "TemplateMatch":
        thr = p.get("threshold")
        thr_s = "" if thr is None else f" thr={thr}"
        return f"模板[{p.get('template')}] roi={roi}{thr_s}"
    if t == "OCR":
        return f"OCR{p.get('expected')}{roi_s}"
    if t == "Custom":
        return f"Custom['{p.get('custom_recognition')}']"
    return f"{t}{roi_s}"


def action_desc(node: dict) -> str:
    """「动作」列：Click/Swipe/StartApp/Custom/—(仅路由)。"""
    act = node.get("action")
    if act is None:
        return "—(仅路由)"
    if isinstance(act, str):
        return act
    t = act.get("type")
    p = act.get("param") or {}
    if t == "Click":
        if p.get("target"):
            return f"Click@{p['target']}"
        if p.get("target_offset"):
            return f"Click@offset{p['target_offset']}"
        return "Click"
    if t == "Custom":
        return f"Custom['{p.get('custom_action')}']"
    return t


def next_desc(nexts) -> str:
    """「后续」列：next 中非 [JumpBack] 项（主链路 / 路由候选）。"""
    mains = [t for t in nexts if not t.startswith("[JumpBack]")]
    if not mains:
        return "（结束）"
    return " / ".join(f"`{t}`" for t in mains)


def main() -> int:
    out_path = _ensure_inside_root(OUT)

    iface = load_jsonc(INTERFACE)
    pipelines = {}          # 文件名 -> 节点字典
    node_owner = {}         # 节点名 -> 定义文件
    all_nodes = set()
    for fn in sorted(os.listdir(PIPELINE_DIR)):
        if not fn.endswith(".json"):
            continue
        d = load_jsonc(os.path.join(PIPELINE_DIR, fn))
        pipelines[fn] = d
        for n in d:
            node_owner.setdefault(n, fn)
        all_nodes |= set(d.keys())

    # entry/next 引用剥了 # / [JumpBack] 前缀，而节点注册名带 #，需先映射回原始名
    stripped_owner = {n.lstrip("#"): n for n in node_owner}

    def find(name: str):
        orig = stripped_owner.get(name, name)
        fn = node_owner.get(orig)
        return (pipelines[fn].get(orig) or {}) if fn else None

    lines = []
    lines.append("# MaaEOV 任务流程梳理与 UI 变更重测清单")
    lines.append("")
    lines.append(f"> 自动生成自 `resource/base/pipeline/` 下 {len(pipelines)} 个流水线文件"
                 f"（`scripts/gen_flow_doc.py`，**请勿手改本文档**；改 pipeline 后重跑生成器，CI 会校验同步）。")
    lines.append("")
    lines.append("> 基准分辨率：1280×720。所有坐标、ROI 均为该基准下的像素值，UI 改版后需逐项复核。")
    lines.append("")
    lines.append(f"> 共解析到 **{len(iface.get('task', []))}** 个任务入口、**{len(all_nodes)}** 个节点。")
    lines.append("")
    lines.append("## 公共约定（所有任务共用）")
    lines.append("")
    lines.append("- 每个节点的 `next` 列表中，以 `[JumpBack]_XXX` 开头的是**中断/弹窗保底处理**"
                 "（服务器维护、断线重连、升级弹窗、领奖等），不属正常流程，故下方流程表默认只列**主链路**"
                 "（`next` 首项）。")
    lines.append("- `DirectHit` 节点**必定命中**，多用于「路由/播报/兜底」；"
                 "`TemplateMatch`/`OCR` 节点按识别结果决定是否执行、再到 `next`。")
    lines.append("- **UI 重测重点**：流程表里「识别」列即该步的 UI 依赖——模板图片需重新截图、"
                 "OCR 文案需逐字核对、坐标需重新定位。任一变更都会导致该节点识别失败、任务卡死或错点。")
    lines.append("- 同一节点跨任务复用时只在首次出现处展开，其余位置标 ↺；"
                 "被多个任务复用的节点单独汇总在文末（改一处影响多处，需一并回归）。")
    lines.append("")
    lines.append("---")

    global_visited = set()      # 全局已展开节点（跨任务去重）
    task_touch = {}             # 节点名 -> 触碰它的任务名集合
    warnings = []

    for task in iface.get("task", []):
        tname = task.get("name", "?")
        entry = (task.get("entry") or "").lstrip("#")
        lines.append("")
        lines.append(f"## `{task.get('entry')}`（{tname}）")
        lines.append("")
        if entry not in stripped_owner:
            warnings.append(f"任务「{tname}」的 entry `{task.get('entry')}` 不在任何 pipeline 中")
            lines.append(f"> [WARN] entry `{task.get('entry')}` 不存在，跳过。")
            continue

        rows = []       # (depth|None, 节点名, 节点dict|None)  None depth = ↺ 行
        backups = []    # [JumpBack] 保底（原样）
        local_visited = set()

        def walk(name: str, depth: int):
            if name in local_visited or name in global_visited:
                # ↺ 引用同样计入「跨任务复用」统计（主链路层面改一处影响多处）
                task_touch.setdefault(name, set()).add(tname)
                rows.append((None, name, None))
                return
            local_visited.add(name)
            global_visited.add(name)
            task_touch.setdefault(name, set()).add(tname)
            node = find(name)
            rows.append((depth, name, node))
            if node is None:
                warnings.append(f"任务「{tname}」链路引用了不存在的节点 `{name}`")
                return
            nexts = node.get("next") or []
            for t in nexts:
                if t.startswith("[JumpBack]"):
                    backups.append(t)
                    continue
                walk(strip_prefix(t), depth + 1)

        walk(entry, 0)

        lines.append("| 步骤 | 节点 | 识别方式 (UI 依赖) | 动作 | 后续 (主链路 / 路由候选) |")
        lines.append("|----|------|------------------|------|--------------------------|")
        for depth, name, node in rows:
            pad = "&nbsp;" * 2 * depth if depth else ""
            step = str(depth) if depth is not None else "·"
            if node is None:
                lines.append(f"| {pad}{step} | `{name}` | ↺ 回到已访问节点（循环/重复，已在上文展开） | | |")
                continue
            nexts = node.get("next") or []
            lines.append(f"| {pad}{step} | `{name}` | {reco_desc(node)} | {action_desc(node)} | {next_desc(nexts)} |")
        lines.append("")
        uniq_backup = list(dict.fromkeys(backups))
        if uniq_backup:
            lines.append("> 该任务挂载的中断保底：" + ", ".join(f"`{t}`" for t in uniq_backup))
        lines.append("")

    # 文末：被多个任务链路复用的节点
    shared = sorted(
        ((n, ts) for n, ts in task_touch.items() if len(ts) > 1),
        key=lambda x: (-len(x[1]), x[0]),
    )
    lines.append("---")
    lines.append("")
    lines.append(f"## 跨任务复用节点（共 {len(shared)} 个，改版回归时需一并验证）")
    lines.append("")
    if shared:
        lines.append("| 节点 | 定义文件 | 复用任务数 | 复用任务 |")
        lines.append("|------|---------|-----------|---------|")
        for n, ts in shared:
            owner = node_owner.get(n, "?")
            lines.append(f"| `{n}` | {owner} | {len(ts)} | {'、'.join(sorted(ts))} |")
    else:
        lines.append("（无）")
    lines.append("")

    if warnings:
        lines.append("---")
        lines.append("")
        lines.append("## 生成警告")
        lines.append("")
        for w in warnings:
            lines.append(f"- [WARN] {w}")
        lines.append("")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines))
    print(f"[OK] 已生成 {os.path.relpath(out_path, ROOT)}"
          f"（{len(iface.get('task', []))} 任务、{len(all_nodes)} 节点、{len(lines)} 行）")
    for w in warnings:
        print(f"[WARN] {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
