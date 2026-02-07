"""
A* 单机路径规划器

支持：
- 4 邻接（UGV）
- 8 邻接（UAV）
- 启发式函数：曼哈顿距离（4 邻接）或切比雪夫距离（8 邻接）
"""

import heapq
from typing import List, Tuple, Optional, Set


class AStarPlanner:
    """A* 单机路径规划器"""

    def __init__(self, grid_map):
        """
        初始化 A* 规划器

        Args:
            grid_map: GridMap 对象
        """
        self.grid_map = grid_map
        self.height = grid_map.height
        self.width = grid_map.width

    def plan(
        self,
        start: Tuple[int, int],
        goal: Tuple[int, int],
        neighbor_mode: int = 4,
        time_limit: Optional[int] = None
    ) -> Tuple[Optional[List[Tuple[int, int]]], bool]:
        """
        A* 路径规划

        Args:
            start: 起点 (i, j)
            goal: 终点 (i, j)
            neighbor_mode: 邻接模式（4 或 8）
            time_limit: 规划时间限制（节点扩展数量）

        Returns:
            path: 路径列表 [(i, j), ...] 或 None
            success: 是否成功
        """
        # 检查起点和终点是否合法
        if not self._is_valid(start) or not self._is_valid(goal):
            return None, False

        # 起点即终点
        if start == goal:
            return [start], True

        # 初始化
        open_set = []  # 优先队列：(f, g, cell, parent)
        closed_set: Set[Tuple[int, int]] = set()
        came_from = {}  # 记录路径
        g_score = {start: 0}

        # 启发式函数
        h_start = self._heuristic(start, goal, neighbor_mode)
        heapq.heappush(open_set, (h_start, 0, start, None))

        expanded = 0
        max_expansions = time_limit if time_limit else 10000

        while open_set and expanded < max_expansions:
            f, g, current, parent = heapq.heappop(open_set)

            # 已访问过
            if current in closed_set:
                continue

            # 记录父节点
            if parent is not None:
                came_from[current] = parent

            # 到达目标
            if current == goal:
                path = self._reconstruct_path(came_from, start, goal)
                return path, True

            closed_set.add(current)
            expanded += 1

            # 扩展邻居
            for neighbor in self._get_neighbors(current, neighbor_mode):
                if neighbor in closed_set:
                    continue

                tentative_g = g + 1

                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    g_score[neighbor] = tentative_g
                    h = self._heuristic(neighbor, goal, neighbor_mode)
                    f = tentative_g + h
                    heapq.heappush(open_set, (f, tentative_g, neighbor, current))

        # 规划失败
        return None, False

    def _is_valid(self, cell: Tuple[int, int]) -> bool:
        """检查格子是否合法（在地图内且不是障碍物）"""
        i, j = cell
        if not (0 <= i < self.height and 0 <= j < self.width):
            return False
        return self.grid_map.grid[i, j] == 0  # 0 表示自由空间

    def _get_neighbors(self, cell: Tuple[int, int], neighbor_mode: int) -> List[Tuple[int, int]]:
        """获取邻居格子"""
        i, j = cell
        neighbors = []

        if neighbor_mode == 4:
            # 4 邻接：上下左右
            deltas = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        elif neighbor_mode == 8:
            # 8 邻接：上下左右 + 对角线
            deltas = [
                (-1, 0), (1, 0), (0, -1), (0, 1),  # 上下左右
                (-1, -1), (-1, 1), (1, -1), (1, 1)  # 对角线
            ]
        else:
            raise ValueError(f"Unsupported neighbor_mode: {neighbor_mode}")

        for di, dj in deltas:
            ni, nj = i + di, j + dj
            if self._is_valid((ni, nj)):
                neighbors.append((ni, nj))

        return neighbors

    def _heuristic(self, cell: Tuple[int, int], goal: Tuple[int, int], neighbor_mode: int) -> float:
        """启发式函数"""
        i1, j1 = cell
        i2, j2 = goal

        if neighbor_mode == 4:
            # 曼哈顿距离（4 邻接）
            return abs(i1 - i2) + abs(j1 - j2)
        elif neighbor_mode == 8:
            # 切比雪夫距离（8 邻接）
            return max(abs(i1 - i2), abs(j1 - j2))
        else:
            raise ValueError(f"Unsupported neighbor_mode: {neighbor_mode}")

    def _reconstruct_path(
        self,
        came_from: dict,
        start: Tuple[int, int],
        goal: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """重建路径"""
        path = [goal]
        current = goal

        while current != start:
            current = came_from[current]
            path.append(current)

        path.reverse()
        return path
