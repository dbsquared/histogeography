#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Step 1 v5: 冀州.png 叠加层剥离 + 形状低通滤波提取。

=========================================================================
根因分析（用户反复反馈的问题）：
  问题A: 背景道路线(橙色2-5px细线)切过青色区 → 边界沿线形成向内锯齿
  问题B: 文字标签(暗色方块)压在边界上/旁边 → 边界形成小凸起方块

  根本原因：源图不是纯净历史州界色块图，而是"历史底色 + 现代路网 +
             现代地名标注 + 行政界线"的叠加图。之前的提取把所有像素
             一视同仁，导致边界被这些叠加物带着跑。

  v4的错误：用B样条/平滑做后处理 → 把本来对的地方也搞坏了，
            而且无法区分"真实的边界弯曲"和"叠加物造成的伪特征"

=========================================================================
v5 方案：叠加层无关(Overlay-Agnostic) 提取

  Phase 1: 叠加层检测与剥离
    - 道路线检测：橙色细线(R>160, G>100, B<140, 细长形态学)
    - 文字检测：暗色连通域(灰度<100, 面积20~2000px)
    - 白线/灰线检测：亮色细线
    - 用 cv2.inpaint 将所有叠加区域替换为周围颜色

  Phase 2: 在干净图上提取青色色块（复用v3的宽松阈值+邻州排除）

  Phase 3: 形状低通滤波 (关键!)
    - 大核闭运算 25×25: 填充道路宽度(~5px)和文字大小(~15px)的缺口
    - 大核开运算 17×17: 切掉同等尺度的外突
    - 这相当于对形状做低通滤波，只保留真实州界的大尺度特征

  Phase 4: 边界提取 + 文字拉平 + 输出
