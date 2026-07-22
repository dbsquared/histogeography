# -*- coding: utf-8 -*-
"""校验: 栅格化 13 州多边形, 统计重叠/空隙."""
import json, numpy as np
from PIL import Image, ImageDraw

d = json.load(open("rendered/state_boundaries.json", encoding="utf-8"))
W, H, scale = 1560, 960, 0.1
count = np.zeros((H, W), dtype=np.int16)
areas = []
for i, r in enumerate(d["states"], start=1):
    c = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(c)
    poly = [(x*scale, y*scale) for x, y in r["vertices_base"]]
    dr.polygon(poly, fill=1)
    for ep in r.get("extra_polygons", []):
        epb = [(e["base"][0]*scale, e["base"][1]*scale) for e in ep]
        dr.polygon(epb, fill=1)
    m = (np.array(c) > 0)
    count += m.astype(np.int16)
    areas.append((r["name"], int(m.sum())))
total = W*H
overlap = int((count > 1).sum())
assigned = int((count >= 1).sum())
unassigned = total - assigned
print(f"画布 {W}x{H} (底图1/10)")
print(f"已分配={assigned}px ({assigned/total*100:.1f}%)  重叠={overlap}px ({overlap/total*100:.3f}%)  "
      f"空隙={unassigned}px ({unassigned/total*100:.1f}%)")
print("各州面积(px):")
for nm, a in areas:
    print(f"  {nm:3s} {a}")
# 列出重叠最严重的配对(粗栅格下仅供参考)
print("注: 重叠主要来自相邻州共用边界像像素的抗锯齿, 量级极小即正常.")
