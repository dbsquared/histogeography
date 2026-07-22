#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按用户在 youzhou_mask_v3_small_修补内凹.jpg 上画的红线修正幽州边界。
把红线从缩略图坐标映射回全图，找到红线与原边界的两个端点，
用红线替换原边界中凹陷的那段弧线。
"""

import json
import cv2
import math
import numpy as np
from PIL import Image

ORIG_IMG = '汉末十三州地图范例/幽州.png'
ANNOT_IMG = 'youzhou_layer_v2/youzhou_mask_v3_small_修补内凹.jpg'
CORR_JSON = 'youzhou_layer_v2/youzhou_correspondence.json'
BACKUP_JSON = 'youzhou_layer_v2/youzhou_correspondence.json.bak_redline'
OUT_JSON = 'youzhou_layer_v2/youzhou_correspondence.json'

RED_THR = {'r': 150, 'g': 90, 'b': 90}  # 红线阈值（在缩略图上）
MIN_STROKE_LEN = 8


def load_boundary():
    with open(CORR_JSON, 'r', encoding='utf-8') as f:
        d = json.load(f)
    pts = d['points']
    xy = np.array([[p['px'], p['py']] for p in pts], dtype=np.float64)
    return d, xy


def extract_red_strokes(annot_path, full_w, full_h):
    """从标注缩略图中提取红线，并映射到全图坐标。"""
    img = np.array(Image.open(annot_path).convert('RGB'))
    H, W = img.shape[:2]
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    red = ((r > RED_THR['r']) & (g < RED_THR['g']) & (b < RED_THR['b'])).astype(np.uint8) * 255

    # 清理孤点
    red = cv2.morphologyEx(red, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8), iterations=1)

    nb, lab, st, _ = cv2.connectedComponentsWithStats(red, connectivity=8)
    strokes = []
    for i in range(1, nb):
        area = st[i, cv2.CC_STAT_AREA]
        if area < MIN_STROKE_LEN:
            continue
        ys, xs = np.where(lab == i)
        pts = np.column_stack([xs, ys])  # (x,y) in small image
        # 按链顺序排列
        ordered = order_stroke_pixels(pts)
        if len(ordered) < 2:
            continue
        # 缩放到全图坐标
        sx, sy = full_w / W, full_h / H
        ordered_full = np.column_stack([
            np.round(ordered[:, 0] * sx).astype(int),
            np.round(ordered[:, 1] * sy).astype(int)
        ])
        strokes.append(ordered_full)
    return strokes, (W, H)


def order_stroke_pixels(pts):
    """把无序的连通像素点按链顺序排列（简单最近邻走法）。"""
    pts = [tuple(p) for p in pts]
    if len(pts) <= 2:
        return np.array(pts)
    # 构建邻居集合
    s = set(pts)

    def neighbors(p):
        x, y = p
        out = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                q = (x + dx, y + dy)
                if q in s:
                    out.append(q)
        return out

    # 找端点（度为1）
    ends = [p for p in pts if len(neighbors(p)) == 1]
    if len(ends) >= 2:
        start = ends[0]
    else:
        start = pts[0]

    ordered = [start]
    seen = {start}
    cur = start
    while True:
        nbs = [n for n in neighbors(cur) if n not in seen]
        if not nbs:
            break
        nxt = nbs[0]
        ordered.append(nxt)
        seen.add(nxt)
        cur = nxt
    return np.array(ordered)


def polygon_area(poly):
    """Shoelace signed area."""
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * (np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def replace_arc_with_redline(boundary, stroke):
    """用红线替换 boundary 上对应的凹陷弧段。"""
    # 红线端点
    a = stroke[0]
    b = stroke[-1]

    # 找原边界上最近的两个点
    da = np.linalg.norm(boundary - a, axis=1)
    db = np.linalg.norm(boundary - b, axis=1)
    ia = int(np.argmin(da))
    ib = int(np.argmin(db))

    n = len(boundary)

    # 两条弧：ia -> ib 正向 / 反向
    def forward_arc(i, j):
        if j >= i:
            return list(range(i, j + 1))
        else:
            return list(range(i, n)) + list(range(0, j + 1))

    arc1 = forward_arc(ia, ib)
    arc2 = forward_arc(ib, ia)

    # 红线本身的方向需要与边界方向一致。分别试两种拼接，选与原多边形方向相同的。
    # 方案1: arc1 被红线替换（红线从 ia 端走到 ib 端）
    seq1 = boundary[arc1[0]:arc1[0] + 1]  # placeholder
    # 实际构造新多边形
    def build(keep_arc, stroke_pts, start_idx, end_idx):
        # keep_arc 是从 start_idx 走到 end_idx 的 arc（包含两端）
        # 新多边形 = 0..start_idx, stroke_pts, end_idx..n-1
        # 需要保持原顺序
        if end_idx >= start_idx:
            new = np.vstack([boundary[:start_idx + 1], stroke_pts, boundary[end_idx:]])
        else:
            new = np.vstack([boundary[:end_idx + 1], stroke_pts[::-1], boundary[start_idx:]])
        return new

    # 方案A: 替换 arc1，红线正向 stroke
    newA = build(arc1, stroke, ia, ib)
    # 方案B: 替换 arc2，红线反向
    newB = build(arc2, stroke[::-1], ib, ia)

    # 选择与原始多边形同方向（同号）且面积更接近或略大的
    orig_area = polygon_area(boundary)
    areaA = polygon_area(newA)
    areaB = polygon_area(newB)

    # 同方向优先
    sameA = (areaA * orig_area) > 0
    sameB = (areaB * orig_area) > 0

    if sameA and not sameB:
        return newA, arc1
    if sameB and not sameA:
        return newB, arc2

    # 都同向：选面积略大（填充凹陷）的那个
    if abs(areaA) > abs(areaB):
        return newA, arc1
    else:
        return newB, arc2


def main():
    d, boundary = load_boundary()
    full_h, full_w = d['image_size'][1], d['image_size'][0]

    strokes, small_size = extract_red_strokes(ANNOT_IMG, full_w, full_h)
    print(f'缩略图尺寸: {small_size}')
    print(f'提取到 {len(strokes)} 条红线')
    for i, s in enumerate(strokes):
        print(f'  红线 {i + 1}: {len(s)} 点, 端点 {tuple(s[0])} -> {tuple(s[-1])}')

    if not strokes:
        print('未检测到红线，退出')
        return

    # 备份
    with open(BACKUP_JSON, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

    # 依次替换
    replaced_arcs = []
    for stroke in strokes:
        new_boundary, replaced_arc = replace_arc_with_redline(boundary, stroke)
        replaced_arcs.append(replaced_arc)
        boundary = new_boundary

    print(f'修正后边界点数: {len(boundary)}（原 {len(d["points"])}）')

    # 更新 JSON
    d['points'] = []
    for i, (x, y) in enumerate(boundary):
        d['points'].append({
            'seq': i,
            'px': int(round(x)),
            'py': int(round(y)),
            'lon': None,
            'lat': None
        })
    d['method'] = d.get('method', '') + ' + 用户红线修正内凹'
    d['redline_fix'] = {
        'strokes': len(strokes),
        'replaced_arcs': [len(a) for a in replaced_arcs]
    }

    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    print(f'已保存 {OUT_JSON}')

    # 画诊断图：红线 + 修正后边界
    rgb = np.array(Image.open(ORIG_IMG).convert('RGB'))
    canvas = rgb.copy()
    # 修正后边界 绿
    cv2.polylines(canvas, [boundary.astype(np.int32)], True, (0, 255, 0), 2)
    # 红线 红
    for stroke in strokes:
        cv2.polylines(canvas, [stroke.astype(np.int32)], False, (255, 0, 0), 2)
    # 端点 黄
    for stroke in strokes:
        cv2.circle(canvas, tuple(stroke[0]), 5, (255, 255, 0), -1)
        cv2.circle(canvas, tuple(stroke[-1]), 5, (255, 255, 0), -1)
    Image.fromarray(canvas).save('youzhou_layer_v2/redline_fix_debug.png')
    print('诊断图保存: youzhou_layer_v2/redline_fix_debug.png')


if __name__ == '__main__':
    main()
