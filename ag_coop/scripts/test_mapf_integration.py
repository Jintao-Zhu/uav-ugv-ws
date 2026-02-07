"""
Day6 Step 6: MAPF 集成测试脚本

独立验证 MAPF 在 receding horizon 场景下的工作：
- 每 K 步调用 MAPF 规划
- 路径缓存与执行
- 失败时 fallback WAIT
- 碰撞检测
- 输出 trace 和 metrics

不修改 core.py，作为独立的验证脚本。
"""

import sys
import json
import argparse
import random
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from collections import deque

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.mapf import MAPFPlanner
from agcoop.map import auto_load_map


def bfs_distance(grid_map, start: Tuple[int, int], goal: Tuple[int, int]) -> int:
    """
    计算两点之间的 BFS 距离

    Args:
        grid_map: 地图对象
        start: 起点
        goal: 终点

    Returns:
        BFS 距离，如果不可达返回 -1
    """
    if start == goal:
        return 0

    visited = {start}
    queue = deque([(start, 0)])

    while queue:
        current, dist = queue.popleft()

        # 检查邻居
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = current[0] + dx, current[1] + dy

            if 0 <= nx < grid_map.width and 0 <= ny < grid_map.height:
                if grid_map.is_free(nx, ny) and (nx, ny) not in visited:
                    if (nx, ny) == goal:
                        return dist + 1

                    visited.add((nx, ny))
                    queue.append(((nx, ny), dist + 1))

    return -1  # 不可达


def sample_free_cells(grid_map, n: int, seed: int, exclude: List[Tuple[int, int]] = None) -> List[Tuple[int, int]]:
    """
    从地图中采样 n 个空闲位置

    Args:
        grid_map: 地图对象
        n: 采样数量
        seed: 随机种子
        exclude: 需要排除的位置列表

    Returns:
        采样的位置列表
    """
    random.seed(seed)

    # 收集所有空闲位置
    free_cells = []
    for x in range(grid_map.width):
        for y in range(grid_map.height):
            if grid_map.is_free(x, y):
                if exclude is None or (x, y) not in exclude:
                    free_cells.append((x, y))

    if len(free_cells) < n:
        raise ValueError(f"地图空闲位置不足：需要 {n}，只有 {len(free_cells)}")

    return random.sample(free_cells, n)


def generate_patrol_goals(
    grid_map,
    n: int,
    starts: List[Tuple[int, int]],
    goal_radius: int,
    seed: int
) -> List[Tuple[int, int]]:
    """
    生成巡逻目标点（确保距离可控）

    Args:
        grid_map: 地图对象
        n: agent 数量
        starts: 起点列表
        goal_radius: 最大 BFS 距离
        seed: 随机种子

    Returns:
        目标点列表
    """
    random.seed(seed)

    # 收集候选点（路口优先）
    candidates = []
    for x in range(grid_map.width):
        for y in range(grid_map.height):
            if grid_map.is_free(x, y):
                # 计算邻居数量
                neighbors = 0
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < grid_map.width and 0 <= ny < grid_map.height:
                        if grid_map.is_free(nx, ny):
                            neighbors += 1

                # 路口（邻居 >= 3）优先
                if neighbors >= 3:
                    candidates.insert(0, (x, y))
                else:
                    candidates.append((x, y))

    # 为每个 agent 选择目标
    goals = []
    for i in range(n):
        start = starts[i]

        # 尝试找到距离合适的目标
        for candidate in candidates:
            if candidate in starts or candidate in goals:
                continue

            dist = bfs_distance(grid_map, start, candidate)
            if 0 < dist <= goal_radius:
                goals.append(candidate)
                break
        else:
            # 如果找不到合适的，就选一个不太远的
            for candidate in candidates:
                if candidate in starts or candidate in goals:
                    continue
                goals.append(candidate)
                break

    if len(goals) < n:
        raise ValueError(f"无法生成足够的目标点：需要 {n}，只有 {len(goals)}")

    return goals


def check_collision_online(
    positions: List[Tuple[int, int]],
    prev_positions: Optional[List[Tuple[int, int]]],
    t: int
) -> Tuple[bool, str]:
    """
    在线碰撞检测

    Args:
        positions: 当前位置列表
        prev_positions: 上一步位置列表
        t: 当前时间步

    Returns:
        (collision_free, error_message)
    """
    n = len(positions)

    # 检查 vertex collision
    for i in range(n):
        for j in range(i + 1, n):
            if positions[i] == positions[j]:
                return False, f"Vertex collision at t={t}: agent {i} and {j} at {positions[i]}"

    # 检查 edge collision (swap)
    if prev_positions is not None:
        for i in range(n):
            for j in range(i + 1, n):
                if positions[i] == prev_positions[j] and positions[j] == prev_positions[i]:
                    return False, f"Edge collision at t={t}: agent {i} and {j} swap positions"

    return True, ""


