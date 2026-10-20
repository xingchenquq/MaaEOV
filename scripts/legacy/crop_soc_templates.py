# -*- coding: utf-8 -*-
"""从原始截图切出模板图，并把切图框画回原图供目视核对。"""
import os
from PIL import Image, ImageDraw

RAW = r'C:\Users\Lee\Documents\Python\MaaEOV\resource\base\image\SeaOfCognition\raw'
DST = r'C:\Users\Lee\Documents\Python\MaaEOV\resource\base\image\SeaOfCognition'
CHK = r'C:\Users\Lee\Documents\Python\MaaEOV\debug'

# (源图, 输出模板名, (x,y,w,h))
JOBS = [
    ('03_deepdive.png',          'DiveUnavailable.png', (733, 239, 213, 65)),
    ('03_deepdive.png',          'DiveFree.png',        (300, 190, 245, 200)),
    ('02_layer_select_二次确认.png', 'StartDive.png',     (1080, 610, 185, 66)),
    ('战斗内buff选取.png',          'QiFa.png',           (476, 440, 120, 46)),
]

# 画框核验（源图 -> 框列表）
CHECK = {}
for src, name, box in JOBS:
    img = Image.open(os.path.join(RAW, src)).convert('RGB')
    x, y, w, h = box
    img.crop((x, y, x + w, y + h)).save(os.path.join(DST, name))
    CHECK.setdefault(src, []).append((name, box))
    print('  crop %-22s %s' % (name, box))

for src, boxes in CHECK.items():
    img = Image.open(os.path.join(RAW, src)).convert('RGB')
    d = ImageDraw.Draw(img)
    for name, (x, y, w, h) in boxes:
        d.rectangle([x, y, x + w, y + h], outline=(255, 0, 0), width=3)
    out = os.path.join(CHK, '_cropchk_' + src)
    img.save(out)
    print('  check ->', out)
