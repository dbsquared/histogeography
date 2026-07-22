"""
地理映射模块 — SRTM底图 像素↔经纬度 一一映射
底图: china_full_v3.tif / china_full_v3.png
尺寸: 15600 x 9600
经度: 75.0 ~ 140.0 E (跨度 65.0)
纬度: 55.0 ~ 15.0 N (跨度 -40.0, 向下递减)
投影: 等经纬度 (Plate Carree)
分辨率: 65/15600 ≈ 0.0041667 °/px ≈ 463 m/px
"""

import numpy as np
import rasterio

# ── 底图常量 ──
BASE_W, BASE_H = 15600, 9600
LON_MIN, LON_MAX = 75.0, 140.0   # 经度范围
LAT_MAX, LAT_MIN = 55.0, 15.0     # 纬度范围 (y=0是北边)
LON_SPAN = LON_MAX - LON_MIN      # 65.0
LAT_SPAN = LAT_MIN - LAT_MAX       # -40.0


def px_to_lonlat(px, py):
    """底图像素坐标 → WGS84经纬度"""
    lon = LON_MIN + (px / BASE_W) * LON_SPAN
    lat = LAT_MAX + (py / BASE_H) * LAT_SPAN
    return lon, lat


def lonlat_to_px(lon, lat):
    """WGS84经纬度 → 底图像素坐标 (浮点)"""
    px = ((lon - LON_MIN) / LON_SPAN) * BASE_W
    py = ((lat - LAT_MAX) / LAT_SPAN) * BASE_H
    return px, py


def elevation_at(lon, lat, tif_path='china_full_v3.tif'):
    """查询指定经纬度的海拔高度 (从GeoTIFF)"""
    px, py = lonlat_to_px(lon, lat)
    with rasterio.open(tif_path) as ds:
        # 读取周围 1x1 像素的窗口
        window = ((int(py), int(py)+1), (int(px), int(px)+1))
        data = ds.read(1, window=window)
        return float(data[0, 0]) if data.size > 0 else None


def elevation_grid(tif_path='china_full_v3.tif', downsample=10):
    """返回降采样后的海拔网格 (用于三维渲染等后续用途)"""
    with rasterio.open(tif_path) as ds:
        data = ds.read(1)[::downsample, ::downsample]
        h, w = data.shape
        lons = np.linspace(LON_MIN, LON_MAX, w)
        lats = np.linspace(LAT_MAX, LAT_MIN, h)
        return {'elevation': data, 'lons': lons, 'lats': lats,
                'shape': (h, w), 'downsample': downsample}


# ── 测试 ──
if __name__ == '__main__':
    # 四角验证
    for px, py in [(0, 0), (BASE_W, 0), (0, BASE_H), (BASE_W, BASE_H),
                   (BASE_W//2, BASE_H//2)]:
        lon, lat = px_to_lonlat(px, py)
        print(f'像素 ({px:>5d},{py:>5d}) → ({lon:.4f}, {lat:.4f})')
    
    # 反向验证
    for lon, lat in [(75, 55), (140, 55), (75, 15), (140, 15),
                     (112.45, 34.62)]:  # 洛阳
        px, py = lonlat_to_px(lon, lat)
        lon2, lat2 = px_to_lonlat(px, py)
        print(f'经纬度 ({lon},{lat}) → 像素 ({px:.1f},{py:.1f}) → 回算 ({lon2:.4f},{lat2:.4f})')
    
    # 海拔采样
    elev = elevation_at(108.94, 34.34)  # 西安附近
    print(f'\n西安附近海拔: {elev} m')
