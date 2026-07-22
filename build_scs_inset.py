# -*- coding: utf-8 -*-
"""
生成 viewer/scs_inset_data.js —— 南海诸岛附图(南海十段线补全)数据
数据源(均公开/权威):
  - 中国海岸线 + 十段线: viewer/provinces.geojson (Supeset China-GeoData 国界 + geojson.cn 十段线)
  - 周边国家轮廓(越南/菲律宾/马来/印尼/文莱等, 仅作地理参照, 非主权主张):
        Natural Earth 10m admin_0_countries (public domain, data/admin/)
  - 主要岛礁: 硬编码常识坐标(海南岛/东沙/西沙/中沙/黄岩岛/南沙/曾母暗沙)
输出 window.SCS_INSET = {box, ne, coast, dash, islands}，供 index.html 渲染 SVG 附图。
"""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(ROOT, 'viewer')
PROV = os.path.join(V, 'provinces.geojson')
NE_SHP = os.path.join(ROOT, 'data/admin/ne_10m_admin_0_countries.shp')
OUT = os.path.join(V, 'scs_inset_data.js')

# 附图显示窗口 (经纬度)
BOX = {'lon0': 103.0, 'lon1': 127.0, 'lat0': 0.0, 'lat1': 27.0}

def in_box(lon, lat):
    return BOX['lon0'] <= lon <= BOX['lon1'] and BOX['lat0'] <= lat <= BOX['lat1']

def clip_ring(ring):
    """把一条闭合环裁剪到显示窗口，返回若干在窗口内的折线段。"""
    segs, cur = [], []
    for pt in ring:
        lon, lat = float(pt[0]), float(pt[1])
        if in_box(lon, lat):
            cur.append([round(lon, 4), round(lat, 4)])
        else:
            if cur:
                segs.append(cur); cur = []
    if cur:
        segs.append(cur)
    return segs

def rings_of(geom):
    """返回几何体的所有外环(用于海岸/国界轮廓)。"""
    out = []
    t = geom['type']
    if t == 'Polygon':
        out.append(geom['coordinates'][0])
    elif t == 'MultiPolygon':
        for poly in geom['coordinates']:
            out.append(poly[0])
    elif t == 'LineString':
        out.append(geom['coordinates'])
    elif t == 'MultiLineString':
        for s in geom['coordinates']:
            out.append(s)
    return out

def _shape_to_geom(shp):
    """把 pyshp shape 转成 {type, coordinates} 供 rings_of 使用。"""
    st = shp.shapeType
    parts = list(shp.parts)
    pts = shp.points
    if st in (5, 15):  # Polygon / PolygonZ
        polys = []
        for i, p in enumerate(parts):
            q = parts[i + 1] if i + 1 < len(parts) else len(pts)
            polys.append(pts[p:q])
        return {'type': 'MultiPolygon', 'coordinates': [[poly] for poly in polys]}
    if st in (3, 13):  # PolyLine
        lines = []
        for i, p in enumerate(parts):
            q = parts[i + 1] if i + 1 < len(parts) else len(pts)
            lines.append(pts[p:q])
        return {'type': 'MultiLineString', 'coordinates': lines}
    return {'type': 'Polygon', 'coordinates': [pts]}

# ---- 1) 中国海岸线(Supeset 国界) + 十段线 ----
gj = json.load(open(PROV, encoding='utf-8'))
coast, dash = [], []
for f in gj['features']:
    k = f['properties'].get('kind')
    if k == 'country_border':
        for r in rings_of(f['geometry']):
            coast.extend(clip_ring(r))
    elif k == 'nine_dash':
        for r in rings_of(f['geometry']):
            dash.extend(clip_ring(r))

# ---- 2) 周边国家轮廓 (Natural Earth, 仅地理参照) ----
ne = []
try:
    import shapefile
    sf = shapefile.Reader(NE_SHP)
    name_idx = None
    for i, fld in enumerate(sf.fields[1:]):
        if fld[0].upper() in ('NAME', 'NAME_EN', 'ADMIN'):
            name_idx = i; break
    for rec, shp in zip(sf.iterRecords(), sf.iterShapes()):
        nm = rec[name_idx] if name_idx is not None else ''
        if nm in ('China', 'Taiwan'):
            continue  # 中国/台湾海岸用 Supeset 权威源，避免重复
        for r in rings_of(_shape_to_geom(shp)):
            ne.extend(clip_ring(r))
except Exception as e:
    print('警告: 读取 Natural Earth 失败，附图将不含周边国家轮廓:', e)

# ---- 3) 主要岛礁(硬编码常识坐标) ----
islands = [
    [109.8, 19.2, '海南岛'],
    [116.7, 20.7, '东沙群岛'],
    [112.0, 16.8, '西沙群岛'],
    [114.5, 15.5, '中沙群岛'],
    [117.8, 15.1, '黄岩岛'],
    [114.3, 9.8, '南沙群岛'],
    [112.5, 4.0, '曾母暗沙'],
]

payload = {
    'box': BOX,
    'ne': ne,
    'coast': coast,
    'dash': dash,
    'islands': islands,
}
with open(OUT, 'w', encoding='utf-8') as f:
    f.write('window.SCS_INSET=')
    json.dump(payload, f, ensure_ascii=False)
    f.write(';')
print('OK', OUT)
print('ne 段数:', len(ne), ' coast 段数:', len(coast), ' dash 段数:', len(dash), ' 岛礁:', len(islands))
