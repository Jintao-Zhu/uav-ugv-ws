"""
Day9 Step 3: Environment Wrappers

提供环境包装器，用于转换观测格式等
"""

import numpy as np
from typing import Dict, Any, Tuple

try:
    import gymnasium as gym
    from gymnasium import spaces
    from gymnasium.core import Wrapper
except ImportError:
    import gym
    from gym import spaces
    from gym.core import Wrapper


class FlattenObservation(Wrapper):
    """
    将 Dict 格式的观测展平为单一的 Box 向量

    用于 PPO 等需要 Box observation space 的算法
    """

    def __init__(self, env):
        """
        初始化 wrapper

        Args:
            env: 原始环境（observation_space 必须是 Dict）
        """
        super().__init__(env)

        # 验证原始 observation space 是 Dict
        if not isinstance(env.observation_space, spaces.Dict):
            raise ValueError(f"FlattenObservation requires Dict observation space, got {type(env.observation_space)}")

        # 计算展平后的维度
        self._obs_keys = sorted(env.observation_space.spaces.keys())
        self._obs_shapes = {key: env.observation_space[key].shape for key in self._obs_keys}
        self._obs_sizes = {key: int(np.prod(shape)) for key, shape in self._obs_shapes.items()}

        total_size = sum(self._obs_sizes.values())

        # 创建展平后的 observation space
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(total_size,),
            dtype=np.float32
        )

        print(f"FlattenObservation: {self._obs_keys} -> Box({total_size},)")
        for key in self._obs_keys:
            print(f"  - {key}: {self._obs_shapes[key]} -> {self._obs_sizes[key]}")

    def _flatten_obs(self, obs_dict: Dict[str, np.ndarray]) -> np.ndarray:
        """
        将 Dict 观测展平为向量

        Args:
            obs_dict: Dict 格式的观测

        Returns:
            展平后的向量
        """
        flattened = []
        for key in self._obs_keys:
            if key not in obs_dict:
                raise KeyError(f"Missing key '{key}' in observation")
            flattened.append(obs_dict[key].flatten())

        return np.concatenate(flattened, axis=0).astype(np.float32)

    def reset(self, **kwargs):
        """重置环境并展平观测"""
        obs_dict, info = self.env.reset(**kwargs)
        return self._flatten_obs(obs_dict), info

    def step(self, action):
        """执行一步并展平观测"""
        obs_dict, reward, terminated, truncated, info = self.env.step(action)
        obs_flat = self._flatten_obs(obs_dict)

        # 在 info 中保留原始 Dict 观测（用于调试）
        info['obs_dict'] = obs_dict

        return obs_flat, reward, terminated, truncated, info


class NormalizeReward(Wrapper):
    """
    归一化奖励（可选，Day10 使用）

    使用移动平均和标准差归一化奖励
    """

    def __init__(self, env, gamma: float = 0.99, epsilon: float = 1e-8):
        """
        初始化 wrapper

        Args:
            env: 原始环境
            gamma: 折扣因子
            epsilon: 数值稳定性常数
        """
        super().__init__(env)
        self.gamma = gamma
        self.epsilon = epsilon
        self.returns = 0.0
        self.return_mean = 0.0
        self.return_var = 1.0
        self.count = 0

    def reset(self, **kwargs):
        """重置环境"""
        self.returns = 0.0
        return self.env.reset(**kwargs)

    def step(self, action):
        """执行一步并归一化奖励"""
        obs, reward, terminated, truncated, info = self.env.step(action)

        # 更新 return 统计
        self.returns = self.returns * self.gamma + reward
        self.count += 1

        # 更新移动平均和方差
        delta = self.returns - self.return_mean
        self.return_mean += delta / self.count
        self.return_var += delta * (self.returns - self.return_mean)

        # 归一化奖励
        std = np.sqrt(self.return_var / max(1, self.count - 1) + self.epsilon)
        normalized_reward = reward / std

        # 在 info 中保留原始奖励
        info['reward_raw'] = reward
        info['reward_normalized'] = normalized_reward

        return obs, normalized_reward, terminated, truncated, info
