#!/usr/bin/env python3
"""
analyze_ref_convention.py
1) 从 digitize_v2.html 提取 GCP_DB
2) 用 5 个已接入州的 pixels.gcps 计算精确仿射
3) 比较图像地理范围与 (a) 州界 bbox (b) GCP_DB 城市 bbox，推导 padding 规律
4) 测试参考图颜色分割可行性（中心采样 + LAB 阈值）
"""
import json, re, os, glob, math
from PIL import Image
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
DIGITIZE = os.path.join(HERE, 'viewer', 'digitize_v2.html')
RAW_DIR = os.path.join(HERE, 'viewer', 'han_states_raw')
REF_DIR = os.path.join(HERE, 'viewer', 'ref_imgs')

def extract_gcp_db(path):
    txt = open(path, encoding='utf-8').read()
    # 找到 GCP_DB = { ... };
    m = re.search(r'const GCP_DB\s*=\s*\{([\s\S]*?)\};', txt)
    if not m:
        raise RuntimeError('GCP_DB not found')
    block = m.group(1)
    db = {}
    # 按州名匹配每个数组
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

def affine_from_gcps(gcps):
    """lstsq: lon = a*px + b*py + c; lat = d*px + e*py + f"""
    X = np.array([[g['px'], g['py'], 1.0] for g in gcps])
    lon = np.array([g['lon'] for g in gcps])
    lat = np.array([g['lat'] for g in gcps])
    Mlon, *_ = np.linalg.lstsq(X, lon, rcond=None)
    Mlat, *_ = np.linalg.lstsq(X, lat, rcond=None)
    return Mlon, Mlat

def px_to_lonlat(Mlon, Mlat, px, py):
    return (Mlon[0]*px + Mlon[1]*py + Mlon[2],
            Mlat[0]*px + Mlat[1]*py + Mlat[2])

def bbox(points):
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    return min(lons), min(lats), max(lons), max(lats)

def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.asin(math.sqrt(a))

def km_per_px(Mlon, Mlat):
    # 取图像中心附近估算
    cx, cy = 1010, 709
    lon0, lat0 = px_to_lonlat(Mlon, Mlat, cx, cy)
    lon1, lat1 = px_to_lonlat(Mlon, Mlat, cx+1, cy)
    lon2, lat2 = px_to_lonlat(Mlon, Mlat, cx, cy+1)
    dx = haversine_km(lon0, lat0, lon1, lat1)
    dy = haversine_km(lon0, lat0, lon2, lat2)
    return dx, dy

def analyze():
    db = extract_gcp_db(DIGITIZE)
    done = ['冀州','凉州','并州','幽州','益州']
    print('=== GCP_DB 城市统计 ===')
    for s in done + ['司隶','兖州','豫州','徐州','青州','荆州','扬州','交州']:
        print(f'  {s}: {len(db.get(s, []))} 城')

    print('\n=== 已接入州：仿射、范围、padding 分析 ===')
    for state in done:
        fp = os.path.join(RAW_DIR, f'{state}.geojson')
        gj = json.load(open(fp, encoding='utf-8'))
        if 'pixels' not in gj or 'gcps' not in gj.get('pixels', {}):
            print(f'\n{state}: 无 pixels.gcps，跳过仿射分析（仍计入城市数）')
            continue
        gcps = gj['pixels']['gcps']
        Mlon, Mlat = affine_from_gcps(gcps)
        dx, dy = km_per_px(Mlon, Mlat)
        # 图像四角
        corners = [(0,0),(2020,0),(2020,1418),(0,1418)]
        img_extent = [px_to_lonlat(Mlon, Mlat, px, py) for px, py in corners]
        img_bbox = bbox(img_extent)
        img_cx = (img_bbox[0]+img_bbox[2])/2
        img_cy = (img_bbox[1]+img_bbox[3])/2
        img_hw_lon = (img_bbox[2]-img_bbox[0])/2
        img_hw_lat = (img_bbox[3]-img_bbox[1])/2

        # 州界 bbox
        ring = gj['features'][0]['geometry']['coordinates'][0]
        bnd_bbox = bbox(ring)
        bnd_hw_lon = (bnd_bbox[2]-bnd_bbox[0])/2
        bnd_hw_lat = (bnd_bbox[3]-bnd_bbox[1])/2
        bnd_cx = (bnd_bbox[0]+bnd_bbox[2])/2
        bnd_cy = (bnd_bbox[1]+bnd_bbox[3])/2

        # GCP_DB 城市 bbox
        cities = db[state]
        cb = bbox([(c['lon'], c['lat']) for c in cities])
        city_hw_lon = (cb[2]-cb[0])/2
        city_hw_lat = (cb[3]-cb[1])/2
        city_cx = (cb[0]+cb[2])/2
        city_cy = (cb[1]+cb[3])/2

        print(f'\n{state}: GCP={len(gcps)}')
        print(f'  affine km/px: dx={dx:.3f}, dy={dy:.3f}')
        print(f'  image bbox:   lon [{img_bbox[0]:.2f},{img_bbox[2]:.2f}] lat [{img_bbox[1]:.2f},{img_bbox[3]:.2f}]')
        print(f'  image center: ({img_cx:.2f},{img_cy:.2f})')
        print(f'  bnd  bbox:    lon [{bnd_bbox[0]:.2f},{bnd_bbox[2]:.2f}] lat [{bnd_bbox[1]:.2f},{bnd_bbox[3]:.2f}]')
        print(f'  bnd  center:  ({bnd_cx:.2f},{bnd_cy:.2f})')
        print(f'  city bbox:    lon [{cb[0]:.2f},{cb[2]:.2f}] lat [{cb[1]:.2f},{cb[3]:.2f}]')
        print(f'  city center:  ({city_cx:.2f},{city_cy:.2f})')
        print(f'  img/bnd hw lon ratio: {img_hw_lon/bnd_hw_lon:.3f}  lat ratio: {img_hw_lat/bnd_hw_lat:.3f}')
        print(f'  img/city hw lon ratio:{img_hw_lon/city_hw_lon:.3f}  lat ratio:{img_hw_lat/city_hw_lat:.3f}')
        print(f'  center offset img-bnd: ({(img_cx-bnd_cx)*111*math.cos(math.radians(img_cy)):.1f}km, {(img_cy-bnd_cy)*111:.1f}km)')
        print(f'  center offset img-city:({(img_cx-city_cx)*111*math.cos(math.radians(img_cy)):.1f}km, {(img_cy-city_cy)*111:.1f}km)')

