#!/usr/bin/env python3
"""
深度调试：检查通信质量差异

对比三个策略的实际通信质量和奖励组成
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
)


def load_config():
    """加载配置文件"""
    config_path = project_root / 'configs' / 'curriculum_learning.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    config['episode']['horizon_steps'] = 100  # 运行100步
    return config


def analyze_policy(policy, env, seed=20000, max_steps=100):
    """深度分析单个策略的通信质量"""
    print(f"\n{'='*70}")
    print(f"分析策略: {policy.policy_name}")
    print(f"{'='*70}")

    # 重置环境
    env.seed = seed
    obs = env.reset()

    # 累积统计
    total_r_comm = 0.0
    total_r_task = 0.0
    total_r_time = 0.0
    total_r_deadline = 0.0
    outage_steps = 0

    comm_samples = []

    # 运行episode
    for step in range(max_steps):
        action, _ = policy.predict(obs)
        obs, reward, done, info = env.step(action)

        # 累积奖励组件
        if 'reward_components' in info:
            rc = info['reward_components']
            total_r_comm += rc.get('r_comm', 0.0)
            total_r_task += rc.get('r_task', 0.0)
            total_r_time += rc.get('r_time', 0.0)
            total_r_deadline += rc.get('r_deadline', 0.0)

        # 记录通信质量
        if 'comm' in obs:
            comm_samples.append(obs['comm'].copy())

        # 统计outage
        if info.get('outage', False):
            outage_steps += 1

        if done:
            break

    # 打印统计结果
    print(f"\n奖励组成（累积）:")
    print(f"  r_task:     {total_r_task:>8.2f}")
    print(f"  r_time:     {total_r_time:>8.2f}")
    print(f"  r_comm:     {total_r_comm:>8.2f}  ← 关键指标")
    print(f"  r_deadline: {total_r_deadline:>8.2f}")
    print(f"  总奖励:     {total_r_task + total_r_time + total_r_comm + total_r_deadline:>8.2f}")

    print(f"\n通信质量:")
    print(f"  Outage步数: {outage_steps}/{max_steps} ({outage_steps/max_steps*100:.1f}%)")

    if comm_samples:
        comm_array = np.array(comm_samples)
        print(f"  平均SNR: {np.mean(comm_array[:, 0]):.2f} dB")
        print(f"  平均Outage: {np.mean(comm_array[:, 1]):.2f}")

    print(f"\n任务完成:")
    print(f"  完成任务数: {info.get('tasks_completed', 0)}")
    print(f"  Deadline miss: {info.get('deadline_miss', 0)}")


def main():
    """主函数"""
    print("\n" + "="*70)
    print("深度调试：通信质量差异分析")
    print("="*70)

    # 加载配置
    config = load_config()

    # 创建环境
    env = AGCoopEnv(config, method='rl', planner='PIBT')
    _ = env.reset()

    # 分析三个策略
    policies = [
        TetheredGreedyPolicy(env),
        StaticCenterPolicy(env),
        DynamicHeuristicPolicy(env, battery_threshold=0.25),
    ]

    for policy in policies:
        analyze_policy(policy, env, seed=20000, max_steps=100)

    print("\n" + "="*70)
    print("分析完成！")
    print("="*70)
    print("\n关键发现:")
    print("  如果三个策略的 r_comm 差异很小（<1.0），说明通信惩罚权重太低")
    print("  如果 Outage 百分比都很低（<10%），说明地图太简单，通信质量都很好")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
