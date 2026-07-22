# -*- coding: utf-8 -*-
"""
路线 A 地形图查看器资产生成
- 晕渲地形底图 (base_terrain.png)
- 矢量等高线 GeoJSON (contours.geojson, 含海拔注记)
- 悬停查海拔用的粗高程网格 (elev_grid.bin + elev_meta.json)

坐标系: 等经纬度 Plate Carree, 经度 75-140E, 纬度 15-55N (与 geo_mapping.py 一致)
底图: china_full_v3.tif (15600x9600, EPSG:4326, nodata=-32768)
"""
import os
import json
import numpy as np
import rasterio
from rasterio.enums import Resampling
from matplotlib.colors import LightSource, LinearSegmentedColormap
from PIL import Image

# ── 常量 ──
ROOT = os.path.dirname(os.path.abspath(__file__))
TIF = os.path.join(ROOT, 'china_full_v4.tif')
OUT = os.path.join(ROOT, 'viewer')
os.makedirs(OUT, exist_ok=True)

LON_MIN, LON_MAX = 72.0, 140.0
LAT_MAX, LAT_MIN = 55.0, 15.0
LON_SPAN = LON_MAX - LON_MIN   # 65
LAT_SPAN = LAT_MAX - LAT_MIN   # 40
NODATA = -32768.0

# 查看器底图分辨率 (约 1.85 km/px)
W, H = 3900, 2400
# 悬停高程网格分辨率 (约 0.2° ≈ 22 km/格)
GW, GH = 325, 200

VMIN, VMAX = -500.0, 8848.0   # 色阶范围: 海底深蓝 -> 雪顶白

# ── 地形色阶 (与 terrain_renderer.py terrain_custom 一致) ──
TERRAIN_COLORS = [
    (0.00, '#2b5d8c'), (0.02, '#4a8ab5'), (0.05, '#7fb5d5'),
    (0.08, '#b3d9a0'), (0.15, '#8cc579'), (0.25, '#6ba356'),
    (0.35, '#c9b458'), (0.45, '#c9a048'), (0.55, '#a67c3d'),
    (0.65, '#8b5e2f'), (0.75, '#9e7a6a'), (0.85, '#c8b8a8'),
    (0.95, '#e8ddd0'), (1.00, '#ffffff'),
]
CMAP = LinearSegmentedColormap.from_list('terrain_custom', TERRAIN_COLORS, N=256)


def rowcol_to_lonlat(r, c):
    lon = LON_MIN + (c / W) * LON_SPAN
    lat = LAT_MAX - (r / H) * LAT_SPAN
    return lon, lat


def rdp(points, epsilon):
    """Ramer-Douglas-Peucker 折线简化 (迭代版)"""
    if len(points) < 3:
        return points
    keep = np.zeros(len(points), dtype=bool)
    keep[0] = True
    keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        s, e = stack.pop()
        if e <= s + 1:
            continue
        A = points[s]
        B = points[e]
        seg = B - A
        seg_len = np.hypot(seg[0], seg[1])
        sub = points[s + 1:e]
        if seg_len == 0:
            d = np.linalg.norm(sub - A, axis=1)
        else:
            v = sub - A
            d = np.abs(v[:, 0] * seg[1] - v[:, 1] * seg[0]) / seg_len
        if d.size == 0:
            continue
        idx = s + 1 + int(np.argmax(d))
        if d.max() > epsilon:
            keep[idx] = True
            stack.append((s, idx))
            stack.append((idx, e))
    return points[keep]


print('[1/4] 读取降采样 DEM ...')
with rasterio.open(TIF) as ds:
    arr = ds.read(1, out_shape=(H, W), resampling=Resampling.average).astype('float32')
    elev_coarse = ds.read(1, out_shape=(GH, GW), resampling=Resampling.bilinear).astype('float32')

arr[arr == NODATA] = np.nan
elev_coarse[elev_coarse == NODATA] = np.nan

# ── 底图: 晕渲 (hypsometric + hillshade) ──
print('[2/4] 生成晕渲地形底图 ...')
arr_filled = np.nan_to_num(arr, nan=-5000.0)   # 海洋填为负值 -> 深蓝
ls = LightSource(azdeg=315, altdeg=45)
rgb = ls.shade(arr_filled, cmap=CMAP, blend_mode='soft', vmin=VMIN, vmax=VMAX)
img = (np.clip(rgb[..., :3], 0, 1) * 255).astype('uint8')
# 底图已由 rerender_base.py 以更高分辨率(8160x4800)生成，此处跳过
# Image.fromarray(img).save(os.path.join(OUT, 'base_terrain.png'), optimize=True)
print('      [base_terrain.png 由 rerender_base.py 生成，跳过]', img.shape)

