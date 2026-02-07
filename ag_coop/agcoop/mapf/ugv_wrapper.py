"""
UGV MAPF Wrapper

为 core.py 提供简洁的 MAPF 规划接口，隔离 MAPF 实现细节。

接口设计：
- 输入：starts, goals, grid_map, H, budget_ms
- 输出：(paths, result)
- result 包含：success, plan_time_ms, termination_reason, expanded_nodes

使用场景：
- Receding horizon 规划（每 K 步调用）
- 失败时 fallback WAIT
"""

from typing import Dict, Tuple, Optional
from dataclasses import dataclass

from agcoop.mapf import MAPFPlanner, MAPFResult


@dataclass
class UGVMAPFResult:
    """
    UGV MAPF 规划结果

    简化的结果接口，供 core.py 使用
    """
    success: bool
    plan_time_ms: float
    termination_reason: str  # "success", "timeout", "no_path"
    expanded_nodes: int
    paths: Optional[Dict[int, list]] = None  # agent_id -> path
    makespan: int = 0
    sum_of_costs: int = 0

    def __repr__(self):
        if self.success:
            return (f"UGVMAPFResult(success=True, "
                    f"plan_time={self.plan_time_ms:.2f}ms, "
                    f"expanded={self.expanded_nodes})")
        else:
            return (f"UGVMAPFResult(success=False, "
                    f"reason={self.termination_reason}, "
                    f"plan_time={self.plan_time_ms:.2f}ms)")


class UGVMAPFWrapper:
    """
    UGV MAPF Wrapper

    封装 MAPF 规划器，提供简洁的接口给 core.py
    """

    def __init__(
        self,
        grid_map,
        connectivity: int = 4,
        time_budget_ms: int = 300
    ):
        """
        初始化 MAPF Wrapper

        Args:
            grid_map: 地图对象
            connectivity: 连通性（4 或 8）
            time_budget_ms: 默认时间预算（毫秒）
        """
        self.grid_map = grid_map
        self.connectivity = connectivity
        self.default_budget_ms = time_budget_ms

        # 创建 MAPF 规划器
        self.planner = MAPFPlanner(
            grid_map=grid_map,
            connectivity=connectivity,
            time_budget_ms=time_budget_ms
        )

        # 统计信息
        self.total_calls = 0
        self.success_calls = 0
        self.timeout_calls = 0
        self.fail_calls = 0

    def plan(
        self,
        starts: Dict[int, Tuple[int, int]],
        goals: Dict[int, Tuple[int, int]],
        H: int,
        budget_ms: Optional[int] = None,
        priority_order: Optional[list] = None
    ) -> UGVMAPFResult:
        """
        规划 UGV 路径

        Args:
            starts: agent_id -> start_position (x, y)
            goals: agent_id -> goal_position (x, y)
            H: 规划时间窗（步数）
            budget_ms: 时间预算（毫秒），None 则使用默认值
            priority_order: agent 优先级顺序，None 则使用默认顺序

        Returns:
            UGVMAPFResult: 规划结果
        """
        # 使用默认 budget 如果未指定
        if budget_ms is None:
            budget_ms = self.default_budget_ms

        # 更新规划器的时间预算
        self.planner.time_budget_ms = budget_ms

        # 调用 MAPF 规划器
        self.total_calls += 1

        result = self.planner.plan_mapf(
            starts=starts,
            goals=goals,
            H=H,
            priority_order=priority_order
        )

        # 转换为简化的结果格式
        if result.success:
            self.success_calls += 1
            return UGVMAPFResult(
                success=True,
                plan_time_ms=result.solve_time_ms,
                termination_reason="success",
                expanded_nodes=result.expanded_total,
                paths=result.paths,
                makespan=result.makespan,
                sum_of_costs=result.sum_of_costs
            )
        else:
            # 失败情况
            if result.timeout:
                self.timeout_calls += 1
                termination_reason = "timeout"
            else:
                self.fail_calls += 1
                termination_reason = result.failure_reason or "no_path"

            return UGVMAPFResult(
                success=False,
                plan_time_ms=result.solve_time_ms,
                termination_reason=termination_reason,
                expanded_nodes=result.expanded_total,
                paths=None
            )

    def get_stats(self) -> Dict:
        """
        获取统计信息

        Returns:
            统计字典
        """
        return {
            'total_calls': self.total_calls,
            'success_calls': self.success_calls,
            'timeout_calls': self.timeout_calls,
            'fail_calls': self.fail_calls,
            'success_rate': self.success_calls / self.total_calls if self.total_calls > 0 else 0.0
        }

    def reset_stats(self):
        """重置统计信息"""
        self.total_calls = 0
        self.success_calls = 0
        self.timeout_calls = 0
        self.fail_calls = 0
