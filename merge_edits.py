#!/usr/bin/env python3
"""把 D:/downloads/all_states_edit.json 的手动校正结果合并回 viewer/han_states_raw/{州}.geojson。
保留原文件的 pixels / metadata（含 verified、color、err），仅用导出的 features 覆盖 state_boundary 与 commandery_seat。
按"state_boundary 之后紧跟其 commandery_seat"的顺序把 seat 关联到所属州。
"""
import json, os, copy

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, 'viewer', 'han_states_raw')
EXP = 'D:/downloads/all_states_edit.json'

exp = json.load(open(EXP, encoding='utf-8'))
feats = exp['features']

# 1) 按出现顺序把 boundary / seats 关联到州
per_state = {}  # name -> {'bnd':feature, 'seats':[feature...]}
cur = None
for f in feats:
    k = f['properties'].get('kind')
    if k == 'state_boundary':
        cur = f['properties'].get('state')
        per_state.setdefault(cur, {'bnd': None, 'seats': []})
        per_state[cur]['bnd'] = f
    elif k == 'commandery_seat':
        if cur is None:
            raise SystemExit('ERROR: commandery_seat 出现在任何 state_boundary 之前')
        per_state[cur]['seats'].append(f)
    else:
        print('忽略未知 kind:', k)

print(f'导出覆盖 {len(per_state)} 个州')

# 2) 逐州合并
for name, data in per_state.items():
    fp = os.path.join(RAW, f'{name}.geojson')
    if not os.path.exists(fp):
        print(f'⚠ 找不到 {fp}，跳过'); continue
    d = json.load(open(fp, encoding='utf-8'))
    old_feats = d.get('features', [])
    # 恢复原有 seat 的 role（按 name 匹配）
    role_by_name = {}
    for of in old_feats:
        if of.get('properties', {}).get('kind') == 'commandery_seat':
            role_by_name[of['properties'].get('name')] = of['properties'].get('role', 'commandery')

    new_feats = []
    # state_boundary
    bnd = data['bnd']
    ring = bnd['geometry']['coordinates'][0]
    if ring and ring[0] != ring[-1]:
        ring = ring + [ring[0]]
    bnd_feat = {
        'type': 'Feature',
        'properties': {'kind': 'state_boundary', 'state': name},
        'geometry': {'type': 'Polygon', 'coordinates': [ring]},
    }
    new_feats.append(bnd_feat)
    # commandery_seat
    for sf in data['seats']:
        nm = sf['properties'].get('name')
        coords = sf['geometry']['coordinates']
        lon, lat = coords[0], coords[1]
        role = role_by_name.get(nm, 'commandery')
        new_feats.append({
            'type': 'Feature',
            'properties': {'kind': 'commandery_seat', 'name': nm, 'role': role},
            'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
        })
    d['features'] = new_feats
    json.dump(d, open(fp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'  ✓ {name}: {len(ring)}v boundary, {len(data["seats"])} seats')

print('合并完成。下一步运行 build_han_states.py')
