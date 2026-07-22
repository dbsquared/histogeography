#!/usr/bin/env python3
"""
SRTM 地形图渲染程序

基于 rasterio + matplotlib 的地形图渲染工具，支持：
1. 单文件渲染（高程色阶、山体阴影、等高线）
2. 多瓦片拼合渲染（覆盖中国大区域）
3. 多种渲染模式组合输出
4. 高分辨率PNG导出

依赖安装：
    pip install rasterio matplotlib numpy

使用方法：
    # 渲染单个文件（所有模式叠加）
    python terrain_renderer.py srtm_60_05.img

    # 仅渲染高程色阶
    python terrain_renderer.py srtm_60_05.img --mode elevation

    # 仅渲染山体阴影
    python terrain_renderer.py srtm_60_05.img --mode hillshade

    # 高程色阶 + 山体阴影叠加
    python terrain_renderer.py srtm_60_05.img --mode elevation+hillshade

    # 全部叠加（高程+阴影+等高线）
    python terrain_renderer.py srtm_60_05.img --mode all

    # 拼合多个瓦片渲染大区域
    python terrain_renderer.py --mosaic srtm_china_data/ --bounds 100 110 30 40

    # 自定义输出路径和分辨率
    python terrain_renderer.py srtm_60_05.img --output my_terrain.png --dpi 300

    # 自定义等高线间距
    python terrain_renderer.py srtm_60_05.img --mode all --contour-interval 100

    # 同时输出 GeoTIFF（含地理参考，可在 QGIS/ArcGIS 叠加）
    python terrain_renderer.py srtm_60_05.img --geotiff

作者：SOLO Assistant
数据来源：地理空间数据云 (https://www.gscloud.cn)
"""

import os
import sys
import glob
import argparse
import tempfile
import zipfile
from pathlib import Path

import numpy as np

# 项目根目录 — 所有临时文件锚定到此，避免塞满系统盘
_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_TMP = os.path.join(_PROJECT_DIR, '.workbuddy', 'tmp')
os.makedirs(_PROJECT_TMP, exist_ok=True)

def _project_temp_dir(prefix='srtm_'):
    """在项目目录下创建独立临时目录，用完即清理"""
    return tempfile.mkdtemp(prefix=prefix, dir=_PROJECT_TMP)


# 中文字体预检测（模块级别）
_CHINESE_FONT_PATH = None


def _detect_chinese_font():
    """检测系统中可用的中文字体文件路径"""
    import matplotlib.font_manager as fm

    # 候选中文字体列表（Windows 常用）
    candidates = [
        'Microsoft YaHei',      # 微软雅黑
        'SimHei',               # 黑体
        'SimSun',               # 宋体
        'FangSong',             # 仿宋
        'KaiTi',                # 楷体
        'DengXian',             # 等线
        'Noto Sans CJK SC',     # 思源黑体
        'WenQuanYi Micro Hei',  # 文泉驿微米黑
        'Noto Sans SC',         # Noto 简体中文
    ]

    # 遍历系统所有字体
    all_fonts = {f.name: f.fname for f in fm.fontManager.ttflist}

    for name in candidates:
        if name in all_fonts:
            return all_fonts[name]

    # 如果以上都找不到，搜索含中文命名的字体文件
    for f in fm.fontManager.ttflist:
        if any(keyword in f.name.lower() for keyword in
               ['yahei', 'simhei', 'simsun', 'cjk', 'chinese', 'hei', 'song', 'ming', 'kai']):
            return f.fname

    return None


def _setup_chinese_font():
    """设置 matplotlib 中文字体"""
    global _CHINESE_FONT_PATH
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties

    if _CHINESE_FONT_PATH is None:
        _CHINESE_FONT_PATH = _detect_chinese_font()

    if _CHINESE_FONT_PATH:
        plt.rcParams['font.sans-serif'] = [
            FontProperties(fname=_CHINESE_FONT_PATH).get_name(),
            'DejaVu Sans'
        ]
        plt.rcParams['axes.unicode_minus'] = False


def _is_zip_file(filepath):
    """检查文件是否为ZIP压缩格式（GSCloud下载的.img文件可能是ZIP压缩包）"""
    try:
        with open(filepath, 'rb') as f:
            magic = f.read(4)
        return magic[:2] == b'PK'
    except Exception:
        return False


def _extract_dem_from_zip(zip_path, extract_dir=None):
    """从ZIP压缩包中提取DEM栅格文件

    GSCloud下载的 .img 文件有时是ZIP压缩包，内含真实的 .img 或 .tif 文件。
    此函数解压到临时目录，返回内部栅格文件的路径。

    参数:
        zip_path: ZIP文件路径
        extract_dir: 解压目标目录（默认为临时目录）

    返回:
        内部DEM文件的路径列表
    """
    if extract_dir is None:
        # 每个zip独立子目录，锚定到项目目录
        extract_dir = _project_temp_dir(prefix='srtm_extract_')

    os.makedirs(extract_dir, exist_ok=True)

    dem_files = []
    raster_extensions = {'.img', '.tif', '.tiff', '.hdf', '.dt0', '.dt1', '.dt2'}

    with zipfile.ZipFile(zip_path, 'r') as zf:
        for name in zf.namelist():
            ext = os.path.splitext(name)[1].lower()
            if ext in raster_extensions and not name.startswith('__MACOSX'):
                # 提取到独立子目录防止冲突
                target = os.path.join(extract_dir, os.path.basename(name))
                with zf.open(name) as src, open(target, 'wb') as dst:
                    dst.write(src.read())
                dem_files.append(target)

    return dem_files


