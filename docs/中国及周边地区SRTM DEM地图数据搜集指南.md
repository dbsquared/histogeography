# 中国及周边地区 SRTM DEM 地图数据搜集指南

> 本文档记录了从地理空间数据云（GSCloud）平台获取覆盖中国及周边地区 SRTM 90M 分辨率数字高程数据（DEM）的完整过程，包括平台探索、数据定位、命名规则推导、下载链接模式发现，以及自动化下载脚本的实现。

---

## 1 项目背景

我们需要获取覆盖中国及周边地区的数字高程模型（DEM）数据，用于地理空间分析。经过调研，地理空间数据云（GSCloud）平台 <sup><a href="#cite-1">[1]</a></sup> 提供免费的 SRTM 90M 分辨率原始高程数据，数据覆盖全球，共享方式为免费，是理想的数据来源。

---

## 2 平台初步探索

### 2.1 认识 GSCloud

GSCloud（地理空间数据云）是由中国科学院计算机网络信息中心运营的遥感数据一站式服务平台，主要提供以下服务：

| 服务 | 说明 |
|------|------|
| 数据获取 | 提供Landsat、Sentinel、MODIS、DEM等全球遥感数据，永久免费 |
| 在线计算 | 提供在线模型和IA编程环境，无需安装即可进行数据处理 |
| 数据众包 | 用户可参与数据需求发布和任务完成，获取报酬或积分 |
| 数据共享 | 支持上传和分享遥感解译数据、地理信息数据等成果 |
| 信息聚类 | 查看最新新闻、公告、典型案例和使用帮助 |

平台首页地址：`https://www.gscloud.cn/home#page4`

### 2.2 平台数据统计

截至访问时，平台的规模数据如下：

- 用户总数：142.83万
- 昨日注册：533
- 计算任务：228,670
- 总数据量：1.71PB

### 2.3 联系方式

| 渠道 | 信息 |
|------|------|
| 邮箱 | data@cnic.cn |
| 数据业务电话 | 010-58812568 / 13911820679 |
| 商务合作电话 | 18610570353 |
| 技术问题电话 | 13027707257 |

---

## 3 数据定位

### 3.1 DEM 数据集概览

在平台的「公开数据」分类下，「DEM 数字高程数据」类别（ID: 302）中包含以下数据产品：

| 数据集 | ID | 分辨率 | 数据量 |
|--------|----|--------|--------|
| SRTMDEM 90M 分辨率原始高程数据 | 305 | 90M | 12.2GB |
| SRTMDEMUTM 90M 分辨率数字高程数据产品 | 306 | 90M | 1.6GB |
| SRTMSLOPE 90M 分辨率坡度数据产品 | 307 | 90M | 3.5GB |
| SRTMTPI 90M 分辨率坡位数据产品 | 308 | 90M | 342.5MB |
| SRTMASPECT 90M 分辨率坡向数据产品 | 309 | 90M | 4.0GB |
| ASTER GDEM 30M 分辨率数字高程数据 | 310 | 30M | 92.3GB |
| GDEMV2 30M 分辨率数字高程数据 | 421 | 30M | 250.4GB |
| GDEMV3 30M 分辨率数字高程数据 | aeab8000… | 30M | 318.3GB |

我们最终选择 **SRTMDEM 90M 分辨率原始高程数据**（ID: 305），其数据访问页面为：

```
https://www.gscloud.cn/sources/accessdata/305?pid=302
```

### 3.2 为什么选择 SRTM 90M

- 全球覆盖面积广，包含中国全境及周边地区
- 数据量适中（共872个文件），适合批量下载
- 免费共享，登录即可下载
- 90M分辨率虽不及ASTER GDEM的30M，但对多数地形分析场景已足够

---

## 4 命名规则推导

### 4.1 观察数据表

进入数据访问页面后，能看到数据列表，每条记录包含以下字段：

