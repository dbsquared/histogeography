# 华夏历史地图 · 3D 地形交互平台

基于 SRTM 90M 数字高程模型（DEM）与中国历史地理矢量数据，构建的**多时代历史地理**交互式地形地图项目。

本项目不局限于某一个朝代——它以真实地形为底，统一的交互框架还原不同历史时期的州郡、山川、城邑格局。当前已完成 **汉末（东汉）十三州** 时期的第一版地图（十三州州界与郡治、地形晕渲、河流、行政边界与南海诸岛附图），后续将持续接入更多时代（如先秦、唐、宋、明等）的历史地图。

> 项目目标：以统一的交互框架呈现中国历代历史地理空间信息，支持在浏览器中缩放、悬停查看地名与治所、按图层 / 时代切换浏览。

---

## 功能特性

- **地形底图**：SRTM 90M DEM 渲染的山体阴影（hillshade）+ 14 级自定义色阶（深水→雪顶），约 450m/px。
- **历史图层（按时代组织）**：
  - *汉末十三州（第一时期）*：十三州边界多边形，悬停高亮并显示「州名 + 州府」；各郡治所标注（郡名在上、治所名在下两行显示），州府以金色圆点突出。
  - 后续时代将作为独立图层 / 时期接入，共享同一地形底图与交互框架。
- **河流 / 湖泊**：Natural Earth 10m 水系叠加（长江、黄河、珠江等主要河流中文标注）。
- **行政边界**：国界（含十段线）、省界（含港澳台标注）、南海附图。
- **交互式查看器**：基于 Leaflet.js，纯前端，支持图层复选框切换、时代切换。
- **数字化工具**：`digitize_v2.html` 交互式打点重建，从参考地图提取历史州界 GeoJSON。

---

## 快速开始（本地预览查看器）

查看器为纯静态前端，但会因浏览器安全策略对 `fetch` 本地文件有限制，因此需通过本地 HTTP 服务器打开（**网页文件位于仓库根目录**）：

```bash
# 在仓库根目录执行
python -m http.server 8765
# 然后浏览器打开： http://localhost:8765/index.html
```

> 提示：直接双击 `index.html`（file:// 协议）可能无法加载数据图层，请务必使用上面的本地服务器方式。
> 在线版本：https://dbsquared.github.io/histogeography/ （由 GitHub Pages 从 `main` 分支根目录直接发布，推送 `main` 即自动重建）。

---

## 项目结构

```
3D地图制作/
├── README.md                  # 本文件
├── docs/                      # 工程文档（engineering-spec.md、plan.md 等）
├── index.html                 # ★ 主查看器页面（Leaflet），位于根目录
├── base_terrain.png           # 地形底图（71MB，hillshade 渲染）
├── data.js / scs_inset_data.js / cities.js / han_states.js / three_kingdoms_sites.js  # 运行时数据
├── .nojekyll                  # 关闭 GitHub Pages 的 Jekyll 处理
├── tools/                     # 构建与数据处理脚本
│   ├── download_srtm_china.py # SRTM 90M DEM 批量下载（GSCloud）
│   ├── terrain_renderer.py    # DEM → hillshade / 色阶渲染
│   ├── build_han_states.py    # 合并各州 GeoJSON → han_states.js
│   ├── build_provinces_layer.py / build_rivers_layer.py / build_mountains_layer.py
│   ├── build_scs_inset.py     # 南海附图构建
│   ├── build_thirteen_states.py / calibrate_13states.py
│   ├── geo_mapping.py         # 像素↔经纬 仿射映射
│   ├── pack_data.py           # 打包 viewer/ 源 → 根目录 data.js
│   ├── validate_geojson.py / digitize_server.py
│   └── data/                  # 构建输入 json（bingzhou_anchor_table.json 等）
├── viewer/                    # 数字化 / 重建源（不参与 Pages 服务，用于重新生成 data.js）
│   ├── han_states_raw/        # 各州原始 GeoJSON（含 GCP 像素侧通道）
│   ├── *.geojson / elev_*.bin / elev_meta.json  # 图层源数据
│   ├── ref_imgs/              # 参考地图（数字化参考扫描）
│   └── digitize*.html / edit_states_terrain.html  # 数字化工具
└── …（其余为各时期迭代过程中的实验 / 调试脚本，见 tools/ 与历史提交）
```

