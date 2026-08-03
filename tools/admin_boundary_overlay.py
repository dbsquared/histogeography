#!/usr/bin/env python3
"""
中国省级行政边界图层生成器（简化版 v2）

只绘制省级边界线（红色）和省份中文标注。
不包含国界线、十段线、南海附图。

改进: 省名标注位置通过可视化方式手动指定像素坐标, 确保标签在各省内部空旷处。

数据来源: Natural Earth 10m admin_1_states_provinces (public domain)

输出:
  - rendered/china_admin_overlay.png        合成图
  - rendered/china_admin_overlay_layer.png  透明图层 (RGBA)
  - rendered/china_admin_overlay_preview.jpg 预览图

用法:
  python admin_boundary_overlay.py
  python admin_boundary_overlay.py --base XYZ.png
  python admin_boundary_overlay.py --debug-positions  # 输出各省当前标签位置, 用于手动调整
"""

import os
import sys
import math
import zipfile
import shapefile
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ── 路径配置 ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'admin')
BASE_PNG = os.path.join(BASE_DIR, 'rendered/china_full_v3.png')
OUTPUT_DIR = os.path.join(BASE_DIR, 'rendered')

# Natural Earth 10m 行政边界数据
ADMIN1_URL = 'https://naciscdn.org/naturalearth/10m/cultural/ne_10m_admin_1_states_provinces.zip'
ADMIN1_ZIP = os.path.join(DATA_DIR, 'ne_10m_admin_1_states_provinces.zip')
ADMIN1_SHP = os.path.join(DATA_DIR, 'ne_10m_admin_1_states_provinces.shp')

# ── 地图范围 (与 rendered/china_full_v3.png 一致) ──
LON_MIN, LON_MAX = 75.0, 140.0
LAT_MIN, LAT_MAX = 15.0, 55.0
IMG_W, IMG_H = 15600, 9600

# ── 字体 ──
FONT_PATHS = [
    'C:/Windows/Fonts/msyhbd.ttc',
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/simhei.ttf',
]
FONT_SIZE_PROV = 90   # 省份标签字号 (调大)

# ── 省界线样式: 红色实线 ──
PROV_BORDER_COLOR = (200, 20, 20, 240)   # 红色, 近不透明
PROV_BORDER_WIDTH = 7                     # 线宽 (像素), 加粗

# ── 省份标注样式 ──
PROV_LABEL_TEXT_COLOR = (255, 255, 255, 255)   # 白色文字
PROV_LABEL_OUTLINE_COLOR = (30, 30, 30, 200)   # 深灰描边

