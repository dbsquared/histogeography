"""
并州锚点表 v3 — 基于白圈标记的全局目视匹配。
每个锚点都精确对准图上的 ○ 白圈标记。
"""
import json, os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, 'bingzhou_step1_v7c')

# 最终修正的5个锚点 — 每个都精确对准检测到的白圈标记
ANCHORS_V3 = [
    {"name": "大同",     "px": 1612, "py": 283,  "lon": 113.300, "lat": 40.080,
     "note": "雁门郡治(#4)"},
    {"name": "太原",     "px": 1792, "py": 907,  "lon": 112.550, "lat": 37.870,
     "note": "太原郡治·晋阳(#17)"},
    {"name": "呼和浩特", "px": 1197, "py": 242,  "lon": 111.730, "lat": 40.830,
     "note": "云中郡治(#2)"},
    {"name": "延安",     "px": 1451, "py": 1204, "lon": 109.490, "lat": 36.600,
     "note": "上郡治(#21)"},
    {"name": "吕梁",     "px": 948,  "py": 802,  "lon": 111.130, "lat": 37.520,
     "note": "西河郡治·离石(#11)"},
]

# 写入
anchor_path = os.path.join(HERE, 'bingzhou_anchor_table.json')
with open(anchor_path, 'w', encoding='utf-8') as f:
    json.dump(ANCHORS_V3, f, ensure_ascii=False, indent=2)

print(f'v3 锚点表 -> {anchor_path}')
for i,a in enumerate(ANCHORS_V3):
    print(f'  {i+1}. {a["name"]:6s} ({a["px"]:4d},{a["py"]:4d})  ({a["lon"]:.3f},{a["lat"]:.3f})  {a["note"]}')

# ── 验证预览 ──
img = Image.open(os.path.join(HERE, '汉末十三州地图范例', '并州.png')).convert('RGB')
draw = ImageDraw.Draw(img)
font = ImageFont.truetype('C:/Windows/Fonts/simhei.ttf', 24)
for i,a in enumerate(ANCHORS_V3):
    x,y = a['px'], a['py']
    draw.ellipse([x-22,y-22,x+22,y+22], outline='red', width=3)
    draw.ellipse([x-6,y-6,x+6,y+6], fill='red')
    lbl = f'{i+1}.{a["name"]}'
    for dx,dy in [(-2,-2),(-2,0),(-2,2),(0,-2),(0,2),(2,-2),(2,0),(2,2)]:
        draw.text((x+25+dx,y-12+dy), lbl, fill='white', font=font)
    draw.text((x+25,y-12), lbl, fill='red', font=font)

preview = os.path.join(OUTDIR, 'anchor_v3_preview.png')
img.save(preview)
print(f'\n预览 -> {preview}')
