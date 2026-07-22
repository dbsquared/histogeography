#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v6: 白线边界追踪算法（用户提出的算法）。

算法（用户原话）：
  1. 确定颜色（冀州青色）
  2. 边界是白色的
  3. 先到一个白色的点
  4. 顺时针找下一个白色的点，如果该点一边是我们要的颜色、另一边不是，
     那这个点就是正确的，继续往相同方向推进

实现：
  - 在原始图上判定冀州青色掩膜（复用v5阈值，无需inpaint）
  - 检测白色边界线（细线，排除大片白色背景内部）
  - 边界判定：白线像素若"8邻域中既有冀州又有非冀州"→ 它在冀州边界上
  - 取最大连通环 → 外轮廓 → 简化 → 输出
"""
import os, json
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
OUTDIR = os.path.join(HERE, 'jizhou_step1_v6')
os.makedirs(OUTDIR, exist_ok=True)

rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = rgb.shape[:2]
r = rgb[:,:,0].astype(int); g = rgb[:,:,1].astype(int); b = rgb[:,:,2].astype(int)
hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
hh = hsv[:,:,0].astype(int); ss = hsv[:,:,1].astype(int); vv = hsv[:,:,2].astype(int)
print(f'[0] 图像 {W}x{H}')

# ============================================================
# 1. 确定冀州颜色（原始图上直接判定，无需inpaint）
# ============================================================
jizho_core = (
    (g > r + 30) & (g > b + 8) &
    (g >= 165) & (g <= 252) &
    (b >= 150) & (b <= 246) &
    (r >= 110) & (r <= 236)
).astype(np.uint8)

# 邻州排除（防止邻州被误判为冀州 → 否则白线两侧都"冀州"会漏掉边界）
bingzhou  = (r > g + 15) & (r > 130) & (g < 190) & (r > 140)
sili     = (abs(r - g) < 30) & (g > b + 10) & (g >= 200)
youzhou  = (g > r + 25) & (g <= 210) & (r < 160) & (b >= 140) & ((g - r) > 30)
qingzhou = (g > 185) & (g <= 235) & (b < 190) & (b > 70) & (g > b + 25) & (r > 170) & (abs(r - g) < 50)
exclude = (bingzhou | sili | youzhou | qingzhou).astype(np.uint8)
jizho_core[exclude > 0] = 0
jizhou = jizho_core.copy()
print(f'[1] 冀州青色像素: {(jizhou>0).sum():,}')

# ============================================================
# 2. 白色边界线（细线，排除大片白背景内部）
# ============================================================
# 纯白
pure_white = (r > 205) & (g > 205) & (b > 205)
# 浅灰/米白：低饱和、高亮度
light = (ss < 45) & (vv > 205) & (r > 175) & (g > 175) & (b > 175)
white_region = (pure_white | light).astype(np.uint8) * 255
# 只保留白区的"边缘"（有非白邻居），排除白色背景内部的大块填充
k3 = np.ones((3,3), np.uint8)
white_count = cv2.filter2D(white_region.astype(np.float32)/255.0, -1, k3)
# white_count[P] = 周围8邻白像素数 + 自身(若白)。对白像素=邻居白数。
edge_of_white = (white_region > 0) & (white_count < 8)
print(f'[2] 白区像素: {(white_region>0).sum():,}; 白线边缘: {(edge_of_white>0).sum():,}')

# ============================================================
# 3. 边界判定：白线像素若8邻域中既有冀州又有非冀州 → 在冀州边界上
# ============================================================
cyan_neigh = cv2.filter2D(jizhou.astype(np.float32), -1, k3)  # 含自身；白像素自身=0
# cyan_neigh[P] = 8邻中冀州像素个数（白像素自身非冀州）
border = (edge_of_white > 0) & (cyan_neigh > 0) & (cyan_neigh < 8)
border = border.astype(np.uint8) * 255
print(f'[3] 冀州-白线边界像素: {(border>0).sum():,}')

# 调试图
wr = np.zeros((H,W,3), np.uint8); wr[white_region>0]=(180,180,180)
Image.fromarray(wr).save(os.path.join(OUTDIR,'debug_white_region.png'))
bd = np.zeros((H,W,3), np.uint8); bd[border>0]=(0,255,255)
Image.fromarray(bd).save(os.path.join(OUTDIR,'debug_border_pixels.png'))

# ============================================================
# 4. 取最大连通环 → 外轮廓 → 简化
# ============================================================
# 桥接白线缺口
border_d = cv2.dilate(border, k3, iterations=2)
nb, lab, st, _ = cv2.connectedComponentsWithStats(border_d, connectivity=8)
main_i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
border_conn = (lab == main_i).astype(np.uint8) * 255
print(f'[4] 最大连通环面积: {st[main_i, cv2.CC_STAT_AREA]:,}')

contours, _ = cv2.findContours(border_conn, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)
arc = cv2.arcLength(main, True)
for eps in [0.0010, 0.0015, 0.0020, 0.0025, 0.0030, 0.0040]:
    poly = cv2.approxPolyDP(main, eps * arc, True).reshape(-1, 2)
    if 100 <= len(poly) <= 320:
        break
print(f'[4] 边界顶点: {len(poly)} (eps={eps:.4f})')

# ============================================================
# 5. 输出
# ============================================================
poly = poly.astype(np.int32)
mask_out = np.zeros((H,W), np.uint8)
cv2.fillPoly(mask_out, [poly], 255)
# 排除邻州颜色溢出
mask_out[exclude > 0] = 0
mask_out = cv2.morphologyEx(mask_out, cv2.MORPH_CLOSE, k3, iterations=1)
print(f'[5] 输出掩膜: {(mask_out>0).sum():,} px')

mean_c = [173,228,207]
# verify_overlay
vf = rgb.astype(float)*0.55
alf = np.zeros_like(rgb, float); alf[mask_out>0]=[0,255,255]
vf += alf*0.45; vf = np.clip(vf,0,255).astype(np.uint8)
cv2.polylines(vf, [poly.reshape(-1,1,2)], True, (255,0,0), 2)
Image.fromarray(vf).save(os.path.join(OUTDIR,'verify_overlay.png'))
# boundary_overlay
ov = rgb.copy(); cv2.polylines(ov,[poly.reshape(-1,1,2)],True,(255,0,0),3)
Image.fromarray(ov).save(os.path.join(OUTDIR,'boundary_overlay.png'))
# 白线+边界叠加
wb = rgb.copy()
cv2.polylines(wb,[poly.reshape(-1,1,2)],True,(0,0,255),2)
Image.fromarray(wb).save(os.path.join(OUTDIR,'white_and_boundary.png'))

pts_out = [{'seq':i,'px':int(x),'py':int(y)} for i,(x,y) in enumerate(poly)]
with open(os.path.join(OUTDIR,'boundary_points.json'),'w',encoding='utf-8') as f:
    json.dump({'source_image':'汉末十三州地图范例/冀州.png','image_size':[W,H],
               'version':'v6-whiteline-trace',
               'method':'white_line_boundary: edge_of_white & (0<cyan_neigh8<8); largest_loop; approxPolyDP',
               'points':pts_out}, f, ensure_ascii=False, indent=2)

print(f'\n[done] => {OUTDIR}/  顶点{len(pts_out)}, 面积{(mask_out>0).sum():,}')
