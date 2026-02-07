"""
Day6.5 Step 0: UGV MAPF Wrapper 使用示例

展示如何在 core.py 中使用 wrapper 进行 receding horizon 规划
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.mapf import UGVMAPFWrapper
from agcoop.map import auto_load_map


def example_receding_horizon():
    """
    示例：Receding Horizon 规划

    模拟 core.py 中的使用场景：
    - 每 K 步调用 MAPF
    - 缓存路径并执行
    - 失败时 fallback WAIT
    """
    print("=" * 80)
    print("示例：Receding Horizon 规划")
    print("=" * 80)
    print()

    # 1. 初始化（在 core.py 的 __init__ 中）
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    wrapper = UGVMAPFWrapper(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=300
    )

    print("✓ MAPF Wrapper 初始化完成")
    print()

    # 2. 模拟 receding horizon 循环（在 core.py 的 step 中）
    K = 5  # 重规划周期
    H = 40  # 规划时间窗
    steps = 20  # 总步数

    # 初始状态
    positions = {0: (5, 5), 1: (10, 10), 2: (15, 15)}
    goals = {0: (15, 15), 1: (5, 5), 2: (10, 10)}

    # 路径缓存
    cache_paths = None
    cache_start_t = -1

    # Fallback 状态
    fallback_remaining = 0

    print(f"配置: K={K}, H={H}, steps={steps}")
    print(f"初始位置: {positions}")
    print(f"目标: {goals}")
    print()

    for t in range(steps):
        # 决策步
        if t % K == 0 and fallback_remaining == 0:
            print(f"t={t:2d}: 调用 MAPF 规划...")

            # 调用 wrapper
            result = wrapper.plan(
                starts=positions,
                goals=goals,
                H=H
            )

            if result.success:
                # 成功：缓存路径
                cache_paths = result.paths
                cache_start_t = t
                print(f"      ✓ 成功 ({result.plan_time_ms:.2f} ms, {result.expanded_nodes} nodes)")
            else:
                # 失败：触发 fallback
                fallback_remaining = K
                cache_paths = None
                print(f"      ✗ 失败 ({result.termination_reason}), 触发 fallback WAIT")

        # 执行步
        if fallback_remaining > 0:
            # Fallback WAIT
            fallback_remaining -= 1
            print(f"t={t:2d}: WAIT (fallback)")
        else:
            # 执行缓存路径
            offset = t - cache_start_t
            for agent_id in positions.keys():
                positions[agent_id] = cache_paths[agent_id][offset + 1]
            print(f"t={t:2d}: 执行路径 (offset={offset})")

    print()
    print("✓ Receding horizon 完成")
    print()

    # 3. 获取统计信息
    stats = wrapper.get_stats()
    print(f"统计信息:")
    print(f"  - 总调用: {stats['total_calls']}")
    print(f"  - 成功: {stats['success_calls']}")
    print(f"  - 超时: {stats['timeout_calls']}")
    print(f"  - 失败: {stats['fail_calls']}")
    print(f"  - 成功率: {stats['success_rate']*100:.1f}%")
    print()


def example_simple_usage():
    """
    示例：简单使用

    最简单的使用方式
    """
    print("=" * 80)
    print("示例：简单使用")
    print("=" * 80)
    print()

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建 wrapper
    wrapper = UGVMAPFWrapper(grid_map=grid_map)

    # 规划
    result = wrapper.plan(
        starts={0: (5, 5), 1: (10, 10)},
        goals={0: (10, 10), 1: (5, 5)},
        H=30
    )

    # 使用结果
    if result.success:
        print(f"✓ 规划成功")
        print(f"  路径: {result.paths}")
    else:
        print(f"✗ 规划失败: {result.termination_reason}")

    print()


def example_custom_budget():
    """
    示例：自定义时间预算

    展示如何为不同场景使用不同的时间预算
    """
    print("=" * 80)
    print("示例：自定义时间预算")
    print("=" * 80)
    print()

    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建 wrapper（默认 budget=300ms）
    wrapper = UGVMAPFWrapper(
        grid_map=grid_map,
        time_budget_ms=300
    )

    starts = {0: (5, 5), 1: (10, 10)}
    goals = {0: (15, 15), 1: (5, 5)}

    # 场景 1: 紧急情况，使用小 budget
    print("场景 1: 紧急情况 (budget=10ms)")
    result1 = wrapper.plan(starts=starts, goals=goals, H=30, budget_ms=10)
    print(f"  结果: {result1}")
    print()

    # 场景 2: 正常情况，使用默认 budget
    print("场景 2: 正常情况 (budget=300ms)")
    result2 = wrapper.plan(starts=starts, goals=goals, H=30)
    print(f"  结果: {result2}")
    print()

    # 场景 3: 复杂场景，使用大 budget
    print("场景 3: 复杂场景 (budget=1000ms)")
    result3 = wrapper.plan(starts=starts, goals=goals, H=30, budget_ms=1000)
    print(f"  结果: {result3}")
    print()


def main():
    print("Day6.5 Step 0: UGV MAPF Wrapper 使用示例")
    print()

    example_simple_usage()
    example_custom_budget()
    example_receding_horizon()

    print("=" * 80)
    print("所有示例完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
