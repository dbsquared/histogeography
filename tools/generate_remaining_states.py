#!/usr/bin/env python3
"""
generate_remaining_states.py
为剩余 8 州自动生成初始 boundary anchors + GCPs，写入 viewer/han_states_raw/{name}.geojson。

方法：
1. 颜色分割：从参考图中心采样主色，LAB 阈值分割，取最大连通域，提取外轮廓。
2. 仿射估计：用 GCP_DB 城市 bbox 扩展 F=1.8 估计图像地理范围，构造方形像素 centered 仿射。
3. 投影：城市 → 像素（初始 GCPs），轮廓像素 → 经纬度（初始 features）。
4. 写入：包含 pixels 侧通道（供 digitize_v2.html 自动加载）和 features（供 build_han_states.py）。
"""
import json, re, os, math, glob
from PIL import Image
import numpy as np
import cv2

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIGITIZE = os.path.join(HERE, 'viewer', 'digitize_v2.html')
RAW_DIR = os.path.join(HERE, 'viewer', 'han_states_raw')
REF_DIR = os.path.join(HERE, 'viewer', 'ref_imgs')
IMG_W, IMG_H = 2020, 1418
SEG_TOL = 40
F_EXPAND = 1.8
TARGET_BND_POINTS = 400  # 加密边界锚点，预描更细致（原 300）

def extract_gcp_db(path):
    txt = open(path, encoding='utf-8').read()
    m = re.search(r'const GCP_DB\s*=\s*\{([\s\S]*?)\};', txt)
    block = m.group(1)
    db = {}
    for sm in re.finditer(r"'([^']+)':\[(.*?)\]", block, re.S):
        state = sm.group(1)
        arr_s = sm.group(2)
        cities = []
        for cm in re.finditer(r"\{name:'([^']+)',lon:([\d.\-]+),lat:([\d.\-]+)\}", arr_s):
            cities.append({
                'name': cm.group(1),
                'lon': float(cm.group(2)),
                'lat': float(cm.group(3)),
            })
        db[state] = cities
    return db

