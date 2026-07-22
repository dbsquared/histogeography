#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_youzhou_img2.py
======================
更精细地提取幽州深绿区域:
  1. 按 RGB 距离做"按色快照"——找几个最像幽州的色点
  2. 限制只取连通域里属于幽州主体的那个
  3. 同时找城市标记点候选: 在幽州外(背景)区域里的小色块, 通常是红色或黑色 dot

输出:
  - diag2/masks_by_color/{k}.png  按色分别的掩膜
  - diag2/green_main.png          主体幽州绿色掩膜 (清理后)
  - diag2/dots_colored.json       红色/黑色 dot 候选 + 像素坐标
  - diag2/dots_preview.png        在原图上画候选 dot
"""

import os, json
import numpy as np
from PIL import Image
import cv2

Image.MAX_IMAGE_PIXELS = None

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '幽州.png')
OUT = os.path.join(HERE, 'youzhou_diag2')
os.makedirs(OUT, exist_ok=True)

rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = rgb.shape[:2]
print(f'Image: {W}x{H}')

# ---------- 1. 深绿色: 用 RGB 目标色 (116,174,128) 做距离阈值 ----------
# 量化目标色——幽州绿在地图上比较纯净
# 试试用 green channel dominant + 不太亮 + 暖色少
g = rgb[:, :, 1].astype(int)
r = rgb[:, :, 0].astype(int)
b = rgb[:, :, 2].astype(int)

# 幽州深绿: G 明显大于 R 和 B, G 介于 120-200, R 介于 60-150
mask_green = (g > r + 25) & (g > b + 20) & (g > 110) & (g < 210) & (r < 160) & (b < 160)
mask_green = mask_green.astype(np.uint8) * 255
# 形态学
k = np.ones((4, 4), np.uint8)
mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_CLOSE, k, iterations=3)
mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, k, iterations=2)

# 最大连通域
nb, lab, st, _ = cv2.connectedComponentsWithStats(mask_green, 8)
print(f'green: {nb-1} components')
areas = sorted([(st[i, cv2.CC_STAT_AREA], i) for i in range(1, nb)], reverse=True)
for a, i in areas[:5]:
    print(f'  comp#{i} area={a:,}')
if nb > 1:
    biggest = areas[0][1]
    main_green = np.zeros_like(mask_green)
    main_green[lab == biggest] = 255
    # 进一步把靠近主区域的次大块也合并进来
    for a, i in areas[1:6]:
        if a > 600:
            main_green[lab == i] = 255
    main_green = cv2.morphologyEx(main_green, cv2.MORPH_CLOSE, np.ones((6, 6), np.uint8), iterations=2)
else:
    main_green = mask_green

cv2.imwrite(os.path.join(OUT, 'green_main.png'), main_green)
ys, xs = np.where(main_green > 0)
if len(xs):
    print(f'Green main: {len(xs):,} px, bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]')
    print(f'Avg RGB = {tuple(rgb[ys, xs].mean(axis=0).astype(int).tolist())}')

# ---------- 2. 找现代城市标记点 ----------
# 原图背景里通常现代城市是用 小圆点 + 文字 标记, 颜色一般是红色/黑色
# 先做红色 dot 检测
r_double = r > 180
g_low = g < 140
b_low = b < 140
red_mask = (r_double & g_low & b_low).astype(np.uint8) * 255
red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
nb, lab, st, cen = cv2.connectedComponentsWithStats(red_mask, 8)
red_dots = []
for i in range(1, nb):
    a = st[i, cv2.CC_STAT_AREA]
    if 4 <= a <= 80:
        cx, cy = cen[i]
        red_dots.append({'area': int(a), 'cx': float(cx), 'cy': float(cy)})
print(f'Red dot candidates: {len(red_dots)}')

# 黑色 dot (深灰)
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
black_mask = (gray < 60).astype(np.uint8) * 255
black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
nb, lab, st, cen = cv2.connectedComponentsWithStats(black_mask, 8)
black_dots = []
for i in range(1, nb):
    a = st[i, cv2.CC_STAT_AREA]
    if 4 <= a <= 80:
        cx, cy = cen[i]
        black_dots.append({'area': int(a), 'cx': float(cx), 'cy': float(cy)})
print(f'Black dot candidates: {len(black_dots)}')

# 蓝色 dot (有些地图用蓝色标城市)
blue_mask = (b > 180) & (r < 150) & (g < 200)
blue_mask = blue_mask.astype(np.uint8) * 255
blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
nb, lab, st, cen = cv2.connectedComponentsWithStats(blue_mask, 8)
blue_dots = []
for i in range(1, nb):
    a = st[i, cv2.CC_STAT_AREA]
    if 4 <= a <= 80:
        cx, cy = cen[i]
        blue_dots.append({'area': int(a), 'cx': float(cx), 'cy': float(cy)})
print(f'Blue dot candidates: {len(blue_dots)}')

# 合并所有 candidates, 在图上用不同色画出来
disp = rgb.copy()
for d in red_dots:
    cv2.circle(disp, (int(d['cx']), int(d['cy'])), 6, (255, 255, 0), 1)
for d in black_dots:
    cv2.circle(disp, (int(d['cx']), int(d['cy'])), 6, (0, 200, 255), 1)
for d in blue_dots:
    cv2.circle(disp, (int(d['cx']), int(d['cy'])), 6, (255, 100, 255), 1)
Image.fromarray(disp).save(os.path.join(OUT, 'dots_preview.png'))
cv2.imwrite(os.path.join(OUT, 'red_mask.png'), red_mask)
cv2.imwrite(os.path.join(OUT, 'black_mask.png'), black_mask)

with open(os.path.join(OUT, 'dots_colored.json'), 'w', encoding='utf-8') as fp:
    json.dump({'image_size': [W, H],
               'red_dots': red_dots, 'black_dots': black_dots, 'blue_dots': blue_dots},
              fp, ensure_ascii=False, indent=2)
print('OK')
