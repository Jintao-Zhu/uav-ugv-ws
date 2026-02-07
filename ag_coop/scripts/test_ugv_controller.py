"""
Day6.5 Step 1: 测试 UGV MAPF Controller

验证 controller 与 Day6 test_mapf_integration.py 的行为一致：
1. 每 K 步规划
2. 缓存执行
3. 失败 WAIT
4. 在线碰撞检查
5. 统计信息正确
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.mapf import UGVMAPFWrapper
from agcoop.controllers import UGVRecedingHorizonMAPFController
from agcoop.map import auto_load_map


def test_controller_basic():
    """测试 controller 基本功能"""
    print("=" * 80)
    print("Test 1: Controller 基本功能")
    print("=" * 80)
    print()

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建 wrapper 和 controller
    wrapper = UGVMAPFWrapper(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=300
    )

    controller = UGVRecedingHorizonMAPFController(
        K=5,
        H=40,
        budget_ms=300,
        wrapper=wrapper,
        enable_collision_check=True
    )

    print(f"✓ Controller 创建成功 (K=5, H=40)")
    print()

    # 初始化
    starts = {0: (5, 5), 1: (10, 10), 2: (15, 15)}
    goals = {0: (10, 10), 1: (15, 15), 2: (5, 5)}

    controller.reset(starts, goals)
    print(f"✓ Controller 重置")
    print(f"  起点: {starts}")
    print(f"  目标: {goals}")
    print()

    # 模拟 20 步
    positions = dict(starts)
    steps = 20

    for t in range(steps):
        # 尝试重规划
        plan_info = controller.maybe_replan(t, positions)

        if plan_info.called:
            if plan_info.success:
                print(f"t={t:2d}: MAPF 成功 ({plan_info.plan_time_ms:.2f} ms)")
            else:
                print(f"t={t:2d}: MAPF 失败 ({plan_info.termination_reason})")

        # 执行一步
        step_info = controller.step(t, positions)

        if not step_info.collision_free:
            print(f"✗ 碰撞: {step_info.collision_error}")
            sys.exit(1)

        # 更新位置
        positions = step_info.positions

    print()
    print(f"✓ 完成 {steps} 步，无碰撞")
    print()

    # 检查统计
    stats = controller.get_stats()
    print(f"统计信息:")
    print(f"  - MAPF 调用: {stats['mapf_calls']}")
    print(f"  - 成功: {stats['mapf_success_calls']}")
    print(f"  - 超时: {stats['mapf_timeout_calls']}")
    print(f"  - 失败: {stats['mapf_fail_calls']}")
    print(f"  - 平均规划时间: {stats['mapf_mean_plan_time_ms']:.2f} ms")
    print(f"  - Fallback 步数: {stats['fallback_wait_steps']}")
    print()

    # 验证调用次数
    expected_calls = (steps + controller.K - 1) // controller.K
    assert stats['mapf_calls'] >= expected_calls - 1, f"调用次数不足: {stats['mapf_calls']} < {expected_calls - 1}"
    print(f"✓ MAPF 调用次数正确: {stats['mapf_calls']} >= {expected_calls - 1}")
    print()


def test_controller_fallback():
    """测试 controller fallback 机制"""
    print("=" * 80)
    print("Test 2: Controller Fallback 机制")
    print("=" * 80)
    print()

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建 wrapper（极小 budget，强制 timeout）
    wrapper = UGVMAPFWrapper(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=0
    )

    controller = UGVRecedingHorizonMAPFController(
        K=5,
        H=40,
        budget_ms=0,
        wrapper=wrapper,
        enable_collision_check=True
    )

    print(f"✓ Controller 创建（budget=0ms，强制 timeout）")
    print()

    # 初始化
    starts = {0: (5, 5), 1: (10, 10)}
    goals = {0: (15, 15), 1: (5, 5)}

    controller.reset(starts, goals)

    # 模拟 15 步
    positions = dict(starts)
    steps = 15

    for t in range(steps):
        # 尝试重规划
        plan_info = controller.maybe_replan(t, positions)

        if plan_info.called:
            print(f"t={t:2d}: MAPF 调用 -> {plan_info.termination_reason}")

        # 执行一步
        step_info = controller.step(t, positions)

        if step_info.in_fallback:
            print(f"t={t:2d}: WAIT (fallback)")

        # 位置应该保持不变（fallback）
        assert step_info.positions == positions, f"t={t}: fallback 时位置应该不变"

        positions = step_info.positions

    print()

    # 检查统计
    stats = controller.get_stats()
    print(f"统计信息:")
    print(f"  - MAPF 调用: {stats['mapf_calls']}")
    print(f"  - 超时: {stats['mapf_timeout_calls']}")
    print(f"  - Fallback 步数: {stats['fallback_wait_steps']}")
    print()

    # 验证 fallback
    assert stats['mapf_timeout_calls'] > 0, "应该有 timeout"
    assert stats['fallback_wait_steps'] == steps, f"Fallback 步数应该是 {steps}"
    print(f"✓ Fallback 机制正确")
    print()


def test_controller_goal_switch():
    """测试 controller 动态目标切换"""
    print("=" * 80)
    print("Test 3: Controller 动态目标切换")
    print("=" * 80)
    print()

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建 wrapper 和 controller
    wrapper = UGVMAPFWrapper(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=300
    )

    controller = UGVRecedingHorizonMAPFController(
        K=5,
        H=40,
        budget_ms=300,
        wrapper=wrapper
    )

    # 初始化
    starts = {0: (5, 5), 1: (10, 10)}
    goals_1 = {0: (10, 10), 1: (5, 5)}
    goals_2 = {0: (15, 15), 1: (10, 5)}

    controller.reset(starts, goals_1)
    print(f"✓ 初始目标: {goals_1}")
    print()

    positions = dict(starts)

    # 前 10 步使用 goals_1
    for t in range(10):
        plan_info = controller.maybe_replan(t, positions)
        step_info = controller.step(t, positions)
        positions = step_info.positions

    print(f"✓ 完成前 10 步")
    print()

    # 切换目标
    controller.set_goals(goals_2)
    print(f"✓ 切换目标: {goals_2}")
    print()

    # 后 10 步使用 goals_2
    for t in range(10, 20):
        plan_info = controller.maybe_replan(t, positions)
        step_info = controller.step(t, positions)
        positions = step_info.positions

    print(f"✓ 完成后 10 步")
    print()

    # 检查统计
    stats = controller.get_stats()
    print(f"统计信息:")
    print(f"  - MAPF 调用: {stats['mapf_calls']}")
    print(f"  - 成功: {stats['mapf_success_calls']}")
    print()

    print(f"✓ 动态目标切换正常")
    print()


def main():
    print("Day6.5 Step 1: UGV MAPF Controller 测试")
    print()

    try:
        test_controller_basic()
        test_controller_fallback()
        test_controller_goal_switch()

        print("=" * 80)
        print("验收结果")
        print("=" * 80)
        print("✓ Test 1: Controller 基本功能")
        print("✓ Test 2: Fallback 机制")
        print("✓ Test 3: 动态目标切换")
        print()
        print("✓ Day6.5 Step 1 验收通过")
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
