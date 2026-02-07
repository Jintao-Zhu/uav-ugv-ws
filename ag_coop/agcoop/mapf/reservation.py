"""
Reservation Table 实现

用于 MAPF 规划中的碰撞检测和避免。
支持顶点预留（vertex reservation）和边预留（edge reservation）。
"""

from typing import Tuple, Set, Dict


class ReservationTable:
    """
    预留表，用于跟踪时空占用情况

    支持：
    - 顶点预留：某个 agent 在某个时刻占用某个位置
    - 边预留：某个 agent 在某个时刻从一个位置移动到另一个位置
    """

    def __init__(self):
        """初始化预留表"""
        # 顶点预留：(cell, t) -> agent_id
        self.vertex_reservations: Dict[Tuple[Tuple[int, int], int], int] = {}

        # 边预留：(u, v, t) -> agent_id
        # 表示 agent 在时刻 t 从 u 移动到 v（到达 v 的时刻是 t+1）
        self.edge_reservations: Dict[Tuple[Tuple[int, int], Tuple[int, int], int], int] = {}

    def reserve_vertex(self, cell: Tuple[int, int], t: int, agent_id: int = -1):
        """
        预留顶点

        Args:
            cell: 位置 (x, y)
            t: 时刻
            agent_id: agent ID（默认 -1 表示通用预留）
        """
        self.vertex_reservations[(cell, t)] = agent_id

    def reserve_edge(
        self,
        u: Tuple[int, int],
        v: Tuple[int, int],
        t: int,
        agent_id: int = -1
    ):
        """
        预留边

        Args:
            u: 起点 (x, y)
            v: 终点 (x, y)
            t: 时刻（从 u 出发的时刻，到达 v 的时刻是 t+1）
            agent_id: agent ID（默认 -1 表示通用预留）
        """
        self.edge_reservations[(u, v, t)] = agent_id

    def is_vertex_free(self, cell: Tuple[int, int], t: int, agent_id: int = -1) -> bool:
        """
        检查顶点是否空闲

        Args:
            cell: 位置 (x, y)
            t: 时刻
            agent_id: 当前 agent ID（用于排除自己的预留）

        Returns:
            True 如果空闲，False 如果被占用
        """
        key = (cell, t)
        if key not in self.vertex_reservations:
            return True

        # 如果被占用，检查是否是自己占用的
        occupier = self.vertex_reservations[key]
        return occupier == agent_id

    def is_edge_free(
        self,
        u: Tuple[int, int],
        v: Tuple[int, int],
        t: int,
        agent_id: int = -1
    ) -> bool:
        """
        检查边是否空闲（包括检查 swap 冲突）

        Args:
            u: 起点 (x, y)
            v: 终点 (x, y)
            t: 时刻（从 u 出发的时刻）
            agent_id: 当前 agent ID（用于排除自己的预留）

        Returns:
            True 如果空闲，False 如果被占用或有 swap 冲突
        """
        # 检查正向边 (u -> v, t)
        forward_key = (u, v, t)
        if forward_key in self.edge_reservations:
            occupier = self.edge_reservations[forward_key]
            if occupier != agent_id:
                return False

        # 检查反向边 (v -> u, t)，防止 swap 冲突
        # 如果有其他 agent 在同一时刻从 v 移动到 u，则会发生 swap
        reverse_key = (v, u, t)
        if reverse_key in self.edge_reservations:
            occupier = self.edge_reservations[reverse_key]
            if occupier != agent_id:
                return False

        return True

    def is_move_valid(
        self,
        u: Tuple[int, int],
        v: Tuple[int, int],
        t: int,
        agent_id: int = -1
    ) -> bool:
        """
        检查移动是否有效

        移动有效需要满足：
        1. 目标顶点在 t+1 时刻空闲
        2. 边 (u, v, t) 空闲（无 swap 冲突）

        Args:
            u: 起点 (x, y)
            v: 终点 (x, y)
            t: 时刻（从 u 出发的时刻）
            agent_id: 当前 agent ID

        Returns:
            True 如果移动有效，False 否则
        """
        # 检查目标顶点在 t+1 时刻是否空闲
        if not self.is_vertex_free(v, t + 1, agent_id):
            return False

        # 检查边是否空闲（包括 swap 检查）
        if not self.is_edge_free(u, v, t, agent_id):
            return False

        return True

    def reserve_move(
        self,
        u: Tuple[int, int],
        v: Tuple[int, int],
        t: int,
        agent_id: int = -1
    ):
        """
        预留一次移动（同时预留顶点和边）

        Args:
            u: 起点 (x, y)
            v: 终点 (x, y)
            t: 时刻（从 u 出发的时刻）
            agent_id: agent ID
        """
        # 预留目标顶点
        self.reserve_vertex(v, t + 1, agent_id)

        # 预留边（仅当不是 WAIT 时）
        if u != v:
            self.reserve_edge(u, v, t, agent_id)

    def reserve_path(self, path: list[Tuple[int, int]], agent_id: int = -1):
        """
        预留整条路径

        Args:
            path: 路径（位置列表）
            agent_id: agent ID
        """
        # 预留起点（t=0）
        if path:
            self.reserve_vertex(path[0], 0, agent_id)

        # 预留每一步移动
        for t in range(len(path) - 1):
            u = path[t]
            v = path[t + 1]
            self.reserve_move(u, v, t, agent_id)

    def clear(self):
        """清空所有预留"""
        self.vertex_reservations.clear()
        self.edge_reservations.clear()

    def clear_agent(self, agent_id: int):
        """
        清除某个 agent 的所有预留

        Args:
            agent_id: agent ID
        """
        # 清除顶点预留
        self.vertex_reservations = {
            k: v for k, v in self.vertex_reservations.items() if v != agent_id
        }

        # 清除边预留
        self.edge_reservations = {
            k: v for k, v in self.edge_reservations.items() if v != agent_id
        }

    def get_vertex_conflicts(self, cell: Tuple[int, int], t: int) -> Set[int]:
        """
        获取在指定位置和时刻的所有冲突 agent

        Args:
            cell: 位置
            t: 时刻

        Returns:
            冲突的 agent ID 集合
        """
        key = (cell, t)
        if key in self.vertex_reservations:
            return {self.vertex_reservations[key]}
        return set()

    def __repr__(self):
        return (f"ReservationTable("
                f"vertices={len(self.vertex_reservations)}, "
                f"edges={len(self.edge_reservations)})")
