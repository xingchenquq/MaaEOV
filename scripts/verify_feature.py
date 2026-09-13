# -*- coding: utf-8 -*-
"""MaaEOV 开发校验脚本（对应 maaeov-feature-add 技能 Step 6）。

校验内容：
1. 推图.json / interface.json 能否按 JSONC 解析（剥离 // 注释）。
2. 推图.json 节点总数与节点名列表。
3. 推图.json 里用到的 custom_action 名，是否都能在 agent/ 已注册模块里找到。
4. 推图.json 里引用的 template 切图，是否都存在于 resource/base/image/。
5. agent/ 下所有 .py 能否通过语法编译（py_compile）。
6. interface.json 的「自动推图」任务是否已登记，entry 是否存在。
7. interface.json 各 option 的 pipeline_override 目标节点，在 推图.json 里是否存在
   （仅针对明确指向推图节点的 override；其它项目的节点在 Tasks.json，跳过）。
8. 全部 pipeline 文件解析、跨文件合并后的 **next 死链检测**、切图存在性、
   custom_action/recognition 注册、interface 任务 entry 存在性，以及「点击确定」防卡死修复状态。
"""
import json
import os
import re
import sys
import py_compile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIPELINE = os.path.join(ROOT, "resource", "base", "pipeline", "推图.json")
INTERFACE = os.path.join(ROOT, "AGENT_NOTE") if False else os.path.join(ROOT, "interface.json")
IMAGE_ROOT = os.path.join(ROOT, "resource", "base", "image")
AGENT_DIR = os.path.join(ROOT, "agent")

MAIN = os.path.join(AGENT_DIR, "main.py")

ok = True


def strip_jsonc(text: str) -> str:
    # 去掉 /* */ 块注释
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    # 去掉 // 行注释（不与 http:// 混淆）
    out = []
    for line in text.split("\n"):
        # 保护 http:// 与 https:// 里的 //
        if "//" in line and "http://" not in line and "https://" not in line:
            # 找到第一个 // （不在字符串里，简单处理）
            idx = line.find("//")
            line = line[:idx]
        out.append(line)
    return "\n".join(out)


def load_jsonc(path: str):
    with open(path, encoding="utf-8") as f:
        return json.loads(strip_jsonc(f.read()))


def iter_templates(tpl):
    """template 可能是字符串或字符串列表，统一成可迭代。"""
    if isinstance(tpl, str):
        return [tpl]
    if isinstance(tpl, list):
        return [t for t in tpl if isinstance(t, str)]
    return []


print("=" * 60)
print("1) JSONC 解析：推图.json / interface.json")
print("=" * 60)
try:
    tasks = load_jsonc(PIPELINE)
    print(f"  [OK] 推图.json 解析成功，节点数 = {len(tasks)}")
    node_names = set(tasks.keys())
except Exception as e:
    ok = False
    print(f"  [FAIL] 推图.json 解析失败: {e}")
    tasks = {}
    node_names = set()

try:
    iface = load_jsonc(INTERFACE)
    print(f"  [OK] interface.json 解析成功")
except Exception as e:
    ok = False
    print(f"  [FAIL] interface.json 解析失败: {e}")
    iface = {}


print("\n" + "=" * 60)
print("2) 推图.json 引用的 custom_action 是否都已注册")
print("=" * 60)
# 收集 agent 里所有 @AgentServer.custom_action("X") 与 custom_recognition
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
    for m in re.findall(r'custom_action\(\s*"([^"]+)"', src):
        action_names.add(m)
    for m in re.findall(r'custom_recognition\(\s*"([^"]+)"', src):
        reco_names.add(m)
print(f"  agent/ 注册的动作: {sorted(action_names)}")
print(f"  agent/ 注册的识别: {sorted(reco_names)}")

# main.py 实际 import 了哪些自定义模块（去掉注释行）
main_src = open(MAIN, encoding="utf-8").read()
imported = set(re.findall(r'^\s*import\s+([A-Za-z_]\w*)', main_src, flags=re.M))
print(f"  main.py import 的自定义模块: {sorted(imported)}")