def load_dem(filepath):
    """加载单个DEM文件，返回高程数组和元数据

    自动处理GSCloud下载的ZIP压缩包格式：
    如果 .img 文件实际上是ZIP压缩包，会先解压再读取内部的栅格文件。
    """
    try:
        import rasterio
    except ImportError:
        print("错误: 缺少 rasterio 包。请运行: pip install rasterio")
        sys.exit(1)

    # 检查是否为ZIP压缩包
    extract_dir = None
    actual_file = filepath
    if _is_zip_file(filepath):
        print(f"  检测到ZIP压缩格式，正在解压...")
        extract_dir = _project_temp_dir(prefix='srtm_single_')
        dem_files = _extract_dem_from_zip(filepath, extract_dir)
        if not dem_files:
            raise IOError(f"ZIP压缩包中未找到栅格数据文件: {filepath}")
        # 使用找到的第一个栅格文件
        actual_file = dem_files[0]
        print(f"  解压得到: {os.path.basename(actual_file)}")

    try:
        with rasterio.open(actual_file) as src:
            elevation = src.read(1).astype(np.float32)
            nodata = src.nodata
            transform = src.transform
            crs = src.crs
            bounds = src.bounds
            profile = src.profile
    finally:
        # 清理临时解压目录
        if extract_dir:
            import shutil
            try:
                shutil.rmtree(extract_dir, ignore_errors=True)
            except Exception:
                pass

    # 处理无效值
    if nodata is not None:
        elevation[elevation == nodata] = np.nan
    # SRTM 常见无效值
    elevation[elevation == -32768] = np.nan
    elevation[elevation < -1000] = np.nan
    elevation[elevation > 9000] = np.nan

    return elevation, {
        'transform': transform,
        'crs': crs,
        'bounds': bounds,
        'nodata': nodata,
        'profile': profile,
    }


def mosaic_dems(directory, bounds=None, downsample=1):
    """将目录中的多个DEM瓦片拼合为一个大数组

    参数:
        directory: 包含 .img 文件的目录路径
        bounds: 可选，(min_lon, max_lon, min_lat, max_lat) 裁剪范围
        downsample: 下采样因子 (1=原图, 2=半分辨率, 5=1/5分辨率)

    返回:
        elevation: 拼合后的高程数组
        meta: 元数据字典
    """
    try:
        import rasterio
        from rasterio.merge import merge
        from rasterio.warp import calculate_default_transform, reproject
    except ImportError:
        print("错误: 缺少 rasterio 包。请运行: pip install rasterio")
        sys.exit(1)

    # 查找所有 .img 文件
    img_files = sorted(glob.glob(os.path.join(directory, "*.img")))
    if not img_files:
        print(f"错误: 在 {directory} 中未找到 .img 文件")
        sys.exit(1)

    print(f"找到 {len(img_files)} 个瓦片文件，正在拼合...")

    # 处理ZIP压缩格式：解压到独立子目录（锚定到项目目录）
    import shutil
    extract_base = _project_temp_dir(prefix='srtm_mosaic_')
    actual_files = []
    extract_dirs_to_cleanup = [extract_base]
    skip_corrupted = []
    for f in img_files:
        if _is_zip_file(f):
            try:
                # 每个zip解压到独立子目录
                dem_files = _extract_dem_from_zip(f, extract_dir=None)
                if dem_files:
                    actual_files.extend(dem_files)
                    # 记录第一个文件的父目录用于后续清理
                    extract_dirs_to_cleanup.append(os.path.dirname(dem_files[0]))
                else:
                    print(f"警告: {f} 解压后未找到栅格文件")
                    skip_corrupted.append(f)
            except Exception as e:
                print(f"警告: 解压 {f} 失败: {e}")
                skip_corrupted.append(f)
        else:
            actual_files.append(f)

    # 打开所有文件
    src_files = []
    for f in actual_files:
        try:
            src_files.append(rasterio.open(f))
        except Exception as e:
            print(f"警告: 无法打开 {f}: {e}")

    if not src_files:
        print("错误: 没有可用的文件")
        shutil.rmtree(extract_base, ignore_errors=True)
        sys.exit(1)

    # 使用 rasterio.merge 拼合
    # 如果下采样因子>1，先降低各源文件分辨率以减少内存需求
    if downsample > 1:
        print(f"  下采样因子: {downsample}x，降低分辨率以节省内存...")
        # 对每个源文件进行下采样
        downsampled_files = []
        ds_extract_dir = tempfile.mkdtemp(prefix='srtm_ds_')
        extract_dirs_to_cleanup.append(ds_extract_dir)
        
        for src in src_files:
            try:
                # 读取并下采样
                data = src.read(1)
                # 使用均值下采样
                h, w = data.shape
                new_h, new_w = h // downsample, w // downsample
                # 裁剪到可整除的尺寸
                trimmed = data[:new_h * downsample, :new_w * downsample]
                # 重塑并取均值
                downsampled = trimmed.reshape(new_h, downsample, new_w, downsample).mean(axis=(1, 3))
                downsampled = downsampled.astype(data.dtype)
                
                downsampled_files.append({
                    'data': downsampled,
                    'transform': src.transform * src.transform.scale(downsample, downsample),
                    'crs': src.crs,
                    'nodata': src.nodata,
                })
            except Exception as e:
                print(f"  警告: 下采样失败 ({src.name}): {e}")
        
        # 关闭所有文件
        for src in src_files:
            src.close()
        
        # 手动拼合下采样后的数据
        if not downsampled_files:
            print("错误: 所有文件下采样失败")
            for d in set(extract_dirs_to_cleanup):
                shutil.rmtree(d, ignore_errors=True)
            sys.exit(1)
        
        # 使用第一个文件的参数作为基准
        ref = downsampled_files[0]
        from rasterio.transform import Affine
        
        # 计算全局范围
        all_data = [d['data'] for d in downsampled_files]
        all_transforms = [d['transform'] for d in downsampled_files]
        
        # 找到全局左上角和右下角
        min_col = min(t.c for t in all_transforms)
        min_row = max(t.f for t in all_transforms)  # 最大的f值（最北端）
        max_col = max(t.c + d.shape[1] * t.a for t, d in zip(all_transforms, all_data))
        max_row = min(t.f + d.shape[0] * t.e for t, d in zip(all_transforms, all_data))  # 最大的e为负，取最小
        
        pixel_size = abs(ref['transform'].a)
        total_cols = int((max_col - min_col) / pixel_size)
        total_rows = int((min_row - max_row) / pixel_size)
        
        # 创建拼合数组
        elevation = np.full((total_rows, total_cols), -32768, dtype=np.float32)
        
        for item in downsampled_files:
            t = item['transform']
            data = item['data'].astype(np.float32)
            data[data == item.get('nodata', -32768)] = np.nan
            
            # 计算偏移量
            col_off = int((t.c - min_col) / pixel_size)
            row_off = int((min_row - t.f) / pixel_size)
            
            h, w = data.shape
            # 写入到拼合数组
            r_start = max(0, row_off)
            r_end = min(total_rows, row_off + h)
            c_start = max(0, col_off)
            c_end = min(total_cols, col_off + w)
            
            dr_start = r_start - row_off
            dr_end = h - (row_off + h - r_end)
            dc_start = c_start - col_off
            dc_end = w - (col_off + w - c_end)
            
            if r_start < r_end and c_start < c_end and dr_start < dr_end and dc_start < dc_end:
                patch = data[dr_start:dr_end, dc_start:dc_end]
                mask = ~np.isnan(patch)
                elevation[r_start:r_end, c_start:c_end][mask] = patch[mask]
        
        from rasterio.transform import Affine as Aff
        mosaic_transform = Aff(pixel_size, 0, min_col, 0, -pixel_size, min_row)
        ref_crs = ref['crs']
        
    else:
        mosaic_array, mosaic_transform = merge(src_files, nodata=-32768)

        # 关闭所有文件
        for src in src_files:
            src.close()

        # 提取第一波段
        elevation = mosaic_array[0].astype(np.float32)
        ref_crs = None

    # 清理临时解压目录
    for d in set(extract_dirs_to_cleanup):
        shutil.rmtree(d, ignore_errors=True)

    # 处理无效值
    elevation[elevation == -32768] = np.nan
    elevation[elevation < -1000] = np.nan
    elevation[elevation > 9000] = np.nan

    # 如果指定了裁剪范围
    if bounds:
        min_lon, max_lon, min_lat, max_lat = bounds
        # 计算像素范围
        from rasterio.transform import rowcol
        # 获取拼合后数据的CRS（优先使用已获取的ref_crs）
        if ref_crs is None and actual_files:
            try:
                with rasterio.open(actual_files[0]) as ref:
                    ref_crs = ref.crs
            except Exception:
                ref_crs = None

        # 假设数据是 WGS84 经纬度坐标
        height, width = elevation.shape
        # 计算经纬度对应的像素行列号
        col_min = max(0, int((min_lon - mosaic_transform.c) / mosaic_transform.a))
        col_max = min(width, int((max_lon - mosaic_transform.c) / mosaic_transform.a))
        row_min = max(0, int((mosaic_transform.f - max_lat) / (-mosaic_transform.e)))
        row_max = min(height, int((mosaic_transform.f - min_lat) / (-mosaic_transform.e)))

        if col_min < col_max and row_min < row_max:
            elevation = elevation[row_min:row_max, col_min:col_max]
            # 更新 transform
            from rasterio.transform import Affine
            mosaic_transform = Affine(
                mosaic_transform.a, mosaic_transform.b,
                mosaic_transform.c + col_min * mosaic_transform.a,
                mosaic_transform.d, mosaic_transform.e,
                mosaic_transform.f + row_min * mosaic_transform.e
            )

    meta = {
        'transform': mosaic_transform,
        'crs': ref_crs if bounds else None,
        'bounds': None,
        'nodata': -32768,
    }

    return elevation, meta


