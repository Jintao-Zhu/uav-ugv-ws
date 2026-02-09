"""
Day9 Step 5: Gym Environment Wrapper

提供标准 Gym 接口的环境包装类，最小侵入 core.py
"""

from typing import Dict, Any, Tuple, Optional
import numpy as np

try:
    import gymnasium as gym
    from gymnasium import spaces
    GYMNASIUM = True
except ImportError:
    import gym
    from gym import spaces
    GYMNASIUM = False

from agcoop.env.core import AGCoopEnv


class AGCoopGymEnv(gym.Env):
    """
    AGCoop Gym 环境包装类

    将 AGCoopEnv (core.py) 包装为标准 Gym 接口
    """

    metadata = {'render_modes': ['human', 'rgb_array']}

    def __init__(
        self,
        config: Dict[str, Any],
        output_dir: Optional[str] = None,
        enable_logging: bool = False,
        run_id: Optional[str] = None,
        render_mode: Optional[str] = None
    ):
        """
        初始化 Gym 环境

        Args:
            config: 配置字典
            output_dir: 输出目录（用于日志记录）
            enable_logging: 是否启用日志记录
            run_id: 运行 ID
            render_mode: 渲染模式 ('human', 'rgb_array', None)
        """
        super().__init__()

        # 创建 core 环境
        self.core_env = AGCoopEnv(
            config,
            output_dir=output_dir,
            enable_logging=enable_logging,
            run_id=run_id,
            method="rl",
            planner="PIBT"
        )

        # 设置 action space 和 observation space
        self.action_space = self.core_env.action_space
        self.observation_space = self.core_env.observation_space

        # 渲染模式
        self.render_mode = render_mode
        self._renderer = None

        # 配置
        self.config = config
        self.horizon_steps = config['episode']['horizon_steps']

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        重置环境

        Args:
            seed: 随机种子（可选）
            options: 额外选项（可选）

        Returns:
            (observation, info) 元组
            - observation: 初始观测
            - info: 额外信息字典
        """
        # 设置随机种子
        if seed is not None:
            self.core_env.config['episode']['seed'] = seed
            # 重新初始化 core 环境的随机数生成器
            self.core_env.rng = np.random.RandomState(seed)

        # 调用 core 环境的 reset
        obs = self.core_env.reset()

        # 构建 info
        info = {
            'timestep': 0,
            'tasks_completed': 0,
            'deadline_miss': 0,
            'outage_steps': 0,
        }

        return obs, info

    def step(
        self,
        action: Any
    ) -> Tuple[Any, float, bool, bool, Dict[str, Any]]:
        """
        执行一步

        Args:
            action: 动作

        Returns:
            (observation, reward, terminated, truncated, info) 元组
            - observation: 新的观测
            - reward: 奖励
            - terminated: 是否因任务完成而结束
            - truncated: 是否因时间限制而结束
            - info: 额外信息字典
        """
        # 调用 core 环境的 step
        obs, reward, done, info = self.core_env.step(action)

        # 区分 terminated 和 truncated
        # terminated: 任务完成（当前版本不使用）
        # truncated: 到达 horizon
        terminated = False
        truncated = done  # done 表示到达 horizon

        # 返回标准 Gym 格式
        if GYMNASIUM:
            return obs, reward, terminated, truncated, info
        else:
            # gym (旧版本) 只有 done
            return obs, reward, done, info

    def render(self, mode: Optional[str] = None):
        """
        渲染环境

        Args:
            mode: 渲染模式 ('human', 'rgb_array', None)

        Returns:
            如果 mode='rgb_array'，返回 RGB 数组；否则返回 None
        """
        if mode is None:
            mode = self.render_mode

        if mode is None:
            return None

        # 简单实现：打印当前状态
        if mode == 'human':
            state = self.core_env.state
            print(f"Step {state.t}/{self.horizon_steps}")
            print(f"  Tasks completed: {state.tasks_completed}")
            print(f"  Active tasks: {len(state.get_active_tasks())}")
            print(f"  Deadline miss: {state.deadline_miss}")
            print(f"  Outage steps: {state.outage_steps}")
            return None

        elif mode == 'rgb_array':
            # TODO: 使用 visualizer 生成图像
            # 暂时返回空白图像
            return np.zeros((480, 640, 3), dtype=np.uint8)

        else:
            raise ValueError(f"Unsupported render mode: {mode}")

    def close(self):
        """关闭环境"""
        # 清理资源
        if self._renderer is not None:
            self._renderer = None

    @property
    def unwrapped(self):
        """返回未包装的环境"""
        return self.core_env
