# -*- coding: utf-8 -*-
"""
生成 viewer/mountains.geojson —— 主要山脉矢量图层(可切换, 接入 viewer/index.html)
数据源: Natural Earth 10m geography_regions_polys (FEATURECLA='Range/mtn', public domain)
        + 手工补齐 NE 缺失的 9 条主要山脉
走向表现: 每条山脉用 PCA 求主方向, 在面内生成"垂直于走向"的梳齿短线段(LineString),
          并画中心轴线 + 双向箭头(LineString) 明确走向; 另出标签点(Point)。
地图为 L.CRS.Simple (1 单位=1 度, x=lon, y=lat 北向上), 故 lon/lat 空间里的垂直即屏幕垂直,
梳齿可直接用经纬度几何表达, 缩放/平移均保持走向正确。
"""
import json, os, math
import numpy as np
import shapefile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NE_SHP = os.path.join(BASE_DIR, 'data', 'mountains', 'ne_10m_geography_regions_polys.shp')
OUT = os.path.join(BASE_DIR, 'viewer', 'mountains.geojson')

# 地图范围(L.CRS.Simple, 与 viewer/index.html 一致)
LON_MIN, LON_MAX = 72.0, 140.0
LAT_MIN, LAT_MAX = 15.0, 55.0

# 梳齿参数(经纬度度)
TOOTH_LEN = 0.18      # 笔触长度(度)
TOOTH_STEP = 0.30     # 网格间距(度)
ARROW_LEN = 0.30      # 箭头翼长(度)

# NE 白名单: 中国主要山脉 + 关键边境山脉
NE_WHITELIST = {
    'Dabie Mountains': '大别山',
    'Greater Khingan': '大兴安岭',
    'Himalayas': '喜马拉雅山脉',
    'Kunlun Mountains': '昆仑山脉',
    'Lesser Khingan': '小兴安岭',
    'Lüliang Mountains': '吕梁山',
    'Nanling Mountains': '南岭',
    'Qilian Mountains': '祁连山',
    'Qinling': '秦岭',
    'Taihang Mountains': '太行山',
    'Tian Shan': '天山山脉',
    'Wuyi Mountains': '武夷山脉',
    'Yin Mountains': '阴山',
    'Altai Mountains': '阿尔泰山脉',
    'Dalou Mountains': '大娄山',
    'Karakoram': '喀喇昆仑山脉',
    'Pamir mountains': '帕米尔高原',
    'Altyn-Tagh': '阿尔金山',
}
# 手工补齐 NE 缺失的主要山脉(简化面, 沿已知走向)
HAND_RANGES = [
    ('横断山脉', [(97.0,25.0),(101.5,25.5),(101.0,32.0),(97.5,32.0)]),
    ('巫山',     [(107.8,30.2),(110.6,30.8),(110.9,31.6),(107.5,31.0)]),
    ('雪峰山',   [(109.4,27.0),(112.0,27.6),(112.2,28.6),(109.6,28.0)]),
    ('贺兰山',   [(105.6,38.2),(106.4,38.4),(106.5,39.4),(105.7,39.2)]),
    ('长白山',   [(126.6,41.4),(128.6,41.2),(130.0,42.0),(127.8,42.9)]),
    ('台湾山脉', [(120.7,22.0),(121.3,22.2),(121.9,24.5),(121.3,24.4)]),
    ('唐古拉山脉',[(88.5,32.8),(93.5,32.5),(93.8,33.6),(88.8,33.9)]),
    ('念青唐古拉山脉',[(87.5,29.8),(93.5,29.5),(93.8,30.6),(87.8,30.9)]),
    ('燕山',     [(114.5,40.3),(119.5,40.5),(120.0,41.3),(115.0,41.1)]),
]

def in_extent(bb):
    return not (bb[2] < LON_MIN or bb[0] > LON_MAX or bb[3] < LAT_MIN or bb[1] > LAT_MAX)

def pip(lon, lat, ring):
    """射线法点在内/外(ring 为 [(lon,lat),...])"""
    inside = False; n = len(ring); j = n - 1
    for i in range(n):
        xi, yi = ring[i]; xj, yj = ring[j]
        if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def poly_geom_from_parts(parts, pts, kind='Polygon'):
    rings = []
    for k in range(len(parts)):
        s = parts[k]; e = parts[k + 1] if k + 1 < len(parts) else len(pts)
        rings.append([[round(x, 5), round(y, 5)] for x, y in pts[s:e]])
    if len(rings) == 1:
        return {'type': 'Polygon', 'coordinates': rings}
    return {'type': 'MultiPolygon', 'coordinates': [[r] for r in rings]}

