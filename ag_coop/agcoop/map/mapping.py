"""
世界坐标与格子坐标的映射（权威实现）

坐标系约定（遵循 ROS map frame）：
- origin = (x0, y0) 表示 cell(0,0) 左下角在 world 中的位置
- cell index (i, j)：
  - i 是行索引（对应 y 方向，从上到下）
  - j 是列索引（对应 x 方向，从左到右）
- cell center 的 world 坐标：
  - x = x0 + (j + 0.5) * resolution
  - y = y0 + (i + 0.5) * resolution

注意：
- grid[i, j] 中，i 是行（y），j 是列（x）
- 这与 numpy 数组索引一致：grid[row, col]
"""

from typing import Tuple
import numpy as np


def cell_to_world(i: int, j: int, origin: Tuple[float, float], resolution: float) -> Tuple[float, float]:
    """
    将格子坐标转换为世界坐标（格子中心）
    
    Args:
        i: 行索引（y 方向）
        j: 列索引（x 方向）
        origin: 地图原点 (x0, y0)，表示 cell(0,0) 左下角的世界坐标
        resolution: 分辨率（米/格）
        
    Returns:
        (x, y) 世界坐标（格子中心）
    """
    x = origin[0] + (j + 0.5) * resolution
    y = origin[1] + (i + 0.5) * resolution
    return (x, y)


def world_to_cell(x: float, y: float, origin: Tuple[float, float], resolution: float) -> Tuple[int, int]:
    """
    将世界坐标转换为格子坐标
    
    使用 floor 归入格子（即向下取整）
    
    Args:
        x: 世界坐标 x
        y: 世界坐标 y
        origin: 地图原点 (x0, y0)
        resolution: 分辨率（米/格）
        
    Returns:
        (i, j) 格子坐标
    """
    j = int(np.floor((x - origin[0]) / resolution))
    i = int(np.floor((y - origin[1]) / resolution))
    return (i, j)


def clip_to_bounds(i: int, j: int, height: int, width: int) -> Tuple[int, int]:
    """
    将格子坐标裁剪到地图边界内
    
    Args:
        i: 行索引
        j: 列索引
        height: 地图高度（行数）
        width: 地图宽度（列数）
        
    Returns:
        (i_clipped, j_clipped) 裁剪后的格子坐标
    """
    i_clipped = max(0, min(i, height - 1))
    j_clipped = max(0, min(j, width - 1))
    return (i_clipped, j_clipped)


def world_to_cell_checked(x: float, y: float, origin: Tuple[float, float], 
                          resolution: float, height: int, width: int) -> Tuple[int, int]:
    """
    将世界坐标转换为格子坐标（带边界检查）
    
    如果转换后的格子坐标越界，抛出 ValueError
    
    Args:
        x: 世界坐标 x
        y: 世界坐标 y
        origin: 地图原点 (x0, y0)
        resolution: 分辨率（米/格）
        height: 地图高度（行数）
        width: 地图宽度（列数）
        
    Returns:
        (i, j) 格子坐标
        
    Raises:
        ValueError: 如果转换后的格子坐标越界
    """
    i, j = world_to_cell(x, y, origin, resolution)
    
    if not (0 <= i < height and 0 <= j < width):
        raise ValueError(
            f"World coordinate ({x}, {y}) maps to cell ({i}, {j}) "
            f"which is out of bounds (height={height}, width={width})"
        )
    
    return (i, j)


def in_bounds(i: int, j: int, height: int, width: int) -> bool:
    """
    检查格子坐标是否在地图边界内
    
    Args:
        i: 行索引
        j: 列索引
        height: 地图高度（行数）
        width: 地图宽度（列数）
        
    Returns:
        True 如果在边界内
    """
    return 0 <= i < height and 0 <= j < width


def get_cell_bounds(i: int, j: int, origin: Tuple[float, float], resolution: float) -> Tuple[float, float, float, float]:
    """
    获取格子的世界坐标边界
    
    Args:
        i: 行索引
        j: 列索引
        origin: 地图原点 (x0, y0)
        resolution: 分辨率（米/格）
        
    Returns:
        (x_min, y_min, x_max, y_max) 格子的世界坐标边界
    """
    x_min = origin[0] + j * resolution
    y_min = origin[1] + i * resolution
    x_max = x_min + resolution
    y_max = y_min + resolution

    return (x_min, y_min, x_max, y_max)


