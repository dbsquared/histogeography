#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_youzhou_img4.py
======================
更精细分析最大的深绿连通域, 确认它就是幽州.
并且把红色 [192,96,96] 和黄色 [192,216,144] 也做掩膜, 检查是否是其他州色块.
这样能确定幽州深绿的精确空间范围.

输出: 
  - mask components 形心+面积 + 长宽 + 边界 extent
  - 多种主要色块的 spatial extent (用于确定幽州)
"""

import os, json
import numpy as np
from PIL import Image
import cv2

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '幽州.png')
OUT = os.path.join(HERE, 'youzhou_diag4')
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

# 每个 connected component 独立 + 临近(2-3像素)做合一
nb, lab, st, cen = cv2.connectedComponentsWithStats(mask, 8)
print(f'green: {nb-1} components')
comps = []
for i in range(1, nb):
    a = st[i, cv2.CC_STAT_AREA]
    if a < 30:
        continue
    x0 = st[i, cv2.CC_STAT_LEFT]
    y0 = st[i, cv2.CC_STAT_TOP]
    w = st[i, cv2.CC_STAT_WIDTH]
    h = st[i, cv2.CC_STAT_HEIGHT]
    comps.append({'i': i, 'area': int(a), 'cx': float(cen[i, 0]), 'cy': float(cen[i, 1]),
                  'bbox': [int(x0), int(y0), int(x0+w), int(y0+h)]})

# 按 area 排序
comps.sort(key=lambda c: -c['area'])
with open(os.path.join(OUT, 'green_components.json'), 'w', encoding='utf-8') as fp:
    json.dump({'image_size': [W, H], 'components': comps}, fp, ensure_ascii=False, indent=2)
print('Top 10 green components:')
for c in comps[:10]:
    print(f"  #{c['i']:3d}  area={c['area']:>7,}  center=({c['cx']:.1f},{c['cy']:.1f})  bbox={c['bbox']}")

# 画在图上, 标号
disp = rgb.copy()
for j, c in enumerate(comps[:20]):
    x0, y0, x1, y1 = c['bbox']
    cv2.rectangle(disp, (x0, y0), (x1, y1), (255, 0, 255), 2)
    cv2.putText(disp, f'a={c["area"]}', (x0, y0 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
Image.fromarray(disp).save(os.path.join(OUT, 'green_components.png'))

# 红色 (192,96,96)
red_mask = ((r > 160) & (g < 130) & (b < 130)).astype(np.uint8) * 255
red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, k, iterations=2)
nb, lab, st, cen = cv2.connectedComponentsWithStats(red_mask, 8)
red_comps = []
for i in range(1, nb):
    a = st[i, cv2.CC_STAT_AREA]
    if a < 50:
        continue
    x0 = st[i, cv2.CC_STAT_LEFT]; y0 = st[i, cv2.CC_STAT_TOP]
    red_comps.append({'i': i, 'area': int(a), 'bbox': [int(x0), int(y0), int(x0+st[i, cv2.CC_STAT_WIDTH]), int(y0+st[i, cv2.CC_STAT_HEIGHT])]})
red_comps.sort(key=lambda c: -c['area'])
print(f'\nRed components ({len(red_comps)}):')
for c in red_comps[:8]:
    print(f'  area={c["area"]:,} bbox={c["bbox"]}')

# 黄色 (192,216,144)
yellow_mask = ((r > 170) & (g > 200) & (b < 170) & (b > 100)).astype(np.uint8) * 255
yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_CLOSE, k, iterations=2)
nb, lab, st, cen = cv2.connectedComponentsWithStats(yellow_mask, 8)
yellow_comps = []
for i in range(1, nb):
    a = st[i, cv2.CC_STAT_AREA]
    if a < 50:
        continue
    x0 = st[i, cv2.CC_STAT_LEFT]; y0 = st[i, cv2.CC_STAT_TOP]
    yellow_comps.append({'area': int(a), 'bbox': [int(x0), int(y0), int(x0+st[i, cv2.CC_STAT_WIDTH]), int(y0+st[i, cv2.CC_STAT_HEIGHT])]})
yellow_comps.sort(key=lambda c: -c['area'])
print(f'\nYellow components ({len(yellow_comps)}):')
for c in yellow_comps[:8]:
    print(f'  area={c["area"]:,} bbox={c["bbox"]}')

# 蓝色海洋 (120,144,192)
sea_mask = ((b > r + 25) & (b > 150) & (r < 180)).astype(np.uint8) * 255
sea_mask = cv2.morphologyEx(sea_mask, cv2.MORPH_CLOSE, k, iterations=2)
nb, lab, st, cen = cv2.connectedComponentsWithStats(sea_mask, 8)
sea = []
for i in range(1, nb):
    a = st[i, cv2.CC_STAT_AREA]
    if a < 200:
        continue
    sea.append({'area': int(a), 'cx': float(cen[i, 0]), 'cy': float(cen[i, 1])})
sea.sort(key=lambda c: -c['area'])
print(f'\nBlue sea components ({len(sea)}):')
for s in sea[:5]:
    print(f'  area={s["area"]:,}  center=({s["cx"]},{s["cy"]})')

# 总合成一个区域分布图
preview = rgb.copy()
# 红色组件红色框
for c in red_comps[:6]:
    x0, y0, x1, y1 = c['bbox']
    cv2.rectangle(preview, (x0, y0), (x1, y1), (255, 0, 0), 4)
# 黄色组件黄色框
for c in yellow_comps[:6]:
    x0, y0, x1, y1 = c['bbox']
    cv2.rectangle(preview, (x0, y0), (x1, y1), (255, 255, 0), 4)
# 绿色组件紫色框 (仅 top 5)
for c in comps[:5]:
    x0, y0, x1, y1 = c['bbox']
    cv2.rectangle(preview, (x0, y0), (x1, y1), (255, 0, 255), 4)
Image.fromarray(preview).save(os.path.join(OUT, 'regional_overlay.png'))
print('OK')
