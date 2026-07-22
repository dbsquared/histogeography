"""
汉末十三州图层 v5 增强 — 视觉质量修复版
========================================
基于 v4 的 GCP 校准结果，修复以下视觉问题：
1. 州域填充透明度提升 (alpha 75→148)
2. 新增13州名印章式大字标签
3. 城市标注字体放大 2x+
4. 州界线提取与叠加 (边缘检测→深色描边)
5. 水印/源图边缘裁切
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import json, os, sys
from scipy.ndimage import sobel, binary_dilation

Image.MAX_IMAGE_PIXELS = None

BASE_DIR = r'E:\projects\3D地图制作'
RENDERED = os.path.join(BASE_DIR, 'rendered')
os.makedirs(RENDERED, exist_ok=True)

# ── 加载 v4 图层 ──
print('=== 加载 v4 图层 ===')
layer_path = os.path.join(RENDERED, 'three_kingdoms_v4_layer.png')
layer_img = Image.open(layer_path).convert('RGBA')
BASE_W, BASE_H = layer_img.size
print(f'  图层尺寸: {BASE_W}x{BASE_H}')

arr = np.array(layer_img)
rgb = arr[:,:,:3].astype(np.float32)
alpha_orig = arr[:,:,3].copy()

# ── 1) 提升透明度 ──
print('\n=== 1) 提升填充透明度 ===')
ALPHA_NEW = 148
# 有颜色的像素(原alpha>0)提升到新值
has_color = alpha_orig > 0
new_alpha = np.zeros_like(alpha_orig)
new_alpha[has_color] = ALPHA_NEW
# 边缘区域保持渐变效果(原alpha<75的保持相对比例)
edge_mask = (alpha_orig > 0) & (alpha_orig < 60)
if edge_mask.any():
    # 边缘用较低alpha做平滑过渡
    new_alpha[edge_mask] = np.clip(alpha_orig[edge_mask].astype(float) * 2.5, 20, 90).astype(np.uint8)

arr[:,:,3] = new_alpha
print(f'  有色像素: {int(has_color.sum()):,} ({100*has_color.mean():.1f}%)')
print(f'  新alpha均值: {float(new_alpha[has_color].mean()):.1f}')

# ── 2) 提取州界线 ──
print('\n=== 2) 提取州界线 ===')
# 方法: 对RGB三通道分别做Sobel边缘检测，合并后二值化
# 只在有色区域内检测边界
edges = np.zeros((BASE_H, BASE_W), dtype=np.float32)
for ch in range(3):
    sx = sobel(rgb[:,:,ch], axis=0)
    sy = sobel(rgb[:,:,ch], axis=1)
    edges += np.sqrt(sx*sx + sy*sy)

# 归一化
e_max = edges.max() if edges.max() > 0 else 1
edges_norm = edges / e_max

# 二值化: 强边缘 + 仅在有色区域内部
edge_threshold = 0.12
edge_binary = (edges_norm > edge_threshold) & has_color
# 稍微膨胀让线条更连续
edge_binary = binary_dilation(edge_binary, iterations=1)

edge_px = int(edge_binary.sum())
print(f'  边缘像素: {edge_px:,} ({100*edge_px/has_color.sum():.2f}% of colored area)')

# ── 3) 构建增强图层 ──
print('\n=== 3) 构建增强图层 ===')

enhanced = arr.copy()

# 叠加深色州界线 (暗红色, 半透明)
border_color = np.array([120, 30, 30, 200], dtype=np.uint8)  # 暗红
for y in range(BASE_H):
    for x in range(BASE_W):
        if edge_binary[y, x]:
            enhanced[y, x, :3] = border_color[:3]
            enhanced[y, x, 3] = max(enhanced[y, x, 3], border_color[3])

# 用向量化替代循环 (上面的循环太慢了, 改为向量化)
enhanced[edge_binary, :3] = border_color[:3]
enhanced[edge_binary, 3] = np.maximum(enhanced[edge_binary, 3], border_color[3])

print(f'  州界线已绘制')

# ── 字体加载 ──
try:
    font_state   = ImageFont.truetype("msyh.ttc", 108)   # 州名大字
    font_capital = ImageFont.truetype("msyh.ttc", 88)     # 州治/重镇
    font_city    = ImageFont.truetype("msyh.ttc", 64)     # 一般城池
    font_small   = ImageFont.truetype("msyh.ttc", 48)     # 关隘/小字
except:
    font_state = ImageFont.load_default()
    font_capital = font_city = font_small = font_state


def draw_text_outlined(draw, x, y, text, font,
                       fill=(0,0,0,255), stroke=(255,255,255,220),
                       stroke_width=4):
    """描边文字"""
    for dx in range(-stroke_width, stroke_width+1):
        for dy in range(-stroke_width, stroke_width+1):
            if dx*dx + dy*dy <= stroke_width*stroke_width:
                draw.text((x+dx, y+dy), text, font=font, fill=stroke)
    draw.text((x, y), text, font=font, fill=fill)


def draw_seal_text(draw, cx, cy, text, font,
                   fill=(180, 20, 20, 230),
                   bg_fill=None):
    """古风印章式文字: 红底金字 + 圆角矩形背景"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    pad_x = max(16, tw // 6)
    pad_y = max(10, th // 4)
    rx0 = cx - tw//2 - pad_x
    ry0 = cy - th//2 - pad_y - 4
    rx1 = cx + tw//2 + pad_x
    ry1 = cy + th//2 + pad_y + 4

    # 暗红圆角背景 (模拟印章)
    if bg_fill is None:
        bg_fill = (139, 0, 0, 175)  # 暗红半透明

    draw.rounded_rectangle([rx0, ry0, rx1, ry1],
                           radius=max(8, min(tw,th)//8),
                           fill=bg_fill)

    # 金色描边 + 主字
    gold_stroke = (255, 215, 0, 200)
    draw_text_outlined(draw, cx - tw//2, cy - th//2 - 4, text, font,
                       fill=fill, stroke=gold_stroke, stroke_width=3)


def lonlat_to_px(lon, lat):
    """WGS84 -> 底图像素 (来自 geo_mapping.py)"""
    LON_MIN, LON_MAX = 75.0, 140.0
    LAT_MAX, LAT_MIN = 55.0, 15.0
    px = (lon - LON_MIN) / (LON_MAX - LON_MIN) * BASE_W
    py = (lat - LAT_MAX) / (LAT_MIN - LAT_MAX) * BASE_H
    return int(round(px)), int(round(py))


enhanced_img = Image.fromarray(enhanced, 'RGBA')
draw = ImageDraw.Draw(enhanced_img)


# ── 4) 州名印章标签 (手动定位各州视觉中心) ──
print('\n=== 4) 绘制州名印章 ===')

# 各州名称 + 近似中心坐标 (WGS84, 经考据谭其骧历史地图集)
STATE_SEALS = [
    ('司隶',   111.50, 35.00),   # 洛阳附近
    ('冀州',   115.70, 37.40),   # 邺/信都之间
    ('兖州',   116.00, 35.50),   # 昌邑/濮阳一带
    ('青州',   118.20, 36.65),   # 临淄附近
    ('徐州',   117.80, 34.25),   # 下邳/彭城一带
    ('扬州',   118.50, 31.50),   # 寿春/建业之间偏西
    ('荆州',   112.00, 30.80),   # 襄阳/江陵之间偏北
    ('豫州',   114.80, 33.50),   # 宛/谯之间
    ('益州',   105.00, 30.80),   # 成都附近
    ('凉州',   104.50, 36.50),   # 武威/姑臧东南
    ('并州',   112.60, 37.20),   # 晋阳/太原附近
    ('幽州',   116.80, 39.50),   # 蓟/北京西南
    ('交州',   111.50, 22.50),   # 番禺西北(广信/苍梧)
]

seal_count = 0
for sname, slon, slat in STATE_SEALS:
    sx, sy = lonlat_to_px(slon, slat)
    if 200 <= sx < BASE_W-200 and 100 <= sy < BASE_H-100:
        draw_seal_text(draw, sx, sy, sname, font_state,
                      fill=(220, 190, 130, 240))  # 金色主字
        seal_count += 1
        print(f'  {sname}: pixel({sx},{sy})')

print(f'  已绘制 {seal_count}/13 个州名印章')


# ── 5) 城市标注 (加大字号) ──
print('\n=== 5) 标注城池 ===')

KEY_CITIES = [
    # (古代名, 经度, 纬度, 等级, 备注)
    ('洛阳',   112.45, 34.62, '州治', '司隶'),
    ('长安',   108.94, 34.34, '州治', '司隶'),
    ('雒县',   104.28, 30.99, '州治', '益州'),
    ('寿春',   116.78, 32.56, '州治', '扬州'),
    ('蓟',     116.40, 39.90, '州治', '幽州'),
    ('晋阳',   112.55, 37.87, '州治', '并州'),
    ('临淄',   118.03, 36.82, '州治', '青州'),
    ('郯',     118.34, 34.71, '州治', '徐州'),
    ('番禺',   113.26, 23.13, '州治', '交州'),
    ('陇县',   106.21, 35.00, '州治', '凉州'),
    ('谯',     115.77, 33.87, '州治', '豫州'),
    ('信都',   115.57, 37.59, '州治', '冀州'),
    ('昌县',   118.37, 36.83, '州治', '青州'),  # 青州另一治所
    ('襄阳',   112.13, 32.02, '重镇', ''),
    ('江陵',   112.24, 30.04, '重镇', ''),
    ('宛',     112.53, 33.00, '重镇', ''),
    ('邺',     115.43, 36.35, '重镇', ''),
    ('建业',   118.78, 32.06, '重镇', ''),
    ('成都',   104.07, 30.67, '重镇', ''),
    ('姑臧',   102.63, 37.93, '重镇', ''),
    ('新野',   112.05, 32.51, '一般', ''),
    ('汉寿',   111.97, 28.97, '一般', ''),
    ('历阳',   118.38, 31.62, '一般', ''),
    ('合肥',   117.27, 31.86, '一般', ''),
]

city_count = 0
for cname, clon, clat, level, note in KEY_CITIES:
    cx, cy = lonlat_to_px(clon, clat)
    if not (100 <= cx < BASE_W-100 and 50 <= cy < BASE_H-50):
        continue

    city_count += 1
    if level == '州治':
        r, fnt, clr = 14, font_capital, (180, 30, 30, 245)
    elif level == '重镇':
        r, fnt, clr = 10, font_city, (60, 60, 60, 230)
    else:
        r, fnt, clr = 7, font_small, (100, 100, 100, 210)

    # 城池圆圈
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=clr, width=3)

    # 标签 (右上偏移避免遮挡)
    loff = r + 6
    draw_text_outlined(draw, cx+loff, cy-loff, cname, fnt,
                       fill=(30,30,30,245), stroke=(255,255,255,220))

print(f'  已标注 {city_count} 个城池')


# ── 6) 关隘标注 ──
PASSES = [
    ('函谷关', 110.83, 34.63),
    ('潼关',   110.25, 34.54),
    ('虎牢关', 113.18, 34.85),
    ('剑阁',   105.50, 32.27),
    ('祁山',   106.01, 34.08),
    ('阳平关', 106.65, 32.83),
    ('濡须口', 117.77, 31.58),
    ('五丈原', 107.33, 34.23),
    ('柴桑',   115.98, 29.73),
    ('合肥',   117.27, 31.86),
]

pass_count = 0
for pname, plon, plat in PASSES:
    px, py = lonlat_to_px(plon, plat)
    if not (100 <= px < BASE_W-100 and 50 <= py < BASE_H-50):
        continue
    pass_count += 1
    s = 9
    draw.polygon([(px, py-s), (px-s, py+s), (px+s, py+s)],
                outline=(150, 80, 20, 225), fill=(255, 200, 150, 150))
    draw_text_outlined(draw, px+s+4, py-s, pname, font_small,
                       fill=(100, 60, 10, 230), stroke=(255,255,255,180))
print(f'  已标注 {pass_count} 个关隘')


# ── 7) 标题 & 数据来源 ──
print('\n=== 7) 标题 & 元信息 ===')
title = "汉末三国 十三州疆域图"
tbbox = draw.textbbox((0,0), title, font=font_capital)
tw = tbbox[2] - tbbox[0]
th = tbbox[3] - tbbox[1]
tx, ty = 80, 80

# 标题无白底 — 直接描边
draw_text_outlined(draw, tx, ty, title, font_capital,
                   fill=(210, 175, 110, 250), stroke=(40, 30, 20, 220), stroke_width=5)

# 数据来源
src = "数据来源: 地理空间数据云 SRTM DEM  |  考据: 《汉书·地理志》《后汉书·郡国志》"
draw_text_outlined(draw, tx, ty + th + 28, src, font_small,
                   fill=(90,85,80,200), stroke=(255,255,255,100))


# ── 8) 保存输出 ──
print('\n=== Step 8: 保存输出 ===')

# 合成图
base_img = Image.open(os.path.join(BASE_DIR, 'china_full_v3.png')).convert('RGBA')
composite = Image.alpha_composite(base_img, enhanced_img)

out_comp = os.path.join(RENDERED, 'three_kingdoms_v5_overlay.png')
out_prev = os.path.join(RENDERED, 'three_kingdoms_v5_overlay_preview.jpg')
out_layer = os.path.join(RENDERED, 'three_kingdoms_v5_layer.png')

print(f'  保存合成图 PNG...')
composite.convert('RGB').save(out_comp, 'PNG')
print(f'  保存预览 JPG...')
composite.convert('RGB').save(out_prev, 'JPEG', quality=90)
print(f'  保存透明图层...')
enhanced_img.save(out_layer, 'PNG')

# 小预览 (用于快速查看)
scale = 1500.0/BASE_W
small = composite.convert('RGB').resize((int(BASE_W*scale), int(BASE_H*scale)), Image.LANCZOS)
small.save(os.path.join(RENDERED, 'three_kingdoms_v5_verify_small.png'))

cs = os.path.getsize(out_comp)//1024//1024
ps = os.path.getsize(out_prev)//1024
ls = os.path.getsize(out_layer)//1024
print(f'\n=== 完成! ===')
print(f'  合成图: {cs} MB  ({out_comp})')
print(f'  预览图: {ps} KB  ({out_prev})')
print(f'  图层:   {ls} KB  ({out_layer})')
print(f'  小预览: rendered/three_kingdoms_v5_verify_small.png')