> 说明：运行时只需根目录的网页文件；`tools/` 为构建管线，`viewer/` 为数字化与重建源；`rendered/`、`srtm_china_data/`、`汉末十三州地图范例/`、`data/` 等为大体量中间数据，已 gitignore 不入库。

---

## 数据管线

```
SRTM 90M DEM (GSCloud)
      │  tools/download_srtm_china.py
      ▼
  本地瓦片 (srtm_china_data/, 已 gitignore，约 2.7GB)
      │  tools/terrain_renderer.py
      ▼
  base_terrain.png + hillshade (约 450m/px)
      │
      ├── 参考地图数字化 → viewer/digitize_v2.html → viewer/han_states_raw/*.geojson
      │                              │  tools/build_han_states.py
      │                              ▼
      │                         han_states.js (州界+郡治)
      ├── Natural Earth 10m → tools/build_rivers_layer.py / build_provinces_layer.py
      ├── viewer/*.geojson + elev_* → tools/pack_data.py
      ▼
  index.html (仓库根目录, Leaflet 叠加所有图层)
```

---

## 数据获取：SRTM 90M DEM 下载

若需重新下载地形数据，使用 `tools/download_srtm_china.py`（数据约 1–5GB，已通过 `.gitignore` 排除，不入库）。

### 步骤 1：获取 GSCloud 会话令牌

下载链接中的 `sid` 是临时会话令牌，需从浏览器获取：

1. 登录 https://www.gscloud.cn/
2. 数据来源 → DEM数字高程数据 → SRTMDEM 90M 分辨率原始高程数据（ID: 305）
3. 点击任一 `.srtm_XX_XX.img` 的下载按钮
4. 打开开发者工具（F12）→ Network，找到到 `bjdl.gscloud.cn/sources/download/305/` 的请求
5. 从其查询参数复制 `sid`（长字符串）与 `uid`（数字）

### 步骤 2：运行下载

```bash
pip install requests tqdm
python tools/download_srtm_china.py --sid YOUR_SID --uid YOUR_UID
# 续传：--skip-existing   指定目录：--output-dir my_data
```

> **注意**：`sid` 有效期较短，下载中出现大量 401/403 需重新获取。

---

## 数据来源与版权

| 数据 | 来源 | 许可 |
|------|------|------|
| SRTM 90M DEM | 中国科学院地理空间数据云 (GSCloud, www.gscloud.cn) | 科研免费，引用需注明 |
| 河流 / 湖泊 / 行政边界 | Natural Earth (naturalearthdata.com) | Public Domain |
| 历史州郡矢量 | 按时代分别基于参考地图数字化重建（本项目） | — |

使用上述数据时请遵守各平台数据政策，并在成果中注明来源。

---

## 当前状态与路线图

- [x] 地形底图渲染（hillshade + 色阶）
- [x] **汉末十三州（第一时期）**：十三州州界与郡治接入（含手工精修与自动初稿）
- [x] 河流 / 湖泊 / 行政边界 / 南海附图叠加
- [x] 交互式查看器（悬停、图层切换、时代组织）
- [x] GitHub Pages 在线发布（main 根目录）
- [ ] 汉末十三州剩余细节打磨与史料校核
- [ ] **扩展更多历史时代**（先秦 / 唐 / 宋 / 明 等）的地图与图层
- [ ] 高程剖面 / 距离量测等分析工具

---

## 许可

代码以 MIT 许可开源；地形与地理数据请遵循上述各自的数据使用条款。
