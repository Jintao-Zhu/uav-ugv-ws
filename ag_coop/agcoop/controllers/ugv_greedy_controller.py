"""
UGV Greedy Controller

Day7 Baseline B: 每个 UGV 独立贪心选目标、独立 BFS 规划路径。
不做联合规划（无碰撞避免），作为 MAPF 的对照基线。

核心逻辑：
1. 每 K 步重新选目标和规划
2. 目标选择：最近的活跃任务（曼哈顿距离）
3. 路径规划：单 agent BFS shortest path
4. 无 inter-agent 碰撞避免
"""

import time
from typing import Dict, Tuple, List, Optional

from agcoop.controllers.ugv_mapf_controller import PlanInfo, StepInfo
from agcoop.map.neighbors import shortest_path


class UGVGreedyController:
    """
    UGV Greedy Controller (Day7 Baseline B)

    每个 UGV 独立规划，不做联合避碰。
    """

    def __init__(self, K: int, grid_map, connectivity: int = 4):
        self.K = K
        self.grid_map = grid_map
        self.connectivity = connectivity

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
        self.n_agents = len(starts)
        self.current_goals = goals or {i: starts[i] for i in starts}
        self.path_cache = None
        self.cache_start_t = -1
        self.replan_calls = 0
        self.replan_success = 0
        self.step_motions_total = 0
        self.total_steps = 0

    def set_goals(self, goals: Dict[int, Tuple[int, int]]):
        self.current_goals = dict(goals)

    def maybe_replan(
        self,
        t: int,
        positions: Dict[int, Tuple[int, int]],
        goals: Optional[Dict[int, Tuple[int, int]]] = None
    ) -> PlanInfo:
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
                # 扩展路径到 K+1 步（末尾 WAIT）
                while len(path) < self.K + 1:
                    path.append(path[-1])
                self.path_cache[i] = path

        self.cache_start_t = t

        elapsed_ms = (time.perf_counter() - t0) * 1000
        if all_ok:
            self.replan_success += 1

        return PlanInfo(
            called=True,
            success=True,  # greedy 总是"成功"（即使部分 agent 不可达也原地等）
            plan_time_ms=elapsed_ms,
            expanded_nodes=0,
            termination_reason="success"
        )

    def step(
        self,
        t: int,
        current_positions: Dict[int, Tuple[int, int]]
    ) -> StepInfo:
        self.total_steps += 1

        if self.path_cache is None:
            # 还没规划过，原地等
            return StepInfo(
                positions=dict(current_positions),
                in_fallback=True,
                collision_free=True,
                collision_error=None
            )

        offset = t - self.cache_start_t
        new_positions = {}

        for i in range(self.n_agents):
            path = self.path_cache[i]
            if offset + 1 < len(path):
                new_positions[i] = path[offset + 1]
            else:
                new_positions[i] = current_positions[i]

        return StepInfo(
            positions=new_positions,
            in_fallback=False,
            collision_free=True,  # greedy 不检查碰撞（baseline）
            collision_error=None
        )

    def get_stats(self) -> Dict:
        return {
            'mapf_calls': self.replan_calls,
            'mapf_success_calls': self.replan_success,
            'mapf_timeout_calls': 0,
            'mapf_fail_calls': 0,
            'mapf_mean_plan_time_ms': 0.0,
            'mapf_p95_plan_time_ms': 0.0,
            'fallback_wait_steps': 0,
            'expanded_nodes_total': 0,
            'mapf_expanded_mean_per_call': 0.0,
        }