"""
import os, json, math
import numpy as np
import cv2
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '汉末十三州地图范例', '冀州.png')
OUTDIR = os.path.join(HERE, 'jizhou_step1_v5')
os.makedirs(OUTDIR, exist_ok=True)

# ============================================================
# 0. 读图
# ============================================================
rgb = np.array(Image.open(SRC).convert('RGB'))
H, W = rgb.shape[:2]
hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
h = hsv[:,:,0].astype(int); s = hsv[:,:,1].astype(int); v = hsv[:,:,2].astype(int)
r = rgb[:,:,0].astype(int); g = rgb[:,:,1].astype(int); b = rgb[:,:,2].astype(int)
print(f'[0] 图像: {W}×{H}')

# ============================================================
# Phase 1: 检测并剥离所有背景叠加层
# ============================================================
overlay_mask = np.zeros((H, W), dtype=np.uint8)

# --- 1a. 道路线 (橙色/棕黄色细线, R高G中B低, 细长) ---
# 主路: 橙-棕色, 明显区别于冀州青色和邻州颜色
road_orange = (
    (r > 150) & (r > g + 10) &   # R偏高
    (g > 80) & (g < 200) &
    (b < r - 20) &               # B明显低于R (橙色调)
    (b < 160) &
    (v > 100)                    # 不太暗
)
road_dark = (
    (r > 120) & (r < 200) &
    (g > 70) & (g < 160) &
    (b < 100) &                  # 暗棕/深橙
    (r > b + 30)
)
road_mask = (road_orange | road_dark).astype(np.uint8) * 255
# 形态学筛选：只保留细长的结构（道路是线状的）
# 用开运算去掉斑点，保留线条
road_mask = cv2.morphologyEx(road_mask, cv2.MORPH_OPEN, np.ones((3,3), np.uint8), iterations=1)
# 再用细化检测：计算每个连通域的长宽比
n_road_comp, road_labels, road_stats, _ = cv2.connectedComponentsWithStats(road_mask, connectivity=8)
thin_road = np.zeros_like(road_mask)
for i in range(1, n_road_comp):
    area = road_stats[i, cv2.CC_STAT_AREA]
    w = road_stats[i, cv2.CC_STAT_WIDTH]
    h = road_stats[i, cv2.CC_STAT_HEIGHT]
    # 道路的特征：面积不大(10~5000)，但长宽比大或呈线状
    if area >= 5 and area < 8000:
        aspect = max(w, h) / (min(w, h) + 1)
        if aspect >= 2 or area < 200:
            thin_road[road_labels == i] = 255
print(f'[1a] 道路线检测: {(thin_road>0).sum():,} px ({n_road_comp-1}个连通域)')
overlay_mask = cv2.bitwise_or(overlay_mask, thin_road)

# --- 1b. 文字 (暗色连通域, 灰度低, 中等面积) ---
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
text_dark = (gray < 110).astype(np.uint8) * 255
# 排除纯黑背景边缘（如果有的话）
n_text, text_labels, text_stats, _ = cv2.connectedComponentsWithStats(text_dark, connectivity=8)
text_blobs = np.zeros((H, W), dtype=np.uint8)
for i in range(1, n_text):
    area = text_stats[i, cv2.CC_STAT_AREA]
    # 文字特征: 面积 15 ~ 3000 px (单个字或词组)
    if 15 <= area <= 3000:
        text_blobs[text_labels == i] = 255
# 也检测红色文字（郡名标签等）
red_text_hsv = ((h <= 18) | (h >= 165)) & (s >= 40) & (v >= 50) & (r > g + 10)
red_text_rgb = (r > 110) & (g < 140) & (b < 140) & (r > g + 15)
red_text = (red_text_hsv | red_text_rgb).astype(np.uint8) * 255
n_red, red_labels, red_stats, _ = cv2.connectedComponentsWithStats(red_text, connectivity=8)
red_blobs = np.zeros((H, W), dtype=np.uint8)
for i in range(1, n_red):
    area = red_stats[i, cv2.CC_STAT_AREA]
    if 10 <= area <= 2000:
        red_blobs[red_labels == i] = 255
all_text = cv2.bitwise_or(text_blobs, red_blobs)
print(f'[1b] 文字检测: 暗={(text_blobs>0).sum():,} 红={(red_blobs>0).sum():,}')
overlay_mask = cv2.bitwise_or(overlay_mask, all_text)

# --- 1c. 白线 / 灰白色行政界线 ---
white_lines = (r > 180) & (g > 180) & (b > 180)
white_lines = white_lines.astype(np.uint8) * 255
# 只保留细线（膨胀后再erode来筛选线性结构）
white_dilated = cv2.dilate(white_lines, np.ones((7,7), np.uint8))
white_thin = cv2.erode(white_dilated, np.ones((9,9), np.uint8))
white_thin = cv2.bitwise_and(white_thin, white_lines)
# 也检测灰色细线
gray_lines = ((r > 130) & (r < 200) & (abs(r.astype(int)-g.astype(int))<30) &
              (abs(g.astype(int)-b.astype(int))<30) & (r > 140)).astype(np.uint8)*255
all_lines = cv2.bitwise_or(white_thin, gray_lines)
print(f'[1c] 白/灰线: {(all_lines>0).sum():,} px')
overlay_mask = cv2.bitwise_or(overlay_mask, all_lines)

# --- 1d. Inpaint! 把所有叠加区域替换为周围像素颜色 ---
total_overlay = (overlay_mask > 0).sum()
print(f'[1d] 总叠加区域: {total_overlay:,} px ({total_overlay/(W*H)*100:.1f}%)')

if total_overlay > 0:
    # inpaint半径要足够覆盖最宽的文字
    cleaned_rgb = cv2.inpaint(rgb, overlay_mask, inpaintRadius=12, flags=cv2.INPAINT_TELEA)
else:
    cleaned_rgb = rgb.copy()

Image.fromarray(cleaned_rgb).save(os.path.join(OUTDIR, 'phase1_cleaned.png'))
print(f'[1d] Inpaint完成, 已保存 phase1_cleaned.png')

# ============================================================
# Phase 2: 在干净图上提取青色色块（基于v3的宽松阈值+排除）
# ============================================================
cr = cleaned_rgb[:,:,0].astype(int)
cg = cleaned_rgb[:,:,1].astype(int)
cb = cleaned_rgb[:,:,2].astype(int)

# 冀州浅青色核心（与v3一致）
jizho_core = (
    (cg > cr + 35) &
    (cg > cb + 10) &
    (cg >= 175) &
    (cg <= 245) &
    (cr >= 115) &
    (cr <= 230) &
    (cb >= 155) &
    (cb <= 242)
).astype(np.uint8) * 255
print(f'[2] 干净图青色像素: {(jizho_core>0).sum():,}')

# 邻州排除（在干净图上重新判定 — 颜色可能因inpaint略有变化）
bingzhou = (
    (cr > cg + 15) & (cr > 130) & (cg < 190) & (cr > 140) &
    (~((cg > cr + 20) & (cb >= 155)))
)
sili = (
    (abs(cr - cg) < 30) & (cg > cb + 10) & (cg >= 200) & (cb < cg - 5) & (cr >= 190) &
    (~((cg > cr + 30) & (cb >= 150)))
)
youzhou = (
    (cg > cr + 25) & (cg >= 160) & (cg <= 210) & (cr < 160) &
    (cb >= 140) & (cb < cg + 20) & ((cg - cr) > 30) &
    (~((cg > cb + 15) & (cg >= 175)))
)
qingzhou = (
    (cg > 185) & (cg <= 235) & (cb < 190) & (cb > 70) &
    (cg > cb + 25) & (cr > 170) & (abs(cr - cg) < 50) &
    (~((cb >= 155) & (cg > cr + 35)))
)
exclude = bingzhou | sili | youzhou | qingzhou
jizho_core[exclude > 0] = 0
print(f'[2] 排除后: {(jizho_core>0).sum():,} px')

# 缺陷填充（只在干净图上）
dark_t = (cr < 105) & (cg < 105) & (cb < 105)
wht_l = (cr > 190) & (cg > 190) & (cb > 190)
defect = (dark_t | wht_l).astype(np.uint8) * 255

mask = jizho_core.copy()
k5 = np.ones((5,5), np.float32)/25.0
for it in range(60):
    gf = cv2.filter2D(mask.astype(np.float32)/255.0, -1, k5)
    cand = (defect>0) & (mask==0) & (gf>0.45) & (~exclude)
    if not cand.any():
        break
    mask[cand] = 255
print(f'[2] 填充后: {(mask>0).sum():,} px ({it+1}轮)')

# ============================================================
# Phase 3: ★ 形状低通滤波 ★ (核心创新！消除锯齿和方块)
# ============================================================
# 原理：道路线宽~3-5px, 文字~10-25px
#       真实州界曲率变化尺度 > 50px
#       所以用 25px 左右的核做形态学开闭 = 形状上的低通滤波

# Step 3a: 先轻度闭运算桥接小缺口
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7,7), np.uint8), iterations=1)
mask[exclude > 0] = 0

# Step 3b: ★ 大核闭运算 ★ — 填充道路宽度级别(<20px)的缺口
# 这是消除"道路锯齿"的关键：道路造成的内向缺口宽度约3-8px
# 25×25 的闭核可以把 ≤12px 的缺口全部填满
big_close_k = 25
mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                          np.ones((big_close_k, big_close_k), np.uint8), iterations=1)
print(f'[3b] 大核闭({big_close_k}×{big_close_k})后: {(mask>0).sum():,} px')

# Step 3c: ★ 大核开运算 ★ — 切掉文字/标签造成的外突(≤15px的突出)
# 文字方块造成的凸起宽度约 10-30px
big_open_k = 17
mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                         np.ones((big_open_k, big_open_k), np.uint8), iterations=1)
print(f'[3c] 大核开({big_open_k}×{big_open_k})后: {(mask>0).sum():,} px')

# 再次安全检查
mask[exclude > 0] = 0

# 最大连通域
nb, lab, st, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
main_i = 1 + int(np.argmax(st[1:, cv2.CC_STAT_AREA]))
mask_conn = (lab == main_i).astype(np.uint8) * 255

# 外轮廓填孔洞
contours, _ = cv2.findContours(mask_conn, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)
mask_final = np.zeros_like(mask_conn)
cv2.drawContours(mask_final, [main], -1, 255, -1)

print(f'[3] 最终掩膜: {(mask_final>0).sum():,} px')

# ============================================================
# Phase 4: 边界提取 + 输出
# ============================================================
contours, _ = cv2.findContours(mask_final, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
main = max(contours, key=cv2.contourArea)
arc = cv2.arcLength(main, True)

for eps_factor in [0.0006, 0.0008, 0.0010, 0.0012, 0.0015, 0.0020, 0.0025, 0.0030]:
    poly_px = cv2.approxPolyDP(main, eps_factor * arc, True).reshape(-1, 2)
    if 120 <= len(poly_px) <= 260:
        break
print(f'[4] 边界顶点: {len(poly_px)} (eps={eps_factor:.4f})')

# 压边文字拉平 (针对原始rgb图中的文字)
def flatten_at_labels(poly_px, h, w, rgb_img, pad=35, min_area=150):
    n = len(poly_px)
    poly = poly_px.copy().astype(np.int32)
    ri=rgb_img[:,:,0].astype(int); gi=rgb_img[:,:,1].astype(int); bi=rgb_img[:,:,2].astype(int)
    dark=(ri<105)&(gi<105)&(bi<105)
    hv=cv2.cvtColor(rgb_img,cv2.COLOR_RGB2HSV)
    hh=hv[:,:,0].astype(int); ss=hv[:,:,1].astype(int); vv=hv[:,:,2].astype(int)
    rh=((hh<=18)|(hh>=165))&(ss>=45)&(vv>=50)&(ri>gi+15)
    rg=(ri>120)&(gi<130)&(bi<130)&(ri>gi+25)
    tmask=(dark|rh|rg).astype(np.uint8)*255
    bl=np.zeros((h,w),dtype=np.uint8)
    for x,y in poly:
        if 0<=x<w and 0<=y<h: bl[y,x]=255
    dt=cv2.distanceTransform(255-bl,cv2.DIST_L2,5)
    nc,nl,ns,_=cv2.connectedComponentsWithStats(tmask,connectivity=8)
    if nc<=1: return poly
    changed=False
    for i in range(1,nc):
        a=ns[i,cv2.CC_STAT_AREA]; ch=False
        if a<min_area: continue
        blob=(nl==i).astype(np.uint8)*255; bd=dt[blob>0]
        if len(bd)==0: continue
        dm=bd.min()
        if dm>pad: continue
        bdil=cv2.dilate(blob,np.ones((pad,pad),np.uint8))
        aff=[idx for idx,(x,y) in enumerate(poly) if 0<=x<w and 0<=y<h and bdil[y,x]>0]
        if not aff: continue
        grp=[]; cur=[aff[0]]
        for idx in aff[1:]:
            p=cur[-1]
            if idx==p+1 or (p==n-1 and idx==0): cur.append(idx)
            else: grp.append(cur); cur=[idx]
        grp.append(cur)
        for gr in grp:
            if len(gr)<3: continue
            si,ei=gr[0],gr[-1]
            p1=poly[si].astype(float); p2=poly[ei].astype(float)
            mid=((p1+p2)/2).astype(int)
            if 0<=mid[0]<w and 0<=mid[1]<h and mask_final[mid[1],mid[0]]>0: continue
            if np.linalg.norm(p2-p1)>250: continue
            new=np.linspace(0,1,len(gr))[:,None]*(p2-p1)+p1
            for k,idx in enumerate(gr): poly[idx]=new[k].astype(int)
            changed=True
    if changed:
        cl=[poly[0]]; [cl.append(p) for p in poly[1:] if p[0]!=cl[-1][0] or p[1]!=cl[-1][1]]
        poly=np.array(cl,dtype=np.int32)
    return poly

poly_px = flatten_at_labels(poly_px, H, W, rgb)
print(f'[4] 拉平后: {len(poly_px)} 点')

# 重建最终掩膜
mask_out = np.zeros((H,W), dtype=np.uint8)
cv2.fillPoly(mask_out, [poly_px.astype(np.int32)], 255)
mask_out[exclude > 0] = 0
mask_out = cv2.morphologyEx(mask_out, cv2.MORPH_CLOSE, np.ones((3,3), np.uint8), iterations=1)
print(f'[4] 输出掩膜: {(mask_out>0).sum():,} px')

# ============================================================
# 输出文件
# ============================================================
mean_c = rgb[jizho_core>0].mean(axis=0).astype(np.uint8) if (jizho_core>0).any() else np.array([173,228,207],dtype=np.uint8)
cleaned_out = rgb.copy()
cleaned_out[mask_out>0] = mean_c

Image.fromarray(mask_out).save(os.path.join(OUTDIR,'mask_clean.png'))

mv = np.zeros((H,W,3),dtype=np.uint8); mv[mask_out>0]=(255,255,255)
cv2.polylines(mv,[poly_px.reshape(-1,1,2)],True,(0,0,255),3)
Image.fromarray(mv).save(os.path.join(OUTDIR,'mask_with_boundary.png'))

Image.fromarray(cleaned_out).save(os.path.join(OUTDIR,'text_erased.png'))

ov = rgb.copy(); cv2.polylines(ov,[poly_px.reshape(-1,1,2)],True,(255,0,0),3)
Image.fromarray(ov).save(os.path.join(OUTDIR,'boundary_overlay.png'))

# 半透明验证
vf = rgb.astype(float)*0.55 + np.stack([mask_out]*3,-1).astype(float)*0.45*np.array([0,1,1])
vf = np.clip(vf,0,255).astype(np.uint8)
cv2.polylines(vf,[poly_px.reshape(-1,1,2)],True,(255,0,0),2)
Image.fromarray(vf).save(os.path.join(OUTDIR,'verify_overlay.png'))

# v3 vs v5 对比
poly_v3 = np.array([[p['px'],p['py']] for p in json.load(open(
    os.path.join(HERE,'jizhou_step1_v3','boundary_points.json'),encoding='utf-8'))['points']],np.int32)
cmp = rgb.copy()
cv2.polylines(cmp,[poly_v3.reshape(-1,1,2)],True,(255,150,150),2)
cv2.polylines(cmp,[poly_px.reshape(-1,1,2)],True,(0,255,0),2)
Image.fromarray(cmp).save(os.path.join(OUTDIR,'v3_vs_v5_comparison.png'))

pts_out = [{'seq':i,'px':int(x),'py':int(y)} for i,(x,y) in enumerate(poly_px)]
with open(os.path.join(OUTDIR,'boundary_points.json'),'w',encoding='utf-8') as f:
    json.dump({
        'source_image':'汉末十三州地图范例/冀州.png',
        'image_size':[W,H],
        'version':'v5-overlay-agnostic',
        'method':'Phase1=inpaint_overlays(roads+text+lines)+Phase2=color_extract+v3_thresholds'
                   '+Phase3=shape_lowpass(close25+open17)+Phase4=contour_simplify',
        'points':pts_out}, f, ensure_ascii=False, indent=2)

tw,th = W//2, H//2
comp_img = np.zeros((th,tw*3,3),dtype=np.uint8)
comp_img[:,0:tw]=cv2.resize(rgb,(tw,th),interpolation=cv2.INTER_AREA)
comp_img[:,tw:2*tw]=cv2.resize(cleaned_out,(tw,th),interpolation=cv2.INTER_AREA)
comp_img[:,2*tw:3*tw]=cv2.resize(ov,(tw,th),interpolation=cv2.INTER_AREA)
Image.fromarray(comp_img).save(os.path.join(OUTDIR,'comparison_preview.png'))

print(f'\n[done] => {OUTDIR}/')
print(f'    边界{len(pts_out)}点, 面积{(mask_out>0).sum():,}px')
print(f'    关键参数: close_k={big_close_k}, open_k={big_open_k}, inpaint_r=12')
