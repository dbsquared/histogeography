#!/usr/bin/env python3
"""
auto_discover_colors.py — K-means自动发现13州真实颜色 + 地理定位映射
对overview_13states.png全体像素跑K-means(K=15)，按颜色+位置自动识别每州
输出：可直接用于trace_v23的COLORS字典 + 验证可视化
"""
import json, os
import numpy as np
from PIL import Image
from sklearn.cluster import MiniBatchKMeans

HERE = os.path.dirname(os.path.abspath(__file__))
OV_IMG = os.path.join(HERE, 'viewer', 'overview_13states.png')
GCP_JSON = os.path.join(HERE, 'gcp_calibration_13states.json')

# ── 加载校准 ──
with open(GCP_JSON, 'r', encoding='utf-8') as _f:
    cal = json.load(_f)
M_lon = np.array(cal['transform']['M_lon'])
M_lat = np.array(cal['transform']['M_lat'])

def p2ll(px, py):
    return float(M_lon[0]*px + M_lon[1]*py + M_lon[2]), \
           float(M_lat[0]*px + M_lat[1]*py + M_lat[2])

# ── 加载图像 ──
img = Image.open(OV_IMG).convert('RGB')
W, H = img.size
arr = np.asarray(img, dtype=np.float32).reshape(-1, 3)
print(f'图像: {W}x{H} = {len(arr):,} 像素')

# ── K-means K=15 (13州 + 海洋 + 背景) ──
K = 15
print(f'\nK-means K={K}...')
km = MiniBatchKMeans(n_clusters=K, n_init=5, random_state=42, batch_size=8192,
                       reassignment_ratio=0.01)
labels = km.fit_predict(arr)
centers = km.cluster_centers_.astype(int)

print(f'\n聚类中心:')
for c in range(K):
    cnt = int((labels == c).sum())
    print(f'  [{c:2d}] RGB({centers[c,0]:3d},{centers[c,1]:3d},{centers[c,2]:3d}) '
          f'{cnt:>9,d}px ({cnt/len(arr)*100:5.2f}%)')

