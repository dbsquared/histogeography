#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v4 边界后处理：修复v3的5处局部瑕疵。

问题清单（从截图识别）：
  #1 西南角(邺城附近): 边界向内凹坑 → 填充平滑
  #2 东北(渤海郡): V形白线尖坑 → 局部平滑消除
  #3 北界(中山国): 向上凸小包 → 裁回青色区
  #4 东北角: 外凸方块 → 裁回青色区
  #5 南缘(河内/东郡): 整体南伸过多 → 南半部裁剪

方法：
  1) 加载v3边界点 + 原图
  2) 对每个边界点做颜色验证：是否在冀州浅青色上？
     - 外溢点(不在青色上): 沿法向收缩回青色边缘
     - 内陷点(在青色内部但形成凹陷): 用局部样条填充
  3) 曲率检测 + 尖角平滑(角度<阈值→B样条局部拟合)
  4) 输出修正后的boundary_points.json + overlay
"""
import os, json, math, copy
import numpy as np
import cv2
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_IMG = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
PTS_V3 = os.path.join(HERE, 'jizhou_step1_v3', 'boundary_points.json')
ANCHORS = os.path.join(HERE, 'jizhou_anchor_table.json')
BASE_MAP = os.path.join(HERE, 'china_full_v3.png')
OUTDIR = os.path.join(HERE, 'jizhou_step1_v4')
OVERLAY_DIR = os.path.join(HERE, 'jizhou_overlay_v4')
os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(OVERLAY_DIR, exist_ok=True)

# ============================================================
# 0. 加载数据
# ============================================================
rgb = np.array(Image.open(SRC_IMG).convert('RGB'))
H_img, W_img = rgb.shape[:2]
r = rgb[:,:,0].astype(int); g = rgb[:,:,1].astype(int); b = rgb[:,:,2].astype(int)

with open(PTS_V3, encoding='utf-8') as f:
    data_v3 = json.load(f)
pts_v3 = np.array([[p['px'], p['py']] for p in data_v3['points']], dtype=float)
n_pts = len(pts_v3)
print(f'[0] 加载v3: {n_pts}个边界点, 图像{W_img}x{H_img}')

# 冀州青色判定函数 (与v3一致但稍宽松用于裁剪验证)
def is_jizhou_cyan(r_px, g_px, b_px):
    """判断像素是否为冀州浅青色或其内部"""
    core = (g_px > r_px + 30) & (g_px > b_px + 8) & (g_px >= 170) & (g_px <= 248)
    return core

# 对整张图的快速判定
cyan_map = is_jizhou_cyan(r, g, b).astype(np.uint8) * 255
print(f'[0] 青色像素总计: {(cyan_map>0).sum():,}')

# ============================================================
# 1. 颜色裁剪：把外溢到非青色区的点沿法向收缩回来
# ============================================================
def normal_direction(pts, idx):
    """计算idx处的外法向（指向外部）"""
    n = len(pts)
    prev = pts[(idx - 1) % n]
    next_pt = pts[(idx + 1) % n]
    tangent = next_pt - prev
    # 法向 = 切线顺时针旋转90° (对于逆时针多边形指向外)
    normal = np.array([tangent[1], -tangent[0]])
    norm = np.linalg.norm(normal)
    if norm > 0:
        normal /= norm
    return normal


def shrink_to_cyan(pt, normal, max_dist=40, step=2):
    """沿法向方向搜索，找到青色区域的边缘"""
    for d in range(0, int(max_dist), step):
        test = pt + normal * d
        ix, iy = int(round(test[0])), int(round(test[1]))
        if 0 <= ix < W_img and 0 <= iy < H_img:
            if cyan_map[iy, ix] > 0:
                return test.copy()
    return pt.copy()


print('[1] 颜色裁剪...')
pts_fixed = pts_v3.copy()

# 标记每个点的颜色状态
color_ok = []
for i in range(n_pts):
    ix, iy = int(round(pts_v3[i, 0])), int(round(pts_v3[i, 1]))
    in_bounds = 0 <= ix < W_img and 0 <= iy < H_img
    is_cyan = cyan_map[iy, ix] > 0 if in_bounds else False
    color_ok.append(is_cyan)

bad_count = sum(1 for c in color_ok if not c)
print(f'    非青色点上: {bad_count}/{n_pts}')

# 收缩外溢点 (向外溢出的点，即不在青色上的)
for i in range(n_pts):
    if not color_ok[i]:
        normal = normal_direction(pts_fixed, i)
        # 法向朝外收缩 — 如果点在外面，需要往里走（反向）
        new_pt = shrink_to_cyan(pts_fixed[i], -normal, max_dist=50, step=2)
        dist_moved = np.linalg.norm(new_pt - pts_fixed[i])
        if dist_moved > 1:
            pts_fixed[i] = new_pt

# 再次检查
bad_after = 0
for i in range(n_pts):
    ix, iy = int(round(pts_fixed[i,0])), int(round(pts_fixed[i,1]))
    if 0 <= ix < W_img and 0 <= iy < H_img:
        if cyan_map[iy, ix] == 0:
            bad_after += 1
print(f'    裁剪后仍有问题点: {bad_after}')

# ============================================================
# 2. 曲率检测 + 尖角平滑
# ============================================================
def turning_angles(pts):
    """计算每个顶点的转向角(度)，正值=左转，负值=右转"""
    n = len(pts)
    angles = []
    for i in range(n):
        prev = pts[(i - 1) % n] - pts[i]
        next_pt = pts[(i + 1) % n] - pts[i]
        cos_a = np.dot(prev, next_pt) / (np.linalg.norm(prev) * np.linalg.norm(next_pt) + 1e-10)
        cos_a = np.clip(cos_a, -1, 1)
        # 叉积决定方向
        cross = prev[0] * next_pt[1] - prev[1] * next_pt[0]
        angle = math.degrees(math.acos(cos_a))
        if cross < 0:
            angle = -angle
        angles.append(angle)
    return angles


def smooth_segment(pts, start, end, window=7):
    """对一段边界用滑动平均平滑"""
    result = pts.copy()
    n = len(pts)
    for i in range(start, end + 1):
        total = np.zeros(2)
        weight_sum = 0
        for w in range(-window, window + 1):
            j = (i + w) % n
            wgt = 1.0 / (1.0 + abs(w))
            total += pts[j] * wgt
            weight_sum += wgt
        result[i] = total / weight_sum
    return result


angles = turning_angles(pts_fixed)
sharp_inward = []   # 尖锐内陷(大正角 = 左转太急 = 向内凹)
sharp_outward = []  # 尖锐外凸(大负角 = 右转太急 = 向外突)
SPIKE_THRESH = 50  # 度

for i, a in enumerate(angles):
    if abs(a) > SPIKE_THRESH:
        if a > 0:
            sharp_inward.append((i, a))
        else:
            sharp_outward.append((i, a))

print(f'[2] 尖角检测: {len(sharp_inward)}个内陷(>+{SPIKE_THRESH}°), '
      f'{len(sharp_outward)}个外凸(<-{SPIKE_THRESH}°)')
for idx, ang in sorted(sharp_inward + sharp_outward, key=lambda x: x[1], reverse=True)[:15]:
    print(f'    点#{idx}: 角度={ang:+.1f}° 位置({pts_fixed[idx,0]:.0f},{pts_fixed[idx,1]:.0f})')

# 对所有尖角区域做局部平滑
pts_smooth = pts_fixed.copy()
smoothed_regions = set()
SPIKE_WINDOW = 9  # 平滑窗口半径

for idx, ang in sharp_inward + sharp_outward:
    # 避免重复平滑重叠区域
    already = any(idx in range(s-SPIKE_WINDOW, s+SPIKE_WINDOW+1) for s in smoothed_regions)
    if already:
        continue
    for s in range(max(0, idx-SPIKE_WINDOW), min(n_pts, idx+SPIKE_WINDOW+1)):
        smoothed_regions.add(s)
    pts_smooth = smooth_segment(pts_smooth, max(0,idx-SPIKE_WINDOW),
                                 min(n_pts-1, idx+SPIKE_WINDOW), window=5)
print(f'    平滑了 {len(smoothed_regions)} 个点的区域')

# ============================================================
# 3. B样条全局平滑 (保持形状特征的同时消除微小抖动)
# ============================================================
try:
    from scipy.interpolate import splprep, splev
    # 闭合参数化
    tck, u = splprep([pts_smooth[:,0].tolist(), pts_smooth[:,1].tolist()],
                      s=len(pts_smooth)*3, per=True, k=3)  # s控制平滑度
    u_new = np.linspace(0, 1, len(pts_smooth))
    xspline, yspline = splev(u_new, tck)
    pts_spline = np.column_stack([xspline, yspline])

    # 确保样条结果不跑太远 — 把偏离原始超过20px的点拉回来
    final_pts = []
    for i in range(len(pts_spline)):
        orig = pts_smooth[i]
        spl = pts_spline[i]
        dist = np.linalg.norm(spl - orig)
        if dist > 25:
            # 插值拉回
            t_clip = 25.0 / dist
            final_pts.append(orig * (1-t_clip) + spl * t_clip)
        else:
            final_pts.append(spl)
    pts_final = np.array(final_pts)
    print('[3] B样条平滑完成 (scipy)')
except ImportError:
    print('[3] scipy不可用,跳过B样条')
    pts_final = pts_smooth.copy()

# ============================================================
# 4. 最终颜色安全检查 + 二次裁剪
# ============================================================
final_check_bad = 0
for i in range(len(pts_final)):
    ix, iy = int(round(pts_final[i, 0])), int(round(pts_final[i, 1]))
    if 0 <= ix < W_img and 0 <= iy < H_img:
        if cyan_map[iy, ix] == 0:
            # 再尝试收缩
            normal = normal_direction(pts_final, i)
            new_p = shrink_to_cyan(pts_final[i], -normal, max_dist=60, step=3)
            pts_final[i] = new_p
            final_check_bad += 1
print(f'[4] 二次裁剪修复: {final_check_bad} 点')

# ============================================================
# 5. 特别针对问题#5(南缘下伸过多)：南部点整体微调北移
# ============================================================
# 找出y值最大的30%的点(南缘)
y_vals = pts_final[:, 1]
y_thresh = np.percentile(y_vals, 70)  # 最南的30%
south_mask = y_vals >= y_thresh
south_indices = np.where(south_mask)[0]
if len(south_indices) > 0:
    south_center_y = np.mean(y_vals[south_mask])
    print(f'[5] 南缘: {len(south_indices)}个点, 平均Y={south_center_y:.0f}, Y范围[{y_vals[south_indices].min():.0f},{y_vals[south_indices].max():.0f}]')
    # 对最南部的15%做轻微北移(缩小3px)
    y_very_high = np.percentile(y_vals, 85)
    very_south = y_vals >= y_very_high
    for i in np.where(very_south)[0]:
        # 只在该点确实偏出青色时才移
        ix, iy = int(round(pts_final[i,0])), int(round(pts_final[i,1]))
        if 0 <= ix < W_img and 0 <= iy < H_img and cyan_map[iy, ix] == 0:
            pts_final[i, 1] -= 6  # 北移6像素
    print(f'[5] 南缘超界点北移: {very_south.sum()} 点')

# ============================================================
# 6. 保存修正后的边界点
# ============================================================

# 去重连续重复点
cleaned = [pts_final[0]]
for p in pts_final[1:]:
    if np.linalg.norm(p - cleaned[-1]) > 0.5:
        cleaned.append(p)
pts_final = np.array(cleaned)
print(f'[6] 去重后: {len(pts_final)} 点')

out_pts = [{'seq': i, 'px': int(round(p[0])), 'py': int(round(p[1]))}
           for i, p in enumerate(pts_final)]
with open(os.path.join(OUTDIR, 'boundary_points.json'), 'w', encoding='utf-8') as f:
    json.dump({
        'source_image': data_v3['source_image'],
        'image_size': data_v3['image_size'],
        'version': 'v4-postprocess_fix',
        'fixes_applied': ['color_clipping', 'spike_smoothing', 'bspline_smooth',
                          'secondary_clipping', 'south_edge_trim'],
        'original_version': 'v3',
        'points': out_pts
    }, f, ensure_ascii=False, indent=2)

# ============================================================
# 7. 生成可视化对比图
# ============================================================
poly_v3 = pts_v3.astype(np.int32).reshape(-1, 1, 2)
poly_v4 = pts_final.astype(np.int32).reshape(-1, 1, 2)

# v3 vs v4 叠加对比
compare = rgb.copy()
cv2.polylines(compare, [poly_v3], True, (255, 100, 100), 2)   # v3: 浅红
cv2.polylines(compare, [poly_v4], True, (0, 255, 0), 2)      # v4: 绿
Image.fromarray(compare).save(os.path.join(OUTDIR, 'v3_vs_v4_overlay.png'))

# v4 单独叠加
overlay_v4 = rgb.copy()
cv2.polylines(overlay_v4, [poly_v4], True, (255, 0, 0), 3)
Image.fromarray(overlay_v4).save(os.path.join(OUTDIR, 'boundary_overlay.png'))

# 半透明验证
verify = rgb.astype(float) * 0.55 + np.full_like(rgb.astype(float), 0) 
mask_v4 = np.zeros((H_img, W_img), dtype=np.uint8)
cv2.fillPoly(mask_v4, [pts_final.astype(np.int32)], 255)
alpha_layer = np.stack([np.zeros_like(mask_v4), mask_v4, mask_v4], axis=-1).astype(float) * 0.45
verify = np.clip(rgb.astype(float)*0.55 + alpha_layer, 0, 255).astype(np.uint8)
cv2.polylines(verify, [poly_v4], True, (255, 0, 0), 2)
Image.fromarray(verify).save(os.path.join(OUTDIR, 'verify_overlay.png'))

print(f'[7] 可视化已保存到 {OUTDIR}/')

# ============================================================
# 8. Overlay 地形图 (复用overlay逻辑)
# ============================================================
BW, BH = 15600, 9600
LON0, LON1 = 75.0, 140.0
LAT0, LAT1 = 15.0, 55.0

def geo_to_big(lon, lat):
    bx = (lon - LON0) / (LON1 - LON0) * BW
    by = (LAT1 - lat) / (LAT1 - LAT0) * BH
    return bx, by

# 加载锚点配准
anchors = json.load(open(ANCHORS, encoding='utf-8'))
axy = [(a['px'], a['py']) for a in anchors]
alon = [a['lon'] for a in anchors]
alat = [a['lat'] for a in anchors]

def basis1(x, y, deg):
    terms = [1.0]
    for p in range(1, deg + 1):
        for j in range(p + 1):
            terms.append(float(x) ** (p - j) * float(y) ** j)
    return terms

def fit_poly(pts, vals, deg):
    A = np.array([basis1(x, y, deg) for x, y in pts], dtype=float)
    coef, *_ = np.linalg.lstsq(A, np.array(vals, dtype=float), rcond=None)
    return coef, deg

def predict(coef, deg, x, y):
    return float(np.dot(coef[:len(basis1(x,y,deg))], basis1(x,y,deg)))

coef_lon_q, dq = fit_poly(axy, alon, 2)
coef_lat_q, _ = fit_poly(axy, alat, 2)

def px_to_geo(x, y):
    return predict(coef_lon_q, dq, x, y), predict(coef_lat_q, dq, x, y)

SHIFT_DEG_LON = 0.0
SHIFT_DEG_LAT = 0.0

# 映射边界到大图
big_pts = []
lons, lats = [], []
for pt in pts_final:
    lon, lat = px_to_geo(float(pt[0]), float(pt[1]))
    lon += SHIFT_DEG_LON; lat += SHIFT_DEG_LAT
    lons.append(lon); lats.append(lat)
    bx, by = geo_to_big(lon, lat)
    big_pts.append((bx, by))
if big_pts[0] != big_pts[-1]:
    big_pts.append(big_pts[0])

print(f'[8] 映射 -> lon[{min(lons):.2f},{max(lons):.2f}] lat[{min(lats):.2f},{max(lats):.2f}]')

PREV_W = 2600
PREV_H = int(BH * PREV_W / BW)
scale_x, scale_y = BW / PREV_W, BH / PREV_H

base = Image.open(BASE_MAP).convert('RGB').resize((PREV_W, PREV_H))
prev_pts = [(int(bx/scale_x), int(by/scale_y)) for (bx,by) in big_pts]

R, Gc, Bc = 100, 180, 165

def make_overlay(fill_alpha, border_alpha, border_w):
    layer = Image.new('RGBA', (PREV_W, PREV_H), (0,0,0,0))
    d = ImageDraw.Draw(layer)
    d.polygon(prev_pts, fill=(R, Gc, Bc, fill_alpha))
    d.line(prev_pts, fill=(R, Gc, Bc, border_alpha), width=border_w, joint='curve')
    return Image.alpha_composite(base.convert('RGBA'), layer).convert('RGB')

for tag, fa, ba, bw in [('a70', 70, 220, 3), ('a50', 50, 220, 3), ('a90', 90, 230, 3)]:
    make_overlay(fa, ba, bw).save(os.path.join(OVERLAY_DIR, f'jizhou_overlay_{tag}.png'))
    print(f'    overlay_{tag}.png ✓')

# Zoom
zoom_w, zoom_h = 1200, 900
center_lon = (min(lons)+max(lons))/2
center_lat = (min(lats)+max(lats))/2
cbx, cby = geo_to_big(center_lon, center_lat)
zx0 = max(0, int(cbx/scale_x - zoom_w//2))
zy0 = max(0, int(cby/scale_y - zoom_h//2))

base_zoom = base.crop((zx0, zy0, zx0+zoom_w, zy0+zoom_h))
zoom_prev_pts = [(int(bx/scale_x-zx0), int(by/scale_y-zy0)) for (bx,by) in big_pts]

layer_z = Image.new('RGBA', (zoom_w, zoom_h), (0,0,0,0))
d_z = ImageDraw.Draw(layer_z)
d_z.polygon(zoom_prev_pts, fill=(R,Gc,Bc,70))
d_z.line(zoom_prev_pts, fill=(R,Gc,Bc,220), width=3, joint='curve')
oz = Image.alpha_composite(base_zoom.convert('RGBA'), layer_z).convert('RGB')
oz.save(os.path.join(OVERLAY_DIR, 'jizhou_overlay_a70_zoom_large.png'), quality=92)
print(f'    zoom_large.png ✓')

print(f'\n[done] v4后处理完成!')
print(f'    边界点: {len(pts_final)}')
print(f'    产物: {OUTDIR}/ + {OVERLAY_DIR}/')
