"""
Base Policy Interface

所有确定性策略的基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
import numpy as np


class BasePolicy(ABC):
    """
    策略基类

    所有确定性策略都应继承此类并实现 select_action 方法
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化策略

        Args:
            config: 配置字典
        """
        self.config = config
        self.top_m = config['tasks'].get('top_m', 5)
        self.candidate_count = config.get('rendezvous', {}).get('candidate_count', 12)

    @abstractmethod
    def select_action(self, observation: Dict[str, np.ndarray], info: Dict[str, Any]) -> Tuple[int, int]:
        """
        根据观测选择动作

        Args:
            observation: 环境观测（Dict格式）
                - ugv_pos: (N, 2) UGV位置
                - uav_state: (3,) UAV状态
                - tasks_topM: (M, 4) Top-M任务
                - comm: (3,) 通信状态
                - candidates_R: (R, 3) 候选中继点
            info: 额外信息

        Returns:
            (task_choice, relay_target) 元组
            - task_choice: 0..M (0表示不指定任务)
            - relay_target: 0..R (0表示不指定中继点)
        """
        pass

    def reset(self):
        """重置策略内部状态（如果有）"""
        pass

    def get_name(self) -> str:
        """返回策略名称"""
        return self.__class__.__name__
