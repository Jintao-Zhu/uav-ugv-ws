#!/usr/bin/env python3
"""
Baseline Policies Evaluation Script

评估Greedy和Coverage两个baseline策略，与Random和PPO对比

使用方法:
    python scripts/evaluate_baselines.py --config configs/day10_ppo_train.yaml --seeds 10000 10001 10002 10003 10004
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import yaml

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from agcoop.rl import AGCoopGymEnv
from agcoop.env.wrappers import FlattenObservation
from agcoop.policies import GreedyPolicy, CoveragePolicy


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def evaluate_policy(
    policy,
    config: Dict[str, Any],
    seeds: List[int],
    policy_name: str,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    评估策略

    Args:
        policy: 策略对象（None表示随机策略）
        config: 环境配置
        seeds: 评估种子列表
        policy_name: 策略名称
        verbose: 是否打印详细信息

    Returns:
        评估结果字典
    """
    if verbose:
        print("=" * 70)
        print(f"评估 {policy_name} 策略")
        print("=" * 70)

    episode_results = []

    for seed in seeds:
        if verbose:
            print(f"\n  Episode (seed={seed})...")

        # 创建环境（不使用FlattenObservation，保持Dict格式）
        env = AGCoopGymEnv(
            config=config,
            output_dir=None,
            enable_logging=False,
        )
        obs, info = env.reset(seed=seed)

        # 重置策略
        if policy is not None:
            policy.reset()

        # 运行 episode
        done = False
        total_reward = 0.0
        episode_length = 0

        # 累积 reward 分量
        reward_components_sum = {
            'r_task': 0.0,
            'r_time': 0.0,
            'r_comm': 0.0,
            'r_deadline': 0.0,
            'r_mapf': 0.0,
        }

        while not done:
            # 选择动作
            if policy is None:
                # 随机策略
                action = env.action_space.sample()
            else:
                # 确定性策略
                task_choice, relay_target = policy.select_action(obs, info)
                action = np.array([task_choice, relay_target], dtype=np.int64)

            # 执行动作
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated

            total_reward += reward
            episode_length += 1

            # 累积 reward 分量
            if 'reward_components' in info:
                rc = info['reward_components']
                for key in reward_components_sum.keys():
                    if key in rc:
                        reward_components_sum[key] += rc[key]

        # 记录结果
        result = {
            'seed': seed,
            'steps': episode_length,
            'total_reward': float(total_reward),
            'mean_reward': float(total_reward / episode_length) if episode_length > 0 else 0.0,
            'reward_task': float(reward_components_sum['r_task']),
            'reward_time': float(reward_components_sum['r_time']),
            'reward_comm': float(reward_components_sum['r_comm']),
            'reward_deadline': float(reward_components_sum['r_deadline']),
            'reward_mapf': float(reward_components_sum['r_mapf']),
            'tasks_completed': int(info.get('tasks_completed', 0)),
            'deadline_miss': int(info.get('deadline_miss', 0)),
        }
        episode_results.append(result)

        if verbose:
            print(f"    Reward: {result['total_reward']:.4f}, Tasks: {result['tasks_completed']}")
            print(f"      Components: task={result['reward_task']:.2f}, "
                  f"time={result['reward_time']:.2f}, "
                  f"comm={result['reward_comm']:.2f}, "
                  f"deadline={result['reward_deadline']:.2f}, "
                  f"mapf={result['reward_mapf']:.2f}")

        env.close()

    # 计算统计量
    stats = compute_stats(episode_results)

    if verbose:
        print(f"\n{policy_name} 策略评估结果:")
        print(f"  Mean reward: {stats['mean_total_reward']:.4f} ± {stats['std_total_reward']:.4f}")
        print(f"  Mean tasks completed: {stats['mean_tasks_completed']:.2f} ± {stats['std_tasks_completed']:.2f}")
        print(f"  Reward components (mean):")
        print(f"    - Task: {stats['mean_reward_task']:.4f}")
        print(f"    - Time: {stats['mean_reward_time']:.4f}")
        print(f"    - Comm: {stats['mean_reward_comm']:.4f}")
        print(f"    - Deadline: {stats['mean_reward_deadline']:.4f}")
        print(f"    - MAPF: {stats['mean_reward_mapf']:.4f}")
        print("=" * 70)

    return {
        'policy_name': policy_name,
        'episodes': episode_results,
        'stats': stats,
    }


def compute_stats(episode_results: List[Dict[str, Any]]) -> Dict[str, float]:
    """计算统计量"""
    stats = {}

    fields = [
        'total_reward',
        'mean_reward',
        'reward_task',
        'reward_time',
        'reward_comm',
        'reward_deadline',
        'reward_mapf',
        'tasks_completed',
        'deadline_miss',
    ]

    for field in fields:
        values = [ep[field] for ep in episode_results]
        stats[f'mean_{field}'] = float(np.mean(values))
        stats[f'std_{field}'] = float(np.std(values))
        stats[f'min_{field}'] = float(np.min(values))
        stats[f'max_{field}'] = float(np.max(values))

    return stats


