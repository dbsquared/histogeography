#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analyze 冀州.png mask boundary to find candidate anchor points (coast, corners, extremes).

Outputs pixel coords of key boundary features for manual georeferencing.
"""
import json, os
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
MASK = os.path.join(HERE, 'jizhou_step1', 'mask_clean.png')
SRC = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
OUT = os.path.join(HERE, 'jizhou_step1', 'anchor_candidates.json')

mask = np.array(Image.open(MASK).convert('L'))
rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = mask.shape[:2]

# Get outer contour
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)
pts = main.reshape(-1, 2)  # (N, 2) array of (x, y)

print(f'Boundary points: {len(pts)}')
xs, ys = pts[:, 0], pts[:, 1]

# === Extremes ===
extremes = {
    'north': (int(xs[np.argmin(ys)]), int(ys.min())),
    'south': (int(xs[np.argmax(ys)]), int(ys.max())),
    'west':  (int(xs.min()), int(ys[np.argmin(xs)])),
    'east':  (int(xs.max()), int(ys[np.argmax(xs)])),
}
print(f'\nExtremes:')
for k, (x, y) in extremes.items():
    print(f'  {k}: ({x}, {y})')

# === Detect coastline segment (east side where boundary meets blue sea) ===
# Sea is blue-ish: B > R and B > G significantly, on right side of image
r, g, b = rgb[:,:,0].astype(int), rgb[:,:,1].astype(int), rgb[:,:,2].astype(int)
sea_mask = (b > r + 20) & (b > g + 10) & (b > 140)  # blue sea detection

# Find boundary points adjacent to sea
coast_pts = []
for i, (x, y) in enumerate(pts):
    if x > W * 0.6:  # eastern portion of boundary
        # Check if nearby pixels are blue (sea)
        for dx in [-5, 0, 5]:
            for dy in [-5, 0, 5]:
                nx_, ny_ = x + dx, y + dy
                if 0 <= nx_ < W and 0 <= ny_ < H and sea_mask[ny_, nx_]:
                    coast_pts.append((int(x), int(y), i))
                    break
            else:
                continue
            break

# Deduplicate coast points (keep every 20th point to spread out)
if len(coast_pts) > 15:
    step = len(coast_pts) // 12
    coast_sampled = [coast_pts[i] for i in range(0, len(coast_pts), step)][:12]
else:
    coast_sampled = coast_pts

print(f'\nCoastal boundary points: {len(coast_pts)} (sampled {len(coast_sampled)})')
for x, y, idx in coast_sampled:
    print(f'  coast ({x}, {y}) idx={idx} RGB=({rgb[y,x,0]},{rgb[y,x,1]},{rgb[y,x,2]})')

# === High-curvature corner detection ===
def get_curvature(pts_array, k=10):
    """Compute discrete curvature at each point."""
    n = len(pts_array)
    curv = np.zeros(n)
    for i in range(n):
        p_prev = pts_array[(i - k) % n]
        p_next = pts_array[(i + k) % n]
        v1 = p_prev - pts_array[i]
        v2 = p_next - pts_array[i]
        cross = float(v1[0]*v2[1] - v1[1]*v2[0])
        dot = float(np.dot(v1, v2))
        curv[i] = abs(np.arctan2(cross, dot))
    return curv

curvature = get_curvature(pts, k=15)
# Find top curvature peaks (corners)
corner_threshold = np.percentile(curvature, 95)
corner_indices = np.where(curvature > corner_threshold)[0]

# Cluster nearby corners (keep only one per cluster of radius 30px)
selected_corners = []
used = set()
for ci in sorted(corner_indices, key=lambda i: -curvature[i]):
    if ci in used:
        continue
    cx, cy = int(pts[ci][0]), int(pts[ci][1])
    selected_corners.append((cx, cy, float(curvature[ci]), ci))
    for j in range(len(pts)):
        dist = ((pts[j][0]-cx)**2 + (pts[j][1]-cy)**2)**0.5
        if dist < 40:
            used.add(j)

print(f'\nCorner points (top curvature):')
for x, y, cval, idx in selected_corners[:15]:
    print(f'  corner ({x}, {y}) curv={cval:.3f} idx={idx}')

# === Build candidates dict ===
candidates = {
    'image_size': [W, H],
    'extremes': [{'name':k, 'px':v[0], 'py':v[1]} for k,v in extremes.items()],
    'coast_points': [{'px':x, 'py':y, 'idx':i} for x,y,i in coast_sampled],
    'corner_points': [{'px':x, 'py':y, 'curvature':round(c,4), 'idx':i} for x,y,c,i in selected_corners[:15]],
}

with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(candidates, f, ensure_ascii=False, indent=2)
print(f'\nSaved candidates to {OUT}')
