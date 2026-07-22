#!/usr/bin/env python3
"""
v7b 白线追踪 — 距离变换带宽法解决白线断裂问题

算法流程：
1. 青色掩膜（仅用于侧判定）
2. 检测白色线条（梯度过滤排除平坦背景）
3. 侧判定：8邻域一侧青色一侧非青色 → 真边界像素
4. ★ 距离变换带宽 ★：以所有真边界像素为种子，生成D像素宽的连续带
   （自动桥接≤2D像素的缺口，不依赖连通性）
5. 取带的外轮廓 = 冀州多边形
6. 轻量坐标平滑
"""

import cv2, numpy as np, json, os, sys

def imread_safe(path):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)

def imwrite_safe(path, img):
    ext = os.path.splitext(path)[1]
    result, buf = cv2.imencode(ext, img)
    if result:
        buf.tofile(path)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
OUTDIR = os.path.join(HERE, 'jizhou_step1_v7b')
os.makedirs(OUTDIR, exist_ok=True)

img = imread_safe(SRC)
if img is None:
    print(f'ERROR: cannot read {SRC}'); sys.exit(1)
H, W = img.shape[:2]
print(f'Image: {W}x{H}')

b, g, r = img[:,:,0].astype(int), img[:,:,1].astype(int), img[:,:,2].astype(int)

# ============================================================
# Phase 1: 青色掩膜（侧判定参考）
# ============================================================
cyan_raw = (g > r + 35) & (g > b + 10) & (g >= 175) & (g <= 245)
cyan_mask = (cyan_raw &
             ~((r > g + 15) & (r > b) & (r > 100)) |           # 并州
              ((np.abs(r-g) < 30) & (g > b + 10) & (g >= 200)) | # 司隶
              ((r < g - 20) & (b < g) & (g > 120) & (r < 150))| # 幽州
              ((g > r + 10) & (g > b) & (b < 180))               # 青州
            ).astype(np.uint8) * 255
# Fix logic: cyan_raw AND NOT (any neighbor)
bingzhou  = (r > g + 15) & (r > b) & (r > 100)
sili      = (np.abs(r - g) < 30) & (g > b + 10) & (g >= 200)
youzhou   = (r < g - 20) & (b < g) & (g > 120) & (r < 150)
qingzhou  = (g > r + 10) & (g > b) & (b < 180)
cyan_mask = (cyan_raw & ~(bingzhou|sili|youzhou|qingzhou)).astype(np.uint8)*255
print(f'Cyan mask: {(cyan_mask>0).sum():,} px')

# ============================================================
# Phase 2: 白色线检测（梯度过滤）
# ============================================================
lo_w = (r > 210) & (g > 210) & (b > 210)
hi_w = (r > 185) & (g > 185) & (b > 185) & \
       (np.abs(r-g)<20) & (np.abs(g-b)<20) & (np.abs(r-b)<20)
white_any = lo_w | hi_w

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
gmag = np.sqrt(gx**2 + gy**2)
white_line = white_any & (gmag > 12)
print(f'White line pixels: {white_line.sum():,}')

# ============================================================
# Phase 3: 侧判定
# ============================================================
cy = np.pad(cyan_mask > 0, 1, mode='constant', constant_values=False)
n_cyn = np.zeros((H,W), dtype=np.int32)
for dy,dx in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
    n_cyn += cy[1+dy:H+dy+1, 1+dx:W+dx+1].astype(np.int32)

border_px = white_line & (n_cyn >= 1) & ((8-n_cyn) >= 1)
border_u8 = (border_px * 255).astype(np.uint8)
print(f'Border pixels (side-test): {border_px.sum():,}')
imwrite_safe(os.path.join(OUTDIR, '00_border_px.png'), border_u8)

# ============================================================
# Phase 4: ★ 距离变换带宽法 ★
#
# 不再依赖连通性。把14k个边界碎片当作"种子点集合"，
# 计算每个像素到最近种子的距离，阈值<D的像素组成一条
# 连续的"带宽"。即使种子之间有≤2D的大缺口也会被桥接。
# ============================================================

# 距离变换：每个像素到最近边界像素的欧氏距离
dist = cv2.distanceTransform(border_u8, cv2.DIST_L2, 5)

# 带宽参数 D=18：桥接≤36px的缺口（足够覆盖文字标签宽度）
D = 18
band = (dist < D).astype(np.uint8) * 255

