#!/usr/bin/env python3
"""kmeans_diag.py — K-means(K=15) 发现真实聚类 + 空间定位, 用于核对调色板/州名映射"""
import json, os
import numpy as np
from PIL import Image
from sklearn.cluster import MiniBatchKMeans
from scipy.ndimage import median_filter

HERE = os.path.dirname(os.path.abspath(__file__))
VIEWER = os.path.join(HERE, 'viewer')
OV_IMG = os.path.join(VIEWER, 'overview_13states.png')
GCP_JSON = os.path.join(HERE, 'gcp_calibration.json')

with open(GCP_JSON, 'r', encoding='utf-8') as _f:
    cal = json.load(_f)
sx = cal['scale_zhi_to_ji']['x']; sy = cal['scale_zhi_to_ji']['y']
gcps = cal['gcps']
_X = np.array([[g['px']*sx, g['py']*sy, 1.0] for g in gcps])
FL = np.linalg.lstsq(_X, np.array([g['lon'] for g in gcps]), rcond=None)[0]
FA = np.linalg.lstsq(_X, np.array([g['lat'] for g in gcps]), rcond=None)[0]

def p2ll(px, py):
    return FL[0]*px*sx + FL[1]*py*sy + FL[2], FA[0]*px*sx + FA[1]*py*sy + FA[2]

img = Image.open(OV_IMG).convert('RGB'); W, H = img.size
arr = np.asarray(img, dtype=np.float32)
print(f'image {W}x{H}')

# 饱和像素 (排除灰白背景/海洋)
r = arr[:,:,0]; g = arr[:,:,1]; b = arr[:,:,2]
mx = np.max(arr, axis=2); mn = np.min(arr, axis=2)
sat = mx - mn
mask = sat > 18
ys, xs = np.where(mask)
pts = arr[ys, xs]
print(f'saturated pixels: {len(pts)} ({len(pts)/(W*H)*100:.1f}%)')

K = 15
km = MiniBatchKMeans(n_clusters=K, n_init=4, random_state=0, batch_size=4096)
km.fit(pts)
cent = km.cluster_centers_.astype(int)
lab = km.predict(pts)

# 每聚类: 颜色/数量/包围盒/地理质心
full = np.full((H, W), -1, dtype=np.int16)
full[ys, xs] = lab
print('\ncluster | RGB | #px | %img | bbox(x0,y0,x1,y1) | lon/lat-center')
for c in range(K):
    cy, cx = np.where(full == c)
    n = len(cx)
    x0, x1 = cx.min(), cx.max(); y0, y1 = cy.min(), cy.max()
    # 地理质心 (用像素均值)
    lons = []; lats = []
    for yy, xx in zip(cy[::max(1,n//200)], cx[::max(1,n//200)]):
        lo, la = p2ll(xx, yy); lons.append(lo); lats.append(la)
    glon = float(np.mean(lons)); glat = float(np.mean(lats))
    print(f'  [{c:2d}] ({cent[c,0]:3d},{cent[c,1]:3d},{cent[c,2]:3d}) {n:7d} {n/(W*H)*100:5.1f}% '
          f'{(x0,x1,y0,y1)}  ({glon:.1f},{glat:.1f})')

# 可视化: 每个聚类一种颜色
import cv2
vis = np.zeros((H, W, 3), dtype=np.uint8)
np.random.seed(7)
pal = np.random.randint(0, 255, (K, 3), dtype=np.uint8)
pal[np.where((cent[:,0]>200)&(cent[:,1]>200)&(cent[:,2]>200))[0]] = (240,240,240)  # 浅色->灰白
for c in range(K):
    cy, cx = np.where(full == c)
    vis[cy, cx] = pal[c]
Image.fromarray(vis).save(os.path.join(HERE, 'kmeans_diag_vis.png'))
print('\nsaved kmeans_diag_vis.png')
