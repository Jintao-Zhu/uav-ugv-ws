"""
AGCoop 环境核心：最小数据模型 (Day1)

定义系统状态、step 逻辑和基础指标。
Day1 版本：UGV 原地不动，UAV 永远在 0 号车上，任务生成简单随机。
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
import numpy as np


@dataclass
class Task:
    """任务数据结构"""
    task_id: int
    position: Tuple[float, float]  # (x, y)
    arrival_time: int
    deadline: int
    completed: bool = False
    completion_time: Optional[int] = None

    def is_overdue(self, current_time: int) -> bool:
        """检查任务是否超期"""
        return current_time > self.deadline

    def get_tardiness(self, current_time: int) -> int:
        """计算延迟时间（如果已完成）"""
        if self.completed and self.completion_time is not None:
            return max(0, self.completion_time - self.deadline)
        return 0


@dataclass
class SystemState:
    """系统状态（Day1 最简版本）"""
    t: int = 0  # 当前时间步
    ugv_positions: List[Tuple[float, float]] = field(default_factory=list)  # [(x,y)] * n_ugv
    uav_onboard_ugv_id: int = 0  # UAV 永远在 0 号车上（Day1）
    task_pool: List[Task] = field(default_factory=list)  # 任务池

    # 指标累计
    tasks_completed: int = 0
    outage_steps: int = 0
    deadline_miss: int = 0
    tardiness_sum: int = 0

    # 内部计数器
    _next_task_id: int = 0

    def add_task(self, position: Tuple[float, float], arrival_time: int, deadline: int) -> Task:
        """添加新任务到任务池"""
        task = Task(
            task_id=self._next_task_id,
            position=position,
            arrival_time=arrival_time,
            deadline=deadline
        )
        self.task_pool.append(task)
        self._next_task_id += 1
        return task

    def complete_task(self, task_id: int, completion_time: int) -> bool:
        """完成任务并更新指标"""
        for task in self.task_pool:
            if task.task_id == task_id and not task.completed:
                task.completed = True
                task.completion_time = completion_time
                self.tasks_completed += 1

                # 检查是否超期
                if completion_time > task.deadline:
                    self.deadline_miss += 1
                    self.tardiness_sum += (completion_time - task.deadline)

                return True
        return False

    def get_active_tasks(self) -> List[Task]:
        """获取未完成的任务"""
        return [task for task in self.task_pool if not task.completed]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志记录）"""
        return {
            't': self.t,
            'ugv_positions': self.ugv_positions,
            'uav_onboard_ugv_id': self.uav_onboard_ugv_id,
            'n_active_tasks': len(self.get_active_tasks()),
            'tasks_completed': self.tasks_completed,
            'outage_steps': self.outage_steps,
            'deadline_miss': self.deadline_miss,
            'tardiness_sum': self.tardiness_sum,
        }


