# -*- coding: utf-8 -*-
"""从全览-郡级.png 用颜色 k-means(k=13) 聚类提取13州。
k-means 比简单合并更能分出13个颜色簇(即使低分辨率抗锯齿bin多)。
"""
import numpy as np
from PIL import Image, ImageDraw
import json, os

BASE = r"E:\projects\3D地图制作\汉末十三州地图范例"
OUT_JSON = r"E:\projects\3D地图制作\legend_states_b.json"
PREVIEW_B = r"E:\projects\3D地图制作\rendered\legend_extract_b_states.png"
PREVIEW_BASE = r"E:\projects\3D地图制作\rendered\legend_extract_b_on_base.png"

B_LON0, B_LON1, B_LAT0, B_LAT1 = 80.0, 130.0, 15.0, 50.0
LON0, LON1, LAT0, LAT1 = 75.0, 140.0, 15.0, 55.0
BW, BH = 15600, 9600
K = 13

print("加载图B...")
ov = Image.open(os.path.join(BASE, "全览-郡级.png")).convert("RGB")
OW, OH = ov.size
arr = np.array(ov, dtype=np.uint8)
r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
mx = np.maximum.reduce([r, g, b]); mn = np.minimum.reduce([r, g, b])
bg = ((b > r + 20) & (b > 150)) | ((r < 55) & (g < 55) & (b < 55)) | \
     ((r > 150) & (g < 80) & (b < 80)) | \
     ((r > 235) & (g > 235) & (b > 235) & ((mx - mn) < 15)) | \
     ((mx - mn) < 40)
fg = ~bg
fgflat = arr.reshape(-1, 3)[fg.reshape(-1)].astype(np.float64)
N = fgflat.shape[0]
print(f"  前景像素 {N}")

rng = np.random.default_rng(7)
idx = rng.choice(N, K, replace=False)
centroids = fgflat[idx].copy()
for it in range(20):
    labels = np.zeros(N, dtype=np.int16)
    for i in range(0, N, 80000):
        xi = fgflat[i:i+80000]
        d = ((xi[:, None, :] - centroids[None, :, :]) ** 2).sum(2)
        labels[i:i+80000] = d.argmin(1)
    newc = np.array([fgflat[labels == k].mean(0) if (labels == k).any() else centroids[k] for k in range(K)])
    if np.allclose(newc, centroids):
        print(f"  kmeans 收敛于 {it} 轮"); centroids = newc; break
    centroids = newc

print("聚类中心(13州色):")
state_map = np.full((OH, OW), -1, dtype=np.int16)
state_map[fg] = labels
states_out = {}
preview_b = np.full((OH, OW, 3), 255, dtype=np.uint8)
preview_base = Image.new("RGB", (BW, BH), (255, 255, 255))
dr = ImageDraw.Draw(preview_base)
for i in range(K):
    mask = (state_map == i)
    area = mask.sum()
    up = np.roll(mask, 1, 0); dn = np.roll(mask, -1, 0)
    lf = np.roll(mask, 1, 1); rt = np.roll(mask, -1, 1)
    edge = mask & ~(up & dn & lf & rt)
    ys, xs = np.where(edge)
    col = tuple(int(v) for v in centroids[i])
    preview_b[ys, xs] = col
    lons = B_LON0 + (xs / OW) * (B_LON1 - B_LON0)
    lats = B_LAT0 + (ys / OH) * (B_LAT1 - B_LAT0)
    bxs = ((lons - LON0) / (LON1 - LON0) * BW).astype(np.int32)
    bys = ((LAT1 - lats) / (LAT1 - LAT0) * BH).astype(np.int32)
    good = (bxs >= 0) & (bxs < BW) & (bys >= 0) & (bys < BH)
    for x, y in zip(bxs[good], bys[good]):
        dr.point((int(x), int(y)), fill=col)
    states_out[f"state{i}"] = {"color": list(col), "area": int(area),
                               "n_edge": int(len(xs)),
                               "pts_b": np.stack([xs, ys], axis=1)[::max(1, len(xs)//3000)].tolist()}
    print(f"  州{i} RGB{col}: 面积 {100*area/(OW*OH):.2f}%, 边缘 {len(xs)}")

result = {"src": "全览-郡级.png", "size": [OW, OH],
          "method": "kmeans_k13_color",
          "assumed_range": [B_LON0, B_LON1, B_LAT0, B_LAT1],
          "state_colors": [list(states_out[f"state{i}"]["color"]) for i in range(K)],
          "states": states_out}
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False)
Image.fromarray(preview_b).resize((1515, 1064)).save(PREVIEW_B)
preview_base.resize((1986, 1403)).save(PREVIEW_BASE)
print(f"\n图B预览: {PREVIEW_B}\n底图预览: {PREVIEW_BASE}")
