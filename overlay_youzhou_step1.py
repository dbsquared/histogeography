#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 step1 修正后的幽州绿色区域（高透明度）叠加到背景地形图 china_full_v3.png 上。

配准：直接复用 youzhou_layer_v2/youzhou_anchor_table.json 里的 27 个锚点
      (px,py) <-> (lon,lat)，拟合 (px,py)->(lon,lat) 多项式。
映射：lon/lat -> china_full_v3.png 像素（BW=15600, BH=9600,
      LON 75..140, LAT 15..55）。
"""
import os, json, math
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, 'china_full_v3.png')
PTS = os.path.join(HERE, 'youzhou_step1', 'boundary_points.json')
ANCHORS = os.path.join(HERE, 'youzhou_layer_v2', 'youzhou_anchor_table.json')
OUTDIR = os.path.join(HERE, 'youzhou_overlay_step1')
os.makedirs(OUTDIR, exist_ok=True)

# 大图映射参数（与 prior 脚本一致）
BW, BH = 15600, 9600
LON0, LON1 = 75.0, 140.0
LAT0, LAT1 = 15.0, 55.0
def geo_to_big(lon, lat):
    bx = (lon - LON0) / (LON1 - LON0) * BW
    by = (LAT1 - lat) / (LAT1 - LAT0) * BH
    return bx, by

# 用户反馈：整体需向右（东）平移一点让辽东半岛对齐；
# 再往右上挪 -> 继续向东 + 向北(上)
# SHIFT_DEG_LON 正值 = 向东（地图右侧）；SHIFT_DEG_LAT 正值 = 向北（地图上/纬度增大）
SHIFT_DEG_LON = 0.75
SHIFT_DEG_LAT = 0.30

# ============================================================
# 1. 加载锚点并拟合 (px,py) -> (lon,lat)
# ============================================================
anchors = json.load(open(ANCHORS, encoding='utf-8'))
axy = [(a['px'], a['py']) for a in anchors]
alon = [a['lon'] for a in anchors]
alat = [a['lat'] for a in anchors]

def basis1(x, y, deg):
    terms = [1.0]
    for p in range(1, deg + 1):
        for j in range(p + 1):
            terms.append(float(x) ** (p - j) * float(y) ** j)
    return terms

def fit_poly(pts, vals, deg):
    A = np.array([basis1(x, y, deg) for x, y in pts], dtype=float)
    coef, *_ = np.linalg.lstsq(A, np.array(vals, dtype=float), rcond=None)
    return coef, deg

def predict(coef, deg, x, y):
    return float(np.dot(coef[: len(basis1(x, y, deg))], basis1(x, y, deg)))

# 比较 一次(仿射) vs 二次
coef_lon_a, da = fit_poly(axy, alon, 1)
coef_lat_a, da = fit_poly(axy, alat, 1)
coef_lon_q, dq = fit_poly(axy, alon, 2)
coef_lat_q, dq = fit_poly(axy, alat, 2)

err_a = []
err_q = []
for (x, y), lo, la in zip(axy, alon, alat):
    e = lambda c1, c2: math.hypot((predict(c1, 1 if c1 is coef_lon_a else 2, x, y) - lo) * 111 * math.cos(math.radians(la)),
                                  (predict(c2, 1 if c2 is coef_lat_a else 2, x, y) - la) * 111)
    err_a.append(e(coef_lon_a, coef_lat_a))
    err_q.append(e(coef_lon_q, coef_lat_q))
ma, mq = sum(err_a)/len(err_a), sum(err_q)/len(err_q)
print(f'[1] 配准锚点 {len(anchors)} 个; 平均残差: 仿射={ma:.1f}km, 二次={mq:.1f}km')
if mq < ma:
    USE_LON, USE_LAT, USE_DEG = coef_lon_q, coef_lat_q, dq
    print('    采用二次多项式')
else:
    USE_LON, USE_LAT, USE_DEG = coef_lon_a, coef_lat_a, da
    print('    采用仿射')

def px_to_geo(x, y):
    return predict(USE_LON, USE_DEG, x, y), predict(USE_LAT, USE_DEG, x, y)

# ============================================================
# 2. 加载 step1 边界，映射到地形图像素
# ============================================================
data = json.load(open(PTS, encoding='utf-8'))
poly_px = [(p['px'], p['py']) for p in data['points']]

big_pts = []
lons, lats = [], []
for (x, y) in poly_px:
    lon, lat = px_to_geo(float(x), float(y))
    lon += SHIFT_DEG_LON
    lat += SHIFT_DEG_LAT
    lons.append(lon); lats.append(lat)
    bx, by = geo_to_big(lon, lat)
    big_pts.append((bx, by))
if big_pts[0] != big_pts[-1]:
    big_pts.append(big_pts[0])
print(f'[2] 边界点 {len(poly_px)} 映射(已东移{SHIFT_DEG_LON}°) -> lon[{min(lons):.2f},{max(lons):.2f}] lat[{min(lats):.2f},{max(lats):.2f}]')

# ============================================================
# 3. 在地形图上叠加（高透明）
# ============================================================
PREV_W = 2600
PREV_H = int(BH * PREV_W / BW)
scale_x = BW / PREV_W
scale_y = BH / PREV_H

print(f'[3] 加载地形图并缩放到 {PREV_W}x{PREV_H} ...')
base = Image.open(BASE).convert('RGB').resize((PREV_W, PREV_H))
# 把边界点转到预览坐标
prev_pts = [(int(bx / scale_x), int(by / scale_y)) for (bx, by) in big_pts]

R, Gc, Bc = 96, 168, 120   # 幽州深绿

def make_overlay(fill_alpha, border_alpha, border_w):
    layer = Image.new('RGBA', (PREV_W, PREV_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.polygon(prev_pts, fill=(R, Gc, Bc, fill_alpha))
    d.line(prev_pts, fill=(R, Gc, Bc, border_alpha), width=border_w, joint='curve')
    return Image.alpha_composite(base.convert('RGBA'), layer).convert('RGB')

# “高透明”填充：多给几档，主档 fill_alpha=70
for tag, fa, ba, bw in [('a70', 70, 220, 3), ('a50', 50, 220, 3), ('a90', 90, 230, 3)]:
    out = make_overlay(fa, ba, bw)
    p = os.path.join(OUTDIR, f'youzhou_overlay_{tag}.png')
    out.save(p)
    print(f'    已保存 {p}  fill_alpha={fa}')

# 主档 also save a smaller jpg for quick view
out = make_overlay(70, 220, 3)
out.resize((1300, int(PREV_H*1300/PREV_W))).save(os.path.join(OUTDIR, 'youzhou_overlay_small.jpg'), quality=85)
print(f'[done] 产物在 {OUTDIR}/')
