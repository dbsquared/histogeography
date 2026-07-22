#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v5b: 补丁 — 填充北界V形缺口等残留凹缺。

问题：v5 的 25×25 闭运算桥接了大部分道路锯齿，
     但某些特别窄深的切口（多条叠加线重叠处）仍残留。

方案：在 v5 边界上做"凹缺检测+填充"：
  1. 计算边界的局部凸包（滑动窗口）
  2. 检测向内偏离凸包超过阈值的点 → 凹缺
  3. 用直线/样条替换凹缺区域
"""
import os, json, math, numpy as np, cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
V5_DIR = os.path.join(HERE, 'jizhou_step1_v5')
OUTDIR = os.path.join(HERE, 'jizhou_step1_v5b')
os.makedirs(OUTDIR, exist_ok=True)

SRC = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = rgb.shape[:2]

# ---- 读入 v5 边界 ----
with open(os.path.join(V5_DIR, 'boundary_points.json'), encoding='utf-8') as f:
    data = json.load(f)
pts = np.array([[p['px'], p['py']] for p in data['points']], dtype=np.int32)
n = len(pts)
print(f'[0] v5 边界: {n} 点')

# ---- 1. 凹缺检测 ----
# 对每个点，取前后 window//2 点做局部参考
# 如果该点显著内凹于局部弦线，标记为需要修正

def detect_concavities(points, window=30, depth_thresh=12):
    """检测边界上的凹陷区域。
    返回: list of (start_idx, end_idx, max_depth, fill_type)
    """
    n = len(points)
    concavities = []
    in_concavity = False
    conc_start = 0
    max_depth = 0
    max_depth_idx = 0

    for i in range(n):
        # 局部窗口的端点
        half = window // 2
        i_prev = (i - half + n) % n
        i_next = (i + half) % n

        p_prev = points[i_prev].astype(float)
        p_curr = points[i].astype(float)
        p_next = points[i_next].astype(float)

        # 弦线向量 (prev -> next)
        chord = p_next - p_prev
        chord_len = np.linalg.norm(chord)
        if chord_len < 1:
            continue
        chord_unit = chord / chord_len

        # 当前点到弦线的有符号距离
        # 正 = 在弦线左侧(外), 负 = 在弦线右侧(内凹)
        v = p_curr - p_prev
        cross = chord_unit[0] * v[1] - chord_unit[1] * v[0]
        # dot = np.dot(v, chord_unit)  # 沿弦线方向的投影

        depth = -cross  # 内凹深度（正值表示向内）

        if depth > depth_thresh:
            if not in_concavity:
                conc_start = i
                in_concavity = True
                max_depth = depth
                max_depth_idx = i
            else:
                if depth > max_depth:
                    max_depth = depth
                    max_depth_idx = i
        else:
            if in_concavity:
                conc_len = (i - conc_start) % n
                if conc_len >= 2:  # 至少跨越几个点
                    concavities.append((conc_start, i, max_depth, max_depth_idx))
                in_concavity = False

    # 处理跨过 0 点的情况
    if in_concavity:
        conc_len = (n - conc_start)
        if conc_len >= 2:
            concavities.append((conc_start, 0, max_depth, max_depth_idx))

    return concavities


concavities = detect_concavities(pts, window=35, depth_thresh=9)
print(f'[1] 检测到 {len(concavities)} 个凹缺:')
for ci, (s, e, d, mi) in enumerate(concavities):
    span = (e - s) % n
    print(f'    #{ci+1}: 点{s}->{e} (跨度{span}点), 最大深度{d:.1f}px @点{mi}')

# ---- 2. 填充凹缺 ----
pts_fixed = pts.copy()
fixed_count = 0

for ci, (start_i, end_i, max_depth, mid_idx) in enumerate(concavities):
    span = (end_i - start_i) % n
    if span < 2 or span > n // 4:
        continue  # 太小或太大跳过

    # 收集凹缺区域的点索引
    if end_i > start_i:
        idx_range = list(range(start_i, end_i + 1))
    else:
        idx_range = list(range(start_i, n)) + list(range(0, end_i + 1))

    # 用两端点之间的直线/曲线替换凹缺
    p_start = pts[start_i].astype(float)
    p_end = pts[end_i].astype(float)

    if max_depth > 18:
        # 深缺口：用直线直接拉平
        for k, idx in enumerate(idx_range):
            t = k / max(len(idx_range) - 1, 1)
            new_pt = (1 - t) * p_start + t * p_end
            pts_fixed[idx] = new_pt.astype(np.int32)
            fixed_count += 1
    else:
        # 中浅缺口：用较小的平滑（保留一定曲率）
        # 取更宽的上下文做样条插值
        ctx_half = min(40, n // 8)
        ctx_s = (start_i - ctx_half + n) % n
        ctx_e = (end_i + ctx_half) % n

        if ctx_e > ctx_s:
            ctx_pts = pts[ctx_s:ctx_e+1].copy()
        else:
            ctx_pts = np.vstack([pts[ctx_s:], pts[:ctx_e+1]])

        # 简单线性插值在 start->end 区间内
        for k, idx in enumerate(idx_range):
            t = k / max(len(idx_range) - 1, 1)
            new_pt = (1 - t) * p_start + t * p_end
            pts_fixed[idx] = new_pt.astype(np.int32)
            fixed_count += 1

print(f'[2] 修复了 {fixed_count} 个点的凹缺')

# ---- 3. 颜色安全检查：确保修复后的点仍在青色区附近 ----
cr = rgb[:,:,0].astype(int); cg = rgb[:,:,1].astype(int); cb = rgb[:,:,2].astype(int)

# 冀州青色判定（宽松）
cyan_ok = (cg > cr + 25) & (cg >= 165) & (cb >= 145)

# 对每个修复后的点检查
out_of_bounds = 0
for i in range(len(pts_fixed)):
    x, y = int(pts_fixed[i, 0]), int(pts_fixed[i, 1])
    x = max(0, min(W-1, x))
    y = max(0, min(H-1, y))
    if not cyan_ok[y, x]:
        # 尝试沿法向收缩一步（最多5步）
        best_x, best_y = x, y
        found = False
        for step in range(1, 6):
            # 简单地往多边形中心方向收缩
            # 找最近的青色像素
            for dy in range(-step, step+1):
                for dx in range(-step, step+1):
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < W and 0 <= ny < H and cyan_ok[ny, nx]:
                        pts_fixed[i] = [nx, ny]
                        found = True
                        out_of_bounds += 1
                        break
                if found:
                    break
            if found:
                break

if out_of_bounds:
    print(f'[3] {out_of_bounds} 个修复点越界，已收缩回青色区')

# ---- 4. 去重 + 轻度平滑 ----
# 合并连续相同坐标的点
unique = [pts_fixed[0]]
for i in range(1, len(pts_fixed)):
    if not (pts_fixed[i][0] == unique[-1][0] and pts_fixed[i][1] == unique[-1][1]):
        unique.append(pts_fixed[i])
pts_final = np.array(unique, dtype=np.int32)
print(f'[4] 去重后: {len(pts_final)} 点 ({n} -> {len(pts_final)})')

# 轻度高斯平滑（对坐标用小核均值滤波）
from scipy.ndimage import uniform_filter1d
if len(pts_final) > 10:
    # 闭合曲线：首尾各复制一段做周期性处理
    pad = 15
    padded = np.vstack([pts_final[-pad:], pts_final, pts_final[:pad]])
    smoothed_x = uniform_filter1d(padded[:, 0].astype(float), size=5, mode='constant')
    smoothed_y = uniform_filter1d(padded[:, 1].astype(float), size=5, mode='constant')
    smoothed = np.column_stack([smoothed_x, smoothed_y])
    pts_final = smoothed[pad:-pad].round().astype(np.int32)

print(f'[4] 平滑后: {len(pts_final)} 点')

# ---- 5. 重建掩膜并输出 ----
mask_out = np.zeros((H, W), dtype=np.uint8)
cv2.fillPoly(mask_out, [pts_final], 255)

# 排除邻州颜色
bingzhou = (cr > cg + 15) & (cr > 130) & (cg < 190)
sili = (abs(cr - cg) < 30) & (cg > cb + 10) & (cg >= 200)
youzhou = (cg > cr + 25) & (cg <= 210) & (cr < 160)
qingzhou = (cg > 185) & (cb < 190) & (cg > cb + 25)
exclude = bingzhou | sili | youzhou | qingzhou
mask_out[exclude > 0] = 0

# 小闭运算修复断口
mask_out = cv2.morphologyEx(mask_out, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8), iterations=1)

print(f'[5] 最终掩膜: {(mask_out>0).sum():,} px')

# ---- 输出文件 ----
mean_c = [173, 228, 207]

# verify_overlay: 半透明青色叠红线
vf = rgb.astype(float)*0.55
alpha_layer = np.zeros_like(rgb, dtype=float)
alpha_layer[mask_out>0] = [0, 255, 255]  # cyan
vf += alpha_layer.astype(float) * 0.45
vf = np.clip(vf, 0, 255).astype(np.uint8)
cv2.polylines(vf, [pts_final.reshape(-1,1,2)], True, (255,0,0), 2)
Image.fromarray(vf).save(os.path.join(OUTDIR, 'verify_overlay.png'))

# boundary_overlay: 原图叠红线
ov = rgb.copy()
cv2.polylines(ov, [pts_final.reshape(-1,1,2)], True, (255,0,0), 3)
Image.fromarray(ov).save(os.path.join(OUTDIR, 'boundary_overlay.png'))

# v5 vs v5b 对比
poly_v5 = np.array([[p['px'],p['py']] for p in data['points']], np.int32)
cmp = rgb.copy()
cv2.polylines(cmp, [poly_v5.reshape(-1,1,2)], True, (255,150,150), 2)
cv2.polylines(cmp, [pts_final.reshape(-1,1,2)], True, (0,255,0), 2)
Image.fromarray(cmp).save(os.path.join(OUTDIR, 'v5_vs_v5b_comparison.png'))

# 放大对比图（聚焦问题区域）
zoom = ov.copy()  # 直接用boundary_overlay作为放大底图
Image.fromarray(zoom).save(os.path.join(OUTDIR, 'boundary_zoom.png'))

# 保存边界点
pts_out = [{'seq':i,'px':int(x),'py':int(y)} for i,(x,y) in enumerate(pts_final)]
with open(os.path.join(OUTDIR, 'boundary_points.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'source_image': data['source_image'],
        'image_size': [W,H],
        'version': 'v5b-notch-fill',
        'method': 'v5_base + concavity_detection(window=35,depth_thresh=9) + linear_fill',
        'parent_version': 'v5-overlay-agnostic',
        'points': pts_out}, f, ensure_ascii=False, indent=2)

print(f'\n[done] => {OUTDIR}/')
print(f'    边界{len(pts_final)}点, 面积{(mask_out>0).sum():,}px, 修复{len(concavities)}个凹缺')
