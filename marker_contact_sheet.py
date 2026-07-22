"""
生成并州地图所有白圈标记的「放大裁剪对照表」——每个标记单独裁剪+放大，
附带坐标和编号，用于人工/视觉确认标记→城市对应关系。
"""
import os, numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(HERE, '汉末十三州地图范例', '并州.png')
OUTDIR = os.path.join(HERE, 'bingzhou_step1_v7c')
os.makedirs(OUTDIR, exist_ok=True)

# ── 用圆环检测法找所有白圈标记 ──
pil_img = Image.open(IMG_PATH).convert('RGB')
img = np.array(pil_img).astype(np.float32)
H, W = img.shape[:2]

# 白圈检测：高亮度环形像素(内黑外红或内灰外红)
bright = ((img[:,:,0]>200)&(img[:,:,1]>200)&(img[:,:,2]>200)).astype(np.uint8)
grayish = ((img[:,:,0].astype(int)+img[:,:,1].astype(int)+img[:,:,2].astype(int))/3 > 180).astype(np.uint8)

from scipy import ndimage
labeled, n_features = ndimage.label(bright)
print(f'亮区连通域: {n_features}')

# 找每个亮区的中心作为候选
centers = []
for i in range(1, n_features+1):
    ys, xs = np.where(labeled == i)
    if 5 < len(xs) < 500:  # 排除过大(背景)过小(噪点)
        cy, cx = int(np.mean(ys)), int(np.mean(xs))
        centers.append((cx, cy, len(xs)))

print(f'候选中心: {len(centers)}')

# 过滤：周围有红色(排除邻州区域的白点)
red_markers = []
for cx, cy, area in centers:
    # 检查 r=15 范围内红色占比
    y0=max(0,cy-20); y1=min(H,cy+21); x0=max(0,cx-20); x1=min(W,cx+21)
    patch = img[y0:y1, x0:x1]
    if patch.size == 0: continue
    r,g,b = patch[:,:,0], patch[:,:,1], patch[:,:,2]
    red_frac = ((r>150)&(g<140)&(b<140)).mean()
    if red_frac > 0.15:  # 周围有足够红色=在并州区域内
        red_markers.append((cx, cy))

print(f'红色区域内标记: {len(red_markers)}')

# 去重(太近的合并)
def dedup(pts, min_dist=30):
    out=[]
    used=set()
    for p in pts:
        dup=False
        for q in out:
            if (p[0]-q[0])**2+(p[1]-q[1])**2 < min_dist**2:
                dup=True; break
        if not dup:
            out.append(p)
    return out

markers = dedup(red_markers, 35)
print(f'去重后标记数: {len(markers)}')

# ── 生成放大裁剪对照表 ──
CROP_R = 80   # 裁剪半径(px)
ZOOM = 3      # 放大倍数
CELL_W = CROP_R*2*ZOOM
CELL_H = CROP_R*2*ZOOM
COLS = 5
ROWS = (len(markers) + COLS - 1) // COLS
sheet_W = COLS * CELL_W + (COLS+1)*6  # padding
sheet_H = ROWS * CELL_H + (ROWS+1)*6 + 40  # 底部留标题

sheet = Image.new('RGB', (sheet_W, sheet_H), (240, 240, 240))
draw = ImageDraw.Draw(sheet)
try:
    font_num = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 14)
    font_coord = ImageFont.truetype("C:/Windows/Fonts/simhei.ttf", 11)
except:
    font_num = ImageFont.load_default()
    font_coord = font_num

for idx, (cx, cy) in enumerate(markers):
    col = idx % COLS
    row = idx // COLS
    ox = 6 + col * (CELL_W + 6)
    oy = 6 + row * (CELL_H + 6)
    
    # 裁剪原图
    x0 = max(0, cx - CROP_R)
    y0 = max(0, cy - CROP_R)
    x1 = min(W, cx + CROP_R)
    y1 = min(H, cy + CROP_R)
    crop = pil_img.crop((x0, y0, x1, y1))
    
    # 放大
    crop_big = crop.resize((crop.width*ZOOM, crop.height*ZOOM), Image.LANCZOS)
    
    # 在放大图上画红圈标出白圈位置(也放大)
    bcx = (cx - x0) * ZOOM
    bcy = (cy - y0) * ZOOM
    draw_crop = ImageDraw.Draw(crop_big)
    draw_crop.ellipse([bcx-4*ZOOM, bcy-4*ZOOM, bcx+4*ZOOM, bcy+4*ZOOM],
                       outline='red', width=2)
    
    sheet.paste(crop_big, (ox, oy))
    
    # 标题: 编号 + 坐标
    title = f'#{idx+1} ({cx},{cy})'
    draw.text((ox+2, oy+CELL_H-22), title, fill=(200,0,0), font=font_num)

out_path = os.path.join(OUTDIR, 'marker_contact_sheet.png')
sheet.save(out_path)
print(f'[done] -> {out_path}  ({len(markers)} markers, {COLS}x{ROWS} grid)')
