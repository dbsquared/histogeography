"""
从图例(全览-郡级.png)提取13州色块区域 v2。
核心改进：
- 用泛洪填充(Flood Fill)从四角找背景区域 → 不依赖颜色启发式
- 前景像素上做k-means(k=13)聚类找州色
- 每个前景像素归入最近州 → 天然无重叠、无空隙
输出：
- rendered/states_extract_preview.png  提取预览
- rendered/states_on_terrain.png      地形叠加预览  
- extracted_states.json              13州掩码信息
"""

import numpy as np
from PIL import Image, ImageDraw
from collections import Counter
import json, os
import rasterio
from scipy import ndimage

# ── 路径 ──
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LEGEND_DIR = os.path.join(SCRIPT_DIR, "汉末十三州地图范例")
RENDER_DIR = os.path.join(SCRIPT_DIR, "rendered")
TERRAIN_TIF = os.path.join(SCRIPT_DIR, "china_full_v3.tif")
TERRAIN_PNG = os.path.join(SCRIPT_DIR, "china_full_v3.png")
LEGEND_FILE = os.path.join(LEGEND_DIR, "全览-郡级.png")

os.makedirs(RENDER_DIR, exist_ok=True)

# ══════════════════════════════════════════════
# Step 1: 加载图例
# ══════════════════════════════════════════════
print("=== Step 1: Load Legend ===")
im = Image.open(LEGEND_FILE).convert("RGB")
arr = np.array(im, dtype=np.uint8)
H, W = arr.shape[:2]
print(f"  Size: {W}x{H}")

# ══════════════════════════════════════════════
# Step 2: 泛洪填充找背景（从4角开始）
# ══════════════════════════════════════════════
print("\n=== Step 2: Flood-fill Background ===")

