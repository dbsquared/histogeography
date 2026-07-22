# -*- coding: utf-8 -*-
"""从全览-郡级.png 提取13州边界（该图配色区分度好，与分州图同系统）。
输出：图B像素系预览 + 假设范围的底图系预览 + 每州边缘点JSON。
"""
import numpy as np
from PIL import Image
import json, os
from collections import Counter

BASE = r"E:\projects\3D地图制作\汉末十三州地图范例"
OUT_JSON = r"E:\projects\3D地图制作\legend_states_b.json"
PREVIEW_B = r"E:\projects\3D地图制作\rendered\legend_extract_b_states.png"
PREVIEW_BASE = r"E:\projects\3D地图制作\rendered\legend_extract_b_on_base.png"

LON0, LON1, LAT0, LAT1 = 80.0, 130.0, 15.0, 50.0  # 假设图B范围(东汉典型)
BW, BH = 15600, 9600

def is_state_color(c):
    r, g, b = c
    if max(c) - min(c) < 25:
        return False
    if b > r + 20 and b > 150:
        return False
    if r < 60 and g < 60 and b < 60:
        return False
    if r > 150 and g < 90 and b < 90:
        return False
    return True

print("加载图B...")
ov = Image.open(os.path.join(BASE, "全览-郡级.png")).convert("RGB")
OW, OH = ov.size
print(f"  尺寸 {OW}x{OH}")
arr = np.array(ov, dtype=np.uint8)
flat = arr.reshape(-1, 3)

q = (flat // 16 * 16)
cnt = Counter(map(tuple, q.tolist()))
cands = [(c, n / flat.shape[0]) for c, n in cnt.most_common(60) if is_state_color(c)]
print(f"候选州色: {len(cands)}")
for c, f in cands[:15]:
    print(f"  RGB{c}: {f*100:.2f}%")
state_colors = [c for c, f in cands[:13]]
print(f"选 {len(state_colors)} 州色")

fi = flat.astype(np.int32)
state_arr = np.full(fi.shape[0], -1, dtype=np.int16)
for i, sc in enumerate(state_colors):
    sc = np.array(sc, dtype=np.int32)
    d = np.sum((fi - sc) ** 2, axis=1)
    state_arr[d < 1600] = i
state_map = state_arr.reshape(OH, OW)

states_out = {}
preview_b = np.full((OH, OW, 3), 255, dtype=np.uint8)
preview_base = Image.new("RGB", (BW, BH), (255, 255, 255))
import PIL.ImageDraw as ImageDraw
dr = ImageDraw.Draw(preview_base)
for i, sc in enumerate(state_colors):
    mask = (state_map == i)
    area = int(mask.sum())
    up = np.roll(mask, 1, 0); dn = np.roll(mask, -1, 0)
    lf = np.roll(mask, 1, 1); rt = np.roll(mask, -1, 1)
    edge = mask & ~(up & dn & lf & rt)
    ys, xs = np.where(edge)
    # 图B系预览
    preview_b[ys, xs] = sc
    # 底图系预览（映射）
    lons = LON0 + (xs / OW) * (LON1 - LON0)
    lats = LAT0 + (ys / OH) * (LAT1 - LAT0)
    bxs = ((lons - 75.0) / (140.0 - 75.0) * BW).astype(np.int32)
    bys = ((55.0 - lats) / (55.0 - 15.0) * BH).astype(np.int32)
    good = (bxs >= 0) & (bxs < BW) & (bys >= 0) & (bys < BH)
    for x, y in zip(bxs[good], bys[good]):
        dr.point((int(x), int(y)), fill=tuple(int(v) for v in sc))
    states_out[f"state{i}"] = {"color": list(sc), "area": area,
                               "n_edge": int(len(xs)),
                               "pts_b": np.stack([xs, ys], axis=1)[::max(1, len(xs)//3000)].tolist()}
    print(f"  州{i} RGB{sc}: 面积 {area} ({100*area/(OW*OH):.2f}%), 边缘 {len(xs)}")

result = {"src": "全览-郡级.png", "size": [OW, OH],
          "assumed_range": [LON0, LON1, LAT0, LAT1],
          "state_colors": [list(c) for c in state_colors],
          "states": states_out}
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False)

Image.fromarray(preview_b).resize((1986, 1403)).save(PREVIEW_B)
preview_base.resize((1986, 1403)).save(PREVIEW_BASE)
print(f"\n图B预览: {PREVIEW_B}\n底图预览: {PREVIEW_BASE}")
