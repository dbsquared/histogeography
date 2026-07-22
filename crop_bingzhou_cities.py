"""
精确定位并州.png上5个地标的白点位置。
方法: 裁剪各城市名附近区域,输出局部放大图供确认。
基于之前读图的目视估测,先粗裁再微调。
"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, '汉末十三州地图范例', '并州.png')
OUTDIR = os.path.join(HERE, 'bingzhou_step1_v7c')

img = Image.open(IMG).convert('RGB')
W, H = img.size  # 2020 x 1418

# 基于图像目视,每个地标附近的大致范围(x,y为裁剪中心)
# 这些是初步估计,需要通过看裁剪图来精确校正
REGIONS = {
    '大同':     {'center': (1530, 480),  'size': 200},   # 东北部 雁门郡
    '太原':     {'center': (1350, 950),  'size': 220},   # 中部偏东 太原郡/晋阳
    '呼和浩特':{'center': (1280, 260),  'size': 200},   # 北部 云中郡
    '延安':     {'center': (880, 1100),  'size': 220},   # 南部 上郡
    '吕梁':     {'center': (940, 830),   'size': 220},   # 西部 西河郡
}

# 裁剪+标注
for name, cfg in REGIONS.items():
    cx, cy = cfg['center']
    s = cfg['size'] // 2
    box = (cx-s, cy-s, cx+s, cy+s)
    # 不越界
    box = tuple(max(0, min(dim, b)) for b, dim in zip(box, [0,0,W,H]*2))
    
    crop = img.crop(box)
    d = ImageDraw.Draw(crop)
    # 在裁剪图中心画十字准星帮助定位
    ccx, ccy = s, s
    d.line([(ccx-30,ccy),(ccx+30,ccy)], fill='red', width=1)
    d.line([(ccx,ccy-30),(ccx,ccy+30)], fill='red', width=1)
    d.ellipse([ccx-6,ccy-6,ccx+6,ccy+6], outline='red', width=2)
    
    out_path = os.path.join(OUTDIR, f'crop_{name}.png')
    crop.save(out_path)
    print(f'{name}: center=({cx},{cy}) -> {out_path} (crop size={box[2]-box[0]}x{box[3]-box[1]})')
