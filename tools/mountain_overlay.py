# -*- coding: utf-8 -*-
"""
中国主要山脉覆盖图层生成器 (v1 预览版)
在 rendered/china_full_v3.png 地形图上叠加主要山脉图层, 用"梳齿(hachure)"短笔触
垂直于山脉主方向(走向)来表现走向, 并沿主轴画带箭头的中心线明确走向。

数据源: Natural Earth 10m geography_regions_polys (FEATURECLA='Range/mtn', public domain)
        + 手工补齐 NE 缺失的 9 条主要山脉(横断/巫山/雪峰/贺兰/长白/台湾/唐古拉/念青唐古拉/燕山)
地形底图: rendered/china_full_v3.png (75°E-140°E / 15°N-55°N)
输出: rendered/china_mountains_preview.png (合成预览, 降采样) + china_mountains_overlay_layer.png (透明图层)
"""
import os, math
import numpy as np
import shapefile
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_PNG = os.path.join(BASE_DIR, 'rendered/china_full_v3.png')
NE_SHP = os.path.join(BASE_DIR, 'data', 'mountains', 'ne_10m_geography_regions_polys.shp')
OUTPUT_DIR = os.path.join(BASE_DIR, 'rendered')

# 预览分辨率 (全分辨率 15600x9600 的 1/4, 比例一致 1.625)
PREVIEW_W, PREVIEW_H = 3900, 2400
LON_MIN, LON_MAX = 75.0, 140.0
LAT_MIN, LAT_MAX = 15.0, 55.0

FONT_PATHS = [
    'C:/Windows/Fonts/msyhbd.ttc',
    'C:/Windows/Fonts/msyh.ttc',
    'C:/Windows/Fonts/simhei.ttf',
]
FONT_LABEL = 30

# 配色: 近黑中性墨色, 避开黄/绿/蓝/橙, 在地形绿/棕、水系蓝上均高反差
HAchure = (30, 30, 32, 230)      # 梳齿笔触 (近黑墨)
OUTLINE = (14, 14, 16, 245)      # 轮廓 (更黑)
CENTER  = (95, 95, 100, 230)     # 走向中心线 + 箭头 (中性中灰, 与梳齿区分)
LABEL_TXT = (255, 255, 255, 255)
LABEL_OUT = (10, 10, 12, 245)

# 梳齿参数 (预览像素)
HAchure_LEN = 13      # 笔触长度
HAchure_GAP = 15      # 笔触间距(网格)
OUTLINE_W = 2
CENTER_W = 2
ARROW = 9

# ---- Natural Earth 白名单: 中国主要山脉 + 关键边境山脉 (按 NAME_EN) ----
NE_WHITELIST = {
    'Dabie Mountains': '大别山',
    'Greater Khingan': '大兴安岭',
    'Himalayas': '喜马拉雅山脉',
    'Kunlun Mountains': '昆仑山脉',
    'Lesser Khingan': '小兴安岭',
    'Lüliang Mountains': '吕梁山',
    'Nanling Mountains': '南岭',
    'Qilian Mountains': '祁连山',
    'Qinling': '秦岭',
    'Taihang Mountains': '太行山',
    'Tian Shan': '天山山脉',
    'Wuyi Mountains': '武夷山脉',
    'Yin Mountains': '阴山',
    'Altai Mountains': '阿尔泰山脉',
    'Dalou Mountains': '大娄山',
    'Karakoram': '喀喇昆仑山脉',
    'Pamir mountains': '帕米尔高原',
    'Altyn-Tagh': '阿尔金山',
}

