#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v6d: 白线边界追踪 — 极角排序法。

核心思路：
  白线边界像素(22k) 不需要连通！
  计算所有边界像素相对于冀州质心的极角，按角度排序 → 直接形成闭合多边形。
  用分桶+中值平滑消除噪声（每个角度桶取中值位置）。
"""
import os, json, math
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
OUTDIR = os.path.join(HERE, 'jizhou_step1_v6d')
os.makedirs(OUTDIR, exist_ok=True)

rgb = np.array(Image.open(SRC).convert('RGB'))
H,W = rgb.shape[:2]
r=rgb[:,:,0].astype(int); g=rgb[:,:,1].astype(int); b=rgb[:,:,2].astype(int)
hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
ss=hsv[:,:,1].astype(int); vv=hsv[:,:,2].astype(int)

# ---- 1. 冀州掩膜 ----
jz=((g>r+30)&(g>b+8)&(g>=165)&(g<=252)&(b>=150)&(b<=246)&(r>=110)&(r<=236)).astype(np.uint8)
bz=(r>g+15)&(r>130)&(g<190)&(r>140)
sl=(abs(r-g)<30)&(g>b+10)&(g>=200)
yz=(g>r+25)&(g<=210)&(r<160)&(b>=140)&((g-r)>30)
qz=(g>185)&(g<=235)&(b<190)&(b>70)&(g>b+25)&(r>170)&(abs(r-g)<50)
ex=(bz|sl|yz|qz).astype(np.uint8); jz[ex>0]=0; jizhou=jz.copy()
print(f'[1] 冀州:{(jizhou>0).sum():,}')

# ---- 2. 白线边缘 + 边界判定 ----
pw=(r>205)&(g>205)&(b>205)
lt=(ss<45)&(vv>205)&(r>175)&(g>175)&(b>175)
wr=(pw|lt).astype(np.uint8)*255
k3=np.ones((3,3),np.uint8)
wc=cv2.filter2D(wr.astype(np.float32)/255,-1,k3)
eow=(wr>0)&(wc<8)
cn=cv2.filter2D(jizhou.astype(np.float32),-1,k3)
border=(eow>0)&(cn>0)&(cn<8)
print(f'[3] 边界:{border.sum():,}')

# ---- 3. 极角排序 ----
ys,xs=np.where(border)
pts=np.column_stack([xs.astype(float),ys.astype(float)])

# 质心：用冀州掩膜的质心（比边界点质心更稳定）
jy,jx=np.where(jizhou)
cx=jx.mean(); cy=jy.mean()
print(f'[3] 冀州质心:({cx:.0f},{cy:.0f})')

# 相对质心的极坐标
dx=pts[:,0]-cx; dy=pts[:,1]-cy
angles=np.arctan2(dy,dx)  # [-π,π]
radii=np.sqrt(dx*dx+dy*dy)

# 分桶：360个桶（每度1个），每个桶内取中值半径
N_BINS=720
bin_idx=((angles+np.pi)/ (2*np.pi) * N_BINS).astype(int) % N_BINS
bin_radii=[[] for _ in range(N_BINS)]
for i in range(len(pts)):
    bi=bin_idx[i]
    bin_radii[bi].append(radii[i])

# 每个桶取中值（对空桶插值）
poly_angles=[]
poly_rs=[]
for i in range(N_BINS):
    if len(bin_radii[i]) >= 3:
        poly_angles.append(i/N_BINS * 2*np.pi - np.pi)
        poly_rs.append(np.median(bin_radii[i]))
    elif len(bin_radii[i]) > 0:
        poly_angles.append(i/N_BINS * 2*np.pi - np.pi)
        poly_rs.append(np.median(bin_radii[i]))
    else:
        # 空桶：线性插值
        poly_angles.append(i/N_BINS * 2*np.pi - np.pi)
        poly_rs.append(np.nan)

# 插值填充空桶
pa=np.array(poly_angles); pr=np.array(poly_rs)
nan_mask=np.isnan(pr)
if nan_mask.any():
    valid_idx=~nan_mask
    pr[nan_mask]=np.interp(pa[nan_mask], pa[valid_idx], pr[valid_idx])

# 转回笛卡尔坐标
poly_x=cx+pr*np.cos(pa)
poly_y=cy+pr*np.sin(pa)
poly=np.column_stack([poly_x,poly_y]).round().astype(np.int32)

# ---- 4. 简化 ----
# 先转成OpenCV contour格式做approxPolyDP
contour=poly.reshape(-1,1,2).astype(np.int32)
arc=cv2.arcLength(contour,True)
for eps in [0.003,0.005,0.008,0.010,0.015]:
    simp=cv2.approxPolyDP(contour,eps*arc,True)
    if 60 <= len(simp) <= 250:
        poly=simp.reshape(-1,2).astype(np.int32)
        break
else:
    poly=simp.reshape(-1,2).astype(np.int32)
print(f'[4] 简化后:{len(poly)} 点')

# ---- 5. 输出 ----
mask_out=np.zeros((H,W),np.uint8)
cv2.fillPoly(mask_out,[poly],255)
mask_out[ex>0]=0
mask_out=cv2.morphologyEx(mask_out,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8),iterations=1)
print(f'[5] 掩膜:{(mask_out>0).sum():,} px')

mc=[173,228,207]
vf=rgb.astype(float)*0.55; al=np.zeros_like(rgb,float); al[mask_out>0]=[0,255,255]
vf+=al*0.45; vf=np.clip(vf,0,255).astype(np.uint8)
cv2.polylines(vf,[poly.reshape(-1,1,2)],True,(255,0,0),2)
Image.fromarray(vf).save(os.path.join(OUTDIR,'verify_overlay.png'))

ov=rgb.copy(); cv2.polylines(ov,[poly.reshape(-1,1,2)],True,(255,0,0),3)
Image.fromarray(ov).save(os.path.join(OUTDIR,'boundary_overlay.png'))

# 边界点叠在原图上（显示原始白线边界点 + 最终多边形）
bp=np.zeros((H,W,3),np.uint8); bp[border]=(0,200,255)   # 青色=原始边界点
cv2.polylines(bp,[poly.reshape(-1,1,2)],True,(255,0,0),2)  # 红色=最终多边形
Image.fromarray(bp).save(os.path.join(OUTDIR,'points_vs_polygon.png'))

pts_o=[{'seq':i,'px':int(x),'py':int(y)} for i,(x,y) in enumerate(poly)]
with open(os.path.join(OUTDIR,'boundary_points.json'),'w',encoding='utf-8') as f:
    json.dump({'source_image':'汉末十三州地图范例/冀州.png','image_size':[W,H],
               'version':'v6d-whiteline-polar',
               'method':'white_edge&cyan_neigh -> polar_sort(720bins,median_r) -> approxPolyDP',
               'points':pts_o}, f, ensure_ascii=False, indent=2)
print(f'\n[done]=>{OUTDIR}/  {len(pts_o)}点,{(mask_out>0).sum():,}px')
