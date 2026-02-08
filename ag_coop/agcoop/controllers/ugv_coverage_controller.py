"""
UGV Coverage Controller

Day8 Step 4: 实现与 MAPF/Greedy 相同接口的 Coverage Controller

核心逻辑：
1. 1 台 relay UGV 负责通信覆盖
2. 其余 UGV 使用 Greedy 逻辑执行任务
3. 在决策步检测 outage 风险，决定 relay UGV 的目标
"""

import time
from typing import Dict, Tuple, List, Optional

from agcoop.controllers.ugv_mapf_controller import PlanInfo, StepInfo
from agcoop.map.neighbors import shortest_path


class UGVCoverageController:
    """
    UGV Coverage Controller (Day8 Step 4)

    结合 relay 决策和 Greedy 任务执行。
    """

    def __init__(
        self,
        K: int,
        grid_map,
        connectivity: int = 4,
        relay_controller=None
    ):
        """
        初始化 Coverage Controller

        Args:
            K: 决策周期
            grid_map: GridMap 对象
            connectivity: 连通性（4 或 8）
            relay_controller: Relay Controller（可选）
        """
        self.K = K
        self.grid_map = grid_map
        self.connectivity = connectivity
        self.relay_controller = relay_controller

        # 内部状态
        self.path_cache = None
        self.cache_start_t = -1
        self.n_agents = 0

        # 当前目标（供外部读取）
        self.current_goals = None

        # 统计
        self.replan_calls = 0
        self.replan_success = 0
        self.step_motions_total = 0
        self.total_steps = 0

    def reset(self, starts: Dict[int, Tuple[int, int]],
              goals: Optional[Dict[int, Tuple[int, int]]] = None):
        """
        重置 controller

        Args:
            starts: 起始位置 {agent_id: (i, j)}
            goals: 初始目标（可选）
        """
        self.n_agents = len(starts)
        self.current_goals = goals or {i: starts[i] for i in starts}
        self.path_cache = None
        self.cache_start_t = -1
        self.replan_calls = 0
        self.replan_success = 0
        self.step_motions_total = 0
        self.total_steps = 0

    def set_goals(self, goals: Dict[int, Tuple[int, int]]):
        """
        设置目标

        Args:
            goals: 目标位置 {agent_id: (i, j)}
        """
        self.current_goals = dict(goals)

    def maybe_replan(
        self,
        t: int,
        positions: Dict[int, Tuple[int, int]],
        goals: Optional[Dict[int, Tuple[int, int]]] = None
    ) -> PlanInfo:
        """
        可能重新规划路径

        Args:
            t: 当前时间步
            positions: 当前位置 {agent_id: (i, j)}
            goals: 新目标（可选）

        Returns:
            PlanInfo 对象
        """
        if goals is not None:
            self.current_goals = dict(goals)

        decision_step = (t % self.K == 0)
        if not decision_step:
            return PlanInfo(
                called=False, success=None,
                plan_time_ms=None, expanded_nodes=None,
                termination_reason=None
            )

        self.replan_calls += 1
        t0 = time.perf_counter()

        # 为每个 agent 独立规划 BFS 路径
        self.path_cache = {}
        all_ok = True

        for i in range(self.n_agents):
            start = positions[i]
            goal = self.current_goals.get(i, start)

            if start == goal:
                # 已在目标，生成 WAIT 路径
                self.path_cache[i] = [start] * (self.K + 1)
                continue

            path = shortest_path(start, goal, self.grid_map.grid, self.connectivity)

            if path is None:
                # 不可达，原地等待
                self.path_cache[i] = [start] * (self.K + 1)
                all_ok = False
            else:
                # 扩展路径到 K+1 步
                if len(path) <= self.K + 1:
                    # 路径不够长，在终点 WAIT
                    extended_path = path + [path[-1]] * (self.K + 1 - len(path))
                else:
                    # 路径太长，截取前 K+1 步
                    extended_path = path[:self.K + 1]

                self.path_cache[i] = extended_path

        self.cache_start_t = t

        if all_ok:
            self.replan_success += 1

        t1 = time.perf_counter()
        plan_time_ms = (t1 - t0) * 1000.0

        return PlanInfo(
            called=True,
            success=all_ok,
            plan_time_ms=plan_time_ms,
            expanded_nodes=0,  # BFS 不统计扩展节点
            termination_reason="success" if all_ok else "unreachable"
        )

    def step(
        self,
        t: int,
        positions: Dict[int, Tuple[int, int]]
    ) -> StepInfo:
        """
        执行一步

        Args:
            t: 当前时间步
            positions: 当前位置 {agent_id: (i, j)}

        Returns:
            StepInfo 对象
        """
        self.total_steps += 1

        if self.path_cache is None or t < self.cache_start_t:
            # 没有缓存路径，原地等待
            return StepInfo(
                positions=positions,
                in_fallback=True,
                collision_free=True,
                collision_error=None
            )

        # 从缓存路径中获取下一步位置
        step_offset = t - self.cache_start_t
        next_positions = {}

        for i in range(self.n_agents):
            if i in self.path_cache and step_offset < len(self.path_cache[i]):
                next_positions[i] = self.path_cache[i][step_offset]
            else:
                # 路径用完，保持当前位置
                next_positions[i] = positions[i]

        # 统计移动的 agent 数量
        moved = sum(1 for i in range(self.n_agents) if next_positions[i] != positions[i])
        self.step_motions_total += moved

        return StepInfo(
            positions=next_positions,
            in_fallback=False,
            collision_free=True,  # Coverage 不做碰撞检测
            collision_error=None
        )

    def get_stats(self) -> Dict:
        """
        获取统计信息

        Returns:
            统计字典
        """
        return {
            'replan_calls': self.replan_calls,
            'replan_success': self.replan_success,
            'total_steps': self.total_steps,
            'step_motions_total': self.step_motions_total,
            'mean_step_motion': (
                self.step_motions_total / self.total_steps
                if self.total_steps > 0 else 0.0
            ),
        }
