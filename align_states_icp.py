#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三州边界贴合修正：以冀州为基准，用 ICP 式最近点配对把
   并州(东界) → 冀州(西界)、幽州(南界) → 冀州(北界) 做刚体平移贴合，
   消除各自独立配准造成的共用边界空隙。

输出:
  you_bing_ji_overlay/aligned_polys.json      修正后三州经纬度多边形
  you_bing_ji_overlay/you_bing_ji_overlay_aligned.png       全图
  you_bing_ji_overlay/you_bing_ji_overlay_aligned_zoom.png  华北放大
"""
import os, json, math
import numpy as np
from scipy.spatial import cKDTree
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

# ---------- 配准(与 overlay_you_bing_ji_combined.py 相同) ----------
def basis1(x, y, deg):
    t=[1.0]
    for p in range(1,deg+1):
        for j in range(p+1): t.append(float(x)**(p-j)*float(y)**j)
    return t
def fit_poly(pts,vals,deg):
    A=np.array([basis1(x,y,deg) for x,y in pts],dtype=float)
    c,*_=np.linalg.lstsq(A,np.array(vals,dtype=float),rcond=None); return c
def predict(c,deg,x,y):
    return float(np.dot(c[:len(basis1(x,y,deg))],basis1(x,y,deg)))
def build_mapper(anchors):
    axy=[(a['px'],a['py']) for a in anchors]
    deg=2 if len(anchors)>=8 else 1
    cl=fit_poly(axy,[a['lon'] for a in anchors],deg)
    ca=fit_poly(axy,[a['lat'] for a in anchors],deg)
    return lambda x,y:(predict(cl,deg,x,y),predict(ca,deg,x,y))
def load_pts(path):
    d=json.load(open(path,encoding='utf-8'))
    raw=d['points'] if 'points' in d else d
    return [(float(p['px']),float(p['py'])) if isinstance(p,dict) else (float(p[0]),float(p[1])) for p in raw]

def poly_lonlat(pts_path, anchors, shift):
    m=build_mapper(anchors); out=[]
    for x,y in load_pts(os.path.join(HERE,pts_path)):
        lon,lat=m(x,y); out.append((lon+shift[0], lat+shift[1]))
    return out

ji_anchors=json.load(open(os.path.join(HERE,'jizhou_anchor_table.json'),encoding='utf-8'))
yo_anchors=json.load(open(os.path.join(HERE,'youzhou_layer_v2','youzhou_anchor_table.json'),encoding='utf-8'))
bz_anchors=json.load(open(os.path.join(HERE,'bingzhou_anchor_table.json'),encoding='utf-8'))

JI = poly_lonlat('jizhou_step1_v7c/boundary_points.json', ji_anchors, (0.0,0.0))
YO = poly_lonlat('youzhou_step1/boundary_points.json',    yo_anchors, (0.75,0.30))
BZ = poly_lonlat('bingzhou_step1_v7c/boundary_points.json', bz_anchors, (0.0,0.0))
print(f'落位(修正前): 冀{len(JI)}点 并{len(BZ)}点 幽{len(YO)}点')

# ---------- ICP 式平移贴合 ----------
LAT_MID = 38.5
KX = 111.0*math.cos(math.radians(LAT_MID))  # ~86.7 km/deg
KY = 111.0
def to_km(poly):
    return np.array([(lon*KX, lat*KY) for lon,lat in poly])
def icp_translate(moving, target, thresh_km=120.0, iters=6, keep_ratio=0.6):
    """对 moving 做纯平移，使其边界点贴合 target 最近边界点。
       只使用距离<阈值的配对，且每轮只用最近 keep_ratio 比例的配对(抗错配)。"""
    M=to_km(moving); T=to_km(target)
    tree=cKDTree(T)
    total_dx=total_dy=0.0
    for it in range(iters):
        dist,idx = tree.query(M, k=1)
        ok = dist < thresh_km
        if ok.sum() < 6:
            print(f'    iter{it}: 配对不足({ok.sum()}), 停止'); break
        d_ok = dist[ok]
        k = max(6, int(len(d_ok)*keep_ratio))
        sel_local = np.argsort(d_ok)[:k]
        Msel = M[ok][sel_local]; Tsel = T[idx[ok][sel_local]]
        delta = (Tsel-Msel).mean(axis=0)
        M = M + delta
        total_dx += delta[0]; total_dy += delta[1]
        print(f'    iter{it}: 配对{k}对, Δ=({delta[0]:+.1f},{delta[1]:+.1f})km, '
              f'残差中位{np.median(d_ok[sel_local]):.1f}km')
    # 最终残差
    dist,_ = tree.query(M, k=1)
    near = dist[dist<thresh_km]
    print(f'    贴合后: 近界点{len(near)}/{len(dist)}, '
          f'中位{np.median(near):.1f}km P90{np.percentile(near,90):.1f}km')
    dlon, dlat = total_dx/KX, total_dy/KY
    return [(lon+dlon, lat+dlat) for lon,lat in moving], (dlon,dlat)

print('\n[1] 并州 → 贴合冀州西界')
BZ2,(dbx,dby) = icp_translate(BZ, JI, thresh_km=120.0)
print(f'    并州总平移: Δlon{dbx:+.3f}° Δlat{dby:+.3f}°')

print('\n[2] 幽州 → 贴合冀州北界')
YO2,(dyx,dyy) = icp_translate(YO, JI, thresh_km=120.0)
print(f'    幽州总平移: Δlon{dyx:+.3f}° Δlat{dyy:+.3f}°')

def close(poly):
    return poly if poly[0]==poly[-1] else poly+[poly[0]]
JIc, BZc, YOc = close(JI), close(BZ2), close(YO2)
json.dump({'冀州':JIc,'并州':BZc,'幽州':YOc},
          open(os.path.join(OUTDIR,'aligned_polys.json'),'w',encoding='utf-8'),
          ensure_ascii=False)

# ---------- 渲染 ----------
STATES=[('幽州',YOc,(96,168,120)),('冀州',JIc,(70,200,180)),('并州',BZc,(213,90,90))]
FONT=r'C:/Windows/Fonts/simhei.ttf'

def render(crop_box, out_path, target_w):
    """crop_box=(lon0,lon1,lat0,lat1) 或 None=全图底图缩放"""
    if crop_box is None:
        prev_w=2600; prev_h=int(BH*prev_w/BW)
        base=Image.open(BASE).convert('RGB').resize((prev_w,prev_h))
        def to_px(lon,lat):
            bx,by=geo_to_big(lon,lat); return bx/(BW/prev_w), by/(BH/prev_h)
    else:
        zlon0,zlon1,zlat0,zlat1=crop_box
        bx0,by0=geo_to_big(zlon0,zlat1); bx1,by1=geo_to_big(zlon1,zlat0)
        bx0,by0,bx1,by1=map(int,(bx0,by0,bx1,by1))
        zw,zh=bx1-bx0,by1-by0
        scale=target_w/zw
        cw,ch=int(zw*scale),int(zh*scale)
        base=Image.open(BASE).convert('RGB').crop((bx0,by0,bx1,by1)).resize((cw,ch))
        def to_px(lon,lat):
            bx,by=geo_to_big(lon,lat)
            return (bx-bx0)*scale,(by-by0)*scale
    layer=Image.new('RGBA',base.size,(0,0,0,0))
    d=ImageDraw.Draw(layer)
    for name,poly,color in STATES:
        pts=[to_px(lon,lat) for lon,lat in poly]
        d.polygon(pts,fill=(*color,70))
        d.line(pts,fill=(*color,235),width=3,joint='curve')
    fsize=max(28,base.size[0]//45)
    font=ImageFont.truetype(FONT,fsize)
    for name,poly,color in STATES:
        pts=[to_px(lon,lat) for lon,lat in poly]
        cx=sum(p[0] for p in pts)/len(pts); cy=sum(p[1] for p in pts)/len(pts)
        d.text((cx,cy),name,font=font,fill=(255,255,255,255),
               stroke_width=4,stroke_fill=(20,20,20,255),anchor='mm')
    Image.alpha_composite(base.convert('RGBA'),layer).convert('RGB').save(out_path)
    print(f'[render] -> {out_path}')

render(None, os.path.join(OUTDIR,'you_bing_ji_overlay_aligned.png'), 2600)
render((106.0,130.0,32.0,45.0), os.path.join(OUTDIR,'you_bing_ji_overlay_aligned_zoom.png'), 3000)
print('\nDone.')
