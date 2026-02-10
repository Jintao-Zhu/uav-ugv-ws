#!/usr/bin/env python3
"""
Day10 Step 5: 对照随机策略

对比随机策略和训练后的 PPO 策略，证明策略确实学到了东西

验收标准：
1. PPO mean_reward > Random mean_reward（至少高 5%）
   或 PPO tasks_completed_mean > Random tasks_completed_mean（至少高 10%）
2. PPO rollout 不出现 NaN/Inf，不崩溃
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
import yaml
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

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


def make_env(config: Dict[str, Any], seed: int):
    """创建环境"""
    def _init():
        env = AGCoopGymEnv(
            config=config,
            output_dir=None,
            enable_logging=False,
        )
        env = FlattenObservation(env)
        env = Monitor(env)
        return env
    return _init


def evaluate_random_policy(config: Dict[str, Any], seeds: List[int], verbose: bool = True) -> Dict[str, Any]:
    """
    评估随机策略

    Args:
        config: 环境配置
        seeds: 评估种子列表
        verbose: 是否打印详细信息

    Returns:
        评估结果字典
    """
    if verbose:
        print("=" * 70)
        print("评估随机策略")
        print("=" * 70)

    episode_results = []

    for seed in seeds:
        if verbose:
            print(f"\n  Episode (seed={seed})...")

        # 创建环境
        env = make_env(config, seed)()
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
            # 随机动作
            action = env.action_space.sample()
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

        # 记录结果（直接从 info 获取 metrics）
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
        print("\n随机策略评估结果:")
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
        'episodes': episode_results,
        'stats': stats,
    }


def evaluate_ppo_policy(model_path: str, config: Dict[str, Any], seeds: List[int], verbose: bool = True) -> Dict[str, Any]:
    """
    评估 PPO 策略

    Args:
        model_path: PPO 模型路径
        config: 环境配置
        seeds: 评估种子列表
        verbose: 是否打印详细信息

    Returns:
        评估结果字典
    """
    if verbose:
        print("=" * 70)
        print("评估 PPO 策略")
        print("=" * 70)
        print(f"  加载模型: {model_path}")

    # 加载模型
    model = PPO.load(model_path)

    episode_results = []
    has_nan_inf = False

    for seed in seeds:
        if verbose:
            print(f"\n  Episode (seed={seed})...")

        # 创建环境
        env = make_env(config, seed)()
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
            # PPO 动作（确定性）
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            done = terminated or truncated

            # 检查 NaN/Inf
            if np.isnan(reward) or np.isinf(reward):
                has_nan_inf = True
                if verbose:
                    print(f"    ⚠️  检测到 NaN/Inf reward: {reward}")

            if np.any(np.isnan(obs)) or np.any(np.isinf(obs)):
                has_nan_inf = True
                if verbose:
                    print(f"    ⚠️  检测到 NaN/Inf observation")

            total_reward += reward
            episode_length += 1

            # 累积 reward 分量
            if 'reward_components' in info:
                rc = info['reward_components']
                for key in reward_components_sum.keys():
                    if key in rc:
                        reward_components_sum[key] += rc[key]

        # 记录结果（直接从 info 获取 metrics）
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
    stats['has_nan_inf'] = has_nan_inf

    if verbose:
        print("\nPPO 策略评估结果:")
        print(f"  Mean reward: {stats['mean_total_reward']:.4f} ± {stats['std_total_reward']:.4f}")
        print(f"  Mean tasks completed: {stats['mean_tasks_completed']:.2f} ± {stats['std_tasks_completed']:.2f}")
        print(f"  Reward components (mean):")
        print(f"    - Task: {stats['mean_reward_task']:.4f}")
        print(f"    - Time: {stats['mean_reward_time']:.4f}")
        print(f"    - Comm: {stats['mean_reward_comm']:.4f}")
        print(f"    - Deadline: {stats['mean_reward_deadline']:.4f}")
        print(f"    - MAPF: {stats['mean_reward_mapf']:.4f}")
        print(f"  NaN/Inf detected: {'Yes ⚠️' if has_nan_inf else 'No ✅'}")
        print("=" * 70)

    return {
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


def compare_policies(random_stats: Dict[str, float], ppo_stats: Dict[str, float]) -> bool:
    """
    对比两个策略

    Args:
        random_stats: 随机策略统计量
        ppo_stats: PPO 策略统计量

    Returns:
        是否通过验收
    """
    print("\n" + "=" * 70)
    print("策略对比")
    print("=" * 70)

    # 对比 mean_reward
    random_reward = random_stats['mean_total_reward']
    ppo_reward = ppo_stats['mean_total_reward']
    reward_improvement = (ppo_reward - random_reward) / random_reward * 100

    print(f"\nMean Reward:")
    print(f"  Random: {random_reward:.4f}")
    print(f"  PPO:    {ppo_reward:.4f}")
    print(f"  Improvement: {reward_improvement:+.2f}%")

    # 对比 tasks_completed
    random_tasks = random_stats['mean_tasks_completed']
    ppo_tasks = ppo_stats['mean_tasks_completed']

    if random_tasks > 0:
        tasks_improvement = (ppo_tasks - random_tasks) / random_tasks * 100
    else:
        tasks_improvement = 0.0 if ppo_tasks == 0 else float('inf')

    print(f"\nMean Tasks Completed:")
    print(f"  Random: {random_tasks:.2f}")
    print(f"  PPO:    {ppo_tasks:.2f}")
    if tasks_improvement != float('inf'):
        print(f"  Improvement: {tasks_improvement:+.2f}%")
    else:
        print(f"  Improvement: +∞% (Random = 0)")

    # 对比 reward 分量
    print(f"\nReward Components:")
    print(f"  {'Component':<15} {'Random':<10} {'PPO':<10} {'Improvement':<15}")
    print("-" * 70)

    components = ['task', 'time', 'comm', 'deadline', 'mapf']
    for comp in components:
        random_val = random_stats[f'mean_reward_{comp}']
        ppo_val = ppo_stats[f'mean_reward_{comp}']

        if random_val != 0:
            comp_improvement = (ppo_val - random_val) / abs(random_val) * 100
        else:
            comp_improvement = 0.0 if ppo_val == 0 else float('inf')

        if comp_improvement != float('inf'):
            print(f"  {comp:<15} {random_val:<10.2f} {ppo_val:<10.2f} {comp_improvement:+.2f}%")
        else:
            print(f"  {comp:<15} {random_val:<10.2f} {ppo_val:<10.2f} +∞%")

    # 验收标准
    print("\n" + "=" * 70)
    print("验收标准检查")
    print("=" * 70)

    # 标准 1: Reward 提升 ≥ 5% 或 Tasks 提升 ≥ 10%
    reward_pass = reward_improvement >= 5.0
    tasks_pass = tasks_improvement >= 10.0 or tasks_improvement == float('inf')

    print(f"\n标准 1: PPO 性能优于随机策略")
    print(f"  Reward 提升 ≥ 5%: {reward_improvement:+.2f}% {'✅' if reward_pass else '❌'}")
    print(f"  Tasks 提升 ≥ 10%: {tasks_improvement if tasks_improvement != float('inf') else '+∞'}% {'✅' if tasks_pass else '❌'}")

    performance_pass = reward_pass or tasks_pass
    print(f"  结果: {'✅ 通过' if performance_pass else '❌ 未通过'} (任一满足即可)")

    # 标准 2: 无 NaN/Inf
    nan_inf_pass = not ppo_stats.get('has_nan_inf', False)
    print(f"\n标准 2: PPO rollout 无 NaN/Inf")
    print(f"  结果: {'✅ 通过' if nan_inf_pass else '❌ 未通过'}")

    # 总结
    print("\n" + "=" * 70)
    print("验收结果")
    print("=" * 70)
    print(f"  标准 1 (性能优于随机): {'✅ 通过' if performance_pass else '❌ 未通过'}")
    print(f"  标准 2 (无 NaN/Inf): {'✅ 通过' if nan_inf_pass else '❌ 未通过'}")
    print("=" * 70)

    overall_pass = performance_pass and nan_inf_pass

    if overall_pass:
        print("\n🎉 Day10 Step 5 验收通过！")
    else:
        print("\n❌ Day10 Step 5 验收未通过")

    return overall_pass


def main():
    parser = argparse.ArgumentParser(description='Day10 Step 5: 对照随机策略')
    parser.add_argument('--config', type=str, default='configs/day10_ppo_train.yaml',
                        help='配置文件路径')
    parser.add_argument('--model', type=str, default='outputs/day10_step4_100k/checkpoints/ppo_model_final.zip',
                        help='PPO 模型路径')
    parser.add_argument('--seeds', type=int, nargs='+', default=[10000, 10001, 10002, 10003, 10004],
                        help='评估种子列表')
    parser.add_argument('--output_dir', type=str, default='outputs/day10_step5_comparison',
                        help='输出目录')
    args = parser.parse_args()

    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载配置
    config = load_config(args.config)

    print("=" * 70)
    print("Day10 Step 5: 对照随机策略")
    print("=" * 70)
    print(f"  配置文件: {args.config}")
    print(f"  PPO 模型: {args.model}")
    print(f"  评估种子: {args.seeds}")
    print(f"  输出目录: {args.output_dir}")
    print("=" * 70)
    print()

    # 评估随机策略
    random_results = evaluate_random_policy(config, args.seeds, verbose=True)

    # 保存随机策略结果
    with open(output_dir / 'random_policy_results.json', 'w') as f:
        json.dump(random_results, f, indent=2)

    print()

    # 评估 PPO 策略
    ppo_results = evaluate_ppo_policy(args.model, config, args.seeds, verbose=True)

    # 保存 PPO 策略结果
    with open(output_dir / 'ppo_policy_results.json', 'w') as f:
        json.dump(ppo_results, f, indent=2)

    print()

    # 对比策略
    overall_pass = compare_policies(random_results['stats'], ppo_results['stats'])

    # 保存对比结果
    comparison = {
        'random': random_results['stats'],
        'ppo': ppo_results['stats'],
        'pass': overall_pass,
    }
    with open(output_dir / 'comparison_results.json', 'w') as f:
        json.dump(comparison, f, indent=2)

    print(f"\n结果已保存到: {output_dir}")

    sys.exit(0 if overall_pass else 1)


if __name__ == '__main__':
    main()