| 字段 | 说明 |
|------|------|
| 数据标识 | 如 `srtm_25_02` |
| 条带号 | 对应经度方向的带号 |
| 行编号 | 对应纬度方向的行号 |
| 经度 | 该瓦片中心的经度值 |
| 纬度 | 该瓦片中心的纬度值 |

### 4.2 推导坐标转换公式

通过对数据列表中多条记录的交叉分析，我们推导出文件名与地理坐标之间的转换关系：

**正推（文件名 → 坐标）：**

```
经度 = -57.5 + (条带号 - 25) × 5
纬度 = 52.5 - (行编号 - 2) × 5
```

**反推（坐标 → 文件名）：**

```
条带号 = 25 + (经度 + 57.5) / 5    （四舍五入取整）
行编号 = 2 + (52.5 - 纬度) / 5      （四舍五入取整）
```

### 4.3 验证示例

以 `srtm_65_03` 为例：

- 条带号 = 65，行编号 = 3
- 经度 = -57.5 + (65 - 25) × 5 = -57.5 + 200 = **142.5**（东经142.5°）
- 纬度 = 52.5 - (3 - 2) × 5 = 52.5 - 5 = **47.5**（北纬47.5°）

这与平台页面上显示的经纬度值完全吻合，验证了公式的正确性。

### 4.4 命名规则图示

```
SRTM 瓦片命名：srtm_XX_YY
                  │   │
                  │   └── 行编号（纬度方向）
                  └────── 条带号（经度方向）

每个瓦片覆盖 5° × 5° 的区域
瓦片中心坐标 = (条带号对应经度, 行编号对应纬度)
瓦片范围 = (中心经度-2.5° ~ 中心经度+2.5°) × (中心纬度-2.5° ~ 中心纬度+2.5°)
```

---

## 5 中国地区的文件范围

### 5.1 地理边界定义

中国及周边地区的坐标范围：

| 边界 | 数值 |
|------|------|
| 最西端 | 73°E（帕米尔高原） |
| 最东端 | 135°E（黑龙江以东） |
| 最南端 | 18°N（南海诸岛） |
| 最北端 | 54°N（漠河以北） |

### 5.2 计算对应的文件名范围

根据反推公式，为覆盖上述区域，需要的数据瓦片应与目标区域有重叠：

**条带号范围（经度方向）：**

- 条带号 ≤ 135 的同时，条带号 + 1 对应区域 ≥ 73
- 即条带号从 **52** 到 **64**，共 13 个值

**行编号范围（纬度方向）：**

- 行编号对应区域 ≤ 54 的同时，行编号 + 1 对应区域 ≥ 18
- 即行编号从 **02** 到 **09**，共 8 个值

### 5.3 文件统计

- 总文件数：13 × 8 = **104 个文件**
- 单个文件约 1-50 MB
- 总数据量估计：1-5 GB

### 5.4 部分参考文件名

| 区域 | 经度范围 | 纬度范围 | 条带号 | 行编号 | 文件名 |
|------|----------|----------|--------|--------|--------|
| 中国西北角 | 73°-78°E | 50°-55°N | 52 | 02 | `srtm_52_02` |
| 中国西南角 | 73°-78°E | 15°-20°N | 52 | 09 | `srtm_52_09` |
| 中国东北角 | 130°-135°E | 50°-55°N | 64 | 02 | `srtm_64_02` |
| 中国东南角 | 130°-135°E | 15°-20°N | 64 | 09 | `srtm_64_09` |
| 北京附近 | 116°-121°E | 39°-44°N | 60 | 05 | `srtm_60_05` |
| 上海附近 | 121°-126°E | 30°-35°N | 61 | 07 | `srtm_61_07` |
| 广州附近 | 113°-118°E | 22°-27°N | 59 | 09 | `srtm_59_09` |
| 成都附近 | 101°-106°E | 30°-35°N | 58 | 07 | `srtm_58_07` |
| 拉萨附近 | 91°-96°E | 29°-34°N | 56 | 06 | `srtm_56_06` |
| 乌鲁木齐附近 | 81°-86°E | 39°-44°N | 54 | 05 | `srtm_54_05` |

