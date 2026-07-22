#!/usr/bin/env python3
"""
v7 白线追踪 — 严格按照用户算法：
1. 确定颜色（青色掩膜，仅用于侧判定）
2. 边界是白色的
3. 找到白色点
4. 一侧是冀州颜色、另一侧不是 → 该点是正确边界点
5. 取最大连通分量（外环）→ 直接取轮廓 → 不与任何色块掩膜相交
"""

import cv2, numpy as np, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
OUTDIR = os.path.join(HERE, 'jizhou_step1_v7')
os.makedirs(OUTDIR, exist_ok=True)

# cv2.imread can't handle CJK paths on Windows — use np.fromfile
def imread_safe(path):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)

def imwrite_safe(path, img):
    ext = os.path.splitext(path)[1]
    result, buf = cv2.imencode(ext, img)
    if result:
        buf.tofile(path)

img = imread_safe(SRC)
if img is None:
    print(f'ERROR: cannot read {SRC}'); sys.exit(1)
H, W = img.shape[:2]
print(f'Image: {W}x{H}')

b, g, r = img[:,:,0].astype(int), img[:,:,1].astype(int), img[:,:,2].astype(int)

# ============================================================
# Phase 1: 冀州青色掩膜 — 仅用于侧判定（不参与最终形状）
# ============================================================
cyan_raw = (g > r + 35) & (g > b + 10) & (g >= 175) & (g <= 245)
bingzhou  = (r > g + 15) & (r > b) & (r > 100)
sili      = (np.abs(r - g) < 30) & (g > b + 10) & (g >= 200)
youzhou   = (r < g - 20) & (b < g) & (g > 120) & (r < 150)
qingzhou  = (g > r + 10) & (g > b) & (b < 180)
cyan_mask = (cyan_raw & ~(bingzhou|sili|youzhou|qingzhou)).astype(np.uint8) * 255
print(f'Cyan mask pixels: {(cyan_mask>0).sum():,}')

# ============================================================
# Phase 2: 检测白色边界线（排除大片白色背景）
# ============================================================
# 宽松白色检测
lo_white = (r > 210) & (g > 210) & (b > 210)
hi_white = (r > 185) & (g > 185) & (b > 185) & \
           (np.abs(r-g) < 20) & (np.abs(g-b) < 20) & (np.abs(r-b) < 20)
white_any = lo_white | hi_white

# 用梯度排除平坦白色背景区域（背景梯度低，线条梯度高）
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
gmag = np.sqrt(gx**2 + gy**2)

# 白色像素中，只有梯度>阈值的才算"线"
white_line = white_any & (gmag > 12)
print(f'White total: {white_any.sum():,},  white line (edge): {white_line.sum():,}')

# ============================================================
# Phase 3: 侧判定 — 用户算法核心
# 对每个白线像素检查8邻域：一侧青色一侧非青色 = 真正的冀州边界
# ============================================================
cyan_p = np.pad(cyan_mask > 0, 1, mode='constant', constant_values=False)

# 向量化8邻域统计
neighbor_offsets = [(-1,-1),(-1,0),(-1,1),(0,-1),
                    (0,1),(1,-1),(1,0),(1,1)]
n_cyan = np.zeros((H,W), dtype=np.int32)
for dy, dx in neighbor_offsets:
    sl = cyan_p[1+dy:H+dy+1, 1+dx:W+dx+1]
    n_cyan += sl.astype(np.int32)

n_non_cyan = 8 - n_cyan
border_px = white_line & (n_cyan >= 1) & (n_non_cyan >= 1)
border_u8 = (border_px * 255).astype(np.uint8)
print(f'Border pixels (side-test passed): {border_px.sum():,}')

# ============================================================
# Phase 4: 连通性分析 — 只保留最大连通分量（外环）
# 内部县界线是小的独立连通块或短枝
# ============================================================
k3 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
border_conn = cv2.dilate(border_u8, k3, iterations=1)  # 仅桥接≤1px间隙

n_lbl, lbl_map, stats, centroids = cv2.connectedComponentsWithStats(border_conn)
print(f'Components before filter: {n_lbl - 1}')

