# -*- coding: utf-8 -*-
"""
v6 矢量边界提取 — 分州图高亮区域生长法
==========================================
对每个州的 分州图，在历史治所坐标采样高亮填充色，
用颜色距离+暗线阻隔做区域生长，提取连通分量作为该州掩膜。
轮廓经 Douglas-Peucker 简化后映射到底图坐标链。

坐标链：ji_px(2020x1418) → ÷scale → zhi(9933x7015) → affine→WGS84 → linear→base(15600x9600)
"""

import json, os, time, sys, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import label as nlabel, binary_dilation
from skimage.measure import find_contours, approximate_polygon

# ── 路径 ──
BASE_DIR = r'E:\projects\3D地图制作'
LEGEND_DIR = os.path.join(BASE_DIR, '汉末十三州地图范例')
BASE_IMG = os.path.join(BASE_DIR, 'china_full_v3.png')
OUT_DIR = os.path.join(BASE_DIR, 'rendered')
GCP_FILE = os.path.join(BASE_DIR, 'gcp_calibration.json')

def log(msg):
    print(msg); sys.stdout.flush()

# ── GCP 坐标变换参数 ──
CAL = json.load(open(GCP_FILE, encoding='utf-8'))
a = CAL['transform_forward']['lon']['a']
b = CAL['transform_forward']['lon']['b']
c = CAL['transform_forward']['lon']['c']
d = CAL['transform_forward']['lat']['d']
e = CAL['transform_forward']['lat']['e']
f_val = CAL['transform_forward']['lat']['f']
Ai = CAL['transform_inverse_zhi']['px_A']
Bi = CAL['transform_inverse_zhi']['px_B']
Ci = CAL['transform_inverse_zhi']['px_C']
Di = CAL['transform_inverse_zhi']['py_D']
Ei = CAL['transform_inverse_zhi']['py_E']
Fi = CAL['transform_inverse_zhi']['py_F']
sx = CAL['scale_zhi_to_ji']['x']   # ~0.2034
sy = CAL['scale_zhi_to_ji']['y']   # ~0.2021

LON_MIN, LON_MAX = 75.0, 140.0
LAT_MAX, LAT_MIN = 55.0, 15.0
BASE_W, BASE_H = 15600, 9600

def zhi_to_wgs84(zx, zy):
    return a * zx + b * zy + c, d * zx + e * zy + f_val

def wgs84_to_base(lon, lat):
    px = ((lon - LON_MIN) / (LON_MAX - LON_MIN)) * BASE_W
    py = ((lat - LAT_MAX) / (LAT_MIN - LAT_MAX)) * BASE_H
    return px, py

def wgs84_to_ji(lon, lat):
    zx = Ai * lon + Bi * lat + Ci
    zy = Di * lon + Ei * lat + Fi
    return zx * sx, zy * sy

def ji_to_wgs84(jx, jy):
    return zhi_to_wgs84(jx / sx, jy / sy)

def ji_to_base(jx, jy):
    lon, lat = ji_to_wgs84(jx, jy)
    return wgs84_to_base(lon, lat)


# ── 十三州定义：(州名, 治所名, 经度, 纬度) — 东汉末年/三国初期 ──
STATES = [
    ('凉州', '武威',  102.63, 37.93),
    ('司隶', '洛阳',  112.45, 34.62),
    ('并州', '晋阳',  112.55, 37.87),
    ('冀州', '鄴',    114.50, 36.10),
    ('幽州', '蓟',    116.40, 39.90),
    ('青州', '临淄',  118.30, 36.82),
    ('兖州', '昌邑',  115.40, 35.58),
    ('徐州', '彭城',  117.18, 34.27),
    ('豫州', '许',    113.90, 34.02),
    ('扬州', '寿春',  116.80, 32.62),   # 用户指定
    ('荆州', '襄阳',  112.13, 32.02),   # 四治所之一
    ('益州', '成都',  104.07, 30.67),
    ('交州', '番禺',  113.26, 23.13),
]

