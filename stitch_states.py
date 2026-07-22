#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三州边界无缝缝合：以冀州多边形为基准，
把并州/幽州边界中『靠近冀州』的顶点直接吸附到冀州对应边界点上，
共用同一段边界 → 共用边严格重合，彻底消除空隙。

非边界顶点保持原位，边界顶点用样条平滑过渡避免锯齿。
"""
import os, json, math
import numpy as np
from scipy.spatial import cKDTree
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, 'china_full_v3.png')
OUTDIR = os.path.join(HERE, 'you_bing_ji_overlay')
os.makedirs(OUTDIR, exist_ok=True)

BW,BH=15600,9600
LON0,LON1=75.0,140.0
LAT0,LAT1=15.0,55.0
def geo_to_big(lon,lat): return (lon-LON0)/(LON1-LON0)*BW,(LAT1-lat)/(LAT1-LAT0)*BH

def basis1(x,y,deg):
    t=[1.0]
    for p in range(1,deg+1):
        for j in range(p+1): t.append(float(x)**(p-j)*float(y)**j)
    return t
def fit_poly(pts,vals,deg):
    A=np.array([basis1(x,y,deg) for x,y in pts],dtype=float)
    c,*_=np.linalg.lstsq(A,np.array(vals,dtype=float),rcond=None); return c
def predict(c,deg,x,y): return float(np.dot(c[:len(basis1(x,y,deg))],basis1(x,y,deg)))
def build_mapper(anchors):
    axy=[(a['px'],a['py']) for a in anchors]; deg=2 if len(anchors)>=8 else 1
    cl=fit_poly(axy,[a['lon'] for a in anchors],deg); ca=fit_poly(axy,[a['lat'] for a in anchors],deg)
    return lambda x,y:(predict(cl,deg,x,y),predict(ca,deg,x,y))
def load_pts(path):
    d=json.load(open(os.path.join(HERE,path),encoding='utf-8')); raw=d['points'] if 'points' in d else d
    return [(float(p['px']),float(p['py'])) if isinstance(p,dict) else (float(p[0]),float(p[1])) for p in raw]
def poly_lonlat(pts_path,anchors,shift):
    m=build_mapper(anchors); return [(lambda lo,la:(lo+shift[0],la+shift[1]))(*m(x,y)) for x,y in load_pts(pts_path)]

ji_a=json.load(open(os.path.join(HERE,'jizhou_anchor_table.json'),encoding='utf-8'))
yo_a=json.load(open(os.path.join(HERE,'youzhou_layer_v2','youzhou_anchor_table.json'),encoding='utf-8'))
bz_a=json.load(open(os.path.join(HERE,'bingzhou_anchor_table.json'),encoding='utf-8'))
JI=poly_lonlat('jizhou_step1_v7c/boundary_points.json',ji_a,(0,0))
YO=poly_lonlat('youzhou_step1/boundary_points.json',yo_a,(0.75,0.30))
BZ=poly_lonlat('bingzhou_step1_v7c/boundary_points.json',bz_a,(0,0))

LAT_MID=38.5; KX=111.0*math.cos(math.radians(LAT_MID)); KY=111.0
def km(poly): return np.array([(x*KX,y*KY) for x,y in poly])

def stitch(moving, base, snap_km=130.0, blend_pts=4):
    """把 moving 多边形中距 base 边界 <snap_km 的顶点吸附到 base 最近边界点。
       吸附段两端用 blend_pts 个顶点做线性过渡，避免突变。
       返回新多边形(经纬度) + 吸附顶点数。"""
    M=km(moving); B=km(base)
    tree=cKDTree(B)
    dist,idx=tree.query(M,k=1)
    snap = dist < snap_km
    n_snap=int(snap.sum())
    M2=M.copy()
    # 直接吸附
    M2[snap]=B[idx[snap]]
    # 找连续吸附段，对每个段的两端做过渡
    n=len(M)
    # 转回经纬度前先做平滑过渡（在 km 空间）
    out=M2.copy()
    visited=np.zeros(n,bool)
    for start in range(n):
        if snap[start] and not visited[start]:
            # 找一个连续段
            seg=[start]; visited[start]=True
            j=(start+1)%n
            while snap[j] and not visited[j] and j!=start:
                seg.append(j); visited[j]=True; j=(j+1)%n
            if len(seg)>=n-2:  # 几乎全部吸附，不做过渡
                continue
            # 段尾过渡
            tail_start=(seg[-1]+1)%n
            for k in range(1,blend_pts+1):
                vi=(tail_start+k-1)%n
                if snap[vi]: break
                t=k/(blend_pts+1)  # 0→1, 越远离吸附段越接近原值
                out[vi]=M2[seg[-1]]*(1-t)+M[vi]*t
            # 段首过渡
            head_end=(seg[0]-1)%n
            for k in range(1,blend_pts+1):
                vi=(head_end-k+1)%n
                if snap[vi]: break
                t=k/(blend_pts+1)
                out[vi]=M2[seg[0]]*(1-t)+M[vi]*t
    res=[(x/KX,y/KY) for x,y in out]
    return res,n_snap

print('[缝合] 并州东界 → 冀州西界')
BZ2,n1=stitch(BZ,JI,snap_km=130.0)
print(f'  并州吸附顶点: {n1}/{len(BZ)}')
print('[缝合] 幽州南界 → 冀州北界')
YO2,n2=stitch(YO,JI,snap_km=130.0)
print(f'  幽州吸附顶点: {n2}/{len(YO)}')

def close(p): return p if p[0]==p[-1] else p+[p[0]]
JIc,BZc,YOc=close(JI),close(BZ2),close(YO2)
json.dump({'冀州':JIc,'并州':BZc,'幽州':YOc},
          open(os.path.join(OUTDIR,'stitched_polys.json'),'w',encoding='utf-8'),ensure_ascii=False)

# 缝合质量报告
def gap(A,B,label):
    a=km(A); b=km(B); t=cKDTree(b); d,_=t.query(a)
    near=d[d<150]
    print(f'  {label}: 近界{len(near)}/{len(a)} ({100*len(near)/len(a):.0f}%) 中位{np.median(near):.1f}km P90{np.percentile(near,90):.1f}km')
print('[缝合后间隙]')
gap(BZc,JIc,'并-冀'); gap(YOc,JIc,'幽-冀')

# ---------- 渲染 ----------
STATES=[('幽州',YOc,(96,168,120)),('冀州',JIc,(70,200,180)),('并州',BZc,(213,90,90))]
FONT=r'C:/Windows/Fonts/simhei.ttf'
def render(crop_box,out_path,target_w):
    if crop_box is None:
        pw=2600; ph=int(BH*pw/BW); base=Image.open(BASE).convert('RGB').resize((pw,ph))
        def tp(lon,lat):
            bx,by=geo_to_big(lon,lat); return bx/(BW/pw),by/(BH/ph)
    else:
        z0,z1,z2,z3=crop_box
        bx0,by0=geo_to_big(z0,z3); bx1,by1=geo_to_big(z1,z2)
        bx0,by0,bx1,by1=map(int,(bx0,by0,bx1,by1)); zw,zh=bx1-bx0,by1-by0
        sc=target_w/zw; cw,ch=int(zw*sc),int(zh*sc)
        base=Image.open(BASE).convert('RGB').crop((bx0,by0,bx1,by1)).resize((cw,ch))
        def tp(lon,lat):
            bx,by=geo_to_big(lon,lat); return (bx-bx0)*sc,(by-by0)*sc
    layer=Image.new('RGBA',base.size,(0,0,0,0)); d=ImageDraw.Draw(layer)
    for name,poly,color in STATES:
        pts=[tp(lo,la) for lo,la in poly]
        d.polygon(pts,fill=(*color,70)); d.line(pts,fill=(*color,235),width=3,joint='curve')
    font=ImageFont.truetype(FONT,max(28,base.size[0]//45))
    for name,poly,color in STATES:
        pts=[tp(lo,la) for lo,la in poly]
        cx=sum(p[0] for p in pts)/len(pts); cy=sum(p[1] for p in pts)/len(pts)
        d.text((cx,cy),name,font=font,fill=(255,255,255,255),stroke_width=4,stroke_fill=(20,20,20,255),anchor='mm')
    Image.alpha_composite(base.convert('RGBA'),layer).convert('RGB').save(out_path)
    print(f'[render] -> {out_path}')

render(None,os.path.join(OUTDIR,'you_bing_ji_overlay_stitched.png'),2600)
render((106.0,130.0,32.0,45.0),os.path.join(OUTDIR,'you_bing_ji_overlay_stitched_zoom.png'),3000)
print('Done.')
