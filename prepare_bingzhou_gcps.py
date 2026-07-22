"""
并州 GCP 锚点准备 v2 — 基于 digitize_v2 工作流

用已校正的 5 个地标(大同/太原/呼和浩特/延安/吕梁)的像素坐标+真实经纬度,
计算仿射变换, 然后将 25+ 个候选城市投影到并州.png 上生成预览图。
同时输出 JSON 格式的完整 GCP 表供用户在 digitize_v2 中使用。

用户工作流:
  1. 打开 viewer/digitize_v2.html → 选「并州」→ 选预设城市 → 在图上点击该城市位置
  2. ≥4 个 GCP 后自动计算仿射
  3. 本脚本生成的预览图帮助快速定位每个城市的大致位置
"""
import json, os, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
IMG_PATH = os.path.join(HERE, '汉末十三州地图范例', '并州.png')
OUTDIR = os.path.join(HERE, 'bingzhou_step1_v7c')

# ── 已校正的 5 个地标（来自 bingzhou_anchor_table.json）──
ANCHORS = [
    {"name": "大同",     "px": 1489, "py": 432,  "lon": 113.300, "lat": 40.080},
    {"name": "太原",     "px": 1472, "py": 792,  "lon": 112.550, "lat": 37.870},
    {"name": "呼和浩特", "px": 1260, "py": 203,  "lon": 111.730, "lat": 40.830},
    {"name": "延安",     "px": 965,  "py": 783,  "lon": 109.490, "lat": 36.600},
    {"name": "吕梁",     "px": 1184, "py": 882,  "lon": 111.130, "lat": 37.520},
]

# ── 候选 GCP 城市（山西/陕北/内蒙古/冀南/豫北/晋南）──
# 分组便于用户按区域选择; lon/lat 为现代城市中心坐标
CANDIDATES = [
    # ═══ 山西省核心（并州主体）════
    {"name": "太原",       "lon": 112.550, "lat": 37.870, "region": "山西", "note": "太原郡·晋阳"},
    {"name": "大同",       "lon": 113.300, "lat": 40.080, "region": "山西", "note": "雁门郡附近"},
    {"name": "临汾",       "lon": 111.518, "lat": 36.084, "region": "山西", "note": "平阳·司隶界"},
    {"name": "运城",       "lon": 110.998, "lat": 35.022, "region": "山西", "note": "安邑·司隶界"},
    {"name": "长治",       "lon": 113.128, "lat": 36.186, "region": "山西", "note": "上党郡·长子"},
    {"name": "晋城",       "lon": 112.851, "lat": 35.497, "region": "山西", "note": "上党郡南端"},
    {"name": "阳泉",       "lon": 113.577, "lat": 37.861, "region": "山西", "note": "真定附近"},
    {"name": "朔州",       "lon": 112.430, "lat": 39.332, "region": "山西", "note": "马邑·雁门西"},
    {"name": "忻州",       "lon": 112.734, "lat": 38.418, "region": "山西", "note": "新兴郡"},
    {"name": "吕梁/离石",   "lon": 111.134, "lat": 37.524, "region": "山西", "note": "西河郡治"},

    # ═══ 陕北（上郡/西河北部）════
    {"name": "延安",       "lon": 109.491, "lat": 36.597, "region": "陕西", "note": "上郡·肤施"},
    {"name": "榆林",       "lon": 109.738, "lat": 38.286, "region": "陕西", "note": "上郡北·榆塞"},
    {"name": "绥德",       "lon": 110.262, "lat": 37.504, "region": "陕西", "note": "西河郡北"},

    # ═══ 内蒙古中部（云中/五原/朔方/定襄）════
    {"name": "呼和浩特",   "lon": 111.730, "lat": 40.827, "region": "内蒙", "note": "云中郡"},
    {"name": "包头",       "lon": 109.842, "lat": 40.659, "region": "内蒙", "note": "五原郡"},
    {"name": "鄂尔多斯/东胜","lon": 109.782, "lat": 39.609, "region": "内蒙", "note": "朔方/五原间"},
    {"name": "乌兰察布/集宁","lon": 113.132, "lat": 41.031, "region": "内蒙", "note": "代郡北·阴山"},
    {"name": "巴彦淖尔/临河","lon": 107.420, "lat": 40.750, "region": "内蒙", "note": "朔方郡"},

    # ═══ 河北南部/东部（冀州/幽州交界）════
    {"name": "石家庄",     "lon": 114.512, "lat": 38.042, "region": "河北", "note": "常山郡·冀州"},
    {"name": "邯郸",       "lon": 114.489, "lat": 36.609, "region": "河北", "note": "邯郸郡/邺"},
    {"name": "张家口",     "lon": 114.888, "lat": 40.821, "region": "河北", "note": "代郡/幽州界"},
    {"name": "保定",       "lon": 115.462, "lat": 38.874, "region": "河北", "note": "中山国"},
    {"name": "邢台",       "lon": 114.500, "lat": 37.072, "region": "河北", "note": "赵国/冀州"},
    {"name": "安阳",       "lon": 114.396, "lat": 36.103, "region": "河南", "note": "魏郡/邺附近"},

    # ═══ 河南北部（司隶/豫州/河内）════
    {"name": "郑州",       "lon": 113.625, "lat": 34.747, "region": "河南", "note": "河南尹"},
    {"name": "洛阳",       "lon": 112.454, "lat": 34.619, "region": "河南", "note": "司隶·洛阳"},
    {"name": "焦作",       "lon": 113.242, "lat": 35.239, "region": "河南", "note": "河内郡"},
    {"name": "新乡",       "lon": 113.926, "lat": 35.303, "region": "河南", "note": "河内郡东"},
    {"name": "济源",       "lon": 112.600, "lat": 35.067, "region": "河南", "note": "河内郡北"},
    {"name": "开封",       "lon": 114.310, "lat": 34.791, "region": "河南", "note": "陈留郡"},

    # ═══ 陕西中部（司隶西界）════
    {"name": "西安",       "lon": 108.940, "lat": 34.342, "region": "陕西", "note": "京兆/司隶"},
    {"name": "渭南",       "lon": 109.503, "lat": 34.500, "region": "陕西", "note": "京兆东"},
]

