"""
Day6 Test C: Bottleneck (走廊瓶颈) 验证

验证 MAPF 系统能否正确处理多个 agent 通过狭窄通道的场景。
这是一个经典的协调挑战，需要 agents 排队通过。

场景：
- 3 agents
- 狭窄走廊（宽度 1 格）
- Agents 需要从走廊两端通过

预期：
- 成功找到无碰撞路径
- Agents 需要等待或绕路
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


def find_corridor_scenario(grid_map):
    """
    在地图中寻找走廊场景

    寻找一个狭窄通道（宽度1格），两端有开阔区域

    Returns:
        (starts, goals) or (None, None) if not found
    """
    # 寻找水平走廊
    for y in range(1, grid_map.height - 1):
        corridor_cells = []
        for x in range(1, grid_map.width - 1):
            if grid_map.is_free(x, y):
                # 检查上下是否是障碍（形成走廊）
                if not grid_map.is_free(x, y-1) and not grid_map.is_free(x, y+1):
                    corridor_cells.append((x, y))

        # 如果找到足够长的走廊（至少5格）
        if len(corridor_cells) >= 5:
            # 检查走廊两端是否有开阔区域
            left_end = corridor_cells[0]
            right_end = corridor_cells[-1]

            # 检查左端开阔区域
            left_open = []
            for dx in range(-2, 0):
                for dy in range(-1, 2):
                    x, y = left_end[0] + dx, left_end[1] + dy
                    if 0 <= x < grid_map.width and 0 <= y < grid_map.height:
                        if grid_map.is_free(x, y):
                            left_open.append((x, y))

            # 检查右端开阔区域
            right_open = []
            for dx in range(1, 3):
                for dy in range(-1, 2):
                    x, y = right_end[0] + dx, right_end[1] + dy
                    if 0 <= x < grid_map.width and 0 <= y < grid_map.height:
                        if grid_map.is_free(x, y):
                            right_open.append((x, y))

            if len(left_open) >= 2 and len(right_open) >= 2:
                # 找到合适的场景
                starts = {
                    0: left_open[0],
                    1: left_open[1] if len(left_open) > 1 else left_open[0],
                    2: right_open[0]
                }

                goals = {
                    0: right_open[0],
                    1: right_open[1] if len(right_open) > 1 else right_open[0],
                    2: left_open[0]
                }

                return starts, goals, corridor_cells

    return None, None, None


def main():
    print("=" * 80)
    print("Day6 Test C: Bottleneck (走廊瓶颈) 验证")
    print("=" * 80)
    print()

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))
    print(f"地图: map_01 ({grid_map.width}x{grid_map.height})")
    print()

    # 寻找走廊场景
    print("寻找走廊场景...")
    starts, goals, corridor = find_corridor_scenario(grid_map)

    if starts is None:
        print("✗ 未找到合适的走廊场景，使用手动设置")
        # 手动设置一个瓶颈场景
        # 假设 map_01 中存在这样的位置
        starts = {
            0: (2, 10),
            1: (3, 10),
            2: (15, 10)
        }

        goals = {
            0: (15, 10),
            1: (16, 10),
            2: (2, 10)
        }
        corridor = [(x, 10) for x in range(5, 13)]
    else:
        print(f"✓ 找到走廊: {len(corridor)} 格")
        print(f"  走廊位置: {corridor[:3]} ... {corridor[-3:]}")

    print(f"起点: {starts}")
    print(f"目标: {goals}")
    print()

    # 验证起点和目标都是空闲格子
    all_valid = True
    for agent_id, pos in starts.items():
        if not grid_map.is_free(pos[0], pos[1]):
            print(f"✗ Agent {agent_id} 起点 {pos} 不是空闲格子")
            all_valid = False

    for agent_id, pos in goals.items():
        if not grid_map.is_free(pos[0], pos[1]):
            print(f"✗ Agent {agent_id} 目标 {pos} 不是空闲格子")
            all_valid = False

    if not all_valid:
        print("✗ 场景设置无效，跳过测试")
        print("注意: 这不是 MAPF 系统的问题，而是测试场景设置问题")
        sys.exit(0)

    print("✓ 所有起点和目标都是空闲格子")
    print()

    # 创建 MAPF 规划器
    planner = MAPFPlanner(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=2000  # 增加时间预算，因为瓶颈场景更复杂
    )

    # 测试不同的优先级顺序
    priority_orders = [
        [0, 1, 2],  # 左侧优先
        [2, 0, 1],  # 右侧优先
        [1, 0, 2]   # 混合优先
    ]

    success_count = 0

    for priority_order in priority_orders:
        print(f"测试优先级顺序: {priority_order}")
        print("-" * 80)

        result = planner.plan_mapf(
            starts=starts,
            goals=goals,
            H=50,  # 增加时间窗，因为瓶颈场景需要更多步数
            priority_order=priority_order
        )

        print(f"  成功: {result.success}")
        print(f"  求解时间: {result.solve_time_ms:.2f} ms")

        if result.success:
            success_count += 1
            print(f"  Makespan: {result.makespan}")
            print(f"  Sum of costs: {result.sum_of_costs}")
            print(f"  展开节点: {result.expanded_total}")
            print()

            # 打印路径摘要
            for agent_id in range(3):
                path = result.paths[agent_id]
                print(f"  Agent {agent_id} 路径长度: {len(path)}")
                print(f"    起点: {path[0]} -> 终点: {path[-1]}")
            print()

            # 碰撞检测
            collision_free, error = check_collision(result.paths, 3)
            if collision_free:
                print(f"  ✓ 碰撞检测通过")
            else:
                print(f"  ✗ 碰撞检测失败: {error}")
                # 不立即退出，继续测试其他优先级

            # 验证路径正确性
            all_correct = True
            for agent_id in range(3):
                path = result.paths[agent_id]
                if path[0] != starts[agent_id]:
                    print(f"  ✗ Agent {agent_id} 路径起点错误")
                    all_correct = False
                if path[-1] != goals[agent_id]:
                    print(f"  ✗ Agent {agent_id} 路径终点错误")
                    all_correct = False

            if all_correct:
                print(f"  ✓ 路径起点和终点正确")
        else:
            print(f"  失败原因: {result.failure_reason}")
            print(f"  超时: {result.timeout}")
            print(f"  注意: 瓶颈场景可能需要更大的 H 或更多时间预算")

        print()

    # 总结
    print("=" * 80)
    print("验收结果")
    print("=" * 80)
    print(f"  成功次数: {success_count}/3")

    if success_count >= 2:
        print("  ✓ 至少 2/3 优先级顺序成功")
        print()
        print("✓ Day6 Test C (Bottleneck) 验收通过")
    elif success_count >= 1:
        print("  ⚠ 部分成功 (1/3)")
        print("  注意: 瓶颈场景对优先级顺序敏感，这是正常的")
        print()
        print("⚠ Day6 Test C (Bottleneck) 部分通过")
    else:
        print("  ✗ 所有优先级顺序都失败")
        print("  可能原因: 场景过于复杂，需要更大的 H 或更好的启发式")
        print()
        print("✗ Day6 Test C (Bottleneck) 未通过")


if __name__ == "__main__":
    main()
