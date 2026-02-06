"""
邻接图和最短路径工具

提供：
- get_neighbors(): 获取格子的合法邻居（4-连通或 8-连通）
- shortest_path_length(): BFS 计算最短路径长度
- shortest_path(): BFS 计算完整路径（可选）

Day2 版本：使用 4-连通（更适合差速车），BFS 足够快。
"""

from typing import List, Tuple, Optional
from collections import deque
import numpy as np


# 4-连通邻居偏移（上下左右）
NEIGHBORS_4 = [
    (-1, 0),  # 上（i-1）
    (1, 0),   # 下（i+1）
    (0, -1),  # 左（j-1）
    (0, 1),   # 右（j+1）
]

# 8-连通邻居偏移（包含对角线）
NEIGHBORS_8 = [
    (-1, 0),   # 上
    (1, 0),    # 下
    (0, -1),   # 左
    (0, 1),    # 右
    (-1, -1),  # 左上
    (-1, 1),   # 右上
    (1, -1),   # 左下
    (1, 1),    # 右下
]


def get_neighbors(
    i: int,
    j: int,
    grid: np.ndarray,
    connectivity: int = 4
) -> List[Tuple[int, int]]:
    """
    获取格子 (i, j) 的合法邻居。

    Args:
        i: 行索引
        j: 列索引
        grid: 栅格地图（0=自由，1=障碍）
        connectivity: 连通性（4 或 8）

    Returns:
        合法邻居列表 [(i1, j1), (i2, j2), ...]
        只返回在边界内且为自由格子的邻居
    """
    height, width = grid.shape
    neighbors = []

    # 选择邻居偏移
    if connectivity == 4:
        offsets = NEIGHBORS_4
    elif connectivity == 8:
        offsets = NEIGHBORS_8
    else:
        raise ValueError(f"connectivity 必须是 4 或 8，得到 {connectivity}")

    # 遍历所有邻居偏移
    for di, dj in offsets:
        ni, nj = i + di, j + dj

        # 检查边界
        if 0 <= ni < height and 0 <= nj < width:
            # 检查是否为自由格子
            if grid[ni, nj] == 0:
                neighbors.append((ni, nj))

    return neighbors


def shortest_path_length(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    grid: np.ndarray,
    connectivity: int = 4
) -> Optional[int]:
    """
    使用 BFS 计算从 start 到 goal 的最短路径长度。

    Args:
        start: 起点 (i, j)
        goal: 终点 (i, j)
        grid: 栅格地图（0=自由，1=障碍）
        connectivity: 连通性（4 或 8）

    Returns:
        最短路径长度（步数），如果无法到达则返回 None
    """
    # 边界检查
    height, width = grid.shape
    si, sj = start
    gi, gj = goal

    if not (0 <= si < height and 0 <= sj < width):
        return None
    if not (0 <= gi < height and 0 <= gj < width):
        return None

    # 检查起点和终点是否为自由格子
    if grid[si, sj] != 0 or grid[gi, gj] != 0:
        return None

    # 特殊情况：起点即终点
    if start == goal:
        return 0

    # BFS
    queue = deque([(start, 0)])  # (cell, distance)
    visited = {start}

    while queue:
        (i, j), dist = queue.popleft()

        # 获取邻居
        for ni, nj in get_neighbors(i, j, grid, connectivity):
            if (ni, nj) in visited:
                continue

            # 检查是否到达终点
            if (ni, nj) == goal:
                return dist + 1

            # 加入队列
            visited.add((ni, nj))
            queue.append(((ni, nj), dist + 1))

    # 无法到达
    return None


def shortest_path(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    grid: np.ndarray,
    connectivity: int = 4
) -> Optional[List[Tuple[int, int]]]:
    """
    使用 BFS 计算从 start 到 goal 的完整最短路径。

    Args:
        start: 起点 (i, j)
        goal: 终点 (i, j)
        grid: 栅格地图（0=自由，1=障碍）
        connectivity: 连通性（4 或 8）

    Returns:
        最短路径 [start, ..., goal]，如果无法到达则返回 None
    """
    # 边界检查
    height, width = grid.shape
    si, sj = start
    gi, gj = goal

    if not (0 <= si < height and 0 <= sj < width):
        return None
    if not (0 <= gi < height and 0 <= gj < width):
        return None

    # 检查起点和终点是否为自由格子
    if grid[si, sj] != 0 or grid[gi, gj] != 0:
        return None

    # 特殊情况：起点即终点
    if start == goal:
        return [start]

    # BFS（记录父节点以重建路径）
    queue = deque([start])
    visited = {start}
    parent = {start: None}

    while queue:
        current = queue.popleft()
        i, j = current

        # 获取邻居
        for ni, nj in get_neighbors(i, j, grid, connectivity):
            neighbor = (ni, nj)
            if neighbor in visited:
                continue

            # 记录父节点
            visited.add(neighbor)
            parent[neighbor] = current
            queue.append(neighbor)

            # 检查是否到达终点
            if neighbor == goal:
                # 重建路径
                path = []
                node = goal
                while node is not None:
                    path.append(node)
                    node = parent[node]
                path.reverse()
                return path

    # 无法到达
    return None


def compute_distance_map(
    start: Tuple[int, int],
    grid: np.ndarray,
    connectivity: int = 4,
    max_distance: Optional[int] = None
) -> np.ndarray:
    """
    从起点开始，计算到所有可达格子的距离（BFS）。

    Args:
        start: 起点 (i, j)
        grid: 栅格地图（0=自由，1=障碍）
        connectivity: 连通性（4 或 8）
        max_distance: 最大距离（可选，用于限制搜索范围）

    Returns:
        距离地图（np.ndarray），未到达的格子为 -1
    """
    height, width = grid.shape
    si, sj = start

    # 初始化距离地图
    dist_map = np.full((height, width), -1, dtype=np.int32)

    # 边界检查
    if not (0 <= si < height and 0 <= sj < width):
        return dist_map
    if grid[si, sj] != 0:
        return dist_map

    # BFS
    queue = deque([start])
    dist_map[si, sj] = 0

    while queue:
        i, j = queue.popleft()
        current_dist = dist_map[i, j]

        # 检查是否超过最大距离
        if max_distance is not None and current_dist >= max_distance:
            continue

        # 获取邻居
        for ni, nj in get_neighbors(i, j, grid, connectivity):
            if dist_map[ni, nj] == -1:  # 未访问
                dist_map[ni, nj] = current_dist + 1
                queue.append((ni, nj))

    return dist_map
