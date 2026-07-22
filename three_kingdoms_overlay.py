#!/usr/bin/env python3
"""
汉末十三州地图图层生成器 v3 (final)

严格匹配图例(全览-郡级.png)的视觉规范:
  - 每州一个鲜明的填色（类似图例配色）
  - 州界为白色分隔线（颜色变化处自然形成）
  - 城市用小圆圈○标注
  - 所有标签描边，禁止任何背景色块

考据依据:
  《汉书·地理志》《后汉书·郡国志》+ 谭其骧《中国历史地图集》第二册
"""

import os, math, json
from PIL import Image, ImageDraw, ImageFont

# ── 路径 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PNG = os.path.join(BASE_DIR, 'china_full_v3.png')
OUTPUT_DIR = os.path.join(BASE_DIR, 'rendered')
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── 地图范围 ──
LON_MIN, LON_MAX = 75.0, 140.0
LAT_MIN, LAT_MAX = 15.0, 55.0
IMG_W, IMG_H = 15600, 9600

# ══════════════════════════════════════════
#  视觉风格 — 匹配图例(全览-郡级.png)
# ══════════════════════════════════════════

# 每州的填充色（从图例目视提取）
STATE_COLORS = {
    "司隶":  (192, 144, 145, 140),   # 浅红褐（关中-洛阳）
    "冀州":  (144, 191, 192, 140),    # 浅青蓝（河北）
    "兖州":  (179, 76, 144, 140),     # 紫红（鲁西-豫东）
    "青州":  (143, 192, 95, 140),     # 黄绿（山东半岛）
    "徐州":  (95, 144, 95, 140),      # 橄榄绿（鲁南苏北）
    "豫州":  (144, 143, 191, 140),    # 淡紫蓝（河南）
    "扬州":  (143, 191, 144, 140),    # 亮绿（东南沿海）
    "荆州":  (191, 95, 96, 140),      # 红色（两湖）
    "益州":  (192, 192, 128, 140),    # 米黄（川渝云贵）
    "凉州":  (224, 160, 128, 140),    # 浅橙（河西走廊）
    "并州":  (192, 153, 96, 140),     # 土黄（山西）
    "幽州":  (95, 137, 144, 140),     # 青绿（东北-朝鲜）
    "交州":  (191, 98, 192, 140),     # 品红（华南-越南）
}

# 州界线：深色细线（类似图例中的郡界线风格，稍粗一点用于州界）
STATE_BORDER_COLOR = (80, 60, 50, 200)
STATE_BORDER_WIDTH = 2

# 文字
FONT_PATHS = [
    'C:/Windows/Fonts/msyhbd.ttc',
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/simhei.ttf',
]

STATE_FONT_SIZE = 90       # 州名字体大小
CAPITAL_FONT_SIZE = 48     # 州治字体
CITY_FONT_SIZE = 36        # 普通城池字体
PASS_FONT_SIZE = 32        # 关隘字体

CAPITAL_CIRCLE_R = 8       # 州治圆圈半径
CITY_CIRCLE_R = 5          # 普通城池圆圈半径
CIRCLE_COLOR = (120, 40, 30, 230)
CIRCLE_FILL = (255, 252, 245, 180)

TEXT_DARK = (45, 35, 25, 240)
TEXT_OUTLINE = (255, 250, 240, 200)
PASS_COLOR = (150, 50, 35, 210)


def get_font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def lonlat_to_pixel(lon, lat):
    px = (lon - LON_MIN) / (LON_MAX - LON_MIN) * IMG_W
    py = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * IMG_H
    return (px, py)


def geo_to_px_int(lon, lat):
    x, y = lonlat_to_pixel(lon, lat)
    return (int(round(x)), int(round(y)))


def draw_text_outlined(draw, x, y, text, font, fill, outline, ox=2, oy=2):
    """描边文字（无背景）"""
    for dx, dy in [(-ox,0),(ox,0),(0,-oy),(0,oy),
                   (-ox,-oy),(ox,-oy),(-ox,oy),(ox,oy)]:
        draw.text((x+dx, y+dy), text, font=font, fill=outline)
    draw.text((x, y), text, font=font, fill=fill)


