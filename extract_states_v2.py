# -*- coding: utf-8 -*-
"""提取13州边界 v2：按'有彩色倾向的浅色填充'聚类，改进背景判定。"""
import numpy as np
from PIL import Image
import json, os
from collections import Counter

BASE = r"E:\projects\3D地图制作\汉末十三州地图范例"
OUT_JSON = r"E:\projects\3D地图制作\legend_states.json"

LON0, LON1, LAT0, LAT1 = 75.0, 140.0, 15.0, 55.0
BW, BH = 15600, 9600

def is_state_color(c):
    r, g, b = c
    if max(c) - min(c) < 25:
        return False  # 灰/白
    if b > r + 20 and b > 150:
        return False  # 海洋
    if r < 60 and g < 60 and b < 60:
        return False  # 黑
    if r > 150 and g < 90 and b < 90:
        return False  # 红(现代)
    return True

def extract(src_name, preview_name):
    print(f"\n=== {src_name} ===")
    ov = Image.open(os.path.join(BASE, src_name)).convert("RGB")
    OW, OH = ov.size
    arr = np.array(ov, dtype=np.uint8)
    flat = arr.reshape(-1, 3)
    # 候选州色
    q = (flat // 8 * 8)
    cnt = Counter(map(tuple, q.tolist()))
    cands = []
    for color, n in cnt.most_common(60):
        if is_state_color(color):
            cands.append((color, n / flat.shape[0]))
    print(f"候选彩色浅色数: {len(cands)}")
    for c, f in cands[:18]:
        print(f"  RGB{c}: {f*100:.2f}%")
    state_colors = [c for c, f in cands[:13]]
    print(f"选 {len(state_colors)} 州色")
    # 分配
    fi = flat.astype(np.int32)
    state_arr = np.full(fi.shape[0], -1, dtype=np.int16)
    for i, sc in enumerate(state_colors):
        sc = np.array(sc, dtype=np.int32)
        d = np.sum((fi - sc) ** 2, axis=1)
        state_arr[d < 1500] = i
    state_map = state_arr.reshape(OH, OW)
    # 边缘
    states_out = {}
    preview = np.full((OH, OW, 3), 255, dtype=np.uint8)
    for i, sc in enumerate(state_colors):
        mask = (state_map == i)
        up = np.roll(mask, 1, 0); dn = np.roll(mask, -1, 0)
        lf = np.roll(mask, 1, 1); rt = np.roll(mask, -1, 1)
        edge = mask & ~(up & dn & lf & rt)
        ys, xs = np.where(edge)
        pts = np.stack([(xs / OW) * BW, (ys / OH) * BH], axis=1).astype(np.int32)
        states_out[i] = {"color": list(sc), "area": int(mask.sum()),
                         "n_edge": int(len(pts)),
                         "pts": pts[::max(1, len(pts)//4000)].tolist()}
        preview[ys, xs] = sc
    result = {"src": src_name, "size": [OW, OH],
              "state_colors": [list(c) for c in state_colors],
              "states": {str(k): v for k, v in states_out.items()}}
    Image.fromarray(preview).resize((1986, 1403)).save(preview_name)
    print(f"预览: {preview_name}")
    return result

r1 = extract("全览-郡治.png", r"E:\projects\3D地图制作\rendered\legend_extract_a.png")
r2 = extract("全览-郡级.png", r"E:\projects\3D地图制作\rendered\legend_extract_b.png")
with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump({"a": r1, "b": r2}, f, ensure_ascii=False)
print("\n保存 legend_states.json")
