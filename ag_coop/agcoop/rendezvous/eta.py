"""
ETA (Estimated Time of Arrival) 估计模块

提供 UAV 和 UGV 到达会合点的时间估计，用于同步出发机制。
"""

from typing import Tuple
from ..map import GridMap
from ..planning import AStarPlanner


class ETAEstimator:
    """
    ETA 估计器

    提供统一的 ETA 估计接口，确保 UAV 和 UGV 的时间估计口径一致。
    """

    def __init__(self, grid_map: GridMap, uav_neighbor_mode: int = 8, ugv_neighbor_mode: int = 4):
        """
        初始化 ETA 估计器

        Args:
            grid_map: 地图对象
            uav_neighbor_mode: UAV 邻接模式（默认 8）
            ugv_neighbor_mode: UGV 邻接模式（默认 4）
        """
        self.grid_map = grid_map
        self.uav_neighbor_mode = uav_neighbor_mode
        self.ugv_neighbor_mode = ugv_neighbor_mode
        self.planner = AStarPlanner(grid_map)

    def estimate_uav_eta(
        self,
        uav_cell: Tuple[int, int],
        task_cell: Tuple[int, int],
        rendezvous_cell: Tuple[int, int],
        service_time: int
    ) -> int:
        """
        估计 UAV 到达会合点的时间

        UAV 路径: uav_cell -> task_cell (服务) -> rendezvous_cell

        Args:
            uav_cell: UAV 当前位置
            task_cell: 任务位置
            rendezvous_cell: 会合点位置
            service_time: 服务时间

        Returns:
            eta_uav: 估计到达时间（步数）
        """
        # 阶段 1: UAV -> 任务点
        dist_to_task = self._estimate_uav_distance(uav_cell, task_cell)

        # 阶段 2: 服务时间
        service = service_time

        # 阶段 3: 任务点 -> 会合点
        dist_to_rendezvous = self._estimate_uav_distance(task_cell, rendezvous_cell)

        eta_uav = dist_to_task + service + dist_to_rendezvous

        return eta_uav

    def estimate_ugv_eta(
        self,
        ugv_cell: Tuple[int, int],
        rendezvous_cell: Tuple[int, int]
    ) -> int:
        """
        估计 UGV 到达会合点的时间

        UGV 路径: ugv_cell -> rendezvous_cell

        Args:
            ugv_cell: UGV 当前位置
            rendezvous_cell: 会合点位置

        Returns:
            eta_ugv: 估计到达时间（步数）
        """
        eta_ugv = self._estimate_ugv_distance(ugv_cell, rendezvous_cell)
        return eta_ugv

    def _estimate_uav_distance(self, start: Tuple[int, int], goal: Tuple[int, int]) -> int:
        """
        估计 UAV 距离（使用 A* 或 Chebyshev 距离）

        Args:
            start: 起点
            goal: 终点

        Returns:
            distance: 估计距离（步数）
        """
        # 方法 1: 使用 A* 规划（更准确）
        path, success = self.planner.plan(start, goal, neighbor_mode=self.uav_neighbor_mode)
        if success and path:
            return len(path) - 1  # 路径长度 - 1 = 步数

        # 方法 2: 回退到 Chebyshev 距离（8 邻接的理论最短距离）
        return self._chebyshev_distance(start, goal)

    def _estimate_ugv_distance(self, start: Tuple[int, int], goal: Tuple[int, int]) -> int:
        """
        估计 UGV 距离（使用 A* 或 Manhattan 距离）

        Args:
            start: 起点
            goal: 终点

        Returns:
            distance: 估计距离（步数）
        """
        # 方法 1: 使用 A* 规划（更准确）
        path, success = self.planner.plan(start, goal, neighbor_mode=self.ugv_neighbor_mode)
        if success and path:
            return len(path) - 1  # 路径长度 - 1 = 步数

        # 方法 2: 回退到 Manhattan 距离（4 邻接的理论最短距离）
        return self._manhattan_distance(start, goal)

    def _chebyshev_distance(self, start: Tuple[int, int], goal: Tuple[int, int]) -> int:
        """Chebyshev 距离（8 邻接）"""
        i1, j1 = start
        i2, j2 = goal
        return max(abs(i1 - i2), abs(j1 - j2))

    def _manhattan_distance(self, start: Tuple[int, int], goal: Tuple[int, int]) -> int:
        """Manhattan 距离（4 邻接）"""
        i1, j1 = start
        i2, j2 = goal
        return abs(i1 - i2) + abs(j1 - j2)
