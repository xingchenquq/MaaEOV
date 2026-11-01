# -*- coding: utf-8 -*-
"""MaaEOV 开发校验脚本（对应 maaeov-feature-add 技能 Step 6）。

校验内容：
1. interface.json 与全部 pipeline 文件按 JSONC 解析（剥离 // 注释）。
2. agent/ 注册的 custom_action / custom_recognition 清单 + 全部 .py 语法编译。
3. interface.json 任务登记：entry 存在、挂载的 option 均已定义。
4. 全 pipeline 跨文件合并检查：
   - 跨文件同名节点（硬性失败）：MaaFw 合并时后者静默覆盖前者，会丢逻辑；
   - next / on_error 死链检测（剥离 [JumpBack] / [Anchor] 前缀）；
   - template 切图存在性；
   - custom_action / custom_recognition 注册核对。
5. **option.pipeline_override 校验**：override 目标节点、override 内 next/on_error 引用
   必须存在于合并节点集。静态扫 next 看不到 override 动态挂载的节点
   （如「设置往期活动战斗次数」仅经 interface.json override 挂入往期活动链），故必须单独校验。
6. **扫荡链 timeout 检查**：扫荡链关键节点（_Sweep* / *ConfirmSweep* / 战斗次数 /
   点击出发 / 快速完成 / 等待结果）必须显式写 timeout。缺省 ~20s 会在「等结算」阶段
   被提前掐断造成假阴性（v1.14.6 危机行动调令根因，实测约 27s 报失败）。
7. **ROI 越界检查**：坐标基准 1280×720，roi / target 超出画面即 FAIL
   （MaaFW 会静默裁剪不报错，但属数据瑕疵，统一拦在校验层）。
8. 「点击确定」防卡死修复状态：expected 必须同时含「确定」与「确认退出」。
9-11. ROI 越界 / 扫荡链 timeout / 点击确定兜底（见各段标题）。
12. **真风险节点 timeout**：非终端 + 无 timeout + `next` 中无即时命中候选
    （判据见 scripts/pj.py::is_timeout_risk）。2026-10-21 已补齐全库 221 个，
    本段由 WARN 升级为 **FAIL**；新增节点漏写会被拦下。
13. `on_error` 自环（指向自身 → 无限重试）。
14. 生成层一致性（存在 `pipeline_src/` 时调用 `pipeline_gen.py --check`）。
15. 资源包清单一致性（存在 `pipeline/.manifest.json` 时比对哈希）。
16. agent 注册扫描覆盖（子目录存在时提示未递归扫描，P1-7 迁移前置护栏）。

解析与判据统一由 `scripts/pj.py` 提供，本脚本不再保留第二份实现。

用法：python scripts/verify_feature.py（退出码 0 = ALL_OK，1 = HAS_ISSUES）。
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import py_compile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INTERFACE = os.path.join(ROOT, "interface.json")
IMAGE_ROOT = os.path.join(ROOT, "resource", "base", "image")
AGENT_DIR = os.path.join(ROOT, "agent")
PIPELINE_DIR = os.path.join(ROOT, "resource", "base", "pipeline")

MAIN = os.path.join(AGENT_DIR, "main.py")
SCREEN_W, SCREEN_H = 1280, 720


def _pj_import():
    """公共解析层（scripts/pj.py）。判据只写一份，禁止在此另立实现。"""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    import pj  # noqa: E402
    return pj


pj = _pj_import()

# 兼容旧调用点：统一转调 pj（避免第三、第四份实现）
strip_jsonc = pj.strip_jsonc
load_jsonc = pj.load_jsonc
iter_templates = pj.iter_templates
strip_next_prefix = pj.strip_ref_prefix


def section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def main() -> int:
    ok = True

    # ------------------------------------------------------------------
    section("1) JSONC 解析：interface.json + 全部 pipeline")
    try:
        iface = load_jsonc(INTERFACE)
        print("  [OK] interface.json 解析成功")
    except Exception as e:
        ok = False
        print(f"  [FAIL] interface.json 解析失败: {e}")
        iface = {}

    pipelines = {}          # 文件名 -> 节点字典
    node_owner = {}         # 节点名 -> 定义它的文件名
    all_nodes = set()       # 跨文件合并后的全部节点名
    for fn in sorted(os.listdir(PIPELINE_DIR)):
        if not fn.endswith(".json"):
            continue
        try:
            d = load_jsonc(os.path.join(PIPELINE_DIR, fn))
        except Exception as e:
            ok = False
            print(f"  [FAIL] {fn} 解析失败: {e}")
            continue
        pipelines[fn] = d
        for n in d:
            node_owner.setdefault(n, fn)
        all_nodes |= set(d.keys())
        print(f"  [OK] {fn} 解析成功，节点数 = {len(d)}")
    print(f"  合并后节点总数（去重）= {len(all_nodes)}")
    stripped_nodes = {n.lstrip("#") for n in all_nodes}

    # ------------------------------------------------------------------
    section("2) agent/ 注册清单 + 语法编译")
    action_names = set()
    reco_names = set()
    for fn in os.listdir(AGENT_DIR):
        if not fn.endswith(".py"):
            continue
        p = os.path.join(AGENT_DIR, fn)
        try:
            src = open(p, encoding="utf-8").read()
        except Exception:
            continue
        action_names.update(re.findall(r'custom_action\(\s*"([^"]+)"', src))
        reco_names.update(re.findall(r'custom_recognition\(\s*"([^"]+)"', src))
    print(f"  agent/ 注册的动作: {sorted(action_names)}")
    print(f"  agent/ 注册的识别: {sorted(reco_names)}")

    main_src = open(MAIN, encoding="utf-8").read()
    imported = set(re.findall(r'^\s*import\s+([A-Za-z_]\w*)', main_src, flags=re.M))
    print(f"  main.py import 的自定义模块: {sorted(imported)}")

    for fn in sorted(os.listdir(AGENT_DIR)):
        if not fn.endswith(".py"):
            continue
        p = os.path.join(AGENT_DIR, fn)
        try:
            py_compile.compile(p, doraise=True)
            print(f"  [OK] {fn}")
        except py_compile.PyCompileError as e:
            ok = False
            print(f"  [FAIL] {fn}: {e}")

    # ------------------------------------------------------------------
    section("3) interface.json 任务登记 + option 引用一致性")
    task_names = [t.get("name") for t in iface.get("task", [])]
    print(f"  已登记任务数 = {len(task_names)}")

    defined_options = iface.get("option", {})
    entry_missing = []
    opt_missing = []
    for t in iface.get("task", []):
        e = t.get("entry")
        if e and e.lstrip("#") not in stripped_nodes:
            entry_missing.append((t.get("name"), e))
        for o in t.get("option", []):
            if o not in defined_options:
                opt_missing.append((t.get("name"), o))
    if entry_missing:
        ok = False
        for nm, e in entry_missing:
            print(f"  [FAIL] 任务「{nm}」的 entry {e} 不在任何 pipeline 中")
    else:
        print(f"  [OK] 全部 {len(task_names)} 个任务的 entry 均存在")
    if opt_missing:
        ok = False
        for nm, o in opt_missing:
            print(f"  [FAIL] 任务「{nm}」挂载的 option「{o}」未在 interface.json 定义")
    else:
        print("  [OK] 全部任务挂载的 option 均已定义")

    hit = next((t for t in iface.get("task", []) if t.get("name") == "自动推图"), None)
    if hit:
        opts = hit.get("option", [])
        print(f"  「自动推图」挂的选项: {opts}")
        if "出战队伍" not in opts:
            print("  [NOTE] 未挂「出战队伍」选项（推图.json 注释里计划通过 pipeline_override 实现）")

    # ------------------------------------------------------------------
    section("4) 跨文件同名节点检测（硬性失败）")
    dups = {}
    for fn, d in pipelines.items():
        for n in d:
            dups.setdefault(n, []).append(fn)
    conflicts = {n: fs for n, fs in dups.items() if len(fs) > 1}
    if conflicts:
        ok = False
        print(f"  [FAIL] 跨文件同名节点 {len(conflicts)} 个（后者会静默覆盖前者，导致逻辑丢失）")
        for n, fs in conflicts.items():
            print(f"         {n} <- {fs}")
    else:
        print("  [OK] 无跨文件同名节点冲突（每节点全局唯一定义）")

    # ------------------------------------------------------------------
    section("5) 死链检测（next / on_error，剥离 [JumpBack]/[Anchor] 前缀）")
    dangling = []
    for fn, d in pipelines.items():
        for name, node in d.items():
            node = node or {}
            for key in ("next", "on_error"):
                nxt = node.get(key)
                if not isinstance(nxt, list):
                    continue
                for t in nxt:
                    if not isinstance(t, str) or not t:
                        continue
                    if strip_next_prefix(t) not in all_nodes:
                        dangling.append((fn, name, key, t))
    if dangling:
        ok = False
        for fn, n, key, t in dangling:
            print(f"  [FAIL] {fn} 节点 {n} 的 {key} 指向不存在的节点: {t}")
    else:
        print("  [OK] 全部 pipeline 所有 next/on_error 目标均存在（无死链）")

    # ------------------------------------------------------------------
    section("6) template 切图存在性")
    missing_img = []
    for fn, d in pipelines.items():
        for name, node in d.items():
            rec = (node or {}).get("recognition")
            if isinstance(rec, dict):
                for tpl in iter_templates(rec.get("param", {}).get("template")):
                    p = os.path.join(IMAGE_ROOT, tpl.replace("/", os.sep))
                    if not os.path.exists(p):
                        missing_img.append((fn, name, tpl))
    if missing_img:
        ok = False
        for fn, n, t in missing_img:
            print(f"  [FAIL] {fn} 节点 {n} 引用的切图缺失: {t}")
    else:
        print("  [OK] 全部 pipeline template 切图均存在")

    # ------------------------------------------------------------------
    section("7) custom_action / custom_recognition 注册核对")
    used_actions = set()
    used_recos = set()
    bad_shape = []      # custom_action/recognition 写在了 param 外层 → 框架静默忽略
    for fn, d in pipelines.items():
        for name, node in d.items():
            node = node or {}
            act = node.get("action")
            if isinstance(act, dict):
                # JAction{type,param} → JCustomAction 必须嵌在 param 内。
                # 写在 action 顶层时 C++ 侧 param 为空，动作**不会执行**且不报错
                # （2026-10-31 认知海域 SoCGBPickAvailable 实战踩坑：一张卡都没选）。
                if act.get("type") == "Custom" and "custom_action" in act:
                    bad_shape.append(f"{fn} 节点 {name} 的 custom_action 写在了 action 顶层（应嵌在 action.param 内）")
                ca = (act.get("param") or {}).get("custom_action")
                if ca:
                    used_actions.add(ca)
            rec = node.get("recognition")
            if isinstance(rec, dict):
                if rec.get("type") == "Custom" and "custom_recognition" in rec:
                    bad_shape.append(f"{fn} 节点 {name} 的 custom_recognition 写在了 recognition 顶层（应嵌在 recognition.param 内）")
                cr = (rec.get("param") or {}).get("custom_recognition")
                if cr:
                    used_recos.add(cr)
    if bad_shape:
        ok = False
        for b in bad_shape:
            print(f"  [FAIL] {b}")
    else:
        print("  [OK] 全部 Custom action/recognition 的命名均写在 param 内")
    miss_a = used_actions - action_names
    miss_r = used_recos - reco_names
    if miss_a or miss_r:
        ok = False
        if miss_a:
            print(f"  [FAIL] pipeline 用到但未注册的 custom_action: {sorted(miss_a)}")
        if miss_r:
            print(f"  [FAIL] pipeline 用到但未注册的 custom_recognition: {sorted(miss_r)}")
    else:
        print(f"  [OK] 全 pipeline 用到的 custom_action/recognition 均已注册"
              f"（action={sorted(used_actions)} reco={sorted(used_recos)}）")

    # ------------------------------------------------------------------
    section("8) option.pipeline_override 目标与引用校验")
    # 静态扫 next 看不到 override 动态挂载的节点（如「设置往期活动战斗次数」
    # 仅经 interface.json override 挂入往期活动链），故 override 层必须单独校验。
    ov_problems = []
    ov_count = 0
    for opt_name, opt in defined_options.items():
        for case in (opt or {}).get("cases", []):
            case_name = case.get("name", "?")
            for node, ov in (case.get("pipeline_override") or {}).items():
                ov_count += 1
                if node not in stripped_nodes:
                    ov_problems.append(f"option「{opt_name}」case「{case_name}」override 目标节点不存在: {node}")
                    continue
                if not isinstance(ov, dict):
                    continue
                for key in ("next", "on_error"):
                    refs = ov.get(key)
                    if not isinstance(refs, list):
                        continue
                    for t in refs:
                        if isinstance(t, str) and t and strip_next_prefix(t) not in all_nodes:
                            ov_problems.append(
                                f"option「{opt_name}」case「{case_name}」override {node}.{key} 死链: {t}")
    print(f"  pipeline_override 条目总数 = {ov_count}")
    if ov_problems:
        ok = False
        for p in ov_problems:
            print(f"  [FAIL] {p}")
    else:
        print("  [OK] 全部 override 目标节点与 next/on_error 引用均存在")

    # ------------------------------------------------------------------
    section("9) 扫荡链 timeout 检查（防默认 20s 掐断长等待 → 假阴性）")
    # v1.14.6 根因：扫荡链上游节点缺显式 timeout，回退默认 ~20s；「等结算」最长 60s+，
    # 结果页尚未出现任务即被掐（实测约 27s 报失败）。链首/关键节点必须显式写 timeout。
    def sweep_keyword(name: str, node: dict):
        act = node.get("action") if isinstance(node.get("action"), dict) else {}
        ca = (act.get("param") or {}).get("custom_action") or ""
        if name.startswith(("_Sweep", "_ConfirmSweep", "~ConfirmSweep")):
            return "扫荡链(_Sweep/ConfirmSweep)"
        if "战斗次数" in name or "战斗次数" in ca:
            return "设置战斗次数"
        if name == "点击出发":
            return "点击出发"
        if "快速完成" in name:
            return "快速完成"
        rec = node.get("recognition")
        if isinstance(rec, dict):
            exp = " ".join(map(str, (rec.get("param") or {}).get("expected") or []))
            if "快速完成结果" in exp:
                return "等待结算"
        if "等待" in name and "结果" in name:
            return "等待结算"
        return None

    no_timeout = []
    for fn, d in pipelines.items():
        for name, node in d.items():
            node = node or {}
            kw = sweep_keyword(name, node)
            if kw and "timeout" not in node:
                no_timeout.append((fn, name, kw))
    if no_timeout:
        ok = False
        print(f"  [FAIL] 扫荡链关键节点缺显式 timeout 共 {len(no_timeout)} 个：")
        for fn, n, kw in no_timeout:
            print(f"         {fn} :: {n}（{kw}）")
    else:
        print("  [OK] 扫荡链关键节点均已显式写 timeout")

    # ------------------------------------------------------------------
    section("10) ROI 越界检查（坐标基准 1280×720）")
    # MaaFW 对越界 roi 会静默裁剪、不报错，但属数据瑕疵；统一在校验层拦截。
    rois_out = []

    def _walk_roi(obj, path, fn, name):
        if isinstance(obj, dict):
            for k, v in obj.items():
                _walk_roi(v, f"{path}/{k}", fn, name)
        elif isinstance(obj, list):
            if (path.endswith("/roi") or path.endswith("/target")) and len(obj) == 4 \
                    and all(isinstance(x, (int, float)) for x in obj):
                x, y, w, h = obj
                if w > 0 and (x < 0 or y < 0 or x + w > SCREEN_W or y + h > SCREEN_H):
                    rois_out.append((fn, name, path, obj))
                elif w == 0 and (x != 0 or y != 0):
                    rois_out.append((fn, name, path, obj))  # [0,0,0,0]=全屏，其余 w=0 无意义
            else:
                for i, v in enumerate(obj):
                    _walk_roi(v, f"{path}/{i}", fn, name)

    for fn, d in pipelines.items():
        for name, node in d.items():
            node = node or {}
            _walk_roi(node.get("recognition"), "recognition", fn, name)
            _walk_roi(node.get("action"), "action", fn, name)
            if isinstance(node.get("roi"), list):
                _walk_roi({"roi": node["roi"]}, "node", fn, name)
    if rois_out:
        ok = False
        print(f"  [FAIL] ROI 越界 {len(rois_out)} 处：")
        for fn, n, path, roi in rois_out:
            print(f"         {fn} :: {n} {path} = {roi}")
    else:
        print("  [OK] 全部 roi/target 均在 1280×720 画面内")

    # ------------------------------------------------------------------
    section("11) 「点击确定」防卡死兜底检查")
    jd = pipelines.get("Shared.json", {}).get("点击确定")
    if jd:
        exp = (jd.get("recognition") or {}).get("param", {}).get("expected", [])
        print(f"  [INFO] 点击确定 expected = {exp}")
        if "确认退出" in exp:
            print("  [OK] 点击确定已含「确认退出」兜底（防结果屏按钮文案不同导致卡死）")
        else:
            ok = False
            print("  [FAIL] 点击确定 缺少「确认退出」兜底，若按钮文案为「确认退出」会永久卡死")
    else:
        print("  [NOTE] Shared.json 未找到「点击确定」节点（当期/往期活动流程可能已改名）")

    # ------------------------------------------------------------------
    section("12) 真风险节点 timeout 检查（非终端 + 无 timeout + next 无即时命中）")
    # 判据来自 scripts/pj.py::is_timeout_risk，与 fill_timeouts.py / check_graph.py 共用。
    # A 类（next 含 DirectHit 候选）扫描即刻返回，不写 timeout 也不构成风险 → 放行。
    node_index = {}
    for d in pipelines.values():
        for n, nd in d.items():
            node_index[n] = nd if isinstance(nd, dict) else {}

    risky_by_file = {}
    safe_count = 0
    for fn, d in pipelines.items():
        for name, node in d.items():
            node = node or {}
            nxt = node.get("next")
            if not isinstance(nxt, list) or not nxt or "timeout" in node:
                continue
            if pj.is_timeout_risk(node, node_index):
                risky_by_file.setdefault(fn, []).append(name)
            else:
                safe_count += 1
    total_risky = sum(len(v) for v in risky_by_file.values())
    print(f"  [INFO] A 类放行（next 含即时命中候选，无需 timeout）= {safe_count}")
    if total_risky:
        ok = False
        print(f"  [FAIL] B 类真风险节点缺 timeout 共 {total_risky} 个（按文件聚合）：")
        for fn in sorted(risky_by_file, key=lambda k: (-len(risky_by_file[k]), k)):
            names = risky_by_file[fn]
            head = "、".join(names[:5]) + ("…" if len(names) > 5 else "")
            print(f"         {fn:<28} {len(names):>3} 个  {head}")
        print("         修复：python scripts/fill_timeouts.py --file <文件> --apply")
    else:
        print("  [OK] 无真风险节点（非终端节点均已显式写 timeout 或含即时命中候选）")

    # ------------------------------------------------------------------
    section("13) on_error 自环检查（指向自身会导致无限重试）")
    oe_self = []
    for fn, d in pipelines.items():
        for name, node in d.items():
            for key, ref in pj.node_refs(node or {}):
                if key == "on_error" and pj.strip_ref_prefix(ref) == name:
                    oe_self.append((fn, name))
    if oe_self:
        ok = False
        print(f"  [FAIL] on_error 指向自身 {len(oe_self)} 处：")
        for fn, n in oe_self:
            print(f"         {fn} :: {n}")
    else:
        print("  [OK] 无 on_error 自环")

    # ------------------------------------------------------------------
    section("14) 生成层一致性（存在 pipeline_src/ 时必须与产物一致）")
    src_dir = os.path.join(ROOT, "resource", "base", "pipeline_src")
    gen_py = os.path.join(ROOT, "scripts", "pipeline_gen.py")
    if not os.path.isdir(src_dir):
        print("  [NOTE] 未启用生成层（无 resource/base/pipeline_src/），跳过")
    elif not os.path.exists(gen_py):
        ok = False
        print(f"  [FAIL] 存在 pipeline_src/ 但缺少生成器 {gen_py}")
    else:
        r = subprocess.run(
            [sys.executable, gen_py, "--check"],
            capture_output=True, text=True, cwd=ROOT,
        )
        if r.returncode == 0:
            print("  [OK] 生成物与 pipeline_src/ 一致")
        else:
            ok = False
            print(f"  [FAIL] 生成物与源不一致（退出码 {r.returncode}）：")
            print("         " + (r.stdout or r.stderr).strip().replace("\n", "\n         "))

    # ------------------------------------------------------------------
    section("15) 资源包清单一致性（pipeline/.manifest.json）")
    manifest = os.path.join(PIPELINE_DIR, ".manifest.json")
    if not os.path.exists(manifest):
        print("  [NOTE] 未生成 .manifest.json（开发期正常；发版构建后应存在）")
    else:
        try:
            mf = json.load(open(manifest, encoding="utf-8"))
            files_mf = mf.get("files") or mf
            bad = []
            for rel, want in files_mf.items():
                p = os.path.join(PIPELINE_DIR, *rel.split("/"))
                if not os.path.exists(p):
                    bad.append((rel, "缺失"))
                    continue
                got = hashlib.sha256(open(p, "rb").read()).hexdigest()
                if got != want:
                    bad.append((rel, "哈希不符"))
            if bad:
                ok = False
                print(f"  [FAIL] 清单不符 {len(bad)} 处：")
                for rel, why in bad[:10]:
                    print(f"         {rel}（{why}）")
            else:
                print(f"  [OK] {len(files_mf)} 个文件与清单一致")
        except Exception as e:  # noqa: BLE001
            ok = False
            print(f"  [FAIL] 清单解析失败: {e}")

    # ------------------------------------------------------------------
    section("16) agent 注册扫描覆盖（子目录内 .py 是否被扫到）")
    sub_py = []
    for root_, dirs, files_ in os.walk(AGENT_DIR):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        if os.path.abspath(root_) == os.path.abspath(AGENT_DIR):
            continue
        sub_py += [os.path.join(root_, f) for f in files_ if f.endswith(".py")]
    if sub_py:
        print(f"  [WARN] agent/ 下发现子目录内 .py 共 {len(sub_py)} 个，但第 2/7 段只扫 agent/*.py：")
        for p in sub_py[:5]:
            print(f"         {os.path.relpath(p, ROOT)}")
        print("         迁移到 agent/maaeov/ 前必须先改为递归扫描，否则注册核对会假绿（P1-7）。")
    else:
        print("  [OK] agent/ 无子目录 .py，当前平铺扫描覆盖完整")

    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    print("汇总")
    print("=" * 60)
    print("RESULT:", "ALL_OK" if ok else "HAS_ISSUES")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
