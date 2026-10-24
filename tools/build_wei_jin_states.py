#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
魏晋南北朝 · 疆域快照构建（220–589，七个断面）

每个政权 = **一条完整外环**（不拼接地理单元）。原因：手工单元很难严丝合缝，
同属一国却拼不上就会露白缝；一政权一环从根上没有这个问题，边界还能贴着山川走。
国与国之间留一点缝是正常的——图上读作边界，不会被视为错误。

七个断面（覆盖三国→隋的全部主要政权）：
  262 三国鼎立      魏 / 蜀 / 吴
  300 西晋一统      西晋
  382 前秦 · 东晋   前秦 / 东晋
  500 北魏 · 南齐   北魏 / 南齐
  546 东魏·西魏·梁  东魏 / 西魏 / 梁 / 吐谷浑 / 柔然
  576 北周·北齐·陈  北周 / 北齐 / 陈 / 突厥 / 吐谷浑
  589 隋            隋 / 吐谷浑 / 突厥

546 年五国环取自上一版手工精修结果（tools/data/wei_jin_546_rings.json），其余为同一套
山川基准下推演。用法：
  PY tools/build_wei_jin_states.py            # 生成 魏晋南北朝/wei_jin_states.js
  PY tools/build_wei_jin_states.py --qa       # 另出 %TEMP%/wj_states_qa.png 七期对照图
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, '魏晋南北朝', 'wei_jin_states.js')
SRC546 = os.path.join(ROOT, 'tools', 'data', 'wei_jin_546_rings.json')

with open(SRC546, encoding='utf-8') as f:
    R546 = json.load(f)

