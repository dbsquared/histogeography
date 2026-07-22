#!/usr/bin/env python3
"""
v7c 轮廓吸附法（Contour Snapping）— 并州版

核心思路（与冀州v7c一致）：
1. 红色掩膜 → 给出并州的大致形状和拓扑（保证面积正确）
2. 侧判定白线边界像素 → 给出精确的边界线位置（避免路网/文字干扰）
3. 对红色掩膜的每个轮廓点，找最近的白线边界像素 → 吸附到白线上
4. 高斯平滑坐标消除抖动

优势：
- 不依赖白线的连通性（即使断成几百片也无所谓）
- 形状由红色掩膜决定（不会出现手指、缺块等拓扑错误）
- 位置由白线决定（不会跟着路网跑）

并州主色：red RGB≈(213,115,114)，主聚类(200,100,100)
邻州：幽州(绿)、冀州(青)、司隶(米黄)、凉州(黄橙)
"""

import cv2, numpy as np, json, os, sys
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

def imread_safe(path):
    return cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)

def imwrite_safe(path, img):
    ext = os.path.splitext(path)[1]
    result, buf = cv2.imencode(ext, img)
    if result:
        buf.tofile(path)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, '汉末十三州地图范例', '并州.png')
OUTDIR = os.path.join(HERE, 'bingzhou_step1_v7c')
os.makedirs(OUTDIR, exist_ok=True)

img = imread_safe(SRC)
H, W = img.shape[:2]
b, g, r = img[:,:,0].astype(int), img[:,:,1].astype(int), img[:,:,2].astype(int)
print(f'Image: {W}x{H}')

# ================================================================
# Phase 1: 红色掩膜（形状参考）— 并州主色
# ================================================================
bingzhou_raw = (r > g + 20) & (r > b + 20) & (r >= 170) & (r <= 245) & (g < 185) & (b < 205)

# 排除邻州
youzhou   = (g > r + 18) & (g > b + 8)  & (g > 110) & (r < 165)          # 幽州 绿
jizhou    = (g > r + 28) & (g > b + 12) & (g >= 170)                     # 冀州 青
sili      = (np.abs(r - g) < 35) & (g > b + 8) & (g >= 188)              # 司隶 米黄
liang     = (r < g + 10) & (r < b + 15) & (g >= 155) & (b >= 125) & (r < 175) & (g > r)  # 凉州/雍州 黄橙

red_mask = (bingzhou_raw & ~(youzhou|jizhou|sili|liang)).astype(np.uint8)*255
print(f'Red mask: {(red_mask>0).sum():,} px')

# 轻量清理红色掩膜（去掉文字/道路造成的小孔洞和突起）
kc9 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(9,9))
ko7 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7))
red_clean = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kc9, iterations=1)
red_clean = cv2.morphologyEx(red_clean, cv2.MORPH_OPEN, ko7, iterations=1)
print(f'Cleaned red: {(red_clean>0).sum():,} px')

imwrite_safe(os.path.join(OUTDIR,'00_red_mask.png'), red_clean)

# ================================================================
# Phase 2: 白线侧判定（位置参考）
# ================================================================
lo_w = (r>210)&(g>210)&(b>210)
hi_w = (r>185)&(g>185)&(b>185)&(np.abs(r-g)<22)&(np.abs(g-b)<22)&(np.abs(r-b)<22)
white_any = lo_w|hi_w
gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
gx=cv2.Sobel(gray,cv2.CV_64F,1,0,ksize=3); gy=cv2.Sobel(gray,cv2.CV_64F,0,1,ksize=3)
gmag=np.sqrt(gx**2+gy**2)
white_line = white_any&(gmag>12)

ry = np.pad(red_mask>0,1,mode='constant',constant_values=False)
n_ryn = np.zeros((H,W),dtype=np.int32)
for dy,dx in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
    n_ryn += ry[1+dy:H+dy+1,1+dx:W+dx+1].astype(np.int32)
border_px = white_line&(n_ryn>=1)&((8-n_ryn)>=1)
print(f'Border pixels (side-test): {border_px.sum():,}')

by,bx = np.where(border_px)
border_coords = np.column_stack([bx.astype(float),by.astype(float)])  # N×2 [x,y]
imwrite_safe(os.path.join(OUTDIR,'00_border_px.png'),(border_px*255).astype(np.uint8))

