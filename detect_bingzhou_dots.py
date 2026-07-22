"""
精确定位并州.png上的地标白点。
策略: 用模板匹配/特征找文字标签位置 → 找标签附近最近的白圆圈标记
"""
import os, numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(HERE, '汉末十三州地图范例', '并州.png')
OUTDIR = os.path.join(HERE, 'bingzhou_step1_v7c')

pil_img = Image.open(IMG_PATH).convert('RGB')
img = np.array(pil_img)[:, :, ::-1].copy()  # RGB -> BGR for cv2
H, W = img.shape[:2]

# ── 步骤1: 检测所有小的白色空心圆圈(郡治标记) ──
# 特征: 白色小圆环,外径约12-20px,内部是红色底色
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# 二值化: 高亮度=白色
_, white_bin = cv2.threshold(gray, 220, 255, cv2.THRESH_BINARY)

# 膨胀填满圆环内部,然后找实心白斑(=原来圆环覆盖的区域)
k_fill = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9,9))
filled = cv2.dilate(white_bin, k_fill, iterations=2)

# 与原图异或得到环形部分
ring = cv2.bitwise_and(filled, cv2.bitwise_not(white_bin))
# 再清理
ring = cv2.morphologyEx(ring, cv2.MORPH_CLOSE, 
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)), iterations=1)

# 找连通域
n_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(ring, connectivity=8)
print(f'检测到 {n_labels-1} 个环形候选')

markers = []
for i in range(1, n_labels):
    x, y, w, h, area = stats[i]
    cx, cy = centroids[i]
    # 筛选: 小圆环面积约30-400px,接近正方形
    if 25 <= area <= 500 and 6 <= w <= 30 and 6 <= h <= 30:
        aspect = max(w,h)/(min(w,h)+0.01)
        if aspect < 2.5:  # 不能太扁
            markers.append({'cx':int(cx), 'cy':int(cy), 'w':w, 'h':h, 'area':area})

print(f'筛选后 {len(markers)} 个圆形标记')
for i,m in enumerate(markers[:30]):
    print(f'  #{i+1} ({m["cx"]:4d},{m["cy"]:4d}) {m["w"]}x{m["h"]} area={m["area"]}')

# ── 步骤2: 在图上标注所有标记 ──
annotated = pil_img.copy()
draw = ImageDraw.Draw(annotated)
font = ImageFont.truetype('C:/Windows/Fonts/simhei.ttf', 16)
for i, m in enumerate(markers):
    cx, cy = m['cx'], m['cy']
    draw.ellipse([cx-14,cy-14,cx+14,cy+14], outline='lime', width=2)
    draw.ellipse([cx-3,cy-3,cx+3,cy+3], fill='lime')
    draw.text((cx+10, cy-8), str(i+1), fill='yellow', font=font)

out1 = os.path.join(OUTDIR, 'markers_ring_detect.png')
annotated.save(out1)
print(f'\n标记图 -> {out1}')
