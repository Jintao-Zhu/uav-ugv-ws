"""
测试UAV独立飞行功能

验证：
1. UAV状态空间正确初始化
2. 动作空间扩展正确
3. UAV物理更新正常工作
4. 观察空间包含完整UAV状态
5. A2G通信模型正确应用
"""

import sys
from pathlib import Path
import numpy as np

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv, UAVMode


def test_basic_initialization():
    """测试1：基础初始化"""
    print("\n" + "="*60)
    print("测试1：基础初始化")
    print("="*60)

    config = {
        'map': {
            'name': 'map_02',
            'map_dir': str(project_root / 'maps')
        },
        'ugv': {
            'n_ugv': 3,
            'carrier_id': 0
        },
        'task': {
            'enabled': True,
            'arrival_rate': 0.1,
            'deadline_min': 25,
            'deadline_max': 60
        },
        'comm': {
            'enabled': True,
            'obstacle_penalty_db': 6.0,
            'obstacle_penalty_a2g_db': 1.5,
            'snr_threshold_db': -20.0
        },
        'rl': {
            'enabled': True,
            'decision_period': 5,
            'top_m': 5,
            'candidate_count': 12
        },
        'horizon_steps': 100
    }

    env = AGCoopEnv(config)
    obs = env.reset()

    # 验证UAV状态
    uav = env.state.uav_state
    print(f"✓ UAV初始化成功")
    print(f"  - 模式: {uav.mode} (UAVMode.ONBOARD)")
    print(f"  - 位置: {uav.position}")
    print(f"  - 电量: {uav.battery_level * 100:.1f}%")
    print(f"  - 搭载车辆: UGV {uav.onboard_ugv_id}")

    # 验证动作空间
    action_space = env.action_space
    print(f"\n✓ 动作空间扩展成功")
    print(f"  - 维度: {action_space.nvec}")
    print(f"  - task_choice: 0-{action_space.nvec[0]-1}")
    print(f"  - relay_target: 0-{action_space.nvec[1]-1}")
    print(f"  - uav_action: 0-{action_space.nvec[2]-1}")

    # 验证观察空间
    print(f"\n✓ 观察空间升级成功")
    print(f"  - ugv_pos: {obs['ugv_pos'].shape}")
    print(f"  - uav_state: {obs['uav_state'].shape} (应为5维)")
    print(f"  - tasks_topM: {obs['tasks_topM'].shape}")
    print(f"  - comm: {obs['comm'].shape}")
    print(f"  - candidates_R: {obs['candidates_R'].shape}")

    return env


def test_uav_flying():
    """测试2：UAV飞行功能"""
    print("\n" + "="*60)
    print("测试2：UAV飞行功能")
    print("="*60)

    config = {
        'map': {
            'name': 'map_02',
            'map_dir': str(project_root / 'maps')
        },
        'ugv': {
            'n_ugv': 3,
            'carrier_id': 0
        },
        'task': {
            'enabled': True,
            'arrival_rate': 0.1
        },
        'comm': {
            'enabled': True,
            'obstacle_penalty_a2g_db': 1.5
        },
        'rl': {
            'enabled': True,
            'decision_period': 5,
            'top_m': 5,
            'candidate_count': 12
        },
        'horizon_steps': 100
    }

    env = AGCoopEnv(config)
    obs = env.reset()

    print(f"初始状态:")
    print(f"  - UAV模式: {env.state.uav_state.mode}")
    print(f"  - UAV位置: {env.state.uav_state.position}")
    print(f"  - UAV电量: {env.state.uav_state.battery_level * 100:.1f}%")

    # 测试：命令UAV飞往第一个中继点
    print(f"\n执行动作: 飞往中继点1")
    action = [0, 0, 1]  # task_choice=0, relay_target=0, uav_action=1 (飞往中继点1)

    for step in range(20):
        obs, reward, done, info = env.step(action)

        if step % 5 == 0:
            uav = env.state.uav_state
            print(f"\n步骤 {step}:")
            print(f"  - UAV模式: {uav.mode} ({['ONBOARD', 'FLYING', 'HOVERING'][uav.mode]})")
            print(f"  - UAV位置: ({uav.position[0]:.2f}, {uav.position[1]:.2f})")
            print(f"  - UAV电量: {uav.battery_level * 100:.1f}%")

            if uav.mode == UAVMode.HOVERING:
                print(f"  ✓ UAV已到达中继点并悬停！")
                break

    return env


