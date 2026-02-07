#!/usr/bin/env python3
"""
测试 UAV 执行器和状态机
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.uav import UAVState, UAVExecutor


def test_uav_initialization():
    """测试 UAV 初始化"""
    print("\n" + "=" * 60)
    print("测试 UAV 初始化")
    print("=" * 60)

    uav = UAVExecutor(uav_id=0, cell=(5, 5))

    print(f"UAV: {uav}")
    print(f"状态: {uav.get_state()}")
    print(f"位置: {uav.get_position()}")

    assert uav.get_state() == UAVState.ONBOARD, "初始状态应该是 ONBOARD"
    assert uav.get_position() == (5, 5), "初始位置错误"
    assert uav.carrier_id == 0, "默认载机 ID 应该是 0"

    print("✓ 初始化测试通过")


def test_uav_outbound():
    """测试 UAV OUTBOUND 状态（飞向任务点）"""
    print("\n" + "=" * 60)
    print("测试 UAV OUTBOUND 状态")
    print("=" * 60)

    uav = UAVExecutor(uav_id=0, cell=(5, 5))

    # 设置为 OUTBOUND
    task_cell = (10, 10)
    uav.set_outbound(task_id=1, task_cell=task_cell)

    print(f"目标任务点: {task_cell}")
    print(f"当前状态: {uav.get_state()}")
    print(f"当前位置: {uav.get_position()}")

    assert uav.get_state() == UAVState.OUTBOUND, "状态应该是 OUTBOUND"
    assert uav.current_task_id == 1, "任务 ID 错误"
    assert uav.target_cell == task_cell, "目标位置错误"

    # 模拟移动
    steps = 0
    while not uav._is_at_target() and steps < 20:
        old_pos = uav.get_position()
        need_action = uav.step(t=steps)
        new_pos = uav.get_position()
        steps += 1

        if steps <= 5:  # 只打印前 5 步
            print(f"  步 {steps}: {old_pos} -> {new_pos}")

        if need_action:
            print(f"  到达任务点！总共 {steps} 步")
            break

    assert uav._is_at_target(), "应该到达任务点"
    assert uav.get_position() == task_cell, "最终位置应该是任务点"
    print(f"✓ OUTBOUND 测试通过（{steps} 步到达）")


def test_uav_servicing():
    """测试 UAV SERVICING 状态（服务任务）"""
    print("\n" + "=" * 60)
    print("测试 UAV SERVICING 状态")
    print("=" * 60)

    uav = UAVExecutor(uav_id=0, cell=(10, 10), service_time=3)

    # 设置为 SERVICING
    uav.set_servicing(task_id=1)

    print(f"服务时间: {uav.service_time}")
    print(f"当前状态: {uav.get_state()}")
    print(f"剩余服务时间: {uav.remaining_service}")

    assert uav.get_state() == UAVState.SERVICING, "状态应该是 SERVICING"
    assert uav.remaining_service == 3, "剩余服务时间错误"

    # 模拟服务
    for t in range(5):
        need_action = uav.step(t=t)
        print(f"  步 {t+1}: 剩余服务时间 = {uav.remaining_service}")

        if need_action:
            print(f"  服务完成！")
            break

    assert uav.remaining_service <= 0, "服务应该完成"
    print("✓ SERVICING 测试通过")


def test_uav_inbound():
    """测试 UAV INBOUND 状态（飞向会合点）"""
    print("\n" + "=" * 60)
    print("测试 UAV INBOUND 状态")
    print("=" * 60)

    uav = UAVExecutor(uav_id=0, cell=(10, 10))

    # 设置为 INBOUND
    rendezvous_cell = (5, 5)
    t_meet = 100
    uav.set_inbound(rendezvous_cell=rendezvous_cell, t_meet=t_meet, window=3)

    print(f"会合点: {rendezvous_cell}")
    print(f"预期会合时刻: {t_meet}")
    print(f"会合时间窗: ±{uav.meet_window}")
    print(f"当前状态: {uav.get_state()}")

    assert uav.get_state() == UAVState.INBOUND, "状态应该是 INBOUND"
    assert uav.rendezvous_cell == rendezvous_cell, "会合点错误"
    assert uav.t_meet == t_meet, "会合时刻错误"

    # 模拟移动
    steps = 0
    while not uav._is_at_target() and steps < 20:
        old_pos = uav.get_position()
        need_action = uav.step(t=steps)
        new_pos = uav.get_position()
        steps += 1

        if steps <= 5:  # 只打印前 5 步
            print(f"  步 {steps}: {old_pos} -> {new_pos}")

        if need_action:
            print(f"  到达会合点！总共 {steps} 步")
            break

    assert uav._is_at_target(), "应该到达会合点"
    assert uav.get_position() == rendezvous_cell, "最终位置应该是会合点"
    print(f"✓ INBOUND 测试通过（{steps} 步到达）")


def test_uav_emergency():
    """测试 UAV EMERGENCY 状态"""
    print("\n" + "=" * 60)
    print("测试 UAV EMERGENCY 状态")
    print("=" * 60)

    uav = UAVExecutor(uav_id=0, cell=(10, 10))

    # 设置为 EMERGENCY
    safe_cell = (1, 1)
    uav.set_emergency(target_cell=safe_cell)

    print(f"安全降落点: {safe_cell}")
    print(f"当前状态: {uav.get_state()}")

    assert uav.get_state() == UAVState.EMERGENCY, "状态应该是 EMERGENCY"
    assert uav.target_cell == safe_cell, "目标位置错误"
    assert uav.current_task_id is None, "任务 ID 应该被清除"

    # 模拟移动
    steps = 0
    while not uav._is_at_target() and steps < 20:
        need_action = uav.step(t=steps)
        steps += 1

        if need_action:
            print(f"  到达安全点！总共 {steps} 步")
            break

    assert uav._is_at_target(), "应该到达安全点"
    print("✓ EMERGENCY 测试通过")


def test_uav_movement_8_neighbor():
    """测试 UAV 8 邻接移动"""
    print("\n" + "=" * 60)
    print("测试 UAV 8 邻接移动（贪心）")
    print("=" * 60)

    uav = UAVExecutor(uav_id=0, cell=(0, 0), neighbor_mode=8)

    # 测试对角线移动
    uav.set_outbound(task_id=1, task_cell=(5, 5))

    print(f"起点: (0, 0)")
    print(f"终点: (5, 5)")
    print(f"预期路径: 对角线移动")

    path = [(0, 0)]
    for t in range(10):
        if uav._is_at_target():
            break
        uav.step(t=t)
        path.append(uav.get_position())

    print(f"实际路径: {path}")
    print(f"路径长度: {len(path) - 1} 步")

    # 验证：8 邻接对角线移动应该是 5 步
    assert len(path) - 1 == 5, "8 邻接对角线移动应该是 5 步"
    assert path[-1] == (5, 5), "最终位置错误"

    print("✓ 8 邻接移动测试通过")


def test_uav_state_transitions():
    """测试 UAV 状态转换"""
    print("\n" + "=" * 60)
    print("测试 UAV 状态转换")
    print("=" * 60)

    uav = UAVExecutor(uav_id=0, cell=(5, 5))

    # ONBOARD -> OUTBOUND
    print("1. ONBOARD -> OUTBOUND")
    assert uav.get_state() == UAVState.ONBOARD
    uav.set_outbound(task_id=1, task_cell=(10, 10))
    assert uav.get_state() == UAVState.OUTBOUND
    print("   ✓")

    # OUTBOUND -> SERVICING
    print("2. OUTBOUND -> SERVICING")
    while not uav._is_at_target():
        uav.step(t=0)
    uav.set_servicing(task_id=1)
    assert uav.get_state() == UAVState.SERVICING
    print("   ✓")

    # SERVICING -> INBOUND
    print("3. SERVICING -> INBOUND")
    while uav.remaining_service > 0:
        uav.step(t=0)
    uav.set_inbound(rendezvous_cell=(5, 5), t_meet=100)
    assert uav.get_state() == UAVState.INBOUND
    print("   ✓")

    # INBOUND -> ONBOARD
    print("4. INBOUND -> ONBOARD")
    while not uav._is_at_target():
        uav.step(t=0)
    uav.set_onboard(carrier_id=0, carrier_cell=(5, 5))
    assert uav.get_state() == UAVState.ONBOARD
    print("   ✓")

    # 任意状态 -> EMERGENCY
    print("5. 任意状态 -> EMERGENCY")
    uav.set_emergency(target_cell=(1, 1))
    assert uav.get_state() == UAVState.EMERGENCY
    print("   ✓")

    print("✓ 状态转换测试通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("UAV 执行器测试")
    print("=" * 60)

    try:
        test_uav_initialization()
        test_uav_outbound()
        test_uav_servicing()
        test_uav_inbound()
        test_uav_emergency()
        test_uav_movement_8_neighbor()
        test_uav_state_transitions()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        raise


if __name__ == "__main__":
    main()
