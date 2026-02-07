"""
通信模型包装类

为 Rendezvous 规划器提供简单的接口
"""

from .comm_model import compute_snr, compute_snr_to_ugvs, CommConfig
from .raycast import compute_los_distance, count_blocked_cells


class CommModel:
    """
    通信模型包装类

    提供简单的 SNR 计算接口
    """

    def __init__(
        self,
        grid_map,
        tx_power_db: float = 0.0,
        pathloss_n: float = 2.0,
        obstacle_penalty_db: float = 6.0,
        snr_threshold_db: float = -9.0,
        eps_m: float = 0.05
    ):
        """
        初始化通信模型

        Args:
            grid_map: GridMap 对象
            tx_power_db: 发射功率（dB）
            pathloss_n: 路径损耗指数
            obstacle_penalty_db: 障碍物惩罚（dB）
            snr_threshold_db: SNR 阈值（dB）
            eps_m: 避免 log(0) 的小量
        """
        self.grid_map = grid_map
        self.config = CommConfig(
            tx_power_db=tx_power_db,
            pathloss_n=pathloss_n,
            obstacle_penalty_db=obstacle_penalty_db,
            snr_threshold_db=snr_threshold_db,
            eps_m=eps_m
        )

    def compute_snr(self, uav_cell, ugv_cell):
        """
        计算 SNR

        Args:
            uav_cell: UAV 位置 (i, j)
            ugv_cell: UGV 位置 (i, j)

        Returns:
            SNR（dB）
        """
        # 计算距离和遮挡（注意：grid_map 是第一个参数）
        distance_m = compute_los_distance(self.grid_map, uav_cell, ugv_cell)
        blocked_count = count_blocked_cells(self.grid_map, uav_cell, ugv_cell)

        # 计算 SNR
        return compute_snr(
            distance_m=distance_m,
            blocked_count=blocked_count,
            config=self.config
        )
