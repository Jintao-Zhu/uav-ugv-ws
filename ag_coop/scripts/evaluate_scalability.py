#!/usr/bin/env python3
"""
可扩展性评估 - 系统负载压力测试

学术目的：证明算法在不同任务负载下的稳定性和可扩展性
测试维度：
1. 低负载 (20 tasks): 验证基础性能
2. 中负载 (40 tasks): 标准工况
3. 高负载 (80 tasks): 极限压力测试

对比对象：
- PPO V4 (你的改进模型)
- Vanilla PPO
- Dynamic-Heuristic (最强baseline)
"""

import sys
import os
from pathlib import Path
import yaml
import numpy as np
import json
from datetime import datetime

from stable_baselines3 import PPO

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv
from agcoop.policies.baseline_policies import DynamicHeuristicPolicy


class PolicyWrapper:
    """包装器：使 baseline 策略兼容 SB3 的 predict() 接口"""
    def __init__(self, policy):
        self.policy = policy

    def predict(self, obs, deterministic=True):
        # baseline 策略直接返回 action，我们需要返回 (action, state)
        action = self.policy.get_action(obs)
        return action, None


def load_config(map_path, n_tasks):
    """加载配置并设置任务数量"""
    config_path = project_root / 'configs' / 'curriculum_learning.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['episode']['map_path'] = map_path
    config['episode']['horizon_steps'] = 500

    # 修改任务生成参数以控制任务数量
    # 通过调整 arrival_rate 来控制任务数量
    if 'tasks' in config:
        # 原始 arrival_rate = 0.1 生成约 40 个任务
        # 调整比例来达到目标任务数
        original_tasks = 40
        scale_factor = n_tasks / original_tasks

        # 调整到达率
        original_rate = config['tasks'].get('arrival_rate', 0.1)
        config['tasks']['arrival_rate'] = min(1.0, original_rate * scale_factor)

        # 调整最大活跃任务数
        config['tasks']['max_active'] = max(20, int(n_tasks * 1.2))

    return config


def evaluate_policy(policy, env, n_episodes=10, policy_name="Policy"):
    """评估策略性能"""
    print(f"\n评估 {policy_name}...")

    episode_rewards = []
    episode_tasks = []
    episode_outages = []
    episode_lengths = []

    for ep in range(n_episodes):
        # 处理 Gym API：reset() 返回 (obs, info)
        reset_result = env.reset()
        if isinstance(reset_result, tuple):
            obs, info = reset_result
        else:
            obs = reset_result

        done = False
        episode_reward = 0
        step_count = 0

        while not done:
            action, _ = policy.predict(obs, deterministic=True)

            # 处理 Gym API：step() 返回 (obs, reward, terminated, truncated, info)
            step_result = env.step(action)
            if len(step_result) == 5:
                obs, reward, terminated, truncated, info = step_result
                done = terminated or truncated
            else:
                obs, reward, done, info = step_result

            episode_reward += reward
            step_count += 1

        # 收集统计信息
        episode_rewards.append(episode_reward)
        episode_tasks.append(info.get('tasks_completed', 0))
        episode_outages.append(info.get('outage_steps', 0))
        episode_lengths.append(step_count)

        print(f"  Episode {ep+1}/{n_episodes}: "
              f"Reward={episode_reward:.2f}, "
              f"Tasks={info.get('tasks_completed', 0)}, "
              f"Outage={info.get('outage_steps', 0)}")

    # 计算统计量
    results = {
        'policy_name': policy_name,
        'mean_reward': float(np.mean(episode_rewards)),
        'std_reward': float(np.std(episode_rewards)),
        'mean_tasks': float(np.mean(episode_tasks)),
        'std_tasks': float(np.std(episode_tasks)),
        'mean_outage': float(np.mean(episode_outages)),
        'std_outage': float(np.std(episode_outages)),
        'mean_length': float(np.mean(episode_lengths)),
        'episodes': episode_rewards
    }

    return results


