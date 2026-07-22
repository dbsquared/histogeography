#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_youzhou_img5.py
======================
对幽州绿色掩膜做边界提取与形状诊断
"""

import os, json
import numpy as np
from PIL import Image
import cv2

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '幽州.png')
OUT = os.path.join(HERE, 'youzhou_diag5')
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

y_proj = (mask > 0).sum(axis=1)  # 每行像元数
x_proj = (mask > 0).sum(axis=0)
print(f'Total: {int((mask > 0).sum()):,} px')
print(f'Width coverage: x range where mask exists:')
print(f'  minx={int(np.where(x_proj > 0)[0].min())}, maxx={int(np.where(x_proj > 0)[0].max())}')
print(f'Height coverage:')
print(f'  miny={int(np.where(y_proj > 0)[0].min())}, maxy={int(np.where(y_proj > 0)[0].max())}')

# 看每一行的 mask 厚度
print(f'\nRow profile (every 50 rows):')
for y in range(0, H, max(1, H // 20)):
    thickness = int(y_proj[y])
    if thickness > 0:
        xs = np.where(mask[y] > 0)[0]
        print(f'  y={y:4d}: thick={thickness:5d}  x[{xs.min()}-{xs.max()}]')

# 提取主轮廓
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
print(f'\nContours: {len(contours)}')
main = max(contours, key=cv2.contourArea)
print(f'Main contour area: {cv2.contourArea(main):.0f}')
print(f'Main contour rect: {cv2.boundingRect(main)}')
# approxPolyDP 不同精度
for eps in [0.001, 0.002, 0.005, 0.01]:
    e = eps * cv2.arcLength(main, True)
    poly = cv2.approxPolyDP(main, e, True).reshape(-1, 2)
    print(f'  eps={eps}: {len(poly)} polygon vertices')

# 可视化
cv2.drawContours(rgb, [main], -1, (255, 0, 0), 4)
poly = cv2.approxPolyDP(main, 0.005 * cv2.arcLength(main, True), True).reshape(-1, 2)
cv2.polylines(rgb, [poly], True, (255, 255, 0), 2)
for p in poly:
    cv2.circle(rgb, tuple(p), 6, (0, 0, 255), 2)
Image.fromarray(rgb).save(os.path.join(OUT, 'main_contour.png'))
print('OK')
