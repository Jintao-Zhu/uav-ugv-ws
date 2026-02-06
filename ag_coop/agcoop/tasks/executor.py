"""
虚拟 UAV 执行器（Day4 简化版）

功能：
- 模拟 UAV 执行任务（不涉及真实运动）
- 使用 Chebyshev 距离估算飞行时间
- 自动选择和完成任务
- Day5 会替换为真实运动逻辑
"""

from typing import Optional, Tuple
from dataclasses import dataclass

from .task import Task
from .manager import TaskManager


def estimate_travel_time(
    uav_cell: Tuple[int, int],
    task_cell: Tuple[int, int],
    service_time: int = 2
) -> int:
    """
    估算 UAV 完成任务的总耗时

    Args:
        uav_cell: UAV 当前位置 (i, j)
        task_cell: 任务位置 (i, j)
        service_time: 到点服务时间（步数）

    Returns:
        总耗时（步数）= 飞行时间 + 服务时间

    Note:
        Day4 使用 Chebyshev 距离（max(|dx|, |dy|)）作为飞行时间
        Day5 会替换为真实路径规划 + 运动学
    """
    # Chebyshev 距离（8-连通最短路径）
    dx = abs(task_cell[1] - uav_cell[1])  # j 方向（x）
    dy = abs(task_cell[0] - uav_cell[0])  # i 方向（y）
    travel_time = max(dx, dy)

    return travel_time + service_time


@dataclass
class VirtualUAVExecutor:
    """
    虚拟 UAV 执行器（Day4 简化版）

    状态：
        uav_busy: UAV 是否正在执行任务
        current_task_id: 当前执行的任务 ID（None 表示空闲）
        remaining_time: 完成当前任务还需要的步数
        uav_cell: UAV 当前位置（虚拟，不真实移动）
        service_time: 到点服务时间（步数）
    """

    uav_cell: Tuple[int, int]  # UAV 当前位置
    service_time: int = 2       # 到点服务时间
    uav_busy: bool = False      # UAV 是否忙碌
    current_task_id: Optional[int] = None  # 当前任务 ID
    remaining_time: int = 0     # 剩余时间

    def step(
        self,
        t: int,
        task_manager: TaskManager,
        policy: str = "earliest_deadline"
    ) -> Optional[int]:
        """
        执行一步

        Args:
            t: 当前时刻
            task_manager: 任务管理器
            policy: 任务选择策略（"earliest_deadline", "random"）

        Returns:
            本步完成的任务 ID（如果有）
        """
        completed_task_id = None

        # 如果 UAV 正在执行任务
        if self.uav_busy:
            # 检查当前任务是否已过期
            task = task_manager.get_task(self.current_task_id)
            if task and task.status == "expired":
                # 任务已过期，放弃执行
                self.uav_busy = False
                self.current_task_id = None
                self.remaining_time = 0
            else:
                self.remaining_time -= 1

                # 任务完成
                if self.remaining_time <= 0:
                    # 再次检查任务状态（可能在最后一步过期）
                    task = task_manager.get_task(self.current_task_id)
                    if task and task.status != "expired":
                        # 标记任务完成
                        task_manager.mark_completed(self.current_task_id, t)
                        completed_task_id = self.current_task_id

                        # 更新 UAV 位置（虚拟移动到任务位置）
                        self.uav_cell = task.cell

                    # 重置状态
                    self.uav_busy = False
                    self.current_task_id = None
                    self.remaining_time = 0

        # 如果 UAV 空闲，尝试分配新任务
        if not self.uav_busy:
            # 获取 Top-M 任务
            top_tasks = task_manager.get_top_m(t, policy=policy)

            if top_tasks:
                # 选择第一个任务（按策略排序后的第一个）
                task = top_tasks[0]

                # 估算完成时间
                total_time = estimate_travel_time(
                    self.uav_cell,
                    task.cell,
                    self.service_time
                )

                # 分配任务
                task_manager.mark_assigned(task.id, t)

                # 更新状态
                self.uav_busy = True
                self.current_task_id = task.id
                self.remaining_time = total_time

        return completed_task_id

    def reset(self, initial_cell: Tuple[int, int]):
        """
        重置执行器

        Args:
            initial_cell: 初始位置
        """
        self.uav_cell = initial_cell
        self.uav_busy = False
        self.current_task_id = None
        self.remaining_time = 0

    def get_status(self) -> dict:
        """
        获取执行器状态

        Returns:
            状态字典
        """
        return {
            'uav_cell': self.uav_cell,
            'uav_busy': self.uav_busy,
            'current_task_id': self.current_task_id,
            'remaining_time': self.remaining_time,
        }