# ---- 手工补齐 NE 缺失的主要山脉 (简化多边形, 沿已知走向) ----
HAND_RANGES = [
    ('横断山脉', [(97.0,25.0),(101.5,25.5),(101.0,32.0),(97.5,32.0)]),
    ('巫山',     [(107.8,30.2),(110.6,30.8),(110.9,31.6),(107.5,31.0)]),
    ('雪峰山',   [(109.4,27.0),(112.0,27.6),(112.2,28.6),(109.6,28.0)]),
    ('贺兰山',   [(105.6,38.2),(106.4,38.4),(106.5,39.4),(105.7,39.2)]),
    ('长白山',   [(126.6,41.4),(128.6,41.2),(130.0,42.0),(127.8,42.9)]),
    ('台湾山脉', [(120.7,22.0),(121.3,22.2),(121.9,24.5),(121.3,24.4)]),
    ('唐古拉山脉',[(88.5,32.8),(93.5,32.5),(93.8,33.6),(88.8,33.9)]),
    ('念青唐古拉山脉',[(87.5,29.8),(93.5,29.5),(93.8,30.6),(87.8,30.9)]),
    ('燕山',     [(114.5,40.3),(119.5,40.5),(120.0,41.3),(115.0,41.1)]),
]

def lonlat_to_pixel(lon, lat):
    px = (lon - LON_MIN) / (LON_MAX - LON_MIN) * PREVIEW_W
    py = (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * PREVIEW_H
    return (px, py)

def get_font(size):
    for p in FONT_PATHS:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def load_ne_ranges():
    sf = shapefile.Reader(NE_SHP)
    out = []
    for i in range(len(sf.shapes())):
        d = sf.record(i).as_dict()
        if d['FEATURECLA'] != 'Range/mtn':
            continue
        en = d.get('NAME_EN') or ''
        if en not in NE_WHITELIST:
            continue
        geom = sf.shape(i)
        parts = geom.parts
        pts = geom.points
        rings = []
        for j in range(len(parts)):
            start = parts[j]
            end = parts[j + 1] if j + 1 < len(parts) else len(pts)
            rings.append(pts[start:end])
        out.append({'name': NE_WHITELIST[en], 'rings': rings})
    sf.close()
    return out

def all_pixels(rings):
    px = []
    for ring in rings:
        for lon, lat in ring:
            if LON_MIN <= lon <= LON_MAX and LAT_MIN <= lat <= LAT_MAX:
                px.append(lonlat_to_pixel(lon, lat))
    return px

def compute_trend(pixels):
    """PCA 求主方向(走向). 返回 (centroid, major_vec, perp_vec, (pmin,pmax)投影范围)"""
    P = np.array(pixels, dtype=float)
    c = P.mean(0)
    X = P - c
    cov = X.T @ X / len(X)
    w, v = np.linalg.eigh(cov)
    maj = v[:, np.argmax(w)]
    perp = np.array([-maj[1], maj[0]])
    proj = X @ maj
    return c, maj, perp, (proj.min(), proj.max())

def draw_range(draw, overlay, name, rings, label_anchor=None):
    pixels = all_pixels(rings)
    if len(pixels) < 4:
        return
    c, maj, perp, (pmin, pmax) = compute_trend(pixels)
    # 包围盒
    xs = [p[0] for p in pixels]; ys = [p[1] for p in pixels]
    x0, x1 = int(min(xs)) - 4, int(max(xs)) + 4
    y0, y1 = int(min(ys)) - 4, int(max(ys)) + 4
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(PREVIEW_W, x1), min(PREVIEW_H, y1)

    # 1) 面掩膜 (用于裁剪梳齿)
    mask = Image.new('L', (PREVIEW_W, PREVIEW_H), 0)
    md = ImageDraw.Draw(mask)
    for ring in rings:
        rp = [lonlat_to_pixel(lon, lat) for lon, lat in ring]
        if len(rp) >= 3:
            md.polygon(rp, fill=255)

    # 2) 梳齿笔触 (垂直于走向) 画在临时层再按掩膜裁剪
    hc = Image.new('RGBA', (PREVIEW_W, PREVIEW_H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(hc)
    half = HAchure_LEN / 2.0
    y = y0
    while y <= y1:
        x = x0
        while x <= x1:
            if mask.getpixel((int(x), int(y))):
                p1 = (x - perp[0] * half, y - perp[1] * half)
                p2 = (x + perp[0] * half, y + perp[1] * half)
                hd.line([p1, p2], fill=HAchure, width=2)
            x += HAchure_GAP
        y += HAchure_GAP
    hc = Image.composite(hc, Image.new('RGBA', (PREVIEW_W, PREVIEW_H), (0, 0, 0, 0)), mask)
    overlay.alpha_composite(hc)

    # 3) 轮廓
    for ring in rings:
        rp = [lonlat_to_pixel(lon, lat) for lon, lat in ring]
        if len(rp) >= 3:
            draw.line(rp + [rp[0]], fill=OUTLINE, width=OUTLINE_W, joint='curve')

    # 4) 走向中心线 + 箭头
    e1 = (c[0] + maj[0] * pmax, c[1] + maj[1] * pmax)
    e2 = (c[0] + maj[0] * pmin, c[1] + maj[1] * pmin)
    draw.line([e1, e2], fill=CENTER, width=CENTER_W)
    for e in (e1, e2):
        # 箭头: 在端点处沿 -maj 方向张开
        bx, by = e[0] - maj[0] * ARROW, e[1] - maj[1] * ARROW
        a1 = (bx + perp[0] * ARROW * 0.7, by + perp[1] * ARROW * 0.7)
        a2 = (bx - perp[0] * ARROW * 0.7, by - perp[1] * ARROW * 0.7)
        draw.line([e, a1], fill=CENTER, width=CENTER_W)
        draw.line([e, a2], fill=CENTER, width=CENTER_W)

    # 5) 标签 (仅描边, 无底色)
    if label_anchor is None:
        label_anchor = (c[0], c[1])
    font = get_font(FONT_LABEL)
    bb = draw.textbbox((0, 0), name, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    lx, ly = label_anchor[0] - tw / 2, label_anchor[1] - th / 2
    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,2),(-2,2),(2,-2)]:
        draw.text((lx + dx, ly + dy), name, fill=LABEL_OUT, font=font)
    draw.text((lx, ly), name, fill=LABEL_TXT, font=font)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print('=== 中国主要山脉图层生成器 (v1 预览) ===')
    ne = load_ne_ranges()
    print(f'Natural Earth 纳入: {len(ne)} 条')
    ranges = ne + [{'name': n, 'rings': [poly]} for n, poly in HAND_RANGES]
    print(f'含手工补齐后共: {len(ranges)} 条山脉')

    print('加载底图并降采样...')
    Image.MAX_IMAGE_PIXELS = None
    base = Image.open(BASE_PNG).convert('RGB').resize((PREVIEW_W, PREVIEW_H))
    print(f'底图预览尺寸: {base.size}')

    overlay = Image.new('RGBA', (PREVIEW_W, PREVIEW_H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for r in ranges:
        draw_range(draw, overlay, r['name'], r['rings'])

    # 合成
    result = Image.alpha_composite(base.convert('RGBA'), overlay).convert('RGB')

    # 角落署名 (仅描边)
    font = get_font(22)
    note = '山脉: Natural Earth 10m · 梳齿示走向'
    nb = draw.textbbox((0, 0), note, font=font)
    nx, ny = 14, PREVIEW_H - (nb[3] - nb[1]) - 14
    for dx, dy in [(-2,0),(2,0),(0,-2),(0,2)]:
        draw.text((nx + dx, ny + dy), note, fill=(0, 0, 0, 220), font=font)
    draw.text((nx, ny), note, fill=(255, 255, 255, 230), font=font)

    combined = os.path.join(OUTPUT_DIR, 'china_mountains_preview.png')
    layer = os.path.join(OUTPUT_DIR, 'china_mountains_overlay_layer.png')
    result.save(combined, 'PNG')
    overlay.save(layer, 'PNG')
    print(f'合成预览 → {combined}')
    print(f'透明图层 → {layer}')

if __name__ == '__main__':
    main()
