#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""用 6 个 GCP 做 6 参数仿射，从 pixels.bnd / pixels.seats 重算 徐州 features。
   输出到临时文件并打印诊断，供人工核对后再覆盖。"""
import json, math, os

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, 'viewer', 'han_states_raw', '徐州.geojson')
TMP = os.path.join(HERE, 'viewer', 'han_states_raw', '徐州_regen.geojson')

d = json.load(open(SRC, encoding='utf-8'))
gcps = d['pixels']['gcps']
bnd = d['pixels']['bnd']
seats = d['pixels'].get('seats', [])

assert len(gcps) == 6, f"期望 6 个 GCP，实际 {len(gcps)}"

# ---- 解 6 参数仿射: lon = a0 + a1*px + a2*py ; lat = a3 + a4*px + a5*py ----
# 用两个 3x3 系统 (lon 与 lat 独立)
def solve3(M, B):
    # 高斯消元解 3x3
    n = 3
    A = [row[:] + [B[i]] for i, row in enumerate(M)]
    for col in range(n):
        # 选主元
        piv = max(range(col, n), key=lambda r: abs(A[r][col]))
        A[col], A[piv] = A[piv], A[col]
        pv = A[col][col]
        for j in range(col, n + 1):
            A[col][j] /= pv
        for r in range(n):
            if r != col and A[r][col] != 0:
                f = A[r][col]
                for j in range(col, n + 1):
                    A[r][j] -= f * A[col][j]
    return [A[i][n] for i in range(n)]

# 构造 3x3: [1, px, py] 对 (lon) 和 (lat)
Ml = [[1.0, g['px'], g['py']] for g in gcps]
Blon = [g['lon'] for g in gcps]
Blat = [g['lat'] for g in gcps]
a0, a1, a2 = solve3(Ml, Blon)
a3, a4, a5 = solve3(Ml, Blat)

def fwd(px, py):
    return (a0 + a1 * px + a2 * py, a3 + a4 * px + a5 * py)

# ---- 残差检查 (GCP 反算距离) ----
def dist_km(lon1, lat1, lon2, lat2):
    R = 6371.0
    p1 = math.radians(lat1); p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1); dl = math.radians(lon2 - lon1)
    h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(min(1, math.sqrt(h)))

errs = []
for g in gcps:
    lonp, latp = fwd(g['px'], g['py'])
    errs.append(dist_km(lonp, latp, g['lon'], g['lat']))
max_err = max(errs); avg_err = sum(errs)/len(errs)

# ---- 重投影边界 ----
new_bnd = [list(fwd(px, py)) for px, py in bnd]
lats = [c[1] for c in new_bnd]
lons = [c[0] for c in new_bnd]
lat_min, lat_max = min(lats), max(lats)
lon_min, lon_max = min(lons), max(lons)

# ---- 重投影 seats ----
new_seats = []
for s in seats:
    lon, lat = fwd(s['px'], s['py'])
    new_seats.append({'name': s['name'], 'role': s['role'], 'lon': lon, 'lat': lat})

# ---- 重组 features ----
boundary_feature = {
    'type': 'Feature',
    'properties': {'kind': 'state_boundary', 'state': '徐州'},
    'geometry': {'type': 'Polygon', 'coordinates': [new_bnd]}
}
seat_features = []
for s in new_seats:
    seat_features.append({
        'type': 'Feature',
        'properties': {'kind': 'commandery_seat', 'state': '徐州',
                       'name': s['name'], 'role': s['role'],
                       'lon': s['lon'], 'lat': s['lat']},
        'geometry': {'type': 'Point', 'coordinates': [s['lon'], s['lat']]}
    })
d['features'] = [boundary_feature] + seat_features

# metadata 残差更新
d['metadata']['gcps'] = 6
d['metadata']['max_err_km'] = round(max_err, 1)
d['metadata']['avg_err_km'] = round(avg_err, 1)
d['metadata']['verified'] = True

json.dump(d, open(TMP, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print("=== 仿射参数 ===")
print(f"lon = {a0:.6f} + {a1:.6e}*px + {a2:.6e}*py")
print(f"lat = {a3:.6f} + {a4:.6e}*px + {a5:.6e}*py")
print(f"GCP 残差: max={max_err:.2f}km, avg={avg_err:.2f}km")
print(f"新边界纬度范围: {lat_min:.4f} ~ {lat_max:.4f} N")
print(f"新边界经度范围: {lon_min:.4f} ~ {lon_max:.4f} E")
print(f"seats 数: {len(new_seats)}")
print(f"样例 seats: {[(s['name'], round(s['lat'],3)) for s in new_seats]}")
print(f"已写出临时文件: {TMP}")
