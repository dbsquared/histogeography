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
import rasterio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NE_SHP = os.path.join(BASE_DIR, 'data', 'mountains', 'ne_10m_geography_regions_polys.shp')
OUT = os.path.join(BASE_DIR, 'viewer', 'mountains.geojson')
# 高程栅格(SRTM DEM, EPSG:4326, 用于把山峰图标放到海拔最高处)
DEM_TIF = os.path.join(BASE_DIR, 'rendered', 'china_full_terrain.tif')

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
    # 泰山: 孤立山峰(单峰), 以玉皇顶(~117.10E,36.25N,1545m)为中心的近似圆, 范围很小 → find_peaks 只返回 1 个峰
    ('泰山',     [(117.22,36.25),(117.185,36.335),(117.10,36.37),(117.015,36.335),
                 (116.98,36.25),(117.015,36.165),(117.10,36.13),(117.185,36.165),(117.22,36.25)]),
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

def inside_any(lon, lat, rings):
    return any(pip(lon, lat, ring) for ring in rings)

def find_peaks(rings, dem_arr, transform, bounds, nodata):
    """在山脉面内采样 DEM 数组, 返回 3 个海拔最高且彼此相距 >= MIN_SEP 的点 [lon,lat]。
    dem_arr=None 或面超出 DEM 范围时返回 [] → 由 JS 退回质心±走向放置。
    像素↔经纬度用纯仿射数学换算(不调用 rasterio.transform, 避免大循环泄漏)。"""
    if dem_arr is None:
        return []
    H, W = dem_arr.shape
    a = transform.a; e = transform.e; tc = transform.c; tf = transform.f
    xs = [p[0] for ring in rings for p in ring]; ys = [p[1] for ring in rings for p in ring]
    lon0, lon1, lat0, lat1 = min(xs), max(xs), min(ys), max(ys)
    lon0 = max(lon0, bounds.left); lon1 = min(lon1, bounds.right)
    lat0 = max(lat0, bounds.bottom); lat1 = min(lat1, bounds.top)
    if lon1 <= lon0 or lat1 <= lat0:
        return []
    # 包围盒四角(经纬度) → 像素索引(纯仿射), 夹到数组范围
    col_tl = (lon0 - tc) / a; row_tl = (lat1 - tf) / e   # 左上角=最小lon/最大lat
    col_br = (lon1 - tc) / a; row_br = (lat0 - tf) / e   # 右下角=最大lon/最小lat
    r0 = max(0, int(math.floor(min(row_tl, row_br)))); r1 = min(H - 1, int(math.ceil(max(row_tl, row_br))))
    c0 = max(0, int(math.floor(min(col_tl, col_br)))); c1 = min(W - 1, int(math.ceil(max(col_tl, col_br))))
    if r1 < r0 or c1 < c0:
        return []
    sub = dem_arr[r0:r1 + 1, c0:c1 + 1]
    wa, we, wc, wf = a, e, tc + c0 * a, tf + r0 * e   # sub 窗口仿射
    rows, cols = sub.shape
    step = max(1, int(math.ceil(max(cols, rows) / 500)))  # 限制候选点数量
    cands = []
    for r in range(0, rows, step):
        lat = wf + r * we
        for c in range(0, cols, step):
            ev = int(sub[r, c])
            if nodata is not None and ev == nodata:
                continue
            if ev <= 0:
                continue
            lon = wc + c * wa
            if not inside_any(lon, lat, rings):
                continue
            cands.append((ev, lon, lat))
    if not cands:
        return []
    cands.sort(reverse=True)  # 按海拔降序
    MIN_SEP = 0.3
    picked = []
    for ev, lon, lat in cands:
        if all(math.hypot(lon - plon, lat - plat) >= MIN_SEP for plon, plat in picked):
            picked.append((lon, lat))
            if len(picked) >= 3:
                break
    return [[round(x, 5), round(y, 5), int(e)] for x, y, e in picked]

def build_features(name, rings, geom, source='Natural Earth 10m', dem=None):
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
    # 山峰图标实际坐标: 面内 DEM 最高的点(彼此分开) → 图标尽量落在海拔最高处
    peaks_raw = find_peaks(rings, dem[0], dem[1], dem[2], dem[3]) if dem else []
    peaks = [[round(p[0], 5), round(p[1], 5)] for p in peaks_raw]
    max_elev = int(peaks_raw[0][2]) if peaks_raw else None
    # 标签点(质心, 作为 JS 无 DEM 峰值时的退回方案)
    lbl_props = {'kind': 'mountain_label', 'name': name, 'source': source}
    if max_elev is not None:
        lbl_props['max_elev'] = max_elev
    feats.append({'type': 'Feature',
        'properties': lbl_props,
        'geometry': {'type': 'Point', 'coordinates': [round(c[0], 5), round(c[1], 5)]}})
    if peaks:
        pk_props = {'kind': 'mountain_peaks', 'name': name, 'source': source}
        if max_elev is not None:
            pk_props['max_elev'] = max_elev
        feats.append({'type': 'Feature',
            'properties': pk_props,
            'geometry': {'type': 'MultiPoint', 'coordinates': peaks}})
    return feats

def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    dem = None
    if os.path.exists(DEM_TIF):
        try:
            ds = rasterio.open(DEM_TIF)
            print(f'已载入 DEM: {DEM_TIF}  (bounds {ds.bounds})')
            dem = (ds.read(1), ds.transform, ds.bounds, ds.nodata)  # 整张数组一次读入, 避免逐山脉窗口读取
            ds.close()
        except Exception as e:
            print('DEM 载入失败, 退回质心±走向放置:', e)
    else:
        print('未找到 DEM, 退回质心±走向放置')
    ranges = load_ne_ranges()
    print(f'Natural Earth 纳入: {len(ranges)} 条')
    for n, poly in HAND_RANGES:
        ranges.append({'name': n, 'geom': {'type': 'Polygon', 'coordinates': [[(x, y) for x, y in poly]]},
                       'source': '手工补绘', 'rings': [poly]})
    print(f'含手工补齐后共: {len(ranges)} 条山脉')

    feats = []
    for r in ranges:
        feats.extend(build_features(r['name'], r['rings'], r['geom'], r.get('source', 'Natural Earth 10m'), dem))
    gj = {'type': 'FeatureCollection', 'features': feats}
    json.dump(gj, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    kinds = {}
    for f in feats:
        kinds[f['properties']['kind']] = kinds.get(f['properties']['kind'], 0) + 1
    print(f'输出 → {OUT}')
    print('各类型要素数:', kinds)
    # 报告每条山脉找到的峰数(0 表示退回质心方案)
    pn = sum(1 for f in feats if f['properties'].get('kind') == 'mountain_peaks')
    print(f'带 DEM 峰值坐标的山脉: {pn}/{len(ranges)}')

if __name__ == '__main__':
    main()