def flood_fill_bg(img_arr, tolerance=35):
    """从图像4角泛洪填充，找到连通的背景区域。
    背景特征：颜色均匀、亮度较高。"""
    visited = np.zeros((H, W), dtype=bool)
    bg_mask = np.zeros((H, W), dtype=bool)
    
    # 取4个角的种子点
    seeds = [
        (0, 0), (0, W-1), (H-1, 0), (H-1, W-1),
        # 加上边缘中点增加覆盖
        (0, W//2), (H//2, 0), (H//2, W-1), (H-1, W//2),
    ]
    
    for sy, sx in seeds:
        sr, sg, sb = int(img_arr[sy, sx, 0]), int(img_arr[sy, sx, 1]), int(img_arr[sy, sx, 2])
        
        stack = [(sy, sx)]
        while stack:
            y, x = stack.pop()
            if y < 0 or y >= H or x < 0 or x >= W:
                continue
            if visited[y, x]:
                continue
            visited[y, x] = True
            
            r, g, b = int(img_arr[y, x, 0]), int(img_arr[y, x, 1]), int(img_arr[y, x, 2])
            
            # 颜色距离在容差内 → 视为同色背景
            dr, dg, db = abs(r-sr), abs(g-sg), abs(b-sb)
            if dr <= tolerance and dg <= tolerance and db <= tolerance:
                bg_mask[y, x] = True
                # 4邻域扩展
                stack.append((y+1, x))
                stack.append((y-1, x))
                stack.append((y, x+1))
                stack.append((y, x-1))
    
    return bg_mask

bg_mask = flood_fill_bg(arr)
bg_count = bg_mask.sum()
print(f"  Background pixels: {bg_count:,} ({100*bg_count/(W*H):.1f}%)")

# ══════════════════════════════════════════════
# Step 3: 识别海洋和文字
# ══════════════════════════════════════════════
print("\n=== Step 3: Detect Ocean & Text ===")

def is_ocean(r, g, b):
    return b > 170 and r < 150 and g < 170 and (b - r > 30)

def is_text(r, g, b):
    return r < 65 and g < 65 and b < 65

ocean_mask = np.zeros((H, W), dtype=bool)
text_mask = np.zeros((H, W), dtype=bool)

for y in range(H):
    for x in range(W):
        if bg_mask[y, x]:
            continue  # 背景已处理
        r, g, b = int(arr[y,x,0]), int(arr[y,x,1]), int(arr[y,x,2])
        if is_ocean(r, g, b):
            ocean_mask[y, x] = True
        elif is_text(r, g, b):
            text_mask[y, x] = True

# 对海洋也做泛洪填充（连接大片蓝色区域）
# 简化：直接用颜色判断
ocean_count = ocean_mask.sum()
text_count = text_mask.sum()
total_px = W * H
print(f"  Ocean: {ocean_count:,} ({100*ocean_count/total_px:.1f}%)")
print(f"  Text/Lines: {text_count:,} ({100*text_count/total_px:.1f}%)")

# ══════════════════════════════════════════════
# Step 4: 前景 = 非背景 & 非海洋 & 非文字
# ══════════════════════════════════════════════
foreground_mask = ~(bg_mask | ocean_mask | text_mask)
fg_count = foreground_mask.sum()
print(f"\n=== Step 4: Foreground ===")
print(f"  Foreground (states): {fg_count:,} ({100*fg_count/total_px:.1f}%)")
print(f"  Sum check: bg+ocean+text+fg = {(bg_mask|ocean_mask|text_mask|foreground_mask).sum()}/{total_px}")

# ══════════════════════════════════════════════
# Step 5: K-means (k=13) 在前景上找州色
# ══════════════════════════════════════════════
print("\n=== Step 5: K-means K=13 on Foreground ===")

from sklearn.cluster import MiniBatchKMeans

fg_pixels = arr[foreground_mask].reshape(-1, 3).astype(np.float32)
print(f"  Foreground pixels to cluster: {len(fg_pixels):,}")

kmeans = MiniBatchKMeans(n_clusters=13, random_state=42, batch_size=10000,
                          max_iter=300, n_init=5)
labels = kmeans.fit_predict(fg_pixels)
centers = kmeans.cluster_centers_.astype(np.uint8)

print(f"\n  13 Cluster Centers:")
for i in range(13):
    mask_i = (labels == i)
    area = mask_i.sum()
    pct = 100 * area / len(labels)
    c = tuple(centers[i])
    print(f"    State{i:2d}: {str(c):>14s}  area={area:>8,}px ({pct:5.2f}%)")

# ══════════════════════════════════════════════
# Step 6: 构建全图状态标注图
# ══════════════════════════════════════════════
print("\n=== Step 6: Build Full State Label Map ===")

state_label = np.full((H, W), -1, dtype=np.int8)

fg_coords = np.argwhere(foreground_mask)  # (N, 2) [y, x]
for idx in range(len(fg_coords)):
    y, x = fg_coords[idx]
    state_label[y, x] = int(labels[idx])

# 统计各州在全图上的面积
print("\n  State areas (full map):")
state_areas = []
for si in range(13):
    m = state_label == si
    a = m.sum()
    state_areas.append(a)
    print(f"    State{si:2d}: {a:>9,}px")

# 验证：所有前景像素都被标注了
labeled_total = sum(state_areas)
print(f"\n  Labeled total: {labeled_total:,}, expected fg: {fg_count:,}")
assert labeled_total == fg_count, f"Mismatch! labeled={labeled_total} vs fg={fg_count}"

# ══════════════════════════════════════════════
# Step 7: 填充孔洞 + 提取轮廓 + 预览
# ══════════════════════════════════════════════
print("\n=== Step 7: Preview Generation ===")

try:
    from scipy.ndimage import binary_fill_holes
    HAS_FILL = True
except ImportError:
    HAS_FILL = False
    print("  WARN: no scipy.ndimage, skipping hole fill")

# 可视化色彩(鲜艳区分13州)
VIS_COLORS = [
    (220, 50, 50),    # 红
    (50, 180, 50),    # 绿
    (50, 120, 220),   # 蓝
    (230, 150, 30),   # 橙
    (180, 50, 180),   # 紫
    (50, 200, 180),   # 青
    (220, 200, 40),   # 黄
    (170, 80, 50),    # 棕
    (140, 50, 200),   # 紫红
    (80, 200, 80),    # 浅绿
    (210, 140, 50),   # 土黄
    (140, 140, 210),  # 淡蓝
    (90, 175, 90),    # 橄榄
]

preview = Image.new("RGB", (W, H), (240, 240, 230))
pv = np.array(preview)

states_info = []

for si in range(13):
    raw_mask = state_label == si
    
    if HAS_FILL:
        mask = ndimage.binary_fill_holes(raw_mask)
    else:
        mask = raw_mask
    
    vc = VIS_COLORS[si]
    
    # 填充该州颜色
    pv[mask] = vc
    
    # 提取边界(腐蚀差集法)
    eroded = ndimage.binary_erosion(mask, iterations=1)
    edge = mask & ~eroded
    
    # 采样轮廓点
    edge_pts = np.argwhere(edge)
    n_edge = len(edge_pts)
    if n_edge > 4000:
        step = max(1, n_edge // 2500)
        sampled = edge_pts[::step]
    else:
        sampled = edge_pts

    info = {
        "id": si,
        "color_rgb": tuple(int(v) for v in centers[si]),
        "vis_color": vc,
        "area_px": int(raw_mask.sum()),
        "filled_area_px": int(mask.sum()),
        "n_boundary_pixels": int(n_edge),
        "boundary_sample": [[int(y), int(x)] for y, x in sampled[:300]],
    }
    states_info.append(info)
    print(f"  State{si:2d}: raw={raw_mask.sum():>8,}, filled={mask.sum():>8,}, boundary={n_edge:>6,}")

# 在预览上画白色边界线
for si in range(13):
    raw_mask = state_label == si
    if HAS_FILL:
        mask = ndimage.binary_fill_holes(raw_mask)
    else:
        mask = raw_mask
    eroded = ndimage.binary_erosion(mask, iterations=1)
    edge = mask & ~eroded
    pv[edge] = (255, 255, 255)

prev_im = Image.fromarray(pv)
prev_path = os.path.join(RENDER_DIR, "states_extract_preview.png")
prev_im.save(prev_path, optimize=True)
print(f"\n  [OK] Saved: {prev_path}")

# ══════════════════════════════════════════════
# Step 8: 叠加地形底图
# ══════════════════════════════════════════════
print("\n=== Step 8: Overlay on Terrain ===")

with rasterio.open(TERRAIN_TIF) as ds:
    gt = ds.transform
    tW, tH = ds.width, ds.height
    lon_left = gt.c
    lat_top = gt.f
    lon_right = lon_left + tW * gt.a
    lat_bottom = lat_top + tH * gt.e

print(f"  Terrain: {tW}x{tH}")
print(f"  Lon: [{lon_left:.2f}, {lon_right:.2f}]")
print(f"  Lat: [{lat_bottom:.2f}, {lat_top:.2f}]")
print(f"  Resolution: {gt.a:.5f} deg/px")

# 图例地理范围假设（后续可调）
LON_RANGE = (85.0, 132.0)   # (west, east)
LAT_RANGE = (10.0, 53.0)     # (south, north)

lon_min, lon_max = LON_RANGE
lat_min, lat_max = LAT_RANGE

terrain_im = Image.open(TERRAIN_PNG).convert("RGBA").resize((tW, tH), Image.LANCZOS)
overlay = Image.new("RGBA", (tW, tH), (0, 0, 0, 0))
ov_arr = np.array(overlay)

for si in range(13):
    raw_mask = state_label == si
    if HAS_FILL:
        mask = ndimage.binary_fill_holes(raw_mask)
    else:
        mask = raw_mask
    
    vc = VIS_COLORS[si]
    
    ys, xs = np.where(mask)
    
    # 批量坐标变换
    geo_lons = lon_min + (xs.astype(float) / W) * (lon_max - lon_min)
    geo_lats = lat_max - (ys.astype(float) / H) * (lat_max - lat_min)
    txs = ((geo_lons - lon_left) / gt.a).round().astype(np.int32)
    tys = ((geo_lats - lat_top) / gt.e).round().astype(np.int32)
    
    valid = (txs >= 0) & (txs < tW) & (tys >= 0) & (tys < tH)
    
    ov_arr[tys[valid], txs[valid]] = (*vc, 90)  # alpha=90 半透明
    
    print(f"  State{si:2d}: {valid.sum():,} valid pixels mapped")

result = Image.alpha_composite(terrain_im, Image.fromarray(ov_arr))

# 缩小预览
SCALE = 5
pw, ph = tW // SCALE, tH // SCALE
small = result.resize((pw, ph), Image.LANCZOS)
out_path = os.path.join(RENDER_DIR, "states_on_terrain.png")
small.save(out_path, quality=92)
print(f"\n  [OK] Terrain overlay saved: {out_path} ({pw}x{ph})")

# ══════════════════════════════════════════════
# Step 9: 保存JSON
# ══════════════════════════════════════════════
output = {
    "src_legend": LEGEND_FILE,
    "legend_size": [W, H],
    "assumed_geo_range": {"lon": LON_RANGE, "lat": LAT_RANGE},
    "terrain_size": [tW, tH],
    "terrain_lon_range": [round(lon_left, 4), round(lon_right, 4)],
    "terrain_lat_range": [round(lat_bottom, 4), round(lat_top, 4)],
    "method": "floodfill-bg + kmeans-13 + nearest-color-label",
    "states": states_info,
}

json_out = os.path.join(SCRIPT_DIR, "extracted_states_v2.json")
with open(json_out, "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"  [OK] JSON saved: {json_out}")
print("\n=== DONE! Check preview images ===")
