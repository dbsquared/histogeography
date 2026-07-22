#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 1: 擦除 冀州.png 上的文字/白线/标注，并修补被文字压偏的州界。

基于 step1_erase_text_youzhou.py 改造。
冀州主色：浅青色/青绿 cyan-teal，RGB≈(173,228,207)，
区别于邻州：幽州(深绿)、并州(红)、青州(黄绿)、豫州(米黄)。

输出:
- jizhou_step1/mask_clean.png          : 二值掩膜（白=冀州，黑=背景）
- jizhou_step1/mask_with_boundary.png  : 掩膜上叠加红色边界
- jizhou_step1/text_erased.png         : 原图去文字后的 RGB 图
- jizhou_step1/boundary_overlay.png    : 原图上叠加修复后的蓝色边界
- jizhou_step1/boundary_points.json    : 边界像素坐标（seq, px, py）
"""
import os, json
import cv2, numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
OUTDIR = os.path.join(HERE, 'jizhou_step1')
os.makedirs(OUTDIR, exist_ok=True)

# ============================================================
# 1. 读图
# ============================================================
rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = rgb.shape[:2]
hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
h = hsv[:, :, 0].astype(int)
s = hsv[:, :, 1].astype(int)
v = hsv[:, :, 2].astype(int)
r = rgb[:, :, 0].astype(int)
g = rgb[:, :, 1].astype(int)
b = rgb[:, :, 2].astype(int)
print(f'[1] 图像尺寸: {W}x{H}')

# ============================================================
# 2. 严格浅青色掩膜（冀州本体）
# 冀州主色 RGB≈(173,228,207): G显著大于R和B，G高(175~245)，B中等偏高(155~240)
# 排除：幽州深绿(G<180)、并州红(R>G)、青州黄绿(B<155)、豫州米黄(G≈R)
# ============================================================
jizhou_mask = (
    (g > r + 35) &      # G 显著大于 R（排除红、米黄）
    (g > b + 10) &       # G 大于 B（区分青绿与纯蓝）
    (g >= 175) &         # G 下限（排除幽州深绿 G~180 但 r/g 关系不同）
    (g <= 245) &
    (r >= 115) &         # R 范围
    (r <= 230) &
    (b >= 155) &         # B 下限（排除青州黄绿 B~168）
    (b <= 242)
).astype(np.uint8) * 255
print(f'[2] 浅青色像素: {(jizhou_mask>0).sum():,}')

# ============================================================
# 3. 缺陷掩膜：文字、白线、红点、红色/棕色标签
# ============================================================
dark_text = (r < 105) & (g < 105) & (b < 105)
white_lines = (r > 190) & (g > 190) & (b > 190)
red_hsv = ((h <= 18) | (h >= 165)) & (s >= 45) & (v >= 50) & (r > g + 15)
red_rgb = (r > 120) & (g < 130) & (b < 130) & (r > g + 25)
red_labels = red_hsv | red_rgb
defect = (dark_text | white_lines | red_labels).astype(np.uint8) * 255
print(f'[3] 缺陷候选像素: {(defect>0).sum():,} (red_hsv={(red_hsv>0).sum():,}, red_rgb={(red_rgb>0).sum():,})')

# ============================================================
# 4. 迭代条件填充：只填被青色包围的缺陷像素
# ============================================================
mask = jizhou_mask.copy()
k7 = np.ones((7, 7), np.float32) / 49.0
for it in range(100):
    green_frac = cv2.filter2D(mask.astype(np.float32) / 255.0, -1, k7)
    candidate = (defect > 0) & (mask == 0) & (green_frac > 0.30)
    if not candidate.any():
        break
    mask[candidate] = 255
print(f'[4] 迭代填充后: {(mask>0).sum():,} px （迭代 {it+1} 次）')

# ============================================================
# 5. 小核闭运算桥接剩余细缺口
# ============================================================
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8), iterations=2)

# 只保留最大连通域
nb, lab, st, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
main_i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
mask_conn = (lab == main_i).astype(np.uint8) * 255

# 取外轮廓并填充内部孔洞
contours, _ = cv2.findContours(mask_conn, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)
mask_filled = np.zeros_like(mask_conn)
cv2.drawContours(mask_filled, [main], -1, 255, -1)
print(f'[5] 修补后掩膜: {(mask_filled>0).sum():,} px')

# 轻微高斯平滑边缘
mask_smooth = cv2.GaussianBlur(mask_filled.astype(np.float32), (5, 5), 0)
mask_smooth = (mask_smooth > 127).astype(np.uint8) * 255
mask_smooth = cv2.morphologyEx(mask_smooth, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)

# ============================================================
# 6. 外轮廓提取 + 自动选 eps 使顶点数落在 120~260
# ============================================================
contours, _ = cv2.findContours(mask_smooth, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)
arc = cv2.arcLength(main, True)

for eps_factor in [0.0006, 0.0008, 0.0010, 0.0012, 0.0015, 0.0018, 0.0020, 0.0025, 0.0030]:
    poly_px = cv2.approxPolyDP(main, eps_factor * arc, True).reshape(-1, 2)
    if 120 <= len(poly_px) <= 260:
        break
print(f'[6] 初始边界顶点数: {len(poly_px)} (eps_factor={eps_factor:.4f})')

# ============================================================
# 6.5 压边文字区域边界拉平
# ============================================================
def flatten_boundary_at_labels(poly_px, h, w, rgb_img, pad=50, min_area=200):
    n = len(poly_px)
    poly = np.array(poly_px, dtype=np.int32)

    ri = rgb_img[:,:,0].astype(int); gi = rgb_img[:,:,1].astype(int); bi = rgb_img[:,:,2].astype(int)
    dark_t = (ri < 105) & (gi < 105) & (bi < 105)
    hsv_i = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2HSV)
    hh_i = hsv_i[:,:,0].astype(int); ss_i = hsv_i[:,:,1].astype(int); vv_i = hsv_i[:,:,2].astype(int)
    red_hs = ((hh_i <= 18) | (hh_i >= 165)) & (ss_i >= 45) & (vv_i >= 50) & (ri > gi + 15)
    red_rg = (ri > 120) & (gi < 130) & (bi < 130) & (ri > gi + 25)
    text_mask = (dark_t | red_hs | red_rg).astype(np.uint8) * 255

    mask_poly = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(mask_poly, [poly.reshape(-1, 1, 2)], -1, 255, -1)

    boundary_line = np.zeros((h, w), dtype=np.uint8)
    for x, y in poly:
        if 0 <= x < w and 0 <= y < h:
            boundary_line[y, x] = 255
    dist_to_boundary = cv2.distanceTransform(255 - boundary_line, cv2.DIST_L2, 5)

    nb_l, labels_l, stats_l, _ = cv2.connectedComponentsWithStats(text_mask, connectivity=8)
    if nb_l <= 1:
        return poly

    changed = False
    for i in range(1, nb_l):
        area = stats_l[i, cv2.CC_STAT_AREA]
        if area < min_area:
            continue
        blob = (labels_l == i).astype(np.uint8) * 255
        blob_dist = dist_to_boundary[blob > 0]
        if len(blob_dist) == 0:
            continue
        d_min = blob_dist.min()
        if d_min > pad:
            continue
        blob_dil = cv2.dilate(blob, np.ones((pad, pad), np.uint8))
        affected = [idx for idx, (x, y) in enumerate(poly)
                    if 0 <= x < w and 0 <= y < h and blob_dil[y, x] > 0]
        if not affected:
            continue
        groups = []
        cur = [affected[0]]
        for idx in affected[1:]:
            prev = cur[-1]
            if (idx == prev + 1) or (prev == n - 1 and idx == 0):
                cur.append(idx)
            else:
                groups.append(cur)
                cur = [idx]
        groups.append(cur)

        for grp in groups:
            if len(grp) < 3:
                continue
            s_idx, e_idx = grp[0], grp[-1]
            p1 = poly[s_idx].astype(np.float32)
            p2 = poly[e_idx].astype(np.float32)
            mid = ((p1 + p2) / 2).astype(np.int32)
            if 0 <= mid[0] < w and 0 <= mid[1] < h and mask_poly[mid[1], mid[0]] > 0:
                continue
            if np.linalg.norm(p2 - p1) > 250:
                continue
            new_pts = np.linspace(0, 1, len(grp))[:, None] * (p2 - p1) + p1
            for k, idx in enumerate(grp):
                poly[idx] = new_pts[k].astype(np.int32)
            changed = True
            print(f'    拉平压边文字 blob #{i}: 索引 {s_idx}-{e_idx}, {len(grp)} 点, 到边界距离 {d_min:.1f}px')

    if changed:
        cleaned = [poly[0]]
        for p in poly[1:]:
            if (p[0] != cleaned[-1][0]) or (p[1] != cleaned[-1][1]):
                cleaned.append(p)
        poly = np.array(cleaned, dtype=np.int32)
    return poly

poly_px = flatten_boundary_at_labels(poly_px, H, W, rgb, pad=50, min_area=200)
print(f'[6.5] 拉平后边界顶点数: {len(poly_px)}')

# 用拉平后的边界重新生成掩膜
mask_flat = np.zeros((H, W), dtype=np.uint8)
cv2.drawContours(mask_flat, [poly_px.reshape(-1, 1, 2)], -1, 255, -1)
mask_smooth = cv2.morphologyEx(mask_flat, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)
print(f'[6.5] 重建掩膜面积: {(mask_smooth>0).sum():,} px')

# ============================================================
# 7. 生成去文字后的 RGB 图（使用最终掩膜）
# ============================================================
if (jizhou_mask > 0).any():
    mean_color = rgb[jizhou_mask > 0].mean(axis=0).astype(np.uint8)
else:
    mean_color = np.array([174, 229, 208], dtype=np.uint8)

inside = mask_smooth > 0
rgb_f = rgb.astype(np.float32)
mean_color_f = mean_color.astype(np.float32)
dist_to_color = np.linalg.norm(rgb_f - mean_color_f, axis=2)

defect_inside = inside & (defect > 0)
not_cyan = inside & ~((g > r + 30) & (g > b + 15) & (g >= 165) & (g <= 245))

residue = (inside & (dist_to_color > 35)) | defect_inside | not_cyan
residue = cv2.dilate(residue.astype(np.uint8) * 255, np.ones((3, 3), np.uint8), iterations=1) > 0

fill_mask = inside & residue

cleaned = rgb.copy()
cleaned[fill_mask] = mean_color

print(f'[7] 最终掩膜内填充像素: {fill_mask.sum():,} px (dist>35: {((inside&(dist_to_color>35)).sum()):,}, defect: {defect_inside.sum():,}, not_cyan: {not_cyan.sum():,})')

# ============================================================
# 8. 保存输出
# ============================================================
Image.fromarray(mask_smooth).save(os.path.join(OUTDIR, 'mask_clean.png'))

mask_view = np.zeros((H, W, 3), dtype=np.uint8)
mask_view[mask_smooth > 0] = (255, 255, 255)
cv2.polylines(mask_view, [poly_px], True, (0, 0, 255), 3)
Image.fromarray(mask_view).save(os.path.join(OUTDIR, 'mask_with_boundary.png'))

Image.fromarray(cleaned).save(os.path.join(OUTDIR, 'text_erased.png'))

overlay = rgb.copy()
cv2.polylines(overlay, [poly_px], True, (255, 0, 0), 3)
Image.fromarray(overlay).save(os.path.join(OUTDIR, 'boundary_overlay.png'))

pts = [{'seq': i, 'px': int(x), 'py': int(y)} for i, (x, y) in enumerate(poly_px)]
with open(os.path.join(OUTDIR, 'boundary_points.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'source_image': '汉末十三州地图范例/冀州.png',
        'image_size': [W, H],
        'method': '浅青色掩膜 + 缺陷检测（文字/白线/红点/红标签） + 迭代条件填充 + 外轮廓简化',
        'points': pts
    }, f, ensure_ascii=False, indent=2)

# 三栏对比图
thumb_w, thumb_h = W // 2, H // 2
orig_thumb = cv2.resize(rgb, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
erased_thumb = cv2.resize(cleaned, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
overlay_thumb = cv2.resize(overlay, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
comparison = np.zeros((thumb_h, thumb_w * 3, 3), dtype=np.uint8)
comparison[:, 0:thumb_w] = orig_thumb
comparison[:, thumb_w:2*thumb_w] = erased_thumb
comparison[:, 2*thumb_w:3*thumb_w] = overlay_thumb
Image.fromarray(comparison).save(os.path.join(OUTDIR, 'comparison_preview.png'))

print(f'[done] 输出到 {OUTDIR}/')
print(f'    mask_clean.png, mask_with_boundary.png, text_erased.png, boundary_overlay.png')
print(f'    comparison_preview.png, boundary_points.json')
print(f'    边界点数量: {len(pts)}')