---

## 6 下载链接模式发现

### 6.1 获取认证信息

GSCloud平台的文件下载需要认证，具体步骤如下：

1. **登录平台**：访问 https://www.gscloud.cn/ 并登录账号
2. **进入数据页面**：导航到 SRTMDEM 90M 数据访问页面
3. **触发单文件下载**：在数据列表中点击任意一条记录的下载按钮
4. **抓取下载链接**：在浏览器中，该下载请求会生成一个包含认证参数的完整URL

### 6.2 链接结构分析

通过手动触发一次下载，我们获得了如下格式的链接：

```
https://bjdl.gscloud.cn/sources/download/305/srtm_65_03?sid=0XaXN0mR2jBonk5VRB2fxm3lq0sA-nWo1GhZcmu5s5bClQ&uid=1465338
```

拆解该URL：

| 组成部分 | 值 | 说明 |
|----------|-----|------|
| 基础URL | `https://bjdl.gscloud.cn/sources/download/305/` | 数据集下载端点，305为数据集ID |
| 文件名 | `srtm_65_03` | 数据标识，与列表中的标识完全对应 |
| sid | `0XaXN0mR2jBonk5VRB2fxm3lq0sA-nWo1GhZcmu5s5bClQ` | 会话认证令牌，临时有效 |
| uid | `1465338` | 用户ID |

### 6.3 下载链接模板

基于上述分析，可以推导出通用的下载链接模板：

```
https://bjdl.gscloud.cn/sources/download/305/{文件名}?sid={会话令牌}&uid={用户ID}
```

其中：

- `{文件名}`：替换为目标数据标识，如 `srtm_60_05`
- `{会话令牌}`：从手动触发的下载请求中获取，有时效性
- `{用户ID}`：从手动触发的下载请求中获取

### 6.4 如何获取 sid 和 uid

**方法一：浏览器开发者工具（推荐）**

1. 登录 GSCloud 平台
2. 按 `F12` 打开浏览器开发者工具
3. 切换到 **Network（网络）** 标签页
4. 在数据页面点击任意文件的下载按钮
5. 在 Network 列表中找到对应的下载请求（URL包含 `bjdl.gscloud.cn/sources/download`）
6. 点击该请求，查看 Headers 或 Query String Parameters
7. 复制 `sid` 和 `uid` 的值

**方法二：直接从浏览器下载对话框获取**

- 部分浏览器在弹出下载确认时会显示完整URL
- 可从下载管理器中复制链接地址

### 6.5 关于 sid 的注意事项

- **时效性**：sid 通常只在当前会话中有效（几分钟到几小时不等）
- **绑定限制**：sid 可能与特定IP或会话绑定
- **刷新获取**：如遇到401/403错误，需重新手动触发一次下载以获取新的sid
- **批量下载建议**：获取sid后应尽快启动批量下载，避免令牌过期

---

## 7 自动化下载脚本

### 7.1 脚本概述

基于上述发现，我们编写了一个 Python 脚本来自动下载中国及周边地区所需的所有 SRTM 瓦片数据。

### 7.2 脚本功能

- 自动生成中国及周边地区所需的全部104个SRTM瓦片文件名
- 支持断点续传（通过 `--start-from` 参数）
- 跳过已存在的文件（通过 `--skip-existing` 参数）
- 下载进度条显示（基于 tqdm）
- 失败自动重试（最多3次，指数退避）
- 下载完整性验证（检查文件大小）
- 自动清理不完整的下载文件

### 7.3 安装依赖

```bash
pip install requests tqdm
```

### 7.4 基本用法

```bash
python download_srtm_china.py --sid YOUR_SID --uid YOUR_UID
```

### 7.5 高级用法

