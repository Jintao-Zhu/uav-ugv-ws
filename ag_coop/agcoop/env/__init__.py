"""
环境模块

包含：
- CoopEnv 协同环境类
- EnvConfig 环境配置类
- FlattenObservation 观测展平 wrapper
- NormalizeReward 奖励归一化 wrapper
"""

from .coop_env import CoopEnv, EnvConfig
from .wrappers import FlattenObservation, NormalizeReward

__all__ = ['CoopEnv', 'EnvConfig', 'FlattenObservation', 'NormalizeReward']
