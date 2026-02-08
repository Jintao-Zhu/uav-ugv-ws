"""
候选中继点生成器

生成用于 UAV 中继通信的候选位置点集合 R。

算法：
1. Intersection 点：邻居可通行数 >= 3 的格子（路口/分叉）
2. Open-space 点：离障碍物较远的格子（使用 BFS 距离）
3. 均匀补点：从 free cells 中均匀采样补足到 R

特点：
- 确定性：相同 seed + map 生成完全一致的 R
- 可复现：结果写入 init.json 的 candidate_relays 字段
- 可视化：支持在 visualizer 中显示
"""

from typing import List, Tuple, Set
import numpy as np
from collections import deque


def generate_candidate_relays(
    grid_map,
    R: int = 12,
    rng: np.random.RandomState = None
) -> List[Tuple[int, int]]:
    """
    生成候选中继点集合

    Args:
        grid_map: GridMap 对象
        R: 候选点数量（默认 12）
        rng: 随机数生成器（用于确定性采样）

    Returns:
        候选点列表 [(i, j), ...]，长度为 R
    """
    if rng is None:
        rng = np.random.RandomState(0)

    # 获取所有 free cells
    free_cells = []
    for i in range(grid_map.height):
        for j in range(grid_map.width):
            if grid_map.is_free(i, j):
                free_cells.append((i, j))

    if len(free_cells) < R:
        # 如果 free cells 不足 R 个，返回所有 free cells
        return free_cells

    candidates = set()

    # 1. Intersection 点：邻居可通行数 >= 3
    intersection_points = _find_intersection_points(grid_map, free_cells)
    candidates.update(intersection_points)

    # 2. Open-space 点：离障碍物较远的格子
    if len(candidates) < R:
        open_space_points = _find_open_space_points(
            grid_map, free_cells,
            exclude=candidates,
            target_count=R - len(candidates)
        )
        candidates.update(open_space_points)

    # 3. 均匀补点：从剩余 free cells 中均匀采样
    if len(candidates) < R:
        remaining_cells = [c for c in free_cells if c not in candidates]
        if remaining_cells:
            # 使用确定性采样
            n_needed = min(R - len(candidates), len(remaining_cells))
            sampled_indices = rng.choice(len(remaining_cells), size=n_needed, replace=False)
            sampled_cells = [remaining_cells[i] for i in sampled_indices]
            candidates.update(sampled_cells)

    # 转换为列表并排序（确保确定性）
    candidates_list = sorted(list(candidates))

    # 如果还不够 R 个，重复采样（理论上不应该发生）
    if len(candidates_list) < R:
        # 从 free_cells 中随机补足
        remaining = [c for c in free_cells if c not in candidates_list]
        if remaining:
            n_needed = R - len(candidates_list)
            sampled_indices = rng.choice(len(remaining), size=min(n_needed, len(remaining)), replace=False)
            candidates_list.extend([remaining[i] for i in sampled_indices])

    # 截取前 R 个
    return candidates_list[:R]


def _find_intersection_points(grid_map, free_cells: List[Tuple[int, int]]) -> Set[Tuple[int, int]]:
    """
    找到 Intersection 点：邻居可通行数 >= 3 的格子

    Args:
        grid_map: GridMap 对象
        free_cells: 所有 free cells

    Returns:
        Intersection 点集合
    """
    intersection_points = set()

    # 4-连通邻居
    neighbors_4 = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    for i, j in free_cells:
        # 统计可通行邻居数
        free_neighbor_count = 0
        for di, dj in neighbors_4:
            ni, nj = i + di, j + dj
            if 0 <= ni < grid_map.height and 0 <= nj < grid_map.width:
                if grid_map.is_free(ni, nj):
                    free_neighbor_count += 1

        # 邻居数 >= 3 表示是路口/分叉点
        if free_neighbor_count >= 3:
            intersection_points.add((i, j))

    return intersection_points


def _find_open_space_points(
    grid_map,
    free_cells: List[Tuple[int, int]],
    exclude: Set[Tuple[int, int]],
    target_count: int
) -> Set[Tuple[int, int]]:
    """
    找到 Open-space 点：离障碍物较远的格子

    使用 BFS 计算每个 free cell 到最近障碍物的距离，
    选择距离最大的 target_count 个点。

    Args:
        grid_map: GridMap 对象
        free_cells: 所有 free cells
        exclude: 已选中的点（不再选择）
        target_count: 目标数量

    Returns:
        Open-space 点集合
    """
    # 计算每个 free cell 到最近障碍物的距离
    distances = {}

    for cell in free_cells:
        if cell in exclude:
            continue
        dist = _distance_to_nearest_obstacle(grid_map, cell)
        distances[cell] = dist

    # 按距离排序，选择距离最大的 target_count 个
    sorted_cells = sorted(distances.items(), key=lambda x: x[1], reverse=True)
    open_space_points = set([cell for cell, dist in sorted_cells[:target_count]])

    return open_space_points


def _distance_to_nearest_obstacle(grid_map, start: Tuple[int, int]) -> int:
    """
    使用 BFS 计算到最近障碍物的距离

    Args:
        grid_map: GridMap 对象
        start: 起始格子 (i, j)

    Returns:
        到最近障碍物的距离（格子数）
    """
    queue = deque([(start, 0)])
    visited = {start}

    neighbors_4 = [(0, 1), (0, -1), (1, 0), (-1, 0)]

    while queue:
        (i, j), dist = queue.popleft()

        # 检查邻居
        for di, dj in neighbors_4:
            ni, nj = i + di, j + dj

            # 边界检查
            if not (0 <= ni < grid_map.height and 0 <= nj < grid_map.width):
                continue

            # 如果是障碍物，返回距离
            if not grid_map.is_free(ni, nj):
                return dist + 1

            # 如果是 free cell 且未访问，加入队列
            if (ni, nj) not in visited:
                visited.add((ni, nj))
                queue.append(((ni, nj), dist + 1))

    # 如果没有找到障碍物（理论上不应该发生），返回一个大值
    return 999
