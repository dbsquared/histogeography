#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 step1 提取后的冀州青色区域（高透明度）叠加到背景地形图 china_full_v3.png 上。

配准：使用 jizhou_anchor_table.json 的 26 个锚点 (px,py) <-> (lon,lat)，
      拟合 (px,py)->(lon,lat) 多项式。
映射：lon/lat -> china_full_v3.png 像素（BW=15600, BH=9600,
      LON 75..140, LAT 15..55）。
"""
import os, json, math
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, 'china_full_v3.png')
PTS = os.path.join(HERE, 'jizhou_step1_v7c', 'boundary_points.json')
ANCHORS = os.path.join(HERE, 'jizhou_anchor_table.json')
OUTDIR = os.path.join(HERE, 'jizhou_overlay_v7c')
os.makedirs(OUTDIR, exist_ok=True)

# 大图映射参数（固定）
BW, BH = 15600, 9600
LON0, LON1 = 75.0, 140.0
LAT0, LAT1 = 15.0, 55.0
def geo_to_big(lon, lat):
    bx = (lon - LON0) / (LON1 - LON0) * BW
    by = (LAT1 - lat) / (LAT1 - LAT0) * BH
    return bx, by

# 平移微调（初始值，后续可根据视觉对齐调整）
SHIFT_DEG_LON = 0.0   # 正值=向东/右
SHIFT_DEG_LAT = 0.0   # 正值=向北/上

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
# 兼容两种格式: v7c的 [[x,y],...] 或旧版 [{'px':x,'py':y},...]
if isinstance(data['points'][0], list):
    poly_px = [(p[0], p[1]) for p in data['points']]
else:
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
print(f'[2] 边界点 {len(poly_px)} 映射 -> lon[{min(lons):.2f},{max(lons):.2f}] lat[{min(lats):.2f},{max(lats):.2f}]')

# ============================================================
# 3. 在地形图上叠加（高透明）
# ============================================================
PREV_W = 2600
PREV_H = int(BH * PREV_W / BW)
scale_x = BW / PREV_W
scale_y = BH / PREV_H

print(f'[3] 加载地形图并缩放到 {PREV_W}x{PREV_H} ...')
base = Image.open(BASE).convert('RGB').resize((PREV_W, PREV_H))
prev_pts = [(int(bx / scale_x), int(by / scale_y)) for (bx, by) in big_pts]

R, Gc, Bc = 100, 180, 165   # 冀州浅青色（与原图一致）

def make_overlay(fill_alpha, border_alpha, border_w):
    layer = Image.new('RGBA', (PREV_W, PREV_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.polygon(prev_pts, fill=(R, Gc, Bc, fill_alpha))
    d.line(prev_pts, fill=(R, Gc, Bc, border_alpha), width=border_w, joint='curve')
    return Image.alpha_composite(base.convert('RGBA'), layer).convert('RGB')

for tag, fa, ba, bw in [('a70', 70, 220, 3), ('a50', 50, 220, 3), ('a90', 90, 230, 3)]:
    out = make_overlay(fa, ba, bw)
    p = os.path.join(OUTDIR, f'jizhou_overlay_{tag}.png')
    out.save(p)
    print(f'    已保存 {p}  fill_alpha={fa}')

out = make_overlay(70, 220, 3)
out.resize((1300, int(PREV_H*1300/PREV_W))).save(os.path.join(OUTDIR, 'jizhou_overlay_small.jpg'), quality=85)

# ============================================================
# 4. Zoom 裁剪（以冀州中心放大）
# ============================================================
zoom_w, zoom_h = 1200, 900
center_lon = (min(lons) + max(lons)) / 2
center_lat = (min(lats) + max(lats)) / 2
cbx, cby = geo_to_big(center_lon + SHIFT_DEG_LON, center_lat + SHIFT_DEG_LAT)
zx0 = max(0, int(cbx/scale_x - zoom_w//2))
zy0 = max(0, int(cby/scale_y - zoom_h//2))

base_zoom = base.crop((zx0, zy0, zx0+zoom_w, zy0+zoom_h))
zoom_prev_pts = [(int(bx/scale_x - zx0), int(by/scale_y - zy0)) for (bx,by) in big_pts]

def make_zoom(fill_alpha, border_alpha):
    layer = Image.new('RGBA', (zoom_w, zoom_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.polygon(zoom_prev_pts, fill=(R, Gc, Bc, fill_alpha))
    d.line(zoom_prev_pts, fill=(R, Gc, Bc, border_alpha), width=3, joint='curve')
    return Image.alpha_composite(base_zoom.convert('RGBA'), layer).convert('RGB')

for tag, fa, ba in [('a70', 70, 220), ('a90', 90, 230)]:
    oz = make_zoom(fa, ba)
    oz.save(os.path.join(OUTDIR, f'jizhou_overlay_{tag}_zoom.png'))
    print(f'    已保存 zoom_{tag}')

oz_large = make_zoom(70, 220)
oz_large.save(os.path.join(OUTDIR, f'jizhou_overlay_a70_zoom_large.png'), quality=92)

print(f'[done] 产物在 {OUTDIR}/')