def compute_affine(anchors):
    """用最小二乘拟合 px,py -> lon 和 px,py -> lat 两个仿射变换"""
    n = len(anchors)
    # 设计矩阵 [px, py, 1]
    A = np.array([[a['px'], a['py'], 1] for a in anchors], dtype=float)
    lons = np.array([a['lon'] for a in anchors])
    lats = np.array([a['lat'] for a in anchors])

    # 最小二乘: solve A^T A x = A^T b
    AtA = A.T @ A
    lon_coef = np.linalg.solve(AtA, A.T @ lons)
    lat_coef = np.linalg.solve(AtA, A.T @ lats)

    # 验证残差
    max_err_lon = 0
    max_err_lat = 0
    for a in anchors:
        pred_lon = lon_coef[0]*a['px'] + lon_coef[1]*a['py'] + lon_coef[2]
        pred_lat = lat_coef[0]*a['px'] + lat_coef[1]*a['py'] + lat_coef[2]
        err_lon = abs(pred_lon - a['lon'])
        err_lat = abs(pred_lat - a['lat'])
        max_err_lon = max(max_err_lon, err_lon)
        max_err_lat = max(max_err_lat, err_lat)

    print(f'仿射变换系数:')
    print(f'  lon = {lon_coef[0]:+.6f}*px + {lon_coef[1]:+.6f}*py + {lon_coef[2]:+.4f}')
    print(f'  lat = {lat_coef[0]:+.6f}*px + {lat_coef[1]:+.6f}*py + {lat_coef[2]:+.4f}')
    print(f'  最大残差: lon={max_err_lon:.4f}°, lat={max_err_lat:.4f}°')
    return lon_coef, lat_coef


def project_city(lon_coef, lat_coef, city):
    """将一个城市的经纬度投影到像素坐标 (逆仿射)"""
    # 解: px,py 使得 lon_coef*px+lon_coef*py+lon_coef_2=lon
    # 即 [lon_coef[0], lon_coef[1]] · [px, py]^T = lon - lon_coef[2]
    # 同理 lat
    # 这是一个 2x2 线性系统:
    # [[lon_c0, lon_c1], [lat_c0, lat_c1]] · [px, py] = [lon-lon_c2, lat-lat_c2]
    M = np.array([
        [lon_coef[0], lon_coef[1]],
        [lat_coef[0], lat_coef[1]]
    ])
    b = np.array([city['lon'] - lon_coef[2], city['lat'] - lat_coef[2]])
    try:
        px, py = np.linalg.solve(M, b)
        return round(px, 1), round(py, 1)
    except np.linalg.LinAlgError:
        return None, None


