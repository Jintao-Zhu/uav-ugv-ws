"""
Day6.5 Step 0: 测试 UGV MAPF Wrapper 接口

验证：
1. Wrapper 接口正确工作
2. 返回结果包含所有必需字段
3. 统计信息正确
4. 与原始 test_mapf_integration.py 兼容（防回归）
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.mapf import UGVMAPFWrapper, UGVMAPFResult
from agcoop.map import auto_load_map


def test_wrapper_basic():
    """测试 wrapper 基本功能"""
    print("=" * 80)
    print("Test 1: Wrapper 基本功能")
    print("=" * 80)
    print()

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))
    print(f"✓ 地图加载: map_01 ({grid_map.width}x{grid_map.height})")

    # 创建 wrapper
    wrapper = UGVMAPFWrapper(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=300
    )
    print(f"✓ Wrapper 创建成功")
    print()

    # 测试场景
    starts = {
        0: (5, 5),
        1: (10, 10),
        2: (15, 15)
    }

    goals = {
        0: (15, 15),
        1: (5, 5),
        2: (10, 10)
    }

    print(f"起点: {starts}")
    print(f"目标: {goals}")
    print()

    # 调用规划
    result = wrapper.plan(
        starts=starts,
        goals=goals,
        H=40
    )

    print(f"规划结果: {result}")
    print()

    # 验证结果字段
    assert hasattr(result, 'success'), "缺少 success 字段"
    assert hasattr(result, 'plan_time_ms'), "缺少 plan_time_ms 字段"
    assert hasattr(result, 'termination_reason'), "缺少 termination_reason 字段"
    assert hasattr(result, 'expanded_nodes'), "缺少 expanded_nodes 字段"
    assert hasattr(result, 'paths'), "缺少 paths 字段"

    print("✓ 所有必需字段存在")
    print()

    if result.success:
        print(f"✓ 规划成功")
        print(f"  - 规划时间: {result.plan_time_ms:.2f} ms")
        print(f"  - 展开节点: {result.expanded_nodes}")
        print(f"  - Makespan: {result.makespan}")
        print(f"  - Sum of costs: {result.sum_of_costs}")
        print(f"  - 路径数量: {len(result.paths)}")

        # 验证路径
        for agent_id, path in result.paths.items():
            assert path[0] == starts[agent_id], f"Agent {agent_id} 起点错误"
            assert path[-1] == goals[agent_id], f"Agent {agent_id} 终点错误"

        print(f"✓ 所有路径起点和终点正确")
    else:
        print(f"✗ 规划失败: {result.termination_reason}")

    print()

    # 检查统计信息
    stats = wrapper.get_stats()
    print(f"统计信息: {stats}")
    assert stats['total_calls'] == 1, "调用次数错误"
    assert stats['success_calls'] == (1 if result.success else 0), "成功次数错误"
    print(f"✓ 统计信息正确")
    print()


def test_wrapper_timeout():
    """测试 wrapper timeout 处理"""
    print("=" * 80)
    print("Test 2: Wrapper Timeout 处理")
    print("=" * 80)
    print()

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建 wrapper（极小 budget）
    wrapper = UGVMAPFWrapper(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=0  # 强制 timeout
    )
    print(f"✓ Wrapper 创建（budget=0ms）")
    print()

    # 测试场景
    starts = {0: (5, 5), 1: (10, 10)}
    goals = {0: (15, 15), 1: (5, 5)}

    # 调用规划
    result = wrapper.plan(
        starts=starts,
        goals=goals,
        H=40
    )

    print(f"规划结果: {result}")
    print()

    # 验证 timeout
    assert not result.success, "应该失败"
    assert result.termination_reason == "timeout", f"应该是 timeout，实际是 {result.termination_reason}"
    assert result.paths is None, "失败时 paths 应该是 None"

    print(f"✓ Timeout 正确处理")
    print(f"  - termination_reason: {result.termination_reason}")
    print(f"  - plan_time_ms: {result.plan_time_ms:.4f}")
    print(f"  - expanded_nodes: {result.expanded_nodes}")
    print()

    # 检查统计
    stats = wrapper.get_stats()
    assert stats['timeout_calls'] == 1, "timeout 次数错误"
    print(f"✓ 统计信息正确: {stats}")
    print()


def test_wrapper_multiple_calls():
    """测试 wrapper 多次调用"""
    print("=" * 80)
    print("Test 3: Wrapper 多次调用")
    print("=" * 80)
    print()

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建 wrapper
    wrapper = UGVMAPFWrapper(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=300
    )

    # 多次调用
    n_calls = 5
    success_count = 0

    for i in range(n_calls):
        starts = {0: (5 + i, 5), 1: (10, 10 + i)}
        goals = {0: (15, 15), 1: (5, 5)}

        result = wrapper.plan(starts=starts, goals=goals, H=40)

        if result.success:
            success_count += 1

        print(f"  Call {i+1}: {result}")

    print()

    # 检查统计
    stats = wrapper.get_stats()
    print(f"统计信息: {stats}")

    assert stats['total_calls'] == n_calls, f"总调用次数错误: {stats['total_calls']} != {n_calls}"
    assert stats['success_calls'] == success_count, f"成功次数错误: {stats['success_calls']} != {success_count}"

    print(f"✓ 多次调用统计正确")
    print()


def test_backward_compatibility():
    """测试向后兼容性（与原始 MAPFPlanner 接口兼容）"""
    print("=" * 80)
    print("Test 4: 向后兼容性")
    print("=" * 80)
    print()

    from agcoop.mapf import MAPFPlanner

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 原始接口仍然可用
    planner = MAPFPlanner(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=300
    )

    starts = {0: (5, 5), 1: (10, 10)}
    goals = {0: (15, 15), 1: (5, 5)}

    result = planner.plan_mapf(
        starts=starts,
        goals=goals,
        H=40
    )

    print(f"✓ 原始 MAPFPlanner 接口仍然可用")
    print(f"  Result: {result}")
    print()


def main():
    print("Day6.5 Step 0: UGV MAPF Wrapper 接口测试")
    print()

    try:
        test_wrapper_basic()
        test_wrapper_timeout()
        test_wrapper_multiple_calls()
        test_backward_compatibility()

        print("=" * 80)
        print("验收结果")
        print("=" * 80)
        print("✓ Test 1: Wrapper 基本功能")
        print("✓ Test 2: Timeout 处理")
        print("✓ Test 3: 多次调用")
        print("✓ Test 4: 向后兼容性")
        print()
        print("✓ Day6.5 Step 0 验收通过")
        print()

    except AssertionError as e:
        print(f"✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
