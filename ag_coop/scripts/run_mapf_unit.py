"""
Day6 Step 4: MAPF 单元测试脚本

批量测试 MAPF 规划器的性能和成功率。

用法:
    python scripts/run_mapf_unit.py --map map_01 --n 3 --H 30 --budget_ms 300 --seeds 0..20
"""

import sys
import argparse
import random
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.mapf import MAPFPlanner
from agcoop.map import auto_load_map


def generate_random_positions(
    grid_map,
    n: int,
    seed: int
) -> Tuple[dict, dict]:
    """
    生成随机的起点和终点

    Args:
        grid_map: 地图对象
        n: agent 数量
        seed: 随机种子

    Returns:
        (starts, goals)
    """
    random.seed(seed)

    # 收集所有空闲位置
    free_cells = []
    for x in range(grid_map.width):
        for y in range(grid_map.height):
            if grid_map.is_free(x, y):
                free_cells.append((x, y))

    if len(free_cells) < 2 * n:
        raise ValueError(f"地图空闲位置不足：需要 {2*n}，只有 {len(free_cells)}")

    # 随机选择起点和终点
    selected = random.sample(free_cells, 2 * n)
    starts = {i: selected[i] for i in range(n)}
    goals = {i: selected[n + i] for i in range(n)}

    return starts, goals


def run_single_test(
    planner: MAPFPlanner,
    starts: dict,
    goals: dict,
    H: int,
    seed: int
):
    """运行单次测试"""
    result = planner.plan_mapf(
        starts=starts,
        goals=goals,
        H=H,
        priority_order=sorted(starts.keys())
    )

    # 验证解的正确性
    collision_free = True
    collision_error = None
    if result.success:
        collision_free, collision_error = planner.validate_solution(result.paths)

    return {
        'seed': seed,
        'success': result.success,
        'timeout': result.timeout,
        'failure_reason': result.failure_reason,
        'solve_time_ms': result.solve_time_ms,
        'makespan': result.makespan,
        'sum_of_costs': result.sum_of_costs,
        'collision_free': collision_free,
        'collision_error': collision_error
    }


def parse_seed_range(seed_str: str) -> List[int]:
    """
    解析种子范围字符串

    Examples:
        "0..20" -> [0, 1, 2, ..., 20]
        "1,2,3" -> [1, 2, 3]
        "42" -> [42]
    """
    if '..' in seed_str:
        # 范围格式：0..20
        start, end = seed_str.split('..')
        return list(range(int(start), int(end) + 1))
    elif ',' in seed_str:
        # 列表格式：1,2,3
        return [int(s.strip()) for s in seed_str.split(',')]
    else:
        # 单个值：42
        return [int(seed_str)]


