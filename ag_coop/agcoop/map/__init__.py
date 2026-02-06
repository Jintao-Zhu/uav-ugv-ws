"""
地图模块：统一的栅格地图表示和 I/O

主要组件：
- GridMap: 核心地图数据结构
- load_movingai_map: 加载 MovingAI .map 格式
- load_text_grid: 加载简单文本格式
- load_ros_map: 加载 ROS map_server 格式
- auto_load_map: 自动检测格式并加载
- mapping: 权威坐标映射函数
- neighbors: 邻接图和最短路径工具
"""

from .grid_map import GridMap
from .io_text import (
    load_movingai_map,
    load_text_grid,
    save_text_grid,
    auto_load_map
)
from .io_ros import (
    load_ros_map,
    save_ros_map,
    load_pgm
)
from . import mapping
from . import neighbors

__all__ = [
    'GridMap',
    'load_movingai_map',
    'load_text_grid',
    'save_text_grid',
    'load_ros_map',
    'save_ros_map',
    'load_pgm',
    'auto_load_map',
    'mapping',
    'neighbors',
]