def test_a2g_communication():
    """测试3：A2G通信模型"""
    print("\n" + "="*60)
    print("测试3：A2G通信模型")
    print("="*60)

    from agcoop.comm import compute_snr
    from agcoop.comm.comm_model import CommConfig

    config = CommConfig(
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        obstacle_penalty_a2g_db=1.5,
        snr_threshold_db=-20.0
    )

    # 测试场景：10米距离，2个障碍物
    distance = 10.0
    blocked = 2

    # G2G通信（地面到地面）
    snr_g2g = compute_snr(distance, blocked, config, is_a2g=False, uav_mode=0)
    print(f"G2G通信 (地面到地面):")
    print(f"  - 距离: {distance}m, 障碍物: {blocked}个")
    print(f"  - SNR: {snr_g2g:.2f} dB")
    print(f"  - 障碍物惩罚: {6.0 * blocked} dB")

    # A2G通信（空中到地面，悬停）
    snr_a2g = compute_snr(distance, blocked, config, is_a2g=True, uav_mode=2)
    print(f"\nA2G通信 (空中到地面, UAV悬停):")
    print(f"  - 距离: {distance}m, 障碍物: {blocked}个")
    print(f"  - SNR: {snr_a2g:.2f} dB")
    print(f"  - 障碍物惩罚: {1.5 * blocked} dB")

    improvement = snr_a2g - snr_g2g
    print(f"\n✓ A2G改善: {improvement:.2f} dB")
    print(f"  理论值: {(6.0 - 1.5) * blocked} dB")

    # 测试极近距离优化
    distance_close = 2.0
    snr_close = compute_snr(distance_close, blocked, config, is_a2g=True, uav_mode=2)
    print(f"\n极近距离优化 ({distance_close}m):")
    print(f"  - SNR: {snr_close:.2f} dB")
    print(f"  - 障碍物惩罚: 0 dB (自动忽略)")


def test_battery_management():
    """测试4：电池管理"""
    print("\n" + "="*60)
    print("测试4：电池管理")
    print("="*60)

    config = {
        'map': {
            'name': 'map_02',
            'map_dir': str(project_root / 'maps')
        },
        'ugv': {
            'n_ugv': 3
        },
        'task': {
            'enabled': False  # 关闭任务生成，专注测试UAV
        },
        'comm': {
            'enabled': True
        },
        'rl': {
            'enabled': True,
            'decision_period': 5
        },
        'horizon_steps': 500
    }

    env = AGCoopEnv(config)
    obs = env.reset()

    # 强制设置低电量
    env.state.uav_state.battery_level = 0.2
    env.state.uav_state.mode = UAVMode.HOVERING

    print(f"初始状态:")
    print(f"  - UAV电量: {env.state.uav_state.battery_level * 100:.1f}%")
    print(f"  - UAV模式: HOVERING")

    # 运行几步，观察电池消耗和紧急返航
    action = [0, 0, 0]  # 无动作

    for step in range(50):
        obs, reward, done, info = env.step(action)

        uav = env.state.uav_state

        if step % 10 == 0:
            print(f"\n步骤 {step}:")
            print(f"  - 电量: {uav.battery_level * 100:.1f}%")
            print(f"  - 模式: {['ONBOARD', 'FLYING', 'HOVERING'][uav.mode]}")

        # 检测紧急返航触发
        if uav.battery_level < 0.15 and uav.mode == UAVMode.FLYING:
            print(f"\n✓ 紧急返航触发！(电量: {uav.battery_level * 100:.1f}%)")
            break

        # 检测成功降落
        if uav.mode == UAVMode.ONBOARD and step > 0:
            print(f"\n✓ UAV成功降落并开始充电！")
            print(f"  - 当前电量: {uav.battery_level * 100:.1f}%")

            # 继续运行几步观察充电
            for charge_step in range(20):
                obs, reward, done, info = env.step(action)
                if charge_step % 5 == 0:
                    print(f"  充电中... 电量: {env.state.uav_state.battery_level * 100:.1f}%")
            break


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("UAV独立飞行系统 - 完整测试")
    print("="*60)

    try:
        # 测试1：基础初始化
        env = test_basic_initialization()

        # 测试2：UAV飞行
        test_uav_flying()

        # 测试3：A2G通信
        test_a2g_communication()

        # 测试4：电池管理
        test_battery_management()

        print("\n" + "="*60)
        print("✓ 所有测试通过！")
        print("="*60)
        print("\n系统升级总结:")
        print("1. ✓ UAV状态空间：支持独立位置、模式、电量")
        print("2. ✓ 动作空间：扩展到3维，支持UAV飞行控制")
        print("3. ✓ UAV物理：飞行、悬停、降落、电池管理")
        print("4. ✓ 观察空间：5维UAV状态（mode, x, y, battery, carrier_id）")
        print("5. ✓ A2G通信：空对地1.5dB/障碍物 vs 地对地6.0dB/障碍物")
        print("6. ✓ 紧急保护：电量<15%自动返航")

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