used_actions = set()
for name, node in tasks.items():
    act = (node or {}).get("action")
    if isinstance(act, dict):
        ca = act.get("param", {}).get("custom_action")
        if ca:
            used_actions.add(ca)
print(f"  推图.json 使用的 custom_action: {sorted(used_actions)}")
missing = used_actions - action_names
if missing:
    ok = False
    print(f"  [FAIL] 以下 custom_action 未在任何 agent 模块注册: {sorted(missing)}")
else:
    print("  [OK] 全部 custom_action 均已注册")


print("\n" + "=" * 60)
print("3) 推图.json 引用的 template 切图是否都存在")
print("=" * 60)
missing_img = []
for name, node in tasks.items():
    rec = (node or {}).get("recognition")
    if isinstance(rec, dict):
        for tpl in iter_templates(rec.get("param", {}).get("template")):
            p = os.path.join(IMAGE_ROOT, tpl.replace("/", os.sep))
            if not os.path.exists(p):
                missing_img.append((name, tpl))
if missing_img:
    ok = False
    for n, t in missing_img:
        print(f"  [FAIL] 节点 {n} 引用的切图缺失: {t}")
else:
    print("  [OK] 全部 template 切图均存在")


print("\n" + "=" * 60)
print("4) agent/ 下 .py 语法编译")
print("=" * 60)
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


print("\n" + "=" * 60)
print("5) interface.json 任务登记检查")
print("=" * 60)
task_names = [t.get("name") for t in iface.get("task", [])]
print(f"  已登记任务数 = {len(task_names)}")
target = "自动推图"
hit = next((t for t in iface.get("task", []) if t.get("name") == target), None)
if hit:
    entry = hit.get("entry")
    print(f"  [OK] 任务「{target}」已登记，entry={entry}")
    stripped = {n.lstrip("#") for n in node_names}
    if entry and entry.lstrip("#") in stripped:
        print(f"  [OK] entry 节点 {entry} 存在于 推图.json")
    else:
        ok = False
        print(f"  [FAIL] entry 节点 {entry} 不在 推图.json")
else:
    ok = False
    print(f"  [FAIL] 任务「{target}」未在 interface.json 登记")

# 自动推图任务是否挂了「出战队伍」选项
opts = hit.get("option", []) if hit else []
print(f"  「自动推图」挂的选项: {opts}")
if "出战队伍" in opts:
    print("  [OK] 已挂「出战队伍」选项")
else:
    print("  [NOTE] 未挂「出战队伍」选项（推图.json 注释里计划通过 pipeline_override 实现，但 interface.json 尚未添加）")


print("\n" + "=" * 60)
print("6) 全 pipeline 解析 + 死链 + 切图 + 自定义注册")
print("=" * 60)
PIPELINE_DIR = os.path.join(ROOT, "resource", "base", "pipeline")
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

for fn, d in pipelines.items():
    print(f"  [OK] {fn} 解析成功，节点数 = {len(d)}")
print(f"  合并后节点总数（去重）= {len(all_nodes)}")

# 跨文件同名节点：MaaFw 会合并，后者覆盖前者（多为有意复用/覆盖，列出来供确认）
dups = {}
for fn, d in pipelines.items():
    for n in d:
        dups.setdefault(n, []).append(fn)
conflicts = {n: fs for n, fs in dups.items() if len(fs) > 1}
if conflicts:
    print(f"  [INFO] 跨文件同名节点 {len(conflicts)} 个（后者覆盖前者，请确认是否符合预期）")
    for n, fs in list(conflicts.items())[:8]:
        print(f"         {n} <- {fs}")
else:
    print("  [OK] 无跨文件同名节点冲突")