def segment_state_contour(state, diag_dir=None):
    """
    多聚类合并分割：
    1. 全局 kmeans 得到 K 个主色；
    2. 从中心区域主导标签出发，迭代合并 LAB 颜色距离 < merge_tol 的聚类；
    3. 对合并后的 mask 取连通域，用“面积 × 中心重叠度”打分，排除全图背景；
    4. 取最佳连通域的外轮廓。
    这样能处理州内有郡级色差（如豫州/荆州中心郡颜色不同）的情况。
    """
    img = Image.open(os.path.join(REF_DIR, f'{state}.png')).convert('RGB')
    arr = np.array(img)
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    h, w = arr.shape[:2]
    cx, cy = w//2, h//2

    # 全局 kmeans（采样加速）
    samples = lab.reshape(-1, 3).astype(np.float32)
    if len(samples) > 50000:
        idx = np.random.choice(len(samples), 50000, replace=False)
        train = samples[idx]
    else:
        train = samples
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    K = 8
    _, labels, centers = cv2.kmeans(train, K, None, criteria, 10, cv2.KMEANS_PP_CENTERS)
    centers = centers.astype(np.float32)

    # 为每个像素分配最近聚类
    dists = np.linalg.norm(samples[:, None, :] - centers[None, :, :], axis=2)
    seg_labels = np.argmin(dists, axis=1).reshape(h, w).astype(np.int32)

    # 中心区域主导标签（避免中心点正好落在白线/文字上）
    center_patch = seg_labels[cy-30:cy+30, cx-30:cx+30]
    vals, counts = np.unique(center_patch, return_counts=True)
    center_label = vals[np.argmax(counts)]

    # 迭代合并与中心标签颜色相近的聚类（收紧 tol，避免把背景/邻州拉进来）
    merge_tol = 32
    merged = {int(center_label)}
    changed = True
    while changed:
        changed = False
        for i in range(K):
            if i in merged:
                continue
            if any(np.linalg.norm(centers[i] - centers[j]) < merge_tol for j in merged):
                merged.add(i)
                changed = True

    mask = np.isin(seg_labels, list(merged)).astype(np.uint8) * 255

    # 先用较大闭运算把州内被白线/文字切开的区域连起来
    kernel = np.ones((7,7), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    # 轻微开运算去孤立噪声
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3,3), np.uint8), iterations=1)

    # 找连通域并打分
    n, cc, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 1:
        raise RuntimeError(f'{state}: 多聚类合并后无连通域')

    roi_y0, roi_y1 = int(h*0.25), int(h*0.75)
    roi_x0, roi_x1 = int(w*0.25), int(w*0.75)
    roi_mask = np.zeros((h, w), dtype=np.uint8)
    roi_mask[roi_y0:roi_y1, roi_x0:roi_x1] = 255
    img_area = h * w

    # 第一顺位：面积不是全图、中心重叠度最高的较大连通域
    candidates = []
    for comp in range(1, n):
        area = stats[comp, cv2.CC_STAT_AREA]
        if area < 10000:
            continue
        comp_mask = (cc == comp).astype(np.uint8)
        overlap = cv2.bitwise_and(comp_mask * 255, roi_mask).sum() / 255.0
        cy_comp, cx_comp = centroids[comp]
        dist_to_center = math.hypot(cx_comp - cx, cy_comp - cy)
        x, y, bw, bh = stats[comp, cv2.CC_STAT_LEFT], stats[comp, cv2.CC_STAT_TOP], \
                       stats[comp, cv2.CC_STAT_WIDTH], stats[comp, cv2.CC_STAT_HEIGHT]
        touches_all_border = (x <= 2 and y <= 2 and x+bw >= w-3 and y+bh >= h-3)
        # 全图背景直接排除
        if area > 0.85 * img_area and touches_all_border:
            continue
        # 贴边大组件（很可能包含背景）降权
        touches_any_border = (x <= 2 or y <= 2 or x+bw >= w-3 or y+bh >= h-3)
        border_penalty = 0.4 if touches_any_border else 1.0
        score = area * overlap * border_penalty / (dist_to_center + 50.0)
        candidates.append((score, comp, area, overlap))

    candidates.sort(reverse=True)
    if not candidates:
        # fallback：中心点所在连通域
        center_cc = cc[cy, cx]
        if center_cc == 0:
            areas = stats[1:, cv2.CC_STAT_AREA]
            center_cc = int(np.argmax(areas) + 1)
        best_comp = center_cc
    else:
        best_comp = candidates[0][1]

    clean = (cc == best_comp).astype(np.uint8) * 255
    # 闭运算填补州内小孔
    kernel = np.ones((5,5), np.uint8)
    clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel, iterations=2)
    clean = cv2.morphologyEx(clean, cv2.MORPH_OPEN, kernel, iterations=1)

    # CHAIN_APPROX_NONE 保留所有像素点，便于后续去锯齿 + 均匀重采样加密
    contours, _ = cv2.findContours(clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    if not contours:
        raise RuntimeError(f'{state}: 未找到外轮廓')
    cnt = max(contours, key=cv2.contourArea)
    cnt = simplify_contour(cnt, TARGET_BND_POINTS)
    pts = [(int(p[0][0]), int(p[0][1])) for p in cnt]

    if diag_dir:
        os.makedirs(diag_dir, exist_ok=True)
        vis = arr.copy()
        vis[clean==0] = (vis[clean==0] * 0.5).astype(np.uint8)
        cv2.drawContours(vis, [cnt], -1, (255,0,0), 2)
        Image.fromarray(vis).save(os.path.join(diag_dir, f'{state}_seg.png'))
    return pts, clean

def simplify_contour(cnt, target):
    """去像素级锯齿后，沿弧长均匀重采样到固定点数，边界平滑且锚点密集。

    旧实现用 approxPolyDP 二分 epsilon，点数受形状复杂度限制、常远低于 target
    （很多州只有 130~180 点）。改为：小 epsilon 去锯齿 → 弧长均匀重采样到精确
    target 点，保证每个州都有稳定且更密的边界锚点，预描更细致。
    """
    peri = cv2.arcLength(cnt, True)
    if peri <= 0:
        return cnt
    # 极小 epsilon：只抹掉像素级台阶锯齿，几乎不改变形状
    approx = cv2.approxPolyDP(cnt, 0.0012 * peri, True)
    if len(approx) < 4:
        approx = cnt
    return resample_contour(approx, target)


def resample_contour(cnt, n):
    """沿闭合轮廓按弧长均匀重采样为恰好 n 个点。"""
    pts = cnt.reshape(-1, 2).astype(np.float64)
    if len(pts) < 3:
        return cnt.reshape(-1, 1, 2).astype(np.int32)
    ring = np.vstack([pts, pts[0]])  # 闭合
    seg = np.diff(ring, axis=0)
    dist = np.sqrt((seg ** 2).sum(axis=1))
    cum = np.concatenate([[0.0], np.cumsum(dist)])
    total = cum[-1]
    if total <= 0:
        return cnt.reshape(-1, 1, 2).astype(np.int32)
    targets = np.linspace(0.0, total, n, endpoint=False)
    out = []
    j = 0
    for t in targets:
        while j < len(cum) - 1 and cum[j + 1] < t:
            j += 1
        seg_len = cum[j + 1] - cum[j]
        r = 0.0 if seg_len == 0 else (t - cum[j]) / seg_len
        p = ring[j] * (1 - r) + ring[j + 1] * r
        out.append([int(round(p[0])), int(round(p[1]))])
    return np.array(out, dtype=np.int32).reshape(-1, 1, 2)

def estimate_affine(cities, F=F_EXPAND):
    """返回 (a, e, c, f): lon=a*px+c, lat=e*py+f; 方形像素、居中"""
    lons = [c['lon'] for c in cities]
    lats = [c['lat'] for c in cities]
    lon_c = (min(lons)+max(lons))/2
    lat_c = (min(lats)+max(lats))/2
    hw_lon = (max(lons)-min(lons))/2
    hw_lat = (max(lats)-min(lats))/2
    # 估计图像地理范围
    ilon0 = lon_c - F*hw_lon
    ilon1 = lon_c + F*hw_lon
    ilat0 = lat_c - F*hw_lat
    ilat1 = lat_c + F*hw_lat
    W_km = (ilon1-ilon0)*111*math.cos(math.radians(lat_c))
    H_km = (ilat1-ilat0)*111
    scale = min(IMG_W/W_km, IMG_H/H_km)  # px/km
    W_img_km = IMG_W/scale
    H_img_km = IMG_H/scale
    a = W_img_km/(IMG_W*111*math.cos(math.radians(lat_c)))
    e = H_img_km/(IMG_H*111)
    c = lon_c - a*IMG_W/2
    f = lat_c - e*IMG_H/2
    return a, e, c, f

def lonlat_from_px(a, e, c, f, px, py):
    return a*px + c, e*py + f

def px_from_lonlat(a, e, c, f, lon, lat):
    return (lon-c)/a, (lat-f)/e

def generate_state(state, color, db, diag_dir=None):
    cities = db[state]
    a, e, c, f = estimate_affine(cities)
    # 轮廓（像素坐标）
    bnd_px, _ = segment_state_contour(state, diag_dir=diag_dir)
    # GCPs：不再预填！
    # 教训（2026-07-25 豫州）：用估计仿射投影出的 GCP 像素不属于该州参考图的真实位置，
    # 会混进用户导出数据造成残差 200km+ 级污染。GCP 必须由用户在该州地图上亲手打点。
    gcps = []
    # 轮廓转经纬度（features）
    ring = []
    for px, py in bnd_px:
        lon, lat = lonlat_from_px(a, e, c, f, px, py)
        ring.append([round(lon, 5), round(lat, 5)])
    ring.append(ring[0])  # 闭合
    # 计算 GCP 残差（用同一仿射，应接近 0）
    max_err = 0.0
    sum_err = 0.0
    for g in gcps:
        plon, plat = lonlat_from_px(a, e, c, f, g['px'], g['py'])
        err = math.hypot((plon-g['lon'])*111*math.cos(math.radians(g['lat'])), (plat-g['lat'])*111)
        max_err = max(max_err, err)
        sum_err += err
    avg_err = sum_err/len(gcps) if gcps else 0.0
    geojson = {
        'type': 'FeatureCollection',
        'metadata': {
            'state': state,
            'color': color,
            'gcps': len(gcps),
            'max_err_km': round(max_err, 1),
            'avg_err_km': round(avg_err, 1),
            'verified': False,  # 自动初稿，未经用户 GCP 校正，地图暂不叠加
        },
        'pixels': {
            'gcps': gcps,
            'bnd': [[px, py] for px, py in bnd_px],
            'seats': [],
        },
        'features': [
            {
                'type': 'Feature',
                'properties': {'kind': 'state_boundary', 'state': state, 'color': color},
                'geometry': {'type': 'Polygon', 'coordinates': [ring]},
            }
        ]
    }
    return geojson

def main():
    db = extract_gcp_db(DIGITIZE)
    # 注意：司隶已由用户校正（verified=true），绝不能覆盖 —— 只重新生成 7 个未校正州
    remaining = ['兖州','豫州','徐州','青州','荆州','扬州','交州']
    # 配色方案（非黄/绿/蓝/橙，高反差；与已有 5 州区分）
    colors = {
        '司隶': '#6A1B9A',  # 深紫（与并州 #8E44AD 区分）— 已校正，不在 remaining 内
        '兖州': '#C62828',  # 正红（与冀州 #D27370 浅珊瑚红区分）
        '豫州': '#5E35B1',  # 靛紫（紫家族）
        '徐州': '#D81B60',  # 樱桃红（与凉州 #E91E63 区分）
        '青州': '#880E4F',  # 深酒红（与益州 #B71C4B 区分）
        '荆州': '#AB47BC',  # 兰花紫（与并州 #8E44AD 区分）
        '扬州': '#F48FB1',  # 浅粉
        '交州': '#EC407A',  # 热粉
    }
    diag_dir = os.path.join(HERE, 'auto_seg_diag')
    for state in remaining:
        print(f'生成 {state} ...')
        gj = generate_state(state, colors[state], db, diag_dir=diag_dir)
        fp = os.path.join(RAW_DIR, f'{state}.geojson')
        with open(fp, 'w', encoding='utf-8') as f:
            json.dump(gj, f, ensure_ascii=False, indent=2)
        print(f'  -> {fp}: bnd={len(gj["pixels"]["bnd"])} pts, gcps={len(gj["pixels"]["gcps"])}')

if __name__ == '__main__':
    main()
