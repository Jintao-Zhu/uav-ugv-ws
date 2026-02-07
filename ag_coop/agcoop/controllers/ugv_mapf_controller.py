"""
UGV Receding Horizon MAPF Controller

将 Day6 test_mapf_integration.py 中的 controller 逻辑抽取为可复用类。

核心机制（来自 Day6）：
1. 每 K 步规划
2. 缓存执行
3. 失败 WAIT
4. 在线碰撞检查
5. 动态目标切换

关键细节：
- Goal filling：到达目标后自动填充 WAIT 到 H+1（由 Space-Time A* 保证）
- Fallback：失败后 WAIT K 步
- 碰撞检测：vertex collision + edge swap
"""

from typing import Dict, Tuple, List, Optional
from dataclasses import dataclass

from agcoop.mapf import UGVMAPFWrapper, UGVMAPFResult


@dataclass
class PlanInfo:
    """规划信息"""
    called: bool                    # 是否调用了 MAPF
    success: Optional[bool]         # 是否成功（None 表示未调用）
    plan_time_ms: Optional[float]   # 规划时间（None 表示未调用）
    expanded_nodes: Optional[int]   # 展开节点数（None 表示未调用）
    termination_reason: Optional[str]  # 终止原因（None 表示未调用）


@dataclass
class StepInfo:
    """单步执行信息"""
    positions: Dict[int, Tuple[int, int]]  # 新位置
    in_fallback: bool                       # 是否在 fallback 状态
    collision_free: bool                    # 是否无碰撞
    collision_error: Optional[str]          # 碰撞错误信息