# ============================================================================
# 外部求解器坐标转换（用于与 MovingAI/MAPF 求解器兼容）
# ============================================================================

def to_solver_coords(i: int, j: int, height: int) -> Tuple[int, int]:
    """
    将内部坐标转换为外部求解器坐标。

    许多 MAPF 求解器和 MovingAI benchmark 使用 (x, y) 约定，其中：
    - x = 列索引（对应我们的 j）
    - y = 行索引，但 y=0 在**顶部**（与我们的 i 方向相反）

    转换规则：
    - solver_x = j（列索引不变）
    - solver_y = (height - 1) - i（行索引翻转）

    Args:
        i: 内部行索引（0 = 底部）
        j: 内部列索引（0 = 左侧）
        height: 地图高度

    Returns:
        (solver_x, solver_y) 外部求解器坐标

    Example:
        >>> # 内部 cell(0, 0) = 左下角
        >>> to_solver_coords(0, 0, height=10)
        (0, 9)  # 求解器坐标：左下角 = (x=0, y=9)

        >>> # 内部 cell(9, 0) = 左上角
        >>> to_solver_coords(9, 0, height=10)
        (0, 0)  # 求解器坐标：左上角 = (x=0, y=0)
    """
    solver_x = j
    solver_y = (height - 1) - i
    return (solver_x, solver_y)


def from_solver_coords(solver_x: int, solver_y: int, height: int) -> Tuple[int, int]:
    """
    将外部求解器坐标转换为内部坐标。

    这是 to_solver_coords() 的逆操作。

    Args:
        solver_x: 求解器 x 坐标（列索引）
        solver_y: 求解器 y 坐标（行索引，0 = 顶部）
        height: 地图高度

    Returns:
        (i, j) 内部坐标

    Example:
        >>> # 求解器坐标 (0, 9) = 左下角
        >>> from_solver_coords(0, 9, height=10)
        (0, 0)  # 内部坐标：左下角 = cell(0, 0)

        >>> # 求解器坐标 (0, 0) = 左上角
        >>> from_solver_coords(0, 0, height=10)
        (9, 0)  # 内部坐标：左上角 = cell(9, 0)
    """
    j = solver_x
    i = (height - 1) - solver_y
    return (i, j)


def format_solver_instance(
    start_cells: list,
    goal_cells: list,
    height: int
) -> dict:
    """
    格式化为求解器实例格式（MovingAI 风格）。

    Args:
        start_cells: 起点列表 [(i, j), ...]（内部坐标）
        goal_cells: 终点列表 [(i, j), ...]（内部坐标）
        height: 地图高度

    Returns:
        求解器实例字典，格式：
        {
            'agents': [
                {'start': [sx, sy], 'goal': [gx, gy]},
                ...
            ]
        }
        其中 (sx, sy) 和 (gx, gy) 是求解器坐标
    """
    agents = []
    for start_cell, goal_cell in zip(start_cells, goal_cells):
        sx, sy = to_solver_coords(start_cell[0], start_cell[1], height)
        gx, gy = to_solver_coords(goal_cell[0], goal_cell[1], height)
        agents.append({
            'start': [sx, sy],
            'goal': [gx, gy]
        })

    return {'agents': agents}


def parse_solver_solution(
    solution: list,
    height: int
) -> list:
    """
    解析求解器返回的路径（转换为内部坐标）。

    Args:
        solution: 求解器路径，格式：[[(x0, y0), (x1, y1), ...], ...]
        height: 地图高度

    Returns:
        内部坐标路径：[[(i0, j0), (i1, j1), ...], ...]
    """
    internal_paths = []
    for path in solution:
        internal_path = []
        for solver_x, solver_y in path:
            i, j = from_solver_coords(solver_x, solver_y, height)
            internal_path.append((i, j))
        internal_paths.append(internal_path)

    return internal_paths
