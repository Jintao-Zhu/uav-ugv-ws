#!/usr/bin/env python3
"""
升级版Baseline评估脚本 - 智能任务分配

对比：
1. Tethered-Smart: 智能任务分配 + UAV绑定在UGV_0
2. Static-Center-Smart: 智能任务分配 + UAV静态中心部署
3. Dynamic-Heuristic-Smart: 智能任务分配 + UAV动态质心跟随
4. Pure-Random: 纯随机（对照组）

目标：证明智能任务分配能够击败Pure-Random
"""

import sys
from pathlib import Path
import yaml
import json
import numpy as np
from tqdm import tqdm

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv
from agcoop.policies.smart_baseline_policies import (
    TetheredSmartPolicy,
    StaticCenterSmartPolicy,
    DynamicHeuristicSmartPolicy,
    PureRandomPolicy
)


def load_config(config_path, map_path=None):
    """加载配置文件"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    if map_path:
        config['episode']['map_path'] = map_path

    return config


def evaluate_policy(policy, env, test_seeds, max_steps=500):
    """评估单个策略"""
    episodes = []

    for seed in tqdm(test_seeds, desc=f"Evaluating {policy.policy_name}"):
        # 设置环境种子
        env.seed = seed
        obs = env.reset()
        done = False
        step_count = 0

        # 累积奖励
        total_reward = 0.0
        reward_task = 0.0
        reward_time = 0.0
        reward_comm = 0.0
        reward_deadline = 0.0
        reward_mapf = 0.0

        while not done and step_count < max_steps:
            # 策略决策
            action, _ = policy.predict(obs)

            # 环境交互
            obs, reward, done, info = env.step(action)

            # 累积奖励
            total_reward += reward
            if 'reward_components' in info:
                rc = info['reward_components']
                reward_task += rc.get('r_task', 0.0)
                reward_time += rc.get('r_time', 0.0)
                reward_comm += rc.get('r_comm', 0.0)
                reward_deadline += rc.get('r_deadline', 0.0)
                reward_mapf += rc.get('r_mapf', 0.0)

            step_count += 1

        # 从最后的info中获取累积统计量
        tasks_completed = info.get('tasks_completed', 0)
        deadline_miss = info.get('deadline_miss', 0)

        # 记录episode结果
        episode_result = {
            'seed': seed,
            'steps': step_count,
            'total_reward': total_reward,
            'mean_reward': total_reward / max(1, step_count),
            'reward_task': reward_task,
            'reward_time': reward_time,
            'reward_comm': reward_comm,
            'reward_deadline': reward_deadline,
            'reward_mapf': reward_mapf,
            'tasks_completed': tasks_completed,
            'deadline_miss': deadline_miss
        }
        episodes.append(episode_result)

    # 计算统计数据
    stats = compute_stats(episodes)

    return {
        'policy_name': policy.policy_name,
        'episodes': episodes,
        'stats': stats
    }


def compute_stats(episodes):
    """计算统计指标"""
    metrics = [
        'total_reward', 'mean_reward', 'reward_task', 'reward_time',
        'reward_comm', 'reward_deadline', 'reward_mapf',
        'tasks_completed', 'deadline_miss'
    ]

    stats = {}
    for metric in metrics:
        values = [ep[metric] for ep in episodes]
        stats[f'mean_{metric}'] = float(np.mean(values))
        stats[f'std_{metric}'] = float(np.std(values))
        stats[f'min_{metric}'] = float(np.min(values))
        stats[f'max_{metric}'] = float(np.max(values))

    return stats


def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description='评估升级版智能Baseline策略')
    parser.add_argument('--map', type=str, default='maps/map_02.map',
                        help='地图文件路径 (默认: maps/map_02.map)')
    parser.add_argument('--output-suffix', type=str, default='_smart',
                        help='输出目录后缀 (默认: _smart)')
    args = parser.parse_args()

    print("\n" + "="*70)
    print("升级版Baseline评估 - 智能任务分配 (EDF)")
    print(f"地图: {args.map}")
    print("="*70)

    # 配置路径
    config_path = project_root / 'configs' / 'curriculum_learning.yaml'
    output_dir = project_root / 'outputs' / f'new_baseline_evaluation{args.output_suffix}'
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载配置
    print("\n1. 加载配置...")
    config = load_config(config_path, map_path=args.map)
    config['episode']['horizon_steps'] = 500

    # 创建环境
    print("2. 创建环境...")
    env = AGCoopEnv(config, method='rl', planner='PIBT')

    # 初始化环境
    print("3. 初始化环境（加载地图）...")
    _ = env.reset()

    # 测试种子
    test_seeds = list(range(20000, 20010))
    print(f"4. 测试集: seeds {test_seeds[0]}-{test_seeds[-1]} (共{len(test_seeds)}个)")

    # 初始化4个升级版baseline策略
    policies = [
        TetheredSmartPolicy(env),
        StaticCenterSmartPolicy(env),
        DynamicHeuristicSmartPolicy(env, battery_threshold=0.25),
        PureRandomPolicy(env)
    ]

    print(f"\n5. 开始评估 {len(policies)} 个升级版baseline策略...")
    print("-" * 70)

    # 评估每个策略
    all_results = {}
    for policy in policies:
        print(f"\n正在评估: {policy.policy_name}")
        results = evaluate_policy(policy, env, test_seeds, max_steps=500)
        all_results[policy.policy_name] = results

        # 保存单个策略结果
        output_file = output_dir / f"{policy.policy_name.lower().replace('-', '_')}_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        # 打印关键指标
        stats = results['stats']
        print(f"  ✓ 平均完成任务: {stats['mean_tasks_completed']:.2f} ± {stats['std_tasks_completed']:.2f}")
        print(f"  ✓ 平均总奖励: {stats['mean_total_reward']:.2f} ± {stats['std_total_reward']:.2f}")
        print(f"  ✓ 平均deadline miss: {stats['mean_deadline_miss']:.2f} ± {stats['std_deadline_miss']:.2f}")
        print(f"  ✓ 结果已保存: {output_file}")

    # 生成对比摘要
    print("\n" + "="*70)
    print("6. 生成对比摘要...")
    summary = {
        'test_seeds': test_seeds,
        'max_steps': 500,
        'policies': {}
    }

    for policy_name, results in all_results.items():
        summary['policies'][policy_name] = {
            'mean_tasks_completed': results['stats']['mean_tasks_completed'],
            'std_tasks_completed': results['stats']['std_tasks_completed'],
            'mean_total_reward': results['stats']['mean_total_reward'],
            'std_total_reward': results['stats']['std_total_reward'],
            'mean_deadline_miss': results['stats']['mean_deadline_miss'],
            'std_deadline_miss': results['stats']['std_deadline_miss']
        }

    # 保存摘要
    summary_file = output_dir / 'summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"✓ 对比摘要已保存: {summary_file}")

    # 打印最终对比表格
    print("\n" + "="*70)
    print("7. 最终对比结果 (升级版 - 智能任务分配)")
    print("="*70)
    print(f"{'策略名称':<30} {'完成任务':<20} {'总奖励':<20} {'Deadline Miss':<20}")
    print("-" * 70)

    # 按完成任务数排序
    sorted_policies = sorted(
        summary['policies'].items(),
        key=lambda x: x[1]['mean_tasks_completed'],
        reverse=True
    )

    for policy_name, stats in sorted_policies:
        tasks = f"{stats['mean_tasks_completed']:.2f} ± {stats['std_tasks_completed']:.2f}"
        reward = f"{stats['mean_total_reward']:.2f} ± {stats['std_total_reward']:.2f}"
        deadline = f"{stats['mean_deadline_miss']:.2f} ± {stats['std_deadline_miss']:.2f}"
        print(f"{policy_name:<30} {tasks:<20} {reward:<20} {deadline:<20}")

    print("\n" + "="*70)
    print("关键发现:")
    print("  - 如果智能策略超越Pure-Random，说明EDF任务分配有效")
    print("  - 如果Dynamic-Heuristic-Smart排名第一，说明人类规则达到极限")
    print("  - PPO的目标：超越Dynamic-Heuristic-Smart")
    print("="*70)
    print(f"\n✓ 所有升级版baseline评估完成！")
    print(f"✓ 结果保存在: {output_dir}")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ 评估失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
