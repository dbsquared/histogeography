#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""扫描 han_states_raw/*.geojson，输出州际「重叠」与「缝隙」多边形，
供 edit_states_terrain.html 作为问题高亮图层加载。

产物: viewer/seam_issues.js  ->  window.SEAM_ISSUES = {overlaps:[...], gaps:[...]}
每个元素: {km2: <float>, states: [州名...], ring: [[lat,lon],...]}
"""
import json
import glob
import math
import os

from shapely.geometry import Polygon
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'han_states_raw')
OUT = os.path.join(HERE, 'seam_issues.js')

MIN_OVERLAP_KM2 = 200.0   # 小于此面积视为贴边毛刺，忽略
MIN_GAP_KM2 = 200.0


def load_ring(path):
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    for ft in data['features']:
        props = ft.get('properties', {})
        if props.get('kind') == 'state_boundary' or props.get('type') == 'state_boundary':
            g = ft['geometry']['coordinates']
            while isinstance(g[0][0], list):
                g = g[0]
            return [(p[0], p[1]) for p in g]
    return None


def km2(poly):
    if poly.is_empty:
        return 0.0
    lat = poly.centroid.y
    return poly.area * 111.32 * 110.57 * math.cos(math.radians(lat))


def to_latlon_ring(poly):
    return [[y, x] for x, y in poly.exterior.coords]


def explode(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    if geom.geom_type in ('MultiPolygon', 'GeometryCollection'):
        out = []
        for g in geom.geoms:
            out.extend(explode(g))
        return out
    return []


def main():
    states = {}
    for path in sorted(glob.glob(os.path.join(RAW, '*.geojson'))):
        name = os.path.splitext(os.path.basename(path))[0]
        ring = load_ring(path)
        if ring:
            states[name] = Polygon(ring).buffer(0)
    print('loaded states: %d' % len(states))

    names = sorted(states)
    overlaps = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            inter = states[a].intersection(states[b])
            for part in explode(inter):
                area = km2(part)
                if area >= MIN_OVERLAP_KM2:
                    overlaps.append({'km2': round(area, 1), 'states': [a, b],
                                     'ring': to_latlon_ring(part)})
    overlaps.sort(key=lambda d: -d['km2'])

    union = unary_union(list(states.values()))
    gaps = []
    for pg in explode(union):
        for interior in pg.interiors:
            hole = Polygon(interior)
            area = km2(hole)
            if area < MIN_GAP_KM2:
                continue
            touching = sorted(
                (n for n in names if states[n].distance(hole) < 1e-6),
                key=lambda n: states[n].distance(hole))
            if not touching:
                touching = sorted(names, key=lambda n: states[n].distance(hole))[:3]
            gaps.append({'km2': round(area, 1), 'states': touching,
                         'ring': to_latlon_ring(hole)})
    gaps.sort(key=lambda d: -d['km2'])

    payload = {
        'overlaps': overlaps,
        'gaps': gaps,
        'summary': {
            'overlap_count': len(overlaps),
            'overlap_km2': round(sum(o['km2'] for o in overlaps), 1),
            'gap_count': len(gaps),
            'gap_km2': round(sum(g['km2'] for g in gaps), 1),
        },
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('window.SEAM_ISSUES = ')
        json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';\n')
    print('overlaps >=%dkm2: %d (%.0f km2)' % (MIN_OVERLAP_KM2, len(overlaps),
                                               payload['summary']['overlap_km2']))
    print('gaps     >=%dkm2: %d (%.0f km2)' % (MIN_GAP_KM2, len(gaps),
                                               payload['summary']['gap_km2']))
    print('wrote %s (%.1f KB)' % (OUT, os.path.getsize(OUT) / 1024))


if __name__ == '__main__':
    main()
