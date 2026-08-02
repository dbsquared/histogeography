#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为各州 geojson 预填候选「郡治」(seats)。
数据源：digitize_v2.html 中的 GCP_DB（古地名/现代城市→经纬度，即各郡治/主要城）。
方法：用各州 geojson 自带 GCP（像素+经纬度）解出仿射，把 GCP_DB[州] 反投影到像素，写入 pixels.seats。
幂等：仅当 pixels.seats 为空时才填充，避免覆盖用户已编辑的郡治。
"""
import json, re, os, math

VIEWER = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(VIEWER, 'digitize_v2.html')
RAW  = os.path.join(VIEWER, 'han_states_raw')

# ── 1. 从 HTML 提取 GCP_DB ──
with open(HTML, encoding='utf-8') as f:
    txt = f.read()
m = re.search(r'const GCP_DB\s*=\s*(\{.*?\n\});', txt, re.S)
if not m:
    raise SystemExit('找不到 GCP_DB')
block = m.group(1)
# 给未加引号的键名加双引号：name:/lon:/lat:
block = re.sub(r'(?<![A-Za-z0-9_"\'])(name|lon|lat)\s*:', r'"\1":', block)
GCP_DB = eval(block, {'__builtins__': {}}, {})

# ── 2. 仿射最小二乘（与 HTML computeAffine 一致）──
def lstsq(pts, vals):
    n = len(pts)
    if n < 3: return None
    s11=s12=s13=s22=s23=s33=t1=t2=t3=0.0
    for (x,y,_) , v in zip(pts, vals):
        s11+=x*x; s12+=x*y; s13+=x
        s22+=y*y; s23+=y; s33+=1
        t1+=x*v; t2+=y*v; t3+=v
    A=[[s11,s12,s13,t1],[s12,s22,s23,t2],[s13,s23,s33,t3]]
    for c in range(3):
        p=c
        for r in range(c+1,3):
            if abs(A[r][c])>abs(A[p][c]): p=r
        A[c],A[p]=A[p],A[c]
        d=A[c][c]
        if abs(d)<1e-12: return None
        for j in range(c,4): A[c][j]/=d
        for r in range(3):
            if r==c: continue
            fct=A[r][c]
            for j in range(c,4): A[r][j]-=fct*A[c][j]
    return [A[0][3],A[1][3],A[2][3]]

def affine(gcps):
    pts=[[g['px'],g['py'],1] for g in gcps]
    Mlon=lstsq(pts,[g['lon'] for g in gcps])
    Mlat=lstsq(pts,[g['lat'] for g in gcps])
    if not Mlon or not Mlat: return None
    return Mlon,Mlat

def lonlat_to_px(lon,lat,Mlon,Mlat):
    a,b,c=Mlon; d,e,f=Mlat
    det=a*e-b*d
    if abs(det)<1e-12: return None
    u=lon-c; v=lat-f
    px=(e*u-b*v)/det; py=(-d*u+a*v)/det
    return px,py

# ── 3. 遍历各州 geojson，填充 seats ──
filled=0; skipped=0
for fn in sorted(os.listdir(RAW)):
    if not fn.endswith('.geojson'): continue
    state=fn[:-len('.geojson')]
    path=os.path.join(RAW,fn)
    with open(path,encoding='utf-8') as f:
        gj=json.load(f)
    px=gj.setdefault('pixels',{})
    seats=px.get('seats')
    if seats:            # 已有郡治，跳过
        skipped+=1; continue
    gcps=px.get('gcps')
    if not gcps or len(gcps)<4:
        print(f'  [跳过] {state}: GCP 不足 4 个，无法反投影'); skipped+=1; continue
    aff=affine(gcps)
    if not aff:
        print(f'  [跳过] {state}: 仿射求解失败'); skipped+=1; continue
    Mlon,Mlat=aff
    cities=GCP_DB.get(state,[])
    if not cities:
        print(f'  [跳过] {state}: GCP_DB 无该州城市'); skipped+=1; continue
    new_seats=[]
    for c in cities:
        pp=lonlat_to_px(c['lon'],c['lat'],Mlon,Mlat)
        if not pp: continue
        x,y=pp
        # 仅保留落在图内的点（允许少量外溢容差）
        new_seats.append({'px':round(x,1),'py':round(y,1),'name':c['name'],'role':'commandery'})
    px['seats']=new_seats
    # 同步更新 features 中的 commandery_seat
    feats=gj.get('features',[])
    feats=[ft for ft in feats if ft.get('properties',{}).get('kind')!='commandery_seat']
    for s in new_seats:
        feats.append({'type':'Feature',
                      'properties':{'kind':'commandery_seat','state':state,'name':s['name'],'role':s['role']},
                      'geometry':{'type':'Point','coordinates':[c['lon'],c['lat']]}})
    gj['features']=feats
    with open(path,'w',encoding='utf-8') as f:
        json.dump(gj,f,ensure_ascii=False,indent=2)
    print(f'  [填充] {state}: {len(new_seats)} 个候选郡治')
    filled+=1

print(f'\n完成：填充 {filled} 州，跳过 {skipped} 州（已有/不可用）。')