```bash
# 指定输出目录
python download_srtm_china.py --sid YOUR_SID --uid YOUR_UID --output-dir my_srtm_data

# 从特定文件开始续传
python download_srtm_china.py --sid YOUR_SID --uid YOUR_UID --start-from srtm_60_05

# 跳过已存在的文件
python download_srtm_china.py --sid YOUR_SID --uid YOUR_UID --skip-existing

# 组合使用
python download_srtm_china.py --sid YOUR_SID --uid YOUR_UID --output-dir china_dem --skip-existing
```

### 7.6 核心代码逻辑

文件名生成的核心逻辑：

```python
def generate_filenames():
    """生成中国及周边地区所需的所有SRTM文件名"""
    filenames = []
    # 条带号范围: 52-64 (对应经度73°-135°E)
    # 行编号范围: 02-09 (对应纬度18°-54°N)
    for band in range(52, 65):       # 52 to 64 inclusive
        for row in range(2, 10):     # 2 to 9 inclusive
            filename = f"srtm_{band:02d}_{row:02d}"
            filenames.append(filename)
    return filenames
```

下载链接构建：

```python
url_template = "https://bjdl.gscloud.cn/sources/download/305/{filename}?sid={sid}&uid={uid}"
url = url_template.format(filename=filename, sid=args.sid, uid=args.uid)
```

---

## 8 数据文件使用指南

### 8.1 文件格式

下载的文件为 `.img` 格式（ERDAS Imagine 镜像文件），这是地理空间领域广泛使用的栅格数据格式。

### 8.2 打开方式

| 软件 | 类型 | 说明 |
|------|------|------|
| **QGIS** | 免费开源 | 推荐首选，菜单栏 → 图层 → 添加图层 → 添加栅格图层 |
| **GDAL** | 命令行 | `gdalinfo your_file.img` 查看信息，`gdal_translate your_file.img output.tif` 转换格式 |
| **Python + rasterio** | 编程 | `rasterio.open('your_file.img')` 读取数据 |
| ArcGIS | 商业 | 直接添加栅格图层即可识别 |
| ENVI | 商业 | 文件 → 打开文件 → 选择 .img |
| ERDAS Imagine | 商业 | .img 格式的原生软件 |

### 8.3 Python 读取示例

```python
import rasterio
import numpy as np

with rasterio.open('srtm_60_05.img') as src:
    # 读取元数据
    print("形状:", src.shape)
    print("坐标系:", src.crs)
    print("范围:", src.bounds)

    # 读取第一波段数据
    elevation = src.read(1)

    # 处理无效值
    elevation[elevation == src.nodata] = np.nan

    # 基本统计
    print("均值高程:", np.nanmean(elevation))
    print("最高点:", np.nanmax(elevation))
    print("最低点:", np.nanmin(elevation))
```

### 8.4 GDAL 常用命令

```bash
# 查看文件信息
gdalinfo srtm_60_05.img

# 转换为 GeoTIFF 格式
gdal_translate srtm_60_05.img srtm_60_05.tif

# 创建金字塔（加快大文件显示速度）
gdaladdo -r average srtm_60_05.img 2 4 8 16

# 查询某点的像素值
gdallocationinfo -valonly -geoloc srtm_60_05.img 116.4 39.9
```

### 8.5 数据特点

| 属性 | 值 |
|------|-----|
| 投影 | 经纬度/WGS84 |
| 数据类型 | 16位有符号整数（Int16） |
| 无效值 | 常见为 -32768 |
| 单位 | 米 |
| 分辨率 | 约90米（每个像素代表约90m×90m地面区域） |
| 单个瓦片覆盖范围 | 5° × 5° |

---

## 9 数据来源引用规范

使用本数据时，请遵守平台的引用规范：

**中文发表的成果：**

