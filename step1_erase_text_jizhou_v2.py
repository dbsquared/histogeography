#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 1 v2: 冀州.png 精确提取 — 修复边界越界问题。

v1 问题:
- 西北侧严重侵入并州(红色)
- 西南侧吃了司隶(米黄色)一小块
- 东北侧被幽州境内白线带偏
- 海岸线往外扩了

v2 修复策略:
1) 收紧颜色阈值: G>R+45(原35), G>B+18(原10), G范围收窄到[180,240]
2) 显式排除掩膜: 并州红色 / 司隶米黄 / 幽州深绿 / 青州黄绿
3) 缩减形态学: 5×5闭运算×1次(原7×7×2次)
4) 提高填充门槛: green_frac>0.50(原0.30),核缩小到5×5
5) 最终掩膜做一次 erosion(3×3)收缩回真实边缘
"""
import os, json
import cv2, numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
OUTDIR = os.path.join(HERE, 'jizhou_step1_v2')
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
# 2. 冀州浅青色精确掩膜 (收紧版)
# 主色 RGB≈(173,228,207): 高G, 中高B, 中R
# ============================================================
jizhou_core = (
    (g > r + 45) &       # G显著大于R (原+35 → +45，更严格)
    (g > b + 18) &       # G大于B (原+10 → +18)
    (g >= 180) &         # G下限提高 (原175→180)
    (g <= 240) &         # G上限降低 (原245→240)
    (r >= 120) &         # R下限
    (r <= 220) &
    (b >= 160) &         # B下限提高 (原155→160)
    (b <= 235)
).astype(np.uint8) * 255
print(f'[2] 浅青色核心像素: {(jizhou_core>0).sum():,}')

# ============================================================
# 3. 邻州颜色排除掩膜 (关键修复!)
# ============================================================
# 并州: 红色 R>G, R偏高
bingzhou_red = (
    (r > g + 20) &
    (r > 140) &
    (g < 180) &
    (r > 150)
)

# 司隶/豫州: 米黄色/浅黄 R≈G>B, 偏暖
sili_beige = (
    (abs(r.astype(int) - g.astype(int)) < 25) &  # R≈G
    (g > b + 15) &                                # G>B
    (g >= 195) &                                  # 亮黄
    (g <= 240) &
    (r >= 185) &
    (b < 200)
)

# 幽州: 深绿/墨绿 G高但R低, 或偏暗的绿
youzhou_darkgreen = (
    (g > 150) & (g < 200) &
    (r < 140) &
    (b > r + 10) &
    (b < g) &
    (g > r + 30)
)

# 青州: 黄绿色 B偏低, 偏黄
qingzhou_yellowgreen = (
    (g > 190) & (g <= 235) &
    (b < 185) &
    (b > 80) &
    (g > b + 30) &
    (r > 160) &
    (abs(r.astype(int) - g.astype(int)) < 40)
)

# 合并所有排除区域
exclude_mask = bingzhou_red | sili_beige | youzhou_darkgreen | qingzhou_yellowgreen
print(f'[3] 排除像素: 并州红={(bingzhou_red.sum()):,}, 司隶黄={(sili_beige.sum()):,}, '
      f'幽州绿={(youzhou_darkgreen.sum()):,}, 青州黄绿={(qingzhou_yellowgreen.sum()):,}')

# 应用排除
jizhou_mask = jizhou_core.copy()
jizhou_mask[exclude_mask > 0] = 0
print(f'[3] 排除后冀州像素: {(jizhou_mask>0).sum():,}')

# ============================================================
# 4. 缺陷掩膜: 文字、白线、红标签
# ============================================================
dark_text = (r < 105) & (g < 105) & (b < 105)
white_lines = (r > 190) & (g > 190) & (b > 190)
red_hsv = ((h <= 18) | (h >= 165)) & (s >= 45) & (v >= 50) & (r > g + 15)
red_rgb = (r > 120) & (g < 130) & (b < 130) & (r > g + 25)
red_labels = red_hsv | red_rgb
defect = (dark_text | white_lines | red_labels).astype(np.uint8) * 255
print(f'[4] 缺陷候选: {(defect>0).sum():,}')

# ============================================================
# 5. 谨慎迭代条件填充 (收紧版)
# 只在被青色包围且不在排除区内的缺陷上填
# ============================================================
mask = jizhou_mask.copy()
k5 = np.ones((5, 5), np.float32) / 25.0  # 原7×7 → 5×5
for it in range(80):
    green_frac = cv2.filter2D(mask.astype(np.float32) / 255.0, -1, k5)
    candidate = (defect > 0) & (mask == 0) & (green_frac > 0.50) & (~exclude_mask)  # 原0.30→0.50
    if not candidate.any():
        break
    mask[candidate] = 255
print(f'[5] 填充后: {(mask>0).sum():,} px ({it+1}轮)')

# ============================================================
# 6. 轻度形态学修补 (大幅缩减)
# ============================================================
# 只用小核闭运算桥接缺口，不做扩张
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8), iterations=1)  # 原7×7×2

# 再次排除邻州颜色
mask[exclude_mask > 0] = 0

# 最大连通域
nb, lab, st, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
main_i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
mask_conn = (lab == main_i).astype(np.uint8) * 255

# 外轮廓填充孔洞
contours, _ = cv2.findContours(mask_conn, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
if contours:
    main = max(contours, key=cv2.contourArea)
else:
    raise RuntimeError("无有效轮廓")
mask_filled = np.zeros_like(mask_conn)
cv2.drawContours(mask_filled, [main], -1, 255, -1)

# 关键修复: 轻微 erosion 收缩回真实边缘 (抵消之前的膨胀)
mask_eroded = cv2.erode(mask_filled, np.ones((3, 3), np.uint8), iterations=1)

# 再次排除
mask_eroded[exclude_mask > 0] = 0

print(f'[6] 修补+收缩后: {(mask_eroded>0).sum():,} px')

# ============================================================
# 7. 边界提取
# ============================================================
contours, _ = cv2.findContours(mask_eroded, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)
arc = cv2.arcLength(main, True)

for eps_factor in [0.0006, 0.0008, 0.0010, 0.0012, 0.0015, 0.0018, 0.0020, 0.0025, 0.0030]:
    poly_px = cv2.approxPolyDP(main, eps_factor * arc, True).reshape(-1, 2)
    if 120 <= len(poly_px) <= 260:
        break
print(f'[7] 边界顶点: {len(poly_px)} (eps={eps_factor:.4f})')

# ============================================================
# 8. 压边文字拉平 (保留原有逻辑但用新边界)
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
            if 0 <= mid[0] < w and 0 <= mid[1] < h and mask_eroded[mid[1], mid[0]] > 0:
                continue
            if np.linalg.norm(p2 - p1) > 250:
                continue
            new_pts = np.linspace(0, 1, len(grp))[:, None] * (p2 - p1) + p1
            for k, idx in enumerate(grp):
                poly[idx] = new_pts[k].astype(np.int32)
            changed = True
            print(f'    拉平文字 #{i}: 索引 {s_idx}-{e_idx}, {len(grp)}点, 距边界{d_min:.1f}px')

    if changed:
        cleaned = [poly[0]]
        for p in poly[1:]:
            if (p[0] != cleaned[-1][0]) or (p[1] != cleaned[-1][1]):
                cleaned.append(p)
        poly = np.array(cleaned, dtype=np.int32)
    return poly

poly_px = flatten_boundary_at_labels(poly_px, H, W, rgb, pad=40, min_area=200)
print(f'[8] 拉平后顶点: {len(poly_px)}')

# 用最终边界重建掩膜
mask_final = np.zeros((H, W), dtype=np.uint8)
cv2.drawContours(mask_final, [poly_px.reshape(-1, 1, 2)], -1, 255, -1)

# 最后再排除一次 (安全网)
mask_final[exclude_mask > 0] = 0

# 轻微闭运算平滑锯齿 (最小限度)
mask_final = cv2.morphologyEx(mask_final, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8), iterations=1)
print(f'[8] 最终掩膜: {(mask_final>0).sum():,} px')

# ============================================================
# 9. 去文字图
# ============================================================
if (jizhou_core > 0).any():
    mean_color = rgb[jizhou_core > 0].mean(axis=0).astype(np.uint8)
else:
    mean_color = np.array([173, 228, 207], dtype=np.uint8)

inside = mask_final > 0
cleaned = rgb.copy()
cleaned[inside] = mean_color

# ============================================================
# 10. 保存输出
# ============================================================
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
        'version': 'v2-fixed',
        'fixes': ['tighter_color_threshold', 'neighbor_color_exclusion', 'reduced_morphology',
                  'erosion_shrinkback', 'higher_fill_threshold'],
        'points': pts
    }, f, ensure_ascii=False, indent=2)

# 三栏对比
thumb_w, thumb_h = W // 2, H // 2
comparison = np.zeros((thumb_h, thumb_w * 3, 3), dtype=np.uint8)
comparison[:, 0:thumb_w] = cv2.resize(rgb, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
comparison[:, thumb_w:2*thumb_w] = cv2.resize(cleaned, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
comparison[:, 2*thumb_w:3*thumb_w] = cv2.resize(overlay, (thumb_w, thumb_h), interpolation=cv2.INTER_AREA)
Image.fromarray(comparison).save(os.path.join(OUTDIR, 'comparison_preview.png'))

# 叠在原图上的验证图 (半透明)
verify = rgb.astype(float) * 0.6 + np.stack([mask_final]*3, axis=-1).astype(float) * 0.4 * np.array([0,1,1])
verify = np.clip(verify, 0, 255).astype(np.uint8)
cv2.polylines(verify, [poly_px], True, (255, 0, 0), 2)
Image.fromarray(verify).save(os.path.join(OUTDIR, 'verify_overlay.png'))

print(f'[done] 输出到 {OUTDIR}/')
print(f'    mask_clean.png, text_erased.png, boundary_overlay.png')
print(f'    comparison_preview.png, verify_overlay.png, boundary_points.json')
print(f'    边界点数: {len(pts)}, 掩膜面积: {(mask_final>0).sum():,} px')
