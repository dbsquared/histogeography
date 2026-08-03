#!/usr/bin/env python3
"""
build_han_states.py — 把 han_states_raw/*.geojson 合并为 viewer/han_states.js
输出 window.HAN_STATES = {meta, states:[{name,color,boundary,seats}]}
"""
import json, os, glob

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(HERE, 'viewer', 'han_states_raw')
OUT = os.path.join(HERE, 'viewer', 'han_states.js')

# role 字段标准化（兼容用户混输中英文）
ROLE_NORM = {
    'capital':     'capital',
    '州治':        'capital',
    '州府':        'capital',
    'commandery':  'commandery',
    '郡治':        'commandery',
    'major':       'major',
    '主要城':      'major',
    'fortress':    'fortress',
    '要塞':        'fortress',
}

states = []
files = sorted(glob.glob(os.path.join(RAW_DIR, '*.geojson')))
if not files:
    print(f'ERROR: {RAW_DIR} 下没有 .geojson 文件')
    raise SystemExit(1)

for fp in files:
    d = json.load(open(fp, encoding='utf-8'))
    meta = d.get('metadata', {})
    state_name = meta.get('state')
    color = meta.get('color', '#888888')
    boundary = None
    seats = []
    for f in d['features']:
        k = f['properties'].get('kind')
        if k == 'state_boundary':
            boundary = f['geometry']['coordinates'][0]  # [[lon,lat],...]
        elif k == 'commandery_seat':
            p = f['properties']
            role_raw = p.get('role', 'commandery')
            role = ROLE_NORM.get(role_raw, 'commandery')
            # 兼容两种坐标存储：properties.lon/lat 或 geometry.coordinates(Point=[lon,lat])
            if 'lon' in p and 'lat' in p:
                lon, lat = p['lon'], p['lat']
            else:
                coords = f['geometry']['coordinates']
                lon, lat = coords[0], coords[1]
            seats.append({
                'name': p['name'],
                'role': role,
                'lon': lon,
                'lat': lat,
            })
    if boundary is None:
        print(f'WARN: {state_name} 缺 state_boundary，跳过')
        continue
    states.append({
        'name': state_name,
        'color': color,
        'boundary': boundary,
        'seats': seats,
        'meta': {
            'gcps': meta.get('gcps'),
            'max_err_km': meta.get('max_err_km'),
            'avg_err_km': meta.get('avg_err_km'),
            'verified': meta.get('verified', False),
        }
    })
    print(f'  ✓ {state_name}: boundary={len(boundary)}v, seats={len(seats)}, err={meta.get("max_err_km")}km')

payload = {
    'meta': {
        'title': '汉末十三州（基于交互式打点重建）',
        'count': len(states),
        'generated_by': 'digitize_v2.html + build_han_states.py',
    },
    'states': states,
}

js = 'window.HAN_STATES = ' + json.dumps(payload, ensure_ascii=False) + ';\n'
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(js)
print(f'\n✓ 输出 {OUT} ({os.path.getsize(OUT):,} bytes, {len(states)} 州)')
