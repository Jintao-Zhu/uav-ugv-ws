"""
MAPF 规划器接口

定义 MAPF 规划的输入输出接口，为后续集成做准备。
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from time import perf_counter

from .reservation import ReservationTable
from .astar import SpaceTimeAStar


@dataclass
class MAPFResult:
    """MAPF 规划结果"""
    success: bool  # 是否成功找到解
    paths: Dict[int, List[Tuple[int, int]]]  # agent_id -> path (list of (x, y))
    makespan: int  # 最大路径长度
    sum_of_costs: int  # 所有路径长度之和
    solve_time_ms: float  # 求解时间（毫秒）
    num_agents: int  # agent 数量
    timeout: bool = False  # 是否超时
    failure_reason: Optional[str] = None  # 失败原因（可选）
    expanded_total: int = 0  # 扩展节点总数（可选）

    def __repr__(self):
        if self.success:
            return (f"MAPFResult(success={self.success}, "
                    f"num_agents={self.num_agents}, "
                    f"makespan={self.makespan}, "
                    f"sum_of_costs={self.sum_of_costs}, "
                    f"solve_time_ms={self.solve_time_ms:.2f})")
        else:
            return (f"MAPFResult(success={self.success}, "
                    f"num_agents={self.num_agents}, "
                    f"timeout={self.timeout}, "
                    f"failure_reason={self.failure_reason}, "
                    f"solve_time_ms={self.solve_time_ms:.2f})")


class MAPFPlanner:
    """
    MAPF 规划器接口

    Day6 Step 0: 冻结接口定义
    - 输入：starts, goals, H, time_budget_ms, priority_order, fixed_reservations
    - 输出：MAPFResult

    后续步骤将实现具体的 MAPF 算法（CBS/ECBS）
    """

    def __init__(
        self,
        grid_map,
        connectivity: int = 4,
        time_budget_ms: int = 1000
    ):
        """
        初始化 MAPF 规划器

        Args:
            grid_map: 地图对象
            connectivity: 连通性（4 或 8 邻接）
            time_budget_ms: 求解时间预算（毫秒）
        """
        self.grid_map = grid_map
        self.connectivity = connectivity
        self.time_budget_ms = time_budget_ms

    def plan_mapf(
        self,
        starts: Dict[int, Tuple[int, int]],
        goals: Dict[int, Tuple[int, int]],
        H: int,
        priority_order: Optional[List[int]] = None,
        fixed_reservations: Optional[Dict[int, List[Tuple[int, int]]]] = None
    ) -> MAPFResult:
        """
        规划 MAPF 路径（使用优先级 MAPF / WHCA*）

        Args:
            starts: agent_id -> start_position (x, y)
            goals: agent_id -> goal_position (x, y)
            H: 规划时间窗（步数）
            priority_order: agent 优先级顺序（可选，用于 prioritized planning）
            fixed_reservations: agent_id -> reserved_path（可选，固定某些 agent 的路径）

        Returns:
            MAPFResult: 规划结果
        """
        start_time = perf_counter()
        num_agents = len(starts)

        # 如果没有指定优先级顺序，使用默认顺序
        if priority_order is None:
            priority_order = sorted(starts.keys())

        # 初始化 Reservation Table
        reservation_table = ReservationTable()

        # 如果有固定预留，先添加到 reservation table
        if fixed_reservations:
            for agent_id, path in fixed_reservations.items():
                reservation_table.reserve_path(path, agent_id)

        # 初始化 Space-Time A*
        astar = SpaceTimeAStar(
            grid_map=self.grid_map,
            reservation_table=reservation_table,
            connectivity=self.connectivity
        )

        # 存储规划结果
        paths = {}
        expanded_total = 0  # 累积展开节点数

        # 按优先级顺序为每个 agent 规划路径
        for agent_id in priority_order:
            # 跳过已有固定路径的 agent
            if fixed_reservations and agent_id in fixed_reservations:
                paths[agent_id] = fixed_reservations[agent_id]
                continue

            start = starts[agent_id]
            goal = goals[agent_id]

            # 计算剩余时间预算
            elapsed_ms = (perf_counter() - start_time) * 1000
            remaining_budget = self.time_budget_ms - elapsed_ms

            if remaining_budget <= 0:
                # 超时
                solve_time_ms = (perf_counter() - start_time) * 1000
                return MAPFResult(
                    success=False,
                    paths=paths,
                    makespan=0,
                    sum_of_costs=0,
                    solve_time_ms=solve_time_ms,
                    num_agents=num_agents,
                    timeout=True,
                    failure_reason="timeout",
                    expanded_total=expanded_total
                )

            # 为当前 agent 规划路径
            path, timeout, expanded_nodes = astar.search(
                start=start,
                goal=goal,
                H=H,
                agent_id=agent_id,
                time_budget_ms=remaining_budget
            )

            # 累积展开节点数
            expanded_total += expanded_nodes

            if timeout:
                # 超时
                solve_time_ms = (perf_counter() - start_time) * 1000
                return MAPFResult(
                    success=False,
                    paths=paths,
                    makespan=0,
                    sum_of_costs=0,
                    solve_time_ms=solve_time_ms,
                    num_agents=num_agents,
                    timeout=True,
                    failure_reason="timeout",
                    expanded_total=expanded_total
                )

            if path is None:
                # 未找到路径
                solve_time_ms = (perf_counter() - start_time) * 1000
                return MAPFResult(
                    success=False,
                    paths=paths,
                    makespan=0,
                    sum_of_costs=0,
                    solve_time_ms=solve_time_ms,
                    num_agents=num_agents,
                    timeout=False,
                    failure_reason="no_path",
                    expanded_total=expanded_total
                )

            # 成功找到路径，添加到结果并预留
            paths[agent_id] = path
            reservation_table.reserve_path(path, agent_id)

        # 所有 agent 都成功规划
        solve_time_ms = (perf_counter() - start_time) * 1000

        # 计算 makespan 和 sum_of_costs
        makespan = max(len(path) for path in paths.values()) if paths else 0
        sum_of_costs = sum(len(path) for path in paths.values())

        return MAPFResult(
            success=True,
            paths=paths,
            makespan=makespan,
            sum_of_costs=sum_of_costs,
            solve_time_ms=solve_time_ms,
            num_agents=num_agents,
            timeout=False,
            failure_reason=None,
            expanded_total=expanded_total
        )

    def validate_solution(
        self,
        paths: Dict[int, List[Tuple[int, int]]]
    ) -> Tuple[bool, Optional[str]]:
        """
        验证 MAPF 解的正确性

        Args:
            paths: agent_id -> path

        Returns:
            (is_valid, error_message)
        """
        # 检查碰撞
        # 1. Vertex collision: 同一时刻两个 agent 在同一位置
        # 2. Edge collision: 两个 agent 交换位置

        if not paths:
            return True, None

        max_len = max(len(path) for path in paths.values())

        for t in range(max_len):
            # 获取所有 agent 在时刻 t 的位置
            positions_at_t = {}
            for agent_id, path in paths.items():
                if t < len(path):
                    pos = path[t]
                else:
                    # agent 已到达目标，停留在最后位置
                    pos = path[-1]

                # 检查 vertex collision
                if pos in positions_at_t.values():
                    other_agent = [aid for aid, p in positions_at_t.items() if p == pos][0]
                    return False, f"Vertex collision at t={t}: agent {agent_id} and {other_agent} at {pos}"

                positions_at_t[agent_id] = pos

            # 检查 edge collision
            if t > 0:
                for agent_id, path in paths.items():
                    if t < len(path):
                        prev_pos = path[t-1]
                        curr_pos = path[t]
                    else:
                        continue

                    # 检查是否有其他 agent 从 curr_pos 移动到 prev_pos（交换位置）
                    for other_id, other_path in paths.items():
                        if other_id == agent_id:
                            continue

                        if t < len(other_path):
                            other_prev = other_path[t-1]
                            other_curr = other_path[t]

                            if prev_pos == other_curr and curr_pos == other_prev:
                                return False, f"Edge collision at t={t}: agent {agent_id} and {other_id} swap positions"

        return True, None
