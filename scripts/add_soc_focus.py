"""给认知海域 pipeline 的每个节点加 `focus` 步骤标记。

MaaFramework 节点支持 `focus` 字段；MFAAvalonia 在 `Node.PipelineNode.Starting`
事件时，把 focus 内容以 display=log 形式写入 GUI 日志面板（见 FocusHandler.cs）。
这样跑认知海域时日志会按步骤打印，卡在哪一步一目了然，且不新增节点、不弹窗。
"""
import os

P = r'C:\Users\Lee\Documents\Python\MaaEOV\resource\base\pipeline\认知海域.json'
s = open(P, encoding='utf-8').read()

MARKERS = [
    ("#SeaOfCognition",        "认知海域 · 任务开始"),
    ("SoCAtBCR",               "步骤 1／点「认知海域」图标（选层界面）"),
    ("SoCSelectLayer",         "步骤 2／选层：梦渊层"),
    ("SoCDeepDive",            "步骤 3／选「深潜指引」"),
    ("SoCTeamEnter",           "步骤 4／配队界面 → 进入海域"),
    ("SoCInspirationNode",     "步骤 5／节点界面 → 点「灵感节点」"),
    ("SoCGBLoop",              "步骤 6／全局 Buff 选择中…"),
    ("SoCGB1",                 "步骤 6a／全局 Buff → 能量涌流"),
    ("SoCGB2",                 "步骤 6b／全局 Buff → 战前准备"),
    ("SoCGB3",                 "步骤 6c／全局 Buff → 环境遮蔽"),
    ("SoCGB4",                 "步骤 6d／全局 Buff → 应急护盾"),
    ("SoCGB5",                 "步骤 6e／全局 Buff → 身心调和"),
    ("SoCGBDone",              "步骤 6／全局 Buff 结束 → 进入战斗"),
    ("SoCNodeLoop",            "步骤 7／循环 → 找下一个战斗节点"),
    ("SoCInBattleBuff",        "步骤 8a／局内 Buff → 点左卡 [472,344]"),
    ("SoCInBattleBuff2nd",     "步骤 8b／局内 Buff → 点左卡 第2下 [472,344]"),
    ("SoCInBattleBuffConfirm", "步骤 8c／局内 Buff → 点「激发」"),
    ("SoCStartBattle",         "步骤 8／开始战斗"),
    ("SoCAutoBattle",          "步骤 9／自动战斗中（等右下「继续」出现）"),
    ("SoCContinue",            "步骤 10／结算 → 点「继续」"),
    ("SoCClaim",               "步骤 11／领奖"),
    ("_SoCNoTicket",           "入场券不足 → 结束任务"),
    ("SoCDone",                "认知海域 · 任务结束"),
]

for name, text in MARKERS:
    anchor = '    "%s": {\n' % name
    if anchor not in s:
        print('  [SKIP] anchor not found:', name)
        continue
    focus_block = ('    "%s": {\n'
                   '        "focus": {\n'
                   '            "Node.PipelineNode.Starting": "%s"\n'
                   '        },\n' % (name, text))
    if focus_block in s:
        print('  [SKIP] already has focus:', name)
        continue
    s = s.replace(anchor, focus_block, 1)
    print('  [OK] +focus', name)

open(P, 'w', encoding='utf-8').write(s)
print('written.')
