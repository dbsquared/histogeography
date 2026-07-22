#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 1 v3: 冀州.png 精确提取 — 宽进严出策略。

v1 问题: 掩膜太大，吃并州/司隶，海岸外扩
v2 问题: 阈值太紧+erosion过度，只剩中心小块

v3 策略: 宽进(用v1的宽松阈值捕获全部浅青色) → 严出(用邻州精确排除+边界裁剪)
1) 用v1的宽松颜色阈值获取完整的浅青色区域
2) 显式排除4个邻州的精确颜色区域
3) 轻度形态学修补(5×5×1次)，不做erosion
4) 最大连通域后填充孔洞
5) 边界提取 + 文字拉平
"""
import os, json
import cv2, numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
OUTDIR = os.path.join(HERE, 'jizhou_step1_v3')
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
# 2. 宽松浅青色掩膜 (与v1一致)
# ============================================================
jizho_mask = (
    (g > r + 35) &
    (g > b + 10) &
    (g >= 175) &
    (g <= 245) &
    (r >= 115) &
    (r <= 230) &
    (b >= 155) &
    (b <= 242)
).astype(np.uint8) * 255
print(f'[2] 宽松浅青色像素: {(jizho_mask>0).sum():,}')

# ============================================================
# 3. 邻州精确排除掩膜 (关键!)
# ============================================================
# --- 并州 (西北红色区域): 高R, R显著大于G ---
bingzhou = (
    (r > g + 15) &       # R明显大于G
    (r > 130) &          # R够红
    (r > 140) &
    (g < 190) &          # G不太高
    (~((g > r + 20) & (b >= 155)))  # 排除自身青色
)

# --- 司隶/豫州 (西南米黄色): R≈G, 偏黄暖色 ---
sili = (
    (abs(r.astype(int) - g.astype(int)) < 30) &   # R≈G
    (g > b + 10) &
    (g >= 200) &           # 偏亮黄
    (b < g - 5) &
    (r >= 190) &
    (~((g > r + 30) & (b >= 150)))  # 排除青色
)

# --- 幽州 (北部深绿): G高但整体偏暗/偏绿 ---
youzhou = (
    (g > r + 25) &         # G>R
    (g >= 160) & (g <= 210) &
    (r < 160) &            # R较低
    (b >= 140) &
    (b < g + 20) &
    ((g.astype(int) - r.astype(int)) > 30) &  # 绿色倾向强
    (~((g > b + 15) & (g >= 175)))  # 排除冀州青色(G>B幅度大的)
)

# --- 青州 (东南黄绿色): 黄色调, B偏低 ---
qingzhou = (
    (g > 185) & (g <= 235) &
    (b < 190) &
    (b > 70) &
    (g > b + 25) &
    (r > 170) &
    (abs(r.astype(int) - g.astype(int)) < 50) &  # R≈G偏黄
    (~((b >= 155) & (g > r + 35)))  # 排除冀州青色(B较高且G>>R的)
)

exclude = bingzhou | sili | youzhou | qingzhou
print(f'[3] 排除: 并州={(bingzhou.sum()):,} 司隶={(sili.sum()):,} '
      f'幽州={(youzhou.sum()):,} 青州={(qingzhou.sum()):,}')

# 应用排除到宽松掩膜
jizho_mask[exclude > 0] = 0
print(f'[3] 排除后: {(jizho_mask>0).sum():,} px')

# ============================================================
# 4. 缺陷检测 + 迭代条件填充
# ============================================================
dark_text = (r < 105) & (g < 105) & (b < 105)
white_lines = (r > 190) & (g > 190) & (b > 190)
red_hsv = ((h <= 18) | (h >= 165)) & (s >= 45) & (v >= 50) & (r > g + 15)
red_rgb = (r > 120) & (g < 130) & (b < 130) & (r > g + 25)
red_labels = red_hsv | red_rgb
defect = (dark_text | white_lines | red_labels).astype(np.uint8) * 255
print(f'[4] 缺陷候选: {(defect>0).sum():,}')

mask = jizho_mask.copy()
k5 = np.ones((5, 5), np.float32) / 25.0
for it in range(80):
    green_frac = cv2.filter2D(mask.astype(np.float32) / 255.0, -1, k5)
    candidate = (defect > 0) & (mask == 0) & (green_frac > 0.40) & (~exclude)
    if not candidate.any():
        break
    mask[candidate] = 255
print(f'[4] 填充后: {(mask>0).sum():,} px ({it+1}轮)')

# ============================================================
# 5. 轻度形态学 (不扩张，只桥接缺口)
# ============================================================
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=1)

# 安全网：再次排除
mask[exclude > 0] = 0

# 最大连通域
nb, lab, st, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
main_i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
mask_conn = (lab == main_i).astype(np.uint8) * 255

# 外轮廓填孔洞
contours, _ = cv2.findContours(mask_conn, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)
mask_filled = np.zeros_like(mask_conn)
cv2.drawContours(mask_filled, [main], -1, 255, -1)

print(f'[5] 最终掩膜: {(mask_filled>0).sum():,} px')

# ============================================================
# 6. 边界提取
# ============================================================
contours, _ = cv2.findContours(mask_filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)
arc = cv2.arcLength(main, True)

for eps_factor in [0.0006, 0.0008, 0.0010, 0.0012, 0.0015, 0.0018, 0.0020, 0.0025, 0.0030]:
    poly_px = cv2.approxPolyDP(main, eps_factor * arc, True).reshape(-1, 2)
    if 120 <= len(poly_px) <= 260:
        break
print(f'[6] 边界顶点: {len(poly_px)} (eps={eps_factor:.4f})')

# ============================================================
# 7. 压边文字拉平
# ============================================================
def flatten_boundary_at_labels(poly_px, h, w, rgb_img, pad=40, min_area=200):
    n = len(poly_px)
    poly = np.array(poly_px, dtype=np.int32)

    ri = rgb_img[:,:,0].astype(int); gi = rgb_img[:,:,1].astype(int); bi = rgb_img[:,:,2].astype(int)
    dark_t = (ri < 105) & (gi < 105) & (bi < 105)
    hsv_i = cv2.cvtColor(rgb_img, cv2.COLOR_RGB2HSV)
    hh_i = hsv_i[:,:,0].astype(int); ss_i = hsv_i[:,:,1].astype(int); vv_i = hsv_i[:,:,2].astype(int)
    red_hs = ((hh_i <= 18) | (hh_i >= 165)) & (ss_i >= 45) & (vv_i >= 50) & (ri > gi + 15)
    red_rg = (ri > 120) & (gi < 130) & (bi < 130) & (ri > gi + 25)
    text_mask = (dark_t | red_hs | red_rg).astype(np.uint8) * 255

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
            if 0 <= mid[0] < w and 0 <= mid[1] < h and mask_filled[mid[1], mid[0]] > 0:
                continue
            if np.linalg.norm(p2 - p1) > 250:
                continue
            new_pts = np.linspace(0, 1, len(grp))[:, None] * (p2 - p1) + p1
            for k, idx in enumerate(grp):
                poly[idx] = new_pts[k].astype(np.int32)
            changed = True
            print(f'    拉平文字 #{i}: {s_idx}-{e_idx}, {len(grp)}点, 距{d_min:.1f}px')

    if changed:
        cleaned = [poly[0]]
        for p in poly[1:]:
            if (p[0] != cleaned[-1][0]) or (p[1] != cleaned[-1][1]):
                cleaned.append(p)
        poly = np.array(cleaned, dtype=np.int32)
    return poly

poly_px = flatten_boundary_at_labels(poly_px, H, W, rgb, pad=40, min_area=200)
print(f'[7] 拉平后顶点: {len(poly_px)}')

# 重建最终掩膜
mask_final = np.zeros((H, W), dtype=np.uint8)
cv2.drawContours(mask_final, [poly_px.reshape(-1, 1, 2)], -1, 255, -1)
mask_final[exclude > 0] = 0  # 安全网
mask_final = cv2.morphologyEx(mask_final, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)
print(f'[7] 最终掩膜: {(mask_final>0).sum():,} px')

# ============================================================
# 8. 输出
# ============================================================
if (jizho_mask > 0).any():
    mean_color = rgb[jizho_mask > 0].mean(axis=0).astype(np.uint8)
else:
    mean_color = np.array([173, 228, 207], dtype=np.uint8)

inside = mask_final > 0
cleaned = rgb.copy()
cleaned[inside] = mean_color

Image.fromarray(mask_final).save(os.path.join(OUTDIR, 'mask_clean.png'))

mask_view = np.zeros((H, W, 3), dtype=np.uint8)
mask_view[mask_final > 0] = (255, 255, 255)
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
        'version': 'v3-wideloose_tighttrim',
        'points': pts
    }, f, ensure_ascii=False, indent=2)

thumb_w, thumb_h = W // 2, H // 2
comparison = np.zeros((thumb_h, thumb_w * 3, 3), dtype=np.uint8)
comparison[:, 0:thumb_w] = cv2.resize(rgb, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
comparison[:, thumb_w:2*thumb_w] = cv2.resize(cleaned, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
comparison[:, 2*thumb_w:3*thumb_w] = cv2.resize(overlay, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
Image.fromarray(comparison).save(os.path.join(OUTDIR, 'comparison_preview.png'))

# 验证叠图
verify = rgb.astype(float) * 0.55 + np.stack([mask_final]*3, axis=-1).astype(float) * 0.45 * np.array([0, 1, 1])
verify = np.clip(verify, 0, 255).astype(np.uint8)
cv2.polylines(verify, [poly_px], True, (255, 0, 0), 2)
Image.fromarray(verify).save(os.path.join(OUTDIR, 'verify_overlay.png'))

print(f'[done] => {OUTDIR}/')
print(f'    边界{len(pts)}点, 面积{(mask_final>0).sum():,}px')