# 州名 → 分州图文件名映射
STATE_FILES = {
    '凉州': '凉州.png', '司隶': '司隶.png', '并州': '并州.png',
    '冀州': '冀州.png', '幽州': '幽州.png', '青州': '青州.png',
    '兖州': '兖州.png', '徐州': '徐州.png', '豫州': '豫州.png',
    '扬州': '扬州.png', '荆州': '荆州.png', '益州': '益州.png',
    '交州': '交州.png',
}

# 手动种子坐标修正（当治所WGS84映射到分州图时落在错误位置时使用）
# 格式: 州名 -> (ji_x, ji_y) 在 2020x1418 分州图中的像素坐标
# 这些值通过视觉检查各分州图确定的高亮填充内部点
MANUAL_SEED_JI = {
    '青州': (950, 350),    # 青州.png 中黄绿色高亮区内（深入内陆避海蓝）
    '徐州': (1300, 700),   # 徐州.png 中淡紫灰高亮区内
    '交州': (750, 1050),   # 交州.png 中品红色高亮区内（远离海岸蓝）
    '并州': (1050, 330),   # 并州.png 红色高亮区偏中心
    '冀州': (1120, 420),   # 冀州.png 浅色高亮区
    '幽州': (1280, 200),   # 幽州.png 高亮区北部
    '兖州': (1180, 450),   # 兖州.png 黄绿色高亮区
    '豫州': (1150, 520),   # 豫州.png 灰蓝色高亮区
    '扬州': (1320, 750),   # 扬州.png 亮绿色高亮区（寿春附近）
}
STATE_COLORS = {
    '凉州': (230, 180, 120, 75),
    '司隶': (220,  80,  80, 85),
    '并州': (160, 120, 200, 75),
    '冀州': (220, 100, 100, 75),
    '幽州': (100, 180, 100, 75),
    '青州': (140, 200, 100, 75),
    '兖州': (180, 200, 130, 75),
    '徐州': (120, 190, 180, 75),
    '豫州': (140, 150, 200, 75),
    '扬州': (100, 190, 100, 75),
    '荆州': (210,  90, 110, 85),
    '益州': (210, 185, 100, 75),
    '交州': (210, 100, 190, 85),
}

# 治所 WGS84（渲染用）
CAPITALS_WGS = {
    '凉州': (102.63, 37.93), '司隶': (112.45, 34.62),
    '并州': (112.55, 37.87), '冀州': (114.50, 36.10),
    '幽州': (116.40, 39.90), '青州': (118.30, 36.82),
    '兖州': (115.40, 35.58), '徐州': (117.18, 34.27),
    '豫州': (113.90, 34.02), '扬州': (116.80, 32.62),
    '荆州': (112.13, 32.02), '益州': (104.07, 30.67),
    '交州': (113.26, 23.13),
}

# 关隘 WGS84（三角标记）
PASSES_WGS = {
    '函谷关': (111.68, 34.53), '潼关': (110.25, 34.54),
    '虎牢关': (113.20, 34.72), '剑阁': (105.52, 32.28),
    '祁山': (106.03, 34.38), '阳平关': (106.48, 32.81),
}

SEAL_WGS = {n: c for n, c in CAPITALS_WGS.items()}


# ════════════════════════════════════════════
# Phase A: 从分州图提取各州掩膜
# ════════════════════════════════════════════
print('=' * 64)
log('Phase A: 分州图高亮区域生长')
t0 = time.time()

JI_W, JI_H = 2020, 1418  # 全览-郡级 / 分州图 尺寸
state_masks = {}          # idx -> bool array (JI_H, JI_W)
seed_info = {}            # idx -> dict

COLOR_TOL_BASE = 30     # 基础欧氏距离容差（自适应时会放大）
WALL_LUM = 135           # 暗线亮度阈值
MAX_AREA_FRAC = 0.20     # 单州最大允许面积比（超过则收紧重试）
MIN_AREA_FRAC = 0.002    # 单州最小期望面积比（低于则放宽重试）

