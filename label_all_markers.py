"""
最终方案: 在并州原图上标注所有32个检测到的白圈标记,
每个带编号+精确像素坐标,一次性看清全局布局。
同时标注5个目标城市的预期方位提示。
"""
import os, json
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(HERE, '汉末十三州地图范例', '并州.png')
OUTDIR = os.path.join(HERE, 'bingzhou_step1_v7c')

img = Image.open(IMG_PATH).convert('RGB')
draw = ImageDraw.Draw(img)
font_id = ImageFont.truetype('C:/Windows/Fonts/simhei.ttf', 24)
font_coord = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 16)
font_hint = ImageFont.truetype('C:/Windows/Fonts/simhei.ttf', 36)

# 32个检测到的标记点(从 ring detect 结果)
MARKERS = [
    (928,220),(1197,242),(463,269),(1612,283),(1941,298),(1375,364),
    (1988,478),(1432,530),(1821,691),(2015,768),(948,802),(306,821),
    (1725,842),(1393,854),(1918,892),(1167,906),(1792,907),(1954,1045),
    (1730,1104),(1719,1169),(1451,1204),(2008,1276),(1818,1308),(521,1323),
    (1830,1369),(1794,1376),(1642,1402),(1166,1401),(1680,1402),(1692,1403),
]

# ── 标注所有标记 ──
for i, (mx, my) in enumerate(MARKERS):
    # 绿色圆圈
    draw.ellipse([mx-20,my-20,mx+20,my+20], outline='#00FF00', width=3)
    draw.ellipse([mx-5,my-5,mx+5,my+5], fill='#00FF00')
    
    # 编号(左上)
    draw.text((mx-22,my-28), str(i+1), fill='#00FF00', font=font_id)
    # 描边保证可读性
    for dx,dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
        draw.text((mx-22+dx,my-28+dy), str(i+1), fill='black', font=font_id)
    draw.text((mx-22,my-28), str(i+1), fill='#00FF00', font=font_id)

    # 坐标文字(右下,小字)
    coord = f'({mx},{my})'
    draw.text((mx+15,my+5), coord, fill='yellow', font=font_coord)

# ── 右下角添加图例 ──
legend_x, legend_y = 50, img.height - 200
draw.text((legend_x, legend_y), '=== 目标地标(待匹配编号) ===', fill='#FFAA00', font=font_hint)
hints = [
    '① 大同 → 雁门郡(东北部)',
    '② 太原 → 晋阳/太原郡(中东部)',  
    '③ 呼和浩特 → 云中郡(北部)',
    '④ 延安 → 上郡(南部)',
    '⑤ 吕梁 → 西河郡/离石(西部)',
]
for j, h in enumerate(hints):
    draw.text((legend_x, legend_y+45+j*38), h, fill='white', font=font_id)

out = os.path.join(OUTDIR, 'all_markers_labeled.png')
img.save(out)
print(f'全图标记 -> {out}')
print(f'\n共 {len(MARKERS)} 个标记,请告诉我每个地标对应哪个编号。')
