# -*- coding: utf-8 -*-
"""将 provinces.geojson 中的行政图层要素裁剪到主图边界 [15,55]x[72,140]。
超出边界的南海部分（十段线南段、南海诸岛领海、海南三沙海域）交由南海微缩图(附图)呈现。
仅处理矢量几何，不改变任何数据源本身。"""
import json

SRC = 'viewer/provinces.geojson'
LON_MIN, LON_MAX = 72.0, 140.0
LAT_MIN, LAT_MAX = 15.0, 55.0

# ── Liang-Barsky 线段裁剪到矩形 ──
def clip_line_seg(p0, p1):
    x0, y0 = p0; x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    p = [-dx, dx, -dy, dy]
    q = [x0 - LON_MIN, LON_MAX - x0, y0 - LAT_MIN, LAT_MAX - y0]
    u0, u1 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return None  # 平行且在外
            continue
        t = qi / pi
        if pi < 0:
            if t > u1:
                return None
            u0 = max(u0, t)
        else:
            if t < u0:
                return None
            u1 = min(u1, t)
    if u0 > u1:
        return None
    ax = x0 + u0 * dx; ay = y0 + u0 * dy
    bx = x0 + u1 * dx; by = y0 + u1 * dy
    return ((ax, ay), (bx, by))

def clip_linestring(coords):
    out = []
    for i in range(len(coords) - 1):
        r = clip_line_seg(coords[i], coords[i + 1])
        if r:
            ((ax, ay), (bx, by)) = r
            if not out:
                out.append([ax, ay])
            elif out[-1] != [ax, ay]:
                out.append([ax, ay])
            if [bx, by] != (out[-1] if out else [bx, by]):
                out.append([bx, by])
    # 规整：相邻重复点剔除
    clean = []
    for pt in out:
        if not clean or clean[-1] != pt:
            clean.append(pt)
    return clean

# ── Sutherland-Hodgman 多边形裁剪到矩形 ──
def clip_polygon_to_box(ring):
    # ring: list of [lon,lat]; 视为闭合环（不要求首尾重复）
    def intersect(p, q, edge):
        # edge: 'left'|'right'|'bottom'|'top'
        if edge == 'left':
            t = (LON_MIN - p[0]) / (q[0] - p[0])
        elif edge == 'right':
            t = (LON_MAX - p[0]) / (q[0] - p[0])
        elif edge == 'bottom':
            t = (LAT_MIN - p[1]) / (q[1] - p[1])
        else:
            t = (LAT_MAX - p[1]) / (q[1] - p[1])
        return [p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])]

    def inside(pt, edge):
        if edge == 'left':
            return pt[0] >= LON_MIN
        if edge == 'right':
            return pt[0] <= LON_MAX
        if edge == 'bottom':
            return pt[1] >= LAT_MIN
        return pt[1] <= LAT_MAX

    poly = list(ring)
    for edge in ('left', 'right', 'bottom', 'top'):
        if not poly:
            break
        new_poly = []
        n = len(poly)
        for i in range(n):
            cur = poly[i]
            prev = poly[i - 1]
            cur_in = inside(cur, edge)
            prev_in = inside(prev, edge)
            if cur_in:
                if not prev_in:
                    new_poly.append(intersect(prev, cur, edge))
                new_poly.append(cur)
            elif prev_in:
                new_poly.append(intersect(prev, cur, edge))
        poly = new_poly
    if len(poly) >= 3:
        # 闭合
        if poly[0] != poly[-1]:
            poly.append(poly[0])
        return poly
    return None

def clip_polygon(rings):
    # rings[0]=外环, rings[1:]=内环(洞)
    out_rings = []
    outer = clip_polygon_to_box(rings[0])
    if not outer:
        return None
    out_rings.append(outer)
    for hole in rings[1:]:
        h = clip_polygon_to_box(hole)
        if h:
            out_rings.append(h)
    return out_rings

def clip_geometry(geom):
    t = geom['type']
    if t == 'LineString':
        c = clip_linestring(geom['coordinates'])
        return {'type': 'LineString', 'coordinates': c} if len(c) >= 2 else None
    if t == 'MultiLineString':
        segs = []
        for s in geom['coordinates']:
            c = clip_linestring(s)
            if len(c) >= 2:
                segs.append(c)
        return {'type': 'MultiLineString', 'coordinates': segs} if segs else None
    if t == 'Polygon':
        r = clip_polygon(geom['coordinates'])
        return {'type': 'Polygon', 'coordinates': r} if r else None
    if t == 'MultiPolygon':
        polys = []
        for poly in geom['coordinates']:
            r = clip_polygon(poly)
            if r:
                polys.append(r)
        return {'type': 'MultiPolygon', 'coordinates': polys} if polys else None
    return geom

gj = json.load(open(SRC, encoding='utf-8'))
new_feats = []
removed = []
for ft in gj['features']:
    k = ft['properties'].get('kind')
    g = clip_geometry(ft['geometry'])
    if g is None:
        removed.append((k, ft['properties'].get('name_zh', '')))
        continue
    ft['geometry'] = g
    new_feats.append(ft)

gj['features'] = new_feats
json.dump(gj, open(SRC, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('保留要素:', len(new_feats))
print('移除要素:', removed)

# 校验：无要素越界
def rings_of(ft):
    g = ft['geometry']
    if g['type'] == 'Polygon':
        return g['coordinates']
    if g['type'] == 'MultiPolygon':
        return [r for poly in g['coordinates'] for r in poly]
    return []
def lines_of(ft):
    g = ft['geometry']
    if g['type'] == 'LineString':
        return [g['coordinates']]
    if g['type'] == 'MultiLineString':
        return g['coordinates']
    return []
minlat = 90
for ft in new_feats:
    if ft['properties'].get('kind') == 'nine_dash':
        for s in lines_of(ft):
            minlat = min(minlat, min(p[1] for p in s))
    elif ft['properties'].get('kind') in ('country_border', 'province'):
        for r in rings_of(ft):
            minlat = min(minlat, min(p[1] for p in r))
print('裁剪后最低纬度:', round(minlat, 3), '°N (应 >= 15)')
