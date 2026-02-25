#!/usr/bin/env python3
"""
Stage 3 高熵正则化微调脚本

基于已训练的 Stage 2 模型，使用更高的学习率和探索系数
在 Map_02 上进行微调，避免过拟合到训练种子。

核心改进：
1. 学习率：0.0002（适度微调，防止僵化）
2. 探索系数：0.015（高熵正则化，保持策略灵活性）
3. 训练步数：400k（早停策略，防止过拟合）
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import torch
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import CheckpointCallback, CallbackList
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from stable_baselines3.common.monitor import Monitor

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from agcoop.rl import AGCoopGymEnv
from agcoop.env.wrappers import FlattenObservation
from agcoop.rl.callbacks import DetailedEvalCallback
import yaml


def load_config(config_path: str):
    """加载配置文件"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def make_env(config, seed: int, rank: int = 0, map_path: str = None):
    """创建环境（无数据增强，分布对齐）"""
    def _init():
        env_config = config.copy()

        if map_path is not None:
            env_config['episode']['map_path'] = map_path

        # 分布对齐：固定任务参数
        env_config['tasks']['arrival_rate'] = 0.1
        env_config['tasks']['deadline_min'] = 25
        env_config['tasks']['deadline_max'] = 60

        env = AGCoopGymEnv(env_config)
        env = FlattenObservation(env)
        env = Monitor(env)
        env.reset(seed=seed + rank)

        return env

    return _init


def create_training_env(config, map_path: str, n_envs: int, seed: int):
    """创建训练环境"""
    if n_envs == 1:
        env = DummyVecEnv([make_env(config, seed, 0, map_path)])
    else:
        env = SubprocVecEnv([
            make_env(config, seed, i, map_path) for i in range(n_envs)
        ])
    return env


