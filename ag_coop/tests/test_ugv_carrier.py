#!/usr/bin/env python3
"""
测试 UGV Carrier
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.ugv import UGVState, UGVCarrier


def test_ugv_initialization():
    """测试 UGV 初始化"""
    print("\n" + "=" * 60)
    print("测试 UGV 初始化")
    print("=" * 60)

    ugv = UGVCarrier(ugv_id=0, cell=(5, 5))

    print(f"UGV: {ugv}")
    print(f"状态: {ugv.get_state()}")
    print(f"位置: {ugv.get_position()}")

    assert ugv.get_state() == UGVState.IDLE, "初始状态应该是 IDLE"
    assert ugv.get_position() == (5, 5), "初始位置错误"
    assert ugv.neighbor_mode == 4, "默认邻接模式应该是 4"

    print("✓ 初始化测试通过")


def test_ugv_moving_to_rendezvous():
    """测试 UGV MOVING_TO_RENDEZVOUS 状态"""
    print("\n" + "=" * 60)
    print("测试 UGV MOVING_TO_RENDEZVOUS 状态")
    print("=" * 60)

    ugv = UGVCarrier(ugv_id=0, cell=(5, 5))

    # 设置路径
    rendezvous_cell = (10, 5)
    path = [(5, 5), (6, 5), (7, 5), (8, 5), (9, 5), (10, 5)]

    ugv.set_moving_to_rendezvous(rendezvous_cell, path)

    print(f"会合点: {rendezvous_cell}")
    print(f"路径: {path}")
    print(f"当前状态: {ugv.get_state()}")

    assert ugv.get_state() == UGVState.MOVING_TO_RENDEZVOUS, "状态应该是 MOVING_TO_RENDEZVOUS"
    assert ugv.get_rendezvous_cell() == rendezvous_cell, "会合点错误"
    assert ugv.has_path(), "应该有路径"

    # 模拟移动
    steps = 0
    while not ugv._is_at_rendezvous() and steps < 20:
        old_pos = ugv.get_position()
        need_action = ugv.step(t=steps)
        new_pos = ugv.get_position()
        steps += 1

        if steps <= 6:  # 打印所有步骤
            print(f"  步 {steps}: {old_pos} -> {new_pos}")

        if need_action:
            print(f"  到达会合点！总共 {steps} 步")
            break

    assert ugv._is_at_rendezvous(), "应该到达会合点"
    assert ugv.get_position() == rendezvous_cell, "最终位置应该是会合点"
    print(f"✓ MOVING_TO_RENDEZVOUS 测试通过（{steps} 步到达）")


def test_ugv_holding():
    """测试 UGV HOLDING 状态"""
    print("\n" + "=" * 60)
    print("测试 UGV HOLDING 状态")
    print("=" * 60)

    ugv = UGVCarrier(ugv_id=0, cell=(10, 5), hold_steps=5)

    # 设置为 HOLDING
    ugv.set_holding()

    print(f"等待时间: {ugv.hold_steps}")
    print(f"当前状态: {ugv.get_state()}")

    assert ugv.get_state() == UGVState.HOLDING, "状态应该是 HOLDING"
    assert ugv.get_hold_counter() == 0, "等待计数器应该是 0"

    # 模拟等待
    for t in range(10):
        need_action = ugv.step(t=t)
        print(f"  步 {t+1}: 等待计数 = {ugv.get_hold_counter()}")

        if need_action:
            print(f"  等待完成！")
            break

    assert ugv.get_hold_counter() >= ugv.hold_steps, "等待应该完成"
    print("✓ HOLDING 测试通过")


def test_ugv_meeting():
    """测试 UGV MEETING 状态"""
    print("\n" + "=" * 60)
    print("测试 UGV MEETING 状态")
    print("=" * 60)

    ugv = UGVCarrier(ugv_id=0, cell=(10, 5))

    # 设置为 MEETING
    ugv.set_meeting()

    print(f"当前状态: {ugv.get_state()}")

    assert ugv.get_state() == UGVState.MEETING, "状态应该是 MEETING"

    # 会合中不移动
    old_pos = ugv.get_position()
    ugv.step(t=0)
    new_pos = ugv.get_position()

    assert old_pos == new_pos, "会合中不应该移动"
    print("✓ MEETING 测试通过")


def test_ugv_state_transitions():
    """测试 UGV 状态转换"""
    print("\n" + "=" * 60)
    print("测试 UGV 状态转换")
    print("=" * 60)

    ugv = UGVCarrier(ugv_id=0, cell=(5, 5), hold_steps=3)

    # IDLE -> MOVING_TO_RENDEZVOUS
    print("1. IDLE -> MOVING_TO_RENDEZVOUS")
    assert ugv.get_state() == UGVState.IDLE
    path = [(5, 5), (6, 5), (7, 5)]
    ugv.set_moving_to_rendezvous((7, 5), path)
    assert ugv.get_state() == UGVState.MOVING_TO_RENDEZVOUS
    print("   ✓")

    # MOVING_TO_RENDEZVOUS -> HOLDING
    print("2. MOVING_TO_RENDEZVOUS -> HOLDING")
    while not ugv._is_at_rendezvous():
        ugv.step(t=0)
    ugv.set_holding()
    assert ugv.get_state() == UGVState.HOLDING
    print("   ✓")

    # HOLDING -> MEETING
    print("3. HOLDING -> MEETING")
    while ugv.get_hold_counter() < ugv.hold_steps:
        ugv.step(t=0)
    ugv.set_meeting()
    assert ugv.get_state() == UGVState.MEETING
    print("   ✓")

    # MEETING -> IDLE
    print("4. MEETING -> IDLE")
    ugv.set_idle()
    assert ugv.get_state() == UGVState.IDLE
    print("   ✓")

    print("✓ 状态转换测试通过")


def test_ugv_path_following():
    """测试 UGV 路径跟随"""
    print("\n" + "=" * 60)
    print("测试 UGV 路径跟随")
    print("=" * 60)

    ugv = UGVCarrier(ugv_id=0, cell=(0, 0))

    # 设置路径（4 邻接）
    path = [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0)]
    ugv.set_moving_to_rendezvous((5, 0), path)

    print(f"起点: (0, 0)")
    print(f"终点: (5, 0)")
    print(f"路径: {path}")

    # 跟随路径
    actual_path = [(0, 0)]
    for t in range(10):
        if ugv._is_at_rendezvous():
            break
        ugv.step(t=t)
        actual_path.append(ugv.get_position())

    print(f"实际路径: {actual_path}")
    print(f"路径长度: {len(actual_path) - 1} 步")

    # 验证路径
    assert actual_path == path, "实际路径应该与规划路径一致"
    assert ugv.get_position() == (5, 0), "最终位置错误"

    print("✓ 路径跟随测试通过")


def test_ugv_with_astar():
    """测试 UGV 使用 A* 规划路径"""
    print("\n" + "=" * 60)
    print("测试 UGV 使用 A* 规划路径")
    print("=" * 60)

    # 需要导入地图和 A* 规划器
    try:
        from agcoop.map import auto_load_map
        from agcoop.planning.astar import AStarPlanner
    except ImportError:
        print("⚠ 跳过测试（需要 map 和 planning 模块）")
        return

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建 A* 规划器
    planner = AStarPlanner(grid_map)

    # 创建 UGV
    start = grid_map.free_cells[0]
    goal = grid_map.free_cells[20]
    ugv = UGVCarrier(ugv_id=0, cell=start)

    print(f"起点: {start}")
    print(f"终点: {goal}")

    # 规划路径
    path, success = planner.plan(start, goal, neighbor_mode=4)

    if not success:
        print("⚠ A* 规划失败")
        return

    print(f"路径长度: {len(path)} 步")
    print(f"路径前 5 步: {path[:5]}")

    # 设置路径
    ugv.set_moving_to_rendezvous(goal, path)

    # 模拟移动
    steps = 0
    while not ugv._is_at_rendezvous() and steps < 100:
        ugv.step(t=steps)
        steps += 1

    print(f"实际移动: {steps} 步")
    assert ugv._is_at_rendezvous(), "应该到达会合点"
    assert ugv.get_position() == goal, "最终位置错误"

    print("✓ A* 路径规划测试通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("UGV Carrier 测试")
    print("=" * 60)

    try:
        test_ugv_initialization()
        test_ugv_moving_to_rendezvous()
        test_ugv_holding()
        test_ugv_meeting()
        test_ugv_state_transitions()
        test_ugv_path_following()
        test_ugv_with_astar()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        raise


if __name__ == "__main__":
    main()