# ── 每聚类的地理质心 ──
lbl_img = labels.reshape(H, W)
print(f'\n地理质心 (lon,lat) + 包围盒:')
cluster_info = []
for c in range(K):
    ys, xs = np.where(lbl_img == c)
    if len(xs) == 0:
        continue; continue
    n = len(xs)
    # 地理质心 (采样以加速)
    step = max(1, n // 500)
    lons, lats = [], []
    for i in range(0, n, step):
        lo, la = p2ll(float(xs[i]), float(ys[i]))
        lons.append(lo); lats.append(la)
    glon = round(float(np.mean(lons)), 2) if lons else 0
    glat = round(float(np.mean(lats)), 2) if lats else 0
    # 像素包围盒
    x0, x1 = int(xs.min()), int(xs.max())
    y0, y1 = int(ys.min()), int(ys.max())
    cluster_info.append({
        'cid': c, 'rgb': tuple(centers[c].tolist()), 'n': n,
        'pct': round(n / len(arr) * 100, 2),
        'geo_center': (glon, glat),
        'bbox': (x0, y0, x1, y1),
    })
    print(f'  [{c:2d}] ({centers[c,0]:3d},{centers[c,1]:3d},{centers[c,2]:3d}) '
          f'{n:>9,d}px {n/len(arr)*100:5.2f}%  geo({glon:.1f},{glat:.1f}) '
          f'bbox({x0},{y0},{x1},{y1})')

# 按大小排序
cluster_info.sort(key=lambda x: -x['n'])

# ── 自动分类：海洋 / 背景 / 州 ──
print(f'\n=== 自动归类 ===')
OCEAN_CID = None   # 最大蓝色簇
BG_CID = None      # 最大近白簇
STATE_CLUSTERS = []

for ci in cluster_info:
    r, g, b = ci['rgb']
    # 海洋判断：蓝色主导，大范围
    is_ocean = (b > r + 30 and b > g + 20 and ci['n'] > 200000)
    # 背景判断：接近白色/米色，大范围
    is_bg = (r > 205 and g > 200 and b > 195 and ci['n'] > 50000 and not is_ocean)

    if is_ocean:
        OCEAN_CID = ci['cid']
        label_name = '🌊 OCEAN'
    elif is_bg:
        BG_CID = ci['cid']
        label_name = '⬜ BACKGROUND'
    else:
        STATE_CLUSTERS.append(ci)
        label_name = f'❓ 州候选'

    print(f'  [{ci["cid"]:2d}] {label_name:14s} RGB{ci["rgb"]} '
          f'{ci["n"]:,}px ({ci["pct"]}%) geo{ci["geo_center"]}')

# ── 手动映射：根据地理位置将州候选→州名 ──
# 已知各州大致地理位置：
STATE_GEO = {
    '凉州':   ('NW', 102, 38),    # 西北
    '益州':   ('SW', 104, 31),    # 西南
    '司隶':   ('CN', 111, 35),    # 中央偏北
    '并州':   ('N',  112, 38),    # 北
    '冀州':   ('NE', 115, 37),    # 北偏东
    '青州':   ('E',  118, 37),    # 东
    '幽州':   ('NE2', 120, 41),   # 最东北
    '兖州':   ('C',  114, 35),    # 中央
    '豫州':   ('CS', 113, 34),    # 中南
    '徐州':   ('CE', 117, 34),    # 中东偏南
    '扬州':   ('SE', 119, 32),    # 东南
    '荆州':   ('S',  112, 30),    # 南中
    '交州':   ('S2', 110, 22),    # 最南
}

def geo_dist(cinfo, target_lon, target_lat):
    """计算聚类质心到目标位置的欧氏距离"""
    cl, ca = cinfo['geo_center']
    return ((cl - target_lon)**2 + (ca - target_lat)**2)**0.5

print(f'\n=== 州名映射 ===')
mapped = {}  # state_name -> cluster_info
used_cids = set()

for sn, (region, tlon, tlat) in sorted(STATE_GEO.items(),
                                          key=lambda x: -abs(x[1][1]-112)):
    # 找最近的未使用州候选
    best = None
    best_d = 999
    for ci in STATE_CLUSTERS:
        if ci['cid'] in used_cids:
            continue
        d = geo_dist(ci, tlon, tlat)
        if d < best_d:
            best_d = d
            best = ci
    if best:
        mapped[sn] = best
        used_cids.add(best['cid'])
        print(f'  {sn:4s} ← 簇[{best["cid"]:2d}] RGB{best["rgb"]} '
              f'{best["n"]:,}px geo{best["geo_center"]} d={best_d:.1f}')
    else:
        print(f'  {sn:4s}: ⚠️ 无可用簇!')

# 未被映射的簇
unmapped = [ci for ci in STATE_CLUSTERS if ci['cid'] not in used_cids]
if unmapped:
    print(f'\n  未映射的 {len(unmapped)} 个簇:')
    for ci in unmapped:
        print(f'    簇[{ci["cid"]:2d}] RGB{ci["rgb"]} {ci["n"]:,}px geo{ci["geo_center"]}')

# ── 输出最终调色板 ──
print(f'\n=== 最终调色板 ===')
final_colors = {}
for sn, ci in mapped.items():
    final_colors[sn] = ci['rgb']
    print(f"  '{sn}': {list(ci['rgb'])},  # 簇[{ci['cid']}] "
          f'{ci["n"]:,}px ({ci["pct"]}%) geo{ci["geo_center"]}')

if OCEAN_CID is not None:
    oc = centers[OCEAN_CID]
    print(f"  # OCEAN: {tuple(oc.tolist())}  [簇[{OCEAN_CID}]]")
else:
    print(f"  # ⚠️ 未识别海洋!")
if BG_CID is not None:
    bc = centers[BG_CID]
    print(f"  # WHITE/BACKGROUND: {tuple(bc.tolist())}  [簇[{BG_CID}]]")
else:
    print(f"  # ⚠️ 未识别背景!")

# ── 可视化：每个聚类独立颜色显示 ──
import cv2
vis = np.zeros((H, W, 3), dtype=np.uint8)
np.random.seed(42)
vis_colors = np.random.randint(40, 220, (K, 3), dtype=np.uint8)
# 给海洋设为深蓝，背景设为浅灰
if OCEAN_CID is not None:
    vis_colors[OCEAN_CID] = [40, 80, 160]
if BG_CID is not None:
    vis_colors[BG_CID] = [220, 218, 215]

for c in range(K):
    vis[lbl_img == c] = vis_colors[c]

Image.fromarray(vis).save(os.path.join(HERE, 'kmeans15_vis.png'))
print(f'\n已保存 kmeans15_vis.png')

# ── 输出可直接复制的Python COLORS字典 ──
print(f'\n{"="*60}')
print('# 可直接复制到 trace_v23.py 的 COLORS 字典:')
print('COLORS_AUTO = {')
for sn in list(final_colors.keys()):
    pass
for sn, rgb in final_colors.items():
    print(f"    '{sn}': {list(rgb)},")
print('}')
oc_str = str(tuple(oc.tolist())) if OCEAN_CID is not None else "(?, ?, ?)"
bc_str = str(tuple(bc.tolist())) if BG_CID is not None else "(?, ?, ?)"
print(f'OCEAN_COLOR_AUTO = {oc_str}')
print(f'WHITE_COLOR_AUTO  = {bc_str}')
