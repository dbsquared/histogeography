# -*- coding: utf-8 -*-
"""把提取的13州边界(图B系)映射到地形底图，生成对齐校验预览。
底图 china_full_v3.png 缩小到 (1986,1403) 叠加州界。
"""
import json, numpy as np
from PIL import Image, ImageDraw

d = json.load(open(r"E:\projects\3D地图制作\legend_states_b.json", encoding="utf-8"))
BW_b, BH_b = d["size"]  # 图B像素尺寸
B_LON0, B_LON1, B_LAT0, B_LAT1 = d["assumed_range"]
LON0, LON1, LAT0, LAT1 = 75.0, 140.0, 15.0, 55.0
BW, BH = 15600, 9600
W, H = 1986, 1403

print("加载底图并缩小...")
base = Image.open(r"E:\projects\3D地图制作\china_full_v3.png").convert("RGB").resize((W, H))
draw = ImageDraw.Draw(base)

for k in d["states"]:
    pts = d["states"][k]["pts_b"]
    for px, py in pts:
        lon = B_LON0 + (px / BW_b) * (B_LON1 - B_LON0)
        lat = B_LAT0 + (py / BH_b) * (B_LAT1 - B_LAT0)
        bx = (lon - LON0) / (LON1 - LON0) * BW
        by = (LAT1 - lat) / (LAT1 - LAT0) * BH
        sx = int(bx / BW * W); sy = int(by / BH * H)
        if 0 <= sx < W and 0 <= sy < H:
            draw.point((sx, sy), fill=(20, 20, 20))
base.save(r"E:\projects\3D地图制作\rendered\legend_on_terrain_preview.png")
print("已保存 rendered/legend_on_terrain_preview.png")
