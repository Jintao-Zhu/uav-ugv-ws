#!/usr/bin/env python3
"""
Day 5-7: 多负载实验

测试不同任务压力下各策略的表现：
- 负载: λ ∈ {3.0, 6.0, 9.0} (低/中/高)
- 地图: map_01, map_02, map_03
- 方法: Random, Greedy, Coverage
- Seeds: 5个评估种子

产出: Throughput vs Load曲线
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
from agcoop.policies import GreedyPolicy, CoveragePolicy


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def evaluate_policy(
    policy,
    policy_name: str,
    config: Dict[str, Any],
    map_path: str,
    arrival_rate: float,
    seeds: List[int]
) -> Dict[str, Any]:
    """
    评估策略在指定负载下的表现

    Args:
        policy: 策略对象（None表示Random）
        policy_name: 策略名称
        config: 配置字典
        map_path: 地图路径
        arrival_rate: 任务到达率（λ）
        seeds: 评估种子列表

    Returns:
        评估结果字典
    """
    # 修改配置
    eval_config = config.copy()
    eval_config['episode']['map_path'] = map_path
    eval_config['tasks']['arrival_rate'] = arrival_rate

    # 评估指标
    rewards = []
    tasks_completed = []
    deadline_miss_rates = []
    throughputs = []  # 任务完成率（tasks/step）

    for seed in seeds:
        # 创建环境
        env = AGCoopGymEnv(
            config=eval_config,
            output_dir=None,
            enable_logging=False,
        )
        obs, info = env.reset(seed=seed)

        # 重置策略
        if policy is not None:
            policy.reset()

        # 运行episode
        done = False
        total_reward = 0.0
        episode_length = 0

        while not done:
            # 选择动作
            if policy is None:
                # Random策略
                action = env.action_space.sample()
            else:
                # 确定性策略
                task_choice, relay_target = policy.select_action(obs, info)
                action = (task_choice, relay_target)

            # 执行动作
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            episode_length += 1
            done = terminated or truncated

        # 记录指标
        rewards.append(total_reward)
        tasks_completed.append(info.get('tasks_completed', 0))

        # 计算deadline miss率
        total_tasks = info.get('tasks_completed', 0) + info.get('deadline_miss', 0)
        miss_rate = (info.get('deadline_miss', 0) / total_tasks * 100) if total_tasks > 0 else 0.0
        deadline_miss_rates.append(miss_rate)

        # 计算吞吐量（tasks/step）
        throughput = info.get('tasks_completed', 0) / episode_length if episode_length > 0 else 0.0
        throughputs.append(throughput)

        env.close()

    # 计算统计量
    results = {
        'policy': policy_name,
        'map': map_path,
        'arrival_rate': arrival_rate,
        'n_episodes': len(seeds),
        'reward_mean': float(np.mean(rewards)),
        'reward_std': float(np.std(rewards)),
        'tasks_mean': float(np.mean(tasks_completed)),
        'tasks_std': float(np.std(tasks_completed)),
        'miss_rate_mean': float(np.mean(deadline_miss_rates)),
        'miss_rate_std': float(np.std(deadline_miss_rates)),
        'throughput_mean': float(np.mean(throughputs)),
        'throughput_std': float(np.std(throughputs)),
    }

    return results


def main():
    parser = argparse.ArgumentParser(description='多负载实验')
    parser.add_argument('--config', type=str, default='configs/ppo_map02_train.yaml',
                        help='基础配置文件')
    parser.add_argument('--maps', type=str, nargs='+',
                        default=['maps/map_01.map', 'maps/map_02.map', 'maps/map_03.map'],
                        help='评估地图列表')
    parser.add_argument('--loads', type=float, nargs='+',
                        default=[3.0, 6.0, 9.0],
                        help='任务到达率列表（λ）')
    parser.add_argument('--policies', type=str, nargs='+',
                        default=['random', 'greedy', 'coverage'],
                        help='评估策略列表')
    parser.add_argument('--seeds', type=int, nargs='+',
                        default=[20000, 20001, 20002, 20003, 20004],
                        help='评估种子列表')
    parser.add_argument('--output', type=str, default='outputs/multi_load_results.json',
                        help='输出结果文件路径')

    args = parser.parse_args()

    print("=" * 70)
    print("Day 5-7: 多负载实验")
    print("=" * 70)
    print()
    print(f"地图: {', '.join([Path(m).stem for m in args.maps])}")
    print(f"负载: λ ∈ {{{', '.join([str(l) for l in args.loads])}}}")
    print(f"策略: {', '.join(args.policies)}")
    print(f"Seeds: {len(args.seeds)} 个")
    print()

    # 加载配置
    config = load_config(args.config)

    # 评估结果
    all_results = []

    # 总实验数
    total_experiments = len(args.maps) * len(args.loads) * len(args.policies)
    current_experiment = 0

    # 对每个组合进行评估
    for map_path in args.maps:
        map_name = Path(map_path).stem

        for arrival_rate in args.loads:
            print("=" * 70)
            print(f"地图: {map_name}, 负载: λ={arrival_rate}")
            print("=" * 70)

            for policy_name in args.policies:
                current_experiment += 1
                print(f"\n[{current_experiment}/{total_experiments}] 评估 {policy_name} 策略...")

                # 创建策略
                if policy_name.lower() == 'random':
                    policy = None
                elif policy_name.lower() == 'greedy':
                    policy = GreedyPolicy(config)
                elif policy_name.lower() == 'coverage':
                    policy = CoveragePolicy(config)
                else:
                    print(f"  未知策略: {policy_name}，跳过")
                    continue

                # 评估
                result = evaluate_policy(
                    policy,
                    policy_name,
                    config,
                    map_path,
                    arrival_rate,
                    args.seeds
                )
                all_results.append(result)

                print(f"  结果: 奖励={result['reward_mean']:.2f}±{result['reward_std']:.2f}, "
                      f"任务={result['tasks_mean']:.1f}±{result['tasks_std']:.1f}, "
                      f"吞吐量={result['throughput_mean']:.4f}±{result['throughput_std']:.4f}, "
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

    # 打印总结
    print("=" * 70)
    print("结果总结")
    print("=" * 70)

    for map_path in args.maps:
        map_name = Path(map_path).stem
        print(f"\n{map_name}:")
        print(f"{'负载':<10} {'策略':<15} {'吞吐量':<20} {'任务数':<20} {'Miss率':<15}")
        print("-" * 80)

        for arrival_rate in args.loads:
            # 提取该地图和负载的所有结果
            map_load_results = [
                r for r in all_results
                if r['map'] == map_path and r['arrival_rate'] == arrival_rate
            ]

            # 按吞吐量排序
            map_load_results_sorted = sorted(
                map_load_results,
                key=lambda x: x['throughput_mean'],
                reverse=True
            )

            for result in map_load_results_sorted:
                print(f"λ={result['arrival_rate']:<7.1f} "
                      f"{result['policy']:<15} "
                      f"{result['throughput_mean']:.4f}±{result['throughput_std']:.4f}    "
                      f"{result['tasks_mean']:.1f}±{result['tasks_std']:.1f}        "
                      f"{result['miss_rate_mean']:.1f}%")

    print()


if __name__ == '__main__':
    main()