class AGCoopEnv:
    """
    AGCoop 环境主类（Day1 最简版本）

    Day1 特性：
    - UGV 原地不动
    - UAV 永远在 0 号车上
    - 任务随机生成（可选）
    - 简单的任务完成规则（测试指标链路）
    """

    def __init__(self, config: Dict[str, Any]):
        """
        初始化环境

        Args:
            config: 配置字典，包含 episode, robots, tasks 等配置
        """
        self.config = config

        # 提取配置参数
        self.horizon_steps = config['episode']['horizon_steps']
        self.seed = config['episode']['seed']
        self.n_ugv = config['robots']['n_ugv']
        self.n_uav = config['robots']['n_uav']

        # 任务配置
        self.tasks_enabled = config['tasks']['enabled']
        self.arrival_rate = config['tasks']['arrival_rate']
        self.deadline_min = config['tasks']['deadline_min']
        self.deadline_max = config['tasks']['deadline_max']

        # 通信配置（Day1 占位）
        self.comm_enabled = config['comm']['enabled']

        # 初始化随机数生成器
        self.rng = np.random.RandomState(self.seed)

        # 状态
        self.state: Optional[SystemState] = None

        # Day1: 简单的地图边界（假设 100x100）
        self.map_width = 100.0
        self.map_height = 100.0

    def reset(self) -> SystemState:
        """
        重置环境到初始状态

        Returns:
            初始系统状态
        """
        # 重置随机数生成器（保证可复现）
        self.rng = np.random.RandomState(self.seed)

        # 初始化状态
        self.state = SystemState()
        self.state.t = 0

        # 初始化 UGV 位置（Day1: 所有 UGV 从原点开始）
        self.state.ugv_positions = [(0.0, 0.0) for _ in range(self.n_ugv)]

        # 初始化 UAV（永远在 0 号车上）
        self.state.uav_onboard_ugv_id = 0

        # 清空任务池
        self.state.task_pool = []

        # 重置指标
        self.state.tasks_completed = 0
        self.state.outage_steps = 0
        self.state.deadline_miss = 0
        self.state.tardiness_sum = 0
        self.state._next_task_id = 0

        return self.state

    def step(self, action: Optional[Any] = None) -> Tuple[SystemState, Dict[str, Any], bool, Dict[str, Any]]:
        """
        执行一步环境演化（Day1 最简版本）

        Args:
            action: 动作（Day1 不使用，占位）

        Returns:
            (state, reward, done, info) 元组
            - state: 新的系统状态
            - reward: 奖励（Day1 占位，返回 0）
            - done: 是否结束
            - info: 额外信息字典
        """
        if self.state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")

        # 时间步进
        self.state.t += 1

        # Day1: UGV 原地不动（不更新位置）
        # self.state.ugv_positions 保持不变

        # Day1: UAV 原地不动（永远在 0 号车上）
        # self.state.uav_onboard_ugv_id 保持为 0

        # 任务生成（可选）
        if self.tasks_enabled:
            self._generate_tasks()

        # 任务完成（Day1 简单规则：如果任务在 (0,0) 附近则立即完成）
        self._complete_tasks_simple()

        # 计算 outage（Day1: 简单随机，但可复现）
        self._update_outage()

        # 检查是否结束
        done = self.state.t >= self.horizon_steps

        # 构建返回信息
        reward = 0.0  # Day1 占位
        info = {
            'timestep': self.state.t,
            'tasks_completed': self.state.tasks_completed,
            'outage_steps': self.state.outage_steps,
            'deadline_miss': self.state.deadline_miss,
            'tardiness_sum': self.state.tardiness_sum,
            'active_tasks': len(self.state.get_active_tasks()),
        }

        return self.state, reward, done, info

    def _generate_tasks(self) -> None:
        """
        生成新任务（Day1 简单版本）

        按 arrival_rate 概率生成任务，位置随机，deadline 随机。
        """
        if self.rng.random() < self.arrival_rate:
            # 随机位置
            x = self.rng.uniform(0, self.map_width)
            y = self.rng.uniform(0, self.map_height)
            position = (x, y)

            # 随机 deadline
            deadline_offset = self.rng.randint(self.deadline_min, self.deadline_max + 1)
            deadline = self.state.t + deadline_offset

            # 添加任务
            self.state.add_task(position, self.state.t, deadline)

    def _complete_tasks_simple(self) -> None:
        """
        简单的任务完成规则（Day1 测试用）

        规则：如果任务位置在 (0,0) 附近（距离 < 5.0），则立即完成。
        这只是为了测试指标链路，Day2+ 会实现真实的任务完成逻辑。
        """
        completion_radius = 5.0

        for task in self.state.get_active_tasks():
            # 计算任务到 (0,0) 的距离
            dist = np.sqrt(task.position[0]**2 + task.position[1]**2)

            if dist < completion_radius:
                # 完成任务
                self.state.complete_task(task.task_id, self.state.t)

    def _update_outage(self) -> None:
        """
        更新 outage 指标（Day1 简单版本）

        Day1: 以 10% 概率发生 outage（可复现）
        Day2+ 会根据真实的通信模型计算。
        """
        if self.comm_enabled:
            # 简单随机 outage（10% 概率）
            if self.rng.random() < 0.1:
                self.state.outage_steps += 1
        # 如果 comm 未启用，outage 保持为 0

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取当前累计指标

        Returns:
            指标字典
        """
        if self.state is None:
            return {}

        return {
            'tasks_completed': self.state.tasks_completed,
            'outage_steps': self.state.outage_steps,
            'deadline_miss': self.state.deadline_miss,
            'tardiness_sum': self.state.tardiness_sum,
            'total_tasks': len(self.state.task_pool),
            'active_tasks': len(self.state.get_active_tasks()),
        }

    def render(self) -> str:
        """
        简单的文本渲染（Day1 版本）

        Returns:
            状态的文本表示
        """
        if self.state is None:
            return "Environment not initialized."

        lines = [
            f"=== AGCoop Environment (t={self.state.t}/{self.horizon_steps}) ===",
            f"UGV Positions: {self.state.ugv_positions}",
            f"UAV on UGV: {self.state.uav_onboard_ugv_id}",
            f"Active Tasks: {len(self.state.get_active_tasks())}",
            f"Metrics:",
            f"  - Tasks Completed: {self.state.tasks_completed}",
            f"  - Deadline Miss: {self.state.deadline_miss}",
            f"  - Tardiness Sum: {self.state.tardiness_sum}",
            f"  - Outage Steps: {self.state.outage_steps}",
        ]

        return "\n".join(lines)