class UGVRecedingHorizonMAPFController:
    """
    UGV Receding Horizon MAPF Controller

    实现 Day6 的 receding horizon 控制逻辑：
    - 每 K 步调用 MAPF 规划
    - 缓存路径并执行
    - 失败时 fallback WAIT K 步
    - 在线碰撞检测
    - 支持动态目标切换
    """

    def __init__(
        self,
        K: int,
        H: int,
        budget_ms: int,
        wrapper: UGVMAPFWrapper,
        enable_collision_check: bool = True
    ):
        """
        初始化 Controller

        Args:
            K: 重规划周期（步数）
            H: 规划时间窗（步数）
            budget_ms: MAPF 时间预算（毫秒）
            wrapper: UGV MAPF Wrapper
            enable_collision_check: 是否启用在线碰撞检测
        """
        self.K = K
        self.H = H
        self.budget_ms = budget_ms
        self.wrapper = wrapper
        self.enable_collision_check = enable_collision_check

        # 内部状态
        self.path_cache = None  # Dict[int, List[Tuple[int, int]]]
        self.cache_start_t = -1
        self.fallback_wait_remaining = 0

        # 统计信息
        self.mapf_calls = 0
        self.mapf_success_calls = 0
        self.mapf_timeout_calls = 0
        self.mapf_fail_calls = 0
        self.mapf_plan_times = []
        self.expanded_nodes_total = 0
        self.fallback_wait_steps = 0

        # 当前状态
        self.current_goals = None
        self.n_agents = 0

    def reset(
        self,
        starts: Dict[int, Tuple[int, int]],
        goals: Dict[int, Tuple[int, int]]
    ):
        """
        重置 controller 状态

        Args:
            starts: 初始位置
            goals: 初始目标
        """
        self.n_agents = len(starts)
        self.current_goals = dict(goals)

        # 清空缓存
        self.path_cache = None
        self.cache_start_t = -1
        self.fallback_wait_remaining = 0

        # 重置统计
        self.mapf_calls = 0
        self.mapf_success_calls = 0
        self.mapf_timeout_calls = 0
        self.mapf_fail_calls = 0
        self.mapf_plan_times = []
        self.expanded_nodes_total = 0
        self.fallback_wait_steps = 0

    def set_goals(self, goals: Dict[int, Tuple[int, int]]):
        """
        设置新目标（支持动态目标切换）

        Args:
            goals: 新目标
        """
        self.current_goals = dict(goals)

    def maybe_replan(
        self,
        t: int,
        starts: Dict[int, Tuple[int, int]],
        goals: Optional[Dict[int, Tuple[int, int]]] = None
    ) -> PlanInfo:
        """
        判断是否需要重规划，如果需要则调用 MAPF

        Args:
            t: 当前时间步
            starts: 当前位置
            goals: 目标位置（None 则使用 current_goals）

        Returns:
            PlanInfo: 规划信息
        """
        # 使用提供的 goals 或当前 goals
        if goals is not None:
            self.current_goals = dict(goals)

        # 判断是否是决策步
        # 标准 Receding Horizon: t=1 立即规划，然后每 K 步重新规划
        # 即 t=1, 1+K, 1+2K, 1+3K, ... = 1, 6, 11, 16, ... (K=5)
        decision_step = ((t - 1) % self.K == 0)

        # 如果在 fallback 状态且是决策步，清零 fallback（准备重新规划）
        if decision_step and self.fallback_wait_remaining > 0:
            self.fallback_wait_remaining = 0

        if not decision_step:
            # 不是决策步
            return PlanInfo(
                called=False,
                success=None,
                plan_time_ms=None,
                expanded_nodes=None,
                termination_reason=None
            )

        # 调用 MAPF 规划
        self.mapf_calls += 1

        result = self.wrapper.plan(
            starts=starts,
            goals=self.current_goals,
            H=self.H,
            budget_ms=self.budget_ms
        )

        # 记录统计
        self.mapf_plan_times.append(result.plan_time_ms)
        self.expanded_nodes_total += result.expanded_nodes

        if result.success:
            # 成功：缓存路径
            self.path_cache = result.paths
            self.cache_start_t = t
            self.mapf_success_calls += 1

            return PlanInfo(
                called=True,
                success=True,
                plan_time_ms=result.plan_time_ms,
                expanded_nodes=result.expanded_nodes,
                termination_reason="success"
            )
        else:
            # 失败：触发 fallback
            self.fallback_wait_remaining = self.K
            self.path_cache = None

            if result.termination_reason == "timeout":
                self.mapf_timeout_calls += 1
            else:
                self.mapf_fail_calls += 1

            return PlanInfo(
                called=True,
                success=False,
                plan_time_ms=result.plan_time_ms,
                expanded_nodes=result.expanded_nodes,
                termination_reason=result.termination_reason
            )

    def step(
        self,
        t: int,
        current_positions: Dict[int, Tuple[int, int]]
    ) -> StepInfo:
        """
        执行一步

        Args:
            t: 当前时间步
            current_positions: 当前位置

        Returns:
            StepInfo: 执行信息（包含新位置）
        """
        prev_positions = dict(current_positions)

        # 判断是否在 fallback 状态
        in_fallback = (self.fallback_wait_remaining > 0)

        if in_fallback:
            # Fallback WAIT：位置不变
            self.fallback_wait_remaining -= 1
            self.fallback_wait_steps += 1
            new_positions = dict(current_positions)
        else:
            # 执行缓存路径
            if self.path_cache is None:
                raise RuntimeError(f"t={t}: 没有缓存路径但不在 fallback 状态")

            offset = t - self.cache_start_t

            # 检查 offset 是否越界
            # 注意：由于 goal filling，所有路径长度应该是 H+1
            first_path_len = len(list(self.path_cache.values())[0])
            if offset + 1 >= first_path_len:
                raise RuntimeError(
                    f"t={t}: offset={offset} 越界 (path_len={first_path_len}, H={self.H})"
                )

            # 更新位置
            new_positions = {}
            for agent_id in range(self.n_agents):
                new_positions[agent_id] = self.path_cache[agent_id][offset + 1]

        # 在线碰撞检测
        collision_free = True
        collision_error = None

        if self.enable_collision_check:
            collision_free, collision_error = self._check_collision(
                new_positions,
                prev_positions,
                t
            )

        return StepInfo(
            positions=new_positions,
            in_fallback=in_fallback,
            collision_free=collision_free,
            collision_error=collision_error
        )

    def _check_collision(
        self,
        positions: Dict[int, Tuple[int, int]],
        prev_positions: Dict[int, Tuple[int, int]],
        t: int
    ) -> Tuple[bool, Optional[str]]:
        """
        在线碰撞检测

        Args:
            positions: 当前位置
            prev_positions: 上一步位置
            t: 当前时间步

        Returns:
            (collision_free, error_message)
        """
        # 检查 vertex collision
        for i in range(self.n_agents):
            for j in range(i + 1, self.n_agents):
                if positions[i] == positions[j]:
                    return False, f"Vertex collision at t={t}: agent {i} and {j} at {positions[i]}"

        # 检查 edge collision (swap)
        for i in range(self.n_agents):
            for j in range(i + 1, self.n_agents):
                if positions[i] == prev_positions[j] and positions[j] == prev_positions[i]:
                    return False, f"Edge collision at t={t}: agent {i} and {j} swap positions"

        return True, None

    def get_stats(self) -> Dict:
        """
        获取统计信息

        Returns:
            统计字典
        """
        mapf_mean_plan_time_ms = (
            sum(self.mapf_plan_times) / len(self.mapf_plan_times)
            if self.mapf_plan_times else 0
        )

        mapf_plan_times_sorted = sorted(self.mapf_plan_times)
        mapf_p95_plan_time_ms = (
            mapf_plan_times_sorted[int(len(mapf_plan_times_sorted) * 0.95)]
            if mapf_plan_times_sorted else 0
        )

        mapf_expanded_mean_per_call = (
            self.expanded_nodes_total / self.mapf_calls
            if self.mapf_calls > 0 else 0
        )

        return {
            'mapf_calls': self.mapf_calls,
            'mapf_success_calls': self.mapf_success_calls,
            'mapf_timeout_calls': self.mapf_timeout_calls,
            'mapf_fail_calls': self.mapf_fail_calls,
            'mapf_mean_plan_time_ms': mapf_mean_plan_time_ms,
            'mapf_p95_plan_time_ms': mapf_p95_plan_time_ms,
            'fallback_wait_steps': self.fallback_wait_steps,
            'expanded_nodes_total': self.expanded_nodes_total,
            'mapf_expanded_mean_per_call': mapf_expanded_mean_per_call
        }
