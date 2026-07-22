#!/usr/bin/env python3
"""
中国主要江河覆盖图层生成器
在 china_full_v3.png 地形图上叠加河流图层

数据来源: Natural Earth 10m Rivers (public domain)
地形底图: china_full_v3.png (downsample=5, 15600×9600, 75°E-140°E / 15°N-55°N)
"""

import json
import os
import sys
import math
import shapefile
from PIL import Image, ImageDraw, ImageFont

# ── 路径配置 ──
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_PNG = os.path.join(BASE_DIR, 'china_full_v3.png')
RIVERS_GEOJSON = os.path.join(BASE_DIR, 'data', 'rivers', 'ne_10m_rivers.geojson')
LAKES_SHP = os.path.join(BASE_DIR, 'data', 'lakes', 'ne_10m_lakes.shp')
OUTPUT_DIR = os.path.join(BASE_DIR, 'rendered')

# ── 地图范围 (与 GeoTIFF bounds 一致) ──
LON_MIN, LON_MAX = 75.0, 140.0
LAT_MIN, LAT_MAX = 15.0, 55.0
IMG_W, IMG_H = 15600, 9600

# ── 色条位置 (模块级, 供标签放置逻辑使用) ──
CBAR_W = 260
CBAR_PAD = 60
CBAR_X0 = IMG_W - CBAR_PAD - CBAR_W   # 色条左边缘

# ── 字体 ──
FONT_PATHS = [
    'C:/Windows/Fonts/msyhbd.ttc',   # Microsoft YaHei Bold
    'C:/Windows/Fonts/msyh.ttc',      # Microsoft YaHei
    'C:/Windows/Fonts/simhei.ttf',    # SimHei
]
FONT_SIZE_MAJOR = 72   # 主要河流标签
FONT_SIZE_MINOR = 52   # 次要河流标签

# ── 河流名称映射 (Natural Earth name → 中文) ──
# 注意: 长江在数据中分 Jinsha(上游)、Chang Jiang(主体)、Yangtze(下游) 三段, 均映射为"长江"
# 珠江在数据中分 Xi(西江主干)、Nanpan、Hongshui、Bei、Dong 等, 主干 Xi→珠江
NAME_TO_CN = {
    'Chang Jiang': '长江',
    'Jinsha': '长江',          # 金沙江 = 长江上游
    'Yangtze': '长江',         # 长江下游/河口
    'Huang': '黄河',
    'Huang He': '黄河',
    'Songhua': '松花江',
    'Heilong Jiang': '黑龙江',
    'Amur': '黑龙江',
    'Lancang': '澜沧江',
    'Mekong': '湄公河',
    'Nu': '怒江',
    'Salween': '萨尔温江',
    'Brahmaputra': '雅鲁藏布江',
    'Yarlung': '雅鲁藏布江',
    'Tarim': '塔里木河',
    'Yarkant': '叶尔羌河',
    'Liao': '辽河',
    'Xiliao': '西辽河',
    'Huai': '淮河',
    'Hai': '海河',
    'Hong': '元江',
    'Yuan': '元江',
    'Xi': '珠江',              # 西江 = 珠江主干
    'Nanpan': '南盘江',        # 珠江上游
    'Hongshui': '红水河',      # 珠江上游
    'Bei': '北江',             # 珠江支流
    'Dong': '东江',            # 珠江支流
    'Min': '闽江',
    'Ertis': '额尔齐斯河',
    'Ertix': '额尔齐斯河',
    'Jialing': '嘉陵江',
    'Han': '汉江',
    'Wu': '乌江',
    'Yalong': '雅砻江',
    'Tuotuo': '沱沱河',           # 长江源
    'Tongtian': '通天河',         # 长江上游
    'Ganges': '恒河',
    'Indus': '印度河',
    'Ayeyarwady': '伊洛瓦底江',
    'Irrawaddy Delta': '伊洛瓦底江',
    'Ob': '鄂毕河',
    'Lena': '勒拿河',
    'Hailar': '海拉尔河',
    'Zeya': '结雅河',
    'Chulym': '丘雷姆河',
    'Vitim': '维季姆河',
    'Olëkma': '奥廖克马河',
    # ── 源数据中未翻译、用户可见的罗马名补充 ──
    'Jinsha': '金沙江',            # 长江上游, 单独标出
    'Za': '扎曲',                  # 澜沧江/湄公河上游源头(青海/西藏 94-97°E)
    'Argun': '额尔古纳河',         # 中俄界河(黑龙江上游)
    'Argun’': '额尔古纳河',
    'Dihang': '雅鲁藏布江',        # 底杭河=雅江下游(印度段)
    'Ideriyn': '伊德尔河',         # 蒙古
    'Irtysh': '额尔齐斯河',        # 英文名变体
    'Kyzyl-Khem': '克孜勒河',      # 图瓦
    'Malyy Yenisey': '小叶尼塞河',
    'Maquan': '玛曲',              # 黄河源(玛曲)
    'Nmai': '恩梅开江',            # 伊洛瓦底江源
    'Selenga': '色楞格河',         # 蒙古/俄
    'Shishhid Gol': '希什希德河',  # 蒙古
    'Verkhniy Yenisey': '上叶尼塞河',
    'Xun': '寻江',                 # 广西
    'Xiang': '湘江',               # 湖南
    # ── 第二轮补充: 源数据中漏翻的中国河流 ──
    'Fuchun': '富春江',            # 浙江
    'Gan': '赣江',                 # 江西
    'Ou': '瓯江',                  # 浙江
    'Sanggan': '桑干河',           # 永定河上游(晋冀)
    'Xar Moron': '西拉木伦河',     # 内蒙古(西辽河源)
    'Yongding': '永定河',          # 京津冀(海河系)
    'Ile': '伊犁河',               # 新疆
    'Ussuri': '乌苏里江',          # 黑龙江(中俄界河)
    'Konqi': '孔雀河',             # 新疆
    'You': '酉水',                 # 湘西北(沅江支流)
    'Yu': '郁江',                  # 广西
    'Yong': '邕江',                # 南宁(郁江上游)
}

