#!/usr/bin/env python3
"""
Day10 Step 1: PPO Training Script

使用 Stable-Baselines3 训练 PPO 策略
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import numpy as np
import yaml
import torch  # 添加torch导入
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import (
    CheckpointCallback,
    CallbackList,
)
from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv
from stable_baselines3.common.monitor import Monitor

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from agcoop.rl import AGCoopGymEnv
from agcoop.env.wrappers import FlattenObservation
from agcoop.rl.callbacks import DetailedEvalCallback


def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def make_env(config: Dict[str, Any], seed: int, rank: int = 0, map_list: list = None):
    """
    创建环境的工厂函数（用于并行环境）

    Args:
        config: 配置字典
        seed: 随机种子
        rank: 环境编号（用于并行环境）
        map_list: 地图列表（用于多地图训练）
    """
    def _init():
        # 复制配置
        env_config = config.copy()

        # 1. 多地图训练：确定性地选择地图
        if map_list is not None and len(map_list) > 0:
            # 使用 rank 和 seed 来确定性地选择地图（保证可复现）
            map_idx = (seed + rank) % len(map_list)
            env_config['episode']['map_path'] = map_list[map_idx]

        # 2. 数据增强：随机化任务参数
        import random
        rng = random.Random(seed + rank)

        # 随机arrival_rate：从[0.08, 0.10, 0.12]中选择
        env_config['tasks']['arrival_rate'] = rng.choice([0.08, 0.10, 0.12])

        # 随机deadline范围：从3种配置中选择
        deadline_configs = [
            (20, 50),  # 紧张
            (25, 60),  # 标准
            (30, 70),  # 宽松
        ]
        deadline_min, deadline_max = rng.choice(deadline_configs)
        env_config['tasks']['deadline_min'] = deadline_min
        env_config['tasks']['deadline_max'] = deadline_max

        # 创建基础环境
        env = AGCoopGymEnv(env_config)

        # 应用 FlattenObservation wrapper
        env = FlattenObservation(env)

        # 应用 Monitor wrapper（记录 episode 统计）
        env = Monitor(env)

        # 设置种子
        env.reset(seed=seed + rank)

        return env

    return _init


def save_config(config: Dict[str, Any], output_dir: Path):
    """保存配置文件"""
    config_path = output_dir / 'config_resolved.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    # 同时保存 JSON 格式
    config_json_path = output_dir / 'config_resolved.json'
    with open(config_json_path, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"配置已保存到: {config_path}")


def main():
    parser = argparse.ArgumentParser(description='Day10 PPO Training')
    parser.add_argument('--config', type=str, default='configs/day10_ppo_train.yaml',
                        help='配置文件路径')
    parser.add_argument('--total_timesteps', type=int, default=None,
                        help='总训练步数（覆盖配置文件）')
    parser.add_argument('--n_envs', type=int, default=None,
                        help='并行环境数量（覆盖配置文件）')
    parser.add_argument('--seed', type=int, default=42,
                        help='训练随机种子')
    parser.add_argument('--eval_seed', type=int, default=10000,
                        help='评估随机种子')
    parser.add_argument('--output_dir', type=str, default=None,
                        help='输出目录（默认：outputs/day10_ppo/<timestamp>）')
    parser.add_argument('--device', type=str, default='auto',
                        help='训练设备 (cpu/cuda/auto)')
    parser.add_argument('--resume', type=str, default=None,
                        help='从 checkpoint 恢复训练（提供 .zip 文件路径）')

    args = parser.parse_args()

    # 加载配置
    print("=" * 70)
    print("Day10 Step 1: PPO Training")
    print("=" * 70)
    print(f"配置文件: {args.config}")
    print()

    config = load_config(args.config)

    # 覆盖配置（如果命令行提供）
    training_config = config.get('training', {})
    if args.total_timesteps is not None:
        training_config['total_timesteps'] = args.total_timesteps
    if args.n_envs is not None:
        training_config['n_envs'] = args.n_envs

    # 提取训练参数
    total_timesteps = training_config.get('total_timesteps', 1000000)
    n_envs = training_config.get('n_envs', 4)
    batch_size = training_config.get('batch_size', 256)
    n_epochs = training_config.get('n_epochs', 10)
    learning_rate = training_config.get('learning_rate', 3e-4)
    gamma = training_config.get('gamma', 0.99)
    gae_lambda = training_config.get('gae_lambda', 0.95)
    clip_range = training_config.get('clip_range', 0.2)
    ent_coef = training_config.get('ent_coef', 0.01)
    vf_coef = training_config.get('vf_coef', 0.5)
    max_grad_norm = training_config.get('max_grad_norm', 0.5)
    save_freq = training_config.get('save_freq', 50000)
    eval_freq = training_config.get('eval_freq', 25000)
    eval_episodes = training_config.get('eval_episodes', 10)

    # 计算 n_steps（如果配置中没有提供）
    # n_steps 是每个环境收集的步数，PPO 要求 batch_size = n_steps * n_envs
    n_steps = training_config.get('n_steps', batch_size // n_envs)

    # 将实际使用的 n_steps 写回配置（用于保存）
    training_config['n_steps'] = n_steps

    print(f"训练参数:")
    print(f"  Total timesteps: {total_timesteps:,}")
    print(f"  Parallel envs: {n_envs}")
    print(f"  Batch size: {batch_size}")
    print(f"  n_steps (per env): {n_steps}")
    print(f"  n_epochs: {n_epochs}")
    print(f"  Learning rate: {learning_rate}")
    print(f"  Training seed: {args.seed}")
    print(f"  Eval seed: {args.eval_seed}")
    print(f"  Device: {args.device}")
    print()

    # 创建输出目录
    if args.output_dir is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(f'outputs/day10_ppo/run_{timestamp}')
    else:
        output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    tb_dir = output_dir / 'tb'
    checkpoint_dir = output_dir / 'checkpoints'
    checkpoint_dir.mkdir(exist_ok=True)

    print(f"输出目录: {output_dir}")
    print()

    # 保存配置
    save_config(config, output_dir)

    # 获取地图列表（用于多地图训练）
    map_list = training_config.get('maps', None)
    if map_list is not None and len(map_list) > 1:
        print(f"多地图训练模式: {len(map_list)} 张地图")
        for i, map_path in enumerate(map_list):
            print(f"  地图 {i+1}: {map_path}")
        print()
    elif map_list is not None and len(map_list) == 1:
        print(f"单地图训练模式: {map_list[0]}")
        print()
    else:
        print(f"单地图训练模式: {config['episode']['map_path']}")
        print()

    # 创建训练环境（并行）
    print("创建训练环境...")
    if n_envs == 1:
        # 单环境
        train_env = DummyVecEnv([make_env(config, args.seed, 0, map_list)])
    else:
        # 多环境（使用 SubprocVecEnv 实现真正的并行）
        train_env = SubprocVecEnv([
            make_env(config, args.seed, i, map_list) for i in range(n_envs)
        ])

    print(f"  训练环境: {n_envs} 个并行环境")
    print()

    # 创建评估环境（单个，使用第一张地图或配置中的地图）
    print("创建评估环境...")
    eval_map_list = [map_list[0]] if map_list is not None and len(map_list) > 0 else None
    eval_env = DummyVecEnv([make_env(config, args.eval_seed, 0, eval_map_list)])
    if eval_map_list:
        print(f"  评估环境: 1 个环境 (seed={args.eval_seed}, map={eval_map_list[0]})")
    else:
        print(f"  评估环境: 1 个环境 (seed={args.eval_seed})")
    print()

    # 创建或加载 PPO 模型
    if args.resume is not None:
        print(f"从 checkpoint 恢复训练: {args.resume}")
        model = PPO.load(
            args.resume,
            env=train_env,
            device=args.device,
            tensorboard_log=str(tb_dir),
        )
        print("  模型加载成功")
    else:
        print("创建 PPO 模型...")

        # 定义更大的网络架构
        policy_kwargs = dict(
            net_arch=[128, 128, 64],  # 增加网络深度和宽度
            activation_fn=torch.nn.ReLU,
        )

        model = PPO(
            policy='MlpPolicy',
            env=train_env,
            policy_kwargs=policy_kwargs,
            learning_rate=learning_rate,
            n_steps=n_steps,  # 使用计算好的 n_steps
            batch_size=batch_size,
            n_epochs=n_epochs,
            gamma=gamma,
            gae_lambda=gae_lambda,
            clip_range=clip_range,
            ent_coef=ent_coef,
            vf_coef=vf_coef,
            max_grad_norm=max_grad_norm,
            verbose=1,
            device=args.device,
            tensorboard_log=str(tb_dir),
            seed=args.seed,
        )
        print("  模型创建成功")

    print()
    print("模型架构:")
    print(model.policy)
    print()

    # 创建回调
    print("创建训练回调...")

    # 1. Checkpoint 回调（定期保存）
    checkpoint_callback = CheckpointCallback(
        save_freq=save_freq // n_envs,  # 每个环境的步数
        save_path=str(checkpoint_dir),
        name_prefix='ppo_model',
        save_replay_buffer=False,
        save_vecnormalize=False,
    )

    # 2. 评估回调（定期评估 + 保存最佳模型）
    eval_callback = DetailedEvalCallback(
        eval_env,
        eval_freq=eval_freq // n_envs,  # 每个环境的步数
        n_eval_episodes=eval_episodes,
        eval_seeds=list(range(args.eval_seed, args.eval_seed + eval_episodes)),
        log_path=str(output_dir / 'eval_logs'),
        verbose=1,
    )

    # 组合回调
    callback = CallbackList([checkpoint_callback, eval_callback])

    print(f"  Checkpoint 频率: 每 {save_freq:,} 步")
    print(f"  评估频率: 每 {eval_freq:,} 步 ({eval_episodes} episodes, seeds={args.eval_seed}-{args.eval_seed + eval_episodes - 1})")
    print()

    # 开始训练
    print("=" * 70)
    print("开始训练")
    print("=" * 70)
    print()

    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=callback,
            log_interval=10,  # 每 10 次更新打印一次
            tb_log_name='ppo',
            reset_num_timesteps=False if args.resume else True,
        )

        print()
        print("=" * 70)
        print("训练完成")
        print("=" * 70)

        # 保存最终模型
        final_model_path = checkpoint_dir / 'ppo_model_final.zip'
        model.save(final_model_path)
        print(f"最终模型已保存: {final_model_path}")

        # 保存训练摘要
        summary = {
            'config': args.config,
            'total_timesteps': total_timesteps,
            'n_envs': n_envs,
            'train_seed': args.seed,
            'eval_seed': args.eval_seed,
            'output_dir': str(output_dir),
            'final_model': str(final_model_path),
            'best_model': str(checkpoint_dir / 'best_model.zip'),
            'tensorboard_log': str(tb_dir),
        }

        summary_path = output_dir / 'training_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        print(f"训练摘要已保存: {summary_path}")
        print()
        print("输出文件:")
        print(f"  配置: {output_dir / 'config_resolved.yaml'}")
        print(f"  TensorBoard: {tb_dir}")
        print(f"  Checkpoints: {checkpoint_dir}")
        print(f"  最终模型: {final_model_path}")
        print(f"  最佳模型: {checkpoint_dir / 'best_model.zip'}")
        print()
        print("查看 TensorBoard:")
        print(f"  tensorboard --logdir {tb_dir}")
        print()

    except KeyboardInterrupt:
        print()
        print("=" * 70)
        print("训练被用户中断")
        print("=" * 70)

        # 保存中断时的模型
        interrupted_model_path = checkpoint_dir / 'ppo_model_interrupted.zip'
        model.save(interrupted_model_path)
        print(f"中断模型已保存: {interrupted_model_path}")

    except Exception as e:
        print()
        print("=" * 70)
        print("训练出错")
        print("=" * 70)
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

        # 保存出错时的模型
        error_model_path = checkpoint_dir / 'ppo_model_error.zip'
        model.save(error_model_path)
        print(f"出错模型已保存: {error_model_path}")

        raise

    finally:
        # 关闭环境
        train_env.close()
        eval_env.close()


if __name__ == '__main__':
    main()
