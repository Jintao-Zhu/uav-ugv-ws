"""
Greedy Policy

贪心策略：
- 任务选择: EDF (Earliest Deadline First) - 选择deadline最紧急的任务
- 中继点选择: 最近可达点 - 选择距离carrier UGV最近的候选点
"""

from typing import Dict, Any, Tuple
import numpy as np

from agcoop.policies.base_policy import BasePolicy


class GreedyPolicy(BasePolicy):
    """
    Greedy 策略

    核心思想：
    1. 任务选择：优先选择deadline最紧急的任务（EDF）
    2. 中继点选择：选择距离carrier UGV最近的候选点
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化 Greedy 策略

        Args:
            config: 配置字典
        """
        super().__init__(config)
        self.carrier_ugv_id = 0  # 默认0号UGV是carrier

    def select_action(self, observation: Dict[str, np.ndarray], info: Dict[str, Any]) -> Tuple[int, int]:
        """
        根据观测选择动作

        Args:
            observation: 环境观测
                - ugv_pos: (N, 2) UGV位置，归一化到[0,1]
                - uav_state: (3,) UAV状态
                - tasks_topM: (M, 4) Top-M任务 [x, y, deadline_normalized, available_flag]
                - comm: (3,) 通信状态
                - candidates_R: (R, 3) 候选点 [x, y, dist_to_carrier]
            info: 额外信息

        Returns:
            (task_choice, relay_target) 元组
        """
        # 1. 任务选择：EDF (Earliest Deadline First)
        task_choice = self._select_task_edf(observation['tasks_topM'])

        # 2. 中继点选择：最近可达点
        relay_target = self._select_nearest_relay(observation['candidates_R'])

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
        deadlines = tasks_topM[:, 2]  # deadline_normalize     # 将不可用任务的deadline设为无穷大
        deadlines_masked = np.where(available_mask, deadlines, np.inf)

        # 选择deadline最小（最紧急）的任务
        min_deadline_idx = np.argmin(deadlines_masked)

        # 返回任务索引+1（因为0表示不选择）
        return int(min_deadline_idx + 1)

    def _select_nearest_relay(self, candidates_R: np.ndarray) -> int:
        """
        选择距离carrier UGV最近的候选点

        Args:
            candidates_R: (R, 3) 候选点
                - candidates_R[:, 0:2]: 候选点位置 (x, y)
                - candidates_R[:, 2]: dist_to_carrier (距离carrier的距离)

        Returns:
            relay_target: 1..R (选择的候选点索引+1)，0表示不选择
        """
        R = candidates_R.shape[0]

        if R == 0:
            # 没有候选点，返回0
            return 0

        # 获取距离
        distances = candidates_R[:, 2]  # dist_to_carrier

        # 选择距离最小的候选点
        min_dist_idx = np.argmin(distances)

        # 返回候选点索引+1（因为0表示不选择）
        return int(min_dist_idx + 1)

    def get_name(self) -> str:
        """返回策略名称"""
        return "Greedy"