# ── 中国主要河流白名单(决定矢量线粗细, 不依赖 NE 的 scalerank) ──
# NE 的 scalerank 是全球视角重要性排序, 不能反映中国两大母亲河等地位
# 列入此表的河流一律按"主要"渲染(粗线 2.4px + 标签)
CHINA_MAJOR = {
    '长江', '黄河', '珠江', '黑龙江', '松花江', '雅鲁藏布江', '澜沧江', '怒江',
    '淮河', '海河', '辽河', '闽江', '塔里木河', '额尔齐斯河', '元江',
    '雅砻江', '嘉陵江', '汉江', '乌江', '金沙江', '岷江', '湘江', '玛曲', '扎曲',
    '伊犁河', '乌苏里江',
}

# ── 需要标注的主要河流 (只标注这些) ──
LABEL_RIVERS = {
    '长江', '黄河', '珠江', '淮河', '海河', '辽河', '松花江', '黑龙江',
    '雅鲁藏布江', '塔里木河', '澜沧江', '怒江', '额尔齐斯河', '元江',
    '闽江',
}

# ── 河流线宽分级 (15600×9600 像素, 线宽需足够粗才可见) ──
MAJOR_WIDTH = 14    # 主要河流 (标注的): 粗线
NAMED_WIDTH = 9     # 命名支流: 中线
MINOR_WIDTH = 5     # 未命名河流: 细线

# ── 颜色 ──
COLOR_MAJOR = (20, 70, 200, 210)    # 深蓝, 高不透明度
COLOR_NAMED = (40, 110, 220, 170)   # 中蓝
COLOR_MINOR = (60, 140, 230, 120)   # 浅蓝, 低不透明度

# 标签颜色
LABEL_TEXT_COLOR = (255, 255, 255, 255)
LABEL_OUTLINE_COLOR = (0, 0, 80, 200)
LABEL_BG_COLOR = (0, 20, 60, 140)

