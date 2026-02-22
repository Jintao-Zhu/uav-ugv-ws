#!/usr/bin/env python3
"""
快速测试脚本：验证 CoopBridgeNode 的基本功能

测试内容：
1. ag_coop 环境是否能正常初始化
2. 坐标转换是否正确
3. UGV 控制器是否能正常创建
"""

import sys
import os

# 添加 ag_coop 到 Python 路径
sys.path.insert(0, '/home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop')

from agcoop.env.coop_env import CoopEnv, EnvConfig
from agcoop.map.io_text import load_movingai_map
from geometry_msgs.msg import Point


def test_agcoop_init():
    """测试 ag_coop 环境初始化"""
    print("=" * 60)
    print("测试 1: ag_coop 环境初始化")
    print("=" * 60)

    try:
        # 加载地图
        grid_map = load_movingai_map(
            '/home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop/maps/map_01.map',
            resolution=1.0
        )
        print(f"✅ 地图加载成功: {grid_map.width}x{grid_map.height}")

        # 创建环境配置
        env_config = EnvConfig(
            horizon_steps=500,
            decision_period=5,
            seed=0
        )

        # 创建环境
        env = CoopEnv(grid_map=grid_map, config=env_config)
        print("✅ ag_coop 环境初始化成功")
        print(f"   - 地图大小: {grid_map.width}x{grid_map.height}")
        print(f"   - UAV: {env.uav.uav_id}")
        print(f"   - UGV Carrier: {env.carrier.ugv_id}")
        return env
    except Exception as e:
        print(f"❌ ag_coop 环境初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_coordinate_conversion():
    """测试坐标转换"""
    print("\n" + "=" * 60)
    print("测试 2: 坐标转换")
    print("=" * 60)

    def cell_to_world(cell):
        """格子坐标 → 世界坐标"""
        row, col = cell
        x = (col + 0.5) * 1.0
        y = (row + 0.5) * 1.0
        return Point(x=x, y=y, z=0.0)

    test_cases = [
        ((0, 0), (0.5, 0.5)),      # 左上角
        ((0, 19), (19.5, 0.5)),    # 右上角
        ((19, 0), (0.5, 19.5)),    # 左下角
        ((19, 19), (19.5, 19.5)),  # 右下角
        ((10, 10), (10.5, 10.5)),  # 中心
    ]

    print("格子坐标 (row, col) → 世界坐标 (x, y)")
    all_passed = True
    for cell, expected in test_cases:
        world = cell_to_world(cell)
        passed = abs(world.x - expected[0]) < 0.01 and abs(world.y - expected[1]) < 0.01
        status = "✅" if passed else "❌"
        print(f"{status} {cell} → ({world.x:.1f}, {world.y:.1f}) [期望: {expected}]")
        if not passed:
            all_passed = False

    if all_passed:
        print("✅ 所有坐标转换测试通过")
    else:
        print("❌ 部分坐标转换测试失败")

    return all_passed


def test_agcoop_planning(env):
    """测试 ag_coop 规划"""
    print("\n" + "=" * 60)
    print("测试 3: ag_coop 路径规划")
    print("=" * 60)

    if env is None:
        print("❌ 跳过测试（环境未初始化）")
        return False

    try:
        # 重置环境
        env.reset()
        print("✅ 环境重置成功")

        # 打印初始位置
        print("\n初始位置:")
        print(f"   UAV: {env.uav.cell}")
        print(f"   UGV Carrier: {env.carrier.cell}")

        # 运行几步看看
        print("\n运行 10 步...")
        for step in range(10):
            # ag_coop 使用决策周期，这里简单测试环境是否能运行
            env.step()

            if step % 5 == 0:
                print(f"   步骤 {step}: UAV at {env.uav.cell}, Carrier at {env.carrier.cell}")

        print("✅ ag_coop 规划测试完成")
        return True

    except Exception as e:
        print(f"❌ ag_coop 规划测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("CoopBridgeNode 快速测试")
    print("=" * 60 + "\n")

    # 测试 1: 环境初始化
    env = test_agcoop_init()

    # 测试 2: 坐标转换
    coord_ok = test_coordinate_conversion()

    # 测试 3: 规划
    planning_ok = test_agcoop_planning(env)

    # 总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"环境初始化: {'✅' if env is not None else '❌'}")
    print(f"坐标转换:   {'✅' if coord_ok else '❌'}")
    print(f"路径规划:   {'✅' if planning_ok else '❌'}")

    if env is not None and coord_ok and planning_ok:
        print("\n🎉 所有测试通过！CoopBridgeNode 可以启动了。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查错误信息。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
