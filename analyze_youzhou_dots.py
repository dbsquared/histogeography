#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyze_youzhou_dots.py
======================
更仔细分析红/黑/蓝点 candidates 的空间分布, 区分 (a) 图内真正的现代城市标记
和 (b) 右侧/下侧图例文字 假阳性.
策略: 用面积+圆形度+是否在主体内容区域(y<1100)过滤  --> 给候选坐标.
"""

import os, json
import numpy as np
from PIL import Image
import cv2

Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '幽州.png')
OUT = os.path.join(HERE, 'youzhou_diag7')
os.makedirs(OUT, exist_ok=True)

rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = rgb.shape[:2]

r = rgb[:, :, 0].astype(int)
g = rgb[:, :, 1].astype(int)
b = rgb[:, :, 2].astype(int)

# 红色更严格: 暖红, S 高, 排除图边
red_mask = ((r > 180) & (g < 130) & (b < 130) & (r - g > 60) & (r - b > 60)).astype(np.uint8) * 255
# 去掉图边
red_mask[:, 0:50] = 0
red_mask[:, W-50:W] = 0
red_mask[0:50, :] = 0
red_mask[H-50:H, :] = 0
red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))

# 连通域+圆度过滤
def find_dots(mask, min_a=4, max_a=200, label=''):
    nb, lab, st, cen = cv2.connectedComponentsWithStats(mask, 8)
    dots = []
    for i in range(1, nb):
        a = st[i, cv2.CC_STAT_AREA]
        if not (min_a <= a <= max_a):
            continue
        x0 = st[i, cv2.CC_STAT_LEFT]; y0 = st[i, cv2.CC_STAT_TOP]
        w = st[i, cv2.CC_STAT_WIDTH]; h = st[i, cv2.CC_STAT_HEIGHT]
        cx, cy = cen[i]
        # 圆度: w 与 h 大致相近, 且 area 接近 π*(d/2)^2
        ar = w / max(h, 1)
        if ar < 0.45 or ar > 2.2:
            continue   # 太长就是文字
        # 也要保证是较"圆"的形状
        dots.append({'area': int(a), 'cx': float(cx), 'cy': float(cy),
                       'bbox': [int(x0), int(y0), int(x0+w), int(y0+h)],
                       'aspect': float(ar)})
    return dots

red_dots = find_dots(red_mask, 4, 200, 'red')
print(f'Filtered red dots: {len(red_dots)}')
for d in red_dots:
    print(f"  cx={d['cx']:.1f}  cy={d['cy']:.1f}  area={d['area']}  bbox={d['bbox']}")

# 蓝色 dot
blue_mask = ((b > 180) & (r < 150) & (g < 200) & (b - r > 30)).astype(np.uint8) * 255
blue_mask[:, 0:50] = 0
blue_mask[:, W-50:] = 0
blue_mask[0:50, :] = 0
blue_mask[H-50:, :] = 0
blue_mask = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
blue_dots = find_dots(blue_mask)
print(f'\nFiltered blue dots: {len(blue_dots)}')
for d in blue_dots:
    print(f"  cx={d['cx']:.1f}  cy={d['cy']:.1f}  area={d['area']}  bbox={d['bbox']}")

# 黑色 dot (深灰)
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
black_mask = (gray < 70).astype(np.uint8) * 255
black_mask[:, 0:50] = 0
black_mask[:, W-50:] = 0
black_mask[0:50, :] = 0
black_mask[H-50:, :] = 0
black_mask = cv2.morphologyEx(black_mask, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
black_dots = find_dots(black_mask)
print(f'\nFiltered black dots: {len(black_dots)}')
for d in black_dots:
    print(f"  cx={d['cx']:.1f}  cy={d['cy']:.1f}  area={d['area']}")

# 综合可视化
disp = rgb.copy()
def draw_dot(d, col):
    cv2.circle(disp, (int(d['cx']), int(d['cy'])), 8, col, 2)
    cv2.putText(disp, str(d['area']), (int(d['cx']) + 10, int(d['cy']) - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1)
for d in red_dots:
    draw_dot(d, (255, 0, 0))
for d in blue_dots:
    draw_dot(d, (0, 0, 255))
for d in black_dots:
    draw_dot(d, (0, 255, 255))
Image.fromarray(disp).save(os.path.join(OUT, 'dots_filtered.png'))

with open(os.path.join(OUT, 'filtered_dots.json'), 'w', encoding='utf-8') as fp:
    json.dump({'image_size': [W, H],
               'red_dots': red_dots, 'blue_dots': blue_dots, 'black_dots': black_dots},
              fp, ensure_ascii=False, indent=2)
print('OK')