> 数据来源于中国科学院计算机网络信息中心地理空间数据云平台(http://www.gscloud.cn)

**英文发表的成果：**

> The data set is provided by Geospatial Data Cloud site, Computer Network Information Center, Chinese Academy of Sciences. (http://www.gscloud.cn)

---

## 附录 A 完整文件名列表

中国及周边地区（经度73°-135°E，纬度18°-54°N）所需的所有SRTM瓦片文件名：

```
srtm_52_02  srtm_53_02  srtm_54_02  srtm_55_02  srtm_56_02  srtm_57_02  srtm_58_02  srtm_59_02  srtm_60_02  srtm_61_02  srtm_62_02  srtm_63_02  srtm_64_02
srtm_52_03  srtm_53_03  srtm_54_03  srtm_55_03  srtm_56_03  srtm_57_03  srtm_58_03  srtm_59_03  srtm_60_03  srtm_61_03  srtm_62_03  srtm_63_03  srtm_64_03
srtm_52_04  srtm_53_04  srtm_54_04  srtm_55_04  srtm_56_04  srtm_57_04  srtm_58_04  srtm_59_04  srtm_60_04  srtm_61_04  srtm_62_04  srtm_63_04  srtm_64_04
srtm_52_05  srtm_53_05  srtm_54_05  srtm_55_05  srtm_56_05  srtm_57_05  srtm_58_05  srtm_59_05  srtm_60_05  srtm_61_05  srtm_62_05  srtm_63_05  srtm_64_05
srtm_52_06  srtm_53_06  srtm_54_06  srtm_55_06  srtm_56_06  srtm_57_06  srtm_58_06  srtm_59_06  srtm_60_06  srtm_61_06  srtm_62_06  srtm_63_06  srtm_64_06
srtm_52_07  srtm_53_07  srtm_54_07  srtm_55_07  srtm_56_07  srtm_57_07  srtm_58_07  srtm_59_07  srtm_60_07  srtm_61_07  srtm_62_07  srtm_63_07  srtm_64_07
srtm_52_08  srtm_53_08  srtm_54_08  srtm_55_08  srtm_56_08  srtm_57_08  srtm_58_08  srtm_59_08  srtm_60_08  srtm_61_08  srtm_62_08  srtm_63_08  srtm_64_08
srtm_52_09  srtm_53_09  srtm_54_09  srtm_55_09  srtm_56_09  srtm_57_09  srtm_58_09  srtm_59_09  srtm_60_09  srtm_61_09  srtm_62_09  srtm_63_09  srtm_64_09
```

共计 **104 个文件**。

---

## 附录 B 数据获取流程总结

```
1. 访问平台首页
   https://www.gscloud.cn/
   │
2. 注册/登录账号
   │
3. 导航至数据页面
   公开数据 → DEM数字高程数据 → SRTMDEM 90M 原始高程数据
   https://www.gscloud.cn/sources/accessdata/305?pid=302
   │
4. 分析数据表结构
   识别字段：数据标识、条带号、行编号、经度、纬度
   │
5. 推导命名规则
   条带号 ↔ 经度：经度 = -57.5 + (条带号-25) × 5
   行编号 ↔ 纬度：纬度 = 52.5 - (行编号-2) × 5
   │
6. 确定中国地区文件范围
   条带号: 52-64, 行编号: 02-09, 共104个文件
   │
7. 手动触发一次下载
   在数据页面点击任意文件的下载按钮
   │
8. 抓取下载链接中的认证参数
   从浏览器开发者工具(F12) → Network 标签页获取
   记录 sid（会话令牌）和 uid（用户ID）
   │
9. 分析下载URL模式
   https://bjdl.gscloud.cn/sources/download/305/{文件名}?sid={令牌}&uid={用户ID}
   │
10. 运行自动化脚本批量下载
    python download_srtm_china.py --sid YOUR_SID --uid YOUR_UID
    │
11. 使用GIS软件或编程工具打开和分析数据
    QGIS / GDAL / Python+rasterio / ArcGIS / ENVI
```

---

## Sources

1. <span class="src-title">中国科学院计算机网络信息中心, 地理空间数据云平台. 提供全球免费遥感数据下载服务。</span>
   <a class="src-url" href="https://www.gscloud.cn" target="_blank" rel="noopener">https://www.gscloud.cn</a>
