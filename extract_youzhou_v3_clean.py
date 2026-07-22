#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提取幽州深绿边界 v3：先去文字/白线，再修补，最后取外轮廓.

思路（按用户指引）:
1.  先用严格的深绿阈值得到 幽州 主体（避免把邻州浅绿也包进来）。
2.  检测缺陷：白色细线（郡界）和深色文字（郡名/国名）。
3.  只修补被绿色包围的缺陷像素：迭代条件填充，文字块和白线从边缘向中心填实；
    外部不是绿色，填充不会越界到邻州。
4.  小核闭运算填平剩余的细线缺口。
5.  取最大外轮廓并填充内部空洞。
6.  用 approxPolyDP 简化到 120~240 个转折点。
"""
import os, json, cv2, numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, 'youzhou_layer_v2')
SRC_IMG = os.path.join(HERE, '汉末十三州地图范例', '幽州.png')
JSON_PATH = os.path.join(OUTDIR, 'youzhou_correspondence.json')

os.makedirs(OUTDIR, exist_ok=True)

# ============================================================
# 1. 读图
# ============================================================
rgb = np.array(Image.open(SRC_IMG).convert('RGB'))
H, W = rgb.shape[:2]
r = rgb[:, :, 0].astype(int)
g = rgb[:, :, 1].astype(int)
b = rgb[:, :, 2].astype(int)

# ============================================================
# 2. 严格深绿掩膜（只抓幽州本体，避免邻州浅绿）
# ============================================================
green_mask = (
    (g > r + 45) & (g > b + 40) &
    (g < 195) & (r < 140) & (b < 140) & (g > 100)
).astype(np.uint8) * 255

print(f'[1] 严格深绿掩膜: {(green_mask>0).sum():,} px')

# ============================================================
# 3. 检测“缺陷”像素：白线 + 深色文字
# ============================================================
white_lines = ((r > 210) & (g > 210) & (b > 210)).astype(np.uint8) * 255
dark_text = ((r < 90) & (g < 90) & (b < 90)).astype(np.uint8) * 255
defect = cv2.bitwise_or(white_lines, dark_text)
print(f'[2] 缺陷候选: {(defect>0).sum():,} px')

# ============================================================
# 4. 迭代条件填充：只填被绿色包围的缺陷像素
# ============================================================
mask = green_mask.copy()
k7 = np.ones((7, 7), np.float32) / 49.0
for it in range(30):
    green_frac = cv2.filter2D(mask.astype(np.float32) / 255.0, -1, k7)
    candidate = (defect > 0) & (mask == 0) & (green_frac > 0.40)
    if not candidate.any():
        break
    mask[candidate] = 255

print(f'[3] 迭代填充后: {(mask>0).sum():,} px （迭代 {it+1} 次）')

# ============================================================
# 5. 小核闭运算：把剩余的白线细缺口全部桥接，但不越出绿色范围太多
# ============================================================
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=2)

# 保留大连通块（严格阈值可能有碎片）
nb, lab, st, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
if nb > 1:
    areas = [st[i, cv2.CC_STAT_AREA] for i in range(1, nb)]
    max_area = max(areas)
    keep_threshold = max_area * 0.05
    mask_clean = np.zeros_like(mask)
    for i in range(1, nb):
        if st[i, cv2.CC_STAT_AREA] >= keep_threshold:
            mask_clean[lab == i] = 255
else:
    mask_clean = mask

# 取外轮廓并填充内部空洞
contours, _ = cv2.findContours(mask_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)
mask_filled = np.zeros_like(mask_clean)
cv2.drawContours(mask_filled, [main], -1, 255, -1)

# 极轻量平滑：3x3 闭运算 1 次
mask_filled = cv2.morphologyEx(mask_filled, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)

ys, xs = np.where(mask_filled > 0)
print(f'[4] 修补后掩膜: {(mask_filled>0).sum():,} px  bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]')

# ============================================================
# 6. 取外轮廓，自动选 eps 使顶点数落在 120~240
# ============================================================
contours, _ = cv2.findContours(mask_filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)

for eps_factor in [0.0008, 0.0010, 0.0012, 0.0015, 0.0018, 0.0020, 0.0025, 0.0030]:
    poly_px = cv2.approxPolyDP(main, eps_factor * cv2.arcLength(main, True), True).reshape(-1, 2)
    n = len(poly_px)
    print(f'    eps={eps_factor:.4f} -> {n} 顶点')
    if 120 <= n <= 240:
        break
else:
    best = None
    best_n = 0
    for eps_factor in [0.0005, 0.0008, 0.0010, 0.0015, 0.0020, 0.0025, 0.0030, 0.0040, 0.0050]:
        poly_px = cv2.approxPolyDP(main, eps_factor * cv2.arcLength(main, True), True).reshape(-1, 2)
        if best is None or abs(len(poly_px) - 180) < abs(best_n - 180):
            best = poly_px
            best_n = len(poly_px)
    poly_px = best

print(f'[5] 最终边界顶点数: {len(poly_px)}')

# ============================================================
# 7. 保存掩膜预览
# ============================================================
mask_preview = np.zeros((H, W, 3), dtype=np.uint8)
mask_preview[mask_filled > 0] = (255, 255, 255)
cv2.polylines(mask_preview, [poly_px], True, (0, 0, 255), 3)
Image.fromarray(mask_preview).save(os.path.join(OUTDIR, 'youzhou_mask_v3.png'))

# 在原图上叠加边界
rgb_view = rgb.copy()
cv2.polylines(rgb_view, [poly_px], True, (255, 0, 0), 3)
Image.fromarray(rgb_view).save(os.path.join(OUTDIR, 'youzhou_extract_v3_preview.png'))

# ============================================================
# 8. 写入 correspondence JSON（像素坐标；经纬度由 recalc 重新拟合）
# ============================================================
pts = []
for i, (x, y) in enumerate(poly_px):
    pts.append({
        'seq': i,
        'px': int(x),
        'py': int(y),
        'lon': None,
        'lat': None
    })

data = {
    'source_image': '汉末十三州地图范例/幽州.png',
    'image_size': [W, H],
    'method': '严格深绿 + 去文字/白线 + 迭代条件填充 + 外轮廓提取 (px,py)->(lon,lat) 仿射',
    'anchors': [],
    'points': pts
}

# 保留原有 anchors（从 anchor_table.json 读取后由 recalc 使用）
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    old = json.load(f)
data['anchors'] = old.get('anchors', [])

with open(JSON_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'[6] 已保存 {JSON_PATH}，{len(pts)} 个边界点')
