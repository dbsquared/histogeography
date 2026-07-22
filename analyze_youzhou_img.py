#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_youzhou_img.py
======================
对 幽州.png 做色彩分布分析, 帮助确定:
  1) 深绿色"幽州全境"的精确 HSV/RGB 阈值
  2) 背景图中"现代城市标记点"的形态/颜色 (通常是带白边的小圆点 or 黑色 dot)
  3) 是否有文字标签 (中文城市名)

输出:
  - youzhou_diag/colors_histogram.png   主要颜色的散点/直方图
  - youzhou_diag/mask_green.png         阈值得到的深绿掩膜
  - youzhou_diag/mask_dots.png          候选城市标记点
  - youzhou_diag/sample_colors.json     采样色统计
"""

import os, json
import numpy as np
from PIL import Image
import cv2

Image.MAX_IMAGE_PIXELS = None

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '幽州.png')
OUT = os.path.join(HERE, 'youzhou_diag')
os.makedirs(OUT, exist_ok=True)

rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = rgb.shape[:2]
print(f'Image size: {W} x {H}')

# ----- 1. 主色直方图 (把 RGB 量化到 16 级看主要颜色) -----
q = (rgb // 16) * 16   # 量化
flat = q.reshape(-1, 3)
colors, counts = np.unique(flat, axis=0, return_counts=True)
order = np.argsort(-counts)
top = [(colors[i].tolist(), int(counts[i])) for i in order[:25]]
print('Top 25 colors (RGB, count):')
for c, n in top:
    pct = 100 * n / (W * H)
    print(f'  RGB{c}  {pct:5.2f}%  n={n}')
with open(os.path.join(OUT, 'sample_colors.json'), 'w', encoding='utf-8') as fp:
    json.dump({'image_size': [W, H], 'top25_colors': top}, fp, ensure_ascii=False, indent=2)

# ----- 2. 深绿区域掩膜 (用放宽阈值再看一次) -----
hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
# 分别尝试几组阈值, 选连通域最大的一组
candidates = []
for lo, hi in [
    ([30, 30, 30], [100, 220, 220]),
    ([35, 50, 40], [100, 200, 200]),
    ([40, 60, 50], [95, 220, 200]),
    ([45, 40, 30], [90, 220, 220]),
]:
    m = cv2.inRange(hsv, np.array(lo), np.array(hi))
    nb, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    if nb > 1:
        biggest = max(range(1, nb), key=lambda i: st[i, cv2.CC_STAT_AREA])
        area = st[biggest, cv2.CC_STAT_AREA]
    else:
        area = 0
    candidates.append((lo, hi, area, m if nb > 1 else None))
    print(f'  HSV {lo}-{hi}: biggest area = {area:,}')
best = max(candidates, key=lambda x: x[2])
print(f'Best green HSV range: {best[0]} - {best[1]}  area={best[2]:,}')
green_mask = best[3]
# 形态学清理
k = np.ones((4, 4), np.uint8)
green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_CLOSE, k, iterations=2)
green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, k, iterations=1)
# 只要最深绿 (排除浅绿背景)
g, r, b = rgb[:, :, 1].astype(int), rgb[:, :, 0].astype(int), rgb[:, :, 2].astype(int)
dom = (g > r + 12) & (g > b + 8) & (g < 200)
green_mask = ((green_mask > 0) & dom).astype(np.uint8) * 255
cv2.imwrite(os.path.join(OUT, 'mask_green.png'), green_mask)
ys, xs = np.where(green_mask > 0)
if len(xs):
    print(f'Green region px count = {len(xs):,}  bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]')
    avg = rgb[ys, xs].mean(axis=0).astype(int)
    print(f'Green avg RGB = {tuple(avg.tolist())}')

# ----- 3. 城市标记点候选 -----
# 现代地图上城市标记一般是 小的红色/黑色圆点带白边
# 先找所有"小而圆的高对比度斑点"
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
# 用差距检测: 与中值滤波差大的点
med = cv2.medianBlur(gray, 5)
diff = cv2.absdiff(gray, med)
_, dot_mask = cv2.threshold(diff, 40, 255, cv2.THRESH_BINARY)
# 形态学开运算去噪
dot_mask = cv2.morphologyEx(dot_mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
# 找连通域, 只保留面积小的 (2-40 像素)
nb, lab, st, cen = cv2.connectedComponentsWithStats(dot_mask, 8)
dot_cands = []
for i in range(1, nb):
    a = st[i, cv2.CC_STAT_AREA]
    if 2 <= a <= 40:
        dot_cands.append({'label': i, 'area': int(a),
                          'cx': float(cen[i, 0]), 'cy': float(cen[i, 1])})
print(f'Dot candidates: {len(dot_cands)}')
# 把候选点画出来
disp = rgb.copy()
for d in dot_cands:
    cv2.circle(disp, (int(d['cx']), int(d['cy'])), 4, (255, 0, 255), 1)
cv2.imwrite(os.path.join(OUT, 'mask_dots.png'), disp)

# 也输出 quilt 视图: 原图 + green mask + dots
preview = np.zeros((H, W * 3, 3), dtype=np.uint8)
preview[:, :W] = rgb
preview[:, W:2*W] = cv2.cvtColor(green_mask, cv2.COLOR_GRAY2RGB)
preview[:, 2*W:] = disp
Image.fromarray(preview).resize((W // 2 * 3, H // 2)).save(os.path.join(OUT, 'overview.png'))
print('OK')
