"""
通信模型：SNR 计算和 outage 判断

基于距离衰减和障碍物遮挡的通信质量模型。

SNR 公式：
    snr_db = tx_power_db - 10 * pathloss_n * log10(d + eps) - obstacle_penalty_db * blocked

其中：
- tx_power_db: 发射功率（dB）
- pathloss_n: 路径损耗指数（通常 2.0-4.0）
- d: 距离（米）
- eps: 避免 log(0) 的小量
- blocked: 遮挡的障碍格子数
- obstacle_penalty_db: 每个障碍的衰减（dB）

Outage 判断：
    outage = 1 if snr_best < snr_threshold_db else 0
"""

from typing import Tuple, List, Optional
import numpy as np
from dataclasses import dataclass


@dataclass
class CommConfig:
    """通信模型配置"""
    enabled: bool = True
    tx_power_db: float = 0.0
    pathloss_n: float = 2.0
    obstacle_penalty_db: float = 6.0
    snr_threshold_db: float = -20.0
    eps_m: float = 0.05

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'CommConfig':
        """从配置字典创建"""
        return cls(
            enabled=config_dict.get('enabled', True),
            tx_power_db=config_dict.get('tx_power_db', 0.0),
            pathloss_n=config_dict.get('pathloss_n', 2.0),
            obstacle_penalty_db=config_dict.get('obstacle_penalty_db', 6.0),
            snr_threshold_db=config_dict.get('snr_threshold_db', -20.0),
            eps_m=config_dict.get('eps_m', 0.05),
        )


def compute_snr(
    distance_m: float,
    blocked_count: int,
    config: CommConfig
) -> float:
    """
    计算 SNR（信噪比）。

    Args:
        distance_m: 距离（米）
        blocked_count: 遮挡的障碍格子数
        config: 通信配置

    Returns:
        SNR（dB）

    Example:
        >>> config = CommConfig(tx_power_db=0.0, pathloss_n=2.0, obstacle_penalty_db=6.0, eps_m=0.05)
        >>> compute_snr(1.0, 0, config)
        0.0  # 1 米无障碍，SNR = 0 - 10*2*log10(1.05) ≈ -0.21

        >>> compute_snr(10.0, 2, config)
        -32.0  # 10 米 + 2 个障碍，SNR = 0 - 10*2*log10(10.05) - 6*2 ≈ -32.0
    """
    # 距离衰减项
    distance_loss_db = 10.0 * config.pathloss_n * np.log10(distance_m + config.eps_m)

    # 障碍衰减项
    obstacle_loss_db = config.obstacle_penalty_db * blocked_count

    # 总 SNR
    snr_db = config.tx_power_db - distance_loss_db - obstacle_loss_db

    return snr_db


def compute_snr_to_ugvs(
    uav_cell: Tuple[int, int],
    ugv_cells: List[Tuple[int, int]],
    grid_map,
    config: CommConfig
) -> Tuple[List[float], List[float], List[int]]:
    """
    计算 UAV 到所有 UGV 的 SNR。

    Args:
        uav_cell: UAV 格子坐标 (i, j)
        ugv_cells: UGV 格子坐标列表 [(i, j), ...]
        grid_map: GridMap 对象
        config: 通信配置

    Returns:
        (snr_list, distance_list, blocked_list)
        - snr_list: 每个 UGV 的 SNR（dB）
        - distance_list: 每个 UGV 的距离（米）
        - blocked_list: 每个 UGV 的遮挡数

    Example:
        >>> snr_list, dist_list, blocked_list = compute_snr_to_ugvs(
        ...     (0, 0), [(0, 5), (5, 5)], grid_map, config
        ... )
    """
    from agcoop.comm import raycast

    snr_list = []
    distance_list = []
    blocked_list = []

    for ugv_cell in ugv_cells:
        # 计算距离
        distance = raycast.compute_los_distance(grid_map, uav_cell, ugv_cell)

        # 计算遮挡
        blocked = raycast.count_blocked_cells(grid_map, uav_cell, ugv_cell)

        # 计算 SNR
        snr = compute_snr(distance, blocked, config)

        snr_list.append(snr)
        distance_list.append(distance)
        blocked_list.append(blocked)

    return snr_list, distance_list, blocked_list


def compute_best_snr(
    uav_cell: Tuple[int, int],
    ugv_cells: List[Tuple[int, int]],
    grid_map,
    config: CommConfig
) -> Tuple[float, int, bool]:
    """
    计算 UAV 到所有 UGV 的最佳 SNR。

    Args:
        uav_cell: UAV 格子坐标 (i, j)
        ugv_cells: UGV 格子坐标列表 [(i, j), ...]
        grid_map: GridMap 对象
        config: 通信配置

    Returns:
        (snr_best, best_ugv_id, outage)
        - snr_best: 最佳 SNR（dB）
        - best_ugv_id: 最佳 UGV 的索引（0-based）
        - outage: 是否处于 outage 状态（True/False）

    Example:
        >>> snr_best, best_id, outage = compute_best_snr(
        ...     (0, 0), [(0, 5), (5, 5)], grid_map, config
        ... )
        >>> print(f"Best SNR: {snr_best:.2f} dB, Best UGV: {best_id}, Outage: {outage}")
    """
    if not ugv_cells:
        # 没有 UGV，返回最差情况
        return -np.inf, -1, True

    # 计算所有 UGV 的 SNR
    snr_list, _, _ = compute_snr_to_ugvs(uav_cell, ugv_cells, grid_map, config)

    # 找到最佳 SNR
    snr_best = max(snr_list)
    best_ugv_id = int(np.argmax(snr_list))

    # 判断 outage
    outage = snr_best < config.snr_threshold_db

    return snr_best, best_ugv_id, outage


def compute_comm_metrics(
    uav_cell: Tuple[int, int],
    ugv_cells: List[Tuple[int, int]],
    grid_map,
    config: CommConfig
) -> dict:
    """
    计算完整的通信指标（用于日志记录）。

    Args:
        uav_cell: UAV 格子坐标 (i, j)
        ugv_cells: UGV 格子坐标列表 [(i, j), ...]
        grid_map: GridMap 对象
        config: 通信配置

    Returns:
        通信指标字典：
        {
            'snr_best': float,
            'best_ugv_id': int,
            'outage': bool,
            'snr_list': List[float],
            'distance_list': List[float],
            'blocked_list': List[int],
        }

    Example:
        >>> metrics = compute_comm_metrics((0, 0), [(0, 5), (5, 5)], grid_map, config)
        >>> print(f"SNR best: {metrics['snr_best']:.2f} dB")
        >>> print(f"Outage: {metrics['outage']}")
    """
    if not ugv_cells:
        return {
            'snr_best': -np.inf,
            'best_ugv_id': -1,
            'outage': True,
            'snr_list': [],
            'distance_list': [],
            'blocked_list': [],
        }

    # 计算所有 UGV 的 SNR
    snr_list, distance_list, blocked_list = compute_snr_to_ugvs(
        uav_cell, ugv_cells, grid_map, config
    )

    # 找到最佳 SNR
    snr_best = max(snr_list)
    best_ugv_id = int(np.argmax(snr_list))

    # 判断 outage
    outage = snr_best < config.snr_threshold_db

    return {
        'snr_best': float(snr_best),
        'best_ugv_id': int(best_ugv_id),
        'outage': bool(outage),
        'snr_list': [float(s) for s in snr_list],
        'distance_list': [float(d) for d in distance_list],
        'blocked_list': [int(b) for b in blocked_list],
    }
