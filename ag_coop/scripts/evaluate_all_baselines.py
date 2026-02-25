#!/usr/bin/env python3
"""
评估所有Baseline方法

对比：
1. Random baseline
2. Greedy baseline (EDF + 最近中继点)
3. Coverage baseline (EDF + 最大化覆盖)
4. PPO (map_02模型)
5. PPO (多地图模型)

在3张地图上评估，每个方法运行多个seeds
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np
import yaml
from stable_baselines3 import PPO

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv
from agcoop.policies import GreedyPolicy, CoveragePolicy


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def evaluate_random_policy(
    config: Dict[str, Any],
    map_path: str,
    n_episodes: int = 10,
    seed_start: int = 20000
) -> Dict[str, Any]:
    """
    评估Random策略

    Args:
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
    env = AGCoopEnv(
        eval_config,
        output_dir=None,
        enable_logging=False,
        method="random",
        planner="PIBT"
    )

    # 评估指标
    rewards = []
    tasks_completed = []
    deadline_miss_rates = []

    print(f"  评估地图: {map_path}")

    for ep in range(n_episodes):
        seed = seed_start + ep
        eval_config['episode']['seed'] = seed
        env.config = eval_config
        env.reset()

        # 运行episode
        done = False
        while not done:
            done = env.step()

        # 记录指标
        state = env.state
        episode_reward = state.total_reward
        rewards.append(episode_reward)
        tasks_completed.append(state.tasks_completed)

        # 计算deadline miss率
        total_tasks = state.tasks_completed + state.deadline_miss
        miss_rate = (state.deadline_miss / total_tasks * 100) if total_tasks > 0 else 0.0
        deadline_miss_rates.append(miss_rate)

        if (ep + 1) % 5 == 0:
            print(f"    Episode {ep+1}/{n_episodes}: reward={episode_reward:.2f}, tasks={state.tasks_completed}")

    # 计算统计量
    results = {
        'method': 'Random',
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
    }

    return results