def main():
    parser = argparse.ArgumentParser(description='MAPF 集成测试脚本')
    parser.add_argument('--map', type=str, default='map_01', help='地图名称')
    parser.add_argument('--n', type=int, default=3, help='agent 数量')
    parser.add_argument('--steps', type=int, default=500, help='总步数')
    parser.add_argument('--K', type=int, default=5, help='重规划周期')
    parser.add_argument('--H', type=int, default=40, help='规划时间窗')
    parser.add_argument('--budget_ms', type=int, default=300, help='MAPF 时间预算（毫秒）')
    parser.add_argument('--seed', type=int, default=0, help='随机种子')
    parser.add_argument('--goal_switch_period', type=int, default=50, help='目标切换周期')
    parser.add_argument('--goal_radius', type=int, default=10, help='目标最大 BFS 距离')
    parser.add_argument('--out_dir', type=str, default=None, help='输出目录')

    args = parser.parse_args()

    # 设置输出目录
    if args.out_dir is None:
        run_id = f"{args.map}_n{args.n}_seed{args.seed}_K{args.K}_H{args.H}"
        args.out_dir = f"outputs/test_mapf_integration/{run_id}"

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("Day6 Step 6: MAPF 集成测试")
    print("=" * 80)
    print(f"参数:")
    print(f"  地图: {args.map}")
    print(f"  Agent 数量: {args.n}")
    print(f"  总步数: {args.steps}")
    print(f"  重规划周期 K: {args.K}")
    print(f"  规划时间窗 H: {args.H}")
    print(f"  时间预算: {args.budget_ms} ms")
    print(f"  随机种子: {args.seed}")
    print(f"  输出目录: {args.out_dir}")
    print()

    # Step 1: 加载地图
    print("Step 1: 加载地图")
    map_path = project_root / "maps" / f"{args.map}.map"
    grid_map = auto_load_map(str(map_path))
    print(f"  ✓ 地图: {args.map} ({grid_map.width}x{grid_map.height})")

    # 统计空闲格子数量
    free_count = sum(1 for x in range(grid_map.width) for y in range(grid_map.height) if grid_map.is_free(x, y))
    print(f"  ✓ 空闲格子: {free_count}")

    # 采样初始位置
    starts = sample_free_cells(grid_map, args.n, args.seed)
    print(f"  ✓ 初始位置: {starts}")
    assert len(set(starts)) == args.n, "初始位置有重复"
    print()

    # Step 2: 生成巡逻目标
    print("Step 2: 生成巡逻目标")
    goals = generate_patrol_goals(grid_map, args.n, starts, args.goal_radius, args.seed)
    print(f"  ✓ 初始目标: {goals}")

    # 验证距离
    for i in range(args.n):
        dist = bfs_distance(grid_map, starts[i], goals[i])
        print(f"  ✓ Agent {i}: {starts[i]} -> {goals[i]} (距离: {dist})")
        assert 0 < dist <= args.goal_radius, f"Agent {i} 距离超出限制"
    print()

    # 保存初始化信息
    init_info = {
        'map': args.map,
        'n': args.n,
        'starts': starts,
        'goals': goals,
        'seed': args.seed
    }
    with open(out_dir / 'init.json', 'w') as f:
        json.dump(init_info, f, indent=2)

    # 保存完整配置（config_resolved.yaml）
    import yaml
    config_resolved = {
        'map': args.map,
        'n_agents': args.n,
        'steps': args.steps,
        'K': args.K,
        'H': args.H,
        'budget_ms': args.budget_ms,
        'seed': args.seed,
        'goal_switch_period': args.goal_switch_period,
        'goal_radius': args.goal_radius,
        'connectivity': 4,
        'starts': starts,
        'goals': goals,
        'map_size': [grid_map.width, grid_map.height],
        'free_cells': free_count
    }
    with open(out_dir / 'config_resolved.yaml', 'w') as f:
        yaml.dump(config_resolved, f, default_flow_style=False, allow_unicode=True)

    # Step 3: 创建 MAPF 规划器
    print("Step 3: 创建 MAPF 规划器")
    planner = MAPFPlanner(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=args.budget_ms
    )
    print(f"  ✓ MAPF 规划器创建成功")
    print()

    # Step 4: Receding horizon 主循环
    print("Step 4: Receding horizon 主循环")
    print()

    # 初始化状态
    positions = list(starts)
    current_goals = list(goals)

    # 路径缓存
    cache_paths = None
    cache_start_t = -1

    # Fallback 状态
    fallback_wait_remaining = 0

    # 统计信息
    mapf_calls = 0
    mapf_success_calls = 0
    mapf_timeout_calls = 0
    mapf_fail_calls = 0
    mapf_plan_times = []
    fallback_wait_steps = 0
    expanded_nodes_total = 0  # 新增：总展开节点数
    step_motions = []  # 新增：每步移动的 agent 数量

    # Trace 记录
    trace = []

    # 主循环
    for t in range(args.steps):
        prev_positions = list(positions)

        # 目标切换
        if t > 0 and t % args.goal_switch_period == 0:
            # Round-robin 换目标
            new_goals = [current_goals[(i + 1) % args.n] for i in range(args.n)]
            current_goals = new_goals
            print(f"  t={t:3d}: 目标切换 -> {current_goals}")

        # 决策步
        decision_step = (t % args.K == 0)
        mapf_called = False
        mapf_success = None
        mapf_plan_time_ms = None

        if decision_step and fallback_wait_remaining == 0:
            # 调用 MAPF
            mapf_called = True
            mapf_calls += 1

            starts_dict = {i: positions[i] for i in range(args.n)}
            goals_dict = {i: current_goals[i] for i in range(args.n)}

            result = planner.plan_mapf(
                starts=starts_dict,
                goals=goals_dict,
                H=args.H,
                priority_order=list(range(args.n))
            )

            mapf_success = result.success
            mapf_plan_time_ms = result.solve_time_ms
            mapf_plan_times.append(mapf_plan_time_ms)

            # 记录展开节点数
            if hasattr(result, 'expanded_total'):
                expanded_nodes_total += result.expanded_total

            if result.success:
                # 缓存路径
                cache_paths = result.paths
                cache_start_t = t
                mapf_success_calls += 1
                print(f"  t={t:3d}: MAPF 成功 ({mapf_plan_time_ms:.2f} ms)")
            else:
                # 失败，触发 fallback
                fallback_wait_remaining = args.K
                cache_paths = None
                if result.timeout:
                    mapf_timeout_calls += 1
                    print(f"  t={t:3d}: MAPF 超时 ({mapf_plan_time_ms:.2f} ms)")
                else:
                    mapf_fail_calls += 1
                    print(f"  t={t:3d}: MAPF 失败 ({result.failure_reason}, {mapf_plan_time_ms:.2f} ms)")

        # 执行步
        in_fallback = (fallback_wait_remaining > 0)

        if in_fallback:
            # Fallback WAIT
            # positions 保持不变
            fallback_wait_remaining -= 1
            fallback_wait_steps += 1
        else:
            # 执行缓存路径
            if cache_paths is None:
                raise RuntimeError(f"t={t}: 没有缓存路径但不在 fallback 状态")

            offset = t - cache_start_t
            if offset + 1 >= len(list(cache_paths.values())[0]):
                raise RuntimeError(f"t={t}: offset={offset} 越界")

            # 更新位置
            for i in range(args.n):
                positions[i] = cache_paths[i][offset + 1]

        # 在线碰撞检测
        collision_free, error = check_collision_online(positions, prev_positions, t)
        if not collision_free:
            print(f"\n✗ 碰撞检测失败: {error}")
            print(f"  当前位置: {positions}")
            print(f"  上一步位置: {prev_positions}")
            raise RuntimeError(error)

        # 检查所有位置都是空闲格子
        for i, pos in enumerate(positions):
            if not grid_map.is_free(pos[0], pos[1]):
                raise RuntimeError(f"t={t}: Agent {i} 位置 {pos} 不是空闲格子")

        # 计算本步移动的 agent 数量
        if t > 0:
            moved_count = sum(1 for i in range(args.n) if positions[i] != prev_positions[i])
            step_motions.append(moved_count)

        # 记录 trace
        trace.append({
            't': t,
            'ugv_positions': positions.copy(),
            'ugv_goals': current_goals.copy(),
            'decision_step': decision_step,
            'mapf_called': mapf_called,
            'mapf_success': mapf_success,
            'mapf_plan_time_ms': mapf_plan_time_ms,
            'fallback': in_fallback
        })

    print()
    print(f"✓ 主循环完成 ({args.steps} 步)")
    print()

    # Step 5: 输出 trace 和 metrics
    print("Step 5: 输出结果")

    # 保存 trace
    with open(out_dir / 'trace.jsonl', 'w') as f:
        for entry in trace:
            f.write(json.dumps(entry) + '\n')
    print(f"  ✓ trace.jsonl ({len(trace)} 行)")

    # 计算 metrics
    mapf_mean_plan_time_ms = sum(mapf_plan_times) / len(mapf_plan_times) if mapf_plan_times else 0
    mapf_plan_times_sorted = sorted(mapf_plan_times)
    mapf_p95_plan_time_ms = mapf_plan_times_sorted[int(len(mapf_plan_times_sorted) * 0.95)] if mapf_plan_times_sorted else 0

    # 计算新增指标
    mapf_expanded_mean_per_call = expanded_nodes_total / mapf_calls if mapf_calls > 0 else 0
    mean_step_motion = sum(step_motions) / len(step_motions) if step_motions else 0

    metrics = {
        'seed': args.seed,
        'steps': args.steps,
        'K': args.K,
        'H': args.H,
        'budget_ms': args.budget_ms,
        'n_agents': args.n,
        'mapf_calls': mapf_calls,
        'mapf_success_calls': mapf_success_calls,
        'mapf_timeout_calls': mapf_timeout_calls,
        'mapf_fail_calls': mapf_fail_calls,
        'mapf_mean_plan_time_ms': mapf_mean_plan_time_ms,
        'mapf_p95_plan_time_ms': mapf_p95_plan_time_ms,
        'fallback_wait_steps': fallback_wait_steps,
        'collision_free': True,
        'expanded_nodes_total': expanded_nodes_total,
        'mapf_expanded_mean_per_call': mapf_expanded_mean_per_call,
        'mean_step_motion': mean_step_motion
    }

    with open(out_dir / 'metrics.json', 'w') as f:
        json.dump(metrics, f, indent=2)
    print(f"  ✓ metrics.json")
    print()

    # 打印统计
    print("=" * 80)
    print("统计结果")
    print("=" * 80)
    print(f"  MAPF 调用: {mapf_calls}")
    print(f"    - 成功: {mapf_success_calls} ({mapf_success_calls/mapf_calls*100:.1f}%)")
    print(f"    - 超时: {mapf_timeout_calls}")
    print(f"    - 失败: {mapf_fail_calls}")
    print(f"  平均规划时间: {mapf_mean_plan_time_ms:.2f} ms")
    print(f"  P95 规划时间: {mapf_p95_plan_time_ms:.2f} ms")
    print(f"  Fallback WAIT 步数: {fallback_wait_steps} ({fallback_wait_steps/args.steps*100:.1f}%)")
    print(f"  碰撞检测: ✓ 通过")
    print()

    # 验收标准检查
    print("=" * 80)
    print("验收标准检查")
    print("=" * 80)

    # 1. MAPF 调用次数
    expected_calls = (args.steps + args.K - 1) // args.K
    if mapf_calls >= expected_calls:
        print(f"  ✓ MAPF 调用次数正确: {mapf_calls} >= {expected_calls}")
    else:
        print(f"  ✗ MAPF 调用次数不足: {mapf_calls} < {expected_calls}")

    # 2. 成功率
    success_rate = mapf_success_calls / mapf_calls if mapf_calls > 0 else 0
    if success_rate >= 0.7:
        print(f"  ✓ MAPF 成功率 ≥ 70%: {success_rate*100:.1f}%")
    else:
        print(f"  ✗ MAPF 成功率 < 70%: {success_rate*100:.1f}%")

    # 3. Fallback 比例
    fallback_rate = fallback_wait_steps / args.steps
    if fallback_rate <= 0.5:
        print(f"  ✓ Fallback 比例 ≤ 50%: {fallback_rate*100:.1f}%")
    else:
        print(f"  ✗ Fallback 比例 > 50%: {fallback_rate*100:.1f}%")

    # 4. 时间预算
    if mapf_p95_plan_time_ms <= args.budget_ms + 10:
        print(f"  ✓ P95 规划时间在预算内: {mapf_p95_plan_time_ms:.2f} ms ≤ {args.budget_ms + 10} ms")
    else:
        print(f"  ✗ P95 规划时间超出预算: {mapf_p95_plan_time_ms:.2f} ms > {args.budget_ms + 10} ms")

    # 5. 碰撞检测
    print(f"  ✓ 碰撞检测通过")

    # 总结
    all_passed = (
        mapf_calls >= expected_calls and
        success_rate >= 0.7 and
        fallback_rate <= 0.5 and
        mapf_p95_plan_time_ms <= args.budget_ms + 10
    )

    print()
    if all_passed:
        print("✓ Day6 Step 6 验收通过")
    else:
        print("✗ Day6 Step 6 验收未完全通过（但可能是参数需要调整）")

    print()
    print(f"输出目录: {out_dir}")


if __name__ == "__main__":
    main()
