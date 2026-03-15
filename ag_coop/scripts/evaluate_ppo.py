#!/usr/bin/env python3
"""
PPO模型评估脚本 - 在测试集上评估训练好的PPO模型

在测试集(seeds 20000-20009)上评估PPO模型，并与baseline对比
"""

import sys
from pathlib import Path
import yaml
import json
import numpy as np
from tqdm import tqdm
import argparse

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv
from stable_baselines3 import PPO


def load_config(map_path):
    """加载配置文件"""
    config_path = project_root / 'configs' / 'curriculum_learning.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['episode']['map_path'] = map_path
    config['episode']['horizon_steps'] = 500

    return config


def evaluate_ppo(model_path, map_path, test_seeds, max_steps=500):
    """
    评估PPO模型

    Args:
        model_path: 模型文件路径
        map_path: 地图文件路径
        test_seeds: 测试种子列表
        max_steps: 每个episode的最大步数

    Returns:
        results: 评估结果字典
    """
    # 加载模型
    print(f"加载模型: {model_path}")
    model = PPO.load(model_path)

    # 加载配置
    config = load_config(map_path)

    results = {
        'tasks_completed': [],
        'episode_rewards': [],
        'deadline_miss': [],
        'outage_steps': [],
        'seeds': test_seeds
    }

    print(f"\n开始评估 (测试集: seeds {test_seeds[0]}-{test_seeds[-1]})")

    for seed in tqdm(test_seeds, desc="评估进度"):
        # 创建环境
        env = AGCoopEnv(config, method='rl', planner='PIBT')
        env.seed = seed

        # 重置环境
        obs, info = env.reset(seed=seed)

        episode_reward = 0.0
        done = False
        step_count = 0

        while not done and step_count < max_steps:
            # 使用模型预测动作
            action, _states = model.predict(obs, deterministic=True)

            # 执行动作
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated

            episode_reward += reward
            step_count += 1

        # 记录结果
        results['tasks_completed'].append(env.state.tasks_completed)
        results['episode_rewards'].append(episode_reward)
        results['deadline_miss'].append(env.state.deadline_miss)
        results['outage_steps'].append(env.state.outage_steps)

    return results


def print_statistics(results, policy_name):
    """打印统计结果"""
    tasks = np.array(results['tasks_completed'])
    rewards = np.array(results['episode_rewards'])
    deadline_miss = np.array(results['deadline_miss'])
    outage = np.array(results['outage_steps'])

    print(f"\n{'='*70}")
    print(f"策略: {policy_name}")
    print(f"{'='*70}")
    print(f"任务完成数:")
    print(f"  平均值: {tasks.mean():.2f}")
    print(f"  标准差: {tasks.std():.2f}")
    print(f"  最小值: {tasks.min():.0f}")
    print(f"  最大值: {tasks.max():.0f}")
    print(f"  中位数: {np.median(tasks):.0f}")
    print(f"\n总奖励:")
    print(f"  平均值: {rewards.mean():.2f}")
    print(f"  标准差: {rewards.std():.2f}")
    print(f"  最小值: {rewards.min():.2f}")
    print(f"  最大值: {rewards.max():.2f}")
    print(f"\nDeadline Miss:")
    print(f"  平均值: {deadline_miss.mean():.2f}")
    print(f"\n通信中断步数:")
    print(f"  平均值: {outage.mean():.2f}")


def main():
    parser = argparse.ArgumentParser(description='评估PPO模型')
    parser.add_argument('--model', type=str,
                       default='outputs/upgraded_ppo_map02/best_model/best_model.zip',
                       help='模型文件路径')
    parser.add_argument('--map', type=str,
                       default='maps/map_02.map',
                       help='地图文件路径')
    parser.add_argument('--output', type=str,
                       default='outputs/ppo_evaluation_results.json',
                       help='输出JSON文件路径')

    args = parser.parse_args()

    # 测试种子
    test_seeds = list(range(20000, 20010))

    # 评估PPO模型
    results = evaluate_ppo(args.model, args.map, test_seeds)

    # 打印统计结果
    print_statistics(results, "PPO (Trained)")

    # 保存结果
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 转换numpy类型为Python原生类型
    results_json = {
        'policy': 'PPO',
        'model_path': args.model,
        'map': args.map,
        'tasks_completed': [int(x) for x in results['tasks_completed']],
        'episode_rewards': [float(x) for x in results['episode_rewards']],
        'deadline_miss': [int(x) for x in results['deadline_miss']],
        'outage_steps': [int(x) for x in results['outage_steps']],
        'seeds': results['seeds'],
        'statistics': {
            'tasks_completed_mean': float(np.mean(results['tasks_completed'])),
            'tasks_completed_std': float(np.std(results['tasks_completed'])),
            'episode_reward_mean': float(np.mean(results['episode_rewards'])),
            'episode_reward_std': float(np.std(results['episode_rewards'])),
            'deadline_miss_mean': float(np.mean(results['deadline_miss'])),
            'outage_steps_mean': float(np.mean(results['outage_steps']))
        }
    }

    with open(output_path, 'w') as f:
        json.dump(results_json, f, indent=2)

    print(f"\n结果已保存到: {output_path}")

    # 与baseline对比
    print(f"\n{'='*70}")
    print("与Baseline对比 (Map_02)")
    print(f"{'='*70}")
    print(f"{'策略':<25} {'任务完成':<12} {'总奖励':<12}")
    print(f"{'-'*70}")

    # Baseline结果（来自之前的评估）
    baselines = {
        'Tethered-Greedy': {'tasks': 44.90, 'reward': -32.54},
        'Static-Center': {'tasks': 44.90, 'reward': 29.68},
        'Dynamic-Heuristic': {'tasks': 44.90, 'reward': -29.52},
        'Pure-Random': {'tasks': 38.50, 'reward': 24.44}
    }

    for name, stats in baselines.items():
        print(f"{name:<25} {stats['tasks']:<12.2f} {stats['reward']:<12.2f}")

    print(f"{'-'*70}")
    ppo_tasks = np.mean(results['tasks_completed'])
    ppo_reward = np.mean(results['episode_rewards'])
    print(f"{'PPO (Trained)':<25} {ppo_tasks:<12.2f} {ppo_reward:<12.2f}")
    print(f"{'='*70}")

    # 判断是否达到目标
    print("\n训练目标达成情况:")
    if ppo_tasks >= 48:
        print(f"  ✅ 任务完成数: {ppo_tasks:.2f} >= 48 (目标: 48-52)")
    else:
        print(f"  ❌ 任务完成数: {ppo_tasks:.2f} < 48 (目标: 48-52)")

    if ppo_reward >= 35:
        print(f"  ✅ 总奖励: {ppo_reward:.2f} >= 35 (目标: 35-45)")
    else:
        print(f"  ❌ 总奖励: {ppo_reward:.2f} < 35 (目标: 35-45)")

    if ppo_tasks > 44.90:
        print(f"  ✅ 超越最佳Baseline (44.90任务)")
    else:
        print(f"  ❌ 未超越最佳Baseline (44.90任务)")


if __name__ == "__main__":
    main()