for idx, (sname, cap, lon, lat) in enumerate(STATES):
    fname = STATE_FILES[sname]
    fpath = os.path.join(LEGEND_DIR, fname)
    if not os.path.exists(fpath):
        log(f'  [SKIP] {sname} 文件不存在: {fname}')
        state_masks[idx] = None; continue

    log(f'\n  [{idx+1:2d}/13] {sname} ({cap}) — {fname}')

    img = np.array(Image.open(fpath).convert('RGB')).astype(np.float64)
    lum = np.mean(img, axis=2)  # 亮度
    wall = (lum < WALL_LUM).astype(np.uint8)

    # 治所 → ji 像素坐标
    jx, jy = wgs84_to_ji(lon, lat)
    ix, iy = int(round(jx)), int(round(jy))

    if not (0 <= ix < JI_W and 0 <= iy < JI_H):
        log(f'      治所越界 ji=({ix},{iy}), 跳过')
        state_masks[idx] = None; continue

    # 种子选择：优先用手动修正坐标（若存在），否则用治所WGS84映射
    if sname in MANUAL_SEED_JI:
        sx0, sy0 = MANUAL_SEED_JI[sname]
        log(f'      使用手动种子 ji=({sx0},{sy0})')
    else:
        sx0, sy0 = ix, iy
        if wall[iy, ix] or lum[iy, ix] < 110 or lum[iy, ix] > 245:
            # 治所点不可用，在 R=25px 内螺旋找非暗线、亮度合理的像素
            found = False
            for r in range(1, 30):
                for dy in range(-r, r+1):
                    for dx in range(-r, r+1):
                        xx, yy = ix+dx, iy+dy
                        if 0 <= xx < JI_W and 0 <= yy < JI_H:
                            if wall[yy,xx] == 0 and 120 <= lum[yy,xx] <= 240:
                                sx0, sy0 = xx, yy; found = True; break
                    if found: break
                if found: break
            if not found:
                log(f'      [WARN] 治所周围无可选像素'); state_masks[idx] = None; continue

    # 排除偏蓝种子（海/河像素）：若 B 通道比 R、G 都高 >15，则搜索附近暖色像素
    seed_color = img[sy0, sx0]
    sr, sg, sb = float(seed_color[0]), float(seed_color[1]), float(seed_color[2])
    if sb > sr + 15 and sb > sg + 15:
        log(f'      种子偏蓝({sr:.0f},{sg:.0f},{sb:.0f})，搜索暖色替代...')
        best_warm = None
        best_score = -999
        wr = 50
        wx0, wx1 = max(0, int(sx0)-wr), min(JI_W, int(sx0)+wr+1)
        wy0, wy1 = max(0, int(sy0)-wr), min(JI_H, int(sy0)+wr+1)
        for cy in range(wy0, wy1):
            for cx in range(wx0, wx1):
                if wall[cy, cx] != 0: continue
                cr, cg, cb_ = float(img[cy, cx, 0]), float(img[cy, cx, 1]), float(img[cy, cx, 2])
                if not (cb_ > cr + 15 and cb_ > cg + 15):  # 非蓝色
                    warmth = (cr + cg) / 2 - cb_  # 暖度分数
                    sat_ = max(cr, cg, cb_) - min(cr, cg, cb_)
                    score = warmth + sat_ * 0.5
                    if score > best_score:
                        best_score = score
                        best_warm = (cx, cy, (cr, cg, cb_))
        if best_warm:
            sx0, sy0 = best_warm[0], best_warm[1]
            seed_color = np.array(best_warm[2])
            log(f'      暖色替换 ji=({sx0},{sy0}) 色=({seed_color[0]:.0f},{seed_color[1]:.0f},{seed_color[2]:.0f})')
    log(f'      治所ji=({ix},{iy}) 种子ji=({sx0},{sy0}) 色=({seed_color[0]:.0f},{seed_color[1]:.0f},{seed_color[2]:.0f}) '
        f'lum={lum[sy0,sx0]:.0f}')

    # 全图颜色距离（供容差迭代使用）
    diff = img - seed_color
    dist_sq = (diff ** 2).sum(axis=2)

    # ── 自适应容差：分析种子周围 60×60 窗口内的颜色分布 ──
    WR = 40
    wx0, wx1 = max(0, int(sx0) - WR), min(JI_W, int(sx0) + WR + 1)
    wy0, wy1 = max(0, int(sy0) - WR), min(JI_H, int(sy0) + WR + 1)
    win_img = img[wy0:wy1, wx0:wx1]
    win_wall = wall[wy0:wy1, wx0:wx1]
    interior = (win_wall == 0)
    if interior.sum() > 100:
        win_colors = win_img[interior]
        dists = np.sqrt(((win_colors - seed_color) ** 2).sum(axis=1))
        # 用 P75 分位数作为基础容差（容忍大部分填充变化，排除离群点）
        adaptive_tol = float(np.percentile(dists, 75))
        adaptive_tol = max(adaptive_tol, COLOR_TOL_BASE)   # 至少 25
        adaptive_tol = min(adaptive_tol, 55.0)             # 上限 55
    else:
        adaptive_tol = COLOR_TOL_BASE
    tol_sq = adaptive_tol ** 2

    log(f'      自适应容差={adaptive_tol:.1f} (tol_sq={tol_sq:.0f})')

    # ── 迭代提取：调整容差直到面积合理 ──
    best_mask = None
    best_score = -1e9

    for trial_tol_factor in [1.0, 0.6, 1.5, 2.0, 2.8, 4.0]:
        trial_tol_sq = tol_sq * (trial_tol_factor ** 2)
        cand = (dist_sq <= trial_tol_sq) & (wall == 0)
        lab, ncomp = nlabel(cand, structure=np.ones((3, 3), dtype=int))
        lseed = lab[sy0, sx0] if (0 <= sy0 < JI_H and 0 <= sx0 < JI_W) else 0
        if ncomp == 0 or lseed == 0:
            continue
        comp = (lab == lseed)
        area = int(comp.sum())
        frac = area / (JI_W * JI_H)

        # 评分：面积越接近理想范围越好（期望每州 ~5-12%）
        target_frac = 0.08
        score = -abs(frac - target_frac)
        if MIN_AREA_FRAC < frac < MAX_AREA_FRAC:
            score += 10  # 奖励在范围内

        if score > best_score:
            best_score = score
            best_mask = comp
            best_area = area
            best_frac = frac
            best_tolf = trial_tol_factor

        # 如果已经在好范围内，不再试更大容差
        if MIN_AREA_FRAC < frac < MAX_AREA_FRAC and trial_tol_factor >= 1.0:
            break

    if best_mask is None or best_mask.sum() < 20:
        log(f'      [WARN] 提取失败'); state_masks[idx] = None; continue

    comp = best_mask
    area = best_area; frac = best_frac * 100
    ys, xs = np.where(comp)

    state_masks[idx] = comp
    seed_info[idx] = {
        'seed_ji': (int(sx0), int(sy0)),
        'seed_rgb': [round(float(c)) for c in seed_color],
        'area_px': area,
        'pct': round(frac, 2),
        'bbox_ji': [int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max())],
    }
    log(f'      面积={area}px ({frac:.2f}%) bbox_x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]')


