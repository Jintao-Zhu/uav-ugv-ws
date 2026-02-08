"""
任务跟踪器

从 tasks.json 加载任务信息，并提供按时间查询的接口
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import json


class Task:
    """任务数据"""

    def __init__(self, task_dict: Dict[str, Any]):
        self.id = task_dict['id']
        self.cell = tuple(task_dict['cell'])  # (row, col)
        self.release_t = task_dict['release_t']
        self.deadline_t = task_dict['deadline_t']
        self.completed_t = task_dict.get('completed_t')
        self.status = task_dict['status']

    def is_active(self, t: int) -> bool:
        """任务在时刻 t 是否活跃（已发布但未完成）"""
        if t < self.release_t:
            return False
        if self.completed_t is not None and t >= self.completed_t:
            return False
        if t > self.deadline_t:
            return False
        return True

    def is_completed_at(self, t: int) -> bool:
        """任务在时刻 t 是否刚完成（用于显示完成动画）"""
        return self.completed_t == t

    def is_missed(self, t: int) -> bool:
        """任务在时刻 t 是否已过期未完成"""
        return t > self.deadline_t and self.completed_t is None

    def time_to_deadline(self, t: int) -> int:
        """距离 deadline 的剩余时间"""
        return self.deadline_t - t

    def __repr__(self):
        return (
            f"Task(id={self.id}, cell={self.cell}, "
            f"release={self.release_t}, deadline={self.deadline_t}, "
            f"status={self.status})"
        )


class TaskTracker:
    """任务跟踪器"""

    def __init__(self, tasks: List[Task]):
        self.tasks = tasks
        self.tasks_by_id = {task.id: task for task in tasks}

    def get_active_tasks(self, t: int) -> List[Task]:
        """获取时刻 t 的活跃任务"""
        return [task for task in self.tasks if task.is_active(t)]

    def get_completed_tasks(self, t: int, window: int = 5) -> List[Task]:
        """获取最近完成的任务（用于显示完成动画）"""
        return [
            task for task in self.tasks
            if task.completed_t is not None
            and t - window < task.completed_t <= t
        ]

    def get_missed_tasks(self, t: int) -> List[Task]:
        """获取已过期未完成的任务"""
        return [task for task in self.tasks if task.is_missed(t)]

    def get_task_color_urgency(self, task: Task, t: int) -> float:
        """
        计算任务的紧急度（0-1），用于颜色映射

        Returns:
            0.0 = 不紧急（距离 deadline 很远）
            1.0 = 非常紧急（接近 deadline）
        """
        slack = task.time_to_deadline(t)
        if slack <= 0:
            return 1.0
        # 假设 30 步以上都算不紧急
        max_slack = 30
        urgency = 1.0 - min(slack / max_slack, 1.0)
        return urgency

    def __repr__(self):
        return f"TaskTracker(n_tasks={len(self.tasks)})"


def load_tasks(run_dir: str) -> Optional[TaskTracker]:
    """
    从 tasks.json 加载任务信息

    Args:
        run_dir: 输出目录路径

    Returns:
        TaskTracker 对象，如果文件不存在返回 None
    """
    tasks_file = Path(run_dir) / "tasks.json"
    if not tasks_file.exists():
        return None

    with open(tasks_file, 'r') as f:
        data = json.load(f)

    tasks = [Task(task_dict) for task_dict in data['tasks']]
    return TaskTracker(tasks)