def load_ne_ranges():
    sf = shapefile.Reader(NE_SHP)
    out = []
    for i in range(len(sf.shapes())):
        d = sf.record(i).as_dict()
        if d['FEATURECLA'] != 'Range/mtn':
            continue
        en = d.get('NAME_EN') or ''
        if en not in NE_WHITELIST:
            continue
        geom = sf.shape(i)
        parts = geom.parts; pts = geom.points
        if not in_extent(geom.bbox):
            continue
        out.append({'name': NE_WHITELIST[en],
                    'geom': poly_geom_from_parts(parts, pts),
                    'source': 'Natural Earth 10m',
                    'rings': [[(x, y) for x, y in pts[parts[k]:(parts[k+1] if k+1 < len(parts) else len(pts))]]
                              for k in range(len(parts))]})
    sf.close()
    return out

def compute_trend(rings):
    P = np.array([(x, y) for ring in rings for (x, y) in ring], dtype=float)
    c = P.mean(0)
    X = P - c
    cov = X.T @ X / len(X)
    w, v = np.linalg.eigh(cov)
    maj = v[:, np.argmax(w)]
    perp = np.array([-maj[1], maj[0]])
    proj = X @ maj
    return c, maj, perp, (proj.min(), proj.max())

def build_features(name, rings, geom, source='Natural Earth 10m'):
    feats = []
    c, maj, perp, (pmin, pmax) = compute_trend(rings)
    # 包围盒(用于梳齿网格)
    xs = [p[0] for ring in rings for p in ring]; ys = [p[1] for ring in rings for p in ring]
    lon0, lon1 = min(xs), max(xs); lat0, lat1 = min(ys), max(ys)
    half = TOOTH_LEN / 2.0
    h = half
    lat = lat0
    while lat <= lat1:
        lon = lon0
        while lon <= lon1:
            inside = any(pip(lon, lat, ring) for ring in rings)
            if inside:
                a = [round(lon + perp[0] * h, 5), round(lat + perp[1] * h, 5)]
                b = [round(lon - perp[0] * h, 5), round(lat - perp[1] * h, 5)]
                feats.append({'type': 'Feature',
                    'properties': {'kind': 'mountain_hachure'},
                    'geometry': {'type': 'LineString', 'coordinates': [a, b]}})
            lon += TOOTH_STEP
        lat += TOOTH_STEP
    # 中心轴线
    e1 = [round(c[0] + maj[0] * pmax, 5), round(c[1] + maj[1] * pmax, 5)]
    e2 = [round(c[0] + maj[0] * pmin, 5), round(c[1] + maj[1] * pmin, 5)]
    feats.append({'type': 'Feature',
        'properties': {'kind': 'mountain_axis', 'name': name, 'source': source},
        'geometry': {'type': 'LineString', 'coordinates': [e1, e2]}})
    # 双向箭头(翼)
    for e in (e1, e2):
        back = np.array([e[0] - c[0], e[1] - c[1]]); back = back / np.linalg.norm(back)
        for sgn in (1, -1):
            wpt = [round(e[0] + back[0] * ARROW_LEN + perp[0] * ARROW_LEN * 0.6 * sgn, 5),
                   round(e[1] + back[1] * ARROW_LEN + perp[1] * ARROW_LEN * 0.6 * sgn, 5)]
            feats.append({'type': 'Feature',
                'properties': {'kind': 'mountain_arrow'},
                'geometry': {'type': 'LineString', 'coordinates': [e, wpt]}})
    # 面(范围提示, 极淡填充)
    feats.append({'type': 'Feature',
        'properties': {'kind': 'mountain_area', 'name': name, 'source': source},
        'geometry': geom})
    # 标签点(质心)
    feats.append({'type': 'Feature',
        'properties': {'kind': 'mountain_label', 'name': name, 'source': source},
        'geometry': {'type': 'Point', 'coordinates': [round(c[0], 5), round(c[1], 5)]}})
    return feats

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    ranges = load_ne_ranges()
    print(f'Natural Earth 纳入: {len(ranges)} 条')
    for n, poly in HAND_RANGES:
        ranges.append({'name': n, 'geom': {'type': 'Polygon', 'coordinates': [[(x, y) for x, y in poly]]},
                       'source': '手工补绘', 'rings': [poly]})
    print(f'含手工补齐后共: {len(ranges)} 条山脉')

    feats = []
    for r in ranges:
        feats.extend(build_features(r['name'], r['rings'], r['geom'], r.get('source', 'Natural Earth 10m')))
    gj = {'type': 'FeatureCollection', 'features': feats}
    json.dump(gj, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    kinds = {}
    for f in feats:
        kinds[f['properties']['kind']] = kinds.get(f['properties']['kind'], 0) + 1
    print(f'输出 → {OUT}')
    print('各类型要素数:', kinds)

if __name__ == '__main__':
    main()