# ── 湖泊配置 ──
# 主要湖泊 (scalerank <= 4 自动标注, 此处列出中文名映射)
# name_zh 字段已提供中文名, 无需手动映射
LAKE_LABEL_SCALERANK = 4   # scalerank <= 此值的湖泊自动标注
LAKE_FILL_COLOR = (30, 120, 180, 90)    # 湖泊填充色 (半透明蓝)
LAKE_OUTLINE_COLOR = (20, 80, 140, 180) # 湖泊轮廓色
LAKE_OUTLINE_WIDTH = 3

# 湖泊标签颜色
LAKE_LABEL_TEXT_COLOR = (255, 255, 255, 255)
LAKE_LABEL_OUTLINE_COLOR = (0, 40, 80, 200)
LAKE_LABEL_BG_COLOR = (0, 30, 80, 90)
FONT_SIZE_LAKE = max(40, int(IMG_H * 0.005))  # 湖泊标签字号, 按图片高度等比例缩放


def lonlat_to_pixel(lon, lat):
    """经纬度 → 像素坐标"""
    px = (lon - LON_MIN) / (LON_MAX - LON_MIN) * IMG_W
    py = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * IMG_H
    return (px, py)


def get_font(size):
    """获取中文字体"""
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def load_rivers():
    """加载 GeoJSON 并筛选范围内的河流"""
    with open(RIVERS_GEOJSON, encoding='utf-8') as f:
        data = json.load(f)

    rivers = []
    for feat in data['features']:
        geom = feat['geometry']
        if geom['type'] not in ('LineString', 'MultiLineString'):
            continue

        props = feat['properties']
        name = props.get('name', '') or ''
        name_en = props.get('name_en', '') or ''

        # 展开坐标
        if geom['type'] == 'LineString':
            segments = [geom['coordinates']]
        else:
            segments = geom['coordinates']

        # 筛选: 至少有一个点在范围内
        all_in_bounds = False
        for seg in segments:
            for lon, lat in seg:
                if LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX:
                    all_in_bounds = True
                    break
            if all_in_bounds:
                break
        if not all_in_bounds:
            continue

        # 裁剪每条线段到范围
        clipped_segments = []
        for seg in segments:
            clipped = []
            for lon, lat in seg:
                if LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX:
                    clipped.append((lon, lat))
                else:
                    if len(clipped) >= 2:
                        clipped_segments.append(clipped)
                    clipped = []
            if len(clipped) >= 2:
                clipped_segments.append(clipped)

        if not clipped_segments:
            continue

        # 确定中文名
        cn_name = NAME_TO_CN.get(name, '') or NAME_TO_CN.get(name_en, '')

        rivers.append({
            'name': name,
            'name_en': name_en,
            'cn_name': cn_name,
            'segments': clipped_segments,
            'total_points': sum(len(s) for s in clipped_segments),
        })

    return rivers


def load_lakes():
    """加载湖泊 shapefile 并筛选范围内的湖泊"""
    if not os.path.exists(LAKES_SHP):
        print(f'  警告: 湖泊数据不存在: {LAKES_SHP}')
        return []

    sf = shapefile.Reader(LAKES_SHP)

    lakes = []
    for i in range(len(sf.shapes())):
        rec = sf.record(i)
        geom = sf.shape(i)
        bbox = geom.bbox  # (xmin, ymin, xmax, ymax)

        # 边界判断: 是否与范围重叠
        if bbox[2] < LON_MIN or bbox[0] > LON_MAX or bbox[3] < LAT_MIN or bbox[1] > LAT_MAX:
            continue

        name = rec['name'] if rec['name'] else ''
        name_zh = rec['name_zh'] if rec['name_zh'] else ''
        scalerank = rec['scalerank']

        # 获取多边形坐标
        # shapeType 5 = Polygon
        points = geom.points
        parts = geom.parts

        # 将多边形分割为多个环 ( exterior + interiors )
        polygons = []
        for j in range(len(parts)):
            start = parts[j]
            end = parts[j + 1] if j + 1 < len(parts) else len(points)
            ring = points[start:end]
            # 过滤到范围内的坐标
            ring_in_bounds = [(lon, lat) for lon, lat in ring
                              if LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX]
            if len(ring_in_bounds) >= 3:
                polygons.append(ring_in_bounds)

        if not polygons:
            continue

        # 确定中文名
        cn_name = name_zh if name_zh else name

        lakes.append({
            'name': name,
            'name_zh': name_zh,
            'cn_name': cn_name,
            'scalerank': scalerank,
            'polygons': polygons,  # 每个元素是一个环的坐标列表
        })

    sf.close()
    return lakes


