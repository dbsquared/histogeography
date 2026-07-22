#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_youzhou_layer.py

从 `汉末十三州地图范例/幽州.png` 提取"本来的深绿色"幽州全境，
用现代大城市/历史郡治锚点做 Delaunay 三角网 + 重心插值，把像素映射到经纬度，
再映射到大地图 china_full_v3，输出单独半透明图层。
"""
import os
import math
import json
import numpy as np
import cv2
from PIL import Image, ImageDraw
from scipy.spatial import Delaunay

SRC = '汉末十三州地图范例/幽州.png'
OUTDIR = 'youzhou_layer'
BIG_MAP = 'china_full_v3.png'
BIG_LON0, BIG_LON1 = 75.0, 140.0
BIG_LAT0, BIG_LAT1 = 15.0, 55.0
BW, BH = 15600, 9600

# 颜色: 项目定义的幽州深绿色 (build_thirteen_states)
YOUZHOU_COLOR = (74, 139, 92)
FILL_ALPHA = 80
BORDER_ALPHA = 220
BORDER_WIDTH = 6

# ── 锚点表: (名称, 像素 x, 像素 y, 经度, 纬度) ──
# 现代大城市 + 历史郡治/县治 (同一地点或相近)。坐标为 WGS84。
ANCHORS = [
    # 现代大城市 (用户明确提到或邻近幽州)
    ('北京', 440, 690, 116.407, 39.904),
    ('沈阳', 1340, 360, 123.432, 41.806),
    ('大连', 1280, 950, 121.615, 38.914),
    ('秦皇岛', 1220, 430, 119.600, 39.932),
    ('平壤', 1810, 840, 125.763, 39.039),
    ('丹东', 1490, 480, 124.360, 40.000),
    # 东北/东部极值锚点
    ('高句丽', 1485, 354, 126.190, 41.120),
    ('玄菟', 1518, 292, 125.800, 41.800),
    ('元山', 1950, 850, 127.440, 39.150),
    ('旅顺', 1300, 1000, 121.200, 38.800),
    # 历史郡治/县治作为补充锚点(精确像素来自 OCR 聚类)
    ('襄平/辽阳', 1461, 440, 123.180, 41.270),
    ('渔阳/蓟州', 532, 634, 117.410, 40.050),
    ('涿郡/涿州', 380, 787, 115.870, 39.480),
    ('代郡/蔚县', 179, 698, 114.580, 39.840),
]

# ── 1. 提取幽州深绿色掩膜 ──
print('[1] 提取幽州深绿色掩膜...')
img = Image.open(SRC).convert('RGB')
W, H = img.size
rgb = np.array(img)
hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
r = rgb[:, :, 0].astype(int); g = rgb[:, :, 1].astype(int); b = rgb[:, :, 2].astype(int)

# 幽州深绿: 中绿层 (H 35-110, S 40-230, V 118-185), G 主导
# 排除黄绿 (他州) 和浅蓝绿水域
youzhou_mask = (
    (hsv[:, :, 0] >= 35) & (hsv[:, :, 0] <= 110) &
    (hsv[:, :, 1] >= 40) & (hsv[:, :, 1] <= 230) &
    (hsv[:, :, 2] >= 118) & (hsv[:, :, 2] <= 185) &
    (g > r) & (g > b)
).astype(np.uint8) * 255

# 形态学闭运算: 弥合郡界白色细缝, 让幽州成为完整区域
k = np.ones((5, 5), np.uint8)
youzhou_mask = cv2.morphologyEx(youzhou_mask, cv2.MORPH_CLOSE, k)

# 填掉内部孔洞 (白色郡界围成的白洞)
# flood fill from outside, then invert
filled = youzhou_mask.copy()
h, w = filled.shape
mask = np.zeros((h + 2, w + 2), np.uint8)
cv2.floodFill(filled, mask, (0, 0), 0)
# 任何原本是前景但 flood fill 没改到的孔洞: 用原图 - 外部背景
holes = (youzhou_mask > 0) & (filled == 0)
youzhou_mask[holes] = 255

# 保留最大连通域 (保险)
num, lab, st, _ = cv2.connectedComponentsWithStats(youzhou_mask, 8)
if num > 1:
    big = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
    youzhou_mask = (lab == big).astype(np.uint8) * 255

print(f'    深绿像素数: {int(np.sum(youzhou_mask > 0)):,}  ({100*np.sum(youzhou_mask>0)/(W*H):.1f}%)')

# ── 2. 提取边界点 ──
print('[2] 提取边界点...')
contours, _ = cv2.findContours(youzhou_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main_contour = max(contours, key=cv2.contourArea)
boundary_px = main_contour.reshape(-1, 2)

# 边界抽稀: 每 step 像素取一个代表, 保留形状
step = 5
boundary_px = boundary_px[::step]
print(f'    边界点数: {len(boundary_px)}')

# ── 3. Delaunay 三角网 + 重心插值 ──
print('[3] 构建 Delaunay 锚点三角网并插值边界坐标...')
pts = np.array([[a[1], a[2]] for a in ANCHORS], float)
geo = np.array([[a[3], a[4]] for a in ANCHORS], float)
tri = Delaunay(pts)

def barycentric(px, py):
    simplex = tri.find_simplex([[px, py]])
    if simplex[0] == -1:
        # 凸包外: 用最近三角形的质心并做外推
        centroids = pts[tri.simplices].mean(axis=1)
        dist = np.sum((centroids - [px, py]) ** 2, axis=1)
        idx = int(np.argmin(dist))
    else:
        idx = int(simplex[0])
    A = np.column_stack([
        pts[tri.simplices[idx][1]] - pts[tri.simplices[idx][0]],
        pts[tri.simplices[idx][2]] - pts[tri.simplices[idx][0]],
    ])
    A_inv = np.linalg.inv(A)
    b = A_inv @ (np.array([px, py]) - pts[tri.simplices[idx][0]])
    w0, w1, w2 = 1 - b[0] - b[1], b[0], b[1]
    #  clamp for extrapolation
    w0, w1, w2 = max(w0, 0), max(w1, 0), max(w2, 0)
    total = w0 + w1 + w2
    w0, w1, w2 = w0 / total, w1 / total, w2 / total
    plon = w0 * geo[tri.simplices[idx][0], 0] + w1 * geo[tri.simplices[idx][1], 0] + w2 * geo[tri.simplices[idx][2], 0]
    plat = w0 * geo[tri.simplices[idx][0], 1] + w1 * geo[tri.simplices[idx][1], 1] + w2 * geo[tri.simplices[idx][2], 1]
    return plon, plat

# 计算边界点经纬度
correspondence = []
for x, y in boundary_px:
    lon, lat = barycentric(int(x), int(y))
    correspondence.append({
        'px': int(x), 'py': int(y),
        'lon': round(lon, 4), 'lat': round(lat, 4)
    })

# 锚点表输出
anchor_table = []
for name, px, py, lon, lat in ANCHORS:
    anchor_table.append({
        'name': name, 'type': 'city' if '/' not in name else 'city/historical',
        'px': px, 'py': py, 'lon': lon, 'lat': lat
    })

# 统计
lons = [c['lon'] for c in correspondence]
lats = [c['lat'] for c in correspondence]
print(f'    边界经纬度范围: lon {min(lons):.2f}..{max(lons):.2f}, lat {min(lats):.2f}..{max(lats):.2f}')

# ── 4. 映射到大地图并生成图层 ──
print('[4] 映射到大地图并生成图层...')

def geo_to_big(lon, lat):
    bx = (lon - BIG_LON0) / (BIG_LON1 - BIG_LON0) * BW
    by = (BIG_LAT1 - lat) / (BIG_LAT1 - BIG_LAT0) * BH
    return bx, by

layer = Image.new('RGBA', (BW, BH), (0, 0, 0, 0))
draw = ImageDraw.Draw(layer)

# 边界点 -> 大地图像素
big_pts = []
for c in correspondence:
    bx, by = geo_to_big(c['lon'], c['lat'])
    big_pts.append((bx, by))

# 绘制半透明填充 + 边界
R, Gc, B = YOUZHOU_COLOR
if len(big_pts) >= 3:
    draw.polygon(big_pts, fill=(R, Gc, B, FILL_ALPHA))
    draw.line(big_pts + [big_pts[0]], fill=(R, Gc, B, BORDER_ALPHA), width=BORDER_WIDTH)

layer.save(os.path.join(OUTDIR, 'youzhou_layer.png'))

# 叠加到底图生成预览
base = Image.open(BIG_MAP).convert('RGBA')
overlay = Image.alpha_composite(base, layer)
overlay.save(os.path.join(OUTDIR, 'youzhou_overlay_preview.png'))

# 全图缩放预览
preview = overlay.resize((1560, 960))
preview.save(os.path.join(OUTDIR, 'youzhou_overlay_preview_small.png'))

# 局部放大: 幽州区域
left, top = geo_to_big(114.0, 45.0)
right, bottom = geo_to_big(130.0, 35.0)
left, top, right, bottom = int(left), int(top), int(right), int(bottom)
crop = overlay.crop((left, top, right, bottom))
crop = crop.resize((crop.width // 3, crop.height // 3))
crop.save(os.path.join(OUTDIR, 'diagnostic_zoom_overlay.png'))

# 提取预览: 原图 + 边界 + 锚点
extract = img.copy()
draw2 = ImageDraw.Draw(extract)
pts_list = [(int(x), int(y)) for x, y in boundary_px]
draw2.line(pts_list + [pts_list[0]], fill=(255, 255, 0), width=2)
for name, px, py, lon, lat in ANCHORS:
    draw2.ellipse([px - 5, py - 5, px + 5, py + 5], fill=(255, 0, 0))
    draw2.text((px + 8, py - 8), name, fill=(255, 0, 0))
extract.save(os.path.join(OUTDIR, 'youzhou_extract_preview.png'))

# 保存 JSON
with open(os.path.join(OUTDIR, 'youzhou_correspondence.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'source_image': SRC,
        'image_size': [W, H],
        'method': 'Delaunay triangulation + barycentric interpolation on anchor pixels -> geo',
        'anchor_count': len(ANCHORS),
        'boundary_points': len(correspondence),
        'points': correspondence
    }, f, ensure_ascii=False, indent=2)

with open(os.path.join(OUTDIR, 'youzhou_anchor_table.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'source_image': SRC,
        'anchors': anchor_table
    }, f, ensure_ascii=False, indent=2)

print('[done]')
print(f'    -> {OUTDIR}/youzhou_layer.png')
print(f'    -> {OUTDIR}/youzhou_correspondence.json')
print(f'    -> {OUTDIR}/youzhou_anchor_table.json')
print(f'    -> {OUTDIR}/youzhou_extract_preview.png')
print(f'    -> {OUTDIR}/diagnostic_zoom_overlay.png')