def compute_hillshade(elevation, azimuth=315, altitude=45, z_factor=1):
    """计算山体阴影（Hillshade）—— 内存优化版，分块处理

    参数:
        elevation: 高程数组 (2D numpy array)
        azimuth: 光源方位角（度），315为西北方向
        altitude: 光源高度角（度）
        z_factor: 高程放大因子

    返回:
        hillshade: 0-255的阴影数组
    """
    # 确保使用 float32 节省内存
    elevation = elevation.astype(np.float32)

    azimuth_rad = np.float32(np.radians(azimuth))
    altitude_rad = np.float32(np.radians(altitude))
    cos_alt = np.cos(altitude_rad)
    sin_alt = np.sin(altitude_rad)
    cos_az = np.cos(azimuth_rad)
    sin_az = np.sin(azimuth_rad)

    # 使用分块处理避免创建过多大型临时数组
    # 分块计算 hillshade
    h, w = elevation.shape
    block_size = 2000  # 每次处理2000行
    result = np.empty_like(elevation, dtype=np.uint8)

    for r_start in range(0, h, block_size):
        r_end = min(r_start + block_size, h)
        # 扩展1行边界用于梯度计算
        ext_start = max(0, r_start - 1)
        ext_end = min(h, r_end + 1)

        block = elevation[ext_start:ext_end, :]
        dy, dx = np.gradient(block * z_factor)

        # 裁剪回目标行（去掉边界行）
        if ext_start < r_start:
            dy = dy[1:]
            dx = dx[1:]
        if ext_end > r_end:
            dy = dy[:-1]
            dx = dx[:-1]

        slope = np.arctan(np.sqrt(dx**2 + dy**2)).astype(np.float32)
        aspect = np.arctan2(-dy, dx).astype(np.float32)

        hs_block = cos_alt * np.cos(slope) + sin_alt * np.sin(slope) * np.cos(azimuth_rad - aspect)
        hs_block = np.clip(hs_block, 0, 1)
        result[r_start:r_end, :] = (hs_block * 255).astype(np.uint8)

        # 释放临时变量
        del block, dy, dx, slope, aspect, hs_block

    return result


def create_terrain_colormap():
    """创建地形专用色阶

    返回 matplotlib ListedColormap，包含从深蓝（海下）到白色（雪山）的渐变
    """
    from matplotlib.colors import ListedColormap, LinearSegmentedColormap

    colors = [
        (0.00, '#2b5d8c'),   # 深蓝 - 深水
        (0.02, '#4a8ab5'),   # 浅蓝 - 浅水
        (0.05, '#7fb5d5'),   # 极浅蓝 - 沿海
        (0.08, '#b3d9a0'),   # 浅绿 - 低地
        (0.15, '#8cc579'),   # 绿 - 平原
        (0.25, '#6ba356'),   # 深绿 - 丘陵
        (0.35, '#c9b458'),   # 黄绿 - 低山
        (0.45, '#c9a048'),   # 土黄 - 中山
        (0.55, '#a67c3d'),   # 褐色 - 高山
        (0.65, '#8b5e2f'),   # 深褐 - 高原
        (0.75, '#9e7a6a'),   # 紫褐 - 极高山
        (0.85, '#c8b8a8'),   # 浅灰 - 雪线附近
        (0.95, '#e8ddd0'),   # 近白 - 永久积雪
        (1.00, '#ffffff'),   # 白色 - 雪顶
    ]

    cmap = LinearSegmentedColormap.from_list(
        'terrain_custom',
        [(pos, color) for pos, color in colors],
        N=256
    )

    return cmap


