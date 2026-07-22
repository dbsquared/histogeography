#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""幽州 / 并州 / 冀州 三州边界各自独立配准后，叠加到 china_full_v3.png 核对。

关键发现：三张范例图是各自独立居中/缩放的不同帧（冀州图四角 lon108.7-119.5，
幽州图 lon113.5-127.7），不能共用一个多项式。因此每州用自己的锚点表：
  - 幽州：youzhou_layer_v2/youzhou_anchor_table.json + SHIFT(0.75,0.30)
  - 冀州：jizhou_anchor_table.json + SHIFT(0,0)
  - 并州：bingzhou_anchor_table.json（5 个城市地标锚点，用户标注）
"""
import os, json, math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, 'china_full_v3.png')
OUTDIR = os.path.join(HERE, 'you_bing_ji_overlay')
os.makedirs(OUTDIR, exist_ok=True)

BW, BH = 15600, 9600
LON0, LON1 = 75.0, 140.0
LAT0, LAT1 = 15.0, 55.0
def geo_to_big(lon, lat):
    return (lon-LON0)/(LON1-LON0)*BW, (LAT1-lat)/(LAT1-LAT0)*BH

# ---------- 配准工具 ----------
def basis1(x, y, deg):
    t=[1.0]
    for p in range(1,deg+1):
        for j in range(p+1): t.append(float(x)**(p-j)*float(y)**j)
    return t
def fit_poly(pts,vals,deg):
    A=np.array([basis1(x,y,deg) for x,y in pts],dtype=float)
    c,*_=np.linalg.lstsq(A,np.array(vals,dtype=float),rcond=None); return c,deg
def predict(c,deg,x,y):
    return float(np.dot(c[:len(basis1(x,y,deg))],basis1(x,y,deg)))
def build_mapper(anchors):
    axy=[(a['px'],a['py']) for a in anchors]
    n=len(anchors)
    # 自适应阶数：>=8 个锚点用二次，否则用一次（防外推爆炸）
    deg=2 if n>=8 else 1
    cl,_=fit_poly(axy,[a['lon'] for a in anchors],deg)
    ca,_=fit_poly(axy,[a['lat'] for a in anchors],deg)
    print(f'    配准: {n} 个锚点, {deg}次多项式')
    # 残差报告
    max_err=0
    for a in anchors:
        pl=predict(cl,deg,a['px'],a['py'])
        pa=predict(ca,deg,a['px'],a['py'])
        e=math.hypot((pl-a['lon'])*111*math.cos(math.radians(a['lat'])),(pa-a['lat'])*111)
        max_err=max(max_err,e)
    print(f'    最大残差: {max_err:.1f} km')
    return lambda x,y:(predict(cl,deg,x,y),predict(ca,deg,x,y))

def load_pts(path):
    d=json.load(open(path,encoding='utf-8'))
    raw=d['points'] if 'points' in d else d
    out=[]
    for p in raw:
        out.append((float(p['px']),float(p['py'])) if isinstance(p,dict) else (float(p[0]),float(p[1])))
    return out

# ---------- 并州锚点表 bootstrap ----------
def mask_side_edge(img, mask_fn, side, frac=0.18):
    """取二值掩膜某一侧(side='west'/'east')约 frac 比例的边界点，按 y 排序。"""
    b,g,r = (img[:,:,i].astype(int) for i in (0,1,2))
    mask = mask_fn(r,g,b).astype(np.uint8)
    k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(7,7))
    mask=cv2.morphologyEx(mask,cv2.MORPH_CLOSE,k,iterations=1)
    cnts,_=cv2.findContours(mask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
    if not cnts: return np.empty((0,2))
    c=max(cnts,key=cv2.contourArea).reshape(-1,2)
    xs=c[:,0]
    thr = (np.percentile(xs,frac*100) if side=='west' else np.percentile(xs,(1-frac)*100))
    sel = (c[:,0]<=thr) if side=='west' else (c[:,0]>=thr)
    edge=c[sel]
    edge=edge[np.argsort(edge[:,1])]  # 按 y 升序
    return edge

def bingzhou_mask(r,g,b):
    raw=(r>g+20)&(r>b+20)&(r>=170)&(r<=245)&(g<185)&(b<205)
    youzhou=(g>r+18)&(g>b+8)&(g>110)&(r<165)
    jizhou=(g>r+28)&(g>b+12)&(g>=170)
    sili=(np.abs(r-g)<35)&(g>b+8)&(g>=188)
    liang=(r<g+10)&(r<b+15)&(g>=155)&(b>=125)&(r<175)&(g>r)
    return raw & ~(youzhou|jizhou|sili|liang)
def jizhou_mask(r,g,b):
    raw=(g>r+35)&(g>b+10)&(g>=175)&(g<=245)
    bing=(r>g+15)&(r>b)&(r>100)
    sili=(np.abs(r-g)<30)&(g>b+10)&(g>=200)
    you=(r<g-20)&(b<g)&(g>120)&(r<150)
    qing=(g>r+10)&(g>b)&(b<180)
    return raw & ~(bing|sili|you|qing)

def envelope(points, axis, side, nbins=60):
    """取多边形某侧包络：按 axis(0=x/1=y) 分箱，取 side('min'/'max') 端的点。
    points: Nx2 (x,y)。返回按 axis 升序的重采样包络点。"""
    ps=np.array(points,float)
    a=ps[:,axis]
    lo,hi=a.min(),a.max()
    edges=np.linspace(lo,hi,nbins+1)
    out=[]
    for i in range(nbins):
        m=(a>=edges[i])&(a<edges[i+1])
        if m.sum()==0: continue
        seg=ps[m]
        p=seg[seg[:,1-axis].argmin() if side=='min' else seg[:,1-axis].argmax()]
        out.append(p)
    return np.array(out)

def build_bingzhou_anchors(n=15):
    """用冀州已正确落位多边形的『西岸包络』(=并-冀边界) 与
       并州多边形的『东岸包络』(=同一边界) 按南北分数配对生成并州锚点。"""
    jz_map=build_mapper(json.load(open(os.path.join(HERE,'jizhou_anchor_table.json'),encoding='utf-8')))
    # 冀州多边形（像素，冀州图帧）
    jz_px=load_pts(os.path.join(HERE,'jizhou_step1_v7c','boundary_points.json'))
    # 并州多边形（像素，并州图帧）
    bz_px=load_pts(os.path.join(HERE,'bingzhou_step1_v7c','boundary_points.json'))
    # 冀州西岸包络 = 并-冀边界；转为真实 lon/lat
    env_jz=envelope(jz_px, axis=1, side='min', nbins=80)   # 按 y 分箱取 min-x
    if len(env_jz)<5: raise RuntimeError('冀州西岸包络点不足')
    env_jz_ll=np.array([jz_map(float(x),float(y)) for x,y in env_jz])  # (lon,lat)
    # 并州东岸包络 = 并-冀边界
    env_bz=envelope(bz_px, axis=1, side='max', nbins=80)   # 按 y 分箱取 max-x
    if len(env_bz)<5: raise RuntimeError('并州东岸包络点不足')
    # 按 y 分数重采样到 n 个点配对
    def resamp(pts,n):
        ys=pts[:,1]; f=(ys-ys.min())/(ys.max()-ys.min()+1e-9)
        o=np.argsort(f); f=f[o]; p=pts[o]
        fi=np.linspace(0,1,n)
        return np.column_stack([np.interp(fi,f,p[:,0]),np.interp(fi,f,p[:,1])])
    rj=resamp(env_jz_ll,n)   # (lon,lat)
    rb=resamp(env_bz,n)      # (px,py)
    anchors=[]
    for (lon,lat),(xb,yb) in zip(rj,rb):
        anchors.append({'name':'并冀界','type':'border','lon':round(lon,3),'lat':round(lat,3),
                        'px':int(xb),'py':int(yb)})
    # 西界约束：并州西界为黄河弯曲（地理已知坐标），与并州西岸包络按南北配对，
    # 防止西界被二次式外推偏东。
    yellow_river=[(111.0,40.3),(110.6,39.5),(110.3,38.5),(110.2,37.5),
                  (110.3,36.5),(110.6,35.5),(111.0,34.8)]
    env_bz_w=envelope(bz_px, axis=1, side='min', nbins=80)   # 并州西岸包络
    if len(env_bz_w)>=5:
        ry=np.array([p[1] for p in yellow_river]); order=np.argsort(ry)
        yr=np.array([yellow_river[i][1] for i in order]); xr=np.array([yellow_river[i][0] for i in order])
        fi=np.linspace(0,1,n)
        fr=(yr-yr.min())/(yr.max()-yr.min())
        lon_w=np.interp(fi,fr,xr); lat_w=np.interp(fi,fr,yr)
        rw=resamp(env_bz_w,n)
        for (lo,la),(xb,yb) in zip(zip(lon_w,lat_w),rw):
            anchors.append({'name':'黄河界','type':'border','lon':round(lo,3),'lat':round(la,3),
                            'px':int(xb),'py':int(yb)})
    return anchors

# ---------- 各州配置 ----------
ji_anchors=json.load(open(os.path.join(HERE,'jizhou_anchor_table.json'),encoding='utf-8'))
yo_anchors=json.load(open(os.path.join(HERE,'youzhou_layer_v2','youzhou_anchor_table.json'),encoding='utf-8'))
bz_anchors=json.load(open(os.path.join(HERE,'bingzhou_anchor_table.json'),encoding='utf-8'))
print(f'[anchors] 并州真实锚点 {len(bz_anchors)} 个: {[a["name"] for a in bz_anchors]}')

STATES=[
    ('幽州','youzhou_step1/boundary_points.json',(96,168,120), yo_anchors, (0.75,0.30)),
    ('冀州','jizhou_step1_v7c/boundary_points.json',(70,200,180), ji_anchors, (0.0,0.0)),
    ('并州','bingzhou_step1_v7c/boundary_points.json',(213,90,90), bz_anchors, (0.0,0.0)),
]

PREV_W=2600; PREV_H=int(BH*PREV_W/BW)
sx=BW/PREV_W; sy=BH/PREV_H
base=Image.open(BASE).convert('RGB').resize((PREV_W,PREV_H)).convert('RGBA')

state_polys=[]
poly_px_full={}   # name -> list of (lon,lat) 大图完整点（含闭合点）
for name,pts_path,color,anchors,shift in STATES:
    mapper=build_mapper(anchors)
    poly_px=load_pts(pts_path)
    lons,lats=[],[]
    ll=[]
    for (x,y) in poly_px:
        lon,lat=mapper(float(x),float(y))
        lon+=shift[0]; lat+=shift[1]
        lons.append(lon); lats.append(lat)
        ll.append((lon,lat))
    if ll and ll[0]!=ll[-1]: ll.append(ll[0])
    poly_px_full[name]=ll
    big=[geo_to_big(lon,lat) for (lon,lat) in ll]
    prev=[(int(bx/sx),int(by/sy)) for bx,by in big]
    state_polys.append((name,color,prev))
    print(f'  {name}: {len(poly_px)}点 -> lon[{min(lons):.2f},{max(lons):.2f}] lat[{min(lats):.2f},{max(lats):.2f}]')

# ---------- 叠加 + 标注 ----------
FONT=r'C:/Windows/Fonts/simhei.ttf'
font_big=ImageFont.truetype(FONT,46)
layer=Image.new('RGBA',(PREV_W,PREV_H),(0,0,0,0))
d=ImageDraw.Draw(layer)
for name,color,prev in state_polys:
    R,Gc,Bc=color
    d.polygon(prev,fill=(R,Gc,Bc,70))
    d.line(prev,fill=(R,Gc,Bc,235),width=3,joint='curve')
for name,color,prev in state_polys:
    xs=[p[0] for p in prev]; ys=[p[1] for p in prev]
    cx,cy=sum(xs)/len(xs),sum(ys)/len(ys)
    d.text((cx,cy),name,font=font_big,fill=(255,255,255,255),stroke_width=4,stroke_fill=(20,20,20,255),anchor='mm')

composite=Image.alpha_composite(base,layer).convert('RGB')
composite.save(os.path.join(OUTDIR,'you_bing_ji_overlay_a70.png'))
composite.resize((1300,int(PREV_H*1300/PREV_W))).save(os.path.join(OUTDIR,'you_bing_ji_overlay_small.jpg'),quality=85)
print(f'[done] full -> {OUTDIR}')

# ---------- 华北区域放大图（直接裁大图高分辨率） ----------
print('[zoom] 生成华北放大图 ...')
ZLON0,ZLON1,ZLAT0,ZLAT1 = 106.0, 130.0, 32.0, 45.0
zbx0,zby0 = geo_to_big(ZLON0, ZLAT1)   # 左上
zbx1,zby1 = geo_to_big(ZLON1, ZLAT0)   # 右下
zbx0,zby0,zbx1,zby1 = map(int,(zbx0,zby0,zbx1,zby1))
zw = zbx1-zbx0; zh = zby1-zby0
base_big = Image.open(BASE).convert('RGB')
crop = base_big.crop((zbx0,zby0,zbx1,zby1)).resize((min(3000,zw), min(1846,zh)))
cw,ch = crop.size
# 状态多边形映射到放大图坐标
cx0 = zbx0; cy0 = zby0
zoom_polys=[]
for name,color,prev in state_polys:
    big_full=[]
    for (x,y) in poly_px_full[name]:
        bx,by=geo_to_big(x,y)
        big_full.append((int((bx-cx0)*cw/zw), int((by-cy0)*ch/zh)))
    zoom_polys.append((name,color,big_full))
zl=ImageDraw.Draw(crop)
for name,color,zp in zoom_polys:
    R,Gc,Bc=color
    zl.polygon(zp,fill=(R,Gc,Bc,70))
    zl.line(zp,fill=(R,Gc,Bc,235),width=3,joint='curve')
for name,color,zp in zoom_polys:
    xs=[p[0] for p in zp]; ys=[p[1] for p in zp]
    zl.text((sum(xs)/len(xs),sum(ys)/len(ys)),name,font=font_big,fill=(255,255,255,255),
            stroke_width=4,stroke_fill=(20,20,20,255),anchor='mm')
crop.save(os.path.join(OUTDIR,'you_bing_ji_overlay_zoom.png'))
print(f'[done] zoom -> {OUTDIR}/you_bing_ji_overlay_zoom.png')
