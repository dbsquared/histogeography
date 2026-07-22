"""
并州 Step 2 锚点表生成 + 可视化验证
用用户提供的 5 个地标(大同/太原/呼和浩特/延安/吕梁)的真实经纬度 + 图上估测像素,
生成 bingzhou_anchor_table.json,并在并州图上标注锚点供人工校验。
"""
import json, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, '汉末十三州地图范例', '并州.png')
OUTDIR = os.path.join(HERE, 'bingzhou_step1_v7c')
os.makedirs(OUTDIR, exist_ok=True)

# ── 用户提供的 5 个地标: 名称, (图像像素x,y), (真实经度, 纬度), 对应图中可见特征 ──
ANCHORS_RAW = [
    {"name": "大同",     "px": 1528, "py": 495,  "lon": 113.300, "lat": 40.080, "note": "雁门郡治附近"},
    {"name": "太原",     "px": 1360, "py": 998,  "lon": 112.550, "lat": 37.870, "note": "太原郡治"},
    {"name": "呼和浩特", "px": 1278, "py": 278,  "lon": 111.730, "lat": 40.830, "note": "云中郡治"},
    {"name": "延安",     "px": 868,  "py": 1135, "lon": 109.490, "lat": 36.600, "note": "上郡治"},
    {"name": "吕梁",     "px": 928,  "py": 852,  "lon": 111.130, "lat": 37.520, "note": "西河郡治"},
]

# ── 输出 JSON 锚点表 ──
anchor_table = []
for a in ANCHORS_RAW:
    anchor_table.append({
        "name": a["name"],
        "type": "city",
        "lon": round(a["lon"], 4),
        "lat": round(a["lat"], 4),
        "px": a["px"],
        "py": a["py"],
        "note": a.get("note", ""),
    })

json_path = os.path.join(HERE, 'bingzhou_anchor_table.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(anchor_table, f, ensure_ascii=False, indent=2)
print(f'[ok] 锚点表已写入 {json_path} ({len(anchor_table)} 个锚点)')

# ── 在并州原图上可视化标注锚点 ──
img = Image.open(SAMPLE).convert('RGB')
draw = ImageDraw.Draw(img)
W, H = img.size  # 2020 x 1418

# 尝试加载字体
font_path = 'C:/Windows/Fonts/simhei.ttf'
try:
    font = ImageFont.truetype(font_path, 28)
    font_sm = ImageFont.truetype(font_path, 22)
except Exception:
    font = font_sm = ImageFont.load_default()

for i, a in enumerate(ANCHORS_RAW):
    x, y = a['px'], a['py']
    # 红色圆圈标记
    r = 12
    draw.ellipse([x-r, y-r, x+r, y+r], outline='red', width=3)
    draw.ellipse([x-3, y-3, x+3, y+3], fill='red')
    
    # 标签: 编号+名称+经纬度
    label = f"{i+1}.{a['name']} ({a['lon']},{a['lat']})"
    # 标签背景偏移(避免互相遮挡)
    ox = 18 if x < W//2 else -(len(label)*12 + 5)
    oy = -28 if y > H*0.25 else 10
    
    # 描边文字(白边保证可读性)
    for dx, dy in [(-2,-2),(-2,0),(-2,2),(0,-2),(0,2),(2,-2),(2,0),(2,2)]:
        draw.text((x+ox+dx, y+oy+dy), label, fill='white', font=font_sm)
    draw.text((x+ox, y+oy), label, fill='#FF0000', font=font_sm)

preview_path = os.path.join(OUTDIR, 'anchor_check_preview.png')
img.save(preview_path)
print(f'[ok] 锚点预览图 -> {preview_path}')

# ── 打印锚点表摘要 ──
print(f'\n{"="*55}')
print(f'并州锚点表 (基于并州.png {W}x{H})')
print(f'{"="*55}')
print(f'{"#":>2}  {"名称":6s}  {"像素(px,py)":>14s}  {"经纬度":>16s}  备注')
print(f'{"-"*55}')
for i, a in enumerate(anchor_table):
    print(f'{i+1:>2}  {a["name"]:6s}  ({a["px"]:>4d},{a["py"]:>4d})   ({a["lon"]:>7.3f},{a["lat"]:>7.3f})  {a.get("note","")}')
print(f'\n请检查 preview 图中红圈是否对准各郡治白点。')
print(f'若位置有偏差,修改本脚本 ANCHORS_RAW 中的 px/py 后重跑即可。')
