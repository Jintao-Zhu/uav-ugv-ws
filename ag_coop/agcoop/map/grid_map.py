"""
GridMap 数据结构：统一的栅格地图表示

支持：
- 纯文本网格地图（.map, .txt）
- ROS 栅格地图（.yaml + .pgm）
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
from . import mapping


@dataclass
class GridMap:
    """
    栅格地图数据结构
    
    Attributes:
        width: 地图宽度（格数）
        height: 地图高度（格数）
        grid: 栅格数据，shape (H, W)，0=free, 1=obstacle
        resolution: 分辨率（米/格），默认 0.2
        origin: world 坐标系下 cell(0,0) 的左下角位置 (x, y)
        frame: 坐标系名称（默认 "map"）
        free_cells: 预计算的自由格子列表 [(i, j), ...]
    """
    width: int
    height: int
    grid: np.ndarray
    resolution: float = 0.2
    origin: Tuple[float, float] = (0.0, 0.0)
    frame: str = "map"
    free_cells: List[Tuple[int, int]] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        """初始化后处理：验证数据并预计算 free_cells"""
        # 验证 grid 形状
        if self.grid.shape != (self.height, self.width):
            raise ValueError(
                f"Grid shape {self.grid.shape} does not match (height={self.height}, width={self.width})"
            )
        
        # 预计算自由格子
        self._compute_free_cells()
    
    def _compute_free_cells(self) -> None:
        """预计算所有自由格子的坐标"""
        self.free_cells = []
        for i in range(self.height):
            for j in range(self.width):
                if self.grid[i, j] == 0:
                    self.free_cells.append((i, j))
    
    def is_free(self, i: int, j: int) -> bool:
        """
        检查格子 (i, j) 是否为自由格子
        
        Args:
            i: 行索引
            j: 列索引
            
        Returns:
            True 如果格子在边界内且为自由格子
        """
        if not self.in_bounds(i, j):
            return False
        return self.grid[i, j] == 0
    
    def in_bounds(self, i: int, j: int) -> bool:
        """
        检查格子 (i, j) 是否在地图边界内

        Args:
            i: 行索引
            j: 列索引

        Returns:
            True 如果在边界内
        """
        return mapping.in_bounds(i, j, self.height, self.width)

    def cell_to_world(self, i: int, j: int) -> Tuple[float, float]:
        """
        将格子坐标转换为世界坐标（格子中心）

        使用权威映射函数 mapping.cell_to_world

        Args:
            i: 行索引
            j: 列索引

        Returns:
            (x, y) 世界坐标
        """
        return mapping.cell_to_world(i, j, self.origin, self.resolution)

    def world_to_cell(self, x: float, y: float) -> Tuple[int, int]:
        """
        将世界坐标转换为格子坐标

        使用权威映射函数 mapping.world_to_cell

        Args:
            x: 世界坐标 x
            y: 世界坐标 y

        Returns:
            (i, j) 格子坐标
        """
        return mapping.world_to_cell(x, y, self.origin, self.resolution)
    
    def get_neighbors(self, i: int, j: int, connectivity: int = 4) -> List[Tuple[int, int]]:
        """
        获取格子 (i, j) 的邻居
        
        Args:
            i: 行索引
            j: 列索引
            connectivity: 连通性（4 或 8）
            
        Returns:
            邻居格子列表 [(i, j), ...]
        """
        neighbors = []
        
        # 4-连通
        deltas_4 = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        
        # 8-连通
        deltas_8 = deltas_4 + [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        
        deltas = deltas_8 if connectivity == 8 else deltas_4
        
        for di, dj in deltas:
            ni, nj = i + di, j + dj
            if self.is_free(ni, nj):
                neighbors.append((ni, nj))
        
        return neighbors
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"GridMap(width={self.width}, height={self.height}, "
            f"resolution={self.resolution}, free_cells={len(self.free_cells)})"
        )
    
    def visualize(self, max_size: int = 50) -> str:
        """
        可视化地图（用于调试）
        
        Args:
            max_size: 最大显示尺寸
            
        Returns:
            地图的字符串表示
        """
        if self.height > max_size or self.width > max_size:
            return f"Map too large to visualize ({self.height}x{self.width})"
        
        lines = []
        for i in range(self.height):
            row = ""
            for j in range(self.width):
                row += "." if self.grid[i, j] == 0 else "#"
            lines.append(row)
        
        return "\n".join(lines)
