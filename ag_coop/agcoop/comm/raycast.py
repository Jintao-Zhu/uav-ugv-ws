"""
格栅射线追踪（Bresenham 算法）

用于计算两个格子之间的视线（Line of Sight, LOS）和遮挡情况。

坐标约定：
- i = row (y 方向)
- j = col (x 方向)
- 与项目其他模块保持一致
"""

from typing import List, Tuple
import numpy as np


def bresenham_cells(i0: int, j0: int, i1: int, j1: int) -> List[Tuple[int, int]]:
    """
    使用 Bresenham 算法计算两点连线穿过的格子序列。

    返回从 (i0, j0) 到 (i1, j1) 的所有格子，**包含端点**。

    Args:
        i0: 起点行索引
        j0: 起点列索引
        i1: 终点行索引
        j1: 终点列索引

    Returns:
        格子序列 [(i, j), ...]，包含起点和终点

    Example:
        >>> bresenham_cells(0, 0, 0, 3)
        [(0, 0), (0, 1), (0, 2), (0, 3)]

        >>> bresenham_cells(0, 0, 2, 2)
        [(0, 0), (1, 1), (2, 2)]
    """
    cells = []

    # 计算差值
    di = abs(i1 - i0)
    dj = abs(j1 - j0)

    # 确定步进方向
    si = 1 if i1 > i0 else -1
    sj = 1 if j1 > j0 else -1

    # 当前位置
    i, j = i0, j0

    # Bresenham 算法
    if dj > di:
        # 主要沿 j 方向移动
        err = dj / 2.0
        while j != j1:
            cells.append((i, j))
            err -= di
            if err < 0:
                i += si
                err += dj
            j += sj
    else:
        # 主要沿 i 方向移动
        err = di / 2.0
        while i != i1:
            cells.append((i, j))
            err -= dj
            if err < 0:
                j += sj
                err += di
            i += si

    # 添加终点
    cells.append((i1, j1))

    return cells


def count_blocked_cells(grid_map, cell_a: Tuple[int, int], cell_b: Tuple[int, int]) -> int:
    """
    计算两个格子之间的视线被多少个障碍格子遮挡。

    使用 Bresenham 算法追踪连线，统计穿过的障碍格子数量。
    **不包含端点**（即不统计 cell_a 和 cell_b 本身）。

    Args:
        grid_map: GridMap 对象（需要有 grid 属性，0=free, 1=obstacle）
        cell_a: 起点格子 (i, j)
        cell_b: 终点格子 (i, j)

    Returns:
        遮挡的障碍格子数量（不含端点）

    Example:
        >>> # 无障碍直线
        >>> count_blocked_cells(grid_map, (0, 0), (0, 5))
        0

        >>> # 中间有障碍
        >>> count_blocked_cells(grid_map, (0, 0), (0, 5))
        2  # 假设 (0, 2) 和 (0, 4) 是障碍
    """
    i0, j0 = cell_a
    i1, j1 = cell_b

    # 获取连线上的所有格子
    cells = bresenham_cells(i0, j0, i1, j1)

    # 统计障碍格子数量（不含端点）
    blocked_count = 0
    for idx, (i, j) in enumerate(cells):
        # 跳过端点
        if idx == 0 or idx == len(cells) - 1:
            continue

        # 检查是否越界
        if not (0 <= i < grid_map.height and 0 <= j < grid_map.width):
            continue

        # 统计障碍
        if grid_map.grid[i, j] == 1:
            blocked_count += 1

    return blocked_count


def has_line_of_sight(grid_map, cell_a: Tuple[int, int], cell_b: Tuple[int, int]) -> bool:
    """
    检查两个格子之间是否有直接视线（无障碍遮挡）。

    Args:
        grid_map: GridMap 对象
        cell_a: 起点格子 (i, j)
        cell_b: 终点格子 (i, j)

    Returns:
        True 如果有直接视线（blocked_count == 0）

    Example:
        >>> has_line_of_sight(grid_map, (0, 0), (0, 5))
        True  # 无障碍

        >>> has_line_of_sight(grid_map, (0, 0), (5, 5))
        False  # 有障碍遮挡
    """
    return count_blocked_cells(grid_map, cell_a, cell_b) == 0


def compute_los_distance(grid_map, cell_a: Tuple[int, int], cell_b: Tuple[int, int]) -> float:
    """
    计算两个格子之间的欧几里得距离（用于通信模型）。

    Args:
        grid_map: GridMap 对象
        cell_a: 起点格子 (i, j)
        cell_b: 终点格子 (i, j)

    Returns:
        欧几里得距离（米）

    Example:
        >>> compute_los_distance(grid_map, (0, 0), (3, 4))
        1.0  # 假设 resolution=0.2，则 sqrt(3^2 + 4^2) * 0.2 = 1.0
    """
    i0, j0 = cell_a
    i1, j1 = cell_b

    # 计算格子距离
    di = i1 - i0
    dj = j1 - j0
    cell_distance = np.sqrt(di**2 + dj**2)

    # 转换为世界距离
    world_distance = cell_distance * grid_map.resolution

    return world_distance
