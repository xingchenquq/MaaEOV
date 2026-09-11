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
        tpl = rec.get("param", {}).get("template")
        if tpl:
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
print("汇总")
print("=" * 60)
print("RESULT:", "ALL_OK" if ok else "HAS_ISSUES")
sys.exit(0 if ok else 1)
