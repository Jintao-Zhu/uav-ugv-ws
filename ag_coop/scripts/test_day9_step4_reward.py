#!/usr/bin/env python3
"""
Day9 Step 4 验证：Reward Function

验证标准：
1. reward 每一步都是 finite number（非 NaN/Inf）
2. 1 episode 的 sum_reward 可打印/保存，且不同 seed 下不全相同
"""

import sys
from pathlib import Path
import yaml
import numpy as np

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv


def test_reward_finite(config_path: str, num_steps: int = 100):
    """
    测试 reward 是否为 finite number

    Args:
        config_path: 配置文件路径
        num_steps: 运行步数
    """
    print("=" * 70)
    print("Day9 Step 4: Reward Finite 测试")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print(f"运行步数: {num_steps}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 创建环境
    env = AGCoopEnv(
        config,
        output_dir=None,
        enable_logging=False,
        method="rl",
        planner="none"
    )

    obs = env.reset()

    # 统计
    nan_inf_count = 0
    rewards = []
    reward_components_list = []

    for step in range(num_steps):
        # 随机 action
        action = env.action_space.sample()

        # 执行一步
        obs, reward, done, info = env.step(action)

        # 检查 reward 是否 finite
        if not np.isfinite(reward):
            nan_inf_count += 1
            print(f"   ✗ Step {step}: reward is not finite: {reward}")

        # 记录 reward
        rewards.append(reward)

        # 记录 reward 组成部分
        if 'reward_components' in info:
            reward_components_list.append(info['reward_components'])

        if done:
            print(f"   Episode 结束于 step {step}")
            break

    print()
    print(f"运行完成: {step + 1} 步")
    print(f"  - NaN/Inf 次数: {nan_inf_count}")
    print(f"  - 总 reward: {sum(rewards):.4f}")
    print(f"  - 平均 reward: {np.mean(rewards):.4f}")
    print(f"  - 最小 reward: {min(rewards):.4f}")
    print(f"  - 最大 reward: {max(rewards):.4f}")
    print()

    # 打印 reward 组成部分统计
    if reward_components_list:
        print("Reward 组成部分统计:")
        keys = reward_components_list[0].keys()
        for key in keys:
            values = [rc[key] for rc in reward_components_list]
            print(f"  - {key}: sum={sum(values):.4f}, mean={np.mean(values):.4f}")
        print()

    if nan_inf_count > 0:
        print("   ✗ Reward finite 测试失败")
        return False

    print("   ✓ Reward finite 测试通过")
    return True


def test_reward_variance(config_path: str, num_seeds: int = 3, num_steps: int = 100):
    """
    测试不同 seed 下 reward 是否有差异

    Args:
        config_path: 配置文件路径
        num_seeds: 测试的 seed 数量
        num_steps: 每个 seed 运行的步数
    """
    print("=" * 70)
    print("Day9 Step 4: Reward Variance 测试")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print(f"测试 seed 数量: {num_seeds}")
    print(f"每个 seed 运行步数: {num_steps}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    sum_rewards = []

    for seed_idx in range(num_seeds):
        # 修改 seed
        config['episode']['seed'] = 1000 + seed_idx

        # 创建环境
        env = AGCoopEnv(
            config,
            output_dir=None,
            enable_logging=False,
            method="rl",
            planner="none"
        )

        obs = env.reset()

        # 运行 episode
        rewards = []
        for step in range(num_steps):
            action = env.action_space.sample()
            obs, reward, done, info = env.step(action)
            rewards.append(reward)

            if done:
                break

        sum_reward = sum(rewards)
        sum_rewards.append(sum_reward)

        print(f"Seed {1000 + seed_idx}: sum_reward = {sum_reward:.4f} ({len(rewards)} 步)")

    print()
    print(f"Sum rewards: {sum_rewards}")
    print(f"  - Mean: {np.mean(sum_rewards):.4f}")
    print(f"  - Std: {np.std(sum_rewards):.4f}")
    print()

    # 检查是否所有 sum_reward 都相同
    if len(set(sum_rewards)) == 1:
        print("   ✗ 所有 seed 的 sum_reward 都相同，reward 可能没有响应")
        return False

    print("   ✓ 不同 seed 的 sum_reward 不同，reward 有响应")
    return True


def test_reward_components(config_path: str, num_steps: int = 50):
    """
    测试 reward 各组成部分是否合理

    Args:
        config_path: 配置文件路径
        num_steps: 运行步数
    """
    print("=" * 70)
    print("Day9 Step 4: Reward Components 测试")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print(f"运行步数: {num_steps}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 创建环境
    env = AGCoopEnv(
        config,
        output_dir=None,
        enable_logging=False,
        method="rl",
        planner="none"
    )

    obs = env.reset()

    # 统计各组成部分
    component_stats = {
        'r_task': [],
        'r_time': [],
        'r_comm': [],
        'r_deadline': [],
        'r_mapf': [],
        'r_total': [],
    }

    for step in range(num_steps):
        action = env.action_space.sample()
        obs, reward, done, info = env.step(action)

        if 'reward_components' in info:
            for key in component_stats.keys():
                if key in info['reward_components']:
                    component_stats[key].append(info['reward_components'][key])

        if done:
            break

    print(f"运行完成: {step + 1} 步")
    print()

    # 打印统计
    print("Reward 组成部分详细统计:")
    for key, values in component_stats.items():
        if values:
            print(f"\n{key}:")
            print(f"  - Count: {len(values)}")
            print(f"  - Sum: {sum(values):.4f}")
            print(f"  - Mean: {np.mean(values):.4f}")
            print(f"  - Min: {min(values):.4f}")
            print(f"  - Max: {max(values):.4f}")
            print(f"  - Non-zero count: {sum(1 for v in values if v != 0)}")

    print()
    print("   ✓ Reward components 测试完成")
    return True


def main():
    """主函数"""
    config_path = "configs/day7_baseline.yaml"

    if not Path(config_path).exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    # 测试 1: Reward finite
    success1 = test_reward_finite(config_path, num_steps=100)

    # 测试 2: Reward variance
    success2 = test_reward_variance(config_path, num_seeds=3, num_steps=100)

    # 测试 3: Reward components
    success3 = test_reward_components(config_path, num_steps=50)

    # 总结
    print("=" * 70)
    print("验收总结")
    print("=" * 70)
    print()

    print(f"1. Reward finite 测试: {'✅' if success1 else '❌'}")
    print(f"2. Reward variance 测试: {'✅' if success2 else '❌'}")
    print(f"3. Reward components 测试: {'✅' if success3 else '❌'}")
    print()

    if success1 and success2 and success3:
        print("✅✅✅ Day9 Step 4 验收通过！✅✅✅")
        sys.exit(0)
    else:
        print("❌ Day9 Step 4 验收失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