# ── 复用环（同一套山川基准，便于断面之间比对） ──────────────────────
# 北方外缘：山海关 → 燕山 → 阴山 → 河西走廊 → 祁连 → 湟水（自东向西）
NORTH_RIM = [
    [119.90,40.00],[118.80,40.85],[117.60,41.05],[116.30,41.20],[115.00,41.05],
    [113.90,40.75],[113.10,40.50],[112.20,40.35],[111.20,40.40],[110.60,39.40],
    [109.80,39.20],[108.80,39.60],[107.60,39.80],[106.50,39.90],[105.50,39.30],
    [104.60,38.80],[103.60,38.40],[102.40,38.45],[101.00,38.90],[99.60,39.30],
    [98.20,39.60],[96.60,40.30],[95.20,40.60],[94.30,40.60],
    [93.80,39.80],[94.80,38.90],[96.20,38.20],[97.80,37.60],[99.20,37.10],
    [100.40,36.60],[101.30,36.20]
]
# 西部外缘：湟水 → 陇右 → 岷山 → 大渡河 → 滇西（自北向南）
WEST_RIM = [
    [102.10,35.60],[102.80,34.80],[103.40,34.10],[103.90,33.60],
    [103.50,32.90],[103.10,32.20],[102.60,31.40],[102.10,30.60],[101.60,29.30],
    [101.10,28.00],[100.60,26.80],[100.00,25.60],[99.40,24.40],[98.80,23.50]
]
# 南部海岸：长江口 → 闽浙 → 岭南 → 北部湾 → 交州西界（自东向西）
COAST_SOUTH = [
    [121.90,31.00],[122.20,29.95],[121.65,28.80],[120.95,27.80],[120.35,26.60],
    [119.65,25.55],[118.55,24.55],[117.35,23.75],[116.30,23.20],[114.80,22.85],
    [113.60,22.45],[112.30,21.75],[111.20,21.15],[110.55,20.30],[110.45,21.20],
    [109.80,21.55],[108.60,21.60],[108.20,21.25],[107.70,20.70],[107.15,19.90],
    [106.70,18.55],[106.05,18.80],[105.40,19.90],[104.90,22.60]
]
# 交州西界 → 滇西（自东向西）
WEST_TO_JP = [
    [104.90,22.60],[103.70,22.60],[102.40,22.30],[101.10,21.80],[99.90,21.60],[98.30,22.80]
]
# 宁州北界（金沙江）：滇西 → 三峡
JP_NORTH = [
    [98.80,23.50],[99.50,25.50],[100.50,27.00],[101.50,28.00],[102.50,27.80],
    [104.00,28.50],[104.60,28.70],[105.50,28.80],[106.50,29.50],[107.40,30.55],[108.40,30.85]
]
# 东部海岸：长江口北岸 → 苏北 → 山东半岛 → 渤海湾 → 山海关（自南向北）
EAST_COAST = [
    [121.10,32.15],[120.30,33.20],[120.25,34.25],[120.70,35.10],[121.10,35.90],
    [121.70,36.60],[122.35,37.35],[121.60,37.80],[120.40,37.85],[119.60,37.35],
    [118.80,38.30],[117.90,39.05],[118.20,39.60]
]
# 秦岭（自西向东）
QINLING = [
    [103.90,33.60],[104.60,33.45],[105.40,33.55],[106.15,33.72],[106.90,33.88],
    [107.65,33.95],[108.45,34.05],[109.20,34.12],[109.90,34.26],[110.30,34.45]
]
# 淮河—桐柏—南阳（自西向东）
HUAI = [
    [112.65,32.62],[113.25,32.50],[114.10,32.38],[115.10,32.45],[116.10,32.50],
    [117.00,32.55],[117.95,32.75],[118.80,33.20],[119.20,34.05]
]
# 长江（三峡—江陵—武昌—建康—江口，自西向东）
CHANGJIANG = [
    [109.51,31.05],[110.40,30.85],[111.28,30.70],[112.19,30.35],[113.30,30.30],
    [114.31,30.55],[115.60,30.00],[116.60,30.40],[117.60,31.45],[118.60,32.20],
    [119.50,32.35],[120.30,32.60]
]
# 荆北（江陵 → 南阳）
JINGBEI = [[112.30,32.95],[112.55,33.95],[111.90,34.15],[111.00,34.32],[110.45,34.45]]
# 统一王朝的完整轮廓（西晋 300 / 隋 589 共用）
CHINA_UNIFIED = (NORTH_RIM + WEST_RIM + WEST_TO_JP[::-1] + COAST_SOUTH[::-1][1:] + EAST_COAST)
# 北方政权轮廓（魏 262 / 北魏 500 共用）：北方 + 河西 + 南阳 + 淮南
NORTH_CHINA = (NORTH_RIM + WEST_RIM[0:3] + QINLING +
               [[111.00,34.32],[111.90,34.15],[112.55,33.95],[112.40,33.45],[112.30,32.95]] +
               HUAI + EAST_COAST[2:])
# 江南政权轮廓（吴 262 / 陈 576 共用）：长江以南 + 交广（无宁州）
JIANGNAN = (CHANGJIANG + COAST_SOUTH +
            [[105.00,24.00],[106.00,25.50],[107.50,26.50],[108.40,27.90],[109.20,29.60]])

# 蜀：益州 + 汉中 + 南中（云南·贵州西部）
SHU_262 = [
    [105.50,33.20],[106.20,33.55],[107.00,33.55],[107.60,33.45],[108.20,33.15],
    [109.30,32.60],[110.10,32.60],[109.80,31.50],[109.51,31.05],[108.40,30.85],
    [107.40,30.55],[106.50,29.50],[105.50,28.80],[104.60,28.70],
    [105.30,27.10],[105.50,25.80],[105.70,24.60],[105.20,23.30],[104.90,22.60],
    [103.70,22.60],[102.40,22.30],[101.10,21.80],[99.90,21.60],[98.30,22.80],
    [98.80,23.50],[99.40,24.40],[100.60,26.80],[101.60,29.30],[102.60,31.40],
    [103.40,33.40],[104.40,33.40],[105.40,33.30]
]
# 前秦：北方 + 巴蜀 + 汉中 + 荆北 + 淮南
BASU_SOUTH = [[102.80,29.60],[104.00,29.00],[105.50,28.90],[106.50,29.50],
             [107.40,30.55],[108.40,30.85]]
