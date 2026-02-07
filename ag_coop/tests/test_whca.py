"""
Day6 Step 3 验收测试：WHCA* / Prioritized MAPF

验证：
1. 2 agents 互换位置的 swap 场景：算法必须给出无 swap 的联合路径
2. 3 agents 走廊瓶颈：成功率≥1（至少成功一次）且无冲突
3. 失败场景：把 H 设太小，必须 success=False，并有 failure_reason
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.mapf import MAPFPlanner
from agcoop.map import auto_load_map


def test_swap_scenario():
    """测试 1: 2 agents 互换位置的 swap 场景"""
    print("\n" + "=" * 80)
    print("测试 1: 2 Agents 互换位置（Swap 场景）")
    print("=" * 80)

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建 MAPF 规划器
    planner = MAPFPlanner(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=1000
    )

    # 2 agents 互换位置
    # Agent 0: (5, 5) -> (7, 5)
    # Agent 1: (7, 5) -> (5, 5)
    starts = {0: (5, 5), 1: (7, 5)}
    goals = {0: (7, 5), 1: (5, 5)}
    H = 20

    print(f"  Agent 0: {starts[0]} -> {goals[0]}")
    print(f"  Agent 1: {starts[1]} -> {goals[1]}")
    print(f"  时间窗 H: {H}")

    # 规划路径
    result = planner.plan_mapf(
        starts=starts,
        goals=goals,
        H=H,
        priority_order=[0, 1]
    )

    print(f"\n  规划结果: {result}")

    # 检查是否成功
    assert result.success, f"规划失败: {result.failure_reason}"
    print(f"  ✓ 规划成功")

    # 检查路径数量
    assert len(result.paths) == 2, f"路径数量错误: {len(result.paths)}"
    print(f"  ✓ 路径数量正确: {len(result.paths)}")

    # 验证解的正确性（无碰撞）
    is_valid, error = planner.validate_solution(result.paths)
    assert is_valid, f"解无效: {error}"
    print(f"  ✓ 解有效（无碰撞）")

    # 检查起点和终点
    for agent_id in [0, 1]:
        path = result.paths[agent_id]
        assert path[0] == starts[agent_id], f"Agent {agent_id} 起点错误"
        # 检查是否到达目标（可能在路径中间到达，然后 stay）
        assert goals[agent_id] in path, f"Agent {agent_id} 未到达目标"
        print(f"  ✓ Agent {agent_id} 起点和终点正确")

    # 打印路径前几步
    print(f"\n  Agent 0 路径前 5 步: {result.paths[0][:5]}")
    print(f"  Agent 1 路径前 5 步: {result.paths[1][:5]}")

    print("\n✓ 2 Agents 互换位置测试通过")
    return True


def test_corridor_bottleneck():
    """测试 2: 3 agents 走廊瓶颈"""
    print("\n" + "=" * 80)
    print("测试 2: 3 Agents 走廊瓶颈")
    print("=" * 80)

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建 MAPF 规划器
    planner = MAPFPlanner(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=2000
    )

    # 3 agents 在走廊中相遇
    # Agent 0: (5, 5) -> (15, 5)
    # Agent 1: (10, 5) -> (5, 5)
    # Agent 2: (5, 10) -> (15, 10)
    starts = {0: (5, 5), 1: (10, 5), 2: (5, 10)}
    goals = {0: (15, 5), 1: (5, 5), 2: (15, 10)}
    H = 30

    print(f"  Agent 0: {starts[0]} -> {goals[0]}")
    print(f"  Agent 1: {starts[1]} -> {goals[1]}")
    print(f"  Agent 2: {starts[2]} -> {goals[2]}")
    print(f"  时间窗 H: {H}")

    # 规划路径
    result = planner.plan_mapf(
        starts=starts,
        goals=goals,
        H=H,
        priority_order=[0, 1, 2]
    )

    print(f"\n  规划结果: {result}")

    # 检查是否成功（至少成功一次）
    assert result.success, f"规划失败: {result.failure_reason}"
    print(f"  ✓ 规划成功")

    # 检查路径数量
    assert len(result.paths) == 3, f"路径数量错误: {len(result.paths)}"
    print(f"  ✓ 路径数量正确: {len(result.paths)}")

    # 验证解的正确性（无碰撞）
    is_valid, error = planner.validate_solution(result.paths)
    assert is_valid, f"解无效: {error}"
    print(f"  ✓ 解有效（无碰撞）")

    # 检查起点和终点
    for agent_id in [0, 1, 2]:
        path = result.paths[agent_id]
        assert path[0] == starts[agent_id], f"Agent {agent_id} 起点错误"
        assert goals[agent_id] in path, f"Agent {agent_id} 未到达目标"
        print(f"  ✓ Agent {agent_id} 起点和终点正确")

    print("\n✓ 3 Agents 走廊瓶颈测试通过")
    return True


def test_failure_scenario():
    """测试 3: 失败场景（H 太小）"""
    print("\n" + "=" * 80)
    print("测试 3: 失败场景（H 太小）")
    print("=" * 80)

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建 MAPF 规划器
    planner = MAPFPlanner(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=1000
    )

    # 2 agents，但 H 太小
    starts = {0: (5, 5), 1: (7, 5)}
    goals = {0: (15, 15), 1: (5, 15)}
    H = 3  # 太小，无法到达目标

    print(f"  Agent 0: {starts[0]} -> {goals[0]}")
    print(f"  Agent 1: {starts[1]} -> {goals[1]}")
    print(f"  时间窗 H: {H} (太小)")

    # 规划路径
    result = planner.plan_mapf(
        starts=starts,
        goals=goals,
        H=H,
        priority_order=[0, 1]
    )

    print(f"\n  规划结果: {result}")

    # 检查是否失败
    assert not result.success, "应该规划失败，但返回成功"
    print(f"  ✓ 正确检测到失败")

    # 检查失败原因
    assert result.failure_reason in ["no_path", "timeout"], \
        f"失败原因错误: {result.failure_reason}"
    print(f"  ✓ 失败原因正确: {result.failure_reason}")

    print("\n✓ 失败场景测试通过")
    return True


def test_timeout_scenario():
    """测试 4: 超时场景"""
    print("\n" + "=" * 80)
    print("测试 4: 超时场景")
    print("=" * 80)

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建 MAPF 规划器（极小的时间预算）
    planner = MAPFPlanner(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=0.1  # 极小的时间预算
    )

    # 多个 agents，复杂场景
    starts = {0: (5, 5), 1: (10, 5), 2: (15, 5), 3: (5, 10)}
    goals = {0: (50, 50), 1: (50, 45), 2: (50, 40), 3: (50, 35)}
    H = 100

    print(f"  4 agents，目标距离很远")
    print(f"  时间预算: 0.1 ms (极小)")

    # 规划路径
    result = planner.plan_mapf(
        starts=starts,
        goals=goals,
        H=H,
        priority_order=[0, 1, 2, 3]
    )

    print(f"\n  规划结果: {result}")

    # 检查是否超时
    assert not result.success, "应该超时失败"
    assert result.failure_reason == "timeout", f"应该是超时，但是: {result.failure_reason}"
    print(f"  ✓ 正确检测到超时")

    print("\n✓ 超时场景测试通过")
    return True


def main():
    """运行所有测试"""
    print("=" * 80)
    print("Day6 Step 3 验收测试：WHCA* / Prioritized MAPF")
    print("=" * 80)

    tests = [
        ("2 Agents 互换位置", test_swap_scenario),
        ("3 Agents 走廊瓶颈", test_corridor_bottleneck),
        ("失败场景（H 太小）", test_failure_scenario),
        ("超时场景", test_timeout_scenario),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except AssertionError as e:
            print(f"\n✗ 测试失败: {name}")
            print(f"  断言错误: {e}")
            results.append((name, False))
        except Exception as e:
            print(f"\n✗ 测试失败: {name}")
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # 打印总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    for name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {name}")

    all_passed = all(success for _, success in results)

    if all_passed:
        print("\n" + "=" * 80)
        print("✓ Day6 Step 3 验收通过")
        print("=" * 80)
        print("\n验收标准：")
        print("  ✓ 2 agents 互换位置：算法给出无 swap 的联合路径")
        print("  ✓ 3 agents 走廊瓶颈：成功率≥1 且无冲突")
        print("  ✓ 失败场景：H 太小时返回 success=False 和 failure_reason")
        print("  ✓ 超时场景：时间预算极小时返回 timeout")
    else:
        print("\n✗ 部分测试失败，请检查")
        sys.exit(1)


if __name__ == "__main__":
    main()
