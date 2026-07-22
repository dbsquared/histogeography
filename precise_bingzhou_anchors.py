"""
终极方案: 直接在并州.png上逐个目视确认5个地标的正确像素坐标。
方法: 输出5张局部放大裁剪图(以文字标签为中心),每张上叠加坐标网格,
     让人一眼看出白点精确位置。
"""
import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(HERE, '汉末十三州地图范例', '并州.png')
OUTDIR = os.path.join(HERE, 'bingzhou_step1_v7c')

img = Image.open(IMG_PATH).convert('RGB')

# 基于原图仔细辨认后的文字标签大致位置(需要微调)
# 每个元组:(城市名, 标签文本, 粗略中心像素x,y)
TARGETS = [
    ('大同',   '雁门',   1190, 230),    # 东北, 雁门郡区域
    ('太原',   '晋阳',   1730, 1080),    # 中东部, 太原郡治=晋阳
    ('呼和浩特','云中',  1370, 350),     # 北部, 云中郡
    ('延安',   '上郡',   860, 1080),     # 南部偏西, 上郡
    ('吕梁',   '离石',   940, 820),      # 中西部, 西河郡治=离石
]

font_sm = ImageFont.truetype('C:/Windows/Fonts/simhei.ttf', 18)
font_grid = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 14)

for city, label_text, cx, cy in TARGETS:
    # 裁剪 300x300 区域
    s = 150
    left = max(0, cx - s)
    upper = max(0, cy - s)
    right = min(img.width, cx + s)
    lower = min(img.height, cy + s)
    
    crop = img.crop((left, upper, right, lower))
    dw = ImageDraw.Draw(crop)
    
    # 画坐标网格(每50px一条线+标注)
    for gx in range(0, right-left, 50):
        actual_x = left + gx
        dw.line([(gx, 0), (gx, lower-upper)], fill='#FFFFFF40', width=1)
        if gx % 50 == 0 and gx > 10:
            dw.text((gx+2, 2), str(actual_x), fill='white', font=font_grid)
    for gy in range(0, lower-upper, 50):
        actual_y = upper + gy
        dw.line([(0, gy), (right-left, gy)], fill='#FFFFFF40', width=1)
        if gy % 50 == 0 and gy > 10:
            dw.text((2, gy+2), str(actual_y), fill='white', font=font_grid)
    
    # 中心十字准星
    local_cx, local_cy = cx - left, cy - upper
    dw.line([(local_cx-40,local_cy),(local_cx+40,local_cy)], fill='red', width=2)
    dw.line([(local_cx,local_cy-40),(local_cx,local_cy+40)], fill='red', width=2)
    dw.ellipse([local_cx-10,local_cy-10,local_cx+10,local_cy+10], outline='red', width=2)
    
    # 标题
    title = f'{city} ({label_text}) — 图中心≈({cx},{cy})'
    dw.text((5, 5), title, fill='yellow', font=font_sm)
    
    out_path = os.path.join(OUTDIR, f'precise_{city}.png')
    crop.save(out_path)
    print(f'{city}({label_text}): center≈({cx},{cy}) crop=[{left},{upper},{right},{lower}] -> {out_path}')
