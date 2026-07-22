# -*- coding: utf-8 -*-
import json, os
WORK=r'E:\projects\3D地图制作'
gj=os.path.join(WORK,'viewer','thirteen_states.geojson')
d=json.load(open(gj,'r',encoding='utf-8'))
feats=d['features']
states=[f for f in feats if f['properties'].get('kind')=='thirteen_states']
cities=[f for f in feats if f['properties'].get('kind')=='ancient_city']
print(f'Total features: {len(feats)} | states: {len(states)} | cities: {len(cities)}')
names=[s['properties']['state_name'] for s in states]
print('States present:', names)
expected=['凉州','益州','司隶','并州','冀州','青州','幽州','兖州','豫州','徐州','扬州','荆州','交州']
missing=[n for n in expected if n not in names]
print('Missing:', missing or 'NONE')
# validity + distinctness
rings={}
dups=[]
for s in states:
    ring=s['geometry']['coordinates'][0]
    n=len(ring)
    closed = ring[0]==ring[-1]
    ok = n>=4 and closed
    key=tuple(tuple(round(c,4) for c in pt) for pt in ring)
    print(f"  {s['properties']['state_name']:4s} verts={n:>6d} closed={closed} valid={ok} "
          f"area_px={s['properties'].get('trace_area_px')} method={s['properties'].get('extraction_detail')}")
    if key in rings: dups.append((s['properties']['state_name'], rings[key]))
    else: rings[key]=s['properties']['state_name']
print('\nDuplicate rings:', dups or 'NONE')
# bbox sanity
import math
lons=[pt[0] for s in states for pt in s['geometry']['coordinates'][0]]
lats=[pt[1] for s in states for pt in s['geometry']['coordinates'][0]]
print(f'Bbox lon[{min(lons):.2f},{max(lons):.2f}] lat[{min(lats):.2f},{max(lats):.2f}]')
print('VALID' if (not missing and not dups and all(
    len(s['geometry']['coordinates'][0])>=4 for s in states)) else 'CHECK FAILED')