log(f'\nPhase A 耗时 {time.time()-t0:.1f}s')
log(f'成功: {sum(1 for v in state_masks.values() if v is not None)}/13')


# ════════════════════════════════════════════
# Phase B: 轮廓提取 + 坐标映射
# ════════════════════════════════════════════
print('\n' + '=' * 64)
log('Phase B: 轮廓提取 + 坐标链映射')
t0 = time.time()
SIMPLIFY_TOL = 3.0  # Douglas-Peucker 容差(像素)

output_states = []
for idx, (sname, cap, lon, lat) in enumerate(STATES):
    mask = state_masks.get(idx)
    if mask is None:
        output_states.append({'name': sname, 'error': 'no_mask'}); continue

    log(f'\n  [{idx+1:2d}/13] {sname} 轮廓提取')

    # find_contours 返回 (N,2) 坐标数组 (row, col) = (y, x)
    contours = find_contours(mask.astype(float), 0.5)
    if not contours:
        log(f'      [WARN] 无轮廓'); continue

    # 取最长外轮廓
    main_contour = max(contours, key=len)
    simp = approximate_polygon(main_contour, tolerance=SIMPLIFY_TOL)

    vertices_ji = []
    vertices_wgs84 = []
    vertices_base = []

    for pt in simp:
        py_i, px_i = float(pt[0]), float(pt[1])  # find_contours returns (row, col)
        vjx, vjy = px_i, py_i                     # ji pixel coords

        # 坐标链: ji → wgs84
        w_lon, w_lat = ji_to_wgs84(vjx, vjy)

        # 坐标链: ji → base
        bpx, bpy = ji_to_base(vjx, vjy)

        vertices_ji.append([round(vjx, 1), round(vjy, 1)])
        vertices_wgs84.append([round(w_lon, 4), round(w_lat, 4)])
        vertices_base.append([round(bpx, 1), round(bpy, 1)])

    si = seed_info.get(idx, {})
    output_states.append({
        'name': sname,
        'capital': cap,
        'capital_wgs84': [round(lon, 4), round(lat, 4)],
        'vertex_count': len(simp),
        'vertices_ji': vertices_ji,
        'vertices_wgs84': vertices_wgs84,
        'vertices_base': vertices_base,
        **si,
    })
    log(f'      顶点数={len(simp)} '
        f'wgs84 lon[{min(v[0] for v in vertices_wgs84):.1f},'
        f'{max(v[0] for v in vertices_wgs84):.1f}] '
        f'lat[{min(v[1] for v in vertices_wgs84):.1f},'
        f'{max(v[1] for v in vertices_wgs84):.1f}]')