def evaluate_deterministic_policy(
    policy,
    config: Dict[str, Any],
    map_path: str,
    n_episodes: int = 10,
    seed_start: int = 20000
) -> Dict[str, Any]:
    """
    评估确定性策略（Greedy或Coverage）

    Args:
        policy: 策略对象
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
    env = AGCoopEnv(
        eval_config,
        output_dir=None,
        enable_logging=False,
        method="rl",
        planner="PIBT"
    )

    # 评估指标
    rewards = []
    tasks_completed = []
    deadline_miss_rates = []

    print(f"  评估地图: {map_path}")

    for ep in range(n_episodes):
        seed = seed_start + ep
        eval_config['episode']['seed'] = seed
        env.config = eval_config
        obs = env.reset()

        # 运行episode
        done = False
        while not done:
            # 使用策略选择动作
            task_choice, relay_target = policy.select_action(obs, {})
            action = (task_choice, relay_target)

            # 执行动作
            obs, reward, done, info = env.step_rl(action)

        # 记录指标
        state = env.state
        episode_reward = state.total_reward
        rewards.append(episode_reward)
        tasks_completed.append(state.tasks_completed)

        # 计算deadline miss率
        total_tasks = state.tasks_completed + state.deadline_miss
        miss_rate = (state.deadline_miss / total_tasks * 100) if total_tasks > 0 else 0.0
        deadline_miss_rates.append(miss_rate)

        if (ep + 1) % 5 == 0:
            print(f"    Episode {ep+1}/{n_episodes}: reward={episode_reward:.2f}, tasks={state.tasks_completed}")

    # 计算统计量
    results = {
        'method': policy.get_name(),
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
    }

    return results


def evaluate_ppo_policy(
    model: PPO,
    config: Dict[str, Any],
    map_path: str,
    model_name: str,
    n_episodes: int = 10,
    seed_start: int = 20000
) -> Dict[str, Any]:
    """
    评估PPO策略

    Args:
        model: PPO模型
        config: 配置字典
        map_path: 地图路径
        model_name: 模型名称
        n_episodes: 评估episode数量
        seed_start: 起始随机种子

    Returns:
        评估结果字典
    """
    # 修改配置中的地图路径
    eval_config = config.copy()
    eval_config['episode']['map_path'] = map_path

    # 创建环境
    env = AGCoopEnv(
        eval_config,
        output_dir=None,
        enable_logging=False,
        method="rl",
        planner="PIBT"
    )

    # 评估指标
    rewards = []
    tasks_completed = []
    deadline_miss_rates = []

    print(f"  评估地图: {map_path}")

    for ep in range(n_episodes):
        seed = seed_start + ep
        eval_config['episode']['seed'] = seed
        env.config = eval_config
        obs = env.reset()

        # Flatten observation
        obs_flat = env.flatten_observation(obs)

        # 运行episode
        done = False
        while not done:
            # 使用PPO选择动作
            action_flat, _states = model.predict(obs_flat, deterministic=True)

            # 解码动作
            action = env.decode_action(action_flat)

            # 执行动作
            obs, reward, done, info = env.step_rl(action)
            obs_flat = env.flatten_observation(obs)

        # 记录指标
        state = env.state
        episode_reward = state.total_reward
        rewards.append(episode_reward)
        tasks_completed.append(state.tasks_completed)

        # 计算deadline miss率
        total_tasks = state.tasks_completed + state.deadline_miss
        miss_rate = (state.deadline_miss / total_tasks * 100) if total_tasks > 0 else 0.0
        deadline_miss_rates.append(miss_rate)

        if (ep + 1) % 5 == 0:
            print(f"    Episode {ep+1}/{n_episodes}: reward={episode_reward:.2f}, tasks={state.tasks_completed}")

    # 计算统计量
    results = {
        'method': model_name,
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
    }

    return results


def main():
    parser = argparse.ArgumentParser(description='评估所有Baseline方法')
    parser.add_argument('--config', type=str, default='configs/ppo_map02_train.yaml',
                        help='基础配置文件')
    parser.add_argument('--maps', type=str, nargs='+',
                        default=['maps/map_01.map', 'maps/map_02.map', 'maps/map_03.map'],
                        help='评估地图列表')
    parser.add_argument('--ppo_map02', type=str, default=None,
                        help='map_02训练的PPO模型路径')
    parser.add_argument('--ppo_multimap', type=str, default=None,
                        help='多地图训练的PPO模型路径')
    parser.add_argument('--n_episodes', type=int, default=10,
                        help='每个地图评估的episode数量')
    parser.add_argument('--seed_start', type=int, default=20000,
                        help='评估起始随机种子')
    parser.add_argument('--output', type=str, default='outputs/baseline_comparison.json',
                        help='输出结果文件路径')

    args = parser.parse_args()

    print("=" * 70)
    print("评估所有Baseline方法")
    print("=" * 70)
    print()

    # 加载配置
    config = load_config(args.config)

    # 评估结果
    all_results = []

    # 方法列表
    methods = ['Random', 'Greedy', 'Coverage']
    if args.ppo_map02:
        methods.append('PPO-map02')
    if args.ppo_multimap:
        methods.append('PPO-multimap')

    print(f"评估方法: {', '.join(methods)}")
    print(f"评估地图: {', '.join(args.maps)}")
    print(f"每地图episodes: {args.n_episodes}")
    print()

    # 加载PPO模型（如果提供）
    ppo_map02_model = None
    ppo_multimap_model = None

    if args.ppo_map02:
        print(f"加载PPO-map02模型: {args.ppo_map02}")
        ppo_map02_model = PPO.load(args.ppo_map02)

    if args.ppo_multimap:
        print(f"加载PPO-multimap模型: {args.ppo_multimap}")
        ppo_multimap_model = PPO.load(args.ppo_multimap)

    print()

    # 对每张地图评估所有方法
    for map_path in args.maps:
        map_name = Path(map_path).stem
        print("=" * 70)
        print(f"评估地图: {map_name}")
        print("=" * 70)

        # 1. Random
        print("\n[1/5] Random baseline")
        result = evaluate_random_policy(config, map_path, args.n_episodes, args.seed_start)
        all_results.append(result)
        print(f"  结果: 奖励={result['reward_mean']:.2f}±{result['reward_std']:.2f}, "
              f"任务={result['tasks_mean']:.1f}±{result['tasks_std']:.1f}, "
              f"miss率={result['miss_rate_mean']:.1f}%")

        # 2. Greedy
        print("\n[2/5] Greedy baseline")
        greedy_policy = GreedyPolicy(config)
        result = evaluate_deterministic_policy(greedy_policy, config, map_path, args.n_episodes, args.seed_start)
        all_results.append(result)
        print(f"  结果: 奖励={result['reward_mean']:.2f}±{result['reward_std']:.2f}, "
              f"任务={result['tasks_mean']:.1f}±{result['tasks_std']:.1f}, "
              f"miss率={result['miss_rate_mean']:.1f}%")

        # 3. Coverage
        print("\n[3/5] Coverage baseline")
        coverage_policy = CoveragePolicy(config)
        result = evaluate_deterministic_policy(coverage_policy, config, map_path, args.n_episodes, args.seed_start)
        all_results.append(result)
        print(f"  结果: 奖励={result['reward_mean']:.2f}±{result['reward_std']:.2f}, "
              f"任务={result['tasks_mean']:.1f}±{result['tasks_std']:.1f}, "
              f"miss率={result['miss_rate_mean']:.1f}%")

        # 4. PPO-map02 (如果提供)
        if ppo_map02_model:
            print("\n[4/5] PPO-map02")
            result = evaluate_ppo_policy(ppo_map02_model, config, map_path, 'PPO-map02', args.n_episodes, args.seed_start)
            all_results.append(result)
            print(f"  结果: 奖励={result['reward_mean']:.2f}±{result['reward_std']:.2f}, "
                  f"任务={result['tasks_mean']:.1f}±{result['tasks_std']:.1f}, "
                  f"miss率={result['miss_rate_mean']:.1f}%")

        # 5. PPO-multimap (如果提供)
        if ppo_multimap_model:
            print("\n[5/5] PPO-multimap")
            result = evaluate_ppo_policy(ppo_multimap_model, config, map_path, 'PPO-multimap', args.n_episodes, args.seed_start)
            all_results.append(result)
            print(f"  结果: 奖励={result['reward_mean']:.2f}±{result['reward_std']:.2f}, "
                  f"任务={result['tasks_mean']:.1f}±{result['tasks_std']:.1f}, "
                  f"miss率={result['miss_rate_mean']:.1f}%")

        print()

    # 保存结果
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(all_results, f, indent=2)

    print("=" * 70)
    print("评估完成")
    print("=" * 70)
    print(f"结果已保存到: {output_path}")
    print()

    # 打印对比总结
    print("=" * 70)
    print("对比总结")
    print("=" * 70)

    for map_path in args.maps:
        map_name = Path(map_path).stem
        print(f"\n{map_name}:")

        # 提取该地图的所有结果
        map_results = [r for r in all_results if r['map'] == map_path]

        # 按奖励排序
        map_results_sorted = sorted(map_results, key=lambda x: x['reward_mean'], reverse=True)

        for i, result in enumerate(map_results_sorted):
            print(f"  {i+1}. {result['method']:15s}: "
                  f"奖励={result['reward_mean']:6.2f}, "
                  f"任务={result['tasks_mean']:5.1f}, "
                  f"miss率={result['miss_rate_mean']:5.1f}%")

    print()


if __name__ == '__main__':
    main()