def main():
    parser = argparse.ArgumentParser(description='Stage 3 高熵正则化微调')
    parser.add_argument('--stage2_model', type=str, required=True,
                        help='Stage 2 模型路径')
    parser.add_argument('--config', type=str, default='configs/curriculum_learning.yaml',
                        help='配置文件路径')
    parser.add_argument('--n_envs', type=int, default=8,
                        help='并行环境数量')
    parser.add_argument('--seed', type=int, default=42,
                        help='训练随机种子')
    parser.add_argument('--eval_seed', type=int, default=10000,
                        help='评估随机种子')
    parser.add_argument('--device', type=str, default='auto',
                        help='训练设备 (cpu/cuda/auto)')
    parser.add_argument('--output_dir', type=str, default=None,
                        help='输出目录')

    # 核心超参数
    parser.add_argument('--learning_rate', type=float, default=0.0002,
                        help='学习率（默认 0.0002）')
    parser.add_argument('--ent_coef', type=float, default=0.015,
                        help='探索系数（默认 0.015，高熵正则化）')
    parser.add_argument('--timesteps', type=int, default=400000,
                        help='训练步数（默认 400k，早停策略）')

    args = parser.parse_args()

    print("=" * 70)
    print("Stage 3: 高熵正则化微调")
    print("=" * 70)
    print(f"Stage 2 模型: {args.stage2_model}")
    print(f"配置文件: {args.config}")
    print()
    print("核心超参数:")
    print(f"  学习率: {args.learning_rate} (适度微调)")
    print(f"  探索系数: {args.ent_coef} (高熵正则化)")
    print(f"  训练步数: {args.timesteps:,} (早停策略)")
    print(f"  并行环境: {args.n_envs}")
    print(f"  设备: {args.device}")
    print()

    # 加载配置
    config = load_config(args.config)

    # 创建输出目录
    if args.output_dir is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(f'outputs/stage3_regularized/run_{timestamp}')
    else:
        output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    tb_dir = output_dir / 'tb'
    checkpoint_dir = output_dir / 'checkpoints'
    checkpoint_dir.mkdir(exist_ok=True)

    print(f"输出目录: {output_dir}")
    print()

    # 创建 Map_02 训练环境
    print("创建训练环境...")
    train_env = create_training_env(
        config,
        'maps/map_02.map',
        args.n_envs,
        args.seed
    )
    print(f"  训练环境: {args.n_envs} 个并行环境 (Map_02)")
    print()

    # 创建评估环境
    print("创建评估环境...")
    eval_env = create_training_env(
        config,
        'maps/map_02.map',
        1,
        args.eval_seed
    )
    print(f"  评估环境: 1 个环境 (seed={args.eval_seed})")
    print()

    # 加载 Stage 2 模型并注入新超参数
    print(f"加载 Stage 2 模型: {args.stage2_model}")
    print()
    print("注入新超参数（高熵正则化）:")
    print(f"  learning_rate: {args.learning_rate}")
    print(f"  ent_coef: {args.ent_coef}")
    print()

    custom_objects = {
        "learning_rate": args.learning_rate,
        "ent_coef": args.ent_coef,
    }

    model = PPO.load(
        args.stage2_model,
        env=train_env,
        device=args.device,
        custom_objects=custom_objects
    )

    # 重新设置 tensorboard_log
    model.tensorboard_log = str(tb_dir)

    print("✓ 模型加载成功")
    print("✓ 超参数已更新")
    print()

    # 创建回调
    print("创建训练回调...")

    checkpoint_callback = CheckpointCallback(
        save_freq=50000 // args.n_envs,
        save_path=str(checkpoint_dir),
        name_prefix='stage3_regularized',
        save_replay_buffer=False,
        save_vecnormalize=False,
    )

    eval_callback = DetailedEvalCallback(
        eval_env,
        eval_freq=25000 // args.n_envs,
        n_eval_episodes=10,
        eval_seeds=list(range(args.eval_seed, args.eval_seed + 10)),
        log_path=str(output_dir / 'eval_logs'),
        verbose=1,
    )

    callback = CallbackList([checkpoint_callback, eval_callback])

    print(f"  Checkpoint 频率: 每 50,000 步")
    print(f"  评估频率: 每 25,000 步")
    print()

    # 保存训练配置
    training_config = {
        'stage2_model': args.stage2_model,
        'map': 'maps/map_02.map',
        'learning_rate': args.learning_rate,
        'ent_coef': args.ent_coef,
        'timesteps': args.timesteps,
        'n_envs': args.n_envs,
        'seed': args.seed,
        'eval_seed': args.eval_seed,
        'strategy': 'high_entropy_regularization',
        'description': '高熵正则化微调，防止过拟合到训练种子'
    }

    config_path = output_dir / 'training_config.json'
    with open(config_path, 'w') as f:
        json.dump(training_config, f, indent=2)
    print(f"训练配置已保存: {config_path}")
    print()

    # 开始训练
    print("=" * 70)
    print("开始训练 Stage 3 (高熵正则化)")
    print("=" * 70)
    print()
    print("预期行为:")
    print("  - 策略熵保持在较高水平 (-3.8 到 -3.5)")
    print("  - 训练奖励稳定在 40-45 分")
    print("  - 避免过拟合到训练种子")
    print()

    try:
        model.learn(
            total_timesteps=args.timesteps,
            callback=callback,
            log_interval=1,
            tb_log_name='stage3_high_entropy',
            reset_num_timesteps=False,
        )

        print()
        print("=" * 70)
        print("训练完成")
        print("=" * 70)

        # 保存最终模型
        final_model_path = output_dir / 'ppo_stage3_regularized_final.zip'
        model.save(final_model_path)
        print(f"最终模型已保存: {final_model_path}")

        # 保存训练摘要
        summary = {
            'stage2_model': args.stage2_model,
            'training_config': training_config,
            'output_dir': str(output_dir),
            'final_model': str(final_model_path),
            'tensorboard_log': str(tb_dir),
        }

        summary_path = output_dir / 'training_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"训练摘要已保存: {summary_path}")
        print()
        print("下一步：评估模型")
        print(f"  python scripts/evaluate_curriculum.py \\")
        print(f"    --model {final_model_path} \\")
        print(f"    --map maps/map_02.map \\")
        print(f"    --test_seeds 20000-20009")
        print()

    except KeyboardInterrupt:
        print()
        print("训练被用户中断")
        interrupted_model_path = checkpoint_dir / 'stage3_regularized_interrupted.zip'
        model.save(interrupted_model_path)
        print(f"中断模型已保存: {interrupted_model_path}")

    except Exception as e:
        print()
        print(f"训练出错: {e}")
        import traceback
        traceback.print_exc()

        error_model_path = checkpoint_dir / 'stage3_regularized_error.zip'
        model.save(error_model_path)
        print(f"出错模型已保存: {error_model_path}")
        raise

    finally:
        train_env.close()
        eval_env.close()


if __name__ == '__main__':
    main()
