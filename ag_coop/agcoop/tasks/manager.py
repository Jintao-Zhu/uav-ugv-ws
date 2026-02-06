"""
任务管理器（TaskManager）

功能：
- 管理任务池（active, assigned, done, expired）
- 提供 Top-M 任务选择（EDF, Random）
- 跟踪任务状态转换
- 统计任务完成情况
"""

from typing import List, Dict, Optional
import random

from .task import Task


class TaskManager:
    """
    任务管理器

    功能：
    - 管理任务池（按状态分类）
    - 提供 Top-M 任务选择
    - 跟踪任务状态转换
    - 统计任务完成情况
    """

    def __init__(self, max_active: int = 20, top_m: int = 5, seed: Optional[int] = None):
        """
        初始化任务管理器

        Args:
            max_active: 最大活跃任务数
            top_m: Top-M 任务数量
            seed: 随机种子（用于 Random 策略）
        """
        self.max_active = max_active
        self.top_m = top_m
        self.seed = seed

        # 任务池（按状态分类）
        self.tasks: Dict[int, Task] = {}  # 所有任务（id -> Task）
        self.active_ids: List[int] = []   # 活跃任务 ID
        self.assigned_ids: List[int] = [] # 已分配任务 ID
        self.done_ids: List[int] = []     # 已完成任务 ID
        self.expired_ids: List[int] = []  # 已过期任务 ID

        # 随机数生成器（用于 Random 策略）
        self.rng = random.Random(seed)

        # 统计信息
        self.total_added = 0
        self.total_completed = 0
        self.total_expired = 0
        self.total_tardiness = 0

    def add_task(self, task: Task) -> bool:
        """
        添加任务到任务池

        Args:
            task: 任务对象

        Returns:
            是否成功添加（False 表示容量满）
        """
        # 检查容量
        if len(self.active_ids) >= self.max_active:
            return False

        # 添加任务
        self.tasks[task.id] = task
        self.active_ids.append(task.id)
        self.total_added += 1

        return True

    def get_active_tasks(self) -> List[Task]:
        """
        获取所有活跃任务

        Returns:
            活跃任务列表
        """
        return [self.tasks[tid] for tid in self.active_ids]

    def get_assigned_tasks(self) -> List[Task]:
        """
        获取所有已分配任务

        Returns:
            已分配任务列表
        """
        return [self.tasks[tid] for tid in self.assigned_ids]

    def get_done_tasks(self) -> List[Task]:
        """
        获取所有已完成任务

        Returns:
            已完成任务列表
        """
        return [self.tasks[tid] for tid in self.done_ids]

    def get_expired_tasks(self) -> List[Task]:
        """
        获取所有已过期任务

        Returns:
            已过期任务列表
        """
        return [self.tasks[tid] for tid in self.expired_ids]

    @property
    def num_active(self) -> int:
        """活跃任务数量"""
        return len(self.active_ids)

    @property
    def num_assigned(self) -> int:
        """已分配任务数量"""
        return len(self.assigned_ids)

    @property
    def num_done(self) -> int:
        """已完成任务数量"""
        return len(self.done_ids)

    @property
    def num_expired(self) -> int:
        """已过期任务数量"""
        return len(self.expired_ids)

    def get_top_m(self, t: int, policy: str = "earliest_deadline") -> List[Task]:
        """
        获取 Top-M 任务

        Args:
            t: 当前时刻
            policy: 选择策略（"earliest_deadline", "random"）

        Returns:
            Top-M 任务列表（最多 top_m 个）
        """
        # 获取所有活跃任务
        active_tasks = self.get_active_tasks()

        if not active_tasks:
            return []

        # 根据策略排序
        if policy == "earliest_deadline":
            # EDF: 按 deadline 升序排序
            sorted_tasks = sorted(active_tasks, key=lambda task: task.deadline_t)
        elif policy == "random":
            # Random: 随机打乱
            sorted_tasks = active_tasks.copy()
            self.rng.shuffle(sorted_tasks)
        else:
            raise ValueError(f"Unknown policy: {policy}")

        # 返回前 top_m 个
        return sorted_tasks[:self.top_m]

    def mark_assigned(self, task_id: int, t: int):
        """
        标记任务为已分配

        Args:
            task_id: 任务 ID
            t: 当前时刻
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]

        # 状态转换：active -> assigned
        if task.status == "active":
            task.assign(t)
            self.active_ids.remove(task_id)
            self.assigned_ids.append(task_id)
        else:
            raise ValueError(f"Cannot assign task {task_id} in status {task.status}")

    def mark_completed(self, task_id: int, t: int):
        """
        标记任务为已完成

        Args:
            task_id: 任务 ID
            t: 当前时刻
        """
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")

        task = self.tasks[task_id]

        # 状态转换：active/assigned -> done
        if task.status == "active":
            self.active_ids.remove(task_id)
        elif task.status == "assigned":
            self.assigned_ids.remove(task_id)
        else:
            raise ValueError(f"Cannot complete task {task_id} in status {task.status}")

        task.complete(t)
        self.done_ids.append(task_id)

        # 更新统计
        self.total_completed += 1
        self.total_tardiness += task.tardiness

    def expire_overdue_tasks(self, t: int):
        """
        过期所有超过 deadline 的任务

        Args:
            t: 当前时刻
        """
        # 检查活跃任务
        expired_active = []
        for task_id in self.active_ids:
            task = self.tasks[task_id]
            if t >= task.deadline_t:
                expired_active.append(task_id)

        # 检查已分配任务
        expired_assigned = []
        for task_id in self.assigned_ids:
            task = self.tasks[task_id]
            if t >= task.deadline_t:
                expired_assigned.append(task_id)

        # 过期任务
        for task_id in expired_active:
            task = self.tasks[task_id]
            task.expire(t)
            self.active_ids.remove(task_id)
            self.expired_ids.append(task_id)
            self.total_expired += 1

        for task_id in expired_assigned:
            task = self.tasks[task_id]
            task.expire(t)
            self.assigned_ids.remove(task_id)
            self.expired_ids.append(task_id)
            self.total_expired += 1

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            统计信息字典
        """
        # 基础统计
        stats = {
            'total_added': self.total_added,
            'total_completed': self.total_completed,
            'total_expired': self.total_expired,
            'num_active': self.num_active,
            'num_assigned': self.num_assigned,
            'num_done': self.num_done,
            'num_expired': self.num_expired,
            'completion_rate': self.total_completed / max(1, self.total_added),
            'expiration_rate': self.total_expired / max(1, self.total_added),
            'total_tardiness': self.total_tardiness,
            'avg_tardiness': self.total_tardiness / max(1, self.total_completed),
        }

        # 完成时间分布
        done_tasks = self.get_done_tasks()
        if done_tasks:
            completion_times = [task.completed_t - task.release_t for task in done_tasks]
            stats['mean_completion_time'] = sum(completion_times) / len(completion_times)
            sorted_times = sorted(completion_times)
            p95_idx = int(len(sorted_times) * 0.95)
            stats['p95_completion_time'] = sorted_times[p95_idx] if p95_idx < len(sorted_times) else sorted_times[-1]
        else:
            stats['mean_completion_time'] = 0.0
            stats['p95_completion_time'] = 0.0

        # Slack 分析（deadline 松弛度）
        if done_tasks:
            slack_at_assignment = [task.deadline_t - task.assigned_t for task in done_tasks if task.assigned_t is not None]
            slack_at_completion = [task.deadline_t - task.completed_t for task in done_tasks]
            stats['mean_slack_at_assignment'] = sum(slack_at_assignment) / len(slack_at_assignment) if slack_at_assignment else 0.0
            stats['mean_slack_at_completion'] = sum(slack_at_completion) / len(slack_at_completion)
        else:
            stats['mean_slack_at_assignment'] = 0.0
            stats['mean_slack_at_completion'] = 0.0

        return stats

    def reset(self):
        """重置任务管理器"""
        self.tasks.clear()
        self.active_ids.clear()
        self.assigned_ids.clear()
        self.done_ids.clear()
        self.expired_ids.clear()

        self.rng = random.Random(self.seed)

        self.total_added = 0
        self.total_completed = 0
        self.total_expired = 0
        self.total_tardiness = 0

    def get_task(self, task_id: int) -> Optional[Task]:
        """
        获取任务对象

        Args:
            task_id: 任务 ID

        Returns:
            任务对象（如果存在）
        """
        return self.tasks.get(task_id)

    def has_task(self, task_id: int) -> bool:
        """
        检查任务是否存在

        Args:
            task_id: 任务 ID

        Returns:
            是否存在
        """
        return task_id in self.tasks