def main():
    parser = argparse.ArgumentParser(description='MAPF 单元测试脚本')
    parser.add_argument('--map', type=str, required=True, help='地图名称（如 map_01）')
    parser.add_argument('--n', type=int, required=True, help='agent 数量')
    parser.add_argument('--H', type=int, required=True, help='规划时间窗')
    parser.add_argument('--budget_ms', type=int, required=True, help='时间预算（毫秒）')
    parser.add_argument('--seeds', type=str, required=True, help='随机种子（如 0..20 或 1,2,3）')
    parser.add_argument('--connectivity', type=int, default=4, help='连通性（4 或 8）')

    args = parser.parse_args()

    # 加载地图
    map_path = project_root / "maps" / f"{args.map}.map"
    if not map_path.exists():
        print(f"✗ 地图文件不存在: {map_path}")
        sys.exit(1)

    grid_map = auto_load_map(str(map_path))
    print(f"✓ 加载地图: {args.map} ({grid_map.width}x{grid_map.height})")

    # 创建 MAPF 规划器
    planner = MAPFPlanner(
        grid_map=grid_map,
        connectivity=args.connectivity,
        time_budget_ms=args.budget_ms
    )

    # 解析种子范围
    seeds = parse_seed_range(args.seeds)
    print(f"✓ 测试种子: {len(seeds)} 个")
    print(f"✓ 参数: n={args.n}, H={args.H}, budget_ms={args.budget_ms}")
    print()

    # 运行测试
    results = []
    for seed in seeds:
        # 生成随机起点和终点
        starts, goals = generate_random_positions(grid_map, args.n, seed)

        # 运行测试
        result = run_single_test(planner, starts, goals, args.H, seed)
        results.append(result)

        # 打印结果
        status = "✓" if result['success'] else "✗"
        time_str = f"{result['solve_time_ms']:.2f}ms"
        if result['success']:
            collision_str = "✓" if result['collision_free'] else f"✗ {result['collision_error']}"
            print(f"  {status} seed={seed:3d} | {time_str:>8s} | makespan={result['makespan']:3d} | collision={collision_str}")
        else:
            reason = result['failure_reason'] or 'unknown'
            print(f"  {status} seed={seed:3d} | {time_str:>8s} | FAILED: {reason}")

    # 统计结果
    print()
    print("=" * 80)
    print("统计结果")
    print("=" * 80)

    total = len(results)
    success_count = sum(1 for r in results if r['success'])
    timeout_count = sum(1 for r in results if r['timeout'])
    no_path_count = sum(1 for r in results if r['failure_reason'] == 'no_path')
    collision_count = sum(1 for r in results if r['success'] and not r['collision_free'])

    success_rate = success_count / total * 100 if total > 0 else 0

    print(f"  总测试数: {total}")
    print(f"  成功: {success_count} ({success_rate:.1f}%)")
    print(f"  失败: {total - success_count}")
    print(f"    - 超时: {timeout_count}")
    print(f"    - 无路径: {no_path_count}")
    print(f"  碰撞: {collision_count}")

    # 时间统计
    if results:
        solve_times = [r['solve_time_ms'] for r in results]
        avg_time = sum(solve_times) / len(solve_times)
        max_time = max(solve_times)
        min_time = min(solve_times)

        print(f"\n  求解时间:")
        print(f"    - 平均: {avg_time:.2f} ms")
        print(f"    - 最大: {max_time:.2f} ms")
        print(f"    - 最小: {min_time:.2f} ms")
        print(f"    - 预算: {args.budget_ms} ms")

        # 检查是否超出预算（允许 10ms 抖动）
        over_budget = [r for r in results if r['solve_time_ms'] > args.budget_ms + 10]
        if over_budget:
            print(f"\n  ⚠️  警告: {len(over_budget)} 次测试超出预算 (>{args.budget_ms + 10}ms)")

    # 验收标准检查
    print()
    print("=" * 80)
    print("验收标准检查")
    print("=" * 80)

    # 1. 成功率 ≥ 85%
    if success_rate >= 85:
        print(f"  ✓ 成功率 ≥ 85%: {success_rate:.1f}%")
    else:
        print(f"  ✗ 成功率 < 85%: {success_rate:.1f}%")

    # 2. 时间预算控制
    over_budget_count = sum(1 for r in results if r['solve_time_ms'] > args.budget_ms + 10)
    if over_budget_count == 0:
        print(f"  ✓ 所有测试在预算内 (≤{args.budget_ms + 10}ms)")
    else:
        print(f"  ✗ {over_budget_count} 次测试超出预算")

    # 3. 无碰撞
    if collision_count == 0:
        print(f"  ✓ 所有成功的解无碰撞")
    else:
        print(f"  ✗ {collision_count} 次成功的解有碰撞")

    # 总结
    all_passed = (success_rate >= 85 and over_budget_count == 0 and collision_count == 0)
    print()
    if all_passed:
        print("✓ Day6 Step 4 验收通过")
    else:
        print("✗ Day6 Step 4 验收未通过")
        sys.exit(1)


if __name__ == "__main__":
    main()
