# -*- coding: utf-8 -*-
"""
生成 viewer/provinces.geojson
数据源(均遵循中国自然资源部标准地图):
  - 国界/省界: Supeset/China-GeoData (含完整藏南-达旺/珞瑜/下察隅/墨脱南 与 阿克赛钦, MIT)
  - 南海断续线: geojson.cn 十段线 (引自民政部 xzqh.mca.gov.cn)
注: 原 DATAV 数据沿麦克马洪线将藏南划出; 本版改用 Supeset 以纳入完整藏南。
"""
import json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
NATIONAL = os.path.join(ROOT, 'data/cn_official/supeset_national.geojson')
PROVINCES = os.path.join(ROOT, 'data/cn_official/supeset_provinces.geojson')
OUT = os.path.join(ROOT, 'viewer/provinces.geojson')

# ---- 十段线 (geojson.cn, 引自民政部) ----
TEN_DASH = [
    [[109.51763678906526,16.360467782665847],[109.72339159230361,16.05587198177934],
     [109.8780414893003,15.766823920473868],[109.96506402665503,15.526031073258686],
     [109.98526818797363,15.335615618596712]],
    [[110.48331454715199,12.431407837351566],[110.48240767589328,12.085792287259398],
     [110.45136562643113,11.863835000833953],[110.25652028695671,11.393616070326182]],
    [[108.3388949586325,7.26656318024262],[108.30727608084116,6.727803403200289],
     [108.35631901989032,6.112648053307836]],
    [[111.94112275674237,3.553559321848772],[112.40151782268552,3.646409974664658],
     [112.92104341055976,3.845112027649191]],
    [[115.69079809651517,7.29016984601141],[116.4095482213759,8.137962397303875]],
    [[118.63503455703679,11.080904139262175],[118.85587024190139,11.457907321145406],
     [119.10128629647166,12.062751715859875],[119.12181771101825,12.135585760471585]],
    [[119.60808384544805,18.143451232827125],[119.91075760817219,18.77194701315816],
     [120.11918953031866,19.117669954512905]],
    [[121.40591812413318,20.8001943859176],[122.12216430894797,21.716094829922323]],
    [[122.80328441666389,23.665545127578547],[123.00481138309124,24.74934291726869]],
    [[119.16836075308866,15.107448879733406],[119.16981236678279,15.755038547478351],
     [119.17823197590195,16.265658015720753]],
]

def short_name(full):
    n = full or ''
    n = (n.replace('维吾尔自治区','').replace('壮族自治区','').replace('回族自治区','')
           .replace('自治区','').replace('特别行政区','').replace('省','')
           .replace('市',''))
    return n

# ---- 省标签像素级微调 ----
# (dx, dy) 为文字相对地理锚点的偏移(单位px); 所有缩放级别下此偏移量恒定(Leaflet divIcon
# 以像素定位), 故缩放时不会漂移。 dx>0 文字右移, dy>0 文字下移。
# 应用方式: iconAnchor = [60-dx, 8-dy]  (容器 120x16, 中心 [60,8], 文字 flex 居中)
LABEL_OFFSET = {
    '江苏': (18, 0),    # 往右
    '河北': (18, 0),    # 往右
    '福建': (-18, 0),   # 往左
    '宁夏': (0, 14),    # 往下
}

features = []

# 1) 中国国界 (Supeset/China-GeoData, 遵循自然资源部标准地图: 含完整藏南-达旺/珞瑜/下察隅/墨脱南 与 阿克赛钦)
nat = json.load(open(NATIONAL, encoding='utf-8'))
nat_geom = nat['features'][0]['geometry']
features.append({'type':'Feature',
    'properties':{'kind':'country_border','name_zh':'中国国界'},
    'geometry': nat_geom})

# 2) 省级行政区
prov = json.load(open(PROVINCES, encoding='utf-8'))
n_prov = 0
for f in prov['features']:
    p = f.get('properties', {})
    full = p.get('name') or ''
    if not full:
        continue  # 跳过空名要素(原九段线 JD, 由 geojson.cn 十段线替代)
    adcode = p.get('adcode')
    geom = f['geometry']
    name = short_name(full)
    center = p.get('center') or p.get('centroid')
    if center and isinstance(center, list) and len(center) == 2 and (center[0] or center[1]) \
            and (70 <= float(center[0]) <= 140) and (3 <= float(center[1]) <= 55):
        lon, lat = float(center[0]), float(center[1])
    else:
        def first_pt(c):
            return c[0] if (isinstance(c[0], (int,float)) and isinstance(c[1], (int,float))) else first_pt(c[0])
        pt0 = first_pt(geom['coordinates'])
        lon, lat = float(pt0[0]), float(pt0[1])
    dx, dy = LABEL_OFFSET.get(name, (0, 0))
    features.append({'type':'Feature',
        'properties':{'kind':'province','name_zh':name,'name_full':full,
                      'label_lon':round(lon,4),'label_lat':round(lat,4),
                      'label_dx':dx,'label_dy':dy,
                      'border_red':(name=='台湾省')},
        'geometry':{'type':geom['type'],'coordinates':geom['coordinates']}})
    n_prov += 1

# 3) 十段线
features.append({'type':'Feature',
    'properties':{'kind':'nine_dash','name_zh':'十段线',
                  'label_lon':119.0,'label_lat':16.2},
    'geometry':{'type':'MultiLineString','coordinates':TEN_DASH}})

gj = {'type':'FeatureCollection','features':features}
json.dump(gj, open(OUT,'w',encoding='utf-8'), ensure_ascii=False)
print('OK provinces.geojson: 国界1 + 省级%d + 十段线1 = 共%d 要素' % (n_prov, len(features)))
