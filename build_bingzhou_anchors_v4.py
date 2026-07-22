"""生成并州锚点v4预览图——基于标签文字的正确匹配"""
import os, json
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, '汉末十三州地图范例', '并州.png')
OUT = os.path.join(HERE, 'bingzhou_step1_v7c', 'anchor_v4_preview.png')

anchors = json.load(open(os.path.join(HERE, 'bingzhou_anchor_table.json'), encoding='utf-8'))
img = Image.open(IMG).convert('RGB')
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 18)
except:
    font = ImageFont.load_default()

for i, a in enumerate(anchors):
    x, y = a['px'], a['py']
    # 红圈
    draw.ellipse([x-18, y-18, x+18, y+18], outline='red', width=3)
    # 编号+名称
    label = f"{i+1}.{a['name']}({a['note']})"
    draw.text((x+22, y-10), label, fill='red', font=font)

img.save(OUT)
print(f'[done] -> {OUT}')
for a in anchors:
    print(f"  {a['name']:6s} ({a['px']:>4},{a['py']:>4}) lon{a['lon']:.2f} lat{a['lat']:.2f} [{a['note']}]")