def render_elevation(ax, elevation, meta, cmap=None, vmin=None, vmax=None, alpha=1.0):
    """渲染高程色阶图层

    参数:
        ax: matplotlib axes
        elevation: 高程数组
        meta: 元数据
        cmap: 色阶（默认使用自定义地形色阶）
        vmin, vmax: 高程值范围
        alpha: 透明度
    """
    from matplotlib.colors import Normalize

    if cmap is None:
        cmap = create_terrain_colormap()

    # 获取有效数据范围（用 nanmin/nanmax 避免布尔索引大临时数组）
    if vmin is None:
        vmin = float(np.nanmin(elevation)) if not np.all(np.isnan(elevation)) else 0
    if vmax is None:
        vmax = float(np.nanmax(elevation)) if not np.all(np.isnan(elevation)) else 8000

    norm = Normalize(vmin=vmin, vmax=vmax)

    im = ax.imshow(
        elevation,
        cmap=cmap,
        norm=norm,
        alpha=alpha,
        extent=get_extent(meta),
        aspect='equal',
        origin='upper',
    )

    return im


def render_hillshade(ax, hillshade, meta, alpha=0.5):
    """渲染山体阴影图层

    参数:
        ax: matplotlib axes
        hillshade: 阴影数组 (0-255)
        meta: 元数据
        alpha: 透明度（0-1，越小越透明）
    """
    im = ax.imshow(
        hillshade,
        cmap='gray',
        alpha=alpha,
        extent=get_extent(meta),
        aspect='equal',
        origin='upper',
    )
    return im


def render_contours(ax, elevation, meta, interval=200, color='#4a3728', linewidth=0.3, alpha=0.4):
    """渲染等高线图层

    参数:
        ax: matplotlib axes
        elevation: 高程数组
        meta: 元数据
        interval: 等高线间距（米）
        color: 等高线颜色
        linewidth: 线宽
        alpha: 透明度
    """
    # 用 nanmin/nanmax 检查是否有有效数据，避免布尔索引大临时数组
    if np.all(np.isnan(elevation)):
        return None

    vmin = int(np.floor(np.nanmin(elevation) / interval) * interval)
    vmax = int(np.ceil(np.nanmax(elevation) / interval) * interval)
    levels = np.arange(vmin, vmax + interval, interval)

    # 主等高线（细线）
    extent = get_extent(meta)
    cs = ax.contour(
        elevation,
        levels=levels,
        extent=extent,
        colors=color,
        linewidths=linewidth,
        alpha=alpha,
        origin='upper',
    )

    # 加粗等高线（每5条加粗一条）
    major_levels = np.arange(vmin, vmax + interval * 5, interval * 5)
    if len(major_levels) > 1:
        ax.contour(
            elevation,
            levels=major_levels,
            extent=extent,
            colors=color,
            linewidths=linewidth * 2.5,
            alpha=alpha * 1.2,
            origin='upper',
        )

    return cs


def get_extent(meta):
    """从元数据中获取图像的空间范围 [left, right, bottom, top]"""
    if meta.get('bounds'):
        b = meta['bounds']
        return [b.left, b.right, b.bottom, b.top]
    else:
        # 从 transform 计算
        transform = meta.get('transform')
        if transform is not None:
            height, width = meta.get('shape', (0, 0))
            if height > 0 and width > 0:
                left = transform.c
                top = transform.f
                right = left + width * transform.a
                bottom = top + height * transform.e
                return [left, right, bottom, top]
        return None


def add_map_elements(ax, elevation, meta, title=None):
    """添加地图元素：标题、色阶条、坐标轴标签、比例尺

    参数:
        ax: matplotlib axes
        elevation: 高程数组
        meta: 元数据
        title: 图幅标题
    """
    import matplotlib.pyplot as plt
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    extent = get_extent(meta)
    is_geographic = extent is not None and extent[1] - extent[0] <= 180

    # 标题
    if title:
        ax.set_title(title, fontsize=16, fontweight='bold', pad=15)

    # 坐标轴标签
    if is_geographic:
        ax.set_xlabel('经度 (°E)', fontsize=11)
        ax.set_ylabel('纬度 (°N)', fontsize=11)

        # 格式化刻度标签
        from matplotlib.ticker import FormatStrFormatter
        ax.xaxis.set_major_formatter(FormatStrFormatter('%.1f'))
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.1f'))

        # 添加经纬网
        ax.grid(True, linestyle='--', alpha=0.3, color='gray')
    else:
        ax.set_xlabel('X', fontsize=11)
        ax.set_ylabel('Y', fontsize=11)

    # 数据来源标注
    ax.text(
        0.01, 0.01,
        '数据来源: 地理空间数据云 (www.gscloud.cn)',
        transform=ax.transAxes,
        fontsize=7,
        color='gray',
        ha='left',
        va='bottom',
        style='italic',
    )


def add_colorbar(fig, im, ax, label='海拔 (m)'):
    """添加色阶条

    参数:
        fig: matplotlib figure
        im: 图像对象（用于生成colorbar）
        ax: 主图axes
        label: 色阶条标签
    """
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right", size="3%", pad=0.1)
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label(label, fontsize=10)
    return cbar


def write_geotiff(elevation, meta, output_path, hillshade=None, write_hillshade=False):
    """将高程数据写出为 GeoTIFF，保留地理参考信息

    产出的 GeoTIFF 可直接在 QGIS/ArcGIS 中叠加使用。

    参数:
        elevation: 高程数组（含 NaN 表示无效值）
        meta: 元数据（含 transform, crs）
        output_path: 输出 .tif 路径
        hillshade: 可选，阴影数组 (0-255 uint8)
        write_hillshade: 是否同时写出阴影 GeoTIFF
    """
    try:
        import rasterio
    except ImportError:
        print("错误: 缺少 rasterio 包。请运行: pip install rasterio")
        return

    transform = meta.get('transform')
    crs = meta.get('crs')
    if crs is None:
        crs = 'EPSG:4326'  # SRTM 默认经纬度坐标

    # 高程 GeoTIFF：int16，nodata=-32768，LZW 压缩
    elev_int = np.where(np.isnan(elevation), -32768, elevation).astype(np.int16)
    profile = {
        'driver': 'GTiff',
        'height': elev_int.shape[0],
        'width': elev_int.shape[1],
        'count': 1,
        'dtype': 'int16',
        'crs': crs,
        'transform': transform,
        'nodata': -32768,
        'compress': 'lzw',
        'tiled': True,
    }
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(elev_int, 1)

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"GeoTIFF 已写出: {output_path} ({file_size:.1f} MB)")

    # 阴影 GeoTIFF：uint8
    if write_hillshade and hillshade is not None:
        hs_path = os.path.splitext(output_path)[0] + '_hillshade.tif'
        hs_profile = {
            'driver': 'GTiff',
            'height': hillshade.shape[0],
            'width': hillshade.shape[1],
            'count': 1,
            'dtype': 'uint8',
            'crs': crs,
            'transform': transform,
            'nodata': None,
            'compress': 'lzw',
            'tiled': True,
        }
        with rasterio.open(hs_path, 'w', **hs_profile) as dst:
            dst.write(hillshade, 1)
        hs_size = os.path.getsize(hs_path) / (1024 * 1024)
        print(f"阴影 GeoTIFF 已写出: {hs_path} ({hs_size:.1f} MB)")


def _elevation_to_rgb(elevation, vmin, vmax):
    """高程数组 -> RGB uint8 数组，全程 uint8 LUT 查找，不经过 float64 RGBA

    内存峰值: H*W*3 (uint8 output) + H*W*1 (valid mask) + H*W*1 (indices)
    对 26000x16000 约 1.7GB，远低于 matplotlib 的 3.78GB float64 RGBA
    """
    from matplotlib.colors import LinearSegmentedColormap

    colors_hex = [
        (0.00, '#2b5d8c'), (0.02, '#4a8ab5'), (0.05, '#7fb5d5'),
        (0.08, '#b3d9a0'), (0.15, '#8cc579'), (0.25, '#6ba356'),
        (0.35, '#c9b458'), (0.45, '#c9a048'), (0.55, '#a67c3d'),
        (0.65, '#8b5e2f'), (0.75, '#9e7a6a'), (0.85, '#c8b8a8'),
        (0.95, '#e8ddd0'), (1.00, '#ffffff'),
    ]
    cmap = LinearSegmentedColormap.from_list(
        'terrain_custom', [(pos, c) for pos, c in colors_hex], N=256)
    lut = (cmap(np.arange(256))[:, :3] * 255).astype(np.uint8)  # 256x3

    # 就地计算颜色索引，避免布尔索引大临时数组
    # 先创建 float 归一化数组，NaN 保留，再 clip 转 uint8
    with np.errstate(invalid='ignore'):
        normalized = (elevation - vmin) / (vmax - vmin) * 255.0
    normalized = np.clip(normalized, 0, 255)
    # 用 NaN 标记无效像素 -> 0 索引（后续覆盖为灰色）
    is_nan = np.isnan(normalized)
    indices = np.nan_to_num(normalized, nan=0).astype(np.uint8)
    del normalized

    rgb = lut[indices]  # HxWx3 uint8
    rgb[is_nan] = [240, 240, 240]  # NaN -> 浅灰
    del indices, is_nan
    return rgb


def _blend_hillshade(rgb, hillshade, alpha=0.5):
    """在 uint8 空间混合 RGB 和 hillshade

    result = rgb * (1 - alpha + alpha * hs/255)
    逐通道处理，峰值仅一个 H*W float32 临时数组
    """
    blend = 1.0 - alpha * (1.0 - hillshade.astype(np.float32) / 255.0)
    for c in range(3):
        ch = rgb[:, :, c].astype(np.float32) * blend
        rgb[:, :, c] = np.clip(ch, 0, 255).astype(np.uint8)
        del ch
    del blend
    return rgb


