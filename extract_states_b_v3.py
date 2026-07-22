# -*- coding: utf-8 -*-
"""从全览-郡级.png 提取13州边界 v3。
修复：前景像素数组赋值；按面积排除大背景块(>10%)；取13州。
"""
import numpy as np
from PIL import Image, ImageDraw
import json, os
from collections import Counter

BASE = r"E:\projects\3D地图制作\汉末十三州地图范例"
OUT_JSON = r"E:\projects\3D地图制作\legend_states_b.json"
PREVIEW_B = r"E:\projects\3D地图制作\rendered\legend_extract_b_states.png"
PREVIEW_BASE = r"E:\projects\3D地图制作\rendered\legend_extract_b_on_base.png"

B_LON0, B_LON1, B_LAT0, B_LAT1 = 80.0, 130.0, 15.0, 50.0  # 图B假设范围
LON0, LON1, LAT0, LAT1 = 75.0, 140.0, 15.0, 55.0
BW, BH = 15600, 9600

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
print(f"  尺寸 {OW}x{OH}, 前景像素: {fg.sum()} ({100*fg.sum()/(OW*OH):.1f}%)")

flat = arr.reshape(-1, 3).astype(np.int32)
fgflat = flat[fg.reshape(-1)]
q = (fgflat // 24 * 24)
cnt = Counter(map(tuple, map(tuple, q.tolist())))
items = sorted(cnt.items(), key=lambda x: -x[1])
seeds = []
for color, n in items:
    color = np.array(color)
    merged = False
    for s in seeds:
        if np.sum((s["c"] - color) ** 2) < 70 * 70:
            s["n"] += n; merged = True; break
    if not merged:
        seeds.append({"c": color.astype(int), "n": n})
# 排除大背景块(>10%前景), 取前13
seeds = [s for s in seeds if s["n"] < 0.10 * fg.sum()][:13]
print(f"\n合并+过滤后种子 {len(seeds)} 个:")
for s in seeds:
    print(f"  RGB{tuple(int(v) for v in s['c'])}: {100*s['n']/fg.sum():.2f}%")

state_arr = np.full(fgflat.shape[0], -1, dtype=np.int16)
for i, s in enumerate(seeds):
    sc = s["c"].astype(np.int32)
    d = np.sum((fgflat - sc) ** 2, axis=1)
    state_arr[d < 1600] = i
state_map = np.full((OH, OW), -1, dtype=np.int16)
state_map[fg] = state_arr

states_out = {}
preview_b = np.full((OH, OW, 3), 255, dtype=np.uint8)
preview_base = Image.new("RGB", (BW, BH), (255, 255, 255))
dr = ImageDraw.Draw(preview_base)
for i, s in enumerate(seeds):
    mask = (state_map == i)
    up = np.roll(mask, 1, 0); dn = np.roll(mask, -1, 0)
    lf = np.roll(mask, 1, 1); rt = np.roll(mask, -1, 1)
    edge = mask & ~(up & dn & lf & rt)
    ys, xs = np.where(edge)
    preview_b[ys, xs] = s["c"]
    lons = B_LON0 + (xs / OW) * (B_LON1 - B_LON0)
    lats = B_LAT0 + (ys / OH) * (B_LAT1 - B_LAT0)
    bxs = ((lons - LON0) / (LON1 - LON0) * BW).astype(np.int32)
    bys = ((LAT1 - lats) / (LAT1 - LAT0) * BH).astype(np.int32)
    good = (bxs >= 0) & (bxs < BW) & (bys >= 0) & (bys < BH)
    for x, y in zip(bxs[good], bys[good]):
        dr.point((int(x), int(y)), fill=tuple(int(v) for v in s["c"]))
    states_out[f"state{i}"] = {"color": [int(v) for v in s["c"]],
                               "area": int(mask.sum()),
                               "n_edge": int(len(xs)),
                               "pts_b": np.stack([xs, ys], axis=1)[::max(1, len(xs)//3000)].tolist()}
    print(f"  州{i} RGB{tuple(int(v) for v in s['c'])}: 面积 {100*mask.sum()/(OW*OH):.2f}%, 边缘 {len(xs)}")

result = {"src": "全览-郡级.png", "size": [OW, OH],
          "assumed_range": [B_LON0, B_LON1, B_LAT0, B_LAT1],
          "state_colors": [[int(v) for v in s["c"]] for s in seeds],
          "states": states_out}
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False)
Image.fromarray(preview_b).resize((1515, 1064)).save(PREVIEW_B)
preview_base.resize((1986, 1403)).save(PREVIEW_BASE)
print(f"\n图B预览: {PREVIEW_B}\n底图预览: {PREVIEW_BASE}")
