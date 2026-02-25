#!/usr/bin/env python3
"""
Curriculum Learning Model Evaluation Script

评估课程学习训练的模型在测试集上的表现
测试集：seeds 20000-20009（10个episode）
评估指标：完成任务数、方差、奖励等
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

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


def evaluate_model(
    model_path: str,
    config: Dict[str, Any],
    map_path: str,
    test_seeds: List[int],
    verbose: bool = True
) -> Dict[str, Any]:
    """
    评估模型在指定地图和种子上的表现

    Args:
        model_path: 模型路径
        config: 环境配置
        map_path: 地图路径
        test_seeds: 测试种子列表
        verbose: 是否打印详细信息

    Returns:
        评估结果字典
    """
    # 加载模型
    if verbose:
        print(f"加载模型: {model_path}")
    model = PPO.load(model_path)

    # 确保任务参数固定（分布对齐）
    config['tasks']['arrival_rate'] = 0.1
    config['tasks']['deadline_min'] = 25
    config['tasks']['deadline_max'] = 60
    config['episode']['map_path'] = map_path

    results = []

    for seed in test_seeds:
        if verbose:
            print(f"  评估 seed={seed}...", end=' ')

        # 创建环境
        env = AGCoopGymEnv(config)
        env = FlattenObservation(env)

        # 重置环境
        obs, info = env.reset(seed=seed)

        episode_reward = 0.0
        done = False
        truncated = False

        # 运行一个episode
        while not (done or truncated):
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, done, truncated, info = env.step(action)
            episode_reward += reward

        # 收集结果
        episode_result = {
            'seed': seed,
            'tasks_completed': info.get('tasks_completed', 0),
            'deadline_miss': info.get('deadline_miss', 0),
            'episode_reward': float(episode_reward),
            'outage_steps': info.get('outage_steps', 0),
            'tardiness_sum': info.get('tardiness_sum', 0),
        }
        results.append(episode_result)

        if verbose:
            print(f"完成任务={episode_result['tasks_completed']}, "
                  f"奖励={episode_result['episode_reward']:.2f}")

        env.close()

    # 计算统计信息
    tasks_completed = [r['tasks_completed'] for r in results]
    episode_rewards = [r['episode_reward'] for r in results]
    deadline_misses = [r['deadline_miss'] for r in results]

    stats = {
        'model_path': model_path,
        'map_path': map_path,
        'test_seeds': test_seeds,
        'n_episodes': len(results),
        'results': results,
        'statistics': {
            'tasks_completed': {
                'mean': float(np.mean(tasks_completed)),
                'std': float(np.std(tasks_completed)),
                'min': int(np.min(tasks_completed)),
                'max': int(np.max(tasks_completed)),
                'median': float(np.median(tasks_completed)),
            },
            'episode_reward': {
                'mean': float(np.mean(episode_rewards)),
                'std': float(np.std(episode_rewards)),
                'min': float(np.min(episode_rewards)),
                'max': float(np.max(episode_rewards)),
                'median': float(np.median(episode_rewards)),
            },
            'deadline_miss': {
                'mean': float(np.mean(deadline_misses)),
                'std': float(np.std(deadline_misses)),
                'min': int(np.min(deadline_misses)),
                'max': int(np.max(deadline_misses)),
                'median': float(np.median(deadline_misses)),
            },
        }
    }

    return stats


def main():
    parser = argparse.ArgumentParser(description='Evaluate Curriculum Learning Model')
    parser.add_argument('--model', type=str, required=True,
                        help='模型路径（.zip文件）')
    parser.add_argument('--config', type=str, default='configs/curriculum_learning.yaml',
                        help='配置文件路径')
    parser.add_argument('--map', type=str, default='maps/map_02.map',
                        help='测试地图路径')
    parser.add_argument('--test_seeds', type=str, default='20000-20009',
                        help='测试种子范围（格式：start-end）')
    parser.add_argument('--output', type=str, default=None,
                        help='输出结果文件路径（JSON）')

    args = parser.parse_args()

    # 解析测试种子
    if '-' in args.test_seeds:
        start, end = map(int, args.test_seeds.split('-'))
        test_seeds = list(range(start, end + 1))
    else:
        test_seeds = [int(args.test_seeds)]

    print("=" * 70)
    print("Curriculum Learning Model Evaluation")
    print("=" * 70)
    print(f"模型: {args.model}")
    print(f"配置: {args.config}")
    print(f"地图: {args.map}")
    print(f"测试种子: {test_seeds[0]}-{test_seeds[-1]} ({len(test_seeds)} episodes)")
    print()

    # 加载配置
    config = load_config(args.config)

    # 评估模型
    print("开始评估...")
    print()
    results = evaluate_model(
        args.model,
        config,
        args.map,
        test_seeds,
        verbose=True
    )

    # 打印统计信息
    print()
    print("=" * 70)
    print("评估结果")
    print("=" * 70)
    print()

    stats = results['statistics']

    print("完成任务数:")
    print(f"  平均值: {stats['tasks_completed']['mean']:.2f}")
    print(f"  标准差: {stats['tasks_completed']['std']:.2f}")
    print(f"  最小值: {stats['tasks_completed']['min']}")
    print(f"  最大值: {stats['tasks_completed']['max']}")
    print(f"  中位数: {stats['tasks_completed']['median']:.2f}")
    print()

    print("Episode奖励:")
    print(f"  平均值: {stats['episode_reward']['mean']:.2f}")
    print(f"  标准差: {stats['episode_reward']['std']:.2f}")
    print(f"  最小值: {stats['episode_reward']['min']:.2f}")
    print(f"  最大值: {stats['episode_reward']['max']:.2f}")
    print(f"  中位数: {stats['episode_reward']['median']:.2f}")
    print()

    print("Deadline Miss:")
    print(f"  平均值: {stats['deadline_miss']['mean']:.2f}")
    print(f"  标准差: {stats['deadline_miss']['std']:.2f}")
    print(f"  最小值: {stats['deadline_miss']['min']}")
    print(f"  最大值: {stats['deadline_miss']['max']}")
    print(f"  中位数: {stats['deadline_miss']['median']:.2f}")
    print()

    # 保存结果
    if args.output is None:
        model_name = Path(args.model).stem
        output_path = f'outputs/curriculum_eval_{model_name}.json'
    else:
        output_path = args.output

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"结果已保存: {output_path}")
    print()

    # 性能评估
    mean_tasks = stats['tasks_completed']['mean']
    std_tasks = stats['tasks_completed']['std']

    print("=" * 70)
    print("性能评估")
    print("=" * 70)
    print()

    if mean_tasks >= 35 and mean_tasks <= 40:
        print("✓ 目标达成：平均完成任务数在 35-40 范围内")
    else:
        print(f"✗ 目标未达成：平均完成任务数 {mean_tasks:.2f} 不在 35-40 范围内")

    if std_tasks < 5:
        print("✓ 方差良好：标准差 < 5，模型稳定性高")
    elif std_tasks < 8:
        print("○ 方差中等：标准差在 5-8 之间，模型稳定性一般")
    else:
        print(f"✗ 方差较大：标准差 {std_tasks:.2f} > 8，模型稳定性较差")

    print()


if __name__ == '__main__':
    main()