QIN_382 = (NORTH_RIM + WEST_RIM[0:8] + BASU_SOUTH + CHANGJIANG +
           [[120.40,33.40],[119.20,34.05]] + EAST_COAST[2:])
# 东晋：江南 + 荆南 + 交广 + 宁州
JIN_382 = (CHANGJIANG + COAST_SOUTH + WEST_TO_JP[1:] + JP_NORTH)
# 北周：关陇河西 + 汉中 + 巴蜀 + 荆北
BEIZHOU_576 = (R546['西魏']['boundary'][:31] + WEST_RIM[4:8] + BASU_SOUTH +
               CHANGJIANG[0:4] + JINGBEI)
BEIQI_576 = R546['东魏']['boundary']
NANQI_500 = R546['梁']['boundary']
TURK = R546['柔然']['boundary']
# 吐谷浑：北界压在西魏/隋的祁连线以南，避免两国重叠
TUYUHUN = [
    [88.00,36.60],[89.50,37.20],[91.50,37.90],[94.00,38.20],[96.50,38.00],
    [98.50,37.40],[100.00,37.00],[101.20,36.60],[102.00,36.20],[102.00,35.60],
    [101.60,34.90],[101.60,34.10],[101.20,33.40],[100.40,32.80],[99.30,32.60],
    [98.00,32.90],[96.50,33.20],[95.00,33.40],[93.50,33.60],[91.50,34.20],
    [89.50,35.30],[88.00,36.20]
]

