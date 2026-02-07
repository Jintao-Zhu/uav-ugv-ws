"""
Space-Time A* 算法实现

为单个 agent 规划路径，考虑时间维度和预留约束。
"""

from typing import Tuple, List, Optional, Set
import heapq
from time import perf_counter

from .reservation import ReservationTable


class SpaceTimeAStar:
    """
    空间-时间 A* 算法

    状态：(cell, t)
    动作：{WAIT, UP, DOWN, LEFT, RIGHT}
    约束：
    - 地图障碍
    - Reservation Table 预留
    - 时间窗 H
    - 求解时间预算
    """

    def __init__(
        self,
        grid_map,
        reservation_table: ReservationTable,
        connectivity: int = 4
    ):
        """
        初始化 Space-Time A*

        Args:
            grid_map: 地图对象
            reservation_table: 预留表
            connectivity: 连通性（4 或 8 邻接）
        """
        self.grid_map = grid_map
        self.reservation_table = reservation_table
        self.connectivity = connectivity

        # 获取地图尺寸
        self.width = grid_map.width
        self.height = grid_map.height

    def get_neighbors(self, cell: Tuple[int, int]) -> List[Tuple[int, int]]:
        """
        获取邻居节点

        Args:
            cell: 当前位置 (x, y)

        Returns:
            邻居位置列表
        """
        x, y = cell
        neighbors = []

        # 4 邻接
        moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        # 8 邻接（如果需要）
        if self.connectivity == 8:
            moves += [(1, 1), (1, -1), (-1, 1), (-1, -1)]

        for dx, dy in moves:
            nx, ny = x + dx, y + dy

            # 检查边界
            if 0 <= nx < self.width and 0 <= ny < self.height:
                # 检查障碍
                if self.grid_map.is_free(nx, ny):
                    neighbors.append((nx, ny))

        return neighbors

    def heuristic(self, cell: Tuple[int, int], goal: Tuple[int, int]) -> float:
        """
        启发式函数（曼哈顿距离或切比雪夫距离）

        Args:
            cell: 当前位置
            goal: 目标位置

        Returns:
            启发式值
        """
        x1, y1 = cell
        x2, y2 = goal

        if self.connectivity == 4:
            # 曼哈顿距离
            return abs(x1 - x2) + abs(y1 - y2)
        else:
            # 切比雪夫距离
            return max(abs(x1 - x2), abs(y1 - y2))

    def search(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        H: int,
        agent_id: int = -1,
        time_budget_ms: float = 1000.0
    ) -> Tuple[Optional[List[Tuple[int, int]]], bool, int]:
        """
        执行 Space-Time A* 搜索

        Args:
            start: 起点 (x, y)
            goal: 终点 (x, y)
            H: 时间窗（最大时间步数）
            agent_id: agent ID（用于检查预留）
            time_budget_ms: 求解时间预算（毫秒）

        Returns:
            (path, timeout, expanded_nodes)
            - path: 路径（位置列表），如果失败则为 None
            - timeout: 是否超时
            - expanded_nodes: 展开的节点数
        """
        start_time = perf_counter()
        time_deadline = start_time + time_budget_ms / 1000.0

        # 统计展开节点数
        expanded_nodes = 0

        # 优先队列：(f, g, t, cell, parent)
        # f = g + h, g = 当前代价, t = 当前时刻
        open_list = []
        h_start = self.heuristic(start, goal)
        heapq.heappush(open_list, (h_start, 0, 0, start, None))

        # 已访问节点：(cell, t) -> (parent_cell, parent_t, g)
        visited = {}
        visited[(start, 0)] = (None, None, 0)

        # 记录到达目标的最早时刻和最佳路径
        best_goal_time = None
        best_goal_cost = None

        while open_list:
            # 检查超时
            if perf_counter() > time_deadline:
                return None, True, expanded_nodes

            f, g, t, cell, parent = heapq.heappop(open_list)

            # 跳过已经以更低代价访问过的状态
            current_state = (cell, t)
            if current_state in visited and g > visited[current_state][2]:
                continue

            # 展开节点计数
            expanded_nodes += 1

            # 检查是否到达目标
            if cell == goal:
                # 记录到达目标的时刻
                if best_goal_time is None or g < best_goal_cost:
                    best_goal_time = t
                    best_goal_cost = g

                # 如果已经到达时间窗 H，返回路径
                if t >= H:
                    path = self._reconstruct_path(visited, cell, t)
                    return path, False, expanded_nodes

            # 检查时间窗
            if t >= H:
                continue

            # 扩展邻居（包括 WAIT）
            # 1. WAIT 动作
            if self.reservation_table.is_move_valid(cell, cell, t, agent_id):
                next_state = (cell, t + 1)
                next_g = g + 1

                if next_state not in visited or next_g < visited[next_state][2]:
                    visited[next_state] = (cell, t, next_g)
                    next_h = self.heuristic(cell, goal)
                    next_f = next_g + next_h
                    heapq.heappush(open_list, (next_f, next_g, t + 1, cell, (cell, t)))

            # 2. 移动动作
            for neighbor in self.get_neighbors(cell):
                if self.reservation_table.is_move_valid(cell, neighbor, t, agent_id):
                    next_state = (neighbor, t + 1)
                    next_g = g + 1

                    if next_state not in visited or next_g < visited[next_state][2]:
                        visited[next_state] = (cell, t, next_g)
                        next_h = self.heuristic(neighbor, goal)
                        next_f = next_g + next_h
                        heapq.heappush(open_list, (next_f, next_g, t + 1, neighbor, (cell, t)))

        # 搜索结束，检查是否找到了目标
        if best_goal_time is not None:
            # 找到了目标，但没有到达 t=H
            # 重建到达目标的路径，然后在目标位置 WAIT 直到 H
            path = self._reconstruct_path(visited, goal, best_goal_time)

            # 从 best_goal_time 继续在目标位置 WAIT 直到 H
            # 需要检查每个 WAIT 步是否有效（是否被其他 agent 预留）
            current_t = best_goal_time
            while current_t < H:
                # 检查下一个时刻目标位置是否空闲
                if not self.reservation_table.is_move_valid(goal, goal, current_t, agent_id):
                    # 目标位置被占用，无法继续 WAIT
                    return None, False, expanded_nodes
                path.append(goal)
                current_t += 1

            return path, False, expanded_nodes

        # 未找到路径
        return None, False, expanded_nodes

    def _reconstruct_path(
        self,
        visited: dict,
        goal: Tuple[int, int],
        goal_t: int
    ) -> List[Tuple[int, int]]:
        """
        重建路径

        Args:
            visited: 已访问节点字典
            goal: 目标位置
            goal_t: 到达目标的时刻

        Returns:
            路径（位置列表）
        """
        path = []
        current_cell = goal
        current_t = goal_t

        while current_cell is not None:
            path.append(current_cell)
            parent_cell, parent_t, _ = visited[(current_cell, current_t)]
            current_cell = parent_cell
            current_t = parent_t

        path.reverse()
        return path
