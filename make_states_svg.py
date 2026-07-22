# -*- coding: utf-8 -*-
"""
根据 rendered/state_boundaries.json 的 WGS84 经纬度坐标，
生成一份独立、可缩放的 SVG 矢量地图（汉末十三州）。

投影：等经纬度 (Plate Carree)
输出：rendered/three_kingdoms_v6_vector.svg
"""
import json
import colorsys

SRC = 'rendered/state_boundaries.json'
OUT = 'rendered/three_kingdoms_v6_vector.svg'

with open(SRC, encoding='utf-8') as f:
    data = json.load(f)

states = data['states']

# ── 1. 计算经纬度范围 ──
lons, lats = [], []
for s in states:
    for lon, lat in s['vertices_wgs84']:
        lons.append(lon)
        lats.append(lat)
LON_MIN, LON_MAX = min(lons), max(lons)
LAT_MIN, LAT_MAX = min(lats), max(lats)
# 适当外扩，避免边界贴边
pad_lon = (LON_MAX - LON_MIN) * 0.04
pad_lat = (LAT_MAX - LAT_MIN) * 0.04
LON_MIN -= pad_lon; LON_MAX += pad_lon
LAT_MIN -= pad_lat; LAT_MAX += pad_lat
LON_SPAN = LON_MAX - LON_MIN
LAT_SPAN = LAT_MAX - LAT_MIN

# ── 2. 布局尺寸 ──
TITLE_H = 70
MARGIN = 56
LEGEND_H = 46
NOTE_H = 26
WIDTH_TARGET = 1600.0
scale = WIDTH_TARGET / LON_SPAN
inner_w = LON_SPAN * scale
inner_h = LAT_SPAN * scale
total_w = inner_w + 2 * MARGIN
total_h = TITLE_H + inner_h + 2 * MARGIN + LEGEND_H + NOTE_H

# 地图内容组的偏移
map_x0 = MARGIN
map_y0 = TITLE_H + MARGIN

def proj(lon, lat):
    x = (lon - LON_MIN) * scale
    y = (LAT_MAX - lat) * scale
    return x, y

# ── 3. 配色：13 个均匀 HSL 色相，半透明柔和填充 ──
def make_fill(i, n=13):
    hue = (i * 360.0 / n) % 360
    r, g, b = colorsys.hls_to_rgb(hue / 360.0, 0.68, 0.55)
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

fills = [make_fill(i) for i in range(len(states))]

# ── 4. 组装 SVG ──
parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{total_w:.0f}" height="{total_h:.0f}" '
    f'viewBox="0 0 {total_w:.0f} {total_h:.0f}" '
    f'font-family="\'Microsoft YaHei\',\'PingFang SC\',\'Noto Sans CJK SC\',sans-serif">'
)
# 定义样式
parts.append('''
  <defs>
    <style>
      .statefill { stroke:#c0392b; stroke-width:2.2; stroke-linejoin:round; }
      .grat { stroke:#cfc6b0; stroke-width:0.8; }
      .gratlabel { fill:#8a7f66; font-size:12px; }
      .statename { fill:#3a2418; font-size:18px; font-weight:700;
                   paint-order:stroke; stroke:#fff; stroke-width:3.5px; stroke-linejoin:round; }
      .capital { fill:#c0392b; stroke:#fff; stroke-width:1.4; }
      .caplabel { fill:#5a2a20; font-size:12px; font-weight:600;
                  paint-order:stroke; stroke:#fff; stroke-width:2.6px; stroke-linejoin:round; }
      .title { fill:#3a2418; font-size:30px; font-weight:800; }
      .subtitle { fill:#8a7f66; font-size:14px; }
      .legendtext { fill:#3a2418; font-size:13px; }
      .note { fill:#9a9078; font-size:11px; }
    </style>
  </defs>
''')

# 背景（羊皮纸）
parts.append(f'<rect x="0" y="0" width="{total_w:.0f}" height="{total_h:.0f}" fill="#f6f1e3"/>')

# 标题
parts.append(f'<text class="title" x="{total_w/2:.0f}" y="40" text-anchor="middle">汉末十三州 · 矢量图</text>')
parts.append(f'<text class="subtitle" x="{total_w/2:.0f}" y="60" text-anchor="middle">地理坐标 WGS84 · 等经纬度投影（Plate Carrée）· 据谭其骧《中国历史地图集》考据复原</text>')

# 地图组
parts.append(f'<g transform="translate({map_x0:.2f},{map_y0:.2f})">')

# 海洋/陆地底
parts.append(f'<rect x="0" y="0" width="{inner_w:.2f}" height="{inner_h:.2f}" fill="#eef3f4" stroke="#c9bfa6" stroke-width="1.2"/>')

# 经纬网（每 5°）
step = 5
lon_ticks = []
lo = (int(LON_MIN // step) + 1) * step
while lo < LON_MAX:
    lon_ticks.append(lo); lo += step
lat_ticks = []
la = (int(LAT_MIN // step) + 1) * step
while la < LAT_MAX:
    lat_ticks.append(la); la += step

for lo in lon_ticks:
    x, _ = proj(lo, LAT_MAX)
    parts.append(f'<line class="grat" x1="{x:.2f}" y1="0" x2="{x:.2f}" y2="{inner_h:.2f}"/>')
    px, _ = proj(lo, LAT_MIN)
    parts.append(f'<text class="gratlabel" x="{x:.2f}" y="{inner_h+15:.2f}" text-anchor="middle">{lo:.0f}°E</text>')
for la in lat_ticks:
    _, y = proj(LON_MIN, la)
    parts.append(f'<line class="grat" x1="0" y1="{y:.2f}" x2="{inner_w:.2f}" y2="{y:.2f}"/>')
    _, py = proj(LON_MIN, la)
    parts.append(f'<text class="gratlabel" x="-6" y="{py+4:.2f}" text-anchor="end">{la:.0f}°N</text>')

# 州多边形
for i, s in enumerate(states):
    pts = ' '.join(f'{proj(lon,lat)[0]:.2f},{proj(lon,lat)[1]:.2f}' for lon, lat in s['vertices_wgs84'])
    parts.append(f'<polygon class="statefill" points="{pts}" fill="{fills[i]}" fill-opacity="0.55"/>')

def point_in_poly(lon, lat, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > lat) != (yj > lat)) and \
           (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

# 州治 + 州名标注（质心；质心在多边形外时回退到距质心最近的顶点）
for i, s in enumerate(states):
    vs = s['vertices_wgs84']
    cx = sum(p[0] for p in vs) / len(vs)
    cy = sum(p[1] for p in vs) / len(vs)
    if not point_in_poly(cx, cy, vs):
        # 找距质心最近的顶点作为标注锚点
        best = min(vs, key=lambda p: (p[0]-cx)**2 + (p[1]-cy)**2)
        cx, cy = best
    lx, ly = proj(cx, cy)
    # 州治
    cap_lon, cap_lat = s['capital_wgs84']
    cxp, cyp = proj(cap_lon, cap_lat)
    parts.append(f'<circle class="capital" cx="{cxp:.2f}" cy="{cyp:.2f}" r="4.5"/>')
    parts.append(f'<text class="caplabel" x="{cxp+7:.2f}" y="{cyp+4:.2f}">{s["capital"]}</text>')
    # 州名（标注质心，略上方）
    parts.append(f'<text class="statename" x="{lx:.2f}" y="{ly-6:.2f}" text-anchor="middle">{s["name"]}</text>')

parts.append('</g>')  # /map group

# 图例（底部一行 13 个色块）
parts.append(f'<g transform="translate({MARGIN:.2f},{TITLE_H + inner_h + 2*MARGIN + 8:.2f})">')
chip_w = min(118.0, (total_w - 2*MARGIN) / len(states))
for i, s in enumerate(states):
    x = i * chip_w
    parts.append(f'<rect x="{x:.2f}" y="0" width="14" height="14" rx="3" fill="{fills[i]}" fill-opacity="0.7" stroke="#c0392b" stroke-width="1"/>')
    parts.append(f'<text class="legendtext" x="{x+20:.2f}" y="12">{s["name"]}</text>')
parts.append('</g>')

# 数据来源
parts.append(f'<text class="note" x="{MARGIN:.2f}" y="{total_h-8:.2f}">数据来源：汉末十三州边界复原（谭其骧《中国历史地图集》考据） · 渲染底图：地理空间数据云（www.gscloud.cn）SRTM 90M DEM</text>')

parts.append('</svg>')

svg = '\n'.join(parts)
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(svg)

print(f'OK -> {OUT}')
print(f'size: {len(svg)} bytes | {total_w:.0f}x{total_h:.0f} | states={len(states)}')