imwrite_safe(os.path.join(OUTDIR, '01_distance_band.png'), band)
print(f'Distance band (D={D}): {(band>0).sum():,} px')

# 形态学闭运算填平微小残留孔洞
kc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9,9))
band_closed = cv2.morphologyEx(band, cv2.MORPH_CLOSE, kc, iterations=2)

# 取最大连通分量（应该只有一个大的外环了）
n_lbl, lbl_map, stats, _ = cv2.connectedComponentsWithStats(band_closed)
areas = [(stats[i,cv2.CC_STAT_AREA], i) for i in range(1,n_lbl)]
areas.sort(reverse=True)
best_label = areas[0][1]
ring = (lbl_map == best_label).astype(np.uint8) * 255
print(f'Ring component: area={(ring>0).sum():,}, total_components={len(areas)}')
imwrite_safe(os.path.join(OUTDIR, '02_ring.png'), ring)

# ============================================================
# Phase 5: 提取轮廓
# ============================================================
contours, _ = cv2.findContours(ring, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
outer = max(contours, key=cv2.contourArea)
print(f'Raw contour vertices: {len(outer)}')

eps = 0.0025 * cv2.arcLength(outer, True)
simple = cv2.approxPolyDP(outer, eps, True)
pts_raw = simple.reshape(-1,2).copy().astype(float)
print(f'Simplified: {len(pts_raw)} vertices')

# 高斯平滑坐标
from scipy.ndimage import gaussian_filter1d
pts_s = np.zeros_like(pts_raw)
pts_s[:,0] = gaussian_filter1d(pts_raw[:,0], sigma=3)
pts_s[:,1] = gaussian_filter1d(pts_raw[:,1], sigma=3)
pts_list = np.round(pts_s).astype(int).tolist()

# ============================================================
# Phase 6: 填充 + 微裁剪
# ============================================================
final_mask = np.zeros((H,W), dtype=np.uint8)
cv2.fillPoly(final_mask, [np.array(pts_list)], 255)

# 只裁剪明显超出青色区域的孤立小突起（<1000px的独立连通块 outlier）
outlier = (final_mask>0)&(cyan_mask==0)
out_n = outlier.sum()
final_mask[outlier] = 0

# 如果裁剪后产生新洞，重新提取轮廓
c2, _ = cv2.findContours(final_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
if c2:
    o2 = max(c2, key=cv2.contourArea)
    e2 = 0.002 * cv2.arcLength(o2, True)
    fc = cv2.approxPolyDP(o2, e2, True)
    pts_final = fc.reshape(-1,2).tolist()
else:
    pts_final = pts_list

final_area = (final_mask>0).sum()
print(f'Final: {len(pts_final)} vertices, {final_area:,} px (clipped {out_n:,} outliers)')

# ============================================================
# 保存
# ============================================================
with open(os.path.join(OUTDIR,'boundary_points.json'),'w') as f:
    json.dump({'points':pts_final,'count':len(pts_final)}, f, ensure_ascii=False, indent=2)

# verify_overlay
ov = img.copy()
mb = final_mask>0
ov[mb] = ov[mb].astype(float)*0.35 + np.array([173,228,207],dtype=float)*0.65
ov = ov.astype(np.uint8)
cv2.polylines(ov,[np.array(pts_final)],True,(0,0,255),2)
imwrite_safe(os.path.join(OUTDIR,'verify_overlay.png'), ov)

# boundary_overlay
bd = img.copy()
cv2.polylines(bd,[np.array(pts_final)],True,(0,0,255),2)
imwrite_safe(os.path.join(OUTDIR,'boundary_overlay.png'), bd)

# mask
imwrite_safe(os.path.join(OUTDIR,'mask_clean.png'), final_mask)

# comparison
comp = np.hstack([img,
    cv2.bitwise_and(img,img,mask=final_mask),
    bd])
imwrite_safe(os.path.join(OUTDIR,'comparison_preview.png'), comp)

# Save distance transform heatmap for debugging
dist_viz = (np.clip(dist / D * 255, 0, 255)).astype(np.uint8)
dist_color = cv2.applyColorMap(dist_viz, cv2.COLORMAP_JET)
imwrite_safe(os.path.join(OUTDIR,'00_distance_heatmap.png'), dist_color)

print(f'\nDone -> {OUTDIR}')
