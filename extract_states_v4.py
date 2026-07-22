"""
extract_states_v4.py — 从全览-郡级.png正确提取13州边界
方法：粗量化→排除背景海洋→按连通区域提取最大N个块→映射到底图
"""
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from collections import Counter
import json, os, sys

SRC = '汉末十三州地图范例/全览-郡级.png'
OUT_JSON = 'legend_13states.json'
OUT_PREVIEW = 'rendered/v4_states_preview.png'
OUT_TERRAIN = 'rendered/v4_states_on_terrain.png'

# 底图参数
TIF = 'china_full_v3.tif'
BASE_PNG = 'china_full_v3.png'

print('='*60)
print('步骤1：读取全览图')
print('='*60)
im = Image.open(SRC).convert('RGB')
w, h = im.size
arr = np.array(im, dtype=np.uint8)
print(f'  全览图尺寸: {w}x{h}')

print('\n' + '='*60)
print('步骤2：粗量化(48级) + 排除背景/海洋/文字线')
print('='*60)
# 粗量化到48级（每阶48，减少抗锯齿干扰）
q = (arr // 48) * 48
flat = q.reshape(-1, 3)
c = Counter(map(tuple, flat))

# 分析哪些是背景/非州像素
bg_colors = set()
# 更宽松地检测背景（米色/灰白色）
for color, cnt in c.most_common(10):
    r, g, b = [int(x) for x in color]
    # 近白/近灰/米色背景（三通道接近且偏亮）
    if max(r,g,b) > 170 and abs(int(r)-int(g)) < 50 and abs(int(g)-int(b)) < 50 and abs(int(r)-int(b)) < 50:
        bg_colors.add(color)
        print(f'  背景: RGB{color} ({100*cnt/len(flat):.1f}%)')

# 海洋蓝（高B、低RG）
ocean_colors = set()
for color, cnt in c.most_common():
    r, g, b = color
    if b > r + 30 and b > g + 30 and b > 170 and cnt > 500:
        ocean_colors.add(color)
        print(f'  海洋: RGB{color} ({100*cnt/len(flat):.1f}%)')

# 文字/线条（深色或近黑）
line_colors = set()
for color, cnt in c.most_common():
    r, g, b = color
    if r < 80 and g < 80 and b < 80 and cnt > 200:
        line_colors.add(color)
        print(f'  线条/文字: RGB{color} ({100*cnt/len(flat):.1f}%)')

exclude = bg_colors | ocean_colors | line_colors
print(f'\n  排除色数: {len(exclude)} (背景:{len(bg_colors)} 海洋:{len(ocean_colors)} 线条:{len(line_colors)})')

# 创建前景mask
mask = np.ones((h, w), dtype=bool)
for ec in exclude:
    matches = (q[:,:,0] == ec[0]) & (q[:,:,1] == ec[1]) & (q[:,:,2] == ec[2])
    mask &= ~matches

fg_pixels = mask.sum()
print(f'  前景像素: {fg_pixels} ({100*fg_pixels/(w*h):.1f}%)')

print('\n' + '='*60)
print('步骤3：对前景色做k-means(k=15)，获取州的代表色')
print('='*60)
from sklearn.cluster import KMeans

fg_coords = np.argwhere(mask)  # (N, 2) [y,x]
fg_colors_arr = q[mask]       # (N, 3) RGB

if len(fg_colors_arr) > 50000:
    # 下采样加速
    idx = np.random.choice(len(fg_colors_arr), 50000, replace=False)
    sample = fg_colors_arr[idx].astype(float)
else:
    sample = fg_colors_arr.astype(float)

km = KMeans(n_clusters=15, random_state=42, n_init=10)
labels_full = km.fit_predict(fg_colors_arr.astype(float))
centers = km.cluster_centers_.astype(int)

print('  15个聚类中心:')
for i in range(15):
    cnt = (labels_full == i).sum()
    col = tuple(centers[i])
    print(f'    簇{i}: RGB{col} 像素={cnt} ({100*cnt/len(labels_full):.1f}%)')

print('\n' + '='*60)
print('步骤4：为每个聚类找最大连通区域 → 得到州候选')
print('='*60)
from scipy import ndimage

state_masks = []
state_info = []

for i in range(15):
    cluster_mask = np.zeros((h, w), dtype=bool)
    cluster_mask[mask] = (labels_full == i)

    # 形态学闭运算（填补小空洞）
    from scipy.ndimage import binary_closing, binary_dilation, binary_erosion
    cluster_mask = binary_closing(cluster_mask, iterations=2)

    # 连通区域标记
    labeled, n_components = ndimage.label(cluster_mask)
    if n_components == 0:
        continue

    # 取最大连通块
    component_sizes = ndimage.sum(cluster_mask, labeled, range(1, n_components + 1))
    largest_label = np.argmax(component_sizes) + 1
    largest_mask = (labeled == largest_label)

    area = largest_mask.sum()
    if area < 5000:  # 太小的碎片忽略（提高阈值）
        continue

    state_masks.append(largest_mask)
    state_info.append({
        'cluster_id': i,
        'color': centers[i].tolist(),
        'area': int(area),
        'n_components': n_components,
    })
    print(f'  候选{len(state_info)-1}: 簇{i} RGB{tuple(centers[i])} 面积={area}px {n_components}个连通块')

print(f'\n  共得到 {len(state_infos := state_info)} 个有效州候选')

# 如果不是13个，尝试合并最小的或拆分最大的
if len(state_info) != 13:
    print(f'  [!] 得到{len(state_info)}个而非13个，需要调整...')

print('\n' + '='*60)
print('步骤5：提取每个州的外轮廓')
print('='*60)
from skimage.measure import find_contours

states_data = {'src': SRC, 'method': 'kmeans15+connected_components', 'size': [w, h], 'states': {}}

preview = Image.new('RGBA', (w, h), (255, 255, 255, 0))
draw_prev = ImageDraw.Draw(preview)

for idx, smask in enumerate(state_masks):
    info = state_info[idx]
    color = tuple(info['color'])

    # 在量化图上提取轮廓（更干净）
    temp = np.zeros((h, w), dtype=np.uint8)
    temp[smask] = 255
    temp_img = Image.fromarray(temp)

    try:
        contours = find_contours(temp, 0.5)
    except:
        contours = []

    if not contours:
        print(f'  州{idx}: 无轮廓!')
        continue

    # 取最长外轮廓（外边界）
    main_contour = max(contours, key=len)

    # 简化轮廓（减少点数）
    step = max(1, len(main_contour) // 300)
    simple = main_contour[::step]

    # 转换为整数坐标
    pts = [(int(p[1]), int(p[0])) for p in simple]  # (x, y)

    # 绘制预览（用州色填充+描边）
    draw_prev.polygon(pts, fill=color + (120,), outline=(50, 50, 50, 200))

    # 计算质心
    ys = [p[0] for p in main_contour]
    xs = [p[1] for p in main_contour]
    cy, cx = np.mean(ys), np.mean(xs)

    state_key = f'state_{idx}'
    states_data['states'][state_key] = {
        'color': color,
        'area': info['area'],
        'centroid_px': [round(float(cx), 1), round(float(cy), 1)],
        'contour_pts': [[int(p[1]), int(p[0])] for p in simple],  # [x,y] pairs
        'n_points': len(pts),
    }
    print(f'  州{idx}: {len(pts)}个折点, 质心({cx:.0f},{cy:.0f}), 面积{info["area"]}')

preview.save(OUT_PREVIEW)
print(f'\n  预览已保存: {OUT_PREVIEW}')

with open(OUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(states_data, f, ensure_ascii=False, indent=2)
print(f'  数据已保存: {OUT_JSON}')

print('\n' + '='*60)
print('步骤6：叠加到底图（假设范围校准）')
print('='*60)
# 先确定图例的地理范围
# 从图上特征推断：
# - 左边缘约东经73°（帕米尔/葱岭附近，敦煌以西）
# - 右边缘约东经135°（朝鲜半岛东端）
# - 上边缘约北纬53°（贝加尔湖以北）
# - 下边缘约北纬15°（日南/越南南端）

LON_RANGE = (74, 134)  # 经度范围
LAT_RANGE = (14, 54)   # 纬度范围

def px_to_lonlat(px, py, w=w, h=h, lon_r=LON_RANGE, lat_r=LAT_RANGE):
    """像素坐标→经纬度"""
    lon = lon_r[0] + (px / w) * (lon_r[1] - lon_r[0])
    lat = lat_r[1] - (py / h) * (lat_r[1] - lat_r[0])  # y轴翻转
    return lon, lat

def lonlat_to_px(lon, lat, tw, th):
    """经纬度→底图像素坐标（底图: china_full_v3.tif）"""
    # 底图范围（从rasterio读取过）
    TIF_LON = (75.0, 140.0)
    TIF_LAT = (15.0, 55.0)
    px = (lon - TIF_LON[0]) / (TIF_LON[1] - TIF_LON[0]) * tw
    py = (TIF_LAT[1] - lat) / (TIF_LAT[1] - TIF_LAT[0]) * th
    return px, py

base = Image.open(BASE_PNG).convert('RGBA')
tw, th = base.size
overlay = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
draw_o = ImageDraw.Draw(overlay)

print(f'  底图: {tw}x{th}')
print(f'  图例→底图: ({w},{h})→({tw},{th})')
print(f'  假设图例范围: 经度{LON_RANGE}, 纬度{LAT_RANGE}')

for skey, sdata in states_data['states'].items():
    pts = sdata['contour_pts']
    if not pts or len(pts) < 3:
        continue

    # 转换坐标：图例像素 → 经纬度 → 底图像素
    mapped = []
    for x, y in pts:
        lon, lat = px_to_lonlat(x, y)
        mx, my = lonlat_to_px(lon, lat, tw, th)
        mapped.append((mx, my))

    color = tuple(sdata['color']) + (80, 100)  # 半透明填充
    outline_color = (80, 40, 40, 220)
    draw_o.polygon(mapped, fill=(sdata['color'][0], sdata['color'][1], sdata['color'][2], 60),
                   outline=outline_color, width=2)

    cx_pix, cy_pix = lonlat_to_px(*sdata['centroid_px'], tw, th)
    draw_o.text((cx_pix-20, cy_pix-10), skey, fill=(0, 0, 0, 200))

# 合成
result = Image.alpha_composite(base, overlay)
result.save(OUT_TERRAIN)
print(f'  地形叠加已保存: {OUT_TERRAIN}')
print('\n完成！')
