#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v6b: 白线边界追踪 — 骨架化剪枝版。

v6的问题：膨胀后内部县界白线与外环合并，findContours产生"手指"突起。
修复：骨架化 → 剪除短分支（<60px）→ 只保留最长的闭合环。
"""
import os, json
import numpy as np
import cv2
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
OUTDIR = os.path.join(HERE, 'jizhou_step1_v6b')
os.makedirs(OUTDIR, exist_ok=True)

rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = rgb.shape[:2]
r = rgb[:,:,0].astype(int); g = rgb[:,:,1].astype(int); b = rgb[:,:,2].astype(int)
hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
ss = hsv[:,:,1].astype(int); vv = hsv[:,:,2].astype(int)
print(f'[0] {W}x{H}')

# ---- 1. 冀州颜色掩膜（同v6）----
jizho_core = ((g > r + 30)&(g > b + 8)&(g >= 165)&(g <= 252)
            &(b >= 150)&(b <= 246)&(r >= 110)&(r <= 236)).astype(np.uint8)
bingzhou=(r > g + 15)&(r > 130)&(g < 190)&(r > 140)
sili   =(abs(r - g) < 30)&(g > b + 10)&(g >= 200)
youzhou=(g > r + 25)&(g <= 210)&(r < 160)&(b >= 140)&((g - r) > 30)
qingzhou=(g > 185)&(g <= 235)&(b < 190)&(b > 70)&(g > b + 25)&(r > 170)&(abs(r-g)<50)
exclude = (bingzhou|sili|youzhou|qingzhou).astype(np.uint8)
jizho_core[exclude>0] = 0; jizhou = jizho_core.copy()
print(f'[1] 冀州: {(jizhou>0).sum():,} px')

# ---- 2. 白线边缘检测（同v6）----
pure_white = (r > 205)&(g > 205)&(b > 205)
light      = (ss < 45)&(vv > 205)&(r > 175)&(g > 175)&(b > 175)
white_region = (pure_white | light).astype(np.uint8)*255
k3=np.ones((3,3),np.uint8)
wc = cv2.filter2D(white_region.astype(np.float32)/255.0,-1,k3)
edge_of_white = (white_region>0)&(wc < 8)

# ---- 3. 边界判定 ----
cn = cv2.filter2D(jizhou.astype(np.float32),-1,k3)
border = (edge_of_white>0)&(cn>0)&(cn<8)
border = border.astype(np.uint8)*255
print(f'[3] 边界像素: {(border>0).sum():,}')

# ---- 4. 轻微膨胀桥接缺口（仅1次3x3）----
bd = cv2.dilate(border, k3, iterations=1)

# ---- 5. 骨架化（将粗线变成1px宽中心线）----
def skeletonize(binary_mask):
    """迭代形态学细化直到稳定（近似骨架）。"""
    skel = binary_mask.copy()
    elem = np.ones((3,3), np.uint8)
    prev_size = 0
    for i in range(200):
        eroded = cv2.erode(skel, elem)
        opened = cv2.dilate(eroded, elem)
        opened = cv2.subtract(skel, opened)
        skel = cv2.bitwise_or(skel & 255, opened)
        sz = (skel>0).sum()
        if sz == prev_size:
            break
        prev_size = sz
    return skel

skel = skeletonize(bd)
print(f'[5a] 骨架化: {(skel>0).sum():,} px')

Image.fromarray(skel*255).save(os.path.join(OUTDIR,'debug_skeleton.png'))

# ---- 6. 剪枝：移除长度 < min_len 的短分支 ----
def prune_short_branches(skeleton, min_len=40):
    """迭代移除端点分支直到所有剩余分支 ≥ min_len."""
    pruned = skeleton.copy().astype(bool)
    # 8连通邻域
    for _ in range(min_len * 2):  # 最多次数限制
        changed = False
        # 计算每个骨架像素的8邻居骨架像素数
        conv = ndimage.convolve(pruned.astype(np.uint8),
                                 np.array([[1,1,1],[1,0,1],[1,1,1]], dtype=np.uint8),
                                 mode='constant', cval=0)
        # 端点：恰好1个骨架邻居
        endpoints = pruned & (conv == 1)
        n_ep = endpoints.sum()
        if n_ep == 0:
            break
        # 移除端点
        pruned[endpoints] = False
        changed = True
        if _ > min_len:
            # 超过min_len轮后停止（已修剪够长的分支）
            pass
    return pruned.astype(np.uint8)*255

skel_clean = prune_short_branches(skel, min_len=45)
print(f'[5b] 剪枝后: {(skel_clean>0).sum():,} px')

Image.fromarray(skel_clean).save(os.path.join(OUTDIR,'debug_skel_pruned.png'))

# ---- 7. 取最长闭合环 ----
nb, lab, st, _ = cv2.connectedComponentsWithStats(skel_clean, connectivity=8)

# 对每个连通分量，检查是否形成环（面积/周长比）
best_contour = None
best_perimeter = 0

for i in range(1, nb):
    comp = (lab == i).astype(np.uint8) * 255
    contours, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        perim = cv2.arcLength(c, True)
        area = cv2.contourArea(c)
        # 环形特征：周长较大且面积较小（细线）
        if perim > best_perimeter and area > 10:
            best_perimeter = perim
            best_contour = c

if best_contour is None:
    # fallback: 取最大分量填孔取轮廓
    main_i = 1+int(np.argmax(st[1:,cv2.CC_STAT_AREA]))
    comp = (lab==main_i).astype(np.uint8)*255
    contours,_ = cv2.findContours(comp,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    best_contour = max(contours,key=cv2.arcLength)

arc = cv2.arcLength(best_contour, True)
for eps in [0.0010,0.0015,0.0020,0.0030,0.0040,0.0050]:
    poly = cv2.approxPolyDP(best_contour, eps*arc, True).reshape(-1,2)
    if 80 <= len(poly) <= 300:
        break
print(f'[7] 边界顶点: {len(poly)}')

# ---- 8. 输出 ----
poly = poly.astype(np.int32)
mask_out = np.zeros((H,W), np.uint8)
cv2.fillPoly(mask_out,[poly],255)
mask_out[exclude>0]=0
mask_out=cv2.morphologyEx(mask_out,cv2.MORPH_CLOSE,k3,iterations=1)
print(f'[8] 掩膜: {(mask_out>0).sum():,} px')

mean_c=[173,228,207]
vf=rgb.astype(float)*0.55; alf=np.zeros_like(rgb,float); alf[mask_out>0]=[0,255,255]
vf+=alf*0.45; vf=np.clip(vf,0,255).astype(np.uint8)
cv2.polylines(vf,[poly.reshape(-1,1,2)],True,(255,0,0),2)
Image.fromarray(vf).save(os.path.join(OUTDIR,'verify_overlay.png'))
ov=rgb.copy(); cv2.polylines(ov,[poly.reshape(-1,1,2)],True,(255,0,0),3)
Image.fromarray(ov).save(os.path.join(OUTDIR,'boundary_overlay.png'))

pts_o=[{'seq':i,'px':int(x),'py':int(y)} for i,(x,y) in enumerate(poly)]
with open(os.path.join(OUTDIR,'boundary_points.json'),'w',encoding='utf-8') as f:
    json.dump({'source_image':'汉末十三州地图范例/冀州.png','image_size':[W,H],
               'version':'v6b-whiteline-skeleton-prune',
               'method':'white_edge & cyan_neigh_test -> skeletonize -> prune(<45px) -> longest_cycle',
               'points':pts_o}, f, ensure_ascii=False, indent=2)
print(f'\n[done] => {OUTDIR}/  {len(pts_o)}点, {(mask_out>0).sum():,}px')
