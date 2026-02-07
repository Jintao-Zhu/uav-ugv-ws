"""
Day6 Step 5: 固定预留测试

测试 carrier 轨迹作为 fixed_reservations 的功能。

验证：
1. 加 fixed_reservations 后仍能成功（成功率 ≥ 60%）
2. 成功解与 carrier 轨迹无 vertex/edge 冲突
"""

import sys
import random
from pathlib import Path
from typing import List, Tuple, Dict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.mapf import MAPFPlanner
from agcoop.map import auto_load_map


def generate_carrier_path(
    grid_map,
    start: Tuple[int, int],
    H: int,
    seed: int
) -> List[Tuple[int, int]]:
    """
    生成 carrier 的模拟轨迹（随机游走）

    Args:
        grid_map: 地图对象
        start: 起点
        H: 路径长度
        seed: 随机种子

    Returns:
        carrier 路径
    """
    random.seed(seed)
    path = [start]
    current = start

    for _ in range(H):
        # 获取邻居
        neighbors = []
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = current[0] + dx, current[1] + dy
            if 0 <= nx < grid_map.width and 0 <= ny < grid_map.height:
                if grid_map.is_free(nx, ny):
                    neighbors.append((nx, ny))

        if neighbors:
            # 随机选择一个邻居或 WAIT
            if random.random() < 0.3:  # 30% 概率 WAIT
                next_pos = current
            else:
                next_pos = random.choice(neighbors)
        else:
            next_pos = current

        path.append(next_pos)
        current = next_pos

    return path


def generate_random_positions(
    grid_map,
    n: int,
    seed: int,
    exclude_cells: List[Tuple[int, int]] = None
) -> Tuple[dict, dict]:
    """
    生成随机的起点和终点（排除指定位置）

    Args:
        grid_map: 地图对象
        n: agent 数量
        seed: 随机种子
        exclude_cells: 需要排除的位置列表

    Returns:
        (starts, goals)
    """
    random.seed(seed)

    # 收集所有空闲位置
    free_cells = []
    for x in range(grid_map.width):
        for y in range(grid_map.height):
            if grid_map.is_free(x, y):
                if exclude_cells is None or (x, y) not in exclude_cells:
                    free_cells.append((x, y))

    if len(free_cells) < 2 * n:
        raise ValueError(f"地图空闲位置不足：需要 {2*n}，只有 {len(free_cells)}")

    # 随机选择起点和终点
    selected = random.sample(free_cells, 2 * n)
    starts = {i: selected[i] for i in range(n)}
    goals = {i: selected[n + i] for i in range(n)}

    return starts, goals


def check_collision_with_fixed_path(
    paths: Dict[int, List[Tuple[int, int]]],
    fixed_path: List[Tuple[int, int]],
    fixed_agent_id: int
) -> Tuple[bool, str]:
    """
    检查规划路径与固定路径是否有冲突

    Args:
        paths: 规划的路径
        fixed_path: 固定路径
        fixed_agent_id: 固定路径的 agent ID

    Returns:
        (collision_free, error_message)
    """
    # 将固定路径加入检查
    all_paths = dict(paths)
    all_paths[fixed_agent_id] = fixed_path

    # 使用 MAPFPlanner 的 validate_solution 方法
    # 但我们需要一个临时的 planner 实例
    # 这里直接实现碰撞检测逻辑

    max_len = max(len(path) for path in all_paths.values())

    for t in range(max_len):
        # 获取所有 agent 在时刻 t 的位置
        positions_at_t = {}
        for agent_id, path in all_paths.items():
            if t < len(path):
                pos = path[t]
            else:
                pos = path[-1]

            # 检查 vertex collision
            if pos in positions_at_t.values():
                other_agent = [aid for aid, p in positions_at_t.items() if p == pos][0]
                return False, f"Vertex collision at t={t}: agent {agent_id} and {other_agent} at {pos}"

            positions_at_t[agent_id] = pos

        # 检查 edge collision
        if t > 0:
            for agent_id, path in all_paths.items():
                if t < len(path):
                    prev_pos = path[t-1]
                    curr_pos = path[t]
                else:
                    continue

                # 检查是否有其他 agent 从 curr_pos 移动到 prev_pos（交换位置）
                for other_id, other_path in all_paths.items():
                    if other_id == agent_id:
                        continue

                    if t < len(other_path):
                        other_prev = other_path[t-1]
                        other_curr = other_path[t]

                        if prev_pos == other_curr and curr_pos == other_prev:
                            return False, f"Edge collision at t={t}: agent {agent_id} and {other_id} swap positions"

    return True, ""


