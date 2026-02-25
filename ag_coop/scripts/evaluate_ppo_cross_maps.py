#!/usr/bin/env python3
"""
评估PPO模型在不同地图上的泛化能力

对比：
1. map_02单独训练的模型在3张地图上的表现
2. 多地图混合训练的模型在3张地图上的表现
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


def evaluate_model_on_map(
    model: PPO,
    config: Dict[str, Any],
    map_path: str,
    n_episodes: int = 10,
    seed_start: int = 20000
) -> Dict[str, Any]:
    """
    在指定地图上评估模型

    Args:
        model: PPO模型
        config: 配置字典
        map_path: 地图路径
        n_episodes: 评估episode数量
        seed_start: 起始随机种子

    Returns:
        评估结果字典
    """
    # 修改配置中的地图路径
    eval_config = config.copy()
    eval_config['episode']['map_path'] = map_path

    # 创建环境
    env = AGCoopGymEnv(eval_config)
    env = FlattenObservation(env)

    # 评估指标
    rewards = []
    tasks_completed = []
    deadline_miss_rates = []
    comm_penalties = []
    deadline_penalties = []

    print(f"  评估地图: {map_path}")

    for ep in range(n_episodes):
        seed = seed_start + ep
        obs, info = env.reset(seed=seed)

        episode_reward = 0.0
        done = False

        while not done:
            action, _states = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            done = terminated or truncated

        # 记录指标
        rewards.append(episode_reward)
        tasks_completed.append(info.get('tasks_completed', 0))

        # 计算deadline miss率
        total_tasks = info.get('tasks_completed', 0) + info.get('deadline_miss', 0)
        miss_rate = (info.get('deadline_miss', 0) / total_tasks * 100) if total_tasks > 0 else 0.0
        deadline_miss_rates.append(miss_rate)

        # 提取奖励组件
        comm_penalties.append(info.get('reward_comm', 0.0))
        deadline_penalties.append(info.get('reward_deadline', 0.0))

        if (ep + 1) % 5 == 0:
            print(f"    Episode {ep+1}/{n_episodes}: reward={episode_reward:.2f}, tasks={info.get('tasks_completed', 0)}")

    env.close()

    # 计算统计量
    results = {
        'map': map_path,
        'n_episodes': n_episodes,
        'reward_mean': float(np.mean(rewards)),
        'reward_std': float(np.std(rewards)),
        'reward_min': float(np.min(rewards)),
        'reward_max': float(np.max(rewards)),
        'tasks_mean': float(np.mean(tasks_completed)),
        'tasks_std': float(np.std(tasks_completed)),
        'tasks_min': float(np.min(tasks_completed)),
        'tasks_max': float(np.max(tasks_completed)),
        'miss_rate_mean': float(np.mean(deadline_miss_rates)),
        'miss_rate_std': float(np.std(deadline_miss_rates)),
        'comm_penalty_mean': float(np.mean(comm_penalties)),
        'deadline_penalty_mean': float(np.mean(deadline_penalties)),
    }

    return results


def main():
    parser = argparse.ArgumentParser(description='交叉评估PPO模型')
    parser.add_argument('--map02_model', type=str, required=True,
                        help='map_02单独训练的模型路径')
    parser.add_argument('--multimap_model', type=str, required=True,
                        help='多地图混合训练的模型路径')
    parser.add_argument('--config', type=str, default='configs/ppo_map02_train.yaml',
                        help='基础配置文件')
    parser.add_argument('--n_episodes', type=int, default=10,
                        help='每个地图评估的episode数量')
    parser.add_argument('--seed_start', type=int, default=20000,
                        help='评估起始随机种子')
    parser.add_argument('--output', type=str, default='outputs/ppo_cross_eval_results.json',
                        help='输出结果文件路径')

    args = parser.parse_args()

    print("=" * 70)
    print("PPO模型交叉评估")
    print("=" * 70)
    print()

    # 加载配置
    config = load_config(args.config)

    # 地图列表
    maps = [
        'maps/map_01.map',  # 中等遮挡
        'maps/map_02.map',  # 高遮挡
        'maps/map_03.map',  # 开阔
    ]

    # 加载模型
    print("加载模型...")
    print(f"  map_02模型: {args.map02_model}")
    map02_model = PPO.load(args.map02_model)
    print(f"  多地图模型: {args.multimap_model}")
    multimap_model = PPO.load(args.multimap_model)
    print()

    # 评估结果
    results = {
        'map02_model': {
            'model_path': args.map02_model,
            'maps': {}
        },
        'multimap_model': {
            'model_path': args.multimap_model,
            'maps': {}
        }
    }

    # 评估map_02模型
    print("=" * 70)
    print("评估 map_02 单独训练模型")
    print("=" * 70)
    for map_path in maps:
        print(f"\n在 {map_path} 上评估...")
        map_results = evaluate_model_on_map(
            map02_model, config, map_path, args.n_episodes, args.seed_start
        )
        results['map02_model']['maps'][map_path] = map_results
        print(f"  平均奖励: {map_results['reward_mean']:.2f} ± {map_results['reward_std']:.2f}")
        print(f"  平均任务数: {map_results['tasks_mean']:.1f} ± {map_results['tasks_std']:.1f}")
        print(f"  平均miss率: {map_results['miss_rate_mean']:.1f}%")

    # 评估多地图模型
    print("\n" + "=" * 70)
    print("评估 多地图混合训练模型")
    print("=" * 70)
    for map_path in maps:
        print(f"\n在 {map_path} 上评估...")
        map_results = evaluate_model_on_map(
            multimap_model, config, map_path, args.n_episodes, args.seed_start
        )
        results['multimap_model']['maps'][map_path] = map_results
        print(f"  平均奖励: {map_results['reward_mean']:.2f} ± {map_results['reward_std']:.2f}")
        print(f"  平均任务数: {map_results['tasks_mean']:.1f} ± {map_results['tasks_std']:.1f}")
        print(f"  平均miss率: {map_results['miss_rate_mean']:.1f}%")

    # 保存结果
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 70)
    print("评估完成")
    print("=" * 70)
    print(f"结果已保存到: {output_path}")

    # 打印对比总结
    print("\n" + "=" * 70)
    print("对比总结")
    print("=" * 70)

    for map_path in maps:
        map_name = Path(map_path).stem
        map02_res = results['map02_model']['maps'][map_path]
        multi_res = results['multimap_model']['maps'][map_path]

        print(f"\n{map_name}:")
        print(f"  map_02模型: 奖励={map02_res['reward_mean']:.2f}, 任务={map02_res['tasks_mean']:.1f}, miss率={map02_res['miss_rate_mean']:.1f}%")
        print(f"  多地图模型: 奖励={multi_res['reward_mean']:.2f}, 任务={multi_res['tasks_mean']:.1f}, miss率={multi_res['miss_rate_mean']:.1f}%")

        # 判断哪个更好
        if map02_res['reward_mean'] > multi_res['reward_mean']:
            print(f"  → map_02模型更好 (奖励高 {map02_res['reward_mean'] - multi_res['reward_mean']:.2f})")
        else:
            print(f"  → 多地图模型更好 (奖励高 {multi_res['reward_mean'] - map02_res['reward_mean']:.2f})")


if __name__ == '__main__':
    main()
