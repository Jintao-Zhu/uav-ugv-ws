#!/usr/bin/env python3
"""
Multi-Load Evaluation Script

评估不同任务负载下的策略性能，生成Throughput vs Load曲线

使用方法:
    python scripts/evaluate_multi_loads.py --loads 3.0 6.0 9.0 --maps map_01 map_02 map_03 --policies random greedy coverage --seeds 10000 10001 10002 10003 10004
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


def evaluate_policy_on_load(
    policy,
    config: Dict[str, Any],
    map_name: str,
    load: float,
    seeds: List[int],
    policy_name: str,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    在特定负载下评估策略

    Args:
        policy: 策略对象（None表示随机策略）
        config: 环境配置
        map_name: 地图名称
        load: 任务到达率（λ）
        seeds: 评估种子列表
        policy_name: 策略名称
        verbose: 是否打印详细信息

    Returns:
        评估结果字典
    """
    if verbose:
        print(f"  [{policy_name} on {map_name}, λ={load}]", end=' ', flush=True)

    # 修改配置
    config_copy = config.copy()
    config_copy['episode']['map_path'] = f'maps/{map_name}.map'
    config_copy['tasks']['arrival_rate'] = load

    episode_results = []

    for seed in seeds:
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
                    action = env.action_space.sample()
                else:
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

            # 计算吞吐量（tasks per 100 steps）
            horizon = config_copy['episode']['horizon_steps']
            throughput = (info.get('tasks_completed', 0) / horizon) * 100

            # 计算deadline miss rate
            tasks_completed = info.get('tasks_completed', 0)
            deadline_miss = info.get('deadline_miss', 0)
            total_tasks = tasks_completed + deadline_miss
            miss_rate = (deadline_miss / total_tasks * 100) if total_tasks > 0 else 0.0

            # 记录结果
            result = {
                'seed': seed,
                'load': load,
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
                'throughput': float(throughput),
                'miss_rate': float(miss_rate),
            }
            episode_results.append(result)

            env.close()

        except Exception as e:
            if verbose:
                print(f"❌ seed={seed} 失败: {e}")
            continue

    # 计算统计量
    if len(episode_results) > 0:
        stats = compute_stats(episode_results)
        if verbose:
            print(f"✓ Reward={stats['mean_total_reward']:.1f}, Throughput={stats['mean_throughput']:.1f}, Miss={stats['mean_miss_rate']:.1f}%")
    else:
        stats = {}
        if verbose:
            print(f"❌ 所有种子都失败")

    return {
        'policy_name': policy_name,
        'map_name': map_name,
        'load': load,
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
        'throughput',
        'miss_rate',
    ]

    for field in fields:
        values = [ep[field] for ep in episode_results]
        stats[f'mean_{field}'] = float(np.mean(values))
        stats[f'std_{field}'] = float(np.std(values))
        stats[f'min_{field}'] = float(np.min(values))
        stats[f'max_{field}'] = float(np.max(values))

    return stats


