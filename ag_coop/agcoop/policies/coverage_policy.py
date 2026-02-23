"""
Coverage Policy

覆盖策略：
- 任务选择: EDF (Earliest Deadline First) - 选择deadline最紧急的任务
- 中继点选择: 最大化SNR覆盖 - 选择能最大化通信覆盖的候选点
"""

from typing import Dict, Any, Tuple
import numpy as np

from agcoop.policies.base_policy import BasePolicy


class CoveragePolicy(BasePolicy):
    """
    Coverage 策略

    核心思想：
    1. 任务选择：优先选择deadline最紧急的任务（EDF）
    2. 中继点选择：选择能最大化通信覆盖的候选点
       - 考虑候选点到所有UGV的通信质量
       - 优先选择能覆盖更多UGV的候选点
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Coverage 策略

        Args:
            config: 配置字典
        """
        super().__init__(config)
        self.carrier_ugv_id = 0  # 默认0号UGV是carrier

        # 通信参数
        self.comm_config = config.get('comm', {})
        self.snr_threshold_db = self.comm_config.get('snr_threshold_db', -20.0)

        # 覆盖评分权重
        self.coverage_weight_distance = 0.3  # 距离权重
        self.coverage_weight_coverage = 0.7  # 覆盖权重

    def select_action(self, observation: Dict[str, np.ndarray], info: Dict[str, Any]) -> Tuple[int, int]:
        """
        根据观测选择动作

        Args:
            observation: 环境观测
                - ugv_pos: (N, 2) UGV位置，归一化到[0,1]
                - uav_state: (3,) UAV状态
                - tasks_topM: (M, 4) Top-M任务 [x, y, deadline_normalized, available_flag]
                - comm: (3,) 通信状态 [snr_best_nc, outage_percent_worst_nc, best_ugv_id_nc]
                - candidates_R: (R, 3) 候选点 [x, y, dist_to_carrier]
            info: 额外信息

        Returns:
            (task_choice, relay_target) 元组
        """
        # 1. 任务选择：EDF (Earliest Deadline First)
        task_choice = self._select_task_edf(observation['tasks_topM'])

        # 2. 中继点选择：最大化覆盖
        relay_target = self._select_coverage_relay(
            observation['candidates_R'],
            observation['ugv_pos'],
            observation['comm']
        )

        return task_choice, relay_target

    def _select_task_edf(self, tasks_topM: np.ndarray) -> int:
        """
        使用 EDF (Earliest Deadline First) 选择任务

        Args:
            tasks_topM: (M, 4) Top-M任务
                - tasks_topM[:, 0:2]: 任务位置 (x, y)
                - tasks_topM[:, 2]: deadline_normalized (越小越紧急)
                - tasks_topM[:, 3]: available_flag (1=可用, 0=不可用)

        Returns:
            task_choice: 1..M (选择的任务索引+1)，0表示不选择
        """
        M = tasks_topM.shape[0]

        # 找到所有可用任务
        available_mask = tasks_topM[:, 3] > 0.5  # available_flag > 0.5

        if not np.any(available_mask):
            # 没有可用任务，返回0（不选择）
            return 0

        # 获取可用任务的deadline
        deadlines = tasks_topM[:, 2]  # deadline_normalized

        # 将不可用任务的deadline设为无穷大
        deadlines_masked = np.where(available_mask, deadlines, np.inf)

        # 选择deadline最小（最紧急）的任务
        min_deadline_idx = np.argmin(deadlines_masked)

        # 返回任务索引+1（因为0表示不选择）
        return int(min_deadline_idx + 1)

    def _select_coverage_relay(
        self,
        candidates_R: np.ndarray,
        ugv_pos: np.ndarray,
        comm_state: np.ndarray
    ) -> int:
        """
        选择能最大化通信覆盖的候选点

        策略：
        1. 计算每个候选点到所有UGV的距离
        2. 估算覆盖质量：距离越近，覆盖越好
        3. 综合考虑：
           - 覆盖更多UGV（coverage score）
           - 距离carrier不要太远（distance penalty）

        Args:
            candidates_R: (R, 3) 候选点
                - candidates_R[:, 0:2]: 候选点位置 (x, y)，归一化到[0,1]
                - candidates_R[:, 2]: dist_to_carrier
            ugv_pos: (N, 2) UGV位置，归一化到[0,1]
            comm_state: (3,) 通信状态
                - comm_state[0]: snr_best_nc
                - comm_state[1]: outage_percent_worst_nc
                - comm_state[2]: best_ugv_id_nc

        Returns:
            relay_target: 1..R (选择的候选点索引+1)，0表示不选择
        """
        R = candidates_R.shape[0]
        N = ugv_pos.shape[0]

        if R == 0:
            # 没有候选点，返回0
            return 0

        # 提取候选点位置
        candidate_positions = candidates_R[:, 0:2]  # (R, 2)

        # 计算每个候选点的覆盖评分
        coverage_scores = np.zeros(R)

        for i in range(R):
            candidate_pos = candidate_positions[i]  # (2,)

            # 计算到所有UGV的距离
            distances = np.linalg.norm(ugv_pos - candidate_pos, axis=1)  # (N,)

            # 覆盖评分：距离越近，评分越高
            # 使用指数衰减：score = exp(-distance / sigma)
            sigma = 0.2  # 衰减参数（归一化坐标系下）
            coverage_per_ugv = np.exp(-distances / sigma)  # (N,)

            # 总覆盖评分：所有UGV的覆盖之和
            total_coverage = np.sum(coverage_per_ugv)

            # 距离惩罚：候选点距离carrier太远会被惩罚
            dist_to_carrier = candidates_R[i, 2]
            distance_penalty = np.exp(-dist_to_carrier / 0.3)  # 距离越远，惩罚越大

            # 综合评分
            coverage_scores[i] = (
                self.coverage_weight_coverage * total_coverage +
                self.coverage_weight_distance * distance_penalty
            )

        # 选择评分最高的候选点
        best_idx = np.argmax(coverage_scores)

        # 返回候选点索引+1（因为0表示不选择）
        return int(best_idx + 1)

    def get_name(self) -> str:
        """返回策略名称"""
        return "Coverage"