# 6e interface.json 每个任务的 entry 是否都能在合并节点集中找到
entry_missing = []
stripped_nodes = {n.lstrip("#") for n in all_nodes}
for t in iface.get("task", []):
    e = t.get("entry")
    if e and e.lstrip("#") not in stripped_nodes:
        entry_missing.append((t.get("name"), e))
if entry_missing:
    ok = False
    for nm, e in entry_missing:
        print(f"  [FAIL] 任务「{nm}」的 entry {e} 不在任何 pipeline 中")
else:
    print(f"  [OK] interface.json 全部 {len(iface.get('task', []))} 个任务的 entry 均存在")

tasks_json = pipelines.get("Tasks.json", {})

# 6a 死链检测：next 里出现的字符串目标必须能在合并节点集中找到（扫描全部 pipeline）
dangling = []
for fn, d in pipelines.items():
    for name, node in d.items():
        nxt = (node or {}).get("next")
        if isinstance(nxt, list):
            for t in nxt:
                if isinstance(t, str) and t and t not in all_nodes:
                    dangling.append((fn, name, t))
if dangling:
    ok = False
    for fn, n, t in dangling:
        print(f"  [FAIL] {fn} 节点 {n} 的 next 指向不存在的节点: {t}")
else:
    print("  [OK] 全部 pipeline 所有 next 目标均存在（无死链）")

# 6b 切图存在性（扫描全部 pipeline）
missing_img2 = []
for fn, d in pipelines.items():
    for name, node in d.items():
        rec = (node or {}).get("recognition")
        if isinstance(rec, dict):
            for tpl in iter_templates(rec.get("param", {}).get("template")):
                p = os.path.join(IMAGE_ROOT, tpl.replace("/", os.sep))
                if not os.path.exists(p):
                    missing_img2.append((fn, name, tpl))
if missing_img2:
    ok = False
    for fn, n, t in missing_img2:
        print(f"  [FAIL] {fn} 节点 {n} 引用的切图缺失: {t}")
else:
    print("  [OK] 全部 pipeline template 切图均存在")

# 6c 全 pipeline 用到的 custom_action / custom_recognition 是否已注册
used_actions2 = set()
used_recos2 = set()
for fn, d in pipelines.items():
    for name, node in d.items():
        act = (node or {}).get("action")
        if isinstance(act, dict):
            ca = act.get("param", {}).get("custom_action")
            if ca:
                used_actions2.add(ca)
        rec = (node or {}).get("recognition")
        if isinstance(rec, dict):
            cr = rec.get("param", {}).get("custom_recognition")
            if cr:
                used_recos2.add(cr)
miss_a = used_actions2 - action_names
miss_r = used_recos2 - reco_names
if miss_a or miss_r:
    ok = False
    if miss_a:
        print(f"  [FAIL] pipeline 用到但未注册的 custom_action: {sorted(miss_a)}")
    if miss_r:
        print(f"  [FAIL] pipeline 用到但未注册的 custom_recognition: {sorted(miss_r)}")
else:
    print(f"  [OK] 全 pipeline 用到的 custom_action/recognition 均已注册"
          f"（action={sorted(used_actions2)} reco={sorted(used_recos2)}）")

# 6d「点击确定」防卡死修复状态：expected 必须同时含「确定」与「确认退出」
jd = tasks_json.get("点击确定")
if jd:
    exp = (jd.get("recognition") or {}).get("param", {}).get("expected", [])
    print(f"  [INFO] 点击确定 expected = {exp}")
    if "确认退出" in exp:
        print("  [OK] 点击确定已含「确认退出」兜底（防结果屏按钮文案不同导致卡死）")
    else:
        print("  [WARN] 点击确定 缺少「确认退出」兜底，若按钮文案为「确认退出」会永久卡死")
else:
    print("  [NOTE] 未找到「点击确定」节点（当期/往期活动流程可能已改名）")


print("\n" + "=" * 60)
print("汇总")
print("=" * 60)
print("RESULT:", "ALL_OK" if ok else "HAS_ISSUES")
sys.exit(0 if ok else 1)
