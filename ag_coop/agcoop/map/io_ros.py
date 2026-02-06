"""
ROS 格式地图的 I/O 工具

支持 ROS map_server 格式：
- .yaml 配置文件（包含 resolution, origin, image 等）
- .pgm 图像文件（occupancy grid）
"""

import numpy as np
import yaml
from pathlib import Path
from typing import Tuple, Optional
from .grid_map import GridMap


def load_pgm(file_path: str) -> Tuple[np.ndarray, int]:
    """
    加载 PGM 图像文件
    
    支持 P5 (binary) 和 P2 (ASCII) 格式
    
    Args:
        file_path: PGM 文件路径
        
    Returns:
        (image, max_val) 元组
        - image: numpy 数组，shape (H, W)
        - max_val: 最大像素值
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"PGM file not found: {file_path}")
    
    with open(file_path, 'rb') as f:
        # 读取 magic number
        magic = f.readline().strip()
        
        if magic not in [b'P2', b'P5']:
            raise ValueError(f"Unsupported PGM format: {magic}")
        
        # 跳过注释行
        while True:
            line = f.readline()
            if not line.startswith(b'#'):
                break
        
        # 读取宽度和高度
        width, height = map(int, line.split())
        
        # 读取最大值
        max_val = int(f.readline().strip())
        
        # 读取图像数据
        if magic == b'P5':
            # Binary format
            data = np.frombuffer(f.read(), dtype=np.uint8)
        else:
            # ASCII format
            data = np.fromstring(f.read().decode(), dtype=np.uint8, sep=' ')
        
        # Reshape
        image = data.reshape((height, width))
        
    return image, max_val


def load_ros_map(yaml_path: str) -> GridMap:
    """
    加载 ROS map_server 格式地图
    
    Args:
        yaml_path: YAML 配置文件路径
        
    Returns:
        GridMap 对象
    """
    yaml_path = Path(yaml_path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {yaml_path}")
    
    # 读取 YAML 配置
    with open(yaml_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # 提取参数
    image_file = config['image']
    resolution = config['resolution']
    origin = config['origin']  # [x, y, theta]
    negate = config.get('negate', 0)
    occupied_thresh = config.get('occupied_thresh', 0.65)
    free_thresh = config.get('free_thresh', 0.196)
    
    # 构建图像文件路径（相对于 YAML 文件）
    if not Path(image_file).is_absolute():
        image_path = yaml_path.parent / image_file
    else:
        image_path = Path(image_file)
    
    # 加载图像
    image, max_val = load_pgm(str(image_path))
    height, width = image.shape
    
    # 归一化到 [0, 1]
    occupancy = image.astype(np.float32) / max_val

    # 如果 negate=1，反转颜色
    if negate:
        occupancy = 1.0 - occupancy

    # 转换为 0/1 grid
    # ROS 约定：occupancy 表示"被占用的概率"
    # 但 PGM 中：高值（白色，接近 1.0）= 自由，低值（黑色，接近 0.0）= 障碍
    # 所以需要反转：occupancy_prob = 1.0 - normalized_pixel_value
    # 但由于我们的 PGM 已经是这样的约定（255=free, 0=occupied），
    # 所以 occupancy 实际上是"自由度"，需要反转来得到"占用度"

    # 正确的逻辑：
    # occupancy < free_thresh (接近 0，黑色) -> 障碍物 (1)
    # occupancy > 1 - occupied_thresh (接近 1，白色) -> 自由 (0)
    grid = np.ones((height, width), dtype=np.int8)  # 默认为障碍物
    grid[occupancy > (1.0 - occupied_thresh)] = 0  # 高值 -> 自由
    
    # 提取 origin (只取 x, y)
    origin_xy = (origin[0], origin[1])
    
    return GridMap(
        width=width,
        height=height,
        grid=grid,
        resolution=resolution,
        origin=origin_xy,
        frame="map"
    )


def save_ros_map(grid_map: GridMap, yaml_path: str, image_name: str = "map.pgm") -> None:
    """
    保存地图为 ROS map_server 格式
    
    Args:
        grid_map: GridMap 对象
        yaml_path: 输出 YAML 文件路径
        image_name: PGM 图像文件名
    """
    yaml_path = Path(yaml_path)
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 构建 PGM 文件路径
    pgm_path = yaml_path.parent / image_name
    
    # 转换 grid 为图像（0 -> 255 free, 1 -> 0 occupied）
    image = np.where(grid_map.grid == 0, 255, 0).astype(np.uint8)
    
    # 保存 PGM
    with open(pgm_path, 'wb') as f:
        f.write(b'P5\n')
        f.write(f'{grid_map.width} {grid_map.height}\n'.encode())
        f.write(b'255\n')
        f.write(image.tobytes())
    
    # 保存 YAML
    config = {
        'image': image_name,
        'resolution': grid_map.resolution,
        'origin': [grid_map.origin[0], grid_map.origin[1], 0.0],
        'negate': 0,
        'occupied_thresh': 0.65,
        'free_thresh': 0.196
    }
    
    with open(yaml_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
