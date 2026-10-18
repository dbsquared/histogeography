# -*- coding: utf-8 -*-
"""
生成 viewer/rivers.geojson —— 主图范围内的主要河流矢量图层(含国外)
数据源: Natural Earth 10m Rivers (public domain)
中英文名称映射 / 主要河流集合 复用 river_overlay.py
裁剪范围: 72-140°E / 15-55°N (与主图 base_terrain.png 一致)
"""
import json, os
from river_overlay import NAME_TO_CN, LABEL_RIVERS, CHINA_MAJOR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'rivers', 'ne_10m_rivers.geojson')
OUT = os.path.join(ROOT, 'viewer', 'rivers.geojson')

LON_MIN, LON_MAX = 72.0, 140.0
LAT_MIN, LAT_MAX = 15.0, 55.0

# 纳入矢量图层的河流等级阈值; 主要(粗线) 由 CHINA_MAJOR 白名单 + scalerank<=2 共同决定
INCLUDE_MAX_SCALERANK = 7

# ── 手工补绘河流 ────────────────────────────────────────────────────────────
# Natural Earth 10m 未收录、但中国历史地理重要的河流。每条:
#   (名称, 折线坐标[[lon,lat],...], scalerank, major, label)
# 坐标按真实河道走向取关键节点(源→口)，非精确测绘，用于示意。
HAND_RIVERS = [
    # 洛水(南洛河)：源陕西洛南县秦岭，东流经卢氏、洛宁、宜阳、洛阳市南，至巩义洛口入黄河
    # 洛阳因「水北为阳」得名；《洛神赋》所咏即此水。
    ('洛水', [
        [109.88, 34.10],  # 洛源镇(秦岭)
        [110.15, 34.09],  # 洛南县城
        [110.40, 34.02],
        [110.70, 34.00],
        [111.05, 34.05],  # 卢氏县城
        [111.25, 34.15],
        [111.42, 34.24],  # 故县水库
        [111.65, 34.39],  # 洛宁县城
        [111.90, 34.47],
        [112.18, 34.51],  # 宜阳县城
        [112.42, 34.62],  # 洛阳市南
        [112.62, 34.69],
        [112.79, 34.72],  # 偃师
        [112.90, 34.78],
        [113.00, 34.84],  # 巩义洛口，注入黄河
    ], 6.0, True, True),
]

def clip_segment(x0, y0, x1, y1, xmin, xmax, ymin, ymax):
    """Liang-Barsky 线段裁剪到矩形框; 返回 (x1,y1,x2,y2) 或 None"""
    dx, dy = x1 - x0, y1 - y0
    if dx == 0 and dy == 0:
        return None
    p = [-dx, dx, -dy, dy]
    q = [x0 - xmin, xmax - x0, y0 - ymin, ymax - y0]
    u1, u2 = 0.0, 1.0
    for i in range(4):
        if p[i] == 0:
            if q[i] < 0:
                return None
        else:
            r = q[i] / p[i]
            if p[i] < 0:
                if r > u2:
                    return None
                if r > u1:
                    u1 = r
            else:
                if r < u1:
                    return None
                if r < u2:
                    u2 = r
    if u1 > u2:
        return None
    return (x0 + u1 * dx, y0 + u1 * dy, x0 + u2 * dx, y0 + u2 * dy)

def display_name(props):
    name = props.get('name') or ''
    name_en = props.get('name_en') or ''
    cn = NAME_TO_CN.get(name) or NAME_TO_CN.get(name_en) or ''
    if cn:
        return cn
    return name or name_en  # 无中文映射时回退英文/本地名

def mean_lon(polylines):
    """计算一条河所有顶点的平均经度, 用于同名单字河消歧"""
    s = 0.0; n = 0
    for pl in polylines:
        for p in pl:
            s += p[0]; n += 1
    return s / n if n else 0.0

def main():
    gj = json.load(open(SRC, encoding='utf-8'))
    feats = []
    n_incl = 0
    for ft in gj['features']:
        props = ft.get('properties', {})
        if props.get('featurecla') != 'River':
            continue
        sr = props.get('scalerank')
        if sr is None or sr > INCLUDE_MAX_SCALERANK:
            continue
        g = ft['geometry']
        if g['type'] == 'LineString':
            polylines = [g['coordinates']]
        elif g['type'] == 'MultiLineString':
            polylines = g['coordinates']
        else:
            continue
        clipped = []
        for pl in polylines:
            for i in range(len(pl) - 1):
                x0, y0 = pl[i][0], pl[i][1]
                x1, y1 = pl[i + 1][0], pl[i + 1][1]
                seg = clip_segment(x0, y0, x1, y1, LON_MIN, LON_MAX, LAT_MIN, LAT_MAX)
                if seg:
                    clipped.append([[seg[0], seg[1]], [seg[2], seg[3]]])
        if not clipped:
            continue
        raw_name = (props.get('name') or '')
        name = display_name(props)
        # 同名单字河按经度消歧: Min(四川岷江 vs 福建闽江), Han(汉江 vs 韩国汉江)
        if raw_name == 'Min':
            name = '岷江' if mean_lon(polylines) < 110 else '闽江'
        elif raw_name == 'Han':
            name = '汉江' if mean_lon(polylines) < 120 else '汉江（韩国）'
        major = (sr <= 2) or (name in CHINA_MAJOR)
        label = major or (name in LABEL_RIVERS)
        feats.append({
            'type': 'Feature',
            'properties': {
                'kind': 'river',
                'name': name,
                'scalerank': sr,
                'major': major,
                'label': label,
            },
            'geometry': {'type': 'MultiLineString', 'coordinates': clipped},
        })
        n_incl += 1

    # ── 追加手工补绘河流（NE 10m 未收录）──────────────────────────────
    for hname, hcoords, hsr, hmajor, hlabel in HAND_RIVERS:
        feats.append({
            'type': 'Feature',
            'properties': {'kind': 'river', 'name': hname, 'scalerank': hsr,
                           'major': hmajor, 'label': hlabel, 'source': 'hand-drawn'},
            'geometry': {'type': 'MultiLineString', 'coordinates': [hcoords]},
        })
        n_incl += 1

    out = {'type': 'FeatureCollection', 'features': feats}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    named = sum(1 for f in feats if f['properties']['name'])
    labeled = sum(1 for f in feats if f['properties']['label'])
    majors = sum(1 for f in feats if f['properties']['major'])
    print('OK rivers.geojson: 纳入 %d 条河 (主要 %d, 命名 %d, 带标签 %d)' % (n_incl, majors, named, labeled))

if __name__ == '__main__':
    main()