# ── 省份中文名映射 ──
PROV_NAME_TO_CN = {
    'Anhui': '安徽',        'Beijing': '北京',       'Chongqing': '重庆',
    'Fujian': '福建',       'Gansu': '甘肃',        'Guangdong': '广东',
    'Guangxi': '广西',      'Guizhou': '贵州',       'Hainan': '海南',
    'Hebei': '河北',        'Heilongjiang': '黑龙江', 'Henan': '河南',
    'Hong Kong': '香港',    'Hubei': '湖北',        'Hunan': '湖南',
    'Inner Mongolia': '内蒙古', 'Jiangsu': '江苏',    'Jiangxi': '江西',
    'Jilin': '吉林',        'Liaoning': '辽宁',      'Macau': '澳门',
    'Ningxia': '宁夏',      'Qinghai': '青海',       'Shaanxi': '陕西',
    'Shandong': '山东',      'Shanghai': '上海',      'Shanxi': '山西',
    'Sichuan': '四川',      'Tianjin': '天津',       'Xinjiang': '新疆',
    'Xizang': '西藏',       'Taiwan': '台湾',        'Yunnan': '云南',
    'Zhejiang': '浙江',
    # NE name 字段
    'Anhui Sheng': '安徽',  'Beijing Shi': '北京',   'Chongqing Shi': '重庆',
    'Fujian Sheng': '福建', 'Gansu Sheng': '甘肃',  'Guangdong Sheng': '广东',
    'Guangxi Zhuangzu Zizhiqu': '广西', 'Guizhou Sheng': '贵州',
    'Hainan Sheng': '海南',  'Hebei Sheng': '河北',
    'Heilongjiang Sheng': '黑龙江', 'Henan Sheng': '河南',
    'Hubei Sheng': '湖北',  'Hunan Sheng': '湖南',
    'Nei Mongol': '内蒙古',  'Jiangsu Sheng': '江苏', 'Jiangxi Sheng': '江西',
    'Jilin Sheng': '吉林',  'Liaoning Sheng': '辽宁',
    'Ningxia Huizu Zizhiqu': '宁夏', 'Qinghai Sheng': '青海',
    'Shaanxi Sheng': '陕西', 'Shandong Sheng': '山东',
    'Shanghai Shi': '上海',  'Shanxi Sheng': '山西', 'Sichuan Sheng': '四川',
    'Tianjin Shi': '天津',
    'Xinjiang Uygur Zizhiqu': '新疆', 'Xizang Zizhiqu': '西藏',
    'Yunnan Sheng': '云南', 'Zhejiang Sheng': '浙江',
    # 中文名直接映射
    '安徽省': '安徽',       '北京市': '北京',        '重庆市': '重庆',
    '福建省': '福建',       '甘肃省': '甘肃',        '广东省': '广东',
    '广西壮族自治区': '广西', '贵州省': '贵州',        '海南省': '海南',
    '河北省': '河北',       '黑龙江省': '黑龙江',    '河南省': '河南',
    '湖北省': '湖北',       '湖南省': '湖南',        '内蒙古自治区': '内蒙古',
    '江苏省': '江苏',       '江西省': '江西',        '吉林省': '吉林',
    '辽宁省': '辽宁',       '宁夏回族自治区': '宁夏', '青海省': '青海',
    '陕西省': '陕西',       '山东省': '山东',        '上海市': '上海',
    '山西省': '山西',       '四川省': '四川',        '天津市': '天津',
    '新疆维吾尔自治区': '新疆', '西藏自治区': '西藏',    '台湾省': '台湾',
    '云南省': '云南',       '浙江省': '浙江',        '香港特别行政区': '香港',
    '澳门特别行政区': '澳门', '台湾': '台湾',
}


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