SNAPSHOTS = [
    {'year': 262, 'name': '三国鼎立', 'states': [
        {'name': '魏', 'color': '#5E35B1', 'rings': [NORTH_CHINA], 'seats': [
            ('洛阳', 'capital', 112.45, 34.62), ('长安', 'commandery', 108.94, 34.26),
            ('邺', 'commandery', 114.35, 36.33), ('许昌', 'commandery', 113.82, 34.03),
            ('寿春', 'commandery', 117.16, 32.59), ('襄阳', 'commandery', 112.14, 32.04),
            ('姑臧', 'commandery', 102.64, 37.93), ('敦煌', 'commandery', 94.66, 40.14)]},
        {'name': '蜀', 'color': '#D32F2F', 'rings': [SHU_262], 'seats': [
            ('成都', 'capital', 104.07, 30.66), ('汉中', 'commandery', 107.02, 33.07),
            ('江州', 'commandery', 106.55, 29.56), ('永安', 'commandery', 109.51, 31.05),
            ('味县', 'commandery', 103.80, 25.60)]},
        {'name': '吴', 'color': '#616161', 'rings': [JIANGNAN], 'seats': [
            ('建业', 'capital', 118.78, 32.06), ('武昌', 'commandery', 114.31, 30.55),
            ('江陵', 'commandery', 112.19, 30.35), ('长沙', 'commandery', 112.98, 28.20),
            ('番禺', 'commandery', 113.26, 23.13), ('会稽', 'commandery', 120.58, 30.00)]},
    ]},
    {'year': 300, 'name': '西晋一统', 'states': [
        {'name': '西晋', 'color': '#C62828', 'rings': [CHINA_UNIFIED], 'seats': [
            ('洛阳', 'capital', 112.45, 34.62), ('长安', 'commandery', 108.94, 34.26),
            ('邺', 'commandery', 114.35, 36.33), ('成都', 'commandery', 104.07, 30.66),
            ('建邺', 'commandery', 118.78, 32.06), ('襄阳', 'commandery', 112.14, 32.04),
            ('江陵', 'commandery', 112.19, 30.35), ('姑臧', 'commandery', 102.64, 37.93),
            ('番禺', 'commandery', 113.26, 23.13)]},
    ]},
    {'year': 382, 'name': '前秦 · 东晋', 'states': [
        {'name': '前秦', 'color': '#7B1FA2', 'rings': [QIN_382], 'seats': [
            ('长安', 'capital', 108.94, 34.26), ('洛阳', 'commandery', 112.45, 34.62),
            ('邺', 'commandery', 114.35, 36.33), ('晋阳', 'commandery', 112.55, 37.87),
            ('姑臧', 'commandery', 102.64, 37.93), ('成都', 'commandery', 104.07, 30.66),
            ('襄阳', 'commandery', 112.14, 32.04), ('寿春', 'commandery', 117.16, 32.59)]},
        {'name': '东晋', 'color': '#212121', 'rings': [JIN_382], 'seats': [
            ('建康', 'capital', 118.78, 32.06), ('江陵', 'commandery', 112.19, 30.35),
            ('武昌', 'commandery', 114.31, 30.55), ('长沙', 'commandery', 112.98, 28.20),
            ('番禺', 'commandery', 113.26, 23.13), ('会稽', 'commandery', 120.58, 30.00),
            ('龙编', 'commandery', 106.05, 21.05)]},
    ]},
    {'year': 500, 'name': '北魏 · 南齐', 'states': [
        {'name': '北魏', 'color': '#4A148C', 'rings': [NORTH_CHINA], 'seats': [
            ('洛阳', 'capital', 112.45, 34.62), ('平城', 'commandery', 113.30, 40.09),
            ('邺', 'commandery', 114.35, 36.33), ('长安', 'commandery', 108.94, 34.26),
            ('晋阳', 'commandery', 112.55, 37.87), ('姑臧', 'commandery', 102.64, 37.93),
            ('寿春', 'commandery', 117.16, 32.59), ('彭城', 'commandery', 117.18, 34.27)]},
        {'name': '南齐', 'color': '#D32F2F', 'rings': [NANQI_500], 'seats': [
            ('建康', 'capital', 118.78, 32.06), ('江陵', 'commandery', 112.19, 30.35),
            ('成都', 'commandery', 104.07, 30.66), ('襄阳', 'commandery', 112.14, 32.04),
            ('汉中', 'commandery', 107.02, 33.07), ('番禺', 'commandery', 113.26, 23.13)]},
    ]},
    {'year': 546, 'name': '东魏 · 西魏 · 梁', 'states': [
        {'name': '东魏', 'color': '#7B1FA2', 'rings': [R546['东魏']['boundary']], 'seats': [
            ('邺', 'capital', 114.35, 36.33), ('晋阳', 'commandery', 112.55, 37.87),
            ('洛阳', 'commandery', 112.45, 34.62), ('彭城', 'commandery', 117.18, 34.27),
            ('广固', 'commandery', 118.48, 36.70), ('平城', 'commandery', 113.30, 40.09),
            ('悬瓠', 'commandery', 114.36, 33.00)]},
        {'name': '西魏', 'color': '#212121', 'rings': [R546['西魏']['boundary']], 'seats': [
            ('长安', 'capital', 108.94, 34.26), ('姑臧', 'commandery', 102.64, 37.93),
            ('上邽', 'commandery', 105.72, 34.58), ('统万城', 'commandery', 108.85, 38.00),
            ('敦煌', 'commandery', 94.66, 40.14)]},
        {'name': '梁', 'color': '#D32F2F', 'rings': [R546['梁']['boundary']], 'seats': [
            ('建康', 'capital', 118.78, 32.06), ('江陵', 'commandery', 112.19, 30.35),
            ('成都', 'commandery', 104.07, 30.66), ('襄阳', 'commandery', 112.14, 32.04),
            ('番禺', 'commandery', 113.26, 23.13), ('会稽', 'commandery', 120.58, 30.00),
            ('长沙', 'commandery', 112.98, 28.20)]},
        {'name': '吐谷浑', 'color': '#FF80AB', 'rings': [TUYUHUN], 'seats': [
            ('伏俟城', 'capital', 99.10, 36.90)]},
        {'name': '柔然', 'color': '#9E9E9E', 'rings': [TURK], 'seats': [
            ('可汗庭', 'capital', 102.80, 47.50)]},
    ]},
    {'year': 576, 'name': '北周 · 北齐 · 陈', 'states': [
        {'name': '北周', 'color': '#212121', 'rings': [BEIZHOU_576], 'seats': [
            ('长安', 'capital', 108.94, 34.26), ('成都', 'commandery', 104.07, 30.66),
            ('江陵', 'commandery', 112.19, 30.35), ('姑臧', 'commandery', 102.64, 37.93),
            ('统万城', 'commandery', 108.85, 38.00)]},
        {'name': '北齐', 'color': '#7B1FA2', 'rings': [BEIQI_576], 'seats': [
            ('邺', 'capital', 114.35, 36.33), ('晋阳', 'commandery', 112.55, 37.87),
            ('洛阳', 'commandery', 112.45, 34.62), ('平城', 'commandery', 113.30, 40.09),
            ('寿春', 'commandery', 117.16, 32.59)]},
        {'name': '陈', 'color': '#D32F2F', 'rings': [JIANGNAN], 'seats': [
            ('建康', 'capital', 118.78, 32.06), ('长沙', 'commandery', 112.98, 28.20),
            ('番禺', 'commandery', 113.26, 23.13), ('会稽', 'commandery', 120.58, 30.00),
            ('龙编', 'commandery', 106.05, 21.05)]},
        {'name': '突厥', 'color': '#9E9E9E', 'rings': [TURK], 'seats': [
            ('可汗庭', 'capital', 102.80, 47.50)]},
        {'name': '吐谷浑', 'color': '#FF80AB', 'rings': [TUYUHUN], 'seats': [
            ('伏俟城', 'capital', 99.10, 36.90)]},
    ]},
    {'year': 589, 'name': '隋', 'states': [
        {'name': '隋', 'color': '#C62828', 'rings': [CHINA_UNIFIED], 'seats': [
            ('大兴', 'capital', 108.94, 34.26), ('洛阳', 'commandery', 112.45, 34.62),
            ('邺', 'commandery', 114.35, 36.33), ('建康', 'commandery', 118.78, 32.06),
            ('江陵', 'commandery', 112.19, 30.35), ('成都', 'commandery', 104.07, 30.66),
            ('番禺', 'commandery', 113.26, 23.13), ('姑臧', 'commandery', 102.64, 37.93)]},
        {'name': '吐谷浑', 'color': '#FF80AB', 'rings': [TUYUHUN], 'seats': [
            ('伏俟城', 'capital', 99.10, 36.90)]},
        {'name': '突厥', 'color': '#9E9E9E', 'rings': [TURK], 'seats': [
            ('可汗庭', 'capital', 102.80, 47.50)]},
    ]},
]


