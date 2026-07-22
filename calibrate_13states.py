#!/usr/bin/env python3
"""
calibrate_13states.py — 为 overview_13states.png 构建专用GCP仿射校准
方法：从参考图上识别历史城市位置(像素坐标) + 已知现代经纬度 → 最小二乘仿射变换
"""
import json, os, sys, math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OV_IMG = os.path.join(HERE, 'viewer', 'overview_13states.png')
OUT = os.path.join(HERE, 'gcp_calibration_13states.json')

# ── 加载图像 ──
img = Image.open(OV_IMG).convert('RGB')
W, H = img.size
arr = np.asarray(img)
print(f'overview_13states.png: {W}x{H}')

def sample(px, py):
    """采样指定像素的RGB"""
    if 0 <= px < W and 0 <= py < H:
        return tuple(arr[py, px])
    return None

# ── GCP 候选点：城市名, (像素x,y), (真实经度, 纬度), 所属州(用于颜色验证) ──
# 像素坐标基于对 overview_13states.png 的目视估计
GCPS_RAW = [
    # 凉州 (golden-brown ~ #CCAE84)
    ("敦煌郡",     (175, 335),  (94.68, 40.14), "凉州"),
    ("武威/姑臧",   (315, 395),  (102.63, 37.93), "凉州"),
    ("张掖",       (358, 368),  (100.45, 38.94), "凉州"),

    # 益州 (yellow-gold ~ #D5C798)
    ("成都",       (468, 882),  (104.07, 30.67), "益州"),
    ("汉中",       (618, 695),  (107.04, 33.05), "益州"),
    ("巴郡",       (478, 1005), (106.76, 29.58), "益州"),

    # 司隶 (dark red ~ #BC5D5B)
    ("长安/京兆尹", (748, 600),  (108.94, 34.27), "司隶"),
    ("洛阳",       (928, 632),  (112.45, 34.62), "司隶"),
    ("河内",       (948, 562),  (113.01, 35.30), "司隶"),

    # 并州 (gray-blue ~ #918C88)
    ("晋阳",       (958, 362),  (112.55, 37.87), "并州"),
    ("太原",       (978, 392),  (112.57, 37.87), "并州"),

    # 冀州 (red ~ #D27370)
    ("邺",         (1048, 448), (114.48, 36.09), "冀州"),
    ("邯郸",       (1058, 472), (114.49, 36.61), "冀州"),

    # 青州 (olive-green ~ #AEBC83)
    ("临淄",       (1308, 428), (118.28, 36.83), "青州"),
    ("北海郡",     (1318, 398), (119.15, 36.72), "青州"),

    # 幽州 (green ~ #76AE81)
    ("蓟",         (1398, 278), (116.40, 39.90), "幽州"),
    ("辽东/襄平",   (1648, 218), (123.28, 41.13), "幽州"),

    # 兖州 (beige ~ #D3CBC0) — 注意：此色接近背景，可能不准
    ("许昌",       (1008, 692), (113.82, 34.03), "兖州"),
    ("陈留",       (978, 718),  (114.63, 34.78), "豫州"),  # 陈留属豫州

    # 豫州 (gray-brown ~ #B3ADA4)
    # (陈留已列在上面)

    # 徐州 (yellow-green ~ #BCD398)
    ("下邳",       (1288, 582), (117.93, 34.29), "徐州"),
    ("彭城",       (1268, 548), (117.19, 34.26), "徐州"),

    # 扬州 (light green ~ #A0D28C)
    ("寿春",       (1328, 708), (116.79, 32.93), "扬州"),
    ("建业/建康",   (1438, 828), (118.78, 32.06), "扬州"),
    ("吴",         (1498, 798), (120.64, 31.30), "扬州"),

    # 荆州 (magenta ~ #CF72C9)
    ("宛/南阳",    (1038, 772), (112.53, 33.00), "荆州"),
    ("襄阳",       (1068, 788), (112.15, 32.02), "荆州"),
    ("江陵",       (1088, 848), (112.21, 30.35), "荆州"),
    ("长沙",       (1108, 918), (112.96, 28.23), "荆州"),

    # 交州 (bright magenta ~ #E14B9B)
    ("番禺/南海",   (1098, 1208),(113.26, 23.13), "交州"),
    ("合浦",       (1078, 1278),(109.51, 21.66), "交州"),
]

# 各州的代表色（用于验证）
STATE_COLORS = {
    '凉州': (204, 174, 132),
    '益州': (213, 199, 152),
    '司隶': (188,  93,  91),
    '并州': (145, 140, 136),
    '冀州': (210, 115, 112),
    '青州': (174, 188, 131),
    '幽州': (118, 174, 129),
    '兖州': (211, 203, 192),
    '豫州': (179, 173, 164),
    '徐州': (188, 211, 152),
    '扬州': (160, 210, 140),
    '荆州': (207, 114, 201),
    '交州': (225,  75, 155),
}