def main():
    img = Image.open(IMG_PATH).convert('RGB')
    W, H = img.size
    print(f'参考图像: {W}x{H}')

    # 计算仿射
    lon_coef, lat_coef = compute_affine(ANCHORS)

    # 投影所有候选城市
    results = []
    for c in CANDIDATES:
        px, py = project_city(lon_coef, lat_coef, c)
        if px is not None:
            # 检查是否在图像范围内
            in_range = -50 <= px <= W + 50 and -50 <= py <= H + 50
            c['_px'] = px
            c['_py'] = py
            c['_in_range'] = in_range
            results.append(c)
            status = "✓" if in_range else "✗(出界)"
            print(f"  {c['name']:12s} ({c['lon']:7.3f},{c['lat']:7.3f}) → ({px:7.1f},{py:7.1f}) [{status}]")

    print(f'\n共投影 {len(results)} 个城市, 其中 {sum(1 for r in results if r["_in_range"])} 个在范围内')

    # ── 生成预览图 ──
    preview = img.copy()
    draw = ImageDraw.Draw(preview)

    font_path = 'C:/Windows/Fonts/simhei.ttf'
    try:
        font_lg = ImageFont.truetype(font_path, 22)
        font_sm = ImageFont.truetype(font_path, 16)
    except Exception:
        font_lg = font_sm = ImageFont.load_default()

    # 先画已知锚点（红色大圈，作为基准）
    for i, a in enumerate(ANCHORS):
        x, y = int(a['px']), int(a['py'])
        r = 14
        draw.ellipse([x-r, y-r, x+r, y+r], outline='#FF0000', width=3)
        draw.ellipse([x-4, y-4, x+4, y+4], fill='#FF0000')
        label = f"G{i+1}.{a['name']}"
        ox, oy = 18, -24
        for dx, dy in [(-2,-2),(-2,0),(-2,2),(0,-2),(0,2),(2,-2),(2,0),(2,2)]:
            draw.text((x+ox+dx, y+oy+dy), label, fill='white', font=font_sm)
        draw.text((x+ox, y+oy), label, fill='#FF0000', font=font_sm)

    # 再画候选城市（青色小圈，带编号和名称）
    region_colors = {
        "山西": '#00CCFF',
        "陕西": '#FFCC00',
        "内蒙": '#FF66CC',
        "河北": '#99FF66',
        "河南": '#FF9933',
    }

    for i, c in enumerate(results):
        x, y = int(c['_px']), int(c['_py'])
        color = region_colors.get(c.get('region',''), '#AAAAAA')

        if not c['_in_range']:
            # 出界的画到边缘附近
            x = max(10, min(W-10, x))
            y = max(10, min(H-10, y))

        r = 10
        draw.ellipse([x-r, y-r, x+r, y+r], outline=color, width=2)
        draw.ellipse([x-2, y-2, x+2, y+2], fill=color)

        label = f"{i+1}.{c['name']}({c['lon']:.1f},{c['lat']:.1f})"
        ox = 16 if x < W // 2 else -(len(label)*9 + 8)
        oy = -20 if y > H * 0.15 else 12

        # 描边文字
        for dx, dy in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            draw.text((x+ox+dx, y+oy+dy), label, fill='white', font=font_sm)
        draw.text((x+ox, y+oy), label, fill=color, font=font_sm)

    # 图例
    legend_y = H - 120
    draw.rectangle([(10, legend_y-10), (280, H-5)], fill=(0,0,0,180))
    ly = legend_y
    for region_name, rc in region_colors.items():
        draw.ellipse([18, ly, 28, ly+10], outline=rc, width=2)
        draw.text((36, ly-2), f"{region_name} ({sum(1 for r in results if r.get('region')==region_name)})个)", fill=rc, font=font_sm)
        ly += 18

    out_path = os.path.join(OUTDIR, 'bingzhou_gcp_preview_v2.png')
    preview.save(out_path)
    print(f'\nGCP预览图 -> {out_path}')

    # ── 输出完整 GCP JSON 表 ──
    gcp_table = []
    for c in CANDIDATES:
        gcp_table.append({
            "name": c["name"],
            "type": "city",
            "lon": round(c["lon"], 3),
            "lat": round(c["lat"], 3),
            "_est_px": round(c.get("_px", 0), 1),
            "_est_py": round(c.get("_py", 0), 1),
            "_in_range": int(c.get("_in_range", False)),
            "region": c.get("region", ""),
            "note": c.get("note", ""),
        })

    json_out = os.path.join(HERE, 'bingzhou_gcp_full.json')
    with open(json_out, 'w', encoding='utf-8') as f:
        json.dump(gcp_table, f, ensure_ascii=False, indent=2)
    print(f'完整GCP表 -> {json_out} ({len(gcp_table)}个城市)')

    # ── 输出 digitize_v2 PRESET_CITIES 追加代码片段 ──
    snippet_lines = [
        "",
        "  // ── 并州专用 GCP 预设（山西/陕北/内蒙/冀南/豫北/关中）──",
    ]
    for c in CANDIDATES:
        name_js = c["name"].replace("'", "\\'")
        note = c.get("note", "")
        snippet_lines.append(
            f"  {{name:'{name_js}', lon:{c['lon']:.2f}, lat:{c['lat']:.2f}}},  // {note}"
        )

    snippet = '\n'.join(snippet_lines)
    snippet_file = os.path.join(OUTDIR, 'digitize_v2_preset_snippet.js')
    with open(snippet_file, 'w', encoding='utf-8') as f:
        f.write(snippet)
    print(f'PRESET_CITIES追加代码片段 -> {snippet_file}')


if __name__ == '__main__':
    main()