def draw_text_dark(draw, x, y, text, font):
    """深色文字+浅色描边"""
    draw_text_outlined(draw, x, y, text, font, TEXT_DARK, TEXT_OUTLINE)


def draw_text_white(draw, x, y, text, font):
    """白色文字+深色描边"""
    wo = (30, 25, 20, 200)
    draw_text_outlined(draw, x, y, text, font, (255,255,255,240), wo)


# ══════════════════════════════════════════
#  十三州边界多边形 [(lon,lat), ...]
#  依据：谭其骧《中国历史地图集》第二册
# ══════════════════════════════════════════

STATE_BOUNDARIES = {
    "司隶": [
        (106.0, 35.2), (106.5, 35.5), (107.5, 36.0),
        (109.0, 36.2), (110.0, 36.3), (111.0, 36.3),
        (112.0, 36.0), (112.5, 35.7), (113.4, 35.3),
        (113.5, 34.7), (113.0, 34.2), (112.5, 33.9),
        (111.5, 33.7), (110.5, 33.7), (109.5, 33.8),
        (108.5, 33.9), (107.5, 34.0), (106.5, 34.3),
    ],
    "冀州": [
        (115.5, 39.2), (114.5, 38.8), (114.0, 38.0),
        (113.8, 37.3), (114.0, 36.5), (114.2, 35.8),
        (115.0, 35.5), (115.8, 35.5), (116.5, 35.8),
        (117.3, 36.3), (117.8, 37.0), (117.8, 38.0),
        (117.5, 38.7), (116.5, 39.0),
    ],
    "兖州": [
        (115.8, 35.8), (115.5, 35.2), (114.8, 34.8),
        (114.5, 34.5), (115.2, 34.2), (116.0, 34.0),
        (116.8, 34.0), (117.3, 34.5), (117.8, 35.0),
        (118.0, 35.3), (117.5, 35.8), (116.5, 36.0),
        (116.2, 35.8), (115.8, 35.9),
    ],
    "青州": [
        (116.2, 36.0), (116.8, 36.2), (117.3, 36.2),
        (117.8, 36.0), (118.7, 36.0), (119.2, 36.2),
        (119.8, 36.5), (120.2, 37.0), (120.3, 37.5),
        (120.0, 38.0), (119.0, 37.8), (118.0, 37.5),
        (117.2, 37.0), (116.5, 36.5),
    ],
    "徐州": [
        (117.0, 35.5), (117.3, 35.2), (118.2, 35.0),
        (118.8, 35.0), (119.2, 34.5), (119.0, 34.0),
        (118.0, 33.5), (117.3, 33.3), (116.5, 33.3),
        (116.0, 34.0), (115.8, 34.5), (115.8, 35.0),
        (116.5, 35.3),
    ],
    "豫州": [
        (113.5, 34.7), (114.0, 34.5), (114.5, 34.2),
        (114.0, 33.8), (113.5, 33.5), (113.8, 32.8),
        (114.5, 32.3), (115.5, 32.5), (116.0, 32.5),
        (116.5, 33.0), (117.0, 33.5), (116.5, 34.5),
        (115.5, 34.8),
    ],
    "扬州": [
        (117.5, 33.0), (116.8, 33.0), (116.0, 32.5),
        (114.5, 32.0), (114.0, 31.0), (113.5, 29.0),
        (113.5, 26.5), (115.0, 25.0), (116.5, 23.5),
        (117.0, 23.0), (119.0, 23.5), (120.5, 25.5),
        (121.5, 28.0), (121.5, 30.5), (120.5, 31.5),
        (119.5, 32.0), (119.0, 32.5), (118.5, 33.0),
    ],
    "荆州": [
        (111.5, 33.7), (112.5, 33.3), (113.5, 32.8),
        (114.5, 31.5), (114.5, 30.5), (114.0, 29.5),
        (113.5, 28.0), (113.0, 26.5), (112.0, 25.5),
        (111.0, 25.5), (110.0, 26.5), (109.0, 27.5),
        (108.5, 29.0), (109.0, 30.5), (109.5, 31.5),
        (110.0, 32.5), (111.0, 33.0), (111.3, 33.5),
    ],
    "益州": [
        (106.5, 34.3), (107.0, 33.8), (108.0, 33.5),
        (109.0, 33.0), (109.5, 32.5), (109.0, 31.0),
        (108.5, 29.5), (108.5, 28.0), (108.5, 26.5),
        (107.0, 25.5), (105.5, 24.5), (103.5, 24.5),
        (101.0, 24.5), (99.5, 25.5), (99.0, 27.0),
        (99.5, 28.5), (100.5, 29.5), (101.5, 30.5),
        (102.5, 31.5), (103.5, 33.0), (104.5, 33.5),
        (105.5, 34.0), (106.0, 34.2),
    ],
    "凉州": [
        (99.5, 35.5), (101.0, 35.8), (102.0, 36.2),
        (103.5, 36.5), (104.5, 36.5), (105.5, 35.0),
        (106.0, 35.2), (106.5, 35.5), (107.0, 35.8),
        (107.5, 36.3), (107.5, 37.0), (107.0, 37.5),
        (106.5, 38.0), (106.0, 38.5), (105.5, 38.8),
        (104.5, 39.0), (103.5, 38.8), (102.0, 38.8),
        (100.0, 39.0), (98.0, 39.5), (96.0, 39.8),
        (94.5, 40.0), (95.0, 39.0), (96.0, 37.5),
        (97.5, 36.5), (98.5, 36.0), (99.5, 35.8),
    ],
    "并州": [
        (110.5, 39.3), (111.5, 39.8), (112.3, 39.8),
        (113.0, 39.5), (113.5, 39.3), (113.8, 38.5),
        (114.0, 38.0), (113.8, 37.3), (113.5, 36.5),
        (113.0, 36.0), (112.5, 35.8), (111.5, 35.7),
        (110.5, 35.8), (110.0, 36.3), (109.5, 37.0),
        (109.0, 37.5), (109.0, 38.3), (109.5, 38.8),
        (110.0, 39.0),
    ],
    "幽州": [
        (113.5, 39.3), (114.5, 40.0), (116.0, 41.0),
        (117.5, 41.5), (119.0, 42.0), (120.5, 41.5),
        (122.0, 41.5), (123.5, 41.5), (124.5, 41.0),
        (125.5, 40.0), (125.0, 39.0), (124.5, 38.5),
        (123.5, 38.5), (122.5, 39.0), (121.5, 39.5),
        (120.5, 40.0), (119.5, 39.8), (118.5, 39.5),
        (117.5, 39.5), (117.0, 39.3), (116.5, 39.5),
        (116.0, 39.7), (115.5, 39.8), (114.5, 39.5),
    ],
    "交州": [
        (114.5, 25.0), (113.5, 25.0), (112.5, 25.0),
        (111.0, 25.2), (110.0, 25.5), (109.0, 25.5),
        (107.5, 25.0), (106.5, 24.5), (105.0, 24.0),
        (104.5, 23.0), (104.0, 22.0), (104.0, 20.5),
        (105.0, 19.5), (106.0, 18.5), (107.5, 18.0),
        (108.5, 18.5), (109.0, 20.0), (109.5, 21.0),
        (110.0, 21.5), (111.0, 22.0), (112.0, 22.5),
        (113.3, 23.0), (114.0, 23.5), (114.5, 24.5),
    ],
}

