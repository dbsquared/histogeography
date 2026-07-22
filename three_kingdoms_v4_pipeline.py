"""
汉末十三州图层生成管线 v4 — 基于GCP校准的仿射变换方法
==========================================================

Step 1: 从示例总览图提取GCP控制点 (像素坐标 ↔ WGS84经纬度)
Step 2: 最小二乘法解算仿射变换 (6参数: lon=ax+by+c, lat=dx+ey+f)  
Step 3: 将全览-郡级图的每个州域像素映射到SRTM底图上 (无缝拼接!)
Step 4: 叠加城市标记、州界线、标签 (无白底描边)
Step 5: 输出合成图 / 透明图层 / 预览

数据源:
  - 底图: china_full_v3.png (15600x9600, 经度75-140E, 纬度15-55N)
  - 州色图: 汉末十三州地图范例/全览-郡级.png (2020x1418)
  - 细节图: 汉末十三州地图范例/全览-郡治.png (9933x7015, 用于GCP校准)
  - 考据: 《汉书·地理志》《后汉书·郡国志》+ 谭其骧《中国历史地图集》
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import json, os, sys

# 解除PIL大图限制 (底图15600x9600超出默认89M像素)
Image.MAX_IMAGE_PIXELS = None

# 提前导入scipy
from scipy.ndimage import map_coordinates

# ── 路径配置 ──
BASE_DIR = r'E:\projects\3D地图制作'
LEGEND_DIR = os.path.join(BASE_DIR, r'汉末十三州地图范例')
RENDERED = os.path.join(BASE_DIR, 'rendered')
os.makedirs(RENDERED, exist_ok=True)

# ── Step 1: GCP 控制点表 ──
# 从全览-郡治图(9933x7015)上目视识别的城市位置 → WGS84
# 所有坐标来自谭其骧《中国历史地图集》第二册东汉图组
GCP_DATA = [
    # (名称,           郡治图px, 郡治图py, WGS84经度, WGS84纬度, 置信度)
    ('武威/姑臧',      2920,       1910,     102.63,    37.93,   '高'),   # 凉州刺史部
    ('长安/西安',      4450,       2822,     108.94,    34.34,   '高'),   # 司隶京兆尹
    ('成都',           3380,       3980,     104.07,    30.67,   '高'),   # 益州蜀郡
    ('弘农',           4970,       2660,     110.90,    34.52,   '中'),   # 司隶弘农郡
    ('安邑',           5070,       2560,     111.20,    35.15,   '中'),   # 司隶河东郡
    ('洛阳',           5320,       2720,     112.45,    34.62,   '高'),   # 司隶河南尹
    ('晋阳/太原',      5320,       1780,     112.55,    37.87,   '高'),   # 并州太原郡
    ('长子',           5380,       2220,     112.88,    36.12,   '中'),   # 并州上党郡
    ('宛/南阳',        5120,       3370,     112.53,    33.00,   '中'),   # 荆州南阳郡
    ('襄阳',           5280,       3500,     112.13,    32.02,   '高'),   # 荆州南郡/荆州治
    ('邺(近似)',       5950,       2250,     115.43,    36.35,   '低'),   # 冀州魏郡(待精调)
    ('蓟/蓟县',        6250,       1180,     116.40,    39.90,   '高'),   # 幽州广阳郡
    ('临淄(近似)',     6700,       2050,     118.03,    36.82,   '低'),   # 青州齐国(待精调)
    ('寿春(近似)',     6280,       3180,     116.78,    32.56,   '低'),   # 扬州九江郡(待精调)
    ('建业/南京',      6810,       3350,     118.78,    32.06,   '高'),   # 扬州丹阳郡
    ('番禺/广州',      5580,       6000,     113.26,    23.13,   '高'),   # 交州南海郡
]

# 只用置信度高/中的点参与拟合
GCPS = [(n, px, py, lon, lat) for n, px, py, lon, lat, conf in GCP_DATA 
        if conf in ('高', '中')]

print(f'=== GCP控制点 ({len(GCPS)}个用于拟合) ===')
for n, px, py, lon, lat in GCPS:
    print(f'  {n:12s}: 图像({px:>5d},{py:>5d}) <-> WGS84({lon:.2f}E,{lat:.2f}N)')

# ── Step 2: 解算仿射变换 ──
# 正向: lon = a*px + b*py + c,  lat = d*px + e*py + f
A_mat = np.array([[px, py, 1] for _, px, py, _, _ in GCPS], dtype=np.float64)
b_lon = np.array([lon for *_, _, lon, _ in GCPS])
b_lat = np.array([lat for *_, _, _, lat in GCPS])

p_lon, res_lon, rank_lon, sv_lon = np.linalg.lstsq(A_mat, b_lon, rcond=None)
p_lat, res_lat, rank_lat, sv_lat = np.linalg.lstsq(A_mat, b_lat, rcond=None)

a, b, c = p_lon
d, e, f = p_lat

print(f'\n=== 仿射变换 (全览-郡治 9933x7015 -> WGS84) ===')
print(f'  lon(px,py) = {a:.8f}*px {b:+.8f}*py {c:+.4f}')
print(f'  lat(px,py) = {d:.8f}*px {e:+.8f}*py {f:+.4f}')

# 反向: WGS84 -> 全览-郡治 像素
M = np.array([[a, b], [d, e]])
det = M[0,0]*M[1,1] - M[0,1]*M[1,0]
M_inv = np.array([[ M[1,1], -M[0,1]], [-M[1,0], M[0,0]]]) / det
Ai, Bi = M_inv[0]
Di, Ei = M_inv[1]
Ci_val = -(Ai*c + Bi*f)
Cj_val = -(Di*c + Ei*f)

def zhi_px(lon, lat):
    """WGS84经纬度 -> 全览-郡治图像像素坐标"""
    return Ai*lon + Bi*lat + Ci_val, Di*lon + Ei*lat + Cj_val

# 验证残差
print(f'\n=== GCP拟合残差 ===')
max_err = 0
for n, px_true, py_true, lon, lat in GCPS:
    pe, pye = zhi_px(lon, lat)
    err = np.sqrt((pe-px_true)**2 + (pye-py_true)**2)
    max_err = max(max_err, err)
    status = 'OK' if err < 80 else 'WARN'
    print(f'  {n:12s}: 真实({px_true:>5d},{py_true:>5d}) '
          f'拟合({pe:>7.1f},{pye:>7.1f}) 误差{err:>6.1f}px [{status}]')
print(f'  最大残差: {max_err:.1f} px (图像9933宽, 相当于{100*max_err/9933:.1f}%)')

# ── 关键: 郡治图和郡级图之间的缩放关系 ──
# 郡治图 9933x7015, 郡级图 2020x1418
# 比例约 4.915x (同一制图系统, 同一投影, 不同分辨率)
ZHI_W, ZHI_H = 9933, 7015
JI_W, JI_H   = 2020, 1418
scale_x = JI_W / ZHI_W  # 0.2034
scale_y = JI_H / ZHI_H  # 0.2022

print(f'\n=== 图像比例: 郡级/郡治 = {scale_x:.4f} x {scale_y:.4f} ===')

def zhi_to_ji(zhi_px, zhi_py):
    """郡治图像素 -> 郡级图像素"""
    return zhi_px * scale_x, zhi_py * scale_y

def wgs84_to_ji(lon, lat):
    """WGS84经纬度 -> 郡级图像素 (组合变换)"""
    zp, zpy = zhi_px(lon, lat)
    return zhi_to_ji(zp, zpy)


# ── Step 3: 州色提取与底图映射 ──
print('\n=== Step 3: 加载图像 ===')

# 加载底图
base_img = Image.open(os.path.join(BASE_DIR, 'china_full_v3.png')).convert('RGB')
BASE_W, BASE_H = base_img.size
print(f'  底图: {BASE_W}x{BASE_H}')

# 加载郡级图 (州色清晰)
ji_img = Image.open(os.path.join(LEGEND_DIR, '全览-郡级.png')).convert('RGB')
JI_IM_W, JI_IM_H = ji_img.size
print(f'  郡级图: {JI_IM_W}x{JI_IM_H}')

# 加载郡治图 (用于细节参考/城市提取)
zhi_img = Image.open(os.path.join(LEGEND_DIR, '全览-郡治.png')).convert('RGB')
ZHI_IM_W, ZHI_IM_H = zhi_img.size
print(f'  郡治图: {ZHI_IM_W}x{ZHI_IM_H}')

# 底图地理范围 (从 geo_mapping.py)
LON_MIN, LON_MAX = 75.0, 140.0
LAT_MAX, LAT_MIN = 55.0, 15.0

def base_px_to_lonlat(bx, by):
    """底图像素 -> WGS84"""
    lon = LON_MIN + (bx / BASE_W) * (LON_MAX - LON_MIN)
    lat = LAT_MAX + (by / BASE_H) * (LAT_MIN - LAT_MAX)
    return lon, lat


# 创建输出图层 (RGBA)
layer = Image.new('RGBA', (BASE_W, BASE_H), (0, 0, 0, 0))
layer_draw = ImageDraw.Draw(layer)

# 方法: 对底图的每个像素, 计算其经纬度, 映射到郡级图, 取色, 半透明叠加
# 为加速: 每 N 个像素采样一次 (步进)
STEP = 4  # 每4个像素取一个 (15600/4=3900列, 可行)

print(f'\n=== 开始Warp映射 (步进={STEP}, 输出~{BASE_W//STEP}x{BASE_H//STEP}像素) ===')

# 将郡级图转为numpy方便索引
ji_arr = np.array(ji_img)

# 预计算所有像素的映射 (向量化加速)
print('  计算映射网格...')
ys, xs = np.mgrid[0:BASE_H:STEP, 0:BASE_W:STEP]
lons = LON_MIN + (xs / BASE_W) * (LON_MAX - LON_MIN)
lats = LAT_MAX + (ys / BASE_H) * (LAT_MIN - LAT_MAX)

# WGS84 -> 郡级图像素 (向量化)
ji_xs = Ai * lons + Bi * lats + Ci_val  # 先到郡治图
ji_ys = Di * lons + Ei * lats + Cj_val
ji_xs *= scale_x  # 再到郡级图
ji_ys *= scale_y

print(f'  郡级图坐标范围: X[{ji_xs.min():.1f},{ji_xs.max():.1f}] Y[{ji_ys.min():.1f},{ji_ys.max():.1f}]')

# 双线性插值采样郡级图颜色

# ── Step 3: 分块Warp映射 (每块2000行, 控制内存) ──

# 分块处理避免OOM: 每次处理BAND_ROWS行
BAND_ROWS = 2000
layer_arr = np.zeros((BASE_H, BASE_W, 4), dtype=np.uint8)
total_state_px = 0

for band_start in range(0, BASE_H, BAND_ROWS):
    band_end = min(band_start + BAND_ROWS, BASE_H)
    band_h = band_end - band_start
    
    # 该块的坐标网格
    grid_y, grid_x = np.mgrid[band_start:band_end, 0:BASE_W]
    base_lons = LON_MIN + (grid_x / BASE_W) * (LON_MAX - LON_MIN)
    base_lats = LAT_MAX + (grid_y / BASE_H) * (LAT_MIN - LAT_MAX)
    
    # WGS84 -> 郡治图 -> 郡级图
    zhi_xs = Ai * base_lons + Bi * base_lats + Ci_val
    zhi_ys = Di * base_lons + Ei * base_lats + Cj_val
    ji_xs = zhi_xs * scale_x
    ji_ys = zhi_ys * scale_y
    
    # 双线性插值采样
    warped_band = np.zeros((band_h, BASE_W, 3), dtype=np.uint8)
    for ch in range(3):
        warped_band[:,:,ch] = map_coordinates(
            ji_arr[:,:,ch], [ji_ys, ji_xs],
            order=1, mode='constant', cval=255
        )
    
    # 写入图层数组 (非背景像素半透明)
    bg_r, bg_g, bg_b = 225, 225, 215
    is_bg = ((warped_band[:,:,0].astype(int) > bg_r) & 
             (warped_band[:,:,1].astype(int) > bg_g) & 
             (warped_band[:,:,2].astype(int) > bg_b))
    
    layer_arr[band_start:band_end, :, :3] = warped_band
    layer_arr[band_start:band_end, :, 3] = np.where(is_bg, 0, 75).astype(np.uint8)
    
    total_state_px += int((~is_bg).sum())
    pct = 100 * band_end / BASE_H
    print(f'    块 {band_start//BAND_ROWS+1}: 行{band_start}-{band_end} ({pct:.0f}%)')

print(f'  Warp完成! 州域填充: {total_state_px:,} px ({100*total_state_px/(BASE_H*BASE_W):.1f}%)')

layer = Image.fromarray(layer_arr, 'RGBA')
layer_draw = ImageDraw.Draw(layer)

# ── Step 4: 叠加城市标记 ──
print('\n=== Step 4: 叠加城市标记 ===')

# 用腾讯地图风格: 小圆圈 + 描边文字标签 (无白底!)

# 字体
try:
    font_large = ImageFont.truetype("msyh.ttc", 56)
    font_med   = ImageFont.truetype("msyh.ttc", 42)
    font_small = ImageFont.truetype("msyh.ttc", 32)
except:
    font_large = ImageFont.load_default()
    font_med   = font_large
    font_small = font_large

def draw_text_outlined(draw, x, y, text, font, fill=(0,0,0), stroke=(255,255,255), stroke_width=3):
    """描边文字 (白边黑字, 无背景)"""
    # 描边
    for dx in range(-stroke_width, stroke_width+1):
        for dy in range(-stroke_width, stroke_width+1):
            if dx*dx + dy*dy <= stroke_width*stroke_width:
                draw.text((x+dx, y+dy), text, font=font, fill=stroke)
    # 主字
    draw.text((x, y), text, font=font, fill=fill)

# 重要城池列表 (古代名 -> WGS84)
KEY_CITIES = [
    # (古代名, 现代参考, 经度, 纬度, 等级: 州治/重要/一般)
    ('洛阳',  '洛阳',   112.45, 34.62, '州治'),
    ('长安',  '西安',   108.94, 34.34, '州治'),
    ('雒县',  '广汉',   104.28, 30.99, '州治'),  # 益州治
    ('寿春',  '寿县',   116.78, 32.56, '州治'),
    ('襄阳',  '襄阳',   112.13, 32.02, '重镇'),
    ('江陵',  '荆州',   112.24, 30.04, '重镇'),
    ('邺',    '临漳',   115.43, 36.35, '重镇'),
    ('蓟',    '北京',   116.40, 39.90, '州治'),
    ('晋阳',  '太原',   112.55, 37.87, '州治'),
    ('临淄',  '淄博',   118.03, 36.82, '州治'),
    ('郯',    '郯城',   118.34, 34.71, '州治'),
    ('番禺',  '广州',   113.26, 23.13, '州治'),
    ('陇县',  '张家川', 106.21, 35.00, '州治'),  # 凉州治
    ('姑臧',  '武威',   102.63, 37.93, '重镇'),
    ('新野',  '新野',   112.05, 32.51, '一般'),
    ('宛',    '南阳',   112.53, 33.00, '重镇'),
    ('谯',    '亳州',   115.77, 33.87, '州治'),  # 豫州治
    ('建业',  '南京',   118.78, 32.06, '重镇'),
    ('成都',  '成都',   104.07, 30.67, '重镇'),
    ('汉寿',  '汉寿',   111.97, 28.97, '一般'),
    ('信都',  '冀州',   115.57, 37.59, '州治'),  # 冀州治
    ('昌邑',  '金乡',   116.26, 35.07, '州治'),  # 兖州治
    ('历阳',  '和县',   118.38, 31.62, '一般'),
    ('昌县',  '淄博',   118.37, 36.83, '州治'),  # 青州治
    ('晋阳',  '太原',   112.43, 37.74, '州治'),  # 并州治
]

print(f'  标注 {len(KEY_CITIES)} 个城池...')
city_count = 0
for name, ref, lon, lat, level in KEY_CITIES:
    # 经纬度 -> 底图像素
    bx, by = None, None
    try:
        from geo_mapping import lonlat_to_px
        bx_f, by_f = lonlat_to_px(lon, lat)
        bx, by = int(round(bx_f)), int(round(by_f))
    except:
        bx = int((lon - 75.0) / 65.0 * 15600)
        by = int((lat - 55.0) / (-40.0) * 9600)
    
    if bx < 0 or bx >= BASE_W or by < 0 or by >= BASE_H:
        continue
    
    city_count += 1
    # 圆圈半径
    if level == '州治':
        r = 10
        color = (180, 30, 30, 230)
        font = font_med
    elif level == '重镇':
        r = 7
        color = (80, 80, 80, 210)
        font = font_small
    else:
        r = 5
        color = (120, 120, 120, 180)
        font = font_small
    
    # 画圆圈
    layer_draw.ellipse([bx-r, by-r, bx+r, by+r], outline=color, width=2)
    
    # 标签 (右上偏移)
    label_off = r + 4
    draw_text_outlined(layer_draw, bx+label_off, by-label_off, name, font,
                       fill=(30,30,30,240), stroke=(255,255,255,200))

print(f'  已标注 {city_count} 个城池')

# ── 关隘标注 ──
PASSES = [
    ('函谷关', 110.83, 34.63),
    ('潼关',   110.25, 34.54),
    ('虎牢关', 113.18, 34.85),
    ('剑阁',   105.50, 32.27),
    ('祁山',   106.01, 34.08),
    ('阳平关', 106.65, 32.83),
    ('柴桑',   115.98, 29.73),
    ('濡须口', 117.77, 31.58),
    ('合肥',   117.27, 31.86),
    ('五丈原', 107.33, 34.23),
]

print(f'  标注 {len(PASSES)} 个关隘...')
pass_color = (150, 80, 20, 210)
for name, lon, lat in PASSES:
    try:
        from geo_mapping import lonlat_to_px
        bx_f, by_f = lonlat_to_px(lon, lat)
        bx, by = int(round(bx_f)), int(round(by_f))
    except:
        bx = int((lon - 75.0) / 65.0 * 15600)
        by = int((lat - 55.0) / (-40.0) * 9600)
    
    if 0 <= bx < BASE_W and 0 <= by < BASE_H:
        # 三角形符号
        s = 7
        layer_draw.polygon([(bx, by-s), (bx-s, by+s), (bx+s, by+s)],
                          outline=pass_color, fill=(255,200,150,140))
        draw_text_outlined(layer_draw, bx+s+3, by-s, name, font_small,
                           fill=(100,60,10,220), stroke=(255,255,255,180))

# ── 图例 & 标题 ──
print('  添加图例...')

# 标题
title = "汉末三国 十三州"
bbox_title = layer_draw.textbbox((0,0), title, font=font_large)
tw = bbox_title[2] - bbox_title[0]
th = bbox_title[3] - bbox_title[1]
title_x, title_y = 60, 60

# 标题半透明深色背景条
title_bg_w = tw + 40
title_bg_h = th + 20
for tx in range(title_x-20, title_x+title_bg_w):
    for ty in range(title_y-10, title_y+title_bg_h):
        if 0 <= tx < BASE_W and 0 <= ty < BASE_H:
            layer.putpixel((tx, ty), (40, 35, 30, 160))  # 深棕半透明

draw_text_outlined(layer_draw, title_x, title_y, title, font_large,
                   fill=(220, 190, 130, 245), stroke=(255,255,255,200))

# 数据来源
src_text = "数据来源: 地理空间数据云 (www.gscloud.cn) SRTM DEM  |  "
src_text += "考据: 《汉书·地理志》《后汉书·郡国志》谭其骧《中国历史地图集》"
draw_text_outlined(layer_draw, title_x, title_y + th + 25, src_text, font_small,
                   fill=(100,100,100,200), stroke=(255,255,255,100))

# 图例框
lx, ly = 60, BASE_H - 280
# 图例背景
for px in range(lx, lx+320):
    for py in range(ly, ly+230):
        layer.putpixel((px, py), (255,255,255,140))

draw_text_outlined(layer_draw, lx+10, ly+5, "图例", font_med, fill=(40,35,30,230))

# 州治圆圈
layer_draw.ellipse([lx+20, ly+40, lx+36, ly+56], outline=(180,30,30,230), width=2)
draw_text_outlined(layer_draw, lx+45, ly+38, "州治/重镇", font_small, fill=(40,35,30,220))

# 一般城池
layer_draw.ellipse([lx+20, ly+70, lx+30, ly+80], outline=(80,80,80,210), width=2)
draw_text_outlined(layer_draw, lx+45, ly+66, "城池", font_small, fill=(60,60,60,200))

# 关隘
s=5; layer_draw.polygon([(lx+25,ly+92-s),(lx+25-s,ly+92+s),(lx+25+s,ly+92+s)],
                      outline=(150,80,20,210), fill=(255,200,150,140))
draw_text_outlined(layer_draw, lx+45, ly+88, "关隘", font_small, fill=(100,60,10,200))

# 十三州列表 (紧凑排列)
state_names = ['司隶','冀州','兖州','青州','徐州','扬州',
               '荆州','豫州','益州','凉州','并州','幽州','交州']
draw_text_outlined(layer_draw, lx+10, ly+115, "十三州:", font_small, fill=(40,35,30,220))

col1_x = lx+10
col2_x = lx+165
for i, sn in enumerate(state_names):
    cx = col1_x if i < 7 else col2_x
    cy = ly + 138 + (i%7)*22
    draw_text_outlined(layer_draw, cx, cy, f"• {sn}", font_small, fill=(50,45,40,200))

# ── Step 5: 合成输出 ──
print('\n=== Step 5: 输出 ===')

# 合成图 (底图 + 图层)
composite = base_img.convert('RGBA')
composite = Image.alpha_composite(composite, layer)
out_composite = os.path.join(RENDERED, 'three_kingdoms_v4_overlay.png')
composite_rgb = composite.convert('RGB')
out_composite_jpg = os.path.join(RENDERED, 'three_kingdoms_v4_overlay_preview.jpg')

print(f'  保存合成图 PNG ({out_composite})...')
composite_rgb.save(out_composite, 'PNG')
print(f'  保存预览 JPG ({out_composite_jpg})...')
composite_rgb.save(out_composite_jpg, 'JPEG', quality=85)

# 单独保存透明图层
out_layer = os.path.join(RENDERED, 'three_kingdoms_v4_layer.png')
print(f'  保存透明图层 ({out_layer})...')
layer.save(out_layer, 'PNG')

# 保存GCP数据和变换参数供后续使用
calibration_data = {
    'method': 'affine_least_squares_gcp',
    'source_image': '全览-郡治.png (9933x7015)',
    'color_source': '全览-郡级.png (2020x1418)',
    'target_base': 'china_full_v3.png (15600x9600)',
    'gcp_count': len(GCPS),
    'max_residual_px': float(max_err),
    'transform_forward': {
        'lon': {'a':float(a),'b':float(b),'c':float(c)},
        'lat': {'d':float(d),'e':float(e),'f':float(f)},
    },
    'transform_inverse_zhi': {
        'px_A':float(Ai), 'px_B':float(Bi), 'px_C':float(Ci_val),
        'py_D':float(Di), 'py_E':float(Ei), 'py_F':float(Cj_val),
    },
    'scale_zhi_to_ji': {'x':float(scale_x), 'y':float(scale_y)},
    'gcps': [{'name':n,'px':int(px),'py':int(py),'lon':round(lon,4),'lat':round(lat,4)}
             for n,px,py,lon,lat in GCPS],
}

with open(os.path.join(BASE_DIR, 'gcp_calibration.json'), 'w', encoding='utf-8') as fout:
    json.dump(calibration_data, fout, ensure_ascii=False, indent=2)
print(f'  校准数据 -> gcp_calibration.json')

print('\n=== 全部完成! ===')
print(f'  合成图: {os.path.getsize(out_composite)//1024//1024} MB')
print(f'  预览图: {os.path.getsize(out_composite_jpg)//1024} KB')
print(f'  图层:   {os.path.getsize(out_layer)//1024} KB')