def run_scalability_test(model_paths, map_path="maps/map_02.map", n_episodes=10):
    """运行可扩展性测试"""

    print("\n" + "=" * 70)
    print("🔬 系统负载可扩展性测试")
    print("=" * 70)

    # 测试负载配置
    load_configs = [
        {'name': 'Low Load', 'n_tasks': 20, 'description': '低负载 (20 tasks)'},
        {'name': 'Medium Load', 'n_tasks': 40, 'description': '中负载 (40 tasks)'},
        {'name': 'High Load', 'n_tasks': 80, 'description': '高负载 (80 tasks)'},
    ]

    all_results = {}

    for load_cfg in load_configs:
        load_name = load_cfg['name']
        n_tasks = load_cfg['n_tasks']

        print(f"\n{'='*70}")
        print(f"测试场景: {load_cfg['description']}")
        print(f"{'='*70}")

        # 创建环境
        config = load_config(map_path, n_tasks)
        env = AGCoopEnv(config, method='rl', planner='PIBT')

        load_results = {}

        # 1. 评估 PPO V4
        if 'ppo_v4' in model_paths and model_paths['ppo_v4']:
            try:
                # 尝试加载模型，处理 numpy 版本兼容性问题
                import numpy as np
                # 添加兼容性别名
                if not hasattr(np, '_core'):
                    np._core = np.core

                model_v4 = PPO.load(model_paths['ppo_v4'])
                results = evaluate_policy(model_v4, env, n_episodes, "PPO V4")
                load_results['PPO_V4'] = results
            except Exception as e:
                print(f"⚠️  PPO V4 加载失败: {e}")

        # 2. 评估 Vanilla PPO
        if 'vanilla_ppo' in model_paths and model_paths['vanilla_ppo']:
            try:
                model_vanilla = PPO.load(model_paths['vanilla_ppo'])
                results = evaluate_policy(model_vanilla, env, n_episodes, "Vanilla PPO")
                load_results['Vanilla_PPO'] = results
            except Exception as e:
                print(f"⚠️  Vanilla PPO 加载失败: {e}")

        # 3. 评估 DQN
        if 'dqn' in model_paths and model_paths['dqn']:
            try:
                from stable_baselines3 import DQN
                model_dqn = DQN.load(model_paths['dqn'])
                results = evaluate_policy(model_dqn, env, n_episodes, "DQN")
                load_results['DQN'] = results
            except Exception as e:
                print(f"⚠️  DQN 加载失败: {e}")

        # 4. 评估 Dynamic-Heuristic
        try:
            policy_heur = DynamicHeuristicPolicy(env)
            results = evaluate_policy(policy_heur, env, n_episodes, "Dynamic-Heuristic")
            load_results['Dynamic_Heuristic'] = results
        except Exception as e:
            print(f"⚠️  Dynamic-Heuristic 评估失败: {e}")
            import traceback
            traceback.print_exc()

        all_results[load_name] = load_results
        env.close()

    return all_results


def print_comparison_table(results):
    """打印对比表格"""
    print("\n" + "=" * 70)
    print("📊 可扩展性测试结果汇总")
    print("=" * 70)

    for load_name, load_results in results.items():
        print(f"\n{load_name}:")
        print("-" * 70)
        print(f"{'策略':<20} {'平均奖励':<15} {'任务完成':<15} {'通信中断':<15}")
        print("-" * 70)

        for policy_name, policy_results in load_results.items():
            print(f"{policy_name:<20} "
                  f"{policy_results['mean_reward']:>7.2f}±{policy_results['std_reward']:<5.2f} "
                  f"{policy_results['mean_tasks']:>7.2f}±{policy_results['std_tasks']:<5.2f} "
                  f"{policy_results['mean_outage']:>7.2f}±{policy_results['std_outage']:<5.2f}")


def save_results(results, output_dir):
    """保存结果到JSON"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"scalability_test_{timestamp}.json"

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n结果已保存到: {output_file}")


def main():
    """主函数"""

    # 配置模型路径
    model_paths = {
        'ppo_v4': str(project_root / "outputs" / "ppo_v4_golden_ratio_map02" / "best_model" / "best_model.zip"),
        'vanilla_ppo': str(project_root / "outputs" / "vanilla_ppo_baseline_map02" / "best_model" / "best_model.zip"),
        'dqn': str(project_root / "outputs" / "dqn_baseline_map02" / "best_model" / "best_model.zip"),
    }

    # 检查模型是否存在
    print("\n检查模型文件...")
    for name, path in model_paths.items():
        if Path(path).exists():
            print(f"  ✓ {name}: {path}")
        else:
            print(f"  ✗ {name}: 未找到 (将跳过)")
            model_paths[name] = None

    # 运行测试
    results = run_scalability_test(
        model_paths=model_paths,
        map_path="maps/map_02.map",
        n_episodes=10
    )

    # 打印结果
    print_comparison_table(results)

    # 保存结果
    output_dir = project_root / "outputs" / "scalability_tests"
    save_results(results, output_dir)

    print("\n" + "=" * 70)
    print("✅ 可扩展性测试完成")
    print("=" * 70)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
