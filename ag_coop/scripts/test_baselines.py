#!/usr/bin/env python3
"""
Quick Test for Baseline Policies

快速测试Greedy和Coverage策略是否能正常工作
"""

import sys
from pathlib import Path
import numpy as np
import yaml

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from agcoop.rl import AGCoopGymEnv
from agcoop.policies import GreedyPolicy, CoveragePolicy


def test_policy(policy, policy_name: str, config: dict, seed: int = 10000):
    """测试单个策略"""
    print(f"\n{'='*60}")
    print(f"测试 {policy_name} 策略 (seed={seed})")
    print(f"{'='*60}")

    # 创建环境
    env = AGCoopGymEnv(config=config, output_dir=None, enable_logging=False)
    obs, info = env.reset(seed=seed)

    print(f"✓ 环境初始化成功")
    print(f"  Observation keys: {list(obs.keys())}")
    print(f"  Observation shapes:")
    for key, val in obs.items():
        print(f"    - {key}: {val.shape}")

    # 重置策略
    policy.reset()
    print(f"✓ 策略重置成功")

    # 运行几步测试
    total_reward = 0.0
    num_steps = 10

    for step in range(num_steps):
        # 选择动作
        task_choice, relay_target = policy.select_action(obs, info)
        action = np.array([task_choice, relay_target], dtype=np.int64)

        # 执行动作
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward

        if step == 0:
            print(f"✓ 第一步执行成功")
            print(f"  Action: task_choice={task_choice}, relay_target={relay_target}")
            print(f"  Reward: {reward:.4f}")

        if terminated or truncated:
            print(f"  Episode 在第 {step+1} 步结束")
            break

    print(f"✓ 运行 {min(step+1, num_steps)} 步成功")
    print(f"  Total reward: {total_reward:.4f}")
    print(f"  Mean reward: {total_reward/(step+1):.4f}")

    env.close()
    return True


def main():
    print("="*60)
    print("Baseline Policies Quick Test")
    print("="*60)

    # 加载配置
    config_path = 'configs/day10_ppo_train.yaml'
    print(f"\n加载配置: {config_path}")

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print(f"✓ 配置加载成功")
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return False

    # 测试 Greedy 策略
    try:
        greedy_policy = GreedyPolicy(config)
        test_policy(greedy_policy, "Greedy", config, seed=10000)
        print(f"\n✅ Greedy 策略测试通过")
    except Exception as e:
        print(f"\n❌ Greedy 策略测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试 Coverage 策略
    try:
        coverage_policy = CoveragePolicy(config)
        test_policy(coverage_policy, "Coverage", config, seed=10000)
        print(f"\n✅ Coverage 策略测试通过")
    except Exception as e:
        print(f"\n❌ Coverage 策略测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "="*60)
    print("🎉 所有测试通过！")
    print("="*60)
    print("\n下一步：运行完整评估")
    print("  python scripts/evaluate_baselines.py --seeds 10000 10001 10002 10003 10004")
    print("="*60)

    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