def compare_all_policies(results: List[Dict[str, Any]]) -> None:
    """
    对比所有策略

    Args:
        results: 所有策略的评估结果列表
    """
    print("\n" + "=" * 70)
    print("策略对比")
    print("=" * 70)

    # 提取策略名称和统计量
    policy_names = [r['policy_name'] for r in results]
    stats_list = [r['stats'] for r in results]

    # 对比 mean_reward
    print(f"\nMean Reward:")
    print(f"  {'Policy':<15} {'Mean':<12} {'Std':<12} {'Min':<12} {'Max':<12}")
    print("-" * 70)
    for name, stats in zip(policy_names, stats_list):
        print(f"  {name:<15} {stats['mean_total_reward']:<12.4f} "
              f"{stats['std_total_reward']:<12.4f} "
              f"{stats['min_total_reward']:<12.4f} "
              f"{stats['max_total_reward']:<12.4f}")

    # 对比 tasks_completed
    print(f"\nMean Tasks Completed:")
    print(f"  {'Policy':<15} {'Mean':<12} {'Std':<12} {'Min':<12} {'Max':<12}")
    print("-" * 70)
    for name, stats in zip(policy_names, stats_list):
        print(f"  {name:<15} {stats['mean_tasks_completed']:<12.2f} "
              f"{stats['std_tasks_completed']:<12.2f} "
              f"{stats['min_tasks_completed']:<12.2f} "
              f"{stats['max_tasks_completed']:<12.2f}")

    # 对比 reward 分量
    print(f"\nReward Components (Mean):")
    print(f"  {'Policy':<15} {'Task':<10} {'Time':<10} {'Comm':<10} {'Deadline':<10} {'MAPF':<10}")
    print("-" * 70)
    for name, stats in zip(policy_names, stats_list):
        print(f"  {name:<15} "
              f"{stats['mean_reward_task']:<10.2f} "
              f"{stats['mean_reward_time']:<10.2f} "
              f"{stats['mean_reward_comm']:<10.2f} "
              f"{stats['mean_reward_deadline']:<10.2f} "
              f"{stats['mean_reward_mapf']:<10.2f}")

    # 计算相对于Random的提升
    if 'Random' in policy_names:
        random_idx = policy_names.index('Random')
        random_reward = stats_list[random_idx]['mean_total_reward']

        print(f"\nImprovement over Random:")
        print(f"  {'Policy':<15} {'Reward Improvement':<20}")
        print("-" * 70)
        for name, stats in zip(policy_names, stats_list):
            if name == 'Random':
                print(f"  {name:<15} {'(baseline)':<20}")
            else:
                improvement = (stats['mean_total_reward'] - random_reward) / random_reward * 100
                print(f"  {name:<15} {improvement:+.2f}%")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description='Baseline Policies Evaluation')
    parser.add_argument('--config', type=str, default='configs/day10_ppo_train.yaml',
                        help='配置文件路径')
    parser.add_argument('--seeds', type=int, nargs='+', default=[10000, 10001, 10002, 10003, 10004],
                        help='评估种子列表')
    parser.add_argument('--output_dir', type=str, default='outputs/baseline_evaluation',
                        help='输出目录')
    parser.add_argument('--policies', type=str, nargs='+',
                        default=['random', 'greedy', 'coverage'],
                        help='要评估的策略列表 (random, greedy, coverage)')
    args = parser.parse_args()

    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载配置
    config = load_config(args.config)

    print("=" * 70)
    print("Baseline Policies Evaluation")
    print("=" * 70)
    print(f"  配置文件: {args.config}")
    print(f"  评估种子: {args.seeds}")
    print(f"  评估策略: {args.policies}")
    print(f"  输出目录: {args.output_dir}")
    print("=" * 70)
    print()

    # 评估所有策略
    all_results = []

    for policy_name in args.policies:
        policy_name_lower = policy_name.lower()

        if policy_name_lower == 'random':
            # 随机策略
            result = evaluate_policy(None, config, args.seeds, 'Random', verbose=True)
        elif policy_name_lower == 'greedy':
            # Greedy策略
            policy = GreedyPolicy(config)
            result = evaluate_policy(policy, config, args.seeds, 'Greedy', verbose=True)
        elif policy_name_lower == 'coverage':
            # Coverage策略
            policy = CoveragePolicy(config)
            result = evaluate_policy(policy, config, args.seeds, 'Coverage', verbose=True)
        else:
            print(f"⚠️  未知策略: {policy_name}，跳过")
            continue

        all_results.append(result)

        # 保存单个策略结果
        output_file = output_dir / f'{policy_name_lower}_results.json'
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)

        print()

    # 对比所有策略
    if len(all_results) > 1:
        compare_all_policies(all_results)

    # 保存汇总结果
    summary = {
        'config': args.config,
        'seeds': args.seeds,
        'results': all_results,
    }
    with open(output_dir / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n结果已保存到: {output_dir}")


if __name__ == '__main__':
    main()