def test_segment(state, tol=35):
    """测试颜色分割：中心采样 + LAB 阈值"""
    img = Image.open(os.path.join(REF_DIR, f'{state}.png')).convert('RGB')
    arr = np.array(img)
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    h, w = arr.shape[:2]
    # 中心 300x300 采样 dominant color
    cx, cy = w//2, h//2
    patch = lab[cy-150:cy+150, cx-150:cx+150].reshape(-1, 3)
    # kmeans 找主色
    patch = np.float32(patch)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(patch, 3, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    counts = np.bincount(labels.flatten())
    dom = centers[np.argmax(counts)].astype(np.float32)
    print(f'\n[{state}] dominant LAB center color = {dom}')
    # mask
    diff = np.linalg.norm(lab.astype(np.float32) - dom, axis=2)
    mask = diff < tol
    mask = mask.astype(np.uint8) * 255
    # 保留最大连通域
    n, cc, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 1:
        print('  no components')
        return
    areas = stats[1:, cv2.CC_STAT_AREA]
    largest = np.argmax(areas) + 1
    clean = (cc == largest).astype(np.uint8) * 255
    # 闭运算填补小孔
    kernel = np.ones((5,5), np.uint8)
    clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel, iterations=2)
    clean = cv2.morphologyEx(clean, cv2.MORPH_OPEN, kernel, iterations=1)
    # 找外轮廓
    contours, _ = cv2.findContours(clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        print('  no contours')
        return
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    print(f'  largest contour area px={area}, points={len(cnt)}')
    # 可视化保存
    vis = arr.copy()
    vis[clean==0] = (vis[clean==0] * 0.5).astype(np.uint8)
    cv2.drawContours(vis, [cnt], -1, (255,0,0), 2)
    out = os.path.join(HERE, f'seg_test_{state}.png')
    Image.fromarray(vis).save(out)
    print(f'  saved {out}')

def estimate_affine_from_cities(cities, F=1.7):
    """用城市 bbox 扩展 F 倍估计图像地理范围，再构造方形像素 centered 仿射。"""
    lons = [c['lon'] for c in cities]
    lats = [c['lat'] for c in cities]
    lon_c = (min(lons)+max(lons))/2
    lat_c = (min(lats)+max(lats))/2
    hw_lon = (max(lons)-min(lons))/2
    hw_lat = (max(lats)-min(lats))/2
    # 估计图像范围
    ilon0 = lon_c - F*hw_lon
    ilon1 = lon_c + F*hw_lon
    ilat0 = lat_c - F*hw_lat
    ilat1 = lat_c + F*hw_lat
    # 方形像素 fit
    W, H = 2020, 1418
    W_km = (ilon1-ilon0)*111*math.cos(math.radians(lat_c))
    H_km = (ilat1-ilat0)*111
    scale = min(W/W_km, H/H_km)  # px/km
    # 以城市中心为中心
    W_img_km = W/scale
    H_img_km = H/scale
    # lon/px 关系：lon = lon_c + (px-W/2)*(W_km_img/W)/(111*cos(lat_c))
    # 其中 W_km_img = W/scale
    a = W_img_km/(W*111*math.cos(math.radians(lat_c)))
    e = H_img_km/(H*111)
    c = lon_c - a*W/2
    f = lat_c - e*H/2
    return a, e, c, f

def segment_state_bbox(state, tol=40):
    """返回分割后的 state 区域像素 bbox [x0,y0,x1,y1] 及 mask"""
    img = Image.open(os.path.join(REF_DIR, f'{state}.png')).convert('RGB')
    arr = np.array(img)
    lab = cv2.cvtColor(arr, cv2.COLOR_RGB2LAB)
    h, w = arr.shape[:2]
    cx, cy = w//2, h//2
    patch = lab[cy-150:cy+150, cx-150:cx+150].reshape(-1, 3)
    patch = np.float32(patch)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, labels, centers = cv2.kmeans(patch, 3, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    counts = np.bincount(labels.flatten())
    dom = centers[np.argmax(counts)].astype(np.float32)
    diff = np.linalg.norm(lab.astype(np.float32) - dom, axis=2)
    mask = (diff < tol).astype(np.uint8) * 255
    n, cc, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 1:
        return None, None
    areas = stats[1:, cv2.CC_STAT_AREA]
    largest = np.argmax(areas) + 1
    clean = (cc == largest).astype(np.uint8) * 255
    kernel = np.ones((5,5), np.uint8)
    clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel, iterations=2)
    ys, xs = np.where(clean)
    if len(xs)==0:
        return None, None
    return [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], clean

def estimate_affine_from_segment(state, cities, G=1.35):
    """用分割出的 state 像素 bbox + 城市 bbox 扩展 G 倍估计仿射。"""
    bbox = segment_state_bbox(state)
    if bbox is None or bbox[0] is None:
        return None
    px0, py0, px1, py1 = bbox[0]
    lons = [c['lon'] for c in cities]
    lats = [c['lat'] for c in cities]
    lon_c = (min(lons)+max(lons))/2
    lat_c = (min(lats)+max(lats))/2
    hw_lon = (max(lons)-min(lons))/2
    hw_lat = (max(lats)-min(lats))/2
    # 估计 state 地理 bbox
    slon0 = lon_c - G*hw_lon
    slon1 = lon_c + G*hw_lon
    slat0 = lat_c - G*hw_lat
    slat1 = lat_c + G*hw_lat
    geo_w_km = (slon1-slon0)*111*math.cos(math.radians(lat_c))
    geo_h_km = (slat1-slat0)*111
    pix_w = px1 - px0
    pix_h = py1 - py0
    scale = (pix_w/geo_w_km + pix_h/geo_h_km)/2  # px/km
    # 图像中心 = state 地理中心
    W, H = 2020, 1418
    a = 1/(scale*111*math.cos(math.radians(lat_c)))
    e = 1/(scale*111)
    c = lon_c - a*W/2
    f = lat_c - e*H/2
    return a, e, c, f

def estimate_affine_mean_center(state, cities, G=1.35):
    """用城市平均中心 + 分割 state 像素 bbox 估计仿射。"""
    bbox = segment_state_bbox(state)
    if bbox is None or bbox[0] is None:
        return None
    px0, py0, px1, py1 = bbox[0]
    lons = [c['lon'] for c in cities]
    lats = [c['lat'] for c in cities]
    lon_c = sum(lons)/len(lons)
    lat_c = sum(lats)/len(lats)
    # 用城市 5%-95% 范围作为 spread 估计，降低离群城市影响
    hw_lon = (np.percentile(lons,95)-np.percentile(lons,5))/2
    hw_lat = (np.percentile(lats,95)-np.percentile(lats,5))/2
    slon0 = lon_c - G*hw_lon
    slon1 = lon_c + G*hw_lon
    slat0 = lat_c - G*hw_lat
    slat1 = lat_c + G*hw_lat
    geo_w_km = (slon1-slon0)*111*math.cos(math.radians(lat_c))
    geo_h_km = (slat1-slat0)*111
    pix_w = px1 - px0
    pix_h = py1 - py0
    scale = (pix_w/geo_w_km + pix_h/geo_h_km)/2
    W, H = 2020, 1418
    a = 1/(scale*111*math.cos(math.radians(lat_c)))
    e = 1/(scale*111)
    c = lon_c - a*W/2
    f = lat_c - e*H/2
    return a, e, c, f

def test_segment_multicluster(state, k=8, merge_tol=45):
    """多聚类合并：全局 kmeans，从中心标签开始合并颜色相近的聚类"""
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
    _, labels, centers = cv2.kmeans(train, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    centers = centers.astype(np.float32)
    # 为每个像素分配最近聚类
    dists = np.linalg.norm(samples[:,None,:] - centers[None,:,:], axis=2)
    seg_labels = np.argmin(dists, axis=1).reshape(h, w).astype(np.int32)
    # 中心标签
    center_label = seg_labels[cy, cx]
    # 合并与中心标签颜色距离 < merge_tol 的聚类
    merged = {center_label}
    changed = True
    while changed:
        changed = False
        for i in range(k):
            if i in merged: continue
            if any(np.linalg.norm(centers[i]-centers[j]) < merge_tol for j in merged):
                merged.add(i)
                changed = True
    mask = np.isin(seg_labels, list(merged)).astype(np.uint8) * 255
    # 保留中心所在最大连通域
    n, cc, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if n <= 1:
        print(f'[{state}] multicluster: no components')
        return
    # 找包含中心像素的连通域
    center_cc = cc[cy, cx]
    if center_cc == 0:
        areas = stats[1:, cv2.CC_STAT_AREA]
        center_cc = np.argmax(areas) + 1
    clean = (cc == center_cc).astype(np.uint8) * 255
    kernel = np.ones((5,5), np.uint8)
    clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel, iterations=2)
    clean = cv2.morphologyEx(clean, cv2.MORPH_OPEN, kernel, iterations=1)
    contours, _ = cv2.findContours(clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        print(f'[{state}] multicluster: no contours')
        return
    cnt = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(cnt)
    print(f'[{state}] multicluster area={area:.0f}, pts={len(cnt)}, merged={sorted(merged)}')
    vis = arr.copy()
    vis[clean==0] = (vis[clean==0] * 0.5).astype(np.uint8)
    cv2.drawContours(vis, [cnt], -1, (255,0,0), 2)
    out = os.path.join(HERE, f'seg_test_mc_{state}.png')
    Image.fromarray(vis).save(out)

def test_affine_estimate():
    print('\n=== 城市 bbox 扩展法估计仿射精度（仅用于 4 个有 pixels 的州）===')
    db = extract_gcp_db(DIGITIZE)
    for state in ['凉州','并州','幽州','益州']:
        fp = os.path.join(RAW_DIR, f'{state}.geojson')
        gj = json.load(open(fp, encoding='utf-8'))
        gcps = gj['pixels']['gcps']
        cities = db[state]
        print(f'\n{state}:')
        for F in [1.5,1.6,1.7,1.8,1.9,2.0]:
            a,e,c,f = estimate_affine_from_cities(cities, F)
            errs = []
            for g in gcps:
                px_est = (g['lon']-c)/a
                py_est = (g['lat']-f)/e
                errs.append(math.hypot(px_est-g['px'], py_est-g['py']))
            print(f'  city-F={F}: max_err={max(errs):.0f}px avg={sum(errs)/len(errs):.0f}px')
        for G in [1.2,1.3,1.4,1.5,1.6]:
            res = estimate_affine_from_segment(state, cities, G)
            if res is None:
                print(f'  seg-G={G}: segment failed')
                continue
            a,e,c,f = res
            errs = []
            for g in gcps:
                px_est = (g['lon']-c)/a
                py_est = (g['lat']-f)/e
                errs.append(math.hypot(px_est-g['px'], py_est-g['py']))
            print(f'  seg-G={G}: max_err={max(errs):.0f}px avg={sum(errs)/len(errs):.0f}px')
        for G in [1.2,1.3,1.4,1.5,1.6]:
            res = estimate_affine_mean_center(state, cities, G)
            if res is None:
                print(f'  mean-G={G}: segment failed')
                continue
            a,e,c,f = res
            errs = []
            for g in gcps:
                px_est = (g['lon']-c)/a
                py_est = (g['lat']-f)/e
                errs.append(math.hypot(px_est-g['px'], py_est-g['py']))
            print(f'  mean-G={G}: max_err={max(errs):.0f}px avg={sum(errs)/len(errs):.0f}px')

if __name__ == '__main__':
    analyze()
    print('\n=== 颜色分割测试（单阈值）===')
    for s in ['冀州','司隶']:
        test_segment(s, tol=40)
    print('\n=== 颜色分割测试（多聚类合并）===')
    for s in ['司隶','兖州','豫州','徐州','青州','荆州','扬州','交州']:
        test_segment_multicluster(s, k=8, merge_tol=45)
    test_affine_estimate()
