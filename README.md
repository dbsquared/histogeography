# 汉末十三州 · 历史地理 3D 地形地图

基于 SRTM 90M 数字高程模型（DEM）与中国历史地理矢量数据，构建的**汉末（东汉）十三州**交互式地形地图查看器。
目前已完成 **冀州、并州、幽州** 三州的州界与郡治图层接入，并叠加了地形晕渲、河流、郡县、行政边界与南海诸岛附图。

> 项目目标：以真实地形为底，还原汉末州—郡两级行政地理格局，支持在浏览器中缩放、悬停查看州名与州府、切换不同图层。

---

## 功能特性

- **地形底图**：SRTM 90M DEM 渲染的山体阴影（hillshade）+ 14 级自定义色阶（深水→雪顶），约 450m/px。
- **州界图层**：冀州 / 并州 / 幽州 三州边界多边形，悬停高亮并显示「州名 + 州府」。
- **郡治图层**：各郡治所标注（郡名在上、治所名在下两行显示），州府以金色圆点突出。
- **河流 / 湖泊**：Natural Earth 10m 水系叠加（长江、黄河、珠江等主要河流中文标注）。
- **行政边界**：国界（含十段线）、省界（含港澳台标注）、南海附图。
- **交互式查看器**：基于 Leaflet.js，纯前端，支持图层复选框切换。
- **数字化工具**：`digitize_v2.html` 交互式打点重建，从参考地图提取州界 GeoJSON。

---

## 快速开始（本地预览查看器）

查看器为纯静态前端，但会因浏览器安全策略对 `fetch` 本地 `.geojson` 文件有限制，因此需通过本地 HTTP 服务器打开：

```bash
cd viewer
python -m http.server 8765
# 然后浏览器打开： http://localhost:8765/index.html
```

> 提示：直接双击 `viewer/index.html`（file:// 协议）可能无法加载 GeoJSON 图层，请务必使用上面的本地服务器方式。

---

## 项目结构

```
3D地图制作/
├── README.md                  # 本文件
├── engineering-spec.md        # 工程规格与数据命名规则
├── plan.md                    # 实施计划
├── viewer/                    # ★ 核心交付物：交互式查看器（自包含）
│   ├── index.html             # 主查看器页面（Leaflet）
│   ├── base_terrain.png       # 地形底图（71MB，hillshade 渲染）
│   ├── data.js / elev_grid.bin / elev_meta.json   # 高程数据
│   ├── han_states.js          # 三州州界 + 郡治（由 build_han_states.py 生成）
│   ├── han_states_raw/        # 各州原始 GeoJSON（含 GCP 像素侧通道）
│   │   ├── 冀州.geojson
│   │   ├── 并州.geojson
│   │   └── 幽州.geojson
│   ├── provinces.geojson      # 省级行政边界
│   ├── rivers.geojson         # 河流水系
│   ├── contours.geojson       # 等高线
│   ├── cities.js              # 城市点
│   ├── scs_inset_data.js      # 南海附图数据（十段线 + 岛礁）
│   ├── ref_imgs/              # 参考地图（十三州各州全览图）
│   ├── digitize.html          # 数字化工具 v1
│   └── digitize_v2.html       # 数字化工具 v2（仿射变换 GCP 重建）
├── download_srtm_china.py     # SRTM 90M DEM 批量下载（GSCloud）
├── terrain_renderer.py        # DEM → hillshade / 色阶渲染
├── build_han_states.py        # 合并各州 GeoJSON → han_states.js
├── build_provinces_layer.py   # 行政边界图层构建
├── build_rivers_layer.py      # 河流图层构建
├── build_scs_inset.py         # 南海附图构建
├── build_thirteen_states.py   # 十三州总装
├── calibrate_13states.py      # 州界配准校准
├── geo_mapping.py             # 像素↔经纬 仿射映射
├── digitize_server.py         # 数字化后端（可选）
├── validate_geojson.py        # GeoJSON 校验
└── …（其余为各州迭代过程中的实验/调试脚本）
```

---

## 数据管线

```
SRTM 90M DEM (GSCloud)
      │  download_srtm_china.py
      ▼
  本地瓦片 (srtm_china_data/, 已 gitignore，约 2.7GB)
      │  terrain_renderer.py
      ▼
  base_terrain.png + hillshade (约 450m/px)
      │
      ├── 参考地图数字化 → digitize_v2.html → han_states_raw/*.geojson
      │                              │  build_han_states.py
      │                              ▼
      │                         han_states.js (州界+郡治)
      ├── Natural Earth 10m → build_rivers_layer.py / build_provinces_layer.py
      ▼
  viewer/index.html (Leaflet 叠加所有图层)
```

---

## 数据获取：SRTM 90M DEM 下载

若需重新下载地形数据，使用 `download_srtm_china.py`（数据约 1–5GB，已通过 `.gitignore` 排除，不入库）。

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
python download_srtm_china.py --sid YOUR_SID --uid YOUR_UID
# 续传：--skip-existing   指定目录：--output-dir my_data
```

> **注意**：`sid` 有效期较短，下载中出现大量 401/403 需重新获取。

---

## 数据来源与版权

| 数据 | 来源 | 许可 |
|------|------|------|
| SRTM 90M DEM | 中国科学院地理空间数据云 (GSCloud, www.gscloud.cn) | 科研免费，引用需注明 |
| 河流 / 湖泊 / 行政边界 | Natural Earth (naturalearthdata.com) | Public Domain |
| 历史州郡矢量 | 基于参考地图数字化重建（本项目） | — |

使用上述数据时请遵守各平台数据政策，并在成果中注明来源。

---

## 当前状态与路线图

- [x] 地形底图渲染（hillshade + 色阶）
- [x] 冀州 / 并州 / 幽州 三州州界与郡治接入
- [x] 河流 / 湖泊 / 行政边界 / 南海附图叠加
- [x] 交互式查看器（悬停、图层切换）
- [ ] 剩余十州（司隶、豫州、兖州、徐州、青州、荆州、扬州、益州、凉州、交州）数字化接入
- [ ] 高程剖面 / 距离量测等分析工具

---

## 许可

代码以 MIT 许可开源；地形与地理数据请遵循上述各自的数据使用条款。
