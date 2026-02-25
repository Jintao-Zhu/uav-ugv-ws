#!/usr/bin/env python3
"""
Curriculum Learning PPO Training Script

实现三阶段课程学习策略：
- Stage 1: Map_03 (开放地图) - 300k steps
- Stage 2: Map_01 (中等遮挡) - 300k steps
- Stage 3: Map_02 (高遮挡) - 400k steps

关键改进：
1. 分布对齐：固定任务参数，消除数据增强
2. 渐进式难度：从简单到复杂
3. 学习率衰减：每个阶段降低学习率和探索率
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
import torch
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


def make_env(config: Dict[str, Any], seed: int, rank: int = 0, map_path: str = None):
    """
    创建环境的工厂函数（用于并行环境）

    关键改进：移除数据增强，固定任务参数以实现分布对齐

    Args:
        config: 配置字典
        seed: 随机种子
        rank: 环境编号（用于并行环境）
        map_path: 地图路径（用于课程学习）
    """
    def _init():
        # 复制配置
        env_config = config.copy()

        # 如果提供了地图路径，使用指定地图
        if map_path is not None:
            env_config['episode']['map_path'] = map_path

        # ===== 分布对齐：固定任务参数 =====
        # 移除Day24的数据增强，确保训练和测试分布一致
        env_config['tasks']['arrival_rate'] = 0.1  # 固定为0.1
        env_config['tasks']['deadline_min'] = 25   # 固定标准范围
        env_config['tasks']['deadline_max'] = 60

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


def create_training_env(config: Dict[str, Any], map_path: str, n_envs: int, seed: int):
    """创建训练环境（向量化）"""
    print(f"  创建训练环境: {n_envs} 个并行环境")
    print(f"  地图: {map_path}")

    if n_envs == 1:
        env = DummyVecEnv([make_env(config, seed, 0, map_path)])
    else:
        env = SubprocVecEnv([
            make_env(config, seed, i, map_path) for i in range(n_envs)
        ])

    return env


def save_stage_info(output_dir: Path, stage: int, stage_info: Dict[str, Any]):
    """保存阶段信息"""
    stage_file = output_dir / f'stage{stage}_info.json'
    with open(stage_file, 'w') as f:
        json.dump(stage_info, f, indent=2)
    print(f"  阶段信息已保存: {stage_file}")


def main():
    parser = argparse.ArgumentParser(description='Curriculum Learning PPO Training')
    parser.add_argument('--config', type=str, default='configs/day10_ppo_train.yaml',
                        help='基础配置文件路径')
    parser.add_argument('--n_envs', type=int, default=8,
                        help='并行环境数量')
    parser.add_argument('--seed', type=int, default=42,
                        help='训练随机种子')
    parser.add_argument('--eval_seed', type=int, default=10000,
                        help='评估随机种子')
    parser.add_argument('--output_dir', type=str, default=None,
                        help='输出目录（默认：outputs/curriculum_ppo/<timestamp>）')
    parser.add_argument('--device', type=str, default='auto',
                        help='训练设备 (cpu/cuda/auto)')

    args = parser.parse_args()

    # 加载基础配置
    print("=" * 70)
    print("Curriculum Learning PPO Training")
    print("=" * 70)
    print(f"配置文件: {args.config}")
    print()

    config = load_config(args.config)

    # 创建输出目录
    if args.output_dir is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(f'outputs/curriculum_ppo/run_{timestamp}')
    else:
        output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    tb_dir = output_dir / 'tb'
    models_dir = output_dir / 'models'
    models_dir.mkdir(exist_ok=True)

    print(f"输出目录: {output_dir}")
    print(f"TensorBoard: {tb_dir}")
    print()

    # 保存配置
    config_path = output_dir / 'config.yaml'
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    # ===== 课程学习参数定义 =====
    curriculum_stages = [
        {
            'stage': 1,
            'name': 'Stage 1: 基础协同与认知',
            'map_path': 'maps/map_03.map',
            'timesteps': 300000,
            'learning_rate': 0.0005,
            'ent_coef': 0.02,
            'description': 'Map_03 开放地图 - 学习基础协同'
        },
        {
            'stage': 2,
            'name': 'Stage 2: 障碍物适应与规避',
            'map_path': 'maps/map_01.map',
            'timesteps': 300000,
            'learning_rate': 0.0003,
            'ent_coef': 0.01,
            'description': 'Map_01 中等遮挡 - 学习路径规划'
        },
        {
            'stage': 3,
            'name': 'Stage 3: 极端高压微调',
            'map_path': 'maps/map_02.map',
            'timesteps': 600000,  # 400k → 600k，给足收敛时间
            'learning_rate': 0.0001,
            'ent_coef': 0.005,
            'description': 'Map_02 高遮挡 - 最终策略打磨'
        }
    ]

    print("课程学习计划:")
    print("-" * 70)
    for stage_config in curriculum_stages:
        print(f"{stage_config['name']}")
        print(f"  地图: {stage_config['map_path']}")
        print(f"  训练步数: {stage_config['timesteps']:,}")
        print(f"  学习率: {stage_config['learning_rate']}")
        print(f"  探索系数: {stage_config['ent_coef']}")
        print(f"  说明: {stage_config['description']}")
        print()

    total_timesteps = sum(s['timesteps'] for s in curriculum_stages)
    print(f"总训练步数: {total_timesteps:,}")
    print(f"并行环境数: {args.n_envs}")
    print(f"训练种子: {args.seed}")
    print(f"评估种子: {args.eval_seed}")
    print(f"设备: {args.device}")
    print()

    # 保存课程学习计划
    curriculum_plan = {
        'stages': curriculum_stages,
        'total_timesteps': total_timesteps,
        'n_envs': args.n_envs,
        'seed': args.seed,
        'eval_seed': args.eval_seed,
    }
    plan_path = output_dir / 'curriculum_plan.json'
    with open(plan_path, 'w') as f:
        json.dump(curriculum_plan, f, indent=2)
    print(f"课程学习计划已保存: {plan_path}")
    print()

    # ===== 开始课程学习训练 =====
    model = None
    cumulative_timesteps = 0

    for stage_idx, stage_config in enumerate(curriculum_stages):
        stage = stage_config['stage']
        print("=" * 70)
        print(f"{stage_config['name']}")
        print("=" * 70)
        print(f"地图: {stage_config['map_path']}")
        print(f"训练步数: {stage_config['timesteps']:,}")
        print(f"学习率: {stage_config['learning_rate']}")
        print(f"探索系数: {stage_config['ent_coef']}")
        print()

        # 创建当前阶段的训练环境
        train_env = create_training_env(
            config,
            stage_config['map_path'],
            args.n_envs,
            args.seed
        )

        # 创建评估环境（使用当前阶段的地图）
        eval_env = create_training_env(
            config,
            stage_config['map_path'],
            1,
            args.eval_seed
        )
        print(f"  评估环境: 1 个环境 (seed={args.eval_seed})")
        print()

        # 创建或加载模型
        if model is None:
            # Stage 1: 从头开始训练
            print("创建新的 PPO 模型...")

            policy_kwargs = dict(
                net_arch=[128, 128, 64],
                activation_fn=torch.nn.ReLU,
            )

            model = PPO(
                policy='MlpPolicy',
                env=train_env,
                policy_kwargs=policy_kwargs,
                learning_rate=stage_config['learning_rate'],
                n_steps=2048,
                batch_size=256,
                n_epochs=10,
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                ent_coef=stage_config['ent_coef'],
                vf_coef=0.5,
                max_grad_norm=0.5,
                verbose=1,
                device=args.device,
                tensorboard_log=str(tb_dir),
                seed=args.seed,
            )
            print("  模型创建成功")
            print()
        else:
            # Stage 2/3: 加载上一阶段的模型并更新环境
            print(f"加载 Stage {stage-1} 的模型...")
            prev_model_path = models_dir / f'ppo_curriculum_stage{stage-1}.zip'

            # 使用 custom_objects 安全地覆盖超参数
            # SB3 会自动重构带有新学习率的优化器
            custom_objects = {
                "learning_rate": stage_config['learning_rate'],
                "ent_coef": stage_config['ent_coef'],
            }

            model = PPO.load(
                prev_model_path,
                env=train_env,
                device=args.device,
                custom_objects=custom_objects
            )

            # 重新设置 tensorboard_log
            model.tensorboard_log = str(tb_dir)

            print(f"  模型加载成功: {prev_model_path}")
            print(f"  ✓ 学习率已更新: {stage_config['learning_rate']}")
            print(f"  ✓ 探索系数已更新: {stage_config['ent_coef']}")
            print()

        # 创建回调
        checkpoint_dir = output_dir / f'stage{stage}_checkpoints'
        checkpoint_dir.mkdir(exist_ok=True)

        checkpoint_callback = CheckpointCallback(
            save_freq=50000 // args.n_envs,
            save_path=str(checkpoint_dir),
            name_prefix=f'stage{stage}_model',
            save_replay_buffer=False,
            save_vecnormalize=False,
        )

        eval_callback = DetailedEvalCallback(
            eval_env,
            eval_freq=25000 // args.n_envs,
            n_eval_episodes=10,
            eval_seeds=list(range(args.eval_seed, args.eval_seed + 10)),
            log_path=str(output_dir / f'stage{stage}_eval_logs'),
            verbose=1,
        )

        callback = CallbackList([checkpoint_callback, eval_callback])

        # 训练当前阶段
        print(f"开始训练 Stage {stage}...")
        print()

        try:
            # Stage 1 需要 reset_num_timesteps=True 来初始化 TensorBoard
            # Stage 2/3 使用 False 来保持连续的时间步计数
            reset_timesteps = (stage == 1)

            model.learn(
                total_timesteps=stage_config['timesteps'],
                callback=callback,
                log_interval=1,  # 每次更新都记录日志（每 16384 步）
                tb_log_name=f'stage{stage}',
                reset_num_timesteps=reset_timesteps,
            )

            cumulative_timesteps += stage_config['timesteps']

            print()
            print(f"Stage {stage} 训练完成")
            print(f"累计训练步数: {cumulative_timesteps:,}")
            print()

            # 保存当前阶段的模型
            stage_model_path = models_dir / f'ppo_curriculum_stage{stage}.zip'
            model.save(stage_model_path)
            print(f"Stage {stage} 模型已保存: {stage_model_path}")

            # 保存阶段信息
            stage_info = {
                'stage': stage,
                'name': stage_config['name'],
                'map_path': stage_config['map_path'],
                'timesteps': stage_config['timesteps'],
                'cumulative_timesteps': cumulative_timesteps,
                'learning_rate': stage_config['learning_rate'],
                'ent_coef': stage_config['ent_coef'],
                'model_path': str(stage_model_path),
            }
            save_stage_info(output_dir, stage, stage_info)
            print()

        except KeyboardInterrupt:
            print()
            print(f"Stage {stage} 训练被用户中断")
            interrupted_model_path = models_dir / f'ppo_curriculum_stage{stage}_interrupted.zip'
            model.save(interrupted_model_path)
            print(f"中断模型已保存: {interrupted_model_path}")
            break

        except Exception as e:
            print()
            print(f"Stage {stage} 训练出错: {e}")
            import traceback
            traceback.print_exc()

            error_model_path = models_dir / f'ppo_curriculum_stage{stage}_error.zip'
            model.save(error_model_path)
            print(f"出错模型已保存: {error_model_path}")
            raise

        finally:
            # 关闭环境
            train_env.close()
            eval_env.close()

    # ===== 训练完成 =====
    print()
    print("=" * 70)
    print("课程学习训练完成")
    print("=" * 70)
    print()

    # 保存最终模型
    final_model_path = models_dir / 'ppo_curriculum_final.zip'
    model.save(final_model_path)
    print(f"最终模型已保存: {final_model_path}")

    # 保存训练摘要
    summary = {
        'curriculum_stages': curriculum_stages,
        'total_timesteps': cumulative_timesteps,
        'n_envs': args.n_envs,
        'train_seed': args.seed,
        'eval_seed': args.eval_seed,
        'output_dir': str(output_dir),
        'final_model': str(final_model_path),
        'tensorboard_log': str(tb_dir),
    }

    summary_path = output_dir / 'training_summary.json'
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"训练摘要已保存: {summary_path}")
    print()
    print("输出文件:")
    print(f"  配置: {config_path}")
    print(f"  课程计划: {plan_path}")
    print(f"  TensorBoard: {tb_dir}")
    print(f"  模型目录: {models_dir}")
    print(f"  最终模型: {final_model_path}")
    print()
    print("查看 TensorBoard:")
    print(f"  tensorboard --logdir {tb_dir}")
    print()
    print("下一步：使用测试集评估模型")
    print(f"  python scripts/evaluate_ppo_cross_maps.py --model {final_model_path} --test_seeds 20000-20009")
    print()


if __name__ == '__main__':
    main()