# 州名标签位置（像素坐标，手动调整到各州中心合适位置）
STATE_LABEL_POS = {
    "司隶": (8500, 5200),
    "冀州": (9400, 3400),
    "兖州": (10100, 4500),
    "青州": (10500, 3600),
    "徐州": (10500, 5000),
    "豫州": (9700, 5500),
    "扬州": (10400, 6800),
    "荆州": (8600, 6200),
    "益州": (6800, 5800),
    "凉州": (5000, 3800),
    "并州": (8400, 3600),
    "幽州": (9600, 2500),
    "交州": (7900, 8200),
}

# ── 治所 ──
CAPITALS = {
    "洛阳": (112.47, 34.62),
    "长安": (108.95, 34.27),
    "信都": (115.57, 37.59),
    "昌邑": (116.26, 35.07),
    "临淄": (118.37, 36.83),
    "郯": (118.34, 34.71),
    "谯": (115.77, 33.87),
    "寿春": (116.78, 32.61),
    "雒": (104.28, 30.99),
    "陇": (106.21, 35.00),
    "晋阳": (112.43, 37.74),
    "蓟": (116.34, 39.93),
    "番禺": (113.27, 23.13),
}
# 荆州四治所
JZ_CAPS = {"新野": (112.05, 32.51), "襄阳": (112.13, 32.00),
           "江陵": (112.18, 30.04)}