def generate_load_curves(results: List[Dict[str, Any]], output_dir: Path) -> None:
    """
    生成负载曲线图

    Args:
        results: 所有评估结果
        output_dir: 输出目录
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # 使用非交互式后端
    except ImportError:
        print("⚠️  matplotlib未安装，跳过图表生成")
        return

    # 按地图分组
    map_names = sorted(set(r['map_name'] for r in results))
    policy_names = sorted(set(r['policy_name'] for r in results))
    loads = sorted(set(r['load'] for r in results))

    # 为每张地图生成曲线
    for map_name in map_names:
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(f'Performance vs Load on {map_name}', fontsize=14, fontweight='bold')

        # 1. Throughput vs Load
        ax = axes[0, 0]
        for policy_name in policy_names:
            policy_results = [r for r in results if r['map_name'] == map_name and r['policy_name'] == policy_name]
            if policy_results:
                x = [r['load'] for r in policy_results]
                y = [r['stats']['mean_throughput'] for r in policy_results]
                yerr = [r['stats']['std_throughput'] for r in policy_results]
                ax.errorbar(x, y, yerr=yerr, marker='o', label=policy_name, capsize=5)
        ax.set_xlabel('Task Arrival Rate (λ)')
        ax.set_ylabel('Throughput (tasks/100 steps)')
        ax.set_title('Throughput vs Load')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 2. Miss Rate vs Load
        ax = axes[0, 1]
        for policy_name in policy_names:
            policy_results = [r for r in results if r['map_name'] == map_name and r['policy_name'] == policy_name]
            if policy_results:
                x = [r['load'] for r in policy_results]
                y = [r['stats']['mean_miss_rate'] for r in policy_results]
                yerr = [r['stats']['std_miss_rate'] for r in policy_results]
                ax.errorbar(x, y, yerr=yerr, marker='s', label=policy_name, capsize=5)
        ax.set_xlabel('Task Arrival Rate (λ)')
        ax.set_ylabel('Deadline Miss Rate (%)')
        ax.set_title('Miss Rate vs Load')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 3. Mean Reward vs Load
        ax = axes[1, 0]
        for policy_name in policy_names:
            policy_results = [r for r in results if r['map_name'] == map_name and r['policy_name'] == policy_name]
            if policy_results:
                x = [r['load'] for r in policy_results]
                y = [r['stats']['mean_total_reward'] for r in policy_results]
                yerr = [r['stats']['std_total_reward'] for r in policy_results]
                ax.errorbar(x, y, yerr=yerr, marker='^', label=policy_name, capsize=5)
        ax.set_xlabel('Task Arrival Rate (λ)')
        ax.set_ylabel('Mean Reward')
        ax.set_title('Reward vs Load')
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 4. Comm Penalty vs Load
        ax = axes[1, 1]
        for policy_name in policy_names:
            policy_results = [r for r in results if r['map_name'] == map_name and r['policy_name'] == policy_name]
            if policy_results:
                x = [r['load'] for r in policy_results]
                y = [r['stats']['mean_reward_comm'] for r in policy_results]
                yerr = [r['stats']['std_reward_comm'] for r in policy_results]
                ax.errorbar(x, y, yerr=yerr, marker='d', label=policy_name, capsize=5)
        ax.set_xlabel('Task Arrival Rate (λ)')
        ax.set_ylabel('Comm Penalty')
        ax.set_title('Communication Quality vs Load')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        output_file = output_dir / f'load_curves_{map_name}.png'
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  图表已保存: {output_file}")


def print_summary_table(results: List[Dict[str, Any]]) -> None:
    """打印汇总表格"""
    print("\n" + "="*100)
    print("负载实验汇总")
    print("="*100)

    # 按地图分组
    map_names = sorted(set(r['map_name'] for r in results))
    policy_names = sorted(set(r['policy_name'] for r in results))
    loads = sorted(set(r['load'] for r in results))

    for map_name in map_names:
        print(f"\n{map_name}:")
        print(f"  {'Load':<8} {'Policy':<12} {'Reward':<12} {'Throughput':<12} {'Miss Rate':<12} {'Comm':<12}")
        print("  " + "-"*90)

        for load in loads:
            for policy_name in policy_names:
                matching = [r for r in results if r['map_name'] == map_name and r['policy_name'] == policy_name and r['load'] == load]
                if matching and len(matching[0]['episodes']) > 0:
                    stats = matching[0]['stats']
                    print(f"  {load:<8.1f} {policy_name:<12} "
                          f"{stats['mean_total_reward']:<12.2f} "
                          f"{stats['mean_throughput']:<12.2f} "
                          f"{stats['mean_miss_rate']:<12.2f} "
                          f"{stats['mean_reward_comm']:<12.2f}")

    print("="*100)


def main():
    parser = argparse.ArgumentParser(description='Multi-Load Evaluation')
    parser.add_argument('--config', type=str, default='configs/day10_ppo_train.yaml',
                        help='配置文件路径')
    parser.add_argument('--loads', type=float, nargs='+', default=[3.0, 6.0, 9.0],
                        help='任务到达率列表（λ）')
    parser.add_argument('--maps', type=str, nargs='+', default=['map_01', 'map_02', 'map_03'],
                        help='要评估的地图列表')
    parser.add_argument('--policies', type=str, nargs='+',
                        default=['random', 'greedy', 'coverage'],
                        help='要评估的策略列表')
    parser.add_argument('--seeds', type=int, nargs='+', default=[10000, 10001, 10002, 10003, 10004],
                        help='评估种子列表')
    parser.add_argument('--output_dir', type=str, default='outputs/multi_load_evaluation',
                        help='输出目录')
    args = parser.parse_args()

    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载配置
    config = load_config(args.config)

    print("="*100)
    print("Multi-Load Evaluation")
    print("="*100)
    print(f"  配置文件: {args.config}")
    print(f"  负载列表: {args.loads}")
    print(f"  地图列表: {args.maps}")
    print(f"  策略列表: {args.policies}")
    print(f"  评估种子: {args.seeds}")
    print(f"  输出目录: {args.output_dir}")
    print("="*100)

    # 计算总实验数
    total_experiments = len(args.loads) * len(args.maps) * len(args.policies)
    print(f"\n总实验数: {total_experiments} ({len(args.loads)} loads × {len(args.maps)} maps × {len(args.policies)} policies)")
    print(f"每个实验运行 {len(args.seeds)} 个种子\n")

    # 评估所有组合
    all_results = []
    current_experiment = 0
    start_time = time.time()

    for load in args.loads:
        print(f"\n{'='*100}")
        print(f"负载 λ={load}")
        print(f"{'='*100}")

        for map_name in args.maps:
            for policy_name in args.policies:
                current_experiment += 1
                policy_name_lower = policy_name.lower()

                if policy_name_lower == 'random':
                    result = evaluate_policy_on_load(None, config, map_name, load, args.seeds, 'Random', verbose=True)
                elif policy_name_lower == 'greedy':
                    policy = GreedyPolicy(config)
                    result = evaluate_policy_on_load(policy, config, map_name, load, args.seeds, 'Greedy', verbose=True)
                elif policy_name_lower == 'coverage':
                    policy = CoveragePolicy(config)
                    result = evaluate_policy_on_load(policy, config, map_name, load, args.seeds, 'Coverage', verbose=True)
                else:
                    print(f"  ⚠️  未知策略: {policy_name}，跳过")
                    continue

                all_results.append(result)

                # 保存单个结果
                result_file = output_dir / f'{map_name}_load{load}_{policy_name_lower}_results.json'
                with open(result_file, 'w') as f:
                    json.dump(result, f, indent=2)

    elapsed_time = time.time() - start_time

    # 打印汇总表格
    print_summary_table(all_results)

    # 生成曲线图
    print(f"\n生成负载曲线图...")
    generate_load_curves(all_results, output_dir)

    # 保存汇总结果
    summary = {
        'config': args.config,
        'loads': args.loads,
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
    print(f"平均每个实验: {elapsed_time/total_experiments:.1f} 秒")


if __name__ == '__main__':
    main()
