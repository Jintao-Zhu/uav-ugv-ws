"""
文本格式地图的 I/O 工具

支持格式：
1. MovingAI .map 格式（标准 MAPF benchmark）
2. 简单文本格式（0/1 矩阵）
"""

import numpy as np
from pathlib import Path
from typing import Tuple, Optional
from .grid_map import GridMap


def load_movingai_map(file_path: str, resolution: float = 0.2) -> GridMap:
    """
    加载 MovingAI .map 格式地图
    
    格式示例：
    type octile
    height 10
    width 10
    map
    @@@@@@@@@@
    @........@
    @........@
    ...
    
    字符映射：
    - '.' = 自由格子 (0)
    - '@', 'O', 'T', 'W' = 障碍物 (1)
    
    Args:
        file_path: 地图文件路径
        resolution: 分辨率（米/格）
        
    Returns:
        GridMap 对象
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Map file not found: {file_path}")
    
    with open(file_path, 'r') as f:
        lines = f.readlines()
    
    # 解析头部
    height = None
    width = None
    map_start_idx = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        if line.startswith('height'):
            height = int(line.split()[1])
        elif line.startswith('width'):
            width = int(line.split()[1])
        elif line.startswith('map'):
            map_start_idx = i + 1
            break
    
    if height is None or width is None or map_start_idx is None:
        raise ValueError(f"Invalid MovingAI map format: {file_path}")
    
    # 解析地图数据
    grid = np.zeros((height, width), dtype=np.int8)
    
    for i in range(height):
        if map_start_idx + i >= len(lines):
            raise ValueError(f"Map data incomplete at line {map_start_idx + i}")
        
        line = lines[map_start_idx + i].strip()
        if len(line) < width:
            raise ValueError(f"Map row {i} too short: expected {width}, got {len(line)}")
        
        for j in range(width):
            char = line[j]
            # '.' = free, 其他 = obstacle
            grid[i, j] = 0 if char == '.' else 1
    
    return GridMap(
        width=width,
        height=height,
        grid=grid,
        resolution=resolution,
        origin=(0.0, 0.0),
        frame="map"
    )


def load_text_grid(file_path: str, resolution: float = 0.2) -> GridMap:
    """
    加载简单文本格式地图（0/1 矩阵）
    
    格式示例：
    0 0 0 1 0
    0 1 0 0 0
    0 0 0 1 0
    
    Args:
        file_path: 地图文件路径
        resolution: 分辨率（米/格）
        
    Returns:
        GridMap 对象
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Map file not found: {file_path}")
    
    # 使用 numpy 加载
    grid = np.loadtxt(file_path, dtype=np.int8)
    
    # 确保是 2D 数组
    if grid.ndim != 2:
        raise ValueError(f"Expected 2D grid, got shape {grid.shape}")
    
    height, width = grid.shape
    
    return GridMap(
        width=width,
        height=height,
        grid=grid,
        resolution=resolution,
        origin=(0.0, 0.0),
        frame="map"
    )


def save_text_grid(grid_map: GridMap, file_path: str) -> None:
    """
    保存地图为简单文本格式
    
    Args:
        grid_map: GridMap 对象
        file_path: 输出文件路径
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    np.savetxt(file_path, grid_map.grid, fmt='%d')


def auto_load_map(file_path: str, resolution: float = 0.2) -> GridMap:
    """
    自动检测格式并加载地图
    
    Args:
        file_path: 地图文件路径
        resolution: 分辨率（米/格）
        
    Returns:
        GridMap 对象
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Map file not found: {file_path}")
    
    # 根据扩展名判断
    if file_path.suffix == '.map':
        return load_movingai_map(str(file_path), resolution)
    elif file_path.suffix == '.yaml':
        # ROS 格式
        from .io_ros import load_ros_map
        return load_ros_map(str(file_path))
    elif file_path.suffix in ['.txt', '.grid']:
        return load_text_grid(str(file_path), resolution)
    else:
        # 尝试 MovingAI 格式
        try:
            return load_movingai_map(str(file_path), resolution)
        except:
            # 尝试文本格式
            return load_text_grid(str(file_path), resolution)