def render_terrain_pil(elevation, meta=None, mode='all', output=None,
                       azimuth=315, altitude=45, z_factor=1,
                       contour_interval=200, title=None,
                       vmin=None, vmax=None, hillshade_alpha=0.5,
                       contour_alpha=0.4, geotiff=False, dpi=200):
    """PIL 直写 PNG 渲染管线 — 绕过 matplotlib float64 RGBA OOM

    核心渲染（颜色映射 + 阴影混合）全程 uint8。
    装饰元素（标题/坐标轴/色阶条）叠加到降采样预览图上。
    产出两个文件：
      - {output}        高分辨率 PNG（全像素，无标注）
      - {output}_labeled.png  带标题/坐标轴/色阶条的预览图（降采样到 ~3000px）
    """
    from PIL import Image

    h, w = elevation.shape
    print(f"PIL 渲染模式: {w} x {h} 像素")

    # 用 nanmin/nanmax 计算 vmin/vmax，避免布尔索引创建大临时数组
    if vmin is None:
        vmin = float(np.nanmin(elevation))
    if vmax is None:
        vmax = float(np.nanmax(elevation))
    print(f"数据范围: {vmin:.0f}m - {vmax:.0f}m")
    if meta:
        meta['shape'] = (h, w)

    # 步骤 1: 高程 -> RGB
    print("步骤 1/3: 高程颜色映射 (uint8 LUT)...")
    rgb = _elevation_to_rgb(elevation, vmin, vmax)

    # 步骤 2: Hillshade
    hillshade = None
    if mode in ('hillshade', 'contour', 'elevation+hillshade', 'elevation+contour', 'all'):
        print("步骤 2/3: 计算山体阴影...")
        hillshade = compute_hillshade(elevation, azimuth=azimuth,
                                       altitude=altitude, z_factor=z_factor)
        if mode in ('elevation+hillshade', 'all', 'contour'):
            print("  混合阴影...")
            rgb = _blend_hillshade(rgb, hillshade, alpha=hillshade_alpha)
        elif mode == 'hillshade':
            rgb = np.stack([hillshade, hillshade, hillshade], axis=-1)
    else:
        print("步骤 2/3: 跳过 (无阴影)")

    # 步骤 3: 保存 PNG
    print("步骤 3/3: 保存 PNG...")
    if output is None:
        output = f"terrain_{mode}.png"

    img = Image.fromarray(rgb, mode='RGB')
    img.save(output, 'PNG')
    del rgb

    file_size = os.path.getsize(output) / (1024 * 1024)
    print(f"高分辨率 PNG: {output} ({file_size:.1f} MB)")

    # GeoTIFF
    if geotiff:
        if hillshade is None:
            hillshade = compute_hillshade(elevation, azimuth=azimuth,
                                           altitude=altitude, z_factor=z_factor)
        gt_path = os.path.splitext(output)[0] + '.tif'
        write_geotiff(elevation, meta, gt_path, hillshade=hillshade, write_hillshade=True)

    # 带标注的预览图（matplotlib，降采样到安全尺寸 ~3000px）
    preview_max = 3000
    scale = min(1.0, preview_max / w, preview_max / h)
    pv_w, pv_h = int(w * scale), int(h * scale)
    if scale < 1.0:
        preview_img = img.resize((pv_w, pv_h), Image.LANCZOS)
    else:
        preview_img = img

    preview_path = os.path.splitext(output)[0] + '_labeled.png'
    _render_labeled_preview(preview_img, elevation, meta, pv_w, pv_h,
                            title=title, vmin=vmin, vmax=vmax,
                            output=preview_path, dpi=dpi)
    del img, preview_img


