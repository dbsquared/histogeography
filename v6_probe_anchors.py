"""Probe: sample 全览-郡级 pastel color at each state's 治所 anchor; check distinctness."""
import numpy as np
from PIL import Image
import json, os

BASE_DIR = r'E:\projects\3D地图制作'
LEGEND_DIR = os.path.join(BASE_DIR, r'汉末十三州地图范例')
with open(os.path.join(BASE_DIR, 'gcp_calibration.json'), encoding='utf-8') as f:
    CAL = json.load(f)
Ai=CAL['transform_inverse_zhi']['px_A']; Bi=CAL['transform_inverse_zhi']['px_B']; Ci=CAL['transform_inverse_zhi']['px_C']
Di=CAL['transform_inverse_zhi']['py_D']; Ei=CAL['transform_inverse_zhi']['py_E']; Fi=CAL['transform_inverse_zhi']['py_F']
sx=CAL['scale_zhi_to_ji']['x']; sy=CAL['scale_zhi_to_ji']['y']

def wgs84_to_ji(lon,lat):
    zx=Ai*lon+Bi*lat+Ci; zy=Di*lon+Ei*lat+Fi
    return zx*sx, zy*sy

SEAL_WGS={
 '司隶':(111.50,35.00),'冀州':(115.70,37.40),'兖州':(116.00,35.50),'青州':(118.20,36.65),
 '徐州':(117.80,34.25),'扬州':(118.50,31.50),'荆州':(112.00,30.80),'豫州':(114.80,33.50),
 '益州':(105.00,30.80),'凉州':(104.50,36.50),'并州':(112.60,37.20),'幽州':(116.80,39.50),
 '交州':(111.50,22.50)}

ji_full=np.array(Image.open(os.path.join(LEGEND_DIR,'全览-郡级.png')).convert('RGB')).astype(np.int32)
H,W=ji_full.shape[:2]
print(f'全览-郡级 {W}x{H}')

cols={}
for sname,(lon,lat) in SEAL_WGS.items():
    ax,ay=wgs84_to_ji(lon,lat)
    if not (0<=ax<W and 0<=ay<H):
        print(f'{sname}: anchor ji=({ax:.0f},{ay:.0f}) OUT OF BOUNDS'); continue
    yy=int(ay); xx=int(ax)
    patch=ji_full[max(0,yy-12):yy+13, max(0,xx-12):xx+13].reshape(-1,3)
    c=tuple(int(x) for x in patch.mean(axis=0))
    cols[sname]=c
    print(f'{sname}: ji=({ax:6.0f},{ay:6.0f})  pastel=({c[0]:3d},{c[1]:3d},{c[2]:3d})')

# pairwise min distance
names=list(cols)
print('\nPairwise min RGB distance (should be >> ~25 to separate):')
for i in range(len(names)):
    for j in range(i+1,len(names)):
        d=np.sqrt(sum((np.array(cols[names[i]])-np.array(cols[names[j]]))**2))
        if d<60:
            print(f'  {names[i]}-{names[j]}: {d:.1f}  ({cols[names[i]]} vs {cols[names[j]]})')
print('(only pairs <60 shown; if none, all anchors well separated)')
