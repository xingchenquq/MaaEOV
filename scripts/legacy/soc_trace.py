"""认知海域「卡在哪一步」诊断器。

从 debug/maafw.log 抽最后一次「认知海域」任务的节点执行序列，翻译成可读步骤，
并报告最后到达的节点（= 卡点）。作为 GUI 日志之外的可靠兜底。

用法：
    python scripts/soc_trace.py                # 默认读 debug/maafw.log
    python scripts/soc_trace.py <日志路径>
"""
import os
import re
import sys

R = r'C:\Users\Lee\Documents\Python\MaaEOV'
LOG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(R, 'debug', 'maafw.log')

STEP = {
    '#SeaOfCognition':          '任务开始',
    'SoCResume':                '检测当前流程位置（入口路由）',
    'SoCState_GB1':             '检测到全局 Buff（名额剩余）',
    'SoCState_GB0':             '检测到全局 Buff（已选满）',
    'SoCFallbackStart':         '未识别中途状态 → 从 BCR 开始',
    'SoCAtBCR':                 '点「认知海域」图标（选层界面）',
    'SoCSelectLayer':           '选层：梦渊层',
    'SoCStartDive':             '点「开始下潜」',
    'SoCContinueDive':           '点「继续下潜」（已有进行中）',
    'SoCDeepDive':              '下潜方式 → 深潜指引',
    'SoCDeepDiveFree':          '下潜方式 → 自由探索（兜底）',
    'SoCTeamEnter':             '配队界面 → 进入海域',
    'SoCInspirationNode':       '检测到全局 Buff 入口屏（灵感节点）',
    'SoCGBLoop':                '全局 Buff 选择中',
    'SoCGBAllDone':             '全局 Buff → 检测是否已选满（剩余可选灵感 0）',
    'SoCGBSwipe':               '全局 Buff → 左滑',
    'SoCGB1':                   '全局 Buff → 能量涌流',
    'SoCGB2':                   '全局 Buff → 战前准备',
    'SoCGB3':                   '全局 Buff → 环境遮蔽',
    'SoCGB4':                   '全局 Buff → 应急护盾',
    'SoCGB5':                   '全局 Buff → 身心调和',
    'SoCGBDone':                '全局 Buff 结束',
    'SoCGBContinue':            '全局 Buff → 点「继续」出发',
    'SoCNodeLoop':              '循环 → 找下一战斗节点',
    'SoCInBattleBuff':          '局内 Buff → 点左卡',
    'SoCInBattleBuffOCR':       '局内 Buff → OCR 兜底点左卡',
    'SoCInBattleBuff2nd':       '局内 Buff → 点左卡 第2下',
    'SoCInBattleBuffConfirm':   '局内 Buff → 点「激发」',
    'SoCStartBattle':           '开始战斗',
    'SoCAutoBattle':            '自动战斗中（轮询等结算+关奖励）',
    'SoCContinue':              '结算 → 点「继续」',
    'SoCAfterContinue':          '继续后：检测战斗节点 or 全局 Buff',
    'SoCClaim':                 '领奖',
    '_SoCNoTicket':             '入场券不足 → 结束',
    'SoCDone':                  '任务结束',
    # 公共导航节点（认知海域会借道）
    '_NavigateBCR':             '（公共）导航到 BCR',
    '_BCRFromHome':             '（公共）从主页进 BCR',
    '_NavigateHomepage':        '（公共）回主界面',
    '_ServerMaintenance':       '（公共）处理服务器维护弹窗',
    '_ConfrimReconnect':        '（公共）处理重连弹窗',
    '_ConfirmMiddle':           '（公共）处理中间确认弹窗',
    '_LevelUp':                 '（公共）处理升级弹窗',
    '_SeaOfCognitionReward':    '（公共）关战斗奖励弹窗',
    '_CloseWindows':            '（公共）关窗口',
    '~BCR':                     '（公共）已在 BCR',
}

try:
    lines = open(LOG, encoding='utf-8', errors='replace').read().splitlines()
except FileNotFoundError:
    print('找不到日志：', LOG)
    sys.exit(1)

# 最后一次「认知海域」任务起点
start = None
for i, l in enumerate(lines):
    if 'task start:' in l and '#SeaOfCognition' in l:
        start = i
if start is None:
    print('日志中找不到认知海域任务记录（是否跑过？）')
    sys.exit(0)

seq = []
for l in lines[start:]:
    if 'Node.PipelineNode.Starting' in l:
        m = re.search(r'"name":"([^"]+)"', l)
        if m:
            ts = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', l)
            ts = ts.group(1) if ts else ''
            name = m.group(1)
            # 同一节点事件会被多路 sink 重复记录 → 连续同名去重
            if seq and seq[-1][1] == name:
                continue
            seq.append((ts, name))

if not seq:
    print('认知海域任务已启动，但没有任何节点开始执行（异常）。')
    sys.exit(0)

print('===== 认知海域 · 本次节点序列（共 %d 步） =====' % len(seq))
for ts, name in seq[-40:]:
    label = STEP.get(name)
    print('  %s  %-24s %s' % (ts[11:] if ts else '        ', name, ('← ' + label) if label else ''))

last = seq[-1][1]
print()
print('★ 最后到达节点：%s  →  %s' % (last, STEP.get(last, '（未登记的公共/自定义节点）')))
print('  若上面最后一步之后长时间没有新节点 / 任务未正常收尾，即为卡点。')
