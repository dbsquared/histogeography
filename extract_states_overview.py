# -*- coding: utf-8 -*-
"""从全览-郡治.png 提取13州边界轮廓，映射到SRTM底图坐标，生成校验预览。
底图 china_full_v3: 经度75-140E, 纬度15-55N, 15600x9600px, 等经纬。
假设全览图同为等经纬且范围相同（后续据预览校准）。
"""
import numpy as np
from PIL import Image
import json, os
from collections import Counter

BASE = r"E:\projects\3D地图制作\汉末十三州地图范例"
OUT_JSON = r"E:\projects\3D地图制作\legend_states.json"
PREVIEW = r"E:\projects\3D地图制作\rendered\legend_states_extract_preview.png"

# 底图范围
LON0, LON1, LAT0, LAT1 = 75.0, 140.0, 15.0, 55.0
BW, BH = 15600, 9600

# 1. 加载全览图 (uint8 省内存)
print("加载全览图...")
ov = Image.open(os.path.join(BASE, "全览-郡治.png")).convert("RGB")
OW, OH = ov.size
print(f"  尺寸 {OW}x{OH}")
arr = np.array(ov, dtype=np.uint8)

# 2. 掩码：海洋/白/黑/红(现代地图或标注)
r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
ocean = (b > r + 20) & (b > 150) & (g > 140)
white = (r > 235) & (g > 235) & (b > 235)
black = (r < 50) & (g < 50) & (b < 50)
red   = (r > 150) & (g < 90) & (b < 90)
bg_mask = ocean | white | black | red
print(f"  背景像素(海洋/白/黑/红): {bg_mask.sum()} / {OW*OH}")

# 3. 州填充像素聚类：量化//16，取top N浅色
land = arr[~bg_mask]
q = (land // 16 * 16)
cnt = Counter(map(tuple, q))
cands = [(tuple(int(c) for c in color), n / land.shape[0]) for color, n in cnt.most_common(25)]
print("\n候选州色 (top 25 浅色):")
for c, f in cands:
    print(f"  RGB{c}: {f*100:.2f}%")

state_colors = [c for c, f in cands if f > 0.003][:13]
print(f"\n选定 {len(state_colors)} 个州色:")
for c in state_colors:
    print(f"  RGB{c}")

# 4. 每个像素分配到最近州色
print("\n分配像素到州...")
flat_land = land.reshape(-1, 3).astype(np.int32)
state_arr = np.full(flat_land.shape[0], -1, dtype=np.int16)
for i, sc in enumerate(state_colors):
    sc = np.array(sc, dtype=np.int32)
    d = np.sum((flat_land - sc) ** 2, axis=1)
    state_arr[d < 1200] = i
state_map = np.full((OH, OW), -1, dtype=np.int16)
state_map[~bg_mask] = state_arr.reshape(OH, OW)

# 5. 边界提取：每州 mask 的边缘 (4邻域有非本州)
print("提取边界...")
states_out = {}
preview = np.full((OH, OW, 3), 255, dtype=np.uint8)
for i, sc in enumerate(state_colors):
    mask = (state_map == i)
    up = np.roll(mask, 1, axis=0); dn = np.roll(mask, -1, axis=0)
    lf = np.roll(mask, 1, axis=1); rt = np.roll(mask, -1, axis=1)
    edge = mask & ~(up & dn & lf & rt)
    ys, xs = np.where(edge)
    bxs = (xs / OW) * BW
    bys = (ys / OH) * BH
    pts = np.stack([bxs, bys], axis=1).astype(np.int32)
    states_out[i] = {"color": list(sc), "n_edge": int(len(pts)),
                     "points_sample": pts[::max(1, len(pts)//3000)].tolist()}
    preview[ys, xs] = sc
    print(f"  州{i} RGB{sc}: 边缘像素 {len(pts)}")

# 6. 保存
result = {
    "base_range": [LON0, LON1, LAT0, LAT1],
    "overview_size": [OW, OH],
    "state_colors": [list(c) for c in state_colors],
    "states": {str(k): v for k, v in states_out.items()},
}
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False)

pv = Image.fromarray(preview).resize((1986, 1403))
pv.save(PREVIEW)
print(f"\n已保存: {OUT_JSON}\n预览: {PREVIEW}")
