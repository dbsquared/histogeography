#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v6e: 白线边界追踪 — 最终版。

核心策略：v6(白线形状干净但偏紧) 与 v5(面积正确但有噪声) 取长补短。
  1. 用白线判定获取边界像素集（v6方法，无路网/文字干扰）
  2. 膨胀桥接缺口，取最大连通环的外轮廓（v6原始轮廓）
  3. 将此轮廓外扩~8px（补偿白线在色块中心而非边缘的偏差）
  4. 与v5色块掩膜取交集 → 形状干净 + 面积正确
"""
import os, json
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
OUTDIR = os.path.join(HERE, 'jizhou_step1_v6e')
os.makedirs(OUTDIR, exist_ok=True)

rgb = np.array(Image.open(SRC).convert('RGB'))
H,W = rgb.shape[:2]
r=rgb[:,:,0].astype(int); g=rgb[:,:,1].astype(int); b=rgb[:,:,2].astype(int)
hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV); ss=hsv[:,:,1].astype(int); vv=hsv[:,:,2].astype(int)

# ---- 1. 冀州掩膜（同前）----
jz=((g>r+30)&(g>b+8)&(g>=165)&(g<=252)&(b>=150)&(b<=246)&(r>=110)&(r<=236)).astype(np.uint8)
ex=( ((r>g+15)&(r>130)&(g<190)) | ((abs(r-g)<30)&(g>b+10)&(g>=200)) |
     ((g>r+25)&(g<=210)&(r<160)&(b>=140)&((g-r)>30)) |
     ((g>185)&(g<=235)&(b<190)&(b>70)&(g>b+25)&(r>170)&(abs(r-g)<50)) ).astype(np.uint8)
jz[ex>0]=0; jizhou=jz.copy()

# 读入v5掩膜作为"真值面积参考"
V5_MASK_PATH = os.path.join(HERE,'jizhou_step1_v5','mask_clean.png')
if os.path.exists(V5_MASK_PATH):
    v5_raw=np.array(Image.open(V5_MASK_PATH).convert('L'))
    v5_mask=(v5_raw>128).astype(np.uint8)*255
    print(f'[1] v5掩膜:{(v5_mask>0).sum():,}')
else:
    v5_mask=None
print(f'[1] 冀州:{(jizhou>0).sum():,}')

# ---- 2. 白线边界像素（同v6）----
pw=(r>205)&(g>205)&(b>205); lt=(ss<45)&(vv>205)&(r>175)&(g>175)&(b>175)
wr=(pw|lt).astype(np.uint8)*255
k3=np.ones((3,3),np.uint8)
wc=cv2.filter2D(wr.astype(float)/255,-1,k3)
eow=(wr>0)&(wc<8)
cn=cv2.filter2D(jizhou.astype(float),-1,k3)
border=(eow>0)&(cn>0)&(cn<8).astype(np.uint8)*255
print(f'[2] 边界:{border.sum():,}')

# ---- 3. 膨胀 + 最大连通环外轮廓（v6原始方法）----
bd=cv2.dilate(border,np.ones((5,5),np.uint8),iterations=1)  # 5x5膨胀桥接稍大缺口
nb,lab,st,_=cv2.connectedComponentsWithStats(bd,connectivity=8)
mi=1+int(np.argmax(st[1:,cv2.CC_STAT_AREA]))
bd_main=(lab==mi).astype(np.uint8)*255
cts,_=cv2.findContours(bd_main,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
v6_contour=max(cts,key=cv2.contourArea)

arc=cv2.arcLength(v6_contour,True)
for eps in [0.001,0.0015,0.002,0.003]:
    v6_poly=cv2.approxPolyDP(v6_contour,eps*arc,True).reshape(-1,2)
    if 80<=len(v6_poly)<=300: break
v6_poly=v6_poly.astype(np.int32)
print(f'[3] v6轮廓:{len(v6_poly)}点')

# ---- 4. 外扩v6轮廓 + 可选与v5交集 ----
DILATE_PX=9  # 外扩像素数（补偿白线中心位置）
v6_dilated_mask=np.zeros((H,W),np.uint8)
cv2.fillPoly(v6_dilated_mask,[v6_poly],255)
v6_dilated_mask=cv2.dilate(v6_dilated_mask,np.ones((DILATE_PX*2+1,DILATE_PX*2+1),np.uint8),iterations=1)

final_mask=v6_dilated_mask
if v5_mask is not None:
    # 交集：保留两者重叠部分（v6形状约束 + v5面积基准）
    final_mask=cv2.bitwise_and(v6_dilated_mask,v5_mask)
    print(f'[4a] 交集:{(final_mask>0).sum():,} (v6外扩{(v6_dilated_mask>0).sum():,}, v5={(v5_mask>0).sum():,})')
else:
    print(f'[4] v6外扩:{(final_mask>0).sum():,}')

# 排除邻州
final_mask[ex>0]=0
final_mask=cv2.morphologyEx(final_mask,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8),iterations=1)
# 开运算切掉细手指（宽度<12px的突起）
final_mask=cv2.morphologyEx(final_mask,cv2.MORPH_OPEN,np.ones((11,11),np.uint8),iterations=1)
# 再闭一次补回被开运算过度切的缺口
final_mask=cv2.morphologyEx(final_mask,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8),iterations=1)

# ---- 5. 最终外轮廓 ----
cts2,_=cv2.findContours(final_mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
main2=max(cts2,key=cv2.contourArea)
arc2=cv2.arcLength(main2,True)
for eps in [0.0008,0.001,0.0015,0.002,0.003]:
    poly=cv2.approxPolyDP(main2,eps*arc2,True).reshape(-1,2)
    if 100<=len(poly)<=280: break
poly=poly.astype(np.int32)
print(f'[5] 最终:{len(poly)}点,{(final_mask>0).sum():,}px')

# ---- 6. 输出 ----
mc=[173,228,207]
vf=rgb.astype(float)*0.55; al=np.zeros_like(rgb,float); al[final_mask>0]=[0,255,255]
vf+=al*0.45; vf=np.clip(vf,0,255).astype(np.uint8)
cv2.polylines(vf,[poly.reshape(-1,1,2)],True,(255,0,0),2)
Image.fromarray(vf).save(os.path.join(OUTDIR,'verify_overlay.png'))

ov=rgb.copy(); cv2.polylines(ov,[poly.reshape(-1,1,2)],True,(255,0,0),3)
Image.fromarray(ov).save(os.path.join(OUTDIR,'boundary_overlay.png'))

# v6 vs v6e 叠加对比
cmp=rgb.copy()
v6_ov=rgb.copy(); cv2.polylines(v6_ov,[v6_poly.reshape(-1,1,2)],True,(255,150,150),2)
cv2.polylines(cmp,[v6_poly.reshape(-1,1,2)],True,(255,150,150),2)
cv2.polylines(cmp,[poly.reshape(-1,1,2)],True,(0,255,0),2)
Image.fromarray(cmp).save(os.path.join(OUTDIR,'v6_vs_v6e.png'))

pts_o=[{'seq':i,'px':int(x),'py':int(y)} for i,(x,y) in enumerate(poly)]
with open(os.path.join(OUTDIR,'boundary_points.json'),'w',encoding='utf-8') as f:
    json.dump({'source_image':'汉末十三州地图范例/冀州.png','image_size':[W,H],
               'version':'v6e-white-shape-xor-v5-area',
               'method':'white_border->contour->dilate(9px)->intersect_v5_mask',
               'points':pts_o}, f, ensure_ascii=False, indent=2)
print(f'\n[done]=>{OUTDIR}/  {len(pts_o)}点,{(final_mask>0).sum():,}px')