def ensure_data():
    """下载 Natural Earth admin_1 数据"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if not os.path.exists(ADMIN1_SHP):
        print(f"下载 admin_1 数据: {ADMIN1_URL}")
        import urllib.request
        urllib.request.urlretrieve(ADMIN1_URL, ADMIN1_ZIP)
        with zipfile.ZipFile(ADMIN1_ZIP, 'r') as zf:
            zf.extractall(DATA_DIR)
        print(f"  解压完成: {DATA_DIR}")


def load_china_provinces():
    """
    加载中国各省边界。

    Natural Earth admin_1: admin = 'China' 的记录。
    返回: [{'name_cn': ..., 'borders': [...], 'centroid': (lon,lat)}, ...]
    """
    sf = shapefile.Reader(ADMIN1_SHP, encoding='utf-8')
    provinces = []

    for rec, shape in zip(sf.records(), sf.shapes()):
        admin0 = (rec['admin'] or rec['admin0'] or '').strip()
        if admin0 != 'China':
            continue

        # 获取省份中文名
        prov_name_en = rec['name_en'] or ''
        prov_name_local = rec['name'] or rec['name_local'] or ''
        prov_name = (PROV_NAME_TO_CN.get(prov_name_local)
                     or PROV_NAME_TO_CN.get(prov_name_en)
                     or prov_name_local
                     or prov_name_en)

        if not prov_name:
            continue

        # 过滤非省级 (南海诸岛等)
        if 'Island' in prov_name or 'Islands' in prov_name:
            continue

        # centroid: 用 shape.bbox 中心
        bbox = shape.bbox
        centroid_lon = (bbox[0] + bbox[2]) / 2
        centroid_lat = (bbox[1] + bbox[3]) / 2

        # 边界线段 (筛选在范围内的部分)
        borders = []
        points = shape.points
        parts = list(shape.parts) + [len(points)]

        for i in range(len(parts) - 1):
            seg = points[parts[i]:parts[i + 1]]
            filtered = [(lon, lat) for lon, lat in seg
                        if LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX]
            if len(filtered) >= 2:
                borders.append(filtered)

        if borders:
            provinces.append({
                'name_cn': prov_name,
                'name_en': prov_name_en,
                'borders': borders,
                'centroid': (centroid_lon, centroid_lat),
            })

    sf.close()

    # 确保台湾省在列表中 (NE 可能放在 admin_0 而非 admin_1)
    taiwan_names = {'Taiwan', '台湾', '台湾省'}
    has_taiwan = any(p['name_cn'] in taiwan_names for p in provinces)
    if not has_taiwan:
        print("  提示: 补充台湾省边界...")
        _add_taiwan(provinces)

    return provinces


def _add_taiwan(provinces):
    """用 admin_0 数据补充台湾省边界"""
    try:
        sf = shapefile.Reader(
            os.path.join(DATA_DIR, 'ne_10m_admin_0_countries.shp'),
            encoding='utf-8')
        for rec, shape in zip(sf.records(), sf.shapes()):
            name = (rec['SOVEREIGNT'] or rec['ADMIN'] or '').strip()
            if name == 'Taiwan':
                borders = []
                points = shape.points
                parts = list(shape.parts) + [len(points)]
                for i in range(len(parts) - 1):
                    seg = points[parts[i]:parts[i + 1]]
                    filtered = [(lon, lat) for lon, lat in seg
                                if LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX]
                    if len(filtered) >= 2:
                        borders.append(filtered)
                if borders:
                    provinces.append({
                        'name_cn': '台湾',
                        'name_en': 'Taiwan',
                        'borders': borders,
                        'centroid': (121.0, 23.7),
                    })
                    print("    已添加台湾省")
                    break
        sf.close()
    except Exception as e:
        print(f"    补充台湾边界失败: {e}")


# ── 省份标注固定像素位置 ──
# 基于 NE 数据 bbox center 计算:
#   px = (lon - 75) / 65 * 15600,  py = (55 - lat) / 40 * 9600
# 只对有问题的省份做微调 (河北: 从 3758 下调到 3900, 避开北京/天津区域)
LABEL_POS = {
    '上海': (11141, 5696),
    '云南': (6445, 7157),
    '内蒙古': (8789, 3014),   # 往下移 300px (从 2714 → 3014)
    '北京': (9949, 3541),
    '台湾': (11034, 7536),    # 往西移 100px
    '吉林': (12351, 2741),
    '四川': (6706, 5959),
    '天津': (10163, 3742),
    '宁夏': (7442, 4244),
    '安徽': (10140, 5513),
    '山东': (10502, 4464),
    '山西': (8973, 4160),
    '广东': (9220, 7509),     # 往下移 200px (从 7309 → 7509)
    '广西': (7984, 7510),
    '新疆': (2396, 3179),
    '江苏': (10596, 5094),    # 往下移 200px (从 4894 → 5094)
    '江西': (9844, 6653),
    '河北': (9794, 3900),     # 往右移 300px (从 9494 → 9794)
    '河南': (9236, 5068),
    '浙江': (10863, 6196),
    '海南': (8357, 8600),
    '湖北': (8943, 5720),
    '湖南': (8762, 6631),
    '甘肃': (6676, 4154),     # 往右移 500px
    '福建': (10352, 6972),
    '西藏': (3298, 5547),
    '贵州': (7574, 6734),
    '辽宁': (11553, 3336),   # 往东移 200px
    '重庆': (7855, 5953),
    '陕西': (8207, 4645),     # 再往东移 100px
    '青海': (5097, 4696),
    '黑龙江': (12712, 1559),
}


def draw_province_borders(draw, provinces):
    """绘制省界线 — 红色实线"""
    for prov in provinces:
        for segment in prov['borders']:
            pixels = [lonlat_to_pixel(lon, lat) for lon, lat in segment]
            pixels = [(px, py) for px, py in pixels
                      if 0 <= px <= IMG_W and 0 <= py <= IMG_H]
            if len(pixels) < 2:
                continue
            for i in range(len(pixels) - 1):
                draw.line([pixels[i], pixels[i + 1]],
                          fill=PROV_BORDER_COLOR,
                          width=PROV_BORDER_WIDTH)


def draw_province_labels(draw, provinces):
    """绘制省份中文标注 (使用手动调整的固定像素位置)"""
    font = get_font(FONT_SIZE_PROV)

    for prov in provinces:
        # 使用手动调整的固定位置
        pos = LABEL_POS.get(prov['name_cn'])
        if pos:
            px, py = pos
        else:
            # fallback: 用 centroid
            lon, lat = prov['centroid']
            px, py = lonlat_to_pixel(lon, lat)

        label = prov['name_cn']
        bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x = px - tw / 2
        y = py - th / 2

        # 文字描边 (先画4个方向的描边, 再画白色文字)
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-2, -2), (2, -2), (-2, 2), (2, 2)]:
            draw.text((x + dx, y + dy), label, fill=PROV_LABEL_OUTLINE_COLOR, font=font)
        draw.text((x, y), label, fill=PROV_LABEL_TEXT_COLOR, font=font)


def debug_label_positions(provinces):
    """打印各省标签位置, 用于手动调整 LABEL_POS"""
    print("当前各省标签位置 (复制到 LABEL_POS 字典中手动调整):")
    print("LABEL_POS = {")
    for prov in provinces:
        lon, lat = prov['centroid']
        px, py = lonlat_to_pixel(lon, lat)
        print(f"    '{prov['name_cn']}': ({int(px)}, {int(py)}),  # bbox center")
    print("}")


def main():
    parser = argparse.ArgumentParser(description='中国省级行政边界图层生成器（简化版 v2）')
    parser.add_argument('--base', default=BASE_PNG, help='底图 PNG 路径')
    parser.add_argument('--output', default=None, help='输出 PNG 路径前缀')
    parser.add_argument('--debug-positions', action='store_true', help='打印各省标签位置, 用于手动调整')
    args = parser.parse_args()

    ensure_data()

    print("加载中国省界...")
    provinces = load_china_provinces()
    print(f"  省份数: {len(provinces)}")

    if args.debug_positions:
        debug_label_positions(provinces)
        return

    for p in provinces:
        print(f"    {p['name_cn']} ({p['name_en']})")

    # 透明图层
    overlay = Image.new('RGBA', (IMG_W, IMG_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    print("绘制省界线（红色）...")
    draw_province_borders(draw, provinces)

    print("绘制省份标注...")
    draw_province_labels(draw, provinces)

    # 合成
    base = Image.open(args.base).convert('RGBA')
    composite = Image.alpha_composite(base, overlay)
    composite = composite.convert('RGB')

    # 保存
    if args.output is None:
        out_layer = os.path.join(OUTPUT_DIR, 'china_admin_overlay_layer.png')
        out_composite = os.path.join(OUTPUT_DIR, 'china_admin_overlay.png')
        out_preview = os.path.join(OUTPUT_DIR, 'china_admin_overlay_preview.jpg')
    else:
        out_composite = args.output
        out_layer = args.output.replace('.png', '_layer.png')
        out_preview = args.output.replace('.png', '_preview.jpg')

    composite.save(out_composite, 'PNG')
    print(f"合成图: {out_composite}")

    overlay.save(out_layer, 'PNG')
    print(f"透明图层: {out_layer}")

    # 预览
    preview_w = 2400
    preview_h = int(preview_w * IMG_H / IMG_W)
    preview = composite.resize((preview_w, preview_h), Image.LANCZOS)
    preview.save(out_preview, 'JPEG', quality=92)
    print(f"预览图: {out_preview}")

    print("完成!")


if __name__ == '__main__':
    main()