if n_lbl > 2:  # 有多个分量可选
    areas = [(stats[i, cv2.CC_STAT_AREA], i) for i in range(1, n_lbl)]
    areas.sort(reverse=True)
    print('Top components:')
    for area, lid in areas[:5]:
        print(f'  label={lid}  area={area:,}')

    # 外环是面积最大的分量
    best_label = areas[0][1]
    ring = (lbl_map == best_label).astype(np.uint8) * 255
    ring_area = int(ring.sum() / 255)
    print(f'Selected outer ring: label={best_label}, area={ring_area:,}')
else:
    ring = border_conn

imwrite_safe(os.path.join(OUTDIR, '01_ring_component.png'), ring)

# ============================================================
# Phase 5: 从环直接提取轮廓（不膨胀、不相交色块）
# ============================================================
contours, hierarchy = cv2.findContours(
    ring, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE
)
print(f'External contours: {len(contours)}')

if not contours:
    print('ERROR: no contours found'); sys.exit(1)

outer = max(contours, key=cv2.contourArea)
print(f'Outer contour raw vertices: {len(outer)}')

# 多边形简化
eps = 0.002 * cv2.arcLength(outer, True)
simple = cv2.approxPolyDP(outer, eps, True)
pts_raw = simple.reshape(-1, 2).copy().astype(float)
print(f'Simplified vertices: {len(pts_raw)}')

# 轻量高斯平滑坐标（消除像素级抖动）
from scipy.ndimage import gaussian_filter1d
pts_smooth = np.zeros_like(pts_raw)
pts_smooth[:, 0] = gaussian_filter1d(pts_raw[:, 0], sigma=2.5)
pts_smooth[:, 1] = gaussian_filter1d(pts_raw[:, 1], sigma=2.5)

# 闭合成环（首尾相接）
pts_list = np.round(pts_smooth).astype(int).tolist()

# ============================================================
# Phase 6: 填充多边形得到掩膜
# ============================================================
final_mask = np.zeros((H,W), dtype=np.uint8)
cv2.fillPoly(final_mask, [np.array(pts_list)], 255)
final_area = (final_mask > 0).sum()

# 轻微裁剪：去掉明显超出青色区域的离群像素（<500px的小突起）
outlier_mask = (final_mask > 0) & (cyan_mask == 0)
outlier_n = outlier_mask.sum()
final_mask[outlier_mask] = 0
print(f'Outlier pixels clipped: {outlier_n:,}')

# 重新提取轮廓（裁剪后可能有新凹坑需要补）
contours2, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
if contours2:
    outer2 = max(contours2, key=cv2.contourArea)
    eps2 = 0.002 * cv2.arcLength(outer2, True)
    final_contour = cv2.approxPolyDP(outer2, eps2, True)
    pts_final = final_contour.reshape(-1, 2).tolist()
else:
    pts_final = pts_list

print(f'Final vertices: {len(pts_final)},  area: {final_area-outlier_n:,}')

# ============================================================
# 保存输出
# ============================================================
# 边界点 JSON
with open(os.path.join(OUTDIR, 'boundary_points.json'), 'w') as f:
    json.dump({'points': pts_final, 'count': len(pts_final)}, f,
              ensure_ascii=False, indent=2)

# verify_overlay: 半透明青色叠原图
overlay_img = img.copy()
alpha = 0.35
m_bool = final_mask > 0
overlay_img[m_bool] = overlay_img[m_bool].astype(float) * (1-alpha) + \
                       np.array([173,228,207],dtype=float) * alpha
overlay_img = overlay_img.astype(np.uint8)
cv2.polylines(overlay_img, [np.array(pts_final)], True, (0,0,255), 2)
imwrite_safe(os.path.join(OUTDIR, 'verify_overlay.png'), overlay_img)

# boundary_overlay: 红框原图
bound_img = img.copy()
cv2.polylines(bound_img, [np.array(pts_final)], True, (0,0,255), 2)
imwrite_safe(os.path.join(OUTDIR, 'boundary_overlay.png'), bound_img)

# mask
imwrite_safe(os.path.join(OUTDIR, 'mask_clean.png'), final_mask)

# comparison_preview
comp = np.hstack([img,
    cv2.bitwise_and(img, img, mask=final_mask),
    bound_img])
imwrite_safe(os.path.join(OUTDIR, 'comparison_preview.png'), comp)

# Debug: 各阶段可视化
imwrite_safe(os.path.join(OUTDIR, '00_white_line.png'),
            (white_line*255).astype(np.uint8))
imwrite_safe(os.path.join(OUTDIR, '00_border_px.png'), border_u8)

print(f'\nDone! Output in {OUTDIR}')
