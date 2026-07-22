#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_youzhou_img6.py
======================
更精确的检查: 看右上角/右下角的深绿小块是不是文字标签 (例如"幽州"两字)
如果是, 那只保留主体大陆形状, 而剔除文字.
"""

import os, json
import numpy as np
from PIL import Image
import cv2

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '幽州.png')
OUT = os.path.join(HERE, 'youzhou_diag6')
os.makedirs(OUT, exist_ok=True)

rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = rgb.shape[:2]

r = rgb[:, :, 0].astype(int)
g = rgb[:, :, 1].astype(int)
b = rgb[:, :, 2].astype(int)
mask = ((g > r + 45) & (g > b + 40) & (g < 195) & (r < 140) & (b < 140) & (g > 100)).astype(np.uint8) * 255
k = np.ones((4, 4), np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=3)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=2)

ys, xs = np.where(mask > 0)

# 检查几块特殊区域:
# 1) 顶部窄段 y[229-350]: 看是不是幽州北上辽东外延部分
# 2) 右下角 y[1050-1087] x[1690-1965] (绿色): 是图例字体?
# 3) 主体 (y[400-950], x[100-1700])
regions = [
    ('top (y229-350)','mask', xs[ys < 350], ys[ys < 350]),
    ('main upper (y350-700)', '', xs[(ys>=350)&(ys<700)], ys[(ys>=350)&(ys<700)]),
    ('main lower (y700-1000)', '', xs[(ys>=700)&(ys<1000)], ys[(ys>=700)&(ys<1000)]),
    ('bottom (y1000-1090)', '', xs[ys>=1000], ys[ys>=1000]),
    ('bottom-right corner (x>1650, y>=950)', '', xs[(xs>1650)&(ys>=950)], ys[(xs>1650)&(ys>=950)]),
    ('top-right corner (x>1400, y<400)', '', xs[(xs>1400)&(ys<400)], ys[(xs>1400)&(ys<400)]),
]
for label, _, xr, yr in regions:
    if len(xr):
        print(f'{label}: {len(xr):,} px  bbox x[{xr.min()},{xr.max()}] y[{yr.min()},{yr.max()}]')
        # 形心
        print(f'  center=({xr.mean():.1f},{yr.mean():.1f})  aspect ratio (w/h)={(xr.max()-xr.min()+1)/(yr.max()-yr.min()+1):.2f}')
        avg = rgb[yr, xr].mean(axis=0).astype(int)
        print(f'  avg RGB = {tuple(avg.tolist())}')

# 把掩膜单独存成可视化
Image.fromarray(mask * 255 // 255 * 255).save(os.path.join(OUT, 'mask_white_on_black.png'))
# 在原图上画掩膜半透明叠加
overlay = rgb.copy()
overlay[mask > 0] = [255, 100, 255]   # 紫色 fill
alpha = 0.4
out_img = (rgb * (1 - alpha) + overlay * alpha).astype(np.uint8)
Image.fromarray(out_img).save(os.path.join(OUT, 'mask_overlay.png'))

# 把"非主体"的小块(认为面积<总面积5%) 列出来, 看它们是不是文字
nb, lab, st, _ = cv2.connectedComponentsWithStats(mask, 8)
print(f'\nAll components ({nb-1}):')
for i in range(1, nb):
    a = st[i, cv2.CC_STAT_AREA]
    if a < 30:
        continue
    x0 = st[i, cv2.CC_STAT_LEFT]; y0 = st[i, cv2.CC_STAT_TOP]
    w = st[i, cv2.CC_STAT_WIDTH]; h = st[i, cv2.CC_STAT_HEIGHT]
    print(f'  #{i} area={a:,}  bbox x[{x0},{x0+w}] y[{y0},{y0+h}] aspect={w/h:.2f}')
print('OK')
