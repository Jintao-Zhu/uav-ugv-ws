"""
任务流生成器（TaskStream）

功能：
- 按照 Bernoulli 过程在线生成任务
- 可复现（相同 seed 生成相同任务序列）
- 支持任务池容量限制
"""

from typing import List, Optional, Tuple
import random
from dataclasses import dataclass

from .task import Task


@dataclass
class TaskConfig:
    """
    任务配置

    字段：
        enabled: 是否启用任务生成
        arrival_process: 到达过程类型（"bernoulli"）
        arrival_rate: 每步生成任务概率（0.0-1.0）
        deadline_min: 最小 deadline（步数）
        deadline_max: 最大 deadline（步数）
        max_active: 任务池最大容量
        top_m: Top-M 任务数量（用于策略）
        service_time: 到点服务时间（步数）
    """
    enabled: bool = True
    arrival_process: str = "bernoulli"
    arrival_rate: float = 0.2
    deadline_min: int = 25
    deadline_max: int = 60
    max_active: int = 20
    top_m: int = 5
    service_time: int = 2

    def __post_init__(self):
        """验证配置合法性"""
        assert self.arrival_process == "bernoulli", \
            f"Only 'bernoulli' arrival process is supported, got {self.arrival_process}"
        assert 0.0 <= self.arrival_rate <= 1.0, \
            f"arrival_rate must be in [0, 1], got {self.arrival_rate}"
        assert self.deadline_min > 0, \
            f"deadline_min must be > 0, got {self.deadline_min}"
        assert self.deadline_max >= self.deadline_min, \
            f"deadline_max ({self.deadline_max}) must be >= deadline_min ({self.deadline_min})"
        assert self.max_active > 0, \
            f"max_active must be > 0, got {self.max_active}"
        assert self.service_time > 0, \
            f"service_time must be > 0, got {self.service_time}"

    @classmethod
    def from_dict(cls, config: dict) -> 'TaskConfig':
        """从配置字典创建"""
        return cls(
            enabled=config.get('enabled', True),
            arrival_process=config.get('arrival_process', 'bernoulli'),
            arrival_rate=config.get('arrival_rate', 0.2),
            deadline_min=config.get('deadline_min', 25),
            deadline_max=config.get('deadline_max', 60),
            max_active=config.get('max_active', 20),
            top_m=config.get('top_m', 5),
            service_time=config.get('service_time', 2),
        )


class TaskStream:
    """
    任务流生成器

    功能：
    - 按照 Bernoulli 过程在线生成任务
    - 从 free_cells 中随机选择任务位置
    - 随机生成 deadline（在配置范围内）
    - 支持任务池容量限制
    - 可复现（相同 seed 生成相同任务序列）
    """

    def __init__(
        self,
        config: TaskConfig,
        free_cells: List[Tuple[int, int]],
        seed: Optional[int] = None
    ):
        """
        初始化任务流生成器

        Args:
            config: 任务配置
            free_cells: 可用格子列表 [(i, j), ...]
            seed: 随机种子（用于可复现）
        """
        self.config = config
        self.free_cells = free_cells
        self.seed = seed

        # 初始化随机数生成器（独立于全局 random）
        self.rng = random.Random(seed)

        # 任务计数器
        self.next_task_id = 0

        # 统计信息
        self.total_generated = 0
        self.total_dropped = 0  # 因容量满而丢弃的任务数

    def generate_tasks(self, t: int, current_active_count: int) -> List[Task]:
        """
        生成当前时刻的任务

        Args:
            t: 当前时刻（步数）
            current_active_count: 当前活跃任务数量

        Returns:
            新生成的任务列表（可能为空）
        """
        if not self.config.enabled:
            return []

        tasks = []

        # Bernoulli 过程：以概率 arrival_rate 生成 1 个任务
        if self.rng.random() < self.config.arrival_rate:
            # 检查任务池容量
            if current_active_count >= self.config.max_active:
                # 容量满，丢弃任务
                self.total_dropped += 1
                return []

            # 生成任务
            task = self._create_task(t)
            tasks.append(task)
            self.total_generated += 1

        return tasks

    def _create_task(self, t: int) -> Task:
        """
        创建单个任务

        Args:
            t: 当前时刻

        Returns:
            新任务
        """
        # 随机选择任务位置
        cell = self.rng.choice(self.free_cells)

        # 随机生成 deadline
        deadline_offset = self.rng.randint(
            self.config.deadline_min,
            self.config.deadline_max
        )
        deadline_t = t + deadline_offset

        # 创建任务
        task = Task(
            id=self.next_task_id,
            release_t=t,
            cell=cell,
            deadline_t=deadline_t
        )

        self.next_task_id += 1

        return task

    def reset(self):
        """重置生成器（用于新 episode）"""
        # 重置随机数生成器
        self.rng = random.Random(self.seed)

        # 重置计数器
        self.next_task_id = 0
        self.total_generated = 0
        self.total_dropped = 0

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        return {
            'total_generated': self.total_generated,
            'total_dropped': self.total_dropped,
            'drop_rate': self.total_dropped / max(1, self.total_generated + self.total_dropped),
        }
