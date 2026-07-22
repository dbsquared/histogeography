import json
from PIL import Image
import os

OUTDIR = 'E:/projects/3D地图制作/youzhou_overlay_step1'
pts = json.load(open('E:/projects/3D地图制作/youzhou_step1/boundary_points.json'))['points']
W, H = 15600, 9600
LON0, LON1 = 75.0, 140.0
LAT0, LAT1 = 15.0, 55.0
corr = json.load(open('E:/projects/3D地图制作/youzhou_layer_v2/youzhou_correspondence.json'))
coef = corr['method']  # just for record

# 与 overlay_youzhou_step1.py 保持一致：东移 0.75° + 北移 0.30°
SHIFT_DEG_LON = 0.75
SHIFT_DEG_LAT = 0.30

prev_w, prev_h = 2600, 1600
scale_x, scale_y = W/prev_w, H/prev_h

prev_pts = []
for c in corr['points']:
    lon, lat = c['lon'] + SHIFT_DEG_LON, c['lat'] + SHIFT_DEG_LAT
    bx = (lon - LON0) / (LON1 - LON0) * W
    by = (LAT1 - lat) / (LAT1 - LAT0) * H
    prev_pts.append((int(bx/scale_x), int(by/scale_y)))

xs = [p[0] for p in prev_pts]
ys = [p[1] for p in prev_pts]
cx, cy = (min(xs)+max(xs))//2, (min(ys)+max(ys))//2

# crop 1000x800 centered on region
for tag in ['a70', 'a90']:
    img = Image.open(f'{OUTDIR}/youzhou_overlay_{tag}.png')
    iw, ih = img.size
    w, h = 1000, 800
    x1, y1 = max(0, cx - w//2), max(0, cy - h//2)
    x2, y2 = min(iw, x1 + w), min(ih, y1 + h)
    crop = img.crop((x1, y1, x2, y2))
    crop.save(f'{OUTDIR}/youzhou_overlay_{tag}_zoom.png')
    print(f'saved zoom {tag}')

# Also make a region-only crop with a bit more context (1200x900)
for tag in ['a70']:
    img = Image.open(f'{OUTDIR}/youzhou_overlay_{tag}.png')
    iw, ih = img.size
    w, h = 1200, 900
    x1, y1 = max(0, cx - w//2), max(0, cy - h//2)
    x2, y2 = min(iw, x1 + w), min(ih, y1 + h)
    crop = img.crop((x1, y1, x2, y2))
    crop.save(f'{OUTDIR}/youzhou_overlay_{tag}_zoom_large.png')
    print(f'saved large zoom {tag}')
