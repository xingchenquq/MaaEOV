# -*- coding: utf-8 -*-
"""把 5 张全局 Buff 模板从「整张卡」重裁为「卡片底部『未激发』区域」。

目的：选中 Buff 后「未激发」→「已激发」且卡片变亮，原整卡模板大部分像素不变
→ 仍匹配 → 死循环。只保留底部「未激发」区域，选中后该区域文字变化 + 卡片变亮
→ 模板匹配分骤降 → 不再匹配 → 自然停止、不重复点。

输入：SeaOfCognition/能量涌流.png 等（整卡 218x261）
输出：同名覆盖，仅保留底部 ~95px（含描述末段 + 未激发 + 底边）
"""
import os
from PIL import Image

DST = r'C:\Users\Lee\Documents\Python\MaaEOV\resource\base\image\SeaOfCognition'
BUFFS = ['能量涌流', '战前准备', '环境遮蔽', '应急护盾', '身心调和']
KEEP_H = 95  # 保留底部高度

for name in BUFFS:
    p = os.path.join(DST, name + '.png')
    im = Image.open(p).convert('RGB')
    w, h = im.size
    top = max(0, h - KEEP_H)
    crop = im.crop((0, top, w, h))
    crop.save(p)
    print('  %-10s %s -> bottom %dpx (%s)' % (name, (w, h), KEEP_H, crop.size))

print('\nDone — 5 张模板已重裁为底部「未激发」区域（同名覆盖）')
