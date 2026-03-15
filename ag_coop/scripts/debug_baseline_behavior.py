#!/usr/bin/env python3
"""
调试Baseline策略行为

观察UAV的实际动作和状态变化
"""

import sys
from pathlib import Path
import yaml
import numpy as np

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv
from agcoop.policies.baseline_policies import (
    TetheredGreedyPolicy,
    StaticCenterPolicy,
    DynamicHeuristicPolicy,
    PureRandomPolicy
)


def load_config():
    """加载配置文件"""
    config_path = project_root / 'configs' / 'curriculum_learning.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    config['episode']['horizon_steps'] = 50  # 只运行50步观察
    return config


def debug_policy(policy, env, seed=20000, max_steps=50):
    """调试单个策略"""
    print(f"\n{'='*70}")
    print(f"调试策略: {policy.policy_name}")
    print(f"{'='*70}")

    # 重置环境
    env.seed = seed
    obs = env.reset()

    print(f"\n初始状态:")
    print(f"  UAV状态: {obs['uav_state']}")
    print(f"  UGV位置: {obs['ugv_pos']}")

    # 运行几步
    for step in range(min(10, max_steps)):
        # 策略决策
        action, _ = policy.predict(obs)

        print(f"\n步骤 {step}:")
        print(f"  动作: {action} (task={action[0]}, relay={action[1]}, uav={action[2]})")

        # 环境交互
        obs, reward, done, info = env.step(action)

        # 打印UAV状态
        uav_state = obs['uav_state']
        mode_str = ['ONBOARD', 'FLYING', 'HOVERING'][int(round(uav_state[0] * 2.0))]
        print(f"  UAV: mode={mode_str}, pos=({uav_state[1]:.3f}, {uav_state[2]:.3f}), battery={uav_state[3]:.3f}")
        print(f"  奖励: {reward:.3f}, 完成任务: {info.get('tasks_completed', 0)}")

        if done:
            print(f"\n  Episode结束！")
            break

    print(f"\n最终统计:")
    print(f"  完成任务: {info.get('tasks_completed', 0)}")
    print(f"  Deadline miss: {info.get('deadline_miss', 0)}")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("Baseline策略行为调试")
    print("="*70)

    # 加载配置
    config = load_config()

    # 创建环境
    env = AGCoopEnv(config, method='rl', planner='PIBT')
    _ = env.reset()  # 初始化地图

    # 调试每个策略
    policies = [
        TetheredGreedyPolicy(env),
        StaticCenterPolicy(env),
        DynamicHeuristicPolicy(env, battery_threshold=0.25),
        PureRandomPolicy(env)
    ]

    for policy in policies:
        debug_policy(policy, env, seed=20000, max_steps=50)

    print("\n" + "="*70)
    print("调试完成！")
    print("="*70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ 调试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