# 重要城池
CITIES = {
    # 司隶
    "郿坞": (107.80, 34.28), "华阴": (110.10, 34.57), "弘农": (110.85, 34.55),
    # 冀州
    "邺城": (114.53, 36.33), "官渡": (113.90, 34.90), "白马": (114.55, 35.65),
    "平原": (116.45, 37.15),
    # 兖州
    "濮阳": (115.00, 35.72), "陈留": (114.50, 34.75), "东阿": (116.23, 36.33),
    # 青州
    "北海": (119.10, 36.77), "济南": (117.00, 36.65),
    # 徐州
    "下邳": (117.95, 34.35), "彭城": (117.18, 34.26), "小沛": (116.93, 34.70),
    "广陵": (119.42, 32.40),
    # 豫州
    "许": (113.85, 34.03), "汝南": (114.35, 33.00), "颍川": (113.48, 34.16),
    "宛": (112.53, 33.00),
    # 扬州
    "合肥": (117.23, 31.82), "建业": (118.78, 32.05),
    "会稽": (120.58, 30.00), "柴桑": (115.97, 29.72),
    "吴郡": (120.62, 31.30), "庐江": (117.30, 31.33),
    "濡须口": (117.57, 31.30),
    # 荆州
    "樊城": (112.15, 32.02), "赤壁": (113.55, 29.70),
    "江夏": (114.30, 30.35), "长沙": (112.97, 28.22),
    "武陵": (111.70, 29.03), "零陵": (111.60, 26.43),
    "桂阳": (112.73, 25.77), "夷陵": (111.30, 30.80),
    # 益州
    "成都": (104.07, 30.67), "汉中": (107.03, 33.08),
    "白帝城": (109.55, 31.05), "葭萌关": (105.78, 32.37),
    "绵竹": (104.20, 31.13), "江州": (106.55, 29.57),
    "剑阁": (105.55, 32.08),
    # 凉州
    "金城": (103.80, 36.07), "姑臧": (102.64, 37.93),
    "天水": (105.72, 34.58), "街亭": (106.30, 35.30),
    # 并州
    "上党": (112.87, 36.33), "雁门": (112.77, 39.20),
    # 幽州
    "涿郡": (115.95, 39.45), "辽东": (123.18, 41.28),
    "右北平": (118.85, 41.80), "辽西": (119.65, 41.50),
    "乐浪": (124.30, 39.00),
    # 交州
    "合浦": (109.20, 21.67), "苍梧": (111.30, 23.48),
    "交趾": (105.85, 21.03),
}

PASSES = {
    "函谷关": (110.92, 34.67), "武关": (110.50, 33.58),
    "散关": (107.00, 34.25), "虎牢关": (113.40, 34.82),
    "天井关": (112.85, 35.17), "义阳三关": (114.20, 31.80),
    "剑门关": (105.55, 32.08), "阳平关": (106.17, 33.12),
    "祁山": (105.30, 34.18), "雁门关": (112.77, 39.20),
    "居庸关": (116.07, 40.28), "阳关": (94.00, 39.87),
    "玉门关": (93.80, 40.35), "穆陵关": (119.32, 36.05),
    "壶关": (113.30, 36.12), "井陉": (114.13, 38.00),
}


# ══════════════════════════════════════════
#  主绘制流程
# ══════════════════════════════════════════