# ── 验证每个GCP的颜色是否匹配所属州 ──
print('\n=== GCP颜色验证 ===')
valid_gcps = []
for name, (px, py), (lon, lat), state in GCPS_RAW:
    rgb = sample(px, py)
    if rgb is None:
        print(f'  ✗ {name}: ({px},{py}) 出界'); continue
    expected = STATE_COLORS.get(state)
    dist = math.sqrt(sum((int(a)-int(b))**2 for a,b in zip(rgb, expected))) if expected else 999
    status = '✓' if dist < 60 else '~' if dist < 100 else '✗'
    print(f'  {status} {name:12s} px=({px:>4d},{py:>4d}) RGB={rgb} '
          f'→ ({lon:.2f},{lat:.2f}) [{state}] d={dist:.1f}')
    valid_gcps.append({'name': name, 'px': px, 'py': py, 'lon': lon, 'lat': lat,
                       'state': state, 'rgb': [int(c) for c in rgb], 'color_dist': round(float(dist), 1)})

print(f'\n有效GCP: {len(valid_gcps)} / {len(GCPS_RAW)}')

if len(valid_gcps) < 6:
    print('ERROR: 有效GCP不足6个，无法构建可靠仿射变换!')
    sys.exit(1)

# ── 构建仿射变换 (px,py) → (lon,lat) ──
# 模型: [lon, lat] = M @ [px, py, 1]^T
# M 是 2×3 矩阵，用最小二乘拟合
gcps_arr = np.array([[g['px'], g['py'], 1.0] for g in valid_gcps])
lons = np.array([g['lon'] for g in valid_gcps])
lats = np.array([g['lat'] for g in valid_gcps])

M_lon = np.linalg.lstsq(gcps_arr, lons, rcond=None)[0]
M_lat = np.linalg.lstsq(gcps_arr, lats, rcond=None)[0]

print(f'\n=== 仿射变换 ===')
print(f'  lon = {M_lon[0]:.8f}*px + {M_lon[1]:.8f}*py + {M_lon[2]:.4f}')
print(f'  lat = {M_lat[0]:.8f}*px + {M_lat[1]:.8f}*py + {M_lat[2]:.4f}')

# ── 测试变换质量 ──
print(f'\n=== 残差分析 ===')
max_err = 0
for i, g in enumerate(valid_gcps):
    pred_lon = M_lon[0]*g['px'] + M_lon[1]*g['py'] + M_lon[2]
    pred_lat = M_lat[0]*g['px'] + M_lat[1]*g['py'] + M_lat[2]
    err_lon = pred_lon - g['lon']
    err_lat = pred_lat - g['lat']
    err_km = ((err_lon*111*math.cos(math.radians(g['lat'])))**2 + (err_lat*111)**2)**0.5
    max_err = max(max_err, err_km)
    print(f'  {g["name"]:12s} 预测=({pred_lon:.3f},{pred_lat:.3f}) '
          f'误差=({err_lon:+.3f},{err_lat:+.3f}) ≈{err_km:.1f}km')

# ── 测试图像四角映射到什么范围 ──
print(f'\n=== 图像四角 → 经纬度 ===')
corners = [(0, 0), (W-1, 0), (0, H-1), (W-1, H-1), (W//2, H//2)]
for px, py in corners:
    lo = M_lon[0]*px + M_lon[1]*py + M_lon[2]
    la = M_lat[0]*px + M_lat[1]*py + M_lat[2]
    print(f'  px=({px:>5d},{py:>5d}) → ({lo:.2f}, {la:.2f})')

# ── 检查是否覆盖中国范围 (72-140E, 15-55N) ──
c0_lon = M_lon[0]*0 + M_lon[1]*0 + M_lon[2]
c0_lat = M_lat[0]*0 + M_lat[1]*0 + M_lat[2]
cw_lon = M_lon[0]*(W-1) + M_lon[1]*(H-1) + M_lon[2]
cw_lat = M_lat[0]*(W-1) + M_lat[1]*(H-1) + M_lat[2]
all_lons = [M_lon[0]*px + M_lon[1]*py + M_lon[2] for px,py in [(0,0),(W-1,0),(0,H-1),(W-1,H-1)]]
all_lats = [M_lat[0]*px + M_lat[1]*py + M_lat[2] for px,py in [(0,0),(W-1,0),(0,H-1),(W-1,H-1)]]
lon_range = (min(all_lons), max(all_lons))
lat_range = (min(all_lats), max(all_lats))
print(f'\n  Lon范围: [{lon_range[0]:.1f}, {lon_range[1]:.1f}] (期望~[72,140])')
print(f'  Lat范围: [{lat_range[0]:.1f}, {lat_range[1]:.1f}] (期望~[15,55])')

# ── 保存校准文件 ──
calibration = {
    'source_image': 'viewer/overview_13states.png',
    'image_size': [W, H],
    'method': 'affine_least_squares',
    'gcps': valid_gcps,
    'transform': {
        'M_lon': [round(v, 10) for v in M_lon.tolist()],
        'M_lat': [round(v, 10) for v in M_lat.tolist()],
    },
    'residual_stats': {
        'max_error_km': round(max_err, 1),
        'num_gcps': len(valid_gcps),
        'lon_range': [round(lon_range[0], 2), round(lon_range[1], 2)],
        'lat_range': [round(lat_range[0], 2), round(lat_range[1], 2)],
    }
}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(calibration, f, ensure_ascii=False, indent=2)
print(f'\n已保存: {OUT} ({os.path.getsize(OUT):,} bytes)')
