#!/usr/bin/env python3
"""
Day10 Step 3: Reward 分量体检测试

验证 reward 分量记录功能是否正常工作
"""

import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

import argparse
import yaml
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

from agcoop.rl import AGCoopGymEnv
from agcoop.env.wrappers import FlattenObservation
from agcoop.rl.callbacks import DetailedEvalCallback


def load_config(config_path: str):
    """加载配置文件"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def make_env(config, seed=None):
    """创建环境"""
    def _init():
        env = AGCoopGymEnv(
            config=config,
            output_dir=None,
            enable_logging=False,
        )
        env = FlattenObservation(env)
        env = Monitor(env)
        # Gymnasium 环境使用 reset(seed=...) 而不是 seed()
        return env
    return _init


def main():
    parser = argparse.ArgumentParser(description='Day10 Step 3: Reward 分量体检测试')
    parser.add_argument('--config', type=str, default='configs/day10_ppo_train.yaml',
                        help='配置文件路径')
    parser.add_argument('--output_dir', type=str, default='outputs/day10_step3_test',
                        help='输出目录')
    parser.add_argument('--n_episodes', type=int, default=5,
                        help='评估 episode 数量')
    parser.add_argument('--seed', type=int, default=42,
                        help='随机种子')
    parser.add_argument('--eval_seed', type=int, default=10000,
                        help='评估种子起始值')
    args = parser.parse_args()

    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Day10 Step 3: Reward 分量体检测试")
    print("=" * 70)
    print()

    # 加载配置
    print(f"加载配置: {args.config}")
    config = load_config(args.config)
    print()

    # 创建评估环境
    print("创建评估环境...")
    eval_env = DummyVecEnv([make_env(config, seed=args.eval_seed)])
    print()

    # 创建随机策略模型（用于测试）
    print("创建随机策略模型...")
    model = PPO(
        'MlpPolicy',
        eval_env,
        verbose=0,
        seed=args.seed,
    )
    print()

    # 创建评估回调
    print("创建评估回调...")
    eval_callback = DetailedEvalCallback(
        eval_env,
        eval_freq=1,  # 立即评估
        n_eval_episodes=args.n_episodes,
        eval_seeds=list(range(args.eval_seed, args.eval_seed + args.n_episodes)),
        log_path=str(output_dir / 'eval_logs'),
        verbose=1,
    )
    eval_callback.init_callback(model)
    print()

    # 执行评估
    print("执行评估...")
    print()
    eval_callback._evaluate()

    # 读取评估结果
    print()
    print("=" * 70)
    print("验收检查")
    print("=" * 70)
    print()

    import json
    eval_details_path = output_dir / 'eval_logs' / 'eval_details_00000000.json'

    if not eval_details_path.exists():
        print(f"❌ 评估详细文件不存在: {eval_details_path}")
        return

    with open(eval_details_path, 'r') as f:
        eval_details = json.load(f)

    print(f"✅ 成功读取 {len(eval_details)} 个 episode 的评估结果")
    print()

    # 验收标准 1: reward 分量字段存在
    print("验收标准 1: Reward 分量字段存在")
    required_fields = [
        'reward_task',
        'reward_time',
        'reward_comm',
        'reward_deadline',
        'reward_mapf',
    ]

    all_fields_present = True
    for field in required_fields:
        if field in eval_details[0]:
            print(f"  ✅ {field}")
        else:
            print(f"  ❌ {field} (缺失)")
            all_fields_present = False
    print()

    if not all_fields_present:
        print("❌ 验收失败: 部分 reward 分量字段缺失")
        return

    # 验收标准 2: 惩罚项为非正
    print("验收标准 2: 惩罚项为非正（方向正确）")
    penalty_fields = [
        'reward_time',
        'reward_comm',
        'reward_deadline',
        'reward_mapf',
    ]

    all_penalties_correct = True
    for i, episode in enumerate(eval_details):
        print(f"  Episode {i+1} (seed={episode['seed']}):")
        for field in penalty_fields:
            value = episode[field]
            if value <= 0:
                print(f"    ✅ {field}: {value:.4f} (≤ 0)")
            else:
                print(f"    ❌ {field}: {value:.4f} (> 0, 应该 ≤ 0)")
                all_penalties_correct = False
    print()

    if not all_penalties_correct:
        print("⚠️  警告: 部分惩罚项为正值（可能是实现问题）")
        print()

    # 验收标准 3: Task reward 在完成任务时为正
    print("验收标准 3: Task reward 在完成任务时为正")
    for i, episode in enumerate(eval_details):
        task_reward = episode['reward_task']
        tasks_completed = episode['tasks_completed']
        print(f"  Episode {i+1} (seed={episode['seed']}):")
        print(f"    Tasks completed: {tasks_completed}")
        print(f"    Task reward: {task_reward:.4f}")

        if tasks_completed > 0:
            if task_reward > 0:
                print(f"    ✅ Task reward 为正（完成了任务）")
            else:
                print(f"    ⚠️  Task reward 非正（完成了任务但 reward ≤ 0）")
        else:
            if task_reward == 0:
                print(f"    ✅ Task reward 为 0（未完成任务）")
            else:
                print(f"    ⚠️  Task reward 非零（未完成任务但 reward ≠ 0）")
    print()

    # 验收标准 4: Episode 总 reward 不是恒定不变
    print("验收标准 4: Episode 总 reward 不是恒定不变")
    total_rewards = [episode['total_reward'] for episode in eval_details]
    unique_rewards = set(total_rewards)

    print(f"  总 reward 值: {total_rewards}")
    print(f"  唯一值数量: {len(unique_rewards)}")

    if len(unique_rewards) > 1:
        print(f"  ✅ Reward 有变化（learning signal 足够）")
    else:
        print(f"  ⚠️  Reward 恒定不变（learning signal 可能太弱）")
    print()

    # 打印 reward 分量统计
    print("=" * 70)
    print("Reward 分量统计")
    print("=" * 70)
    print()

    import numpy as np
    for field in required_fields:
        values = [episode[field] for episode in eval_details]
        mean_val = np.mean(values)
        std_val = np.std(values)
        min_val = np.min(values)
        max_val = np.max(values)

        print(f"{field}:")
        print(f"  Mean: {mean_val:.4f} ± {std_val:.4f}")
        print(f"  Range: [{min_val:.4f}, {max_val:.4f}]")
        print()

    # 验收总结
    print("=" * 70)
    print("验收总结")
    print("=" * 70)
    print()

    if all_fields_present:
        print("✅ 所有 reward 分量字段存在")
    else:
        print("❌ 部分 reward 分量字段缺失")

    if all_penalties_correct:
        print("✅ 所有惩罚项方向正确（≤ 0）")
    else:
        print("⚠️  部分惩罚项方向错误（> 0）")

    if len(unique_rewards) > 1:
        print("✅ Reward 有变化（learning signal 足够）")
    else:
        print("⚠️  Reward 恒定不变（learning signal 可能太弱）")

    print()
    print("=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == '__main__':
    main()