def main():
    print("=" * 80)
    print("Day6 Step 5: 固定预留测试")
    print("=" * 80)

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))
    print(f"✓ 加载地图: map_01 ({grid_map.width}x{grid_map.height})")

    # 参数
    N = 3  # 总共 3 个 agent（carrier + 2 个需要规划的）
    H = 30
    budget_ms = 300
    num_tests = 20

    print(f"✓ 参数: N={N}, H={H}, budget_ms={budget_ms}, tests={num_tests}")
    print()

    # 创建 MAPF 规划器
    planner = MAPFPlanner(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=budget_ms
    )

    # 统计结果
    without_fixed_success = 0
    with_fixed_success = 0
    collision_count = 0

    print("测试进度:")
    print()

    for seed in range(num_tests):
        # 生成 carrier 起点（固定为 agent 0）
        carrier_start = (5, 5)

        # 生成 carrier 轨迹
        carrier_path = generate_carrier_path(grid_map, carrier_start, H, seed)

        # 收集 carrier 轨迹占用的所有位置（用于排除）
        carrier_cells = set(carrier_path)

        # 生成其他 agent 的起点和终点（排除 carrier 轨迹）
        try:
            other_starts, other_goals = generate_random_positions(
                grid_map, N - 1, seed, exclude_cells=list(carrier_cells)
            )
        except ValueError:
            print(f"  ⚠️  seed={seed:2d}: 无法生成足够的起点/终点（carrier 轨迹占用太多空间）")
            continue

        # 构建完整的 starts 和 goals（包括 carrier）
        all_starts = {0: carrier_start}
        all_goals = {0: carrier_path[-1]}  # carrier 的目标是轨迹终点
        for i, (start, goal) in enumerate(zip(other_starts.values(), other_goals.values()), start=1):
            all_starts[i] = start
            all_goals[i] = goal

        # 测试 1: 不加 fixed_reservations
        result_without = planner.plan_mapf(
            starts=all_starts,
            goals=all_goals,
            H=H,
            priority_order=[0, 1, 2]
        )

        # 测试 2: 加 fixed_reservations（carrier 的路径）
        result_with = planner.plan_mapf(
            starts={1: all_starts[1], 2: all_starts[2]},  # 只规划 agent 1 和 2
            goals={1: all_goals[1], 2: all_goals[2]},
            H=H,
            priority_order=[1, 2],
            fixed_reservations={0: carrier_path}  # carrier 的路径作为固定预留
        )

        # 统计
        if result_without.success:
            without_fixed_success += 1

        if result_with.success:
            with_fixed_success += 1

            # 检查是否与 carrier 轨迹有冲突
            collision_free, error = check_collision_with_fixed_path(
                result_with.paths,
                carrier_path,
                fixed_agent_id=0
            )

            if not collision_free:
                collision_count += 1
                print(f"  ✗ seed={seed:2d}: 有碰撞 - {error}")
            else:
                print(f"  ✓ seed={seed:2d}: 成功且无碰撞")
        else:
            reason = result_with.failure_reason or 'unknown'
            print(f"  ✗ seed={seed:2d}: 失败 ({reason})")

    # 统计结果
    print()
    print("=" * 80)
    print("统计结果")
    print("=" * 80)

    without_rate = without_fixed_success / num_tests * 100
    with_rate = with_fixed_success / num_tests * 100

    print(f"  不加 fixed_reservations:")
    print(f"    - 成功: {without_fixed_success}/{num_tests} ({without_rate:.1f}%)")

    print(f"\n  加 fixed_reservations:")
    print(f"    - 成功: {with_fixed_success}/{num_tests} ({with_rate:.1f}%)")
    print(f"    - 碰撞: {collision_count}/{with_fixed_success if with_fixed_success > 0 else 1}")

    # 验收标准检查
    print()
    print("=" * 80)
    print("验收标准检查")
    print("=" * 80)

    # 1. 成功率 ≥ 60%
    if with_rate >= 60:
        print(f"  ✓ 加 fixed_reservations 成功率 ≥ 60%: {with_rate:.1f}%")
    else:
        print(f"  ✗ 加 fixed_reservations 成功率 < 60%: {with_rate:.1f}%")

    # 2. 无碰撞
    if collision_count == 0:
        print(f"  ✓ 所有成功解与 carrier 轨迹无冲突")
    else:
        print(f"  ✗ {collision_count} 次成功解与 carrier 轨迹有冲突")

    # 总结
    all_passed = (with_rate >= 60 and collision_count == 0)
    print()
    if all_passed:
        print("✓ Day6 Step 5 验收通过")
    else:
        print("✗ Day6 Step 5 验收未通过")
        sys.exit(1)


if __name__ == "__main__":
    main()
