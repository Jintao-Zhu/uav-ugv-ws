#!/usr/bin/env python3
"""
Multi-Map Evaluation Script

评估多张地图上的策略泛化性能

使用方法:
    python scripts/evaluate_multi_maps.py --maps map_01 map_02 map_03 --policies random greedy coverage --seeds 10000 10001 10002 10003 10004
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import time

import numpy as np
import yaml

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from agcoop.rl import AGCoopGymEnv
from agcoop.policies import GreedyPolicy, CoveragePolicy


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def evaluate_policy_on_map(
    policy,
    config: Dict[str, Any],
    map_name: str,
    seeds: List[int],
    policy_name: str,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    在单张地图上评估策略

    Args:
        policy: 策略对象（None表示随机策略）
        config: 环境配置
        map_name: 地图名称
        seeds: 评估种子列表
        policy_name: 策略名称
        verbose: 是否打印详细信息

    Returns:
        评估结果字典
    """
    if verbose:
        print(f"\n{'='*70}")
        print(f"评估 {policy_name} 策略 on {map_name}")
        print(f"{'='*70}")

    # 修改配置中的地图路径
    config_copy = config.copy()
    config_copy['episode']['map_path'] = f'maps/{map_name}.map'

    episode_results = []

    for seed in seeds:
        if verbose:
            print(f"  Episode (seed={seed})...", end=' ', flush=True)

        try:
            # 创建环境
            env = AGCoopGymEnv(
                config=config_copy,
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
                print(f"Reward: {result['total_reward']:.2f}, Tasks: {result['tasks_completed']}")

            env.close()

        except Exception as e:
            print(f"❌ 失败: {e}")
            continue

    # 计算统计量
    if len(episode_results) > 0:
        stats = compute_stats(episode_results)
    else:
        stats = {}

    if verbose and len(episode_results) > 0:
        print(f"\n{policy_name} on {map_name} 结果:")
        print(f"  Mean reward: {stats['mean_total_reward']:.4f} ± {stats['std_total_reward']:.4f}")
        print(f"  Mean tasks: {stats['mean_tasks_completed']:.2f} ± {stats['std_tasks_completed']:.2f}")
        print(f"  Comm penalty: {stats['mean_reward_comm']:.2f}")

    return {
        'policy_name': policy_name,
        'map_name': map_name,
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


def compare_across_maps(results: List[Dict[str, Any]]) -> None:
    """
    对比不同地图上的性能

    Args:
        results: 所有评估结果列表
    """
    print("\n" + "="*70)
    print("跨地图性能对比")
    print("="*70)

    # 按地图和策略组织结果
    map_names = sorted(set(r['map_name'] for r in results))
    policy_names = sorted(set(r['policy_name'] for r in results))

    # 对比 mean_reward
    print(f"\nMean Reward:")
    print(f"  {'Map':<12} " + " ".join(f"{p:<12}" for p in policy_names))
    print("-" * 70)

    for map_name in map_names:
        row = f"  {map_name:<12} "
        for policy_name in policy_names:
            # 找到对应的结果
            matching = [r for r in results if r['map_name'] == map_name and r['policy_name'] == policy_name]
            if matching and len(matching[0]['episodes']) > 0:
                mean_reward = matching[0]['stats']['mean_total_reward']
                row += f"{mean_reward:<12.2f} "
            else:
                row += f"{'N/A':<12} "
        print(row)

    # 对比 tasks_completed
    print(f"\nMean Tasks Completed:")
    print(f"  {'Map':<12} " + " ".join(f"{p:<12}" for p in policy_names))
    print("-" * 70)

    for map_name in map_names:
        row = f"  {map_name:<12} "
        for policy_name in policy_names:
            matching = [r for r in results if r['map_name'] == map_name and r['policy_name'] == policy_name]
            if matching and len(matching[0]['episodes']) > 0:
                mean_tasks = matching[0]['stats']['mean_tasks_completed']
                row += f"{mean_tasks:<12.2f} "
            else:
                row += f"{'N/A':<12} "
        print(row)

    # 对比 comm penalty
    print(f"\nMean Comm Penalty:")
    print(f"  {'Map':<12} " + " ".join(f"{p:<12}" for p in policy_names))
    print("-" * 70)

    for map_name in map_names:
        row = f"  {map_name:<12} "
        for policy_name in policy_names:
            matching = [r for r in results if r['map_name'] == map_name and r['policy_name'] == policy_name]
            if matching and len(matching[0]['episodes']) > 0:
                mean_comm = matching[0]['stats']['mean_reward_comm']
                row += f"{mean_comm:<12.2f} "
            else:
                row += f"{'N/A':<12} "
        print(row)

    # 计算每个策略在不同地图上的平均性能
    print(f"\n策略平均性能（跨地图）:")
    print(f"  {'Policy':<15} {'Mean Reward':<15} {'Mean Tasks':<15} {'Comm Penalty':<15}")
    print("-" * 70)

    for policy_name in policy_names:
        policy_results = [r for r in results if r['policy_name'] == policy_name and len(r['episodes']) > 0]
        if policy_results:
            avg_reward = np.mean([r['stats']['mean_total_reward'] for r in policy_results])
            avg_tasks = np.mean([r['stats']['mean_tasks_completed'] for r in policy_results])
            avg_comm = np.mean([r['stats']['mean_reward_comm'] for r in policy_results])
            print(f"  {policy_name:<15} {avg_reward:<15.2f} {avg_tasks:<15.2f} {avg_comm:<15.2f}")

    print("="*70)


def main():
    parser = argparse.ArgumentParser(description='Multi-Map Evaluation')
    parser.add_argument('--config', type=str, default='configs/day10_ppo_train.yaml',
                        help='配置文件路径')
    parser.add_argument('--maps', type=str, nargs='+', default=['map_01', 'map_02', 'map_03'],
                        help='要评估的地图列表')
    parser.add_argument('--policies', type=str, nargs='+',
                        default=['random', 'greedy', 'coverage'],
                        help='要评估的策略列表')
    parser.add_argument('--seeds', type=int, nargs='+', default=[10000, 10001, 10002, 10003, 10004],
                        help='评估种子列表')
    parser.add_argument('--output_dir', type=str, default='outputs/multi_map_evaluation',
                        help='输出目录')
    args = parser.parse_args()

    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载配置
    config = load_config(args.config)

    print("="*70)
    print("Multi-Map Evaluation")
    print("="*70)
    print(f"  配置文件: {args.config}")
    print(f"  地图列表: {args.maps}")
    print(f"  策略列表: {args.policies}")
    print(f"  评估种子: {args.seeds}")
    print(f"  输出目录: {args.output_dir}")
    print("="*70)

    # 评估所有地图和策略的组合
    all_results = []
    total_experiments = len(args.maps) * len(args.policies)
    current_experiment = 0

    start_time = time.time()

    for map_name in args.maps:
        for policy_name in args.policies:
            current_experiment += 1
            print(f"\n[{current_experiment}/{total_experiments}] 评估 {policy_name} on {map_name}")

            policy_name_lower = policy_name.lower()

            if policy_name_lower == 'random':
                # 随机策略
                result = evaluate_policy_on_map(None, config, map_name, args.seeds, 'Random', verbose=True)
            elif policy_name_lower == 'greedy':
                # Greedy策略
                policy = GreedyPolicy(config)
                result = evaluate_policy_on_map(policy, config, map_name, args.seeds, 'Greedy', verbose=True)
            elif policy_name_lower == 'coverage':
                # Coverage策略
                policy = CoveragePolicy(config)
                result = evaluate_policy_on_map(policy, config, map_name, args.seeds, 'Coverage', verbose=True)
            else:
                print(f"⚠️  未知策略: {policy_name}，跳过")
                continue

            all_results.append(result)

            # 保存单个结果
            result_file = output_dir / f'{map_name}_{policy_name_lower}_results.json'
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)

    elapsed_time = time.time() - start_time

    # 对比所有结果
    if len(all_results) > 1:
        compare_across_maps(all_results)

    # 保存汇总结果
    summary = {
        'config': args.config,
        'maps': args.maps,
        'policies': args.policies,
        'seeds': args.seeds,
        'total_experiments': total_experiments,
        'elapsed_time_seconds': elapsed_time,
        'results': all_results,
    }
    with open(output_dir / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n结果已保存到: {output_dir}")
    print(f"总耗时: {elapsed_time:.1f} 秒 ({elapsed_time/60:.1f} 分钟)")


if __name__ == '__main__':
    main()
