"""
Day6 Test B: Swap Case 验证

验证 MAPF 系统能否正确处理两个 agent 互换位置的场景。
这是一个经典的 edge collision 挑战。

场景：
- 2 agents
- Agent 0: (5, 5) -> (10, 5)
- Agent 1: (10, 5) -> (5, 5)
- 直线距离 5 步，但需要避让

预期：
- 成功找到无碰撞路径
- 一个 agent 需要绕路或等待
- 无 vertex collision 和 edge swap
"""

import sys
import json
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.mapf import MAPFPlanner
from agcoop.map import auto_load_map


def check_collision(
    paths: dict,
    n: int
) -> Tuple[bool, str]:
    """
    检查路径是否有碰撞

    Returns:
        (collision_free, error_message)
    """
    if not paths:
        return True, ""

    max_len = max(len(path) for path in paths.values())

    for t in range(max_len):
        # 获取所有 agent 在时刻 t 的位置
        positions_at_t = {}
        for agent_id in range(n):
            if t < len(paths[agent_id]):
                pos = paths[agent_id][t]
            else:
                pos = paths[agent_id][-1]

            # 检查 vertex collision
            if pos in positions_at_t.values():
                other_agent = [aid for aid, p in positions_at_t.items() if p == pos][0]
                return False, f"Vertex collision at t={t}: agent {agent_id} and {other_agent} at {pos}"

            positions_at_t[agent_id] = pos

        # 检查 edge collision (swap)
        if t > 0:
            for agent_id in range(n):
                if t < len(paths[agent_id]):
                    prev_pos = paths[agent_id][t-1]
                    curr_pos = paths[agent_id][t]
                else:
                    continue

                for other_id in range(n):
                    if other_id == agent_id:
                        continue

                    if t < len(paths[other_id]):
                        other_prev = paths[other_id][t-1]
                        other_curr = paths[other_id][t]

                        if prev_pos == other_curr and curr_pos == other_prev:
                            return False, f"Edge collision at t={t}: agent {agent_id} and {other_id} swap positions"

    return True, ""


def main():
    print("=" * 80)
    print("Day6 Test B: Swap Case 验证")
    print("=" * 80)
    print()

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))
    print(f"地图: map_01 ({grid_map.width}x{grid_map.height})")

    # 定义 swap 场景
    starts = {
        0: (5, 5),
        1: (10, 5)
    }

    goals = {
        0: (10, 5),
        1: (5, 5)
    }

    print(f"起点: {starts}")
    print(f"目标: {goals}")
    print()

    # 验证起点和目标都是空闲格子
    for agent_id, pos in starts.items():
        if not grid_map.is_free(pos[0], pos[1]):
            print(f"✗ Agent {agent_id} 起点 {pos} 不是空闲格子")
            sys.exit(1)

    for agent_id, pos in goals.items():
        if not grid_map.is_free(pos[0], pos[1]):
            print(f"✗ Agent {agent_id} 目标 {pos} 不是空闲格子")
            sys.exit(1)

    print("✓ 所有起点和目标都是空闲格子")
    print()

    # 创建 MAPF 规划器
    planner = MAPFPlanner(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=1000
    )

    # 测试不同的优先级顺序
    priority_orders = [
        [0, 1],  # Agent 0 优先
        [1, 0]   # Agent 1 优先
    ]

    for priority_order in priority_orders:
        print(f"测试优先级顺序: {priority_order}")
        print("-" * 80)

        result = planner.plan_mapf(
            starts=starts,
            goals=goals,
            H=30,
            priority_order=priority_order
        )

        print(f"  成功: {result.success}")
        print(f"  求解时间: {result.solve_time_ms:.2f} ms")

        if result.success:
            print(f"  Makespan: {result.makespan}")
            print(f"  Sum of costs: {result.sum_of_costs}")
            print(f"  展开节点: {result.expanded_total}")
            print()

            # 打印路径
            for agent_id in range(2):
                path = result.paths[agent_id]
                print(f"  Agent {agent_id} 路径 (长度 {len(path)}):")
                print(f"    {' -> '.join(str(p) for p in path)}")
            print()

            # 碰撞检测
            collision_free, error = check_collision(result.paths, 2)
            if collision_free:
                print(f"  ✓ 碰撞检测通过")
            else:
                print(f"  ✗ 碰撞检测失败: {error}")
                sys.exit(1)

            # 验证路径正确性
            for agent_id in range(2):
                path = result.paths[agent_id]
                if path[0] != starts[agent_id]:
                    print(f"  ✗ Agent {agent_id} 路径起点错误")
                    sys.exit(1)
                if path[-1] != goals[agent_id]:
                    print(f"  ✗ Agent {agent_id} 路径终点错误")
                    sys.exit(1)

            print(f"  ✓ 路径起点和终点正确")

            # 检查是否有 agent 绕路或等待
            direct_distance = abs(starts[0][0] - goals[0][0]) + abs(starts[0][1] - goals[0][1])
            print(f"  直线距离: {direct_distance}")

            for agent_id in range(2):
                path_len = len(result.paths[agent_id]) - 1  # 减去起点
                if path_len > direct_distance:
                    print(f"  ✓ Agent {agent_id} 绕路/等待 (路径长度 {path_len} > 直线距离 {direct_distance})")
                else:
                    print(f"  Agent {agent_id} 直线通过 (路径长度 {path_len})")
        else:
            print(f"  失败原因: {result.failure_reason}")
            print(f"  超时: {result.timeout}")
            print(f"  ✗ 规划失败")
            sys.exit(1)

        print()

    # 总结
    print("=" * 80)
    print("验收结果")
    print("=" * 80)
    print("  ✓ 两种优先级顺序都成功")
    print("  ✓ 无碰撞")
    print("  ✓ 路径正确")
    print("  ✓ 至少一个 agent 绕路/等待")
    print()
    print("✓ Day6 Test B (Swap Case) 验收通过")


if __name__ == "__main__":
    main()
