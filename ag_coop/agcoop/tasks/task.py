"""
任务（Task）数据结构

定义：
- 任务在 release_t 时刻到达
- 必须在 deadline_t 之前完成
- 由 UGV 访问指定的 cell 来完成
"""

from dataclasses import dataclass, asdict
from typing import Optional, Tuple
import json


@dataclass
class Task:
    """
    任务数据结构

    字段：
        id: 任务唯一标识符
        release_t: 任务到达时刻（步数）
        cell: 任务位置（格子坐标，(i, j) 格式，i=row, j=col）
        deadline_t: 任务截止时刻（步数）
        assigned_t: 任务分配时刻（None 表示未分配）
        completed_t: 任务完成时刻（None 表示未完成）
        status: 任务状态（"active", "assigned", "done", "expired"）
        tardiness: 延迟时间（max(0, completed_t - deadline_t)，完成后填充）

    状态转换：
        active -> assigned -> done
        active -> expired（超过 deadline 未完成）
        assigned -> expired（超过 deadline 未完成）

    坐标约定：
        cell = (i, j)，其中 i=row(y), j=col(x)
        与项目其他部分保持一致
    """

    id: int
    release_t: int
    cell: Tuple[int, int]  # (i, j) = (row, col)
    deadline_t: int
    assigned_t: Optional[int] = None
    completed_t: Optional[int] = None
    status: str = "active"  # "active", "assigned", "done", "expired"
    tardiness: int = 0

    def __post_init__(self):
        """验证字段合法性"""
        assert self.deadline_t > self.release_t, \
            f"deadline_t ({self.deadline_t}) must be > release_t ({self.release_t})"
        assert self.status in ["active", "assigned", "done", "expired"], \
            f"Invalid status: {self.status}"
        assert len(self.cell) == 2, f"cell must be (i, j) tuple, got {self.cell}"

    def assign(self, t: int):
        """
        分配任务

        Args:
            t: 当前时刻
        """
        assert self.status == "active", f"Cannot assign task in status {self.status}"
        self.assigned_t = t
        self.status = "assigned"

    def complete(self, t: int):
        """
        完成任务

        Args:
            t: 当前时刻
        """
        assert self.status in ["active", "assigned"], \
            f"Cannot complete task in status {self.status}"
        self.completed_t = t
        self.status = "done"
        self.tardiness = max(0, t - self.deadline_t)

    def expire(self, t: int):
        """
        任务过期（超过 deadline 未完成）

        Args:
            t: 当前时刻
        """
        assert self.status in ["active", "assigned"], \
            f"Cannot expire task in status {self.status}"
        assert t >= self.deadline_t, \
            f"Cannot expire task before deadline (t={t}, deadline={self.deadline_t})"
        self.status = "expired"

    def is_active(self) -> bool:
        """任务是否处于活跃状态（可被分配）"""
        return self.status == "active"

    def is_assigned(self) -> bool:
        """任务是否已分配"""
        return self.status == "assigned"

    def is_done(self) -> bool:
        """任务是否已完成"""
        return self.status == "done"

    def is_expired(self) -> bool:
        """任务是否已过期"""
        return self.status == "expired"

    def time_to_deadline(self, t: int) -> int:
        """
        距离 deadline 的剩余时间

        Args:
            t: 当前时刻

        Returns:
            剩余时间（步数），负数表示已过期
        """
        return self.deadline_t - t

    def to_dict(self) -> dict:
        """
        转换为字典（用于 JSON 序列化）

        Returns:
            字典表示
        """
        return {
            'id': self.id,
            'release_t': self.release_t,
            'cell': list(self.cell),  # 转为 list 以便 JSON 序列化
            'deadline_t': self.deadline_t,
            'assigned_t': self.assigned_t,
            'completed_t': self.completed_t,
            'status': self.status,
            'tardiness': self.tardiness,
        }

    def to_json(self) -> str:
        """
        转换为 JSON 字符串

        Returns:
            JSON 字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        """
        从字典创建 Task

        Args:
            data: 字典数据

        Returns:
            Task 对象
        """
        # 将 cell 从 list 转回 tuple
        data = data.copy()
        if isinstance(data['cell'], list):
            data['cell'] = tuple(data['cell'])
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'Task':
        """
        从 JSON 字符串创建 Task

        Args:
            json_str: JSON 字符串

        Returns:
            Task 对象
        """
        data = json.loads(json_str)
        return cls.from_dict(data)

    def __repr__(self) -> str:
        """字符串表示"""
        return (
            f"Task(id={self.id}, "
            f"release_t={self.release_t}, "
            f"cell={self.cell}, "
            f"deadline_t={self.deadline_t}, "
            f"status={self.status})"
        )
