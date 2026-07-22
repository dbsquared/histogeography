#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_youzhou_img3.py
======================
通过在不同空间位置采样像素颜色, 找出幽州深绿 vs 地图背景浅绿的区分阈值.
输出: 
  - samples.json   按区域采样的颜色统计
  - mask_strict.png  严格阈值掩膜
  - mask_overlay.png 原图上叠加红色边界
"""

import os, json
import numpy as np
from PIL import Image, ImageDraw
import cv2

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '幽州.png')
OUT = os.path.join(HERE, 'youzhou_diag3')
os.makedirs(OUT, exist_ok=True)

rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = rgb.shape[:2]

# 按网格采样颜色 — 看每个区块的主色
print('Spatial color sampling (20x14 grid):')
samples = []
for gy in range(14):
    for gx in range(20):
        y0, y1 = gy * H // 14, (gy + 1) * H // 14
        x0, x1 = gx * W // 20, (gx + 1) * W // 20
        block = rgb[y0:y1, x0:x1]
        # 最常见的色
        q = (block // 24) * 24
        flat = q.reshape(-1, 3)
        colors, counts = np.unique(flat, axis=0, return_counts=True)
        i = int(np.argmax(counts))
        dominant = colors[i].tolist()
        samples.append({'gx': gx, 'gy': gy, 'dominant_rgb': dominant,
                         'block_origin': [x0, y0], 'count': int(counts[i])})
        if counts[i] > 200:
            tag = ''
            r, g, b = dominant
            if g > r + 30 and g > b + 30 and g < 200 and r < 150:
                tag = '  <-- deep-green?'
            print(f'  ({gx:2d},{gy:2d}) RGB{dominant} n={counts[i]}{tag}')

with open(os.path.join(OUT, 'samples.json'), 'w', encoding='utf-8') as fp:
    json.dump({'image_size': [W, H], 'samples': samples}, fp, ensure_ascii=False, indent=2)

# 用极严格阈值: G 比 R 高出 40+, B 高出 35+, G 限定
r = rgb[:, :, 0].astype(int)
g = rgb[:, :, 1].astype(int)
b = rgb[:, :, 2].astype(int)

# 尝试3组阈值, 取面积适中(15%-25%)的
for dgr, dgb, gmax, rmax, bmax in [(35, 30, 200, 150, 150),
                                       (40, 35, 200, 145, 145),
                                       (45, 40, 195, 140, 140)]:
    m = (g > r + dgr) & (g > b + dgb) & (g < gmax) & (r < rmax) & (b < bmax) & (g > 100)
    n = int(m.sum())
    print(f'  gr+{dgr} gb+{dgb} g<{gmax} r<{rmax} b<{bmax}: {n:,} px ({100*n/(W*H):.2f}%)')

# 选最严格的(45/40)再清理
mask = ((g > r + 45) & (g > b + 40) & (g < 195) & (r < 140) & (b < 140) & (g > 100)).astype(np.uint8) * 255
k = np.ones((4, 4), np.uint8)
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=3)
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=2)
nb, lab, st, _ = cv2.connectedComponentsWithStats(mask, 8)
areas = sorted([(st[i, cv2.CC_STAT_AREA], i) for i in range(1, nb)], reverse=True)
print(f'After strict: {nb-1} components')
for a, i in areas[:6]:
    print(f'  comp#{i} area={a:,}')
if areas:
    # 主连通域 + 5%以上的邻居
    main_i = areas[0][1]
    main_mask = np.zeros_like(mask)
    main_mask[lab == main_i] = 255
    threshold_area = max(500, areas[0][0] // 50)
    for a, i in areas[1:]:
        if a > threshold_area:
            main_mask[lab == i] = 255
    main_mask = cv2.morphologyEx(main_mask, cv2.MORPH_CLOSE, np.ones((6, 6), np.uint8), iterations=2)
    cv2.imwrite(os.path.join(OUT, 'mask_strict.png'), main_mask)
    ys, xs = np.where(main_mask > 0)
    print(f'Strict mask: {len(xs):,} px  bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]')
    print(f'  avg RGB = {tuple(rgb[ys, xs].mean(axis=0).astype(int).tolist())}')
    # 叠加边界
    contours, _ = cv2.findContours(main_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    disp = rgb.copy()
    cv2.drawContours(disp, contours, -1, (255, 0, 0), 2)
    Image.fromarray(disp).save(os.path.join(OUT, 'mask_overlay.png'))
print('OK')
