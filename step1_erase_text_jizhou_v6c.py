#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v6c: 白线边界追踪 — 填孔法。

核心改进：
  白线边界像素(22k) → 轻微膨胀桥接≤2px缺口 → fillHoles填满环内区域
  → 取最大连通块(=冀州本体) → RETR_EXTERNAL外轮廓 = 干净多边形

这比"骨架化剪枝"简单100倍，且自然排除内部县界（县界形成的微小闭合环面积远小于主环）。
"""
import os, json
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
OUTDIR = os.path.join(HERE, 'jizhou_step1_v6c')
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
border=border.astype(np.uint8)*255
print(f'[3] 边界:{(border>0).sum():,}')

# ---- 3. 轻微膨胀桥接 + 填孔 + 取最大块 ----
bd=cv2.dilate(border,k3,iterations=1)     # 桥接≤2px缺口
# 用 floodFill 从四角标记外部，剩余=内部（环内区域）
outside=np.zeros((H+2,W+2),np.uint8)
seed_pts=[(0,0),(W-1,0),(0,H-1),(W-1,H-1)]
for sx,sy in seed_pts:
    if bd[sy,sx]==0:
        cv2.floodFill(bd,outside,(sx,sy),128,loDiff=0,upDiff=0,flags=cv2.FLOODFILL_FIXED_RANGE|(8<<8))
# bd中值仍为255的=未被flood到的=环内区域
interior=(bd==255).astype(np.uint8)*255
print(f'[4] 内部区域: {(interior>0).sum():,}')

# 取最大连通块（应该是冀州本体）
nb,lab,st,_=cv2.connectedComponentsWithStats(interior,connectivity=8)
mi=1+int(np.argmax(st[1:,cv2.CC_STAT_AREA]))
main_body=(lab==mi).astype(np.uint8)*255
print(f'[4] 最大块: {st[mi,cv2.CC_STAT_AREA]:,} ({st[mi,cv2.CC_STAT_WIDTH]}x{st[mi,cv2.CC_STAT_HEIGHT]})')

Image.fromarray(interior).save(os.path.join(OUTDIR,'debug_interior.png'))
Image.fromarray(main_body).save(os.path.join(OUTDIR,'debug_main_body.png'))

# ---- 4. 开运算去小突起（可选）----
main_body=cv2.morphologyEx(main_body,cv2.MORPH_OPEN,np.ones((7,7),np.uint8),iterations=1)
# 再闭一次修断口
main_body=cv2.morphologyEx(main_body,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8),iterations=1)

# ---- 5. 外轮廓 ----
cts,_=cv2.findContours(main_body,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
main=max(cts,key=cv2.contourArea)
arc=cv2.arcLength(main,True)
for eps in [0.0010,0.0015,0.0020,0.0030,0.0040]:
    poly=cv2.approxPolyDP(main,eps*arc,True).reshape(-1,2)
    if 80<=len(poly)<=300:
        break
print(f'[5] 顶点:{len(poly)}')

# ---- 6. 输出 ----
poly=poly.astype(np.int32)
mask_out=np.zeros((H,W),np.uint8)
cv2.fillPoly(mask_out,[poly],255)
mask_out[ex>0]=0
mask_out=cv2.morphologyEx(mask_out,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8),iterations=1)
print(f'[6] 掩膜:{(mask_out>0).sum():,} px')

mc=[173,228,207]
vf=rgb.astype(float)*0.55; al=np.zeros_like(rgb,float); al[mask_out>0]=[0,255,255]
vf+=al*0.45; vf=np.clip(vf,0,255).astype(np.uint8)
cv2.polylines(vf,[poly.reshape(-1,1,2)],True,(255,0,0),2)
Image.fromarray(vf).save(os.path.join(OUTDIR,'verify_overlay.png'))
ov=rgb.copy(); cv2.polylines(ov,[poly.reshape(-1,1,2)],True,(255,0,0),3)
Image.fromarray(ov).save(os.path.join(OUTDIR,'boundary_overlay.png'))

pts_o=[{'seq':i,'px':int(x),'py':int(y)} for i,(x,y) in enumerate(poly)]
with open(os.path.join(OUTDIR,'boundary_points.json'),'w',encoding='utf-8') as f:
    json.dump({'source_image':'汉末十三州地图范例/冀州.png','image_size':[W,H],
               'version':'v6c-whiteline-floodfill',
               'method':'white_edge&cyan_neigh -> dilate(1) -> floodFill_from_corners -> max_component -> open7_close5',
               'points':pts_o}, f, ensure_ascii=False, indent=2)
print(f'\n[done]=>{OUTDIR}/  {len(pts_o)}点,{(mask_out>0).sum():,}px')
