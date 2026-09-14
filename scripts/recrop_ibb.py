# 从 战斗节点开始.png 按用户实测 ROI 重裁局内 Buff 相关模板
from PIL import Image
import os

SRC = r'C:\Users\Lee\Documents\Python\autodori\assets\resource\image\战斗节点开始.png'
DST = r'C:\Users\Lee\Documents\Python\MaaEOV\resource\base\image\SeaOfCognition'

im = Image.open(SRC)
print('src size', im.size)

crops = {
    # 标题「请选择一个短暂灵感」
    '局内buff选择.png': (517, 130, 517 + 249, 130 + 35),
    # 激发按钮
    'QiFa.png': (562, 529, 562 + 151, 529 + 38),
    # 左卡（后续优先级用）
    '局内buff左卡.png': (352, 205, 352 + 239, 205 + 278),
    # 右卡（后续优先级用）
    '局内buff右卡.png': (682, 206, 682 + 236, 206 + 275),
}

for name, box in crops.items():
    c = im.crop(box)
    out = os.path.join(DST, name)
    c.save(out)
    print('saved', name, c.size, '->', out)
