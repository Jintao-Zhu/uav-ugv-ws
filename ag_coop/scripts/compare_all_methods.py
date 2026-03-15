#!/usr/bin/env python3
"""
综合对比评估 - 所有方法一次性对比

对比方法：
1. PPO V4 (你的改进)
2. Vanilla PPO (消融对照)
3. DQN (架构对照)
4. Dynamic-Heuristic (最强规则)
5. Static-Center (经典基站)
6. Tethered-Greedy (消融基准)
7. Pure-Random (下限)
"""

import sys
from pathlib import Path
import yaml
import numpy as np
import json
from datetime import datetime

from stable_baselines3 import PPO, DQN

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv
from agcoop.policies.baseline_policies import (
    DynamicHeuristicPolicy, StaticCenterPolicy,
    TetheredGreedyPolicy, PureRandomPolicy
)


def evaluate(policy, env, n_episodes=20, name="Policy"):
    """快速评估"""
    rewards, tasks, outages = [], [], []

    for _ in range(n_episodes):
        obs = env.reset()
        done = False
        ep_reward = 0

        while not done:
            action, _ = policy.predict(obs, deterministic=True)
            obs, reward, done, info = env.step(action)
            ep_reward += reward

        rewards.append(ep_reward)
        tasks.append(info.get('tasks_completed', 0))
        outages.append(info.get('outage_steps', 0))

    return {
        'name': name,
        'reward': f"{np.mean(rewards):.2f}±{np.std(rewards):.2f}",
        'tasks': f"{np.mean(tasks):.2f}±{np.std(tasks):.2f}",
        'outage': f"{np.mean(outages):.2f}±{np.std(outages):.2f}",
        'raw': {'rewards': rewards, 'tasks': tasks, 'outages': outages}
    }


def main():
    print("\n🚀 综合对比评估")

    # 加载配置
    config_path = project_root / 'configs' / 'curriculum_learning.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    config['episode']['map_path'] = "maps/map_02.map"
    config['episode']['horizon_steps'] = 500

    env = AGCoopEnv(config, method='rl', planner='PIBT')

    results = []

    # 1. PPO V4
    try:
        model = PPO.load(str(project_root / "outputs/ppo_v4_golden_ratio_map02/best_model/best_model.zip"))
        results.append(evaluate(model, env, 20, "PPO V4 (Ours)"))
    except:
        print("⚠️  PPO V4 未找到")

    # 2. Vanilla PPO
    try:
        model = PPO.load(str(project_root / "outputs/vanilla_ppo_baseline_map02/best_model/best_model.zip"))
        results.append(evaluate(model, env, 20, "Vanilla PPO"))
    except:
        print("⚠️  Vanilla PPO 未找到")

    # 3. DQN
    try:
        model = DQN.load(str(project_root / "outputs/dqn_baseline_map02/best_model/best_model.zip"))
        results.append(evaluate(model, env, 20, "DQN"))
    except:
        print("⚠️  DQN 未找到")

    # 4-7. Baselines
    results.append(evaluate(DynamicHeuristicPolicy(env), env, 20, "Dynamic-Heuristic"))
    results.append(evaluate(StaticCenterPolicy(env), env, 20, "Static-Center"))
    results.append(evaluate(TetheredGreedyPolicy(env), env, 20, "Tethered-Greedy"))
    results.append(evaluate(PureRandomPolicy(env), env, 20, "Pure-Random"))

    # 打印表格
    print("\n" + "="*80)
    print(f"{'方法':<25} {'平均奖励':<20} {'任务完成':<20} {'通信中断':<15}")
    print("="*80)
    for r in results:
        print(f"{r['name']:<25} {r['reward']:<20} {r['tasks']:<20} {r['outage']:<15}")
    print("="*80)

    # 保存
    output_dir = project_root / "outputs" / "comparisons"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(output_dir / f"comparison_{timestamp}.json", 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ 结果已保存")
    env.close()


if __name__ == "__main__":
    main()