result = {
    'method': 'fenztu_highlight_floodfill_v6',
    'source_images': '汉末十三州地图范例/分州图_*.png',
    'image_size_ji': [JI_W, JI_H],
    'base_size': [BASE_W, BASE_H],
    'color_tol_base': COLOR_TOL_BASE,
    'wall_lum': WALL_LUM,
    'simplify_tol': SIMPLIFY_TOL,
    'states': output_states,
}

out_json = os.path.join(OUT_DIR, 'state_boundaries.json')
json.dump(result, open(out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
log(f'\nJSON 已保存: {out_json} ({os.path.getsize(out_json)//1024}KB)')
log(f'Phase B 耗时 {time.time()-t0:.1f}s')


# ════════════════════════════════════════════
# Phase C: 渲染矢量图层
# ════════════════════════════════════════════
print('\n' + '=' * 64)
log('Phase C: 渲染矢量图层')
t0 = time.time()

Image.MAX_IMAGE_PIXELS = None
base = Image.open(BASE_IMG).convert('RGBA')
layer = Image.new('RGBA', (BASE_W, BASE_H), (0, 0, 0, 0))
draw_layer = ImageDraw.Draw(layer)
draw_base = ImageDraw.Draw(base)

# 字体
font_seal = None
font_label = None
font_small = None
for fp in [
    r'C:\Windows\Fonts\msyh.ttc',
    r'C:\Windows\Fonts\simhei.ttf',
    r'C:\Windows\Fonts\simsun.ttc',
]:
    if os.path.exists(fp):
        font_seal = ImageFont.truetype(fp, 56)
        font_label = ImageFont.truetype(fp, 44)
        font_small = ImageFont.truetype(fp, 32)
        break

# 绘制州多边形
for st in output_states:
    if 'vertices_base' not in st or len(st['vertices_base']) < 3:
        continue
    sname = st['name']
    color = STATE_COLORS.get(sname, (180, 80, 80, 70))
    pts = [(v[0], v[1]) for v in st['vertices_base']]
    draw_layer.polygon(pts, fill=color)
    draw_base.line(pts + [pts[0]], fill=(139, 0, 0, 200), width=2)

# 绘制治所圆圈
for sn, (slon, slat) in CAPITALS_WGS.items():
    bx, by = wgs84_to_base(slon, slat)
    r = 14
    draw_base.ellipse([bx-r, by-r, bx+r, by+r], fill=(220, 30, 30), outline=(255,255,255,200), width=2)

# 绘制关隘三角
for pn, (plon, plat) in PASSES_WGS.items():
    bx, by = wgs84_to_base(plon, plat)
    s = 12
    pts = [(bx, by-s), (bx-s, by+s*0.7), (bx+s, by+s*0.7)]
    draw_base.polygon(pts, fill=(180, 120, 40), outline=(255,255,255,180))

# 州名印章 (红底金字)
seal_positions = {}
for st in output_states:
    if 'vertices_base' not in st or len(st['vertices_base']) < 3:
        continue
    sname = st['name']
    xs = [v[0] for v in st['vertices_base']]
    ys = [v[1] for v in st['vertices_base']]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    seal_positions[sname] = (cx, cy)

# 手动微调印章位置（避免落在边界上）
SEAL_OFFSETS = {
    '凉州': (-80, -60),  '司隶': (0, -80),     '并州': (60, 40),
    '冀州': (80, 20),    '幽州': (-40, -60),    '青州': (0, 60),
    '兖州': (-60, -20),  '徐州': (60, 40),     '豫州': (0, 0),
    '扬州': (80, -60),   '荆州': (-80, -40),    '益州': (-60, 0),
    '交州': (0, 40),
}

for sn, (cx, cy) in seal_positions.items():
    ox, oy = SEAL_OFFSETS.get(sn, (0, 0))
    sx, sy = cx + ox, cy + oy
    if font_seal:
        txt = f'【{sn}】'
        bbox = draw_base.textbbox((sx, sy), txt, font=font_seal)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        pad = 8
        # 红底
        draw_base.rounded_rectangle(
            [sx-pad, sy-pad, sx+tw+pad, sy+th+pad],
            radius=6, fill=(180, 30, 30, 215), outline=(120, 20, 20), width=2
        )
        # 金字
        draw_base.text((sx, sy), txt, fill=(255, 225, 150), font=font_seal)

# 图例标题
if font_label:
    title = "汉末三国十三州"
    draw_base.text((120, 80), title, fill=(180, 30, 30), font=font_label)
    sub = "(东汉永和五年~建安二十五年)"
    if font_small:
        draw_base.text((120, 140), sub, fill=(80, 80, 80), font=font_small)

# 合成
composite = Image.alpha_composite(base, layer)
out_png = os.path.join(OUT_DIR, 'three_kingdoms_v6_vector.png')
composite.save(out_png, 'PNG')
log(f'复合图: {out_png} ({os.path.getsize(out_png)//1048576}MB)')

out_layer = os.path.join(OUT_DIR, 'three_kingdoms_v6_vector_layer.png')
layer.save(out_layer, 'PNG')
log(f'透明层: {out_layer} ({os.path.getsize(out_layer)//1024}KB)')

# 缩略预览
preview = composite.copy()
prev_size = (preview.width // 5, preview.height // 5)
preview.thumbnail(prev_size, Image.LANCZOS)
out_prev = os.path.join(OUT_DIR, 'three_kingdoms_v6_vector_preview.png')
preview.save(out_prev, 'PNG')
log(f'预览图: {out_prev}')

log(f'Phase C 耗时 {time.time()-t0:.1f}s')
log('全部完成!')