if len(border_coords) < 10:
    print('ERROR: too few border pixels'); sys.exit(1)

# ================================================================
# Phase 3: 红色掩膜外轮廓
# ================================================================
contours,_ = cv2.findContours(red_clean,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
outer = max(contours,key=cv2.contourArea)
print(f'Rough contour: {len(outer)} vertices')
rough_pts = outer.reshape(-1,2).astype(float)  # M×2 [x,y]

# ================================================================
# Phase 4: ★ 吸附到最近的白线边界像素 ★
# ================================================================
tree = cKDTree(border_coords)
MAX_SNAP_DIST = 25  # 最大吸附距离(px)，超出此距离保持原位

distances,indices = tree.query(rough_pts,k=1)
snapped = np.where(
    distances[:,None] <= MAX_SNAP_DIST,
    border_coords[indices],
    rough_pts
)
n_snapped = (distances <= MAX_SNAP_DIST).sum()
n_keep = (distances > MAX_SNAP_DIST).sum()
print(f'Snap: {n_snapped}→white_line, {n_keep} kept (max_dist={MAX_SNAP_DIST}px)')

# ================================================================
# Phase 5: 坐标平滑
# ================================================================
sigma = 4
pts_smooth = np.zeros_like(snapped)
pts_smooth[:,0] = gaussian_filter1d(snapped[:,0],sigma=sigma)
pts_smooth[:,1] = gaussian_filter1d(snapped[:,1],sigma=sigma)

# 闭合（首尾相接）
pts_final = np.round(pts_smooth).astype(int).tolist()

# ================================================================
# Phase 6: 填充多边形
# ============================================================
final_mask = np.zeros((H,W),dtype=np.uint8)
cv2.fillPoly(final_mask,[np.array(pts_final)],255)
area = (final_mask>0).sum()

# 微裁剪：去掉明显超出红色的孤立离群点（<2000px的独立连通分量）
n_lbl,lbl,stats,_ = cv2.connectedComponentsWithStats(final_mask)
outlier_area = 0
for i in range(1,n_lbl):
    ar = stats[i,cv2.CC_STAT_AREA]
    if ar < 2000:
        final_mask[lbl==i]=0
        outlier_area += ar
print(f'Final: {len(pts_final)} vertices, {area:,} px (clipped {outlier_area:,} outliers)')

# 重新提取最终轮廓（裁剪后可能有凹坑）
cf,_ = cv2.findContours(final_mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
if cf:
    of=max(cf,key=cv2.contourArea)
    ef=0.002*cv2.arcLength(of,True)
    fc=cv2.approxPolyDP(of,ef,True)
    pts_final=fc.reshape(-1,2).tolist()

# ================================================================
# 保存输出
# ================================================================
with open(os.path.join(OUTDIR,'boundary_points.json'),'w') as f:
    json.dump({'points':pts_final,'count':len(pts_final)},f,ensure_ascii=False,indent=2)

ov=img.copy(); mb=final_mask>0
ov[mb]=ov[mb].astype(float)*0.35+np.array([213,115,114],dtype=float)*0.65
ov=ov.astype(np.uint8)
cv2.polylines(ov,[np.array(pts_final)],True,(0,0,255),2)
imwrite_safe(os.path.join(OUTDIR,'verify_overlay.png'),ov)

bd=img.copy()
cv2.polylines(bd,[np.array(pts_final)],True,(0,0,255),2)
imwrite_safe(os.path.join(OUTDIR,'boundary_overlay.png'),bd)

imwrite_safe(os.path.join(OUTDIR,'mask_clean.png'),final_mask)

comp=np.hstack([img,cv2.bitwise_and(img,img,mask=final_mask),bd])
imwrite_safe(os.path.join(OUTDIR,'comparison_preview.png'),comp)

# Debug: rough vs snapped comparison
debug_cmp = img.copy()
cv2.polylines(debug_cmp,[rough_pts.astype(int)],False,(0,255,0),1)  # green = rough
cv2.polylines(debug_cmp,[np.round(snapped).astype(int)],False,(0,0,255),1)  # red = snapped
imwrite_safe(os.path.join(OUTDIR,'debug_rough_vs_snapped.png'), debug_cmp)

print(f'\nDone -> {OUTDIR}')
