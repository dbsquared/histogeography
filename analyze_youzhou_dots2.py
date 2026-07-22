#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_youzhou_dots2.py
========================
更智能的城市标记点发现:
  - 限定在主体区域 (y[200,1100], x[50,1900])
  - 面积 6-60
  - 圆度高 (aspect 0.6-1.6)
  - 颜色: 排除非主体色 (深蓝/红/黑/深绿)
  - 还要找"带白边带颜色的 dot"——典型城市标记常见样式
方法: 先找小连通的"非背景色"块, 再做白环检测.
"""

import os, json
import numpy as np
from PIL import Image
import cv2

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '幽州.png')
OUT = os.path.join(HERE, 'youzhou_diag8')
os.makedirs(OUT, exist_ok=True)

rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = rgb.shape[:2]

# 主体区域 mask
interior = np.zeros((H, W), np.uint8)
interior[200:1100, 50:1900] = 255

# 提取"显著非背景色"小斑点. 背景色: [192,192,192]灰 / [120,144,192]海蓝 / [96,168,120]幽州绿 / [192,216,144]黄
r = rgb[:, :, 0].astype(int)
g = rgb[:, :, 1].astype(int)
b = rgb[:, :, 2].astype(int)
# 跟任何主要背景色的距离都 >25
bg_grays = ((abs(r - 192) < 18) & (abs(g - 192) < 18) & (abs(b - 192) < 18))   # 灰
bg_sea = ((abs(r - 120) < 24) & (abs(g - 144) < 24) & (abs(b - 192) < 24))
bg_sea2 = ((abs(r - 112) < 24) & (abs(g - 160) < 24) & (abs(b - 208) < 24))
bg_green = ((abs(r - 96) < 24) & (abs(g - 168) < 24) & (abs(b - 120) < 24))
bg_yellow = ((abs(r - 192) < 24) & (abs(g - 216) < 24) & (abs(b - 144) < 24))
bg_yellow2 = ((abs(r - 168) < 24) & (abs(g - 216) < 24) & (abs(b - 192) < 24))
bg_red_border = ((abs(r - 192) < 24) & (abs(g - 96) < 24) & (abs(b - 96) < 24))

# 背景颜色汇总
background = bg_grays | bg_sea | bg_sea2 | bg_green | bg_yellow | bg_yellow2 | bg_red_border
# 我们要找的 dot 是与这些"非背景"的小块: 也就是文字、装饰、城市标记
fg_mask = (~background).astype(np.uint8) * 255
# 限制在 interior 区域
fg_mask = cv2.bitwise_and(fg_mask, fg_mask, mask=interior)
# 形态学
fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))

nb, lab, st, cen = cv2.connectedComponentsWithStats(fg_mask, 8)
candidates = []
for i in range(1, nb):
    a = st[i, cv2.CC_STAT_AREA]
    if not (8 <= a <= 80):
        continue
    x0 = st[i, cv2.CC_STAT_LEFT]; y0 = st[i, cv2.CC_STAT_TOP]
    w = st[i, cv2.CC_STAT_WIDTH]; h = st[i, cv2.CC_STAT_HEIGHT]
    cx, cy = float(cen[i][0]), float(cen[i][1])
    ar = w / max(h, 1)
    if ar < 0.55 or ar > 1.8:
        continue
    # 提取该连通域的像素, 看平均色
    comp_pixels = rgb[lab == i]
    avg_color = comp_pixels.mean(axis=0).astype(int).tolist()
    candidates.append({'area': int(a), 'cx': cx, 'cy': cy, 'w': int(w), 'h': int(h),
                       'aspect': float(ar),
                       'color': avg_color, 'bbox': [int(x0), int(y0), int(x0+w), int(y0+h)]})

print(f'Non-bg dot candidates: {len(candidates)}')

# 按颜色分类
def classify(c):
    r, g, b = c['color']
    if r > 180 and g < 150 and b < 150:
        return 'red'
    if b > 180 and r < 180 and b > r + 20:
        return 'blue'
    if r < 80 and g < 80 and b < 80:
        return 'black'
    if r > 220 and g > 220 and b > 200:
        return 'white'    # 白色 (dot 周围白点?)
    if r > 180 and g > 180 and b < 180:
        return 'yellow'
    return 'other'

for c in candidates:
    c['category'] = classify(c)

# 按 category 分组
cats = {}
for c in candidates:
    cats.setdefault(c['category'], []).append(c)

print('Categories:')
for cat, lst in sorted(cats.items(), key=lambda kv: -len(kv[1])):
    print(f'  {cat}: {len(lst)} dots')

# 重点看红色、黑色、白色
focus = []
for cat in ['red', 'black', 'white']:
    focus.extend(cats.get(cat, []))
print(f'\nFocus dots (red/black/white): {len(focus)}')

# 也是按像素位置打印一下 (看是否成簇/独立)
focus.sort(key=lambda c: (round(c['cy'] / 50), c['cx']))
print('Focus dots by position:')
for c in focus:
    print(f"  y={c['cy']:4.0f} x={c['cx']:4.0f} area={c['area']:3d} color={c['color']} cat={c['category']}")

# 可视化
disp = rgb.copy()
for c in focus:
    cv2.circle(disp, (int(c['cx']), int(c['cy'])), 8, (255, 0, 255), 2)
Image.fromarray(disp).save(os.path.join(OUT, 'focus_dots.png'))

with open(os.path.join(OUT, 'focus_dots.json'), 'w', encoding='utf-8') as fp:
    json.dump({'image_size': [W, H], 'focus': focus}, fp, ensure_ascii=False, indent=2)
print('OK')