# ── 几何体检 ─────────────────────────────────────────────────────────
def poly(ring_):
    return Polygon(ring_)


def check():
    from shapely.geometry import Polygon as P
    bad = []
    for snap in SNAPSHOTS:
        for st in snap['states']:
            for i, r in enumerate(st['rings']):
                g = P(r)
                if not g.is_valid:
                    bad.append('%d %s 环%d 自交/无效' % (snap['year'], st['name'], i))
                if g.area < 3:
                    bad.append('%d %s 面积过小 %.2f' % (snap['year'], st['name'], g.area))
        # 政权重叠
        for i in range(len(snap['states'])):
            for j in range(i + 1, len(snap['states'])):
                a, b = snap['states'][i], snap['states'][j]
                ga = [P(r) for r in a['rings'] if P(r).is_valid]
                gb = [P(r) for r in b['rings'] if P(r).is_valid]
                inter = sum(g1.intersection(g2).area for g1 in ga for g2 in gb)
                if inter > 1.0:
                    bad.append('%d %s ∩ %s = %.1f 平方度' % (snap['year'], a['name'], b['name'], inter))
    return bad


def area_km2(rings):
    from shapely.geometry import Polygon as P
    s = sum(P(r).area for r in rings)
    return s * 111.32 * 111.32 * 0.82      # 中纬度近似


