#!/usr/bin/env python3
"""
PPO Multi-Map Multi-Load Evaluation Script

评估训练好的PPO策略在多地图和多负载下的性能

使用方法:
    python scripts/evaluate_ppo_multi.py --model outputs/day10_ppo_summary/best_model.zip --loads 3.0 6.0 9.0 --maps map_01 map_02 map_03 --seeds 10000 10001 10002 10003 10004
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List
import time

import numpy as np
import yaml
from stable_baselines3 import PPO

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from agcoop.rl import AGCoopGymEnv
from agcoop.env.wrappers import FlattenObservation


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def evaluate_ppo_on_load(
    model: PPO,
    config: Dict[str, Any],
    map_name: str,
    load: float,
    seeds: List[int],
    verbose: bool = True
) -> Dict[str, Any]:
    """
    在特定负载下评估PPO策略

    Args:
        model: 训练好的PPO模型
        config: 环境配置
        map_name: 地图名称
        load: 任务到达率（λ）
        seeds: 评估种子列表
        verbose: 是否打印详细信息

    Returns:
        评估结果字典
    """
    if verbose:
        print(f"  [PPO on {map_name}, λ={load}]", end=' ', flush=True)

    # 修改配置
    config_copy = config.copy()
    config_copy['episode']['map_path'] = f'maps/{map_name}.map'
    config_copy['tasks']['arrival_rate'] = load

    episode_results = []

    for seed in seeds:
        try:
            # 创建环境（需要FlattenObservation包装器，因为PPO训练时使用了）
            base_env = AGCoopGymEnv(
                config=config_copy,
                output_dir=None,
                enable_logging=False,
            )
            env = FlattenObservation(base_env)
            obs, info = env.reset(seed=seed)

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
                # 使用PPO选择动作（deterministic=True for evaluation）
                action, _states = model.predict(obs, deterministic=True)

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
            import traceback
            traceback.print_exc()
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
        'policy_name': 'PPO',
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


def load_baseline_results(baseline_dir: Path) -> List[Dict[str, Any]]:
    """加载baseline结果"""
    baseline_results = []

    # 查找所有baseline结果文件
    for result_file in baseline_dir.glob('*_results.json'):
        try:
            with open(result_file, 'r') as f:
                result = json.load(f)
                baseline_results.append(result)
        except Exception as e:
            print(f"⚠️  加载 {result_file} 失败: {e}")

    return baseline_results


def compare_with_baselines(ppo_results: List[Dict[str, Any]], baseline_results: List[Dict[str, Any]]) -> None:
    """对比PPO与baseline性能"""
    print("\n" + "="*100)
    print("PPO vs Baselines 性能对比")
    print("="*100)

    # 按地图和负载组织结果
    map_names = sorted(set(r['map_name'] for r in ppo_results))
    loads = sorted(set(r['load'] for r in ppo_results))

    for map_name in map_names:
        print(f"\n{map_name}:")
        print(f"  {'Load':<8} {'Policy':<12} {'Reward':<12} {'Throughput':<12} {'Miss Rate':<12} {'Comm':<12}")
        print("  " + "-"*90)

        for load in loads:
            # PPO结果
            ppo_match = [r for r in ppo_results if r['map_name'] == map_name and r['load'] == load]
            if ppo_match and len(ppo_match[0]['episodes']) > 0:
                stats = ppo_match[0]['stats']
                print(f"  {load:<8.1f} {'PPO':<12} "
                      f"{stats['mean_total_reward']:<12.2f} "
                      f"{stats['mean_throughput']:<12.2f} "
                      f"{stats['mean_miss_rate']:<12.2f} "
                      f"{stats['mean_reward_comm']:<12.2f}")

            # Baseline结果
            for policy_name in ['Random', 'Greedy', 'Coverage']:
                baseline_match = [r for r in baseline_results
                                 if r['map_name'] == map_name
                                 and r['load'] == load
                                 and r['policy_name'] == policy_name]
                if baseline_match and len(baseline_match[0]['episodes']) > 0:
                    stats = baseline_match[0]['stats']
                    print(f"  {load:<8.1f} {policy_name:<12} "
                          f"{stats['mean_total_reward']:<12.2f} "
                          f"{stats['mean_throughput']:<12.2f} "
                          f"{stats['mean_miss_rate']:<12.2f} "
                          f"{stats['mean_reward_comm']:<12.2f}")

    # 计算平均性能提升
    print(f"\n{'='*100}")
    print("平均性能提升（PPO vs Baselines）")
    print(f"{'='*100}")
    print(f"  {'Map':<12} {'vs Policy':<12} {'Reward Δ':<15} {'Throughput Δ':<15} {'Miss Rate Δ':<15}")
    print("-"*100)

    for map_name in map_names:
        ppo_map_results = [r for r in ppo_results if r['map_name'] == map_name and len(r['episodes']) > 0]
        if not ppo_map_results:
            continue

        ppo_avg_reward = np.mean([r['stats']['mean_total_reward'] for r in ppo_map_results])
        ppo_avg_throughput = np.mean([r['stats']['mean_throughput'] for r in ppo_map_results])
        ppo_avg_miss = np.mean([r['stats']['mean_miss_rate'] for r in ppo_map_results])

        for policy_name in ['Random', 'Greedy', 'Coverage']:
            baseline_map_results = [r for r in baseline_results
                                   if r['map_name'] == map_name
                                   and r['policy_name'] == policy_name
                                   and len(r['episodes']) > 0]
            if not baseline_map_results:
                continue

            baseline_avg_reward = np.mean([r['stats']['mean_total_reward'] for r in baseline_map_results])
            baseline_avg_throughput = np.mean([r['stats']['mean_throughput'] for r in baseline_map_results])
            baseline_avg_miss = np.mean([r['stats']['mean_miss_rate'] for r in baseline_map_results])

            reward_improvement = ((ppo_avg_reward - baseline_avg_reward) / abs(baseline_avg_reward) * 100) if baseline_avg_reward != 0 else 0
            throughput_improvement = ((ppo_avg_throughput - baseline_avg_throughput) / baseline_avg_throughput * 100) if baseline_avg_throughput != 0 else 0
            miss_improvement = baseline_avg_miss - ppo_avg_miss  # 负数表示PPO miss rate更低（更好）

            print(f"  {map_name:<12} {policy_name:<12} "
                  f"{reward_improvement:>+14.2f}% "
                  f"{throughput_improvement:>+14.2f}% "
                  f"{miss_improvement:>+14.2f}%")

    print("="*100)


def main():
    parser = argparse.ArgumentParser(description='PPO Multi-Map Multi-Load Evaluation')
    parser.add_argument('--model', type=str, default='outputs/day10_ppo_summary/best_model.zip',
                        help='PPO模型路径')
    parser.add_argument('--config', type=str, default='configs/day10_ppo_train.yaml',
                        help='配置文件路径')
    parser.add_argument('--loads', type=float, nargs='+', default=[3.0, 6.0, 9.0],
                        help='任务到达率列表（λ）')
    parser.add_argument('--maps', type=str, nargs='+', default=['map_01', 'map_02', 'map_03'],
                        help='要评估的地图列表')
    parser.add_argument('--seeds', type=int, nargs='+', default=[10000, 10001, 10002, 10003, 10004],
                        help='评估种子列表')
    parser.add_argument('--baseline_dir', type=str, default='outputs/multi_load_evaluation',
                        help='Baseline结果目录')
    parser.add_argument('--output_dir', type=str, default='outputs/ppo_multi_evaluation',
                        help='输出目录')
    args = parser.parse_args()

    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载配置
    config = load_config(args.config)

    print("="*100)
    print("PPO Multi-Map Multi-Load Evaluation")
    print("="*100)
    print(f"  PPO模型: {args.model}")
    print(f"  配置文件: {args.config}")
    print(f"  负载列表: {args.loads}")
    print(f"  地图列表: {args.maps}")
    print(f"  评估种子: {args.seeds}")
    print(f"  输出目录: {args.output_dir}")
    print("="*100)

    # 加载PPO模型
    print(f"\n加载PPO模型...")
    try:
        model = PPO.load(args.model)
        print(f"✓ PPO模型加载成功")
    except Exception as e:
        print(f"❌ PPO模型加载失败: {e}")
        return

    # 计算总实验数
    total_experiments = len(args.loads) * len(args.maps)
    print(f"\n总实验数: {total_experiments} ({len(args.loads)} loads × {len(args.maps)} maps)")
    print(f"每个实验运行 {len(args.seeds)} 个种子\n")

    # 评估所有组合
    ppo_results = []
    start_time = time.time()

    for load in args.loads:
        print(f"\n{'='*100}")
        print(f"负载 λ={load}")
        print(f"{'='*100}")

        for map_name in args.maps:
            result = evaluate_ppo_on_load(model, config, map_name, load, args.seeds, verbose=True)
            ppo_results.append(result)

            # 保存单个结果
            result_file = output_dir / f'{map_name}_load{load}_ppo_results.json'
            with open(result_file, 'w') as f:
                json.dump(result, f, indent=2)

    elapsed_time = time.time() - start_time

    # 保存PPO汇总结果
    ppo_summary = {
        'model': args.model,
        'config': args.config,
        'loads': args.loads,
        'maps': args.maps,
        'seeds': args.seeds,
        'total_experiments': total_experiments,
        'elapsed_time_seconds': elapsed_time,
        'results': ppo_results,
    }
    with open(output_dir / 'ppo_summary.json', 'w') as f:
        json.dump(ppo_summary, f, indent=2)

    # 加载baseline结果并对比
    print(f"\n加载baseline结果...")
    baseline_dir = Path(args.baseline_dir)
    if baseline_dir.exists():
        baseline_results = load_baseline_results(baseline_dir)
        print(f"✓ 加载了 {len(baseline_results)} 个baseline结果")

        # 对比性能
        compare_with_baselines(ppo_results, baseline_results)
    else:
        print(f"⚠️  Baseline目录不存在: {baseline_dir}")

    print(f"\n结果已保存到: {output_dir}")
    print(f"总耗时: {elapsed_time:.1f} 秒 ({elapsed_time/60:.1f} 分钟)")
    print(f"平均每个实验: {elapsed_time/total_experiments:.1f} 秒")


if __name__ == '__main__':
    main()
