"""
Coverage 打分函数

用于评估候选中继点的质量，帮助 relay UGV 选择最佳位置以改善通信覆盖。

打分公式：
    score(r) = SNR(UAV_pos, r) - β * dist(relay_ugv, r) - γ * congestion(r)

其中：
- SNR(UAV_pos, r): UAV 当前位置到候选点 r 的 SNR
- dist(relay_ugv, r): relay UGV 到候选点 r 的距离（BFS）
- congestion(r): 候选点 r 的拥挤度（是否被其他 UGV 占用）
- β, γ: 权重参数
"""

from typing import Tuple, List, Dict, Optional
import numpy as np


def compute_coverage_score(
    candidate_cell: Tuple[int, int],
    uav_cell: Tuple[int, int],
    relay_ugv_cell: Tuple[int, int],
    other_ugv_cells: List[Tuple[int, int]],
    grid_map,
    comm_config,
    beta: float = 0.1,
    gamma: float = 5.0
) -> float:
    """
    计算候选中继点的 coverage 打分

    Args:
        candidate_cell: 候选点位置 (i, j)
        uav_cell: UAV 当前位置 (i, j)
        relay_ugv_cell: relay UGV 当前位置 (i, j)
        other_ugv_cells: 其他 UGV 的位置列表 [(i, j), ...]
        grid_map: GridMap 对象
        comm_config: 通信配置
        beta: 距离惩罚权重
        gamma: 拥挤度惩罚权重

    Returns:
        打分值（越高越好）
    """
    # 1. SNR 项：UAV 到候选点的 SNR
    from agcoop.comm import compute_snr

    # 计算距离（米）
    distance_m = _compute_distance_meters(uav_cell, candidate_cell, grid_map)

    # 计算遮挡
    blocked_count = _count_blocked_cells(uav_cell, candidate_cell, grid_map)

    # 计算 SNR
    snr = compute_snr(distance_m, blocked_count, comm_config)

    # 2. 距离项：relay UGV 到候选点的距离
    from agcoop.map.neighbors import shortest_path

    path = shortest_path(relay_ugv_cell, candidate_cell, grid_map.grid, connectivity=4)
    if path is None:
        # 不可达，返回很低的分数
        return -1e6

    dist = len(path) - 1  # 路径长度（格子数）

    # 3. 拥挤度项：候选点是否被其他 UGV 占用
    congestion = 0.0
    for other_cell in other_ugv_cells:
        if other_cell == candidate_cell:
            # 候选点被占用
            congestion += 1.0
        elif _manhattan_distance(other_cell, candidate_cell) <= 1:
            # 候选点附近有其他 UGV
            congestion += 0.5

    # 计算总分
    score = snr - beta * dist - gamma * congestion

    return score


def select_best_relay_target(
    candidate_relays: List[Tuple[int, int]],
    uav_cell: Tuple[int, int],
    relay_ugv_cell: Tuple[int, int],
    other_ugv_cells: List[Tuple[int, int]],
    grid_map,
    comm_config,
    beta: float = 0.1,
    gamma: float = 5.0
) -> Tuple[Optional[Tuple[int, int]], float]:
    """
    从候选点中选择最佳的 relay 目标

    Args:
        candidate_relays: 候选点列表 [(i, j), ...]
        uav_cell: UAV 当前位置 (i, j)
        relay_ugv_cell: relay UGV 当前位置 (i, j)
        other_ugv_cells: 其他 UGV 的位置列表 [(i, j), ...]
        grid_map: GridMap 对象
        comm_config: 通信配置
        beta: 距离惩罚权重
        gamma: 拥挤度惩罚权重

    Returns:
        (best_target, best_score)
        - best_target: 最佳候选点 (i, j)，如果没有可达点则为 None
        - best_score: 最佳分数
    """
    if not candidate_relays:
        return None, -1e6

    best_target = None
    best_score = -1e6

    for candidate in candidate_relays:
        score = compute_coverage_score(
            candidate,
            uav_cell,
            relay_ugv_cell,
            other_ugv_cells,
            grid_map,
            comm_config,
            beta,
            gamma
        )

        if score > best_score:
            best_score = score
            best_target = candidate

    return best_target, best_score


def check_outage_risk(
    snr_best: float,
    snr_threshold: float,
    risk_margin: float = 5.0
) -> bool:
    """
    检查是否存在 outage 风险

    Args:
        snr_best: 当前最佳 SNR (dB)
        snr_threshold: SNR 阈值 (dB)
        risk_margin: 风险边界 (dB)，当 SNR 接近阈值时触发

    Returns:
        True 如果存在风险，False 否则
    """
    # 如果 SNR 低于阈值 + 边界，认为有风险
    return snr_best < (snr_threshold + risk_margin)


def _compute_distance_meters(
    cell1: Tuple[int, int],
    cell2: Tuple[int, int],
    grid_map
) -> float:
    """
    计算两个格子之间的欧几里得距离（米）

    Args:
        cell1: 格子1 (i, j)
        cell2: 格子2 (i, j)
        grid_map: GridMap 对象

    Returns:
        距离（米）
    """
    # 转换为世界坐标
    world1 = grid_map.cell_to_world(cell1[0], cell1[1])
    world2 = grid_map.cell_to_world(cell2[0], cell2[1])

    # 计算欧几里得距离
    dx = world2[0] - world1[0]
    dy = world2[1] - world1[1]
    distance = np.sqrt(dx**2 + dy**2)

    return distance


def _count_blocked_cells(
    cell1: Tuple[int, int],
    cell2: Tuple[int, int],
    grid_map
) -> int:
    """
    计算两个格子之间的遮挡数（使用 Bresenham 直线算法）

    Args:
        cell1: 格子1 (i, j)
        cell2: 格子2 (i, j)
        grid_map: GridMap 对象

    Returns:
        遮挡的格子数
    """
    from agcoop.comm import raycast
    return raycast.count_blocked_cells(grid_map, cell1, cell2)


def _manhattan_distance(
    cell1: Tuple[int, int],
    cell2: Tuple[int, int]
) -> int:
    """
    计算曼哈顿距离

    Args:
        cell1: 格子1 (i, j)
        cell2: 格子2 (i, j)

    Returns:
        曼哈顿距离
    """
    return abs(cell1[0] - cell2[0]) + abs(cell1[1] - cell2[1])