def qa():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MplPoly
    from matplotlib import font_manager
    for f in ('Microsoft YaHei', 'SimHei'):
        try:
            font_manager.findfont(f, fallback_to_default=False)
            matplotlib.rcParams['font.sans-serif'] = [f]
            break
        except Exception:
            continue
    matplotlib.rcParams['axes.unicode_minus'] = False
    fig, axes = plt.subplots(2, 4, figsize=(21, 11.5))
    axes = axes.ravel()
    for ax, snap in zip(axes, SNAPSHOTS):
        for st in snap['states']:
            for r in st['rings']:
                ax.add_patch(MplPoly(r, closed=True, facecolor=st['color'], edgecolor='k',
                                     lw=0.9, alpha=0.55, zorder=2))
            for n, role, lo, la in st['seats'][:1]:
                ax.plot(lo, la, 'k*', ms=7, zorder=5)
        ax.set_xlim(93, 124); ax.set_ylim(17, 51)
        ax.set_aspect(1 / 0.83); ax.grid(alpha=.15)
        ax.set_title('%d 年 · %s' % (snap['year'], snap['name']), fontsize=13)
        ax.tick_params(labelsize=7)
    axes[-1].axis('off')
    fig.tight_layout()
    p = os.path.join(os.environ.get('TEMP', '/tmp'), 'wj_states_qa.png')
    fig.savefig(p, dpi=85)
    print('QA 图：' + p)


def main():
    from shapely.geometry import Polygon as P
    bad = check()
    snaps = []
    for snap in SNAPSHOTS:
        states = []
        for st in snap['states']:
            states.append({
                'name': st['name'], 'color': st['color'],
                'rings': [[[round(x, 2), round(y, 2)] for x, y in r] for r in st['rings']],
                'seats': [{'name': n, 'role': rol, 'lon': lo, 'lat': la} for n, rol, lo, la in st['seats']],
                'meta': {'source': '示意性重建（山川为界）', 'verified': True}
            })
        snaps.append({'year': snap['year'], 'name': snap['name'], 'states': states})

    data = {'meta': {
        'title': '魏晋南北朝 · 疆域断面（220–589）',
        'count': len(snaps),
        'note': ('七个断面的示意性重建：262 三国 / 300 西晋 / 382 前秦·东晋 / 500 北魏·南齐 / '
                 '546 东魏·西魏·梁 / 576 北周·北齐·陈 / 589 隋。边界以山川（燕山、阴山、黄河、'
                 '秦岭、淮河、长江、南岭、祁连山）为界手工推演，非精确数字化；同一政权的疆域变化'
                 '只在这些断面之间切换，断面内的局部得失不另绘。'),
        'generated_by': 'tools/build_wei_jin_states.py'}, 'snapshots': snaps}

    js = ('// 魏晋南北朝 · 疆域断面（七个断面，220–589）\n'
          '// 由 tools/build_wei_jin_states.py 生成；改边界请改该脚本，勿手改本文件。\n'
          '// 结构：{meta, snapshots:[{year, name, states:[{name, color, rings:[[[lon,lat],…]], seats, meta}]}]}\n'
          'window.WEI_JIN_STATES = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(js)
    print('写入 %s（%.1f KB）' % (os.path.basename(OUT), len(js.encode('utf-8')) / 1024))
    for s in snaps:
        line = '  %d %-12s ' % (s['year'], s['name'])
        line += '｜'.join('%s %.0f万km²' % (x['name'], area_km2(x['rings']) / 1e4) for x in s['states'])
        print(line)
    for b in bad:
        print('  ⚠ ' + b)
    print('✅ 几何全部有效' if not bad else '❌ %d 处问题' % len(bad))
    if '--qa' in sys.argv:
        qa()
    return 1 if bad else 0


if __name__ == '__main__':
    from shapely.geometry import Polygon
    sys.exit(main())
