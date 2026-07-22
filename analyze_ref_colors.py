"""分析参考图色彩分布：判断各州边界在哪些图里以可分离的彩色区域存在，
并核验 全览-郡治(9933) 与 全览-郡级(2020) 的对应关系。"""
from PIL import Image
import numpy as np
import os

REF = '汉末十三州地图范例'

def load_rgb(path, size=None):
    im = Image.open(path).convert('RGB')
    if size:
        im = im.resize(size, Image.LANCZOS)
    return np.asarray(im).astype(np.int32)

def vivid_palette(rgb, topn=30, quant=8):
    """返回鲜艳色的 (count, centroid_x, centroid_y, color)，用于判别州填充色。"""
    h, w = rgb.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w]
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    chroma = np.maximum.reduce([r, g, b]) - np.minimum.reduce([r, g, b])
    lum = (r + g + b) / 3
    vivid = (chroma > 45) & (lum > 35) & (lum < 235)
    pts = rgb.reshape(-1, 3)
    vmask = vivid.reshape(-1)
    if vmask.sum() == 0:
        return [], 0.0
    vp = pts[vmask]
    vx = xs.reshape(-1)[vmask]
    vy = ys.reshape(-1)[vmask]
    # 量化
    q = (vp // quant) * quant
    # 用字典聚合
    from collections import defaultdict
    agg = defaultdict(lambda: [0, 0, 0, 0])  # count, sumx, sumy, _
    color_of = {}
    for i in range(len(vp)):
        key = (int(q[i, 0]), int(q[i, 1]), int(q[i, 2]))
        a = agg[key]
        a[0] += 1
        a[1] += int(vx[i])
        a[2] += int(vy[i])
        color_of[key] = (int(vp[i, 0]), int(vp[i, 1]), int(vp[i, 2]))
    items = []
    for key, a in agg.items():
        items.append((a[0], a[1] // a[0], a[2] // a[0], color_of[key]))
    items.sort(reverse=True)
    frac = vmask.sum() / (h * w)
    return items[:topn], frac

def report(path, size=None):
    name = os.path.basename(path)
    rgb = load_rgb(path, size)
    print(f"\n===== {name}  shape={rgb.shape[1]}x{rgb.shape[0]} =====")
    items, frac = vivid_palette(rgb)
    print(f"鲜艳像素占比: {frac*100:.2f}%")
    for cnt, cx, cy, col in items[:18]:
        print(f"  cnt={cnt:7d}  centroid=({cx:5d},{cy:5d})  rgb={col}")

if __name__ == '__main__':
    # 1) 全览-郡治 (9933) 缩小到 2020 便于分析，看是否有彩色州域
    report(os.path.join(REF, '全览-郡治.png'), size=(2020, 1418))
    # 2) 全览-郡级 (2020) 原尺寸
    report(os.path.join(REF, '全览-郡级.png'))
    # 3) 逐个分州图：取每个图最占面积的鲜艳色 = 该州填充色
    print("\n===== 分州图最显著填充色 (按面积最大的鲜艳色簇) =====")
    for st in ['凉州','益州','司隶','并州','冀州','青州','幽州','兖州','豫州','徐州','扬州','荆州','交州']:
        f = os.path.join(REF, f'{st}.png')
        if not os.path.exists(f):
            print('  MISSING', st); continue
        rgb = load_rgb(f)
        items, frac = vivid_palette(rgb, topn=8)
        if items:
            # 面积最大的即聚焦州
            cnt, cx, cy, col = items[0]
            print(f"  {st}: 主导色 rgb={col}  cnt={cnt}  centroid=({cx},{cy})")
