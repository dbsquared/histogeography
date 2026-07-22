"""
坐标↔像素 映射验证可视化
========================
生成两张图, 把"经纬度 ↔ 像素"的映射直观地画出来:

图1 (mapping_graticule.png): 底图经纬度网格 — 等经纬度(Plate Carree) 1:1 线性映射
图2 (mapping_gcp.png):       GCP控制点校准 — 13个古城坐标经仿射变换落到底图的位置 + 残差
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import json, os

Image.MAX_IMAGE_PIXELS = None
BASE_DIR = r'E:\projects\3D地图制作'
RENDERED = os.path.join(BASE_DIR, 'rendered')

# ── 底图映射常量 (geo_mapping.py) ──
BASE_W, BASE_H = 15600, 9600
LON_MIN, LON_MAX = 75.0, 140.0
LAT_MAX, LAT_MIN = 55.0, 15.0
LON_SPAN = LON_MAX - LON_MIN
LAT_SPAN = LAT_MIN - LAT_MAX

def l2p(lon, lat):
    """WGS84 → 底图像素"""
    px = (lon - LON_MIN) / LON_SPAN * BASE_W
    py = (lat - LAT_MAX) / LAT_SPAN * BASE_H
    return px, py

# 字体
try:
    F = ImageFont.truetype("msyh.ttc", 30)
    FB = ImageFont.truetype("msyh.ttc", 40)
except:
    F = FB = ImageFont.load_default()

# ── 加载底图(降采样) ──
print('加载底图...')
base = Image.open(os.path.join(BASE_DIR, 'china_full_v3.png')).convert('RGB')
VW = 2600
scale = VW / BASE_W
VH = int(BASE_H * scale)
vbase = base.resize((VW, VH), Image.LANCZOS)
print(f'  预览尺寸: {VW}x{VH} (scale={scale:.4f})')

def to_view(px, py):
    return px * scale, py * scale

# ════════════════════════════════════════════════
# 图1: 经纬度网格 (证明 1:1 线性映射)
# ════════════════════════════════════════════════
print('\n=== 图1: 经纬度网格 ===')
img1 = vbase.copy()
d1 = ImageDraw.Draw(img1)

# 每 5° 一条线
for lon in range(int(LON_MIN), int(LON_MAX)+1, 5):
    px, _ = l2p(lon, 0)
    vx = px * scale
    d1.line([(vx, 0), (vx, VH)], fill=(255, 255, 255, 140), width=1)
    d1.text((vx+4, 8), f'{lon}°E', font=F, fill=(255,255,255))

for lat in range(int(LAT_MIN), int(LAT_MAX)+1, 5):
    _, py = l2p(0, lat)
    vy = py * scale
    d1.line([(0, vy), (VW, vy)], fill=(255, 255, 255, 140), width=1)
    d1.text((4, vy+4), f'{lat}°N', font=F, fill=(255,255,255))

# 四角标注
corners = [('(0,0)', 0, 0), ('(15600,0)', BASE_W, 0),
           ('(0,9600)', 0, BASE_H), ('(15600,9600)', BASE_W, BASE_H)]
for label, px, py in corners:
    lon, lat = LON_MIN + px/BASE_W*LON_SPAN, LAT_MAX + py/BASE_H*LAT_SPAN
    vx, vy = to_view(px, py)
    d1.ellipse([vx-5, vy-5, vx+5, vy+5], fill=(255, 80, 80))
    d1.text((vx+8, vy-18), f'{label}→({lon:.0f},{lat:.0f})', font=F, fill=(255,120,120))

d1.text((VW//2-180, VH-40), '底图: 等经纬度(Plate Carree) 1:1 线性映射', font=F, fill=(255,255,255))
img1.save(os.path.join(RENDERED, 'mapping_graticule.png'))
print('  已保存 mapping_graticule.png')

# ════════════════════════════════════════════════
# 图2: GCP控制点校准验证
# ════════════════════════════════════════════════
print('\n=== 图2: GCP控制点 ===')
with open(os.path.join(BASE_DIR, 'gcp_calibration.json'), encoding='utf-8') as f:
    cal = json.load(f)

# 仿射变换参数 (郡治图 px → WGS84)
a = cal['transform_forward']['lon']['a']; b = cal['transform_forward']['lon']['b']; c = cal['transform_forward']['lon']['c']
d = cal['transform_forward']['lat']['d']; e = cal['transform_forward']['lat']['e']; f = cal['transform_forward']['lat']['f']

# 反向: WGS84 → 郡治图像素 (用于残差回算)
inv = cal['transform_inverse_zhi']
Ai, Bi, Ci = inv['px_A'], inv['px_B'], inv['px_C']
Di, Ei, Fi = inv['py_D'], inv['py_E'], inv['py_F']

img2 = vbase.copy()
d2 = ImageDraw.Draw(img2)

# 在底图上标出每个GCP的真实WGS84位置
for g in cal['gcps']:
    lon, lat = g['lon'], g['lat']
    # WGS84 → 底图像素
    bpx, bpy = l2p(lon, lat)
    vx, vy = bpx * scale, bpy * scale
    # 残差: 用反向变换算回郡治图像素, 与记录像素比
    zx = Ai*lon + Bi*lat + Ci
    zy = Di*lon + Ei*lat + Fi
    err = ((zx - g['px'])**2 + (zy - g['py'])**2) ** 0.5
    col = (255, 220, 60) if err < 80 else (255, 120, 30)
    d2.ellipse([vx-7, vy-7, vx+7, vy+7], outline=col, width=3)
    # 标签
    txt = f"{g['name']}\n({lon:.2f}E,{lat:.2f}N)\npix({int(bpx)},{int(bpy)})"
    d2.text((vx+10, vy-24), g['name'], font=F, fill=col)
    d2.text((vx+10, vy+0), f"{lon:.2f}E,{lat:.2f}N", font=F, fill=(255,255,255))
    d2.text((vx+10, vy+22), f"res={err:.0f}px", font=F, fill=col)

# 图例
d2.text((20, 20), '黄色圈=残差<80px  橙色圈=残差≥80px', font=F, fill=(255,255,255))
d2.text((20, VH-30), f"GCP={len(cal['gcps'])}个  最大残差={cal['max_residual_px']:.0f}px", font=F, fill=(255,255,255))

img2.save(os.path.join(RENDERED, 'mapping_gcp.png'))
print('  已保存 mapping_gcp.png')

# ════════════════════════════════════════════════
# 文字报告
# ════════════════════════════════════════════════
print('\n=== 映射公式 ===')
print(f'[底图] 像素(px,py) → 经纬度:')
print(f'  lon = 75.0 + (px/15600)*65.0')
print(f'  lat = 55.0 + (py/9600)*(-40.0)')
print(f'  反推: px = (lon-75)/65*15600,  py = (lat-55)/(-40)*9600')
print(f'  分辨率 ≈ {LON_SPAN/BASE_W*111320:.0f} m/px (水平)')
print()
print(f'[GCP仿射] 郡治图像素(px,py) → 经纬度:')
print(f'  lon = {a:.6f}*px {b:+.6f}*py {c:+.4f}')
print(f'  lat = {d:.6f}*px {e:+.6f}*py {f:+.4f}')
print(f'  最大残差: {cal["max_residual_px"]:.1f} px (占图宽 {100*cal["max_residual_px"]/9933:.2f}%)')
