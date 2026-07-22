"""
根据 ring_detect 结果,手动将5个地标匹配到最近的白圈标记。
基于地图布局:
  大同=雁门郡(东北), 太原=晋阳/太原郡(中东), 呼和浩特=云中郡(北),
  延安=上郡(南), 吕梁=西河郡/离石(中西)
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = os.path.join(HERE, 'bingzhou_step1_v7c')

# 从 detect_bingzhou_dots.py 的输出中提取的32个标记点坐标
MARKERS = [
    (928,220),(1197,242),(463,269),(1612,283),(1941,298),(1375,364),
    (1988,478),(1432,530),(1821,691),(2015,768),(948,802),(306,821),
    (1725,842),(1393,854),(1918,892),(1167,906),(1792,907),(1954,1045),
    (1730,1104),(1719,1169),(1451,1204),(2008,1276),(1818,1308),(521,1323),
    (1830,1369),(1794,1376),(1642,1402),(1166,1401),(1680,1402),(1692,1403),
]

# ── 基于图像目视的精确匹配 ──
# 每个地标的正确白圈位置(从 markers_ring_detect.png 目视确认)
ANCHORS_CORRECTED = [
    {"name": "大同",     "px": 1197, "py": 242,  "lon": 113.300, "lat": 40.080,
     "note": "雁门郡治附近(#2)", "marker_id": 2},
    {"name": "太原",     "px": 1730, "py": 1104, "lon": 112.550, "lat": 37.870,
     "note": "晋阳/太原郡治(#19)", "marker_id": 19},
    {"name": "呼和浩特", "px": 1375, "py": 364,  "lon": 111.730, "lat": 40.830,
     "note": "云中郡治(#6)", "marker_id": 6},
    {"name": "延安",     "px": 1451, "py": 1204, "lon": 109.490, "lat": 36.600,
     "note": "上郡治(#21)", "marker_id": 21},
    {"name": "吕梁",     "px": 1393, "py": 854,  "lon": 111.130, "lat": 37.520,
     "note": "西河郡/离石(#14)", "marker_id": 14},
]

# 写入锚点表
anchor_path = os.path.join(HERE, 'bingzhou_anchor_table.json')
with open(anchor_path, 'w', encoding='utf-8') as f:
    json.dump(ANCHORS_CORRECTED, f, ensure_ascii=False, indent=2)

print(f'修正后锚点表 -> {anchor_path}')
print(f'\n{"="*60}')
print(f'{"#":>2} {"名称":6s} {"像素(px,py)":>12s} {"经纬度":>16s}  备注')
print(f'{"-"*60}')
for i,a in enumerate(ANCHORS_CORRECTED):
    print(f'{i+1:>2} {a["name"]:6s} ({a["px"]:4d},{a["py"]:4d})  ({a["lon"]:>7.3f},{a["lat"]:>7.3f})  {a["note"]}')

# ── 验证: 在原图上标注新锚点 ──
from PIL import Image, ImageDraw, ImageFont
img = Image.open(os.path.join(HERE, '汉末十三州地图范例', '并州.png')).convert('RGB')
draw = ImageDraw.Draw(img)
font = ImageFont.truetype('C:/Windows/Fonts/simhei.ttf', 22)
for i,a in enumerate(ANCHORS_CORRECTED):
    x,y = a['px'], a['py']
    draw.ellipse([x-18,y-18,x+18,y+18], outline='red', width=3)
    draw.ellipse([x-5,y-5,x+5,y+5], fill='red')
    label = f'{i+1}.{a["name"]}'
    draw.text((x+22,y-10), label, fill='#FF0000', font=font)
    for dx,dy in [(-2,-2),(-2,0),(-2,2),(0,-2),(0,2),(2,-2),(2,0),(2,2)]:
        draw.text((x+22+dx,y-10+dy), label, fill='white', font=font)

preview = os.path.join(OUTDIR, 'anchor_corrected_preview.png')
img.save(preview)
print(f'\n预览图 -> {preview}')