def _render_labeled_preview(img, elevation, meta, w, h,
                            title=None, vmin=None, vmax=None, output=None, dpi=150):
    """在降采样预览图上叠加标题/坐标轴/色阶条（matplotlib，安全尺寸）"""
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from mpl_toolkits.axes_grid1 import make_axes_locatable

    _setup_chinese_font()

    fig_w = max(w / dpi, 8)
    fig_h = max(h / dpi, 6)
    max_fig = 30
    if fig_w > max_fig or fig_h > max_fig:
        s = min(max_fig / fig_w, max_fig / fig_h)
        fig_w *= s
        fig_h *= s

    fig, ax = plt.subplots(1, 1, figsize=(fig_w, fig_h))
    extent = get_extent(meta)

    ax.imshow(np.array(img), extent=extent, aspect='equal', origin='upper')

    if title:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=10)

    if extent:
        ax.set_xlabel('经度 (°E)', fontsize=10)
        ax.set_ylabel('纬度 (°N)', fontsize=10)
        from matplotlib.ticker import FormatStrFormatter
        ax.xaxis.set_major_formatter(FormatStrFormatter('%.0f'))
        ax.yaxis.set_major_formatter(FormatStrFormatter('%.0f'))
        ax.grid(True, linestyle='--', alpha=0.3, color='gray')

    ax.text(0.01, 0.01, '数据来源: 地理空间数据云 (www.gscloud.cn)',
            transform=ax.transAxes, fontsize=7, color='gray',
            ha='left', va='bottom', style='italic')

    # 色阶条（用独立的 ScalarMappable，不依赖 imshow 对象）
    if vmin is not None and vmax is not None:
        from matplotlib.cm import ScalarMappable
        cmap = create_terrain_colormap()
        norm = Normalize(vmin=vmin, vmax=vmax)
        sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="2%", pad=0.1)
        cbar = fig.colorbar(sm, cax=cax)
        cbar.set_label('海拔 (m)', fontsize=10)

    plt.tight_layout()
    fig.savefig(output, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    file_size = os.path.getsize(output) / (1024 * 1024)
    print(f"标注预览图: {output} ({file_size:.1f} MB)")


def render_terrain(filepath_or_elevation, meta=None, mode='all',
                   output=None, dpi=200, azimuth=315, altitude=45,
                   z_factor=1, contour_interval=200, title=None,
                   vmin=None, vmax=None, hillshade_alpha=0.5,
                   contour_alpha=0.4, figsize=None, geotiff=False):
    """主渲染函数

    参数:
        filepath_or_elevation: DEM文件路径，或已加载的高程数组
        meta: 元数据（如果filepath_or_elevation是数组则必须提供）
        mode: 渲染模式
            - 'elevation': 仅高程色阶
            - 'hillshade': 仅山体阴影
            - 'contour': 仅等高线
            - 'elevation+hillshade': 高程+阴影叠加
            - 'elevation+contour': 高程+等高线
            - 'all': 高程+阴影+等高线
        output: 输出文件路径
        dpi: 输出分辨率
        azimuth: 光源方位角
        altitude: 光源高度角
        z_factor: 高程放大因子
        contour_interval: 等高线间距
        title: 图幅标题
        vmin/vmax: 高程范围
        hillshade_alpha: 阴影透明度
        contour_alpha: 等高线透明度
    """
    import matplotlib
    matplotlib.use('Agg')  # 非交互式后端，避免弹窗
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties

    # 中文字体配置
    _setup_chinese_font()
    if isinstance(filepath_or_elevation, str):
        elevation, meta = load_dem(filepath_or_elevation)
        if title is None:
            title = Path(filepath_or_elevation).stem
    elif isinstance(filepath_or_elevation, np.ndarray):
        elevation = filepath_or_elevation
        if title is None:
            title = "地形图"
    else:
        raise ValueError("filepath_or_elevation 必须是文件路径(str)或numpy数组")

    # 设置 meta 的 shape
    meta['shape'] = elevation.shape

    # 大数组检测：超过 4000 像素边长时切换到 PIL 直写，避免 matplotlib RGBA OOM
    h, w = elevation.shape
    if max(h, w) > 4000:
        print(f"大数组 ({w}x{h})，切换到 PIL 直写模式避免 OOM...")
        render_terrain_pil(
            elevation, meta=meta, mode=mode, output=output,
            azimuth=azimuth, altitude=altitude, z_factor=z_factor,
            contour_interval=contour_interval, title=title,
            vmin=vmin, vmax=vmax, hillshade_alpha=hillshade_alpha,
            contour_alpha=contour_alpha, geotiff=geotiff, dpi=dpi)
        return

    # 计算有效的 vmin/vmax（用 nanmin/nanmax 避免布尔索引大临时数组）
    if np.all(np.isnan(elevation)):
        print("错误: 该区域没有有效的高程数据")
        return
    if vmin is None:
        vmin = max(0, np.floor(np.nanmin(elevation) / 100) * 100)
    if vmax is None:
        vmax = np.ceil(np.nanmax(elevation) / 100) * 100

    # 打印数据信息
    print(f"数据范围: {vmin:.0f}m - {vmax:.0f}m")
    print(f"均值高程: {np.nanmean(elevation):.1f}m")
    print(f"数据尺寸: {elevation.shape[1]} x {elevation.shape[0]} 像素")
    extent = get_extent(meta)
    if extent:
        print(f"地理范围: {extent[0]:.2f}°E - {extent[1]:.2f}°E, {extent[2]:.2f}°N - {extent[3]:.2f}°N")

    # 确定图像大小 — 尽量让输出像素匹配数组尺寸，避免 imshow 下采样损失
    if figsize is None:
        h, w = elevation.shape
        max_output_dim = 14000  # PNG 单边最大像素（平衡质量与文件大小）
        scale = min(1.0, max_output_dim / w, max_output_dim / h)
        output_w = int(w * scale)
        output_h = int(h * scale)
        # figsize = 输出像素 / dpi，限制物理尺寸不超过 45 英寸
        fig_w = output_w / dpi
        fig_h = output_h / dpi
        max_fig = 45
        if fig_w > max_fig or fig_h > max_fig:
            s = min(max_fig / fig_w, max_fig / fig_h)
            fig_w *= s
            fig_h *= s
        figsize = (max(fig_w, 8), max(fig_h, 6))
        print(f"图像尺寸: {figsize[0]:.1f}×{figsize[1]:.1f} 英寸 @ {dpi} dpi = {int(figsize[0]*dpi)}×{int(figsize[1]*dpi)} 像素 (输入数组 {w}×{h})")

    # 创建图像
    fig, ax = plt.subplots(1, 1, figsize=figsize)

    # 根据模式渲染
    hillshade = None
    if mode == 'elevation':
        im = render_elevation(ax, elevation, meta, vmin=vmin, vmax=vmax)
        add_colorbar(fig, im, ax)
    elif mode == 'hillshade':
        hillshade = compute_hillshade(elevation, azimuth=azimuth,
                                       altitude=altitude, z_factor=z_factor)
        im = render_hillshade(ax, hillshade, meta, alpha=1.0)
    elif mode == 'contour':
        # 等高线底图为阴影
        hillshade = compute_hillshade(elevation, azimuth=azimuth,
                                       altitude=altitude, z_factor=z_factor)
        render_hillshade(ax, hillshade, meta, alpha=1.0)
        render_contours(ax, elevation, meta, interval=contour_interval, alpha=contour_alpha)
    elif mode == 'elevation+hillshade':
        im = render_elevation(ax, elevation, meta, vmin=vmin, vmax=vmax)
        hillshade = compute_hillshade(elevation, azimuth=azimuth,
                                       altitude=altitude, z_factor=z_factor)
        render_hillshade(ax, hillshade, meta, alpha=hillshade_alpha)
        add_colorbar(fig, im, ax)
    elif mode == 'elevation+contour':
        im = render_elevation(ax, elevation, meta, vmin=vmin, vmax=vmax)
        render_contours(ax, elevation, meta, interval=contour_interval, alpha=contour_alpha)
        add_colorbar(fig, im, ax)
    elif mode == 'all':
        im = render_elevation(ax, elevation, meta, vmin=vmin, vmax=vmax, alpha=0.85)
        hillshade = compute_hillshade(elevation, azimuth=azimuth,
                                       altitude=altitude, z_factor=z_factor)
        render_hillshade(ax, hillshade, meta, alpha=hillshade_alpha)
        render_contours(ax, elevation, meta, interval=contour_interval, alpha=contour_alpha)
        add_colorbar(fig, im, ax)
    else:
        print(f"错误: 未知渲染模式 '{mode}'")
        print("可用模式: elevation, hillshade, contour, elevation+hillshade, elevation+contour, all")
        return

    # 添加地图元素
    add_map_elements(ax, elevation, meta, title=title)

    # 输出文件名
    if output is None:
        if isinstance(filepath_or_elevation, str):
            base_name = Path(filepath_or_elevation).stem
            output = f"{base_name}_{mode}.png"
        else:
            output = f"terrain_{mode}.png"

    # 保存图像
    plt.tight_layout()
    fig.savefig(output, dpi=dpi, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    file_size = os.path.getsize(output) / (1024 * 1024)
    print(f"渲染完成: {output} ({file_size:.1f} MB)")

    # GeoTIFF 输出（含地理参考，可在 QGIS/ArcGIS 叠加）
    if geotiff:
        if hillshade is None:
            hillshade = compute_hillshade(elevation, azimuth=azimuth,
                                           altitude=altitude, z_factor=z_factor)
        gt_path = os.path.splitext(output)[0] + '.tif'
        write_geotiff(elevation, meta, gt_path, hillshade=hillshade, write_hillshade=True)


def batch_render(directory, mode='all', output_dir=None, geotiff=False, **kwargs):
    """批量渲染目录中的所有 .img 文件

    参数:
        directory: 包含 .img 文件的目录
        mode: 渲染模式
        output_dir: 输出目录（默认在输入目录下创建 rendered 子目录）
        geotiff: 是否同时输出 GeoTIFF
        kwargs: 传递给 render_terrain 的额外参数
    """
    img_files = sorted(glob.glob(os.path.join(directory, "*.img")))
    if not img_files:
        print(f"错误: 在 {directory} 中未找到 .img 文件")
        return

    if output_dir is None:
        output_dir = os.path.join(directory, "rendered")
    os.makedirs(output_dir, exist_ok=True)

    print(f"找到 {len(img_files)} 个文件，开始批量渲染...")
    print(f"渲染模式: {mode}")
    print(f"输出目录: {output_dir}")
    if geotiff:
        print(f"GeoTIFF 输出: 开启")
    print("-" * 50)

    success = 0
    fail = 0
    for i, filepath in enumerate(img_files):
        filename = Path(filepath).stem
        output = os.path.join(output_dir, f"{filename}_{mode}.png")
        try:
            print(f"\n[{i+1}/{len(img_files)}] 渲染: {filename}")
            render_terrain(filepath, mode=mode, output=output, geotiff=geotiff, **kwargs)
            success += 1
        except Exception as e:
            print(f"  失败: {e}")
            fail += 1

    print("\n" + "=" * 50)
    print(f"批量渲染完成!")
    print(f"成功: {success}, 失败: {fail}")


def main():
    parser = argparse.ArgumentParser(
        description='SRTM 地形图渲染程序',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 渲染单个文件（全部模式叠加）
  python terrain_renderer.py srtm_60_05.img

  # 仅高程色阶
  python terrain_renderer.py srtm_60_05.img --mode elevation

  # 高程+山体阴影叠加
  python terrain_renderer.py srtm_60_05.img --mode elevation+hillshade

  # 拼合多个瓦片渲染大区域
  python terrain_renderer.py --mosaic ./srtm_china_data/ --bounds 100 110 30 40

  # 批量渲染目录中所有文件
  python terrain_renderer.py --batch ./srtm_china_data/
        """
    )

    # 输入源（互斥）
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('file', nargs='?', help='单个 .img 文件路径')
    input_group.add_argument('--mosaic', metavar='DIR', help='拼合目录中的多个瓦片渲染大区域')
    input_group.add_argument('--batch', metavar='DIR', help='批量渲染目录中的所有文件')

    # 渲染选项
    parser.add_argument('--mode', default='all',
                       choices=['elevation', 'hillshade', 'contour',
                               'elevation+hillshade', 'elevation+contour', 'all'],
                       help='渲染模式 (默认: all)')
    parser.add_argument('--output', '-o', help='输出文件路径')
    parser.add_argument('--output-dir', help='批量渲染时的输出目录')
    parser.add_argument('--dpi', type=int, default=200, help='输出分辨率 (默认: 200)')
    parser.add_argument('--title', help='图幅标题')

    # 山体阴影参数
    parser.add_argument('--azimuth', type=float, default=315,
                       help='光源方位角 (默认: 315，即西北)')
    parser.add_argument('--altitude', type=float, default=45,
                       help='光源高度角 (默认: 45)')
    parser.add_argument('--z-factor', type=float, default=1,
                       help='高程放大因子 (默认: 1)')

    # 等高线参数
    parser.add_argument('--contour-interval', type=float, default=200,
                       help='等高线间距/米 (默认: 200)')
    parser.add_argument('--contour-alpha', type=float, default=0.4,
                       help='等高线透明度 (默认: 0.4)')

    # 阴影参数
    parser.add_argument('--hillshade-alpha', type=float, default=0.5,
                       help='山体阴影透明度 (默认: 0.5)')

    # 高程范围
    parser.add_argument('--vmin', type=float, help='最小高程值 (默认: 自动)')
    parser.add_argument('--vmax', type=float, help='最大高程值 (默认: 自动)')

    # 拼合模式裁剪范围
    parser.add_argument('--bounds', nargs=4, type=float, metavar=('MIN_LON', 'MAX_LON', 'MIN_LAT', 'MAX_LAT'),
                       help='拼合渲染时的裁剪范围 (经度最小 最大 纬度最小 最大)')

    # 下采样（用于拼合巨型区域时降低内存和加速）
    parser.add_argument('--downsample', type=int, default=1,
                       help='下采样因子 (1=原图, 2=取一半像素, 5=取1/5像素等) (默认:1)')

    # 图像大小
    parser.add_argument('--figsize', nargs=2, type=float, metavar=('W', 'H'),
                       help='图像大小 (英寸)')

    # GeoTIFF 输出
    parser.add_argument('--geotiff', action='store_true',
                       help='同时输出 GeoTIFF (含地理参考，可在 QGIS/ArcGIS 叠加使用)')

    args = parser.parse_args()

    # 执行渲染
    if args.file:
        render_terrain(
            args.file,
            mode=args.mode,
            output=args.output,
            dpi=args.dpi,
            azimuth=args.azimuth,
            altitude=args.altitude,
            z_factor=args.z_factor,
            contour_interval=args.contour_interval,
            title=args.title,
            vmin=args.vmin,
            vmax=args.vmax,
            hillshade_alpha=args.hillshade_alpha,
            contour_alpha=args.contour_alpha,
            figsize=args.figsize,
            geotiff=args.geotiff,
        )
    elif args.mosaic:
        elevation, meta = mosaic_dems(args.mosaic, bounds=args.bounds, downsample=args.downsample)
        title = args.title or "拼合地形图"
        render_terrain(
            elevation,
            meta=meta,
            mode=args.mode,
            output=args.output or "mosaic_terrain.png",
            dpi=args.dpi,
            azimuth=args.azimuth,
            altitude=args.altitude,
            z_factor=args.z_factor,
            contour_interval=args.contour_interval,
            title=title,
            vmin=args.vmin,
            vmax=args.vmax,
            hillshade_alpha=args.hillshade_alpha,
            contour_alpha=args.contour_alpha,
            figsize=args.figsize,
            geotiff=args.geotiff,
        )
    elif args.batch:
        batch_render(
            args.batch,
            mode=args.mode,
            output_dir=args.output_dir,
            dpi=args.dpi,
            azimuth=args.azimuth,
            altitude=args.altitude,
            z_factor=args.z_factor,
            contour_interval=args.contour_interval,
            vmin=args.vmin,
            vmax=args.vmax,
            hillshade_alpha=args.hillshade_alpha,
            contour_alpha=args.contour_alpha,
            geotiff=args.geotiff,
        )


if __name__ == "__main__":
    main()
