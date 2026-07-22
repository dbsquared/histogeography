#!/usr/bin/env python3
"""
SRTM DEM数据下载脚本 - 中国及周边地区
根据用户提供的下载链接模式生成所有所需瓦片的下载链接

使用说明：
1. 首先登录 https://www.gscloud.cn/
2. 触发一次小文件下载（例如点击任何.srtm_XX_XX.img的下载按钮）
3. 在浏览器开发者工具(F12) -> Network标签页中找到该下载请求
4. 复制完整的URL，提取出sid参数的值和您的uid
5. 将这些值填入脚本中的相应变量，或通过命令行参数提供
6. 运行脚本：python download_srtm_china.py

数据范围：中国及周边地区 (经度73°-135°E，纬度18°-54°N)
对应文件：srtm_[52-64]_[02-09].img  (共104个文件)
"""

import os
import sys
import time
import argparse
from pathlib import Path

try:
    import requests
    from tqdm import tqdm
except ImportError:
    print("错误: 缺少必要的依赖包。请先安装:")
    print("pip install requests tqdm")
    sys.exit(1)

def generate_filenames():
    """生成中国及周边地区所需的所有SRTM文件名"""
    filenames = []
    # 条带号范围: 52-64 (对应经度73°-135°E)
    # 行编号范围: 02-09 (对应纬度18°-54°N)
    for band in range(52, 65):  # 52 to 64 inclusive
        for row in range(2, 10):  # 2 to 9 inclusive
            filename = f"srtm_{band:02d}_{row:02d}"
            filenames.append(filename)
    return filenames

def download_file(url, filepath, chunk_size=8192, max_retries=3):
    """下载单个文件，带重试机制和进度显示"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()  # 如果状态码不是200，将引发HTTPError
            
            # 获取文件大小（如果可用）
            total_size = int(response.headers.get('content-length', 0))
            
            # 以流的方式写入文件
            with open(filepath, 'wb') as f, tqdm(
                desc=filepath.name,
                total=total_size,
                unit='iB',
                unit_scale=True,
                unit_divisor=1024,
            ) as pbar:
                for data in response.iter_content(chunk_size=chunk_size):
                    size = f.write(data)
                    pbar.update(size)
            
            # 验证下载是否完成
            if total_size != 0 and os.path.getsize(filepath) != total_size:
                raise RuntimeError("下载不完整：文件大小不匹配")
            
            return True  # 下载成功
            
        except requests.exceptions.RequestException as e:
            print(f"\n警告: 下载失败 (尝试 {attempt+1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"\n错误: 文件 {filepath.name} 下载失败，已达到最大重试次数")
                return False
        except Exception as e:
            print(f"\n错误: 处理文件 {filepath.name} 时发生未知错误: {e}")
            return False
    
    return False

def main():
    parser = argparse.ArgumentParser(description='下载SRTM DEM数据 - 中国及周边地区')
    parser.add_argument('--sid', required=True, help='会话ID (从下载请求中获取)')
    parser.add_argument('--uid', required=True, help='用户ID')
    parser.add_argument('--output-dir', default='srtm_china_data', help='输出目录 (默认: srtm_china_data)')
    parser.add_argument('--start-from', help='从特定文件名开始下载 (用于续传)')
    parser.add_argument('--file', help='仅下载指定文件 (如 srtm_55_03)，与 --start-from 互斥')
    parser.add_argument('--skip-existing', action='store_true', help='跳过已存在的文件')
    
    args = parser.parse_args()

    if args.file and args.start_from:
        print("错误: --file 和 --start-from 不能同时使用")
        sys.exit(1)

    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    print(f"文件将保存到: {output_dir.absolute()}")

    # 确定要下载的文件列表
    if args.file:
        all_filenames = [args.file]
        print(f"准备下载 1 个文件: {args.file}")
    else:
        all_filenames = generate_filenames()
        print(f"准备下载 {len(all_filenames)} 个文件")

        # 如果指定了起始点，则从该点开始
        if args.start_from:
            try:
                start_index = all_filenames.index(args.start_from)
                all_filenames = all_filenames[start_index:]
                print(f"从文件 {args.start_from} 开始下载 (剩余 {len(all_filenames)} 个文件)")
            except ValueError:
                print(f"错误: 未找到起始文件 {args.start_from}")
                sys.exit(1)
    
    # 基础下载URL模式
    base_url = "https://bjdl.gscloud.cn/sources/download/305/{filename}?"
    url_template = base_url + "sid={sid}&uid={uid}"
    
    # 统计信息
    success_count = 0
    fail_count = 0
    skip_count = 0
    
    # 遍历所有文件
    for filename in all_filenames:
        filepath = output_dir / f"{filename}.img"
        
        # 检查是否跳过已存在的文件
        if args.skip_existing and filepath.exists():
            file_size = filepath.stat().st_size
            if file_size > 0:
                print(f"跳过: {filename}.img (已存在，大小: {file_size/1024/1024:.1f} MB)")
                skip_count += 1
                continue
        
        # 构建下载URL
        url = url_template.format(filename=filename, sid=args.sid, uid=args.uid)
        
        # 尝试下载
        print(f"\n正在下载: {filename}.img")
        if download_file(url, filepath):
            success_count += 1
            # 显示下载后的文件大小
            file_size = filepath.stat().st_size
            print(f"完成: {filename}.img ({file_size/1024/1024:.1f} MB)")
        else:
            fail_count += 1
            # 删除可能不完整的文件
            if filepath.exists():
                filepath.unlink()
    
    # 输出最终统计
    print("\n" + "="*50)
    print("下载任务完成!")
    print(f"成功: {success_count} 个文件")
    print(f"失败: {fail_count} 个文件")
    print(f"跳过: {skip_count} 个文件")
    print(f"总计: {len(all_filenames)} 个文件")
    print(f"数据保存位置: {output_dir.absolute()}")
    
    if fail_count > 0:
        print(f"\n注意: 有 {fail_count} 个文件下载失败。您可以:")
        print("1. 检查网络连接")
        print("2. 确认您的sid和uid是否仍然有效")
        print("3. 重新运行脚本（失败的文件将被重新下载）")
        print("4. 使用 --skip-existing 跳过已成功下载的文件以节省时间")

if __name__ == "__main__":
    main()