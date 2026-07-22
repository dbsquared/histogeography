# -*- coding: utf-8 -*-
"""分析汉末十三州图例：提取13州填充色映射 + 全览图州色聚类"""
import numpy as np
from PIL import Image
import json, os, glob

BASE = r"E:\projects\3D地图制作\汉末十三州地图范例"
OUT = r"E:\projects\3D地图制作\legend_analysis.json"

STATES = ["司隶","冀州","兖州","青州","徐州","豫州","扬州","荆州",
          "益州","凉州","并州","幽州","交州"]

def quantize(arr, step=12):
    return (arr // step * step).astype(np.int32)

def is_ocean(c):
    r,g,b = c
    return b > r + 25 and b > 150 and g > 150

def is_white(c):
    return all(v > 235 for v in c)

def is_black(c):
    return all(v < 45 for v in c)

# ── 1. 全览图候选州色聚类 ──
print("分析全览-郡治.png ...")
ov = Image.open(os.path.join(BASE, "全览-郡治.png")).convert("RGB")
ov_s = ov.resize((1986, 1403))
a = np.array(ov_s)
q = quantize(a, 12).reshape(-1, 3)
from collections import Counter
cnt = Counter(map(tuple, q))
candidates = []
for color, n in cnt.most_common(60):
    if is_ocean(color) or is_white(color) or is_black(color):
        continue
    frac = n / len(q)
    if frac > 0.002:  # >0.2%
        candidates.append((list(map(int, color)), round(frac, 4)))
print(f"全览图候选州色数: {len(candidates)}")
for c, f in candidates:
    print(f"  RGB{tuple(c)}: {f*100:.2f}%")

# ── 2. 分州图主色 → 匹配候选州色 ──
def nearest_candidate(color, cands):
    best, bd = None, 1e9
    for cc, _ in cands:
        d = sum((x-y)**2 for x, y in zip(color, cc))
        if d < bd:
            bd, best = d, cc
    return best, bd

mapping = {}
for st in STATES:
    fp = os.path.join(BASE, st + ".png")
    if not os.path.exists(fp):
        print(f"  缺失 {st}.png")
        continue
    im = Image.open(fp).convert("RGB")
    arr = np.array(im)
    qq = quantize(arr, 12).reshape(-1, 3)
    c2 = Counter(map(tuple, qq))
    # 取最大的非海洋/白/黑/红(边界线可能是红)色
    bg = None
    for color, n in c2.most_common(40):
        if is_ocean(color) or is_white(color) or is_black(color):
            continue
        # 排除纯红(边界线/标注): r高g/b低
        if color[0] > 150 and color[1] < 90 and color[2] < 90:
            continue
        bg = list(map(int, color))
        break
    match, dist = nearest_candidate(bg, candidates) if bg else (None, 0)
    mapping[st] = {"local_bg": bg, "overview_match": match, "match_dist": int(dist)}
    print(f"{st}: 本地主色 RGB{tuple(bg)} -> 全览匹配 RGB{tuple(match)} (dist={dist})")

# ── 3. 全览图地理范围推测：检查四角像素 ──
corners = {
    "TL": ov.getpixel((0, 0)),
    "TR": ov.getpixel((ov.width - 1, 0)),
    "BL": ov.getpixel((0, ov.height - 1)),
    "BR": ov.getpixel((ov.width - 1, ov.height - 1)),
}
print("全览图四角像素:", corners)

result = {
    "overview_candidates": candidates,
    "state_color_mapping": mapping,
    "overview_corners": {k: list(v) for k, v in corners.items()},
    "overview_size": list(ov.size),
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print(f"\n已保存分析到 {OUT}")