def find_label_position(segments):
    """找河流最长段的中间点作为标签位置"""
    longest = max(segments, key=len)
    mid_idx = len(longest) // 2
    return lonlat_to_pixel(longest[mid_idx][0], longest[mid_idx][1])


def draw_colorbar(base_img, vmin=0, vmax=8800):
    """在底图右侧绘制高程色标条，返回添加了色标的图像"""
    IMG_W, IMG_H = base_img.size
    CBAR_W = 260          # 色条宽度
    CBAR_PAD = 60         # 色条离右边缘的距离
    CBAR_TOP = int(IMG_H * 0.08)   # 色条顶部位置
    CBAR_BOT = int(IMG_H * 0.92)   # 色条底部位置
    CBAR_H = CBAR_BOT - CBAR_TOP

    # 字体大小按图片高度等比缩放（9600px 高 → 基准 120px）
    FONT_SIZE_TICK = max(60, int(IMG_H * 0.0125))
    FONT_SIZE_UNIT = max(48, int(IMG_H * 0.010))
    FONT_SIZE_TITLE = max(56, int(IMG_H * 0.011))

    # 14 级 terrain_custom 色阶（与 terrain_renderer.py 一致）
    colors = [
        (0.00, (43, 93, 140)),    # 深蓝 - 深水
        (0.02, (74, 138, 181)),   # 浅蓝 - 浅水
        (0.05, (127, 181, 213)),  # 极浅蓝 - 沿海
        (0.08, (179, 217, 160)),  # 浅绿 - 低地
        (0.15, (140, 197, 121)),  # 绿 - 平原
        (0.25, (107, 163, 86)),   # 深绿 - 丘陵
        (0.35, (201, 180, 88)),   # 黄绿 - 低山
        (0.45, (201, 160, 72)),   # 土黄 - 中山
        (0.55, (166, 124, 61)),   # 褐色 - 高山
        (0.65, (139, 94, 47)),    # 深褐 - 高原
        (0.75, (158, 122, 106)),  # 紫褐 - 极高山
        (0.85, (200, 184, 168)),  # 浅灰 - 雪线附近
        (0.95, (232, 221, 208)),  # 近白 - 永久积雪
        (1.00, (255, 255, 255)),  # 白色 - 雪顶
    ]

    # 创建 256 级 LUT
    lut = []
    for i in range(256):
        t = i / 255.0
        # 找到 t 所在的区间
        for j in range(len(colors) - 1):
            p0, c0 = colors[j]
            p1, c1 = colors[j + 1]
            if p0 <= t <= p1:
                frac = (t - p0) / (p1 - p0) if p1 > p0 else 0
                r = int(c0[0] + (c1[0] - c0[0]) * frac)
                g = int(c0[1] + (c1[1] - c0[1]) * frac)
                b = int(c0[2] + (c1[2] - c0[2]) * frac)
                lut.append((r, g, b))
                break
        else:
            lut.append(colors[-1][1])
    # 补齐（如果上面没覆盖到）
    while len(lut) < 256:
        lut.append(colors[-1][1])

    # 使用 base_img 作为绘图目标
    draw = ImageDraw.Draw(base_img)

    # 绘制色条（从上到下 = 高到低的归一化值）
    x0 = IMG_W - CBAR_PAD - CBAR_W
    x1 = IMG_W - CBAR_PAD
    for y in range(CBAR_TOP, CBAR_BOT):
        t = 1.0 - (y - CBAR_TOP) / CBAR_H  # 顶部 = 1.0 (雪顶), 底部 = 0.0 (深水)
        idx = min(255, max(0, int(t * 255)))
        r, g, b = lut[idx]
        draw.line([(x0, y), (x1, y)], fill=(r, g, b))

    # 边框
    draw.rectangle([x0, CBAR_TOP, x1, CBAR_BOT], outline=(0, 0, 0), width=2)

    # 刻度标签（顶部 = 高海拔 = 8800m，底部 = 低海拔 = 0m）
    font = get_font(FONT_SIZE_TICK)
    n_ticks = 9
    for i in range(n_ticks):
        frac = i / (n_ticks - 1)        # 0→1 从下到上
        elev = vmax - frac * (vmax - vmin)  # 顶部 8800, 底部 0
        y = int(CBAR_BOT - frac * CBAR_H)   # 顶部对应 CBAR_TOP, 底部对应 CBAR_BOT
        label = f'{int(elev)}'
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        # 刻度线
        draw.line([(x0 - 12, y), (x0, y)], fill=(0, 0, 0), width=3)
        # 文字（色条左侧）
        draw.text((x0 - tw - 24, y - th // 2), label, fill=(0, 0, 0), font=font)

    # 单位标签 "m"
    unit_font = get_font(FONT_SIZE_UNIT)
    draw.text((x0 - 20, CBAR_TOP - FONT_SIZE_UNIT - 20), 'm', fill=(0, 0, 0), font=unit_font)

    # 色条标题 "高程"
    title_font = get_font(FONT_SIZE_TITLE)
    # 标题竖排或横排放右侧
    title_txt = '高程'
    bbox2 = draw.textbbox((0, 0), title_txt, font=title_font)
    tw2 = bbox2[2] - bbox2[0]
    draw.text((x0 - tw2 // 2, CBAR_TOP - FONT_SIZE_TITLE - FONT_SIZE_UNIT - 40),
              title_txt, fill=(0, 0, 0), font=title_font)

    return base_img


def draw_lakes(overlay, draw, lakes):
    """在 overlay 上绘制湖泊多边形, 返回标签位置列表
    每个标签位置为 (cn_name, suggested_pos, scalerank, lake_bbox_px)
    lake_bbox_px = (pxmin, pymin, pxmax, pymax) 湖泊在像素坐标中的包围盒
    标签绘制时将根据 bbox 把文字放到湖泊侧边而不是正上方
    """
    lake_label_positions = []

    for lake in lakes:
        cn_name = lake['cn_name']
        polygons = lake['polygons']
        scalerank = lake['scalerank']

        # 绘制每个多边形环
        for poly in polygons:
            pixels = [lonlat_to_pixel(lon, lat) for lon, lat in poly]
            if len(pixels) >= 3:
                draw.polygon(pixels, fill=LAKE_FILL_COLOR)
                draw.line(pixels + [pixels[0]], fill=LAKE_OUTLINE_COLOR,
                          width=LAKE_OUTLINE_WIDTH, joint='curve')

        # 收集标签位置: 记录最大多边形的像素包围盒, 用于侧边放置标签
        if scalerank <= LAKE_LABEL_SCALERANK and cn_name:
            largest_poly = max(polygons, key=len)
            pts_px = [lonlat_to_pixel(lon, lat) for lon, lat in largest_poly]
            pxmin = min(p[0] for p in pts_px)
            pymin = min(p[1] for p in pts_px)
            pxmax = max(p[0] for p in pts_px)
            pymax = max(p[1] for p in pts_px)
            # 建议位置: 先放右侧中间 (后面绘制时再微调)
            suggested_pos = (pxmax + 10, (pymin + pymax) // 2)
            lake_label_positions.append((cn_name, suggested_pos, scalerank,
                                       (pxmin, pymin, pxmax, pymax)))

    return lake_label_positions


def draw_rivers_and_lakes(rivers, lakes):
    """在透明 overlay 上绘制河流和湖泊, 然后合成到底图上"""
    print(f'  加载底图 {BASE_PNG}...')
    Image.MAX_IMAGE_PIXELS = None
    base = Image.open(BASE_PNG).convert('RGB')
    print(f'  底图尺寸: {base.size}')

    # 创建 RGBA overlay
    overlay = Image.new('RGBA', (IMG_W, IMG_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # ── 1. 绘制湖泊 (先画, 在底层) ──
    print(f'  绘制 {len(lakes)} 个湖泊...')
    lake_label_positions = draw_lakes(overlay, draw, lakes)
    print(f'    湖泊标签: {len(lake_label_positions)} 个')

    # ── 2. 按中文名分组河流 ──
    river_groups = {}
    for river in rivers:
        cn = river['cn_name']
        if cn not in river_groups:
            river_groups[cn] = {'segments': [], 'is_major': cn in LABEL_RIVERS}
        river_groups[cn]['segments'].extend(river['segments'])

    # ── 3. 绘制河流 (在后, 在上层) ──
    sorted_cn = sorted(river_groups.keys(), key=lambda cn: (
        0 if river_groups[cn]['is_major'] else
        1 if cn else 2,
        -sum(len(s) for s in river_groups[cn]['segments'])
    ))

    drawn_count = 0
    for cn in sorted_cn:
        grp = river_groups[cn]
        is_major = grp['is_major']
        is_named = bool(cn)
        width = MAJOR_WIDTH if is_major else (NAMED_WIDTH if is_named else MINOR_WIDTH)
        color = COLOR_MAJOR if is_major else (COLOR_NAMED if is_named else COLOR_MINOR)
        for seg in grp['segments']:
            pixels = [lonlat_to_pixel(lon, lat) for lon, lat in seg]
            if len(pixels) >= 2:
                draw.line(pixels, fill=color, width=width, joint='curve')
                drawn_count += 1

    # ── 4. 放置河流标签 ──
    label_positions = {}
    for cn, grp in river_groups.items():
        if not grp['is_major'] or cn in label_positions:
            continue
        longest_seg = max(grp['segments'], key=len)
        mid_idx = len(longest_seg) // 2
        pos = lonlat_to_pixel(longest_seg[mid_idx][0], longest_seg[mid_idx][1])
        label_positions[cn] = pos

    print(f'  绘制了 {drawn_count} 条河段, {len(label_positions)} 个河流标签')

    # ── 5. 绘制河流标签 ──
    font_major = get_font(FONT_SIZE_MAJOR)
    outline_w = max(2, int(IMG_H * 0.000417))
    label_pad = max(12, int(FONT_SIZE_MAJOR * 0.25))
    label_radius = max(8, int(FONT_SIZE_MAJOR * 0.167))
    for cn_name, (x, y) in label_positions.items():
        bbox = draw.textbbox((0, 0), cn_name, font=font_major)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rounded_rectangle([x-tw//2-label_pad, y-th//2-label_pad,
                                x+tw//2+label_pad, y+th//2+label_pad],
                                radius=label_radius, fill=LABEL_BG_COLOR)
        offsets = [(-outline_w,0),(outline_w,0),(0,-outline_w),(0,outline_w),
                   (-outline_w,-outline_w),(outline_w,outline_w),
                   (-outline_w,outline_w),(outline_w,-outline_w)]
        for dx, dy in offsets:
            draw.text((x-tw//2+dx, y-th//2+dy), cn_name,
                      fill=LABEL_OUTLINE_COLOR, font=font_major)
        draw.text((x-tw//2, y-th//2), cn_name, fill=LABEL_TEXT_COLOR, font=font_major)

    # ── 6. 绘制湖泊标签 ──
    font_lake = get_font(FONT_SIZE_LAKE)
    outline_w = max(2, int(IMG_H * 0.000417))
    label_pad = max(4, int(FONT_SIZE_LAKE * 0.125))
    label_radius = max(4, int(FONT_SIZE_LAKE * 0.083))
    label_gap = max(8, int(FONT_SIZE_LAKE * 0.2))
    cbar_left = IMG_W - CBAR_PAD - CBAR_W
    # 按 scalerank 排序 (重要的先画, 后画的在上层)
    for item in sorted(lake_label_positions, key=lambda x: x[2]):
        cn_name, _, sr, (pxmin, pymin, pxmax, pymax) = item
        bbox = draw.textbbox((0, 0), cn_name, font=font_lake)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        yc = (pymin + pymax) // 2  # 湖泊垂直中心

        # 尝试放右侧
        x_right = pxmax + label_gap
        # 检查右侧是否有足够空间 (不超出色条)
        if x_right + tw + label_pad <= cbar_left - 10:
            x = x_right
        else:
            # 尝试放左侧
            x_left = pxmin - label_gap - tw
            if x_left - label_pad >= 0:
                x = x_left
            else:
                # fallback: 放湖泊上方中间
                x = max(label_pad, min(pxmin, IMG_W - tw - label_pad - 60))
                yc = max(pymin - th - label_gap, label_pad)

        draw.rounded_rectangle([x-label_pad, yc-th//2-label_pad,
                                x+tw+label_pad, yc+th//2+label_pad],
                                radius=label_radius, fill=LAKE_LABEL_BG_COLOR)
        offsets = [(-outline_w,0),(outline_w,0),(0,-outline_w),(0,outline_w),
                   (-outline_w,-outline_w),(outline_w,outline_w),
                   (-outline_w,outline_w),(outline_w,-outline_w)]
        for dx, dy in offsets:
            draw.text((x+dx, yc-th//2+dy), cn_name,
                      fill=LAKE_LABEL_OUTLINE_COLOR, font=font_lake)
        draw.text((x, yc-th//2), cn_name, fill=LAKE_LABEL_TEXT_COLOR, font=font_lake)

    print(f'  绘制了 {len(lake_label_positions)} 个湖泊标签')

    # ── 7. 合成 ──
    print('  合成图层...')
    base_rgba = base.convert('RGBA')
    result = Image.alpha_composite(base_rgba, overlay)
    result = result.convert('RGB')

    # 绘制高程色标条
    print('  绘制高程色标条...')
    result = draw_colorbar(result, vmin=0, vmax=8800)

    # 保存
    combined_path = os.path.join(OUTPUT_DIR, 'china_rivers_lakes_overlay.png')
    overlay_only_path = os.path.join(OUTPUT_DIR, 'china_rivers_lakes_overlay_layer.png')

    print(f'  保存合成图 → {combined_path}')
    result.save(combined_path, 'PNG')

    print(f'  保存纯图层 → {overlay_only_path}')
    overlay.save(overlay_only_path, 'PNG')

    del base_rgba, result, base, overlay, draw
    return combined_path, overlay_only_path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print('=== 中国主要江河+湖泊覆盖图层生成器 ===')
    print()

    print('1. 加载河流数据...')
    rivers = load_rivers()
    print(f'   范围内河流总数: {len(rivers)}')
    major = [r for r in rivers if r['cn_name'] in LABEL_RIVERS]
    print(f'   主要河流 (将标注): {len(major)}')

    print()
    print('2. 加载湖泊数据...')
    lakes = load_lakes()
    print(f'   范围内湖泊总数: {len(lakes)}')
    major_lakes = [l for l in lakes if l['scalerank'] <= LAKE_LABEL_SCALERANK and l['cn_name']]
    print(f'   主要湖泊 (将标注, scalerank<={LAKE_LABEL_SCALERANK}): {len(major_lakes)}')
    for l in sorted(major_lakes, key=lambda x: x['scalerank']):
        print(f'     [{l["scalerank"]}] {l["cn_name"]} ({l["name"]})')

    print()
    print('3. 绘制河流+湖泊图层...')
    combined, layer = draw_rivers_and_lakes(rivers, lakes)

    print()
    print('=== 完成 ===')
    print(f'  合成图: {combined}')
    print(f'  纯图层: {layer}')


if __name__ == '__main__':
    main()