# ── 等高线 -> GeoJSON ──
print('[3/4] 提取等高线 ...')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.contour import QuadContourSet

minor_levels = list(range(500, 9000, 500))
major_levels = list(range(0, 9000, 1000))   # 含 0=海岸线, 1000,2000...
levels = sorted(set(minor_levels + major_levels))

masked = np.ma.masked_invalid(arr)
fig, ax = plt.subplots()
cs = ax.contour(masked, levels=levels, linewidths=0.5)
plt.close(fig)

features = []
label_features = []
RDP_TOL = 0.008  # 约 0.9 km

for li, lvl in enumerate(cs.levels):
    segs = cs.allsegs[li]
    if lvl == 0:
        klass = 'coast'
    elif lvl % 1000 == 0:
        klass = 'major'
    else:
        klass = 'minor'
    longest = None
    longest_len = 0
    for seg in segs:
        if len(seg) < 2:
            continue
        # matplotlib contour 返回 (x=列, y=行) -> 转 (lon, lat)
        lonlat = np.empty((len(seg), 2), dtype='float64')
        lonlat[:, 0] = LON_MIN + (seg[:, 0] / W) * LON_SPAN
        lonlat[:, 1] = LAT_MAX - (seg[:, 1] / H) * LAT_SPAN
        # 过滤极小噪声段
        if (lonlat[:, 0].max() - lonlat[:, 0].min() < 0.04 and
                lonlat[:, 1].max() - lonlat[:, 1].min() < 0.04):
            continue
        simp = rdp(lonlat, RDP_TOL)
        if len(simp) < 2:
            simp = lonlat
        coords = [[round(float(x), 4), round(float(y), 4)] for x, y in simp]
        if len(coords) < 2:
            continue
        features.append({
            'type': 'Feature',
            'properties': {'kind': 'contour', 'elevation': int(lvl), 'klass': klass},
            'geometry': {'type': 'LineString', 'coordinates': coords},
        })
        # 记录最长段用于海拔注记
        seg_len = float(np.sum(np.hypot(np.diff(lonlat, axis=0)[:, 0],
                                        np.diff(lonlat, axis=0)[:, 1])))
        if klass == 'major' and seg_len > longest_len:
            longest_len = seg_len
            longest = simp
    if longest is not None and len(longest) >= 2:
        mid = longest[len(longest) // 2]
        label_features.append({
            'type': 'Feature',
            'properties': {'kind': 'label', 'elevation': int(lvl), 'text': str(int(lvl))},
            'geometry': {'type': 'Point', 'coordinates': [round(float(mid[0]), 4), round(float(mid[1]), 4)]},
        })

fc = {'type': 'FeatureCollection', 'features': features + label_features}
with open(os.path.join(OUT, 'contours.geojson'), 'w', encoding='utf-8') as f:
    json.dump(fc, f, ensure_ascii=False, separators=(',', ':'))
print('      等高线要素数:', len(features), '| 注记数:', len(label_features))

# ── 悬停高程网格 ──
print('[4/4] 写入悬停高程网格 ...')
with open(os.path.join(OUT, 'elev_grid.bin'), 'wb') as f:
    f.write(elev_coarse.astype('<f4').tobytes())
meta = {
    'width': GW, 'height': GH,
    'lon_min': LON_MIN, 'lon_max': LON_MAX,
    'lat_max': LAT_MAX, 'lat_min': LAT_MIN,
    'nodata': -32768,
}
with open(os.path.join(OUT, 'elev_meta.json'), 'w', encoding='utf-8') as f:
    json.dump(meta, f, ensure_ascii=False)

print('完成。输出目录:', OUT)
for fn in ['base_terrain.png', 'contours.geojson', 'elev_grid.bin', 'elev_meta.json']:
    p = os.path.join(OUT, fn)
    print('  ', fn, f'{os.path.getsize(p)/1024/1024:.2f} MB' if os.path.getsize(p) > 1 << 20 else f' {os.path.getsize(p)/1024:.1f} KB')
