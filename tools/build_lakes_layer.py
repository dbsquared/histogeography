# -*- coding: utf-8 -*-
"""
生成 viewer/lakes.geojson —— 主要湖泊矢量图层(面, 可切换)
数据源: Natural Earth 10m Lakes (public domain), data/lakes/ne_10m_lakes.shp
中文名直接用数据源 name_zh 字段( Natural Earth 提供), 回退 name(英文名)
范围: 72-140°E / 15-55°N (与 rivers/mountains 一致)
属性: kind='lake', name(中文), scalerank, major, label
依赖: pyshp (shapefile)
"""
import json, os
import shapefile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE_DIR, 'data', 'lakes', 'ne_10m_lakes.shp')
OUT = os.path.join(BASE_DIR, 'viewer', 'lakes.geojson')

LON_MIN, LON_MAX = 72.0, 140.0
LAT_MIN, LAT_MAX = 15.0, 55.0

INCLUDE_MAX_SCALERANK = 6      # 纳入阈值(主要湖泊)
LABEL_SCALERANK = 4            # 自动标注阈值(主要湖才标文字)
MAJOR_SCALERANK = 2            # 重点渲染阈值(粗边/重点)

# 中国主要湖泊白名单(确保主要+标注, 覆盖 NE 中文名可能缺失或 scalerank 偏高者)
CHINA_MAJOR_LAKES = {
    '青海湖', '鄱阳湖', '洞庭湖', '太湖', '洪泽湖', '巢湖', '呼伦湖', '贝尔湖', '兴凯湖',
    '纳木错', '色林错', '羊卓雍错', '滇池', '洱海', '抚仙湖', '博斯腾湖', '艾比湖', '呼倫湖',
    '密云水库', '千岛湖', '洪湖', '南四湖', '白洋淀', '微山湖', '日月潭', '茶卡盐湖',
    '察尔汗盐湖', '扎龙湖', '镜泊湖', '五大连池', '松花湖',
}
LABEL_LAKES = CHINA_MAJOR_LAKES

# 手工补齐 NE 10m lakes 未收录的中国主要湖(简化面, 基于已知经纬度范围)
# 10m 比例尺下云南高原湖群(滇池/洱海/抚仙湖等)缺失, 仿 mountains 脚本 HAND_RANGES 方式补绘
HAND_LAKES = [
    ('滇池',   [(102.60, 24.72), (102.98, 24.72), (102.95, 24.98), (102.62, 24.98)]),
    ('洱海',   [(99.92, 25.60), (100.30, 25.62), (100.28, 25.92), (99.90, 25.90)]),
    ('抚仙湖', [(102.83, 24.34), (103.00, 24.34), (103.00, 24.62), (102.83, 24.62)]),
    ('泸沽湖', [(100.62, 27.66), (100.78, 27.66), (100.80, 27.74), (100.60, 27.74)]),
    ('程海',   [(100.60, 26.50), (100.75, 26.50), (100.75, 26.62), (100.60, 26.62)]),
    ('星云湖', [(102.68, 24.28), (102.78, 24.28), (102.78, 24.38), (102.68, 24.38)]),
    ('阳宗海', [(102.93, 24.82), (103.03, 24.82), (103.03, 24.95), (102.93, 24.95)]),
    ('异龙湖', [(102.42, 23.68), (102.55, 23.68), (102.55, 23.78), (102.42, 23.78)]),
]


def in_extent(bb):
    """是否与地图范围重叠"""
    return not (bb[2] < LON_MIN or bb[0] > LON_MAX or bb[3] < LAT_MIN or bb[1] > LAT_MAX)


def poly_geom(shape, pts):
    """pyshp parts/points → GeoJSON 几何; 正确区分 Polygon 的外环与洞"""
    parts = shape.parts
    rings = []
    for k in range(len(parts)):
        s = parts[k]
        e = parts[k + 1] if k + 1 < len(parts) else len(pts)
        rings.append([[round(x, 4), round(y, 4)] for x, y in pts[s:e]])
    st = shape.shapeType
    if st in (5, 15, 25):          # Polygon / PolygonZ / PolygonM
        return {'type': 'Polygon', 'coordinates': rings}   # 第1环=outer, 其余=holes
    return {'type': 'MultiPolygon', 'coordinates': [[r] for r in rings]}


def main():
    sf = shapefile.Reader(SRC)
    feats = []
    n_incl = 0
    for i in range(len(sf.shapes())):
        r = sf.record(i).as_dict()
        # 注: NE 湖泊 featurecla 含 'Lake'/'Alkaline Lake'/'Salt Lake'/'Playa'/'Reservoir' 等,
        # 本图层统一纳入(均为水体), 由 scalerank+白名单控制主要程度
        name_zh = r.get('name_zh') or ''
        name_en = r.get('name') or ''
        cn = name_zh if name_zh else name_en
        if not cn:
            continue
        in_white = cn in CHINA_MAJOR_LAKES
        sr = r.get('scalerank')
        # 白名单中的中国名湖无视 scalerank 阈值强制纳入
        if sr is None or (sr > INCLUDE_MAX_SCALERANK and not in_white):
            continue
        geom = sf.shape(i)
        if not in_extent(geom.bbox):
            continue
        g = poly_geom(geom, geom.points)
        major = (sr <= MAJOR_SCALERANK) or (cn in CHINA_MAJOR_LAKES)
        label = (sr <= LABEL_SCALERANK) or (cn in LABEL_LAKES)
        feats.append({
            'type': 'Feature',
            'properties': {
                'kind': 'lake',
                'name': cn,
                'scalerank': sr,
                'major': major,
                'label': label,
            },
            'geometry': g,
        })
        n_incl += 1
    sf.close()

    # 手工补齐湖(强制主要+标注)
    for name, poly in HAND_LAKES:
        feats.append({
            'type': 'Feature',
            'properties': {'kind': 'lake', 'name': name, 'scalerank': 4,
                           'major': True, 'label': True, 'source': 'hand'},
            'geometry': {'type': 'Polygon',
                         'coordinates': [[[round(x, 4), round(y, 4)] for x, y in poly]]},
        })
        n_incl += 1
    out = {'type': 'FeatureCollection', 'features': feats}
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    named = sum(1 for f in feats if f['properties']['name'])
    labeled = sum(1 for f in feats if f['properties']['label'])
    majors = sum(1 for f in feats if f['properties']['major'])
    print('OK lakes.geojson: 纳入 %d 个湖 (主要 %d, 命名 %d, 带标签 %d)' % (n_incl, majors, named, labeled))
    for f in sorted(feats, key=lambda x: x['properties']['scalerank']):
        if f['properties']['major']:
            print('  [sr%s%s] %s' % (f['properties']['scalerank'],
                                     ' L' if f['properties']['label'] else '  ',
                                     f['properties']['name']))


if __name__ == '__main__':
    main()
