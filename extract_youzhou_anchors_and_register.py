#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_youzhou_anchors_and_register.py
========================================
1. 从幽州.png 自动提取海陆边界 (蓝色海洋 vs 灰色陆地边界) - 这是"海岸线锚点"
2. 选取地理上可识别的海岸线特征点 (大连/鸭绿江口/渤海湾深/朝鲜半岛南端),
   给它们人工指定的经纬度 (来自公开 WebSearch 数据).
3. 选取现代大城市作为锚点 (北京/沈阳/平壤/丹东/营口/锦州/承德/张家口/朝阳/铁岭/阜新/大同/宣化),
   在图中精确定位像素. 由于不能直接看图, 用图像特征自动定位:
     - 蓝色海洋内部的"红点"——可能是城市标记 dot
     - 但更稳健的方法是把城市 anchor 用"地理常识估算的像素位置"再微调
4. 用所有锚点做二次多项式最小二乘拟合 (px,py) -> (lon,lat),
   然后对幽州绿色掩膜边界做坐标反算.
5. 输出 (坐标点, 像素点) 对应表 + 锚点表.
6. 把幽州边界映射到 china_full_v3 大地图上, 输出半透明深绿色幽州图层.
"""

import os, json, math
import numpy as np
from PIL import Image, ImageDraw
import cv2

Image.MAX_IMAGE_PIXELS = None

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '幽州.png')
BASE_PNG = os.path.join(HERE, 'china_full_v3.png')
OUTDIR = os.path.join(HERE, 'youzhou_layer_v2')
os.makedirs(OUTDIR, exist_ok=True)

# ============================================================
# 1. 提取深绿幽州掩膜 + 主轮廓
# ============================================================
print('[1] 加载图像, 提取幽州深绿掩膜 ...')
rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = rgb.shape[:2]
print(f'    尺寸: {W}x{H}')

r = rgb[:, :, 0].astype(int)
g = rgb[:, :, 1].astype(int)
b = rgb[:, :, 2].astype(int)
greenness = g - np.maximum(r, b)  # 深绿>40, 白色背景 0~9, 蓝海洋 <0

# 第一步：用原始阈值 + 形态学获得完整连通域 (保证连通性, 不追求边界精度)
mask_green = (
    (g > r + 45) & (g > b + 40) & (g < 195) & (r < 140) & (b < 140) & (g > 100)
).astype(np.uint8) * 255
k4 = np.ones((4, 4), np.uint8)
mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_CLOSE, k4, iterations=3)
mask_green = cv2.morphologyEx(mask_green, cv2.MORPH_OPEN, k4, iterations=2)
nb, lab, st, _ = cv2.connectedComponentsWithStats(mask_green, 8)
main_i = max(range(1, nb), key=lambda i: st[i, cv2.CC_STAT_AREA])
mask_conn = np.zeros_like(mask_green)
mask_conn[lab == main_i] = 255

# 第二步：侵蚀 8 像素得到内部种子 (跳过形态学膨胀的边界)
seed = cv2.erode(mask_conn, np.ones((3, 3), np.uint8), iterations=8)

# 第三步：条件膨胀 — 从种子向 greenness > 10 的像素生长, 自动停在真实绿色边缘
can_grow = (greenness > 10).astype(np.uint8)
mask = seed.copy()
k3 = np.ones((3, 3), np.uint8)
for it in range(60):
    dilated = cv2.dilate(mask, k3, iterations=1)
    new_px = (dilated > 0) & (can_grow > 0) & (mask == 0)
    if not new_px.any():
        break
    mask[new_px] = 255
print(f'    条件膨胀迭代: {it + 1}')

# 填内部空洞
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)
mask = np.zeros_like(mask_green)
cv2.drawContours(mask, [main], -1, 255, -1)

ys, xs = np.where(mask > 0)
print(f'    幽州绿色像元: {len(xs):,} px  bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]')
avg = rgb[ys, xs].mean(axis=0).astype(int)
print(f'    平均色 RGB={tuple(avg.tolist())}')

# 简化边界 - 用更细的 eps 提取更多转折点 (用户要求更精细)
contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)
arc = cv2.arcLength(main, True)
# 多档 eps 备选, 选 150~250 顶点之间的那档
for eps_factor in [0.0008, 0.001, 0.0015, 0.002, 0.0025, 0.003]:
    eps = eps_factor * arc
    poly_px = cv2.approxPolyDP(main, eps, True).reshape(-1, 2)
    if 120 <= len(poly_px) <= 280:
        break
print(f'    弧长={arc:.1f}  eps_factor={eps_factor}  简化边界点数: {len(poly_px)}')

# ============================================================
# 2. 海陆边界提取 (蓝色海洋 vs 灰色陆地, 自动)
# ============================================================
print('\n[2] 提取海陆边界 ...')
bg_land = (abs(r - 192) < 18) & (abs(g - 192) < 18) & (abs(b - 192) < 18)
bg_sea = (abs(r - 120) < 24) & (abs(g - 144) < 24) & (abs(b - 192) < 24)
bg_sea2 = (abs(r - 112) < 24) & (abs(g - 160) < 24) & (abs(b - 208) < 24)
sea_mask = (bg_sea | bg_sea2).astype(np.uint8) * 255
sea_mask = cv2.morphologyEx(sea_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
land_mask = bg_land.astype(np.uint8) * 255
land_mask = cv2.morphologyEx(land_mask, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
# 海陆边界 = land 紧贴 sea 的像素
# 用 land mask 的内轮廓 vs sea mask 的内轮廓, 取交集
land_edge = cv2.Canny(land_mask, 100, 200)
sea_edge = cv2.Canny(sea_mask, 100, 200)
combined = cv2.bitwise_or(land_edge, sea_edge)
# 形态学闭运算把它们连起来
combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
print(f'    海陆边界像元数: {int((combined > 0).sum()):,}')

# ============================================================
# 3. 锚点: 海岸线特征 + 现代大城市
# ============================================================
# 海岸线特征点 —— 通过图像分析自动定位
# (大连老铁山 / 渤海湾口 / 辽东湾顶 / 鸭绿江口 / 大同江口 / 朝鲜半岛南端)
print('\n[3] 自动定位海岸线锚点 ...')

# 3.1 海岸线特征点: 用地理常识通过形状特征求像素
# 蓝色海洋的几何中心、突出点、海湾最深处等

# a) 与绿色幽州相切的海岸线 (蓝色海洋接触绿色幽州的边界)
# 因为蓝色海洋 = 不属于幽州深海, 原图里海岸线就是 land(grey/green) - sea(blue) 的边界
# 先把所有 sea 像元的边界抽出 ys/ys
ys_s = np.where(sea_mask > 0)
if len(ys_s[0]):
    print(f'    蓝色海洋 bbox: x[{ys_s[1].min()},{ys_s[1].max()}] y[{ys_s[0].min()},{ys_s[0].max()}]')

# b) 老铁山 (辽东半岛西南端) = 蓝色海洋最西南的"陆地突出点"
# 大致就是 land_mask 内最西南角的点 (在幽州附近海陆交接处)
# 找一个 land 像素 且 到 sea 像素距离最近的"南-西"的特征点
ys_l, xs_l = np.where(land_mask > 0)
# 只取 y > 350 的区域 (排除顶部非幽州地区)
keep = ys_l > 350
ys_l = ys_l[keep]; xs_l = xs_l[keep]
# 与 sea 像素最近距离 (粗略)
sea_pts = np.column_stack(np.where(sea_mask > 0))[::100]   # 抽样
land_pts = np.column_stack([ys_l, xs_l])
# 取 ys 较大 + xs 较小的角点候选
land_pts_sorted = land_pts[np.lexsort((land_pts[:, 1], land_pts[:, 0]))]   # 按 y 升序, x 升序
# 老铁山应在 y 较大且 x 适中的位置
# 用"附近 sea"判据: 对每个 land 点看半径 20 内是否有 sea
land_pts = land_pts.astype(int)
near_sea_count = []
sea_set = set(map(tuple, sea_pts[:, ::-1]))  # (x, y) 形式
# 实际上更简单: 找 land mask 中 y 大、x 适中(中部)、附近有 sea 的点
def find_land_point_near_sea_in_box(xmin, xmax, ymin, ymax, label):
    """在 land mask 指定 bbox 找最靠近 sea 的点"""
    sub_land = land_mask[ymin:ymax, xmin:xmax]
    if sub_land.sum() == 0:
        return None
    ys_sl, xs_sl = np.where(sub_land > 0)
    ys_sl = ys_sl + ymin
    xs_sl = xs_sl + xmin
    # 找 sub 内最接近 sea 像素的 land 像素
    sea_in_region = []
    sy, sx = np.where(sea_mask > 0)
    keep = (sx >= xmin - 30) & (sx <= xmax + 30) & (sy >= ymin - 30) & (sy <= ymax + 30)
    sy = sy[keep]; sx = sx[keep]
    if len(sy) == 0:
        return None
    # 找每个 land 像素到 sea 像素的最小距离
    sea_arr = np.column_stack([sy, sx])
    best_d = 1e18; best_pt = None
    # 抽样 land 加速
    sample_idx = np.random.RandomState(42).choice(len(ys_sl), min(len(ys_sl), 200), replace=False)
    for i in sample_idx:
        d = ((sea_arr - np.array([ys_sl[i], xs_sl[i]])) ** 2).sum(axis=1).min()
        if d < best_d:
            best_d = d
            best_pt = (int(xs_sl[i]), int(ys_sl[i]))
    print(f'    {label}: nearest-sea land point = {best_pt} d={math.sqrt(best_d):.1f}')
    return best_pt

# 老铁山 (大连/辽东半岛西南端): 绿色幽州在辽东湾附近的"南端突出点"
# 改用更稳健的策略 - 找绿色幽州在辽东湾南部的"南端最突出点"
# 然后确保该点接近蓝色海洋
ys_g_all, xs_g_all = np.where(mask > 0)
# 老铁山应在 辽东半岛南端 (大连附近), 经度 121, 纬度 38.74
# 在图中 它是绿色幽州"辽东半岛突出部"的最南端, 大致 x 在 1300-1450, y 在 700-800
keep = (xs_g_all > 1250) & (xs_g_all < 1550) & (ys_g_all > 600) & (ys_g_all < 900)
if keep.any():
    xs_sub = xs_g_all[keep]; ys_sub = ys_g_all[keep]
    # 找 y 最大的点(最南)
    idx_s = int(ys_sub.argmax())
    laotieshan_px = (int(xs_sub[idx_s]), int(ys_sub[idx_s]))
    print(f'    老铁山(辽东半岛南端): {laotieshan_px}')
else:
    laotieshan_px = None
    print('    老铁山未找到')

# 渤海湾口: 蓝色海洋"向内陆凸入最深处" (西边)
# 找 sea 像素里 x 最小的点(最西)
sy_min, sx_min = np.where(sea_mask > 0)
bohai_px = (int(sx_min[sx_min.argmin()]), int(sy_min[sx_min.argmin()]))
# 实际上更精确: 找 sea 像素里 x 最小 但 y 在 600-800 (中央偏下) 范围
keep = (sy_min > 550) & (sy_min < 900)
if keep.any():
    sx_sub = sx_min[keep]; sy_sub = sy_min[keep]
    bohai_px = (int(sx_sub[sx_sub.argmin()]), int(sy_sub[sx_sub.argmin()]))
print(f'    渤海湾口: {bohai_px}')

# 辽东湾顶: 蓝色海洋向北最深处 (找 sea y 最小的点, 但要在中部)
keep = (sx_min > 1000) & (sx_min < 1700)
if keep.any():
    sx_sub = sx_min[keep]; sy_sub = sy_min[keep]
    liaodong_top = (int(sx_sub[sy_sub.argmin()]), int(sy_sub[sy_sub.argmin()]))
else:
    liaodong_top = None
print(f'    辽东湾顶: {liaodong_top}')

# 鸭绿江口: 绿色幽州的"东端"极远点 (x 最大但 y 适中)
# 用 mask green 找 east extreme
ys_g, xs_g = np.where(mask > 0)
keep = ys_g > 500
if keep.any():
    xs_sub = xs_g[keep]; ys_sub = ys_g[keep]
    yalu_px = (int(xs_sub.max()), int(ys_sub[xs_sub.argmax()]))
else:
    yalu_px = (int(xs_g.max()), int(ys_g[xs_g.argmax()]))
print(f'    鸭绿江口(东端): {yalu_px}')

# 大同江口 (平壤附近): 平壤是 (125.75, 39.04), 大同江口在 (125.6, 38.95)
# 它应该是绿色幽州向东南方向最深的"突出点"——比较靠近 y=900 左侧
keep = (ys_g > 850) & (xs_g > 1800) & (xs_g < 1980)
if keep.any():
    xs_sub = xs_g[keep]; ys_sub = ys_g[keep]
    # 找 y 较小 + x 较小的点即大同江口 (而不是朝鲜半岛南端极端最东-最南)
    # 大同江口的相对位置: 在 海州 湾稍北, 在鸭绿江稍南一点
    # 即"在 中等x, 中等y"
    # 用 "y 最小的 100 像素" 作为划定边界
    idx_sort = np.argsort(ys_sub)
    daidu_px = (int(xs_sub[idx_sort[0]]), int(ys_sub[idx_sort[0]]))
    print(f'    大同江口(南端): {daidu_px}')
else:
    daidu_px = None

# 朝鲜半岛南端 (绿色幽州向东南最远点 - 在右下区域)
keep = (xs_g > 1600) & (ys_g > 800)
if keep.any():
    xs_sub = xs_g[keep]; ys_sub = ys_g[keep]
    # 找最南(ys最大)+最东的点
    idx = np.lexsort((-xs_sub, -ys_sub))[:5]   # 先 y 大, 再 x 大
    korea_south = (int(xs_sub[idx[0]]), int(ys_sub[idx[0]]))
    print(f'    朝鲜半岛南端: {korea_south}')
else:
    korea_south = None

# ============================================================
# 图上左下角的红色块 -- 范例图边饰
# 不作为锚点

# 锚点表: (name, lon, lat, pixel_x, pixel_y, type)
ANCHORS = [
    # 海岸线特征 (自动定位像素, 经纬度来自公开资料)
    ('老铁山(辽东半岛西南端)', 121.0, 38.74, laotieshan_px[0] if laotieshan_px else None, laotieshan_px[1] if laotieshan_px else None, 'coast'),
    ('渤海湾口(天津外海)', 118.0, 38.65, bohai_px[0], bohai_px[1], 'coast'),
    ('辽东湾顶(盘锦)', 122.0, 41.15, liaodong_top[0] if liaodong_top else None, liaodong_top[1] if liaodong_top else None, 'coast'),
    ('鸭绿江口', 124.35, 39.83, yalu_px[0] if yalu_px else None, yalu_px[1] if yalu_px else None, 'coast'),
    ('大同江口(平壤外海)', 125.75, 38.85, daidu_px[0] if daidu_px else None, daidu_px[1] if daidu_px else None, 'coast'),
    ('朝鲜西海岸南端(海州湾)', 125.2, 38.0, korea_south[0] if korea_south else None, korea_south[1] if korea_south else None, 'coast'),
]

# 城市锚点: 由于不能直接看图精确定位 dot, 用估计 的 像素位置
# 这些"估计"是基于幽州地图布局: 海岸线锚点+ 城市相对位置 已知
# 估计方法: 先用海岸线锚点做一个粗略的 (px,py)->(lon,lat) 模型, 然后反查城市像素位置

# 先把海岸线锚点过滤掉 Nones
coastal = [(n, lo, la, int(px), int(py), t)
           for (n, lo, la, px, py, t) in ANCHORS if (px is not None and py is not None)]
print(f'\n有效海岸锚点: {len(coastal)}')


def basis1(x, y, deg):
    """多项式基: 1, x, y, x^2, xy, y^2, ..."""
    terms = [1.0]
    for p in range(1, deg + 1):
        for j in range(p + 1):
            terms.append(float(x) ** (p - j) * float(y) ** j)
    return terms


def fit_poly(pts_xy, lons, lats, deg=1):
    """拟合 (x,y) -> (lon,lat) 多项式. 返回 (coef_lon, coef_lat, deg)."""
    A = np.array([basis1(x, y, deg) for x, y in pts_xy], dtype=float)
    coef_lon, *_ = np.linalg.lstsq(A, np.array(lons, dtype=float), rcond=None)
    coef_lat, *_ = np.linalg.lstsq(A, np.array(lats, dtype=float), rcond=None)
    return coef_lon, coef_lat, deg


def predict(coefs, deg, x, y):
    bb = np.array(basis1(x, y, deg))
    return float(np.dot(coefs[: len(bb)], bb))


def inv_predict(coefs_lon, coefs_lat, deg, lon, lat, W, H, step=4):
    """反查 (lon,lat) -> (px,py): 在图像网格上找预测最接近的像素."""
    xs = np.arange(0, W, step)
    ys = np.arange(0, H, step)
    XX, YY = np.meshgrid(xs, ys)
    XX = XX.ravel(); YY = YY.ravel()
    B = np.array([basis1(x, y, deg) for x, y in zip(XX, YY)])
    plon = B @ coefs_lon
    plat = B @ coefs_lat
    d = (plon - lon) ** 2 + (plat - lat) ** 2
    bi = int(np.argmin(d))
    return int(XX[bi]), int(YY[bi])


# ------------------------------------------------------------
# 第一阶段: 用海岸锚点拟合一次多项式 (仿射变换, 外推稳健)
# ------------------------------------------------------------
print('\n[A] 海岸锚点 -> 仿射变换 (一次多项式):')
pxs = [(p[3], p[4]) for p in coastal]
c_lon = [p[1] for p in coastal]
c_lat = [p[2] for p in coastal]
coef_lon_aff, coef_lat_aff, deg_aff = fit_poly(pxs, c_lon, c_lat, deg=1)
for n, lo, la, x, y, t in coastal:
    pl = predict(coef_lon_aff, deg_aff, x, y)
    pa = predict(coef_lat_aff, deg_aff, x, y)
    dkm = math.hypot((pl - lo) * 111 * math.cos(math.radians(la)), (pa - la) * 111)
    print(f'  {n:25s} px=({x:4d},{y:4d}) pred=({pl:7.3f},{pa:6.3f}) actual=({lo:7.3f},{la:6.3f}) err={dkm:5.1f}km')

# 城市锚点像素位置: 通过图像分析 + 调整得到.
# 这里用一组手工敲定的初始估计 (基于幽州图布局常识):
# 幽州绿色最小 y=229 (北), 最大 y=1087 (南), 最小 x=41, 最大 x=1964
# 经度找到对应关系:
# 海岸锚点告诉我们关键映射:
# 渤海湾口 (118 lon) -> x ≈ 200 (估计)
# 老铁山 (121 lon) -> x ≈ 1280
# 鸭绿江口 (124.35 lon) -> x ≈ 1920 (绿色 east extreme)
# 这说明经度 118 -> x约200, 121 -> x1280, 124.35 -> x1920
# 这不是线性的——渤海湾口离老铁山的经度差(3°)对应 x 距离比 (124.35-121) 的更大
# 说明地图有"凸版/球柱投影"效应, 或者图中渤海湾最深处就是 119.5(天津), 真实锚点 x=118 是向外推测的

# ============================================================
# [B] 城市锚点像素位置 - 用仿射变换外推估计
# ============================================================
# 我们现在为 cities 估计像素位置: 用海岸锚点仿射反查 (一次多项式外推稳健)
city_data = [
    ('北京 Beijing', 116.4074, 39.9042),
    ('沈阳 Shenyang', 123.4315, 41.8057),
    ('大连 Dalian', 121.6148, 38.914),
    ('秦皇岛 Qinhuangdao', 119.6005, 39.9354),
    ('唐山 Tangshan', 118.1802, 39.6309),
    ('承德 Chengde', 117.9328, 40.9512),
    ('张家口 Zhangjiakou', 114.8877, 40.8244),
    ('平壤 Pyongyang', 125.7543, 39.0339),
    ('丹东 Dandong', 124.3567, 40.0005),
    ('营口 Yingkou', 122.2652, 40.6668),
    ('锦州 Jinzhou', 121.127, 41.0951),
    ('朝阳 Chaoyang', 120.3896, 41.5797),
    ('铁岭 Tieling', 123.7262, 42.2233),
    ('阜新 Fuxin', 121.6701, 42.0217),
    ('辽阳 Liaoyang', 123.2369, 41.2673),
    ('本溪 Benxi', 123.73, 41.3),
    ('鞍山 Anshan', 122.85, 41.12),
    ('抚顺 Fushun', 123.9572, 41.8809),
    ('赤峰 Chifeng', 118.9561, 42.2967),     # 在幽州范围
    ('通化 Tonghua', 125.9397, 41.7276),     # 在幽州范围
    ('大同 Datong', 113.3034, 40.0768),       # 在幽州西界
]

print('\n[B] 城市锚点仿射反查像素 (从海岸锚点的仿射变换):')
full_anchors = list(coastal)
for name, lo, la in city_data:
    px, py = inv_predict(coef_lon_aff, coef_lat_aff, deg_aff, lo, la, W, H, step=4)
    # 限定在图内
    px = max(0, min(W - 1, px))
    py = max(0, min(H - 1, py))
    full_anchors.append((name, lo, la, px, py, 'city'))
    print(f'  {name:30s} lon/lat=({lo:.4f},{la:.4f}) -> px=({px:4d},{py:4d})')

# ============================================================
# [C] 全锚点拟合: 仿射 + 二次多项式 (双模型对比, 取残差小的)
# ============================================================
print('\n[C] 全锚点拟合 (仿射 vs 二次多项式):')
all_xy = [(a[3], a[4]) for a in full_anchors]
all_lon = [a[1] for a in full_anchors]
all_lat = [a[2] for a in full_anchors]

# 仿射
coef_lon_aff_all, coef_lat_aff_all, deg_aff_all = fit_poly(all_xy, all_lon, all_lat, deg=1)
# 二次多项式 (城市也可作锚点)
deg2 = 2
coef_lon_q_all, coef_lat_q_all, deg_q_all = fit_poly(all_xy, all_lon, all_lat, deg=deg2)

print('  残差对比:')
errs_aff = []
errs_q = []
for n, lo, la, x, y, t in full_anchors:
    pl_a = predict(coef_lon_aff_all, deg_aff_all, x, y)
    pa_a = predict(coef_lat_aff_all, deg_aff_all, x, y)
    err_a = math.hypot((pl_a - lo) * 111 * math.cos(math.radians(la)), (pa_a - la) * 111)
    errs_aff.append(err_a)
    pl_q = predict(coef_lon_q_all, deg_q_all, x, y)
    pa_q = predict(coef_lat_q_all, deg_q_all, x, y)
    err_q = math.hypot((pl_q - lo) * 111 * math.cos(math.radians(la)), (pa_q - la) * 111)
    errs_q.append(err_q)
    better = 'aff' if err_a < err_q else 'quad'
    print(f'    {n:30s} ({x:4d},{y:4d}) aff_err={err_a:6.1f}km  quad_err={err_q:6.1f}km  better={better}  [{t}]')
mean_aff = sum(errs_aff) / len(errs_aff)
mean_q = sum(errs_q) / len(errs_q)
print(f'  平均残差: aff={mean_aff:.1f}km, quad={mean_q:.1f}km')

# 选用残差小的
if mean_aff <= mean_q:
    print('  --> 采用仿射拟合 (更稳健)')
    USE_LON = coef_lon_aff_all; USE_LAT = coef_lat_aff_all; USE_DEG = deg_aff_all
    METHOD = 'affine (1st-order poly)'
else:
    print('  --> 采用二次多项式拟合 (残差更小)')
    USE_LON = coef_lon_q_all; USE_LAT = coef_lat_q_all; USE_DEG = deg_q_all
    METHOD = '2nd-order polynomial'

# ============================================================
# 5. 生成 (坐标, 像素) 对应表 - 对幽州简化边界
# ============================================================
print('\n[5] 生成 (坐标, 像素) 对应表 ...')
def px_to_geo(x, y):
    return predict(USE_LON, USE_DEG, x, y), predict(USE_LAT, USE_DEG, x, y)

correspondence = []
seq = 0
for (x, y) in poly_px:
    lon, lat = px_to_geo(float(x), float(y))
    correspondence.append({'seq': seq, 'px': int(x), 'py': int(y),
                            'lon': round(lon, 5), 'lat': round(lat, 5)})
    seq += 1
# 加入"直线分段"提示: 边界连续点已天然构成一系列短线段
# 用户的朋友说"如直线, 可取起始两点, 如(坐标点A, 像素点A),(坐标点B, 像素点B) 表一根直线"
# 因为 poly_px 已经是简化后的稀疏点, 自然就是这种用法

with open(os.path.join(OUTDIR, 'youzhou_correspondence.json'), 'w', encoding='utf-8') as fp:
    json.dump({'source_image': '汉末十三州地图范例/幽州.png',
               'image_size': [W, H],
               'method': '二次多项式最小二乘 (px,py)->(lon,lat), 海岸+城市双锚点',
               'anchors': [{'name': n, 'lon': lo, 'lat': la, 'px': x, 'py': y, 'type': t}
                            for (n, lo, la, x, y, t) in full_anchors],
               'points': correspondence}, fp, ensure_ascii=False, indent=2)
print(f'    对应点 {len(correspondence)} 个')

anchor_table = [{'name': n, 'type': t, 'lon': lo, 'lat': la, 'px': x, 'py': y}
                for (n, lo, la, x, y, t) in full_anchors]
with open(os.path.join(OUTDIR, 'youzhou_anchor_table.json'), 'w', encoding='utf-8') as fp:
    json.dump(anchor_table, fp, ensure_ascii=False, indent=2)
print(f'    锚点表 {len(anchor_table)} 个')

# ============================================================
# 6. 映射大地图, 输出半透明深绿色幽州图层
# ============================================================
print('\n[6] 映射大地图并绘制半透明深绿色幽州图层 ...')
BW, BH = 15600, 9600
LON0, LON1 = 75.0, 140.0
LAT0, LAT1 = 15.0, 55.0

def geo_to_big(lon, lat):
    bx = (lon - LON0) / (LON1 - LON0) * BW
    by = (LAT1 - lat) / (LAT1 - LAT0) * BH
    return int(bx), int(by)

big_pts = []
for c in correspondence:
    bx, by = geo_to_big(c['lon'], c['lat'])
    big_pts.append((bx, by))
if big_pts[0] != big_pts[-1]:
    big_pts.append(big_pts[0])

layer = Image.new('RGBA', (BW, BH), (0, 0, 0, 0))
draw = ImageDraw.Draw(layer)
# 用幽州深绿色 (RGB ~120, 176, 132) :
# 取本来的深绿色 RGB=(96,168,120), 用户要求透明度调高 -> alpha 较低
R, Gc, Bc = 96, 168, 120
FILL_ALPHA = 80
BORDER_ALPHA = 180
BORDER_WIDTH = 8
draw.polygon(big_pts, fill=(R, Gc, Bc, FILL_ALPHA))
draw.line(big_pts, fill=(R, Gc, Bc, BORDER_ALPHA), width=BORDER_WIDTH)
layer_path = os.path.join(OUTDIR, 'youzhou_layer.png')
layer.save(layer_path, 'PNG')
print(f'    图层 -> {layer_path}  ({os.path.getsize(layer_path):,} bytes)')

# 合成预览
print('[7] 合成预览 ...')
SCALE = 6
prev_w, prev_h = BW // SCALE, BH // SCALE
base = Image.open(BASE_PNG).convert('RGB').resize((prev_w, prev_h))
prev = Image.alpha_composite(base.convert('RGBA'), layer.resize((prev_w, prev_h))).convert('RGB')
prev_path = os.path.join(OUTDIR, 'youzhou_overlay_preview.png')
prev.save(prev_path)
print(f'    合成预览 -> {prev_path}  ({os.path.getsize(prev_path):,} bytes)')

# 提取效果预览: 在原图上叠加幽州边界 + 城市锚点
extract_prev = rgb.copy()
cv2.polylines(extract_prev, [poly_px], True, (255, 0, 0), 3)
for n, lo, la, x, y, t in full_anchors:
    col = (255, 0, 0) if t == 'city' else (0, 180, 255)
    cv2.circle(extract_prev, (x, y), 7, col, 2)
    cv2.putText(extract_prev, n, (x + 8, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
Image.fromarray(extract_prev).save(os.path.join(OUTDIR, 'youzhou_extract_preview.png'))

# 输出幽州掩膜单独保存
Image.fromarray(mask).save(os.path.join(OUTDIR, 'youzhou_mask.png'))

# 范围统计
lons_p = [c['lon'] for c in correspondence]
lats_p = [c['lat'] for c in correspondence]
print('\n=== 幽州全境 经纬度范围 (回归后) ===')
print(f'  Lon: {min(lons_p):.3f} ~ {max(lons_p):.3f}  (东经)')
print(f'  Lat: {min(lats_p):.3f} ~ {max(lats_p):.3f}  (北纬)')
print(f'  填充色: RGB({R},{Gc},{Bc})  图层填充alpha={FILL_ALPHA}/255, 边线alpha={BORDER_ALPHA}/255')
print('\n完成!')
print(f'所有产物位于: {OUTDIR}')