def main():
    print("读取底图...")
    base = Image.open(BASE_PNG).convert('RGBA')
    
    # 创建透明图层
    layer = Image.new('RGBA', (IMG_W, IMG_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    state_font = get_font(STATE_FONT_SIZE)
    cap_font = get_font(CAPITAL_FONT_SIZE)
    city_font = get_font(CITY_FONT_SIZE)
    pass_font = get_font(PASS_FONT_SIZE)

    # ── 1. 绘制州域填充 ──
    print("绘制13州填充...")
    for name, coords in STATE_BOUNDARIES.items():
        if len(coords) < 3:
            continue
        pixels = [geo_to_px_int(lon, lat) for lon, lat in coords]
        
        color = STATE_COLORS.get(name, (200, 200, 200, 100))
        draw.polygon(pixels, fill=color)

    # ── 2. 绘制州界线 ──
    print("绘制州界线...")
    for name, coords in STATE_BOUNDARIES.items():
        if len(coords) < 3:
            continue
        closed = coords + [coords[0]]
        pixels = [geo_to_px_int(lon, lat) for lon, lat in closed]
        
        for i in range(len(pixels) - 1):
            p1, p2 = pixels[i], pixels[i+1]
            # 只画在范围内的线段
            if (-1000 <= p1[0] <= IMG_W+1000 and -1000 <= p1[1] <= IMG_H+1000):
                draw.line([p1, p2], fill=STATE_BORDER_COLOR, width=STATE_BORDER_WIDTH)

    # ── 3. 州名标签（深色描边文字，无背景）──
    print("绘制州名标签...")
    for name, (px, py) in STATE_LABEL_POS.items():
        bbox = draw.textbbox((0, 0), name, font=state_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        lx = px - tw // 2
        ly = py - th // 2
        
        # 根据该州填充色选择文字颜色（深色底用白字，浅色底用黑字）
        sc = STATE_COLORS.get(name, (200, 200, 200, 100))
        brightness = 0.299*sc[0] + 0.587*sc[1] + 0.114*sc[2]
        if brightness > 150:
            draw_text_dark(draw, lx, ly, name, state_font)
        else:
            draw_text_white(draw, lx, ly, name, state_font)

    # ── 4. 州治（大圆圈 + 大字标签）──
    print("绘制治所和城池...")
    cap_coords_set = set()
    for cname, (lon, lat) in CAPITALS.items():
        px, py = geo_to_px_int(lon, lat)
        key = (round(lon, 2), round(lat, 2))
        cap_coords_set.add(key)

        r = CAPITAL_CIRCLE_R
        draw.ellipse([px-r, py-r, px+r, py+r],
                     fill=CIRCLE_FILL, outline=CIRCLE_COLOR, width=3)
        draw.ellipse([px-3, py-3, px+3, py+3], fill=CIRCLE_COLOR)

        bbox = draw.textbbox((0, 0), cname, font=cap_font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        lx = px - tw//2
        ly = py - r - th - 4
        draw_text_dark(draw, lx, ly, cname, cap_font)

    # 荆州四治所
    for cname, (lon, lat) in JZ_CAPS.items():
        key = (round(lon, 2), round(lat, 2))
        if key in cap_coords_set:
            continue
        px, py = geo_to_px_int(lon, lat)
        r = CAPITAL_CIRCLE_R
        draw.ellipse([px-r, py-r, px+r, py+r],
                     fill=CIRCLE_FILL, outline=CIRCLE_COLOR, width=3)
        draw.ellipse([px-3, py-3, px+3, py+3], fill=CIRCLE_COLOR)
        bbox = draw.textbbox((0, 0), cname, font=cap_font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        draw_text_dark(draw, px-tw//2, py-r-th-4, cname, cap_font)

    # ── 5. 普通城池（小圆圈 + 小字）──
    for cname, (lon, lat) in CITIES.items():
        key = (round(lon, 2), round(lat, 2))
        if key in cap_coords_set:
            continue
        px, py = geo_to_px_int(lon, lat)
        r = CITY_CIRCLE_R
        draw.ellipse([px-r, py-r, px+r, py+r],
                     fill=CIRCLE_FILL, outline=CIRCLE_COLOR, width=2)
        draw.ellipse([px-2, py-2, px+2, py+2], fill=CIRCLE_COLOR)

        bbox = draw.textbbox((0, 0), cname, font=city_font)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        lx = px - tw//2
        ly = py - r - th - 3
        draw_text_dark(draw, lx, ly, cname, city_font)

    # ── 6. 关隘（三角 + 标签）──
    print("绘制关隘...")
    for pname, (lon, lat) in PASSES.items():
        px, py = geo_to_px_int(lon, lat)
        s = 6
        # 小三角
        draw.polygon([(px, py-s), (px-s, py+s//2), (px+s, py+s//2)],
                     fill=PASS_COLOR)
        bbox = draw.textbbox((0, 0), pname, font=pass_font)
        tw = bbox[2]-bbox[0]
        draw_text_dark(draw, px - tw//2 - s - 2, py + s//2 + 2,
                        pname, pass_font)

    # ── 7. 图例 ──
    print("绘制图例...")
    legend_x, legend_y = 120, 100
    line_h = 55
    
    title_font = get_font(66)
    note_font = get_font(36)
    
    # 标题
    draw_text_dark(draw, legend_x, legend_y,
                   "东汉末年十三州", title_font)
    legend_y += line_h + 20
    
    # 图例项
    items = [
        ("州界", STATE_BORDER_COLOR, "line"),
        ("州治/重镇", CIRCLE_COLOR, "capital"),
        ("城池", CIRCLE_COLOR, "city"),
        ("关隘", PASS_COLOR, "pass"),
    ]
    for label, ctype in [(i[0], i[2]) for i in items]:
        y_off = legend_y
        if ctype == "line":
            draw.line([(legend_x, y_off+10), (legend_x+40, y_off+10)],
                      fill=STATE_BORDER_COLOR, width=STATE_BORDER_WIDTH)
            lx = legend_x + 55
        elif ctype == "capital":
            r = CAPITAL_CIRCLE_R
            draw.ellipse([legend_x+20-r, y_off+10-r, legend_x+20+r, y_off+10+r],
                         fill=CIRCLE_FILL, outline=CIRCLE_COLOR, width=2)
            draw.ellipse([legend_x+17, y_off+7, legend_x+23, y_off+13], fill=CIRCLE_COLOR)
            lx = legend_x + 55
        elif ctype == "city":
            r = CITY_CIRCLE_R
            draw.ellipse([legend_x+20-r, y_off+10-r, legend_x+20+r, y_off+10+r],
                         fill=CIRCLE_FILL, outline=CIRCLE_COLOR, width=2)
            draw.ellipse([legend_x+18, y_off+8, legend_x+22, y_off+12], fill=CIRCLE_COLOR)
            lx = legend_x + 55
        elif ctype == "pass":
            s = 5
            draw.polygon([(legend_x+20, y_off+10-s),
                         (legend_x+20-s, y_off+10+s//2),
                         (legend_x+20+s, y_off+10+s//2)], fill=PASS_COLOR)
            lx = legend_x + 55
        
        draw_text_dark(draw, lx, y_off, label, note_font)
        legend_y += line_h

    # 数据来源
    legend_y += 20
    src_font = get_font(28)
    draw.text((legend_x, legend_y),
              "考据:《汉书地理志》《后汉书郡国志》 谭其骧《中国历史地图集》",
              fill=(100, 90, 80, 180), font=src_font)
    legend_y += 35
    draw.text((legend_x, legend_y),
              "地形数据来源: 地理空间数据云 www.gscloud.cn (SRTM DEM)",
              fill=(100, 90, 80, 180), font=src_font)

    # ── 合成输出 ──
    print("合成图像...")
    result = Image.alpha_composite(base, layer)
    
    out_main = os.path.join(OUTPUT_DIR, 'three_kingdoms_overlay_v3.png')
    out_layer = os.path.join(OUTPUT_DIR, 'three_kingdoms_overlay_v3_layer.png')
    out_preview = os.path.join(OUTPUT_DIR, 'three_kingdoms_overlay_v3_preview.jpg')

    result.save(out_main)
    layer.save(out_layer)
    
    # 预览图（缩小保存为JPG）
    preview = result.resize((3120, 1920), Image.LANCZOS)
    rgb_preview = preview.convert('RGB')
    rgb_preview.save(out_preview, quality=88)

    print(f"\n完成!")
    print(f"  合成图: {out_main}")
    print(f"  透明图层: {out_layer}")
    print(f"  预览图: {out_preview}")


if __name__ == '__main__':
    main()
