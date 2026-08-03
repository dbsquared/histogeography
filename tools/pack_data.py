# -*- coding: utf-8 -*-
"""把所有查看器数据打包成 data.js (全局变量), 使 file:// 双击打开也能用, 不依赖 fetch。

数据源 geojson / 高程二进制位于 viewer/; 打包产物 data.js 输出到仓库根目录
(与 index.html 同目录, 供 GitHub Pages 直接服务)。

路径约定: 本脚本位于 tools/, 故 ROOT = 上两级目录 = 仓库根。
"""
import json, base64, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(ROOT, 'viewer')


def load(p):
    with open(os.path.join(V, p), encoding='utf-8') as f:
        return json.load(f)


contours = load('contours.geojson')
provinces = load('provinces.geojson')
try:
    rivers = load('rivers.geojson')
except FileNotFoundError:
    rivers = {'type': 'FeatureCollection', 'features': []}
try:
    mountains = load('mountains.geojson')
except FileNotFoundError:
    mountains = {'type': 'FeatureCollection', 'features': []}
meta = load('elev_meta.json')
with open(os.path.join(V, 'elev_grid.bin'), 'rb') as f:
    grid = f.read()
g64 = base64.b64encode(grid).decode('ascii')

payload = {
    'contours': contours,
    'provinces': provinces,
    'rivers': rivers,
    'mountains': mountains,
    'elevMeta': meta,
    'elevGridB64': g64,
}

out = os.path.join(ROOT, 'data.js')
with open(out, 'w', encoding='utf-8') as f:
    f.write('window.APP_DATA=')
    json.dump(payload, f, ensure_ascii=False, separators=(',', ':'))
    f.write(';')

print('写入', out)
print('contours 要素:', len(contours['features']))
print('provinces 要素:', len(provinces['features']))
print('rivers 要素:', len(rivers['features']))
print('mountains 要素:', len(mountains['features']))
print('elevGrid base64 长度:', len(g64))
print('data.js 大小(MB): %.2f' % (os.path.getsize(out) / 1e6))
