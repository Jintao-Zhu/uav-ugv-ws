#!/usr/bin/env python3
"""
Stage 3 多种子拓扑训练脚本

基于高熵正则化的成功经验，进一步引入多种子训练策略：
- 8个并行环境使用8个不同的空间生成种子（10000-10007）
- 防止模型过拟合到单一空间拓扑分布
- 提升在极端困难种子上的鲁棒性

核心改进：
1. 学习率：0.0002（已验证最优）
2. 探索系数：0.015（高熵正则化）
3. 训练步数：400k（早停策略）
4. 多种子：每个环境使用不同的空间生成种子（NEW!）

预期效果：
- 最小值：11 → 20-25 (+100%)
- 标准差：12.94 → < 10 (-23%)
- 平均值：35.60 → 37+ (+4%)
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
from stable_baselines3.common.utils import set_random_seed

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


def make_env(config, rank: int, base_seed: int, map_path: str = None):
    """
    环境工厂函数 - 为每个并行环境分配独立的空间生成种子

    关键设计：
    - rank=0 使用 seed=10000
    - rank=1 使用 seed=10001
    - ...
    - rank=7 使用 seed=10007

    这样8个环境会生成8种不同的空间拓扑分布，
    强迫模型学习对各种障碍物布局的鲁棒策略。
    """
    def _init():
        # 计算当前环境的独立种子
        env_seed = base_seed + rank

        # 设置全局随机种子（影响numpy、random等）
        set_random_seed(env_seed)

        env_config = config.copy()

        if map_path is not None:
            env_config['episode']['map_path'] = map_path

        # 🔥 关键：分布对齐，固定任务参数（避免Day24负迁移）
        env_config['tasks']['arrival_rate'] = 0.1
        env_config['tasks']['deadline_min'] = 25
        env_config['tasks']['deadline_max'] = 60

        env = AGCoopGymEnv(env_config)
        env = FlattenObservation(env)
        env = Monitor(env)

        # 重置环境时使用该环境专属的种子
        env.reset(seed=env_seed)

        print(f"  环境 {rank} 初始化完成，使用种子 {env_seed}")

        return env

    return _init


def create_diverse_training_env(config, map_path: str, n_envs: int, base_seed: int):
    """
    创建多种子并行训练环境

    每个环境使用不同的空间生成种子，确保训练数据的拓扑多样性
    """
    print(f"创建多种子训练环境:")
    print(f"  地图: {map_path}")
    print(f"  并行环境数: {n_envs}")
    print(f"  种子范围: {base_seed} - {base_seed + n_envs - 1}")
    print()

    if n_envs == 1:
        env = DummyVecEnv([make_env(config, 0, base_seed, map_path)])
    else:
        env = SubprocVecEnv([
            make_env(config, i, base_seed, map_path) for i in range(n_envs)
        ])

    print(f"✓ 多种子环境创建成功")
    print()
    return env


def main():
    parser = argparse.ArgumentParser(description='Stage 3 多种子拓扑训练')
    parser.add_argument('--stage2_model', type=str, required=True,
                        help='Stage 2 模型路径')
    parser.add_argument('--config', type=str, default='configs/curriculum_learning.yaml',
                        help='配置文件路径')
    parser.add_argument('--n_envs', type=int, default=8,
                        help='并行环境数量')
    parser.add_argument('--base_seed', type=int, default=10000,
                        help='训练种子基准值（每个环境 +1）')
    parser.add_argument('--eval_seed', type=int, default=10000,
                        help='评估随机种子')
    parser.add_argument('--device', type=str, default='auto',
                        help='训练设备 (cpu/cuda/auto)')
    parser.add_argument('--output_dir', type=str, default=None,
                        help='输出目录')

    # 核心超参数（沿用高熵版的成功配置）
    parser.add_argument('--learning_rate', type=float, default=0.0002,
                        help='学习率（默认 0.0002）')
    parser.add_argument('--ent_coef', type=float, default=0.015,
                        help='探索系数（默认 0.015，高熵正则化）')
    parser.add_argument('--timesteps', type=int, default=400000,
                        help='训练步数（默认 400k，早停策略）')

    args = parser.parse_args()

    print("=" * 70)
    print("Stage 3: 多种子拓扑训练 + 高熵正则化")
    print("=" * 70)
    print(f"Stage 2 模型: {args.stage2_model}")
    print(f"配置文件: {args.config}")
    print()
    print("核心策略:")
    print(f"  ✓ 高熵正则化: ent_coef={args.ent_coef}")
    print(f"  ✓ 适度学习率: lr={args.learning_rate}")
    print(f"  ✓ 早停策略: {args.timesteps:,} 步")
    print(f"  ✓ 多种子训练: {args.n_envs} 个环境，种子 {args.base_seed}-{args.base_seed + args.n_envs - 1}")
    print()
    print("预期效果:")
    print("  - 最小值: 11 → 20-25 (+100%)")
    print("  - 标准差: 12.94 → < 10 (-23%)")
    print("  - 平均值: 35.60 → 37+ (+4%)")
    print()

    # 加载配置
    config = load_config(args.config)

    # 创建输出目录
    if args.output_dir is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(f'outputs/stage3_diverse_seeds/run_{timestamp}')
    else:
        output_dir = Path(args.output_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    tb_dir = output_dir / 'tb'
    checkpoint_dir = output_dir / 'checkpoints'
    checkpoint_dir.mkdir(exist_ok=True)

    print(f"输出目录: {output_dir}")
    print()

    # 创建多种子训练环境
    print("=" * 70)
    print("创建训练环境")
    print("=" * 70)
    train_env = create_diverse_training_env(
        config,
        'maps/map_02.map',
        args.n_envs,
        args.base_seed
    )

    # 创建评估环境（使用单一种子，保持评估一致性）
    print("创建评估环境...")
    eval_env = create_diverse_training_env(
        config,
        'maps/map_02.map',
        1,
        args.eval_seed
    )

    # 加载 Stage 2 模型并注入高熵配置
    print("=" * 70)
    print("加载模型并注入超参数")
    print("=" * 70)
    print(f"Stage 2 模型: {args.stage2_model}")
    print()
    print("注入超参数:")
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
        name_prefix='stage3_diverse',
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
        'base_seed': args.base_seed,
        'seed_range': f'{args.base_seed}-{args.base_seed + args.n_envs - 1}',
        'eval_seed': args.eval_seed,
        'strategy': 'diverse_seeds + high_entropy_regularization',
        'description': '多种子拓扑训练 + 高熵正则化，提升极端情况鲁棒性'
    }

    config_path = output_dir / 'training_config.json'
    with open(config_path, 'w') as f:
        json.dump(training_config, f, indent=2)
    print(f"训练配置已保存: {config_path}")
    print()

    # 开始训练
    print("=" * 70)
    print("开始训练 Stage 3 (多种子 + 高熵)")
    print("=" * 70)
    print()
    print("训练策略:")
    print("  1. 每个环境使用不同的空间生成种子")
    print("  2. 高熵正则化防止策略僵化")
    print("  3. 早停策略防止过拟合")
    print()
    print("预期训练动态:")
    print("  - 策略熵保持在 -3.7 左右（灵活）")
    print("  - 训练奖励稳定在 45-48 分（适度）")
    print("  - 价值损失稳定下降（学习中）")
    print()

    try:
        model.learn(
            total_timesteps=args.timesteps,
            callback=callback,
            log_interval=1,
            tb_log_name='stage3_diverse_seeds',
            reset_num_timesteps=False,
        )

        print()
        print("=" * 70)
        print("训练完成")
        print("=" * 70)

        # 保存最终模型
        final_model_path = output_dir / 'ppo_stage3_diverse_seeds_final.zip'
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
        print("=" * 70)
        print("下一步：评估模型")
        print("=" * 70)
        print(f"python scripts/evaluate_curriculum.py \\")
        print(f"  --model {final_model_path} \\")
        print(f"  --map maps/map_02.map \\")
        print(f"  --test_seeds 20000-20009")
        print()
        print("预期结果:")
        print("  - 平均完成任务数: 37+ (vs 35.60)")
        print("  - 标准差: < 10 (vs 12.94)")
        print("  - 最小值: 20-25 (vs 11)")
        print("  - 最大值: 45-50 (稳定)")
        print()

    except KeyboardInterrupt:
        print()
        print("训练被用户中断")
        interrupted_model_path = checkpoint_dir / 'stage3_diverse_interrupted.zip'
        model.save(interrupted_model_path)
        print(f"中断模型已保存: {interrupted_model_path}")

    except Exception as e:
        print()
        print(f"训练出错: {e}")
        import traceback
        traceback.print_exc()

        error_model_path = checkpoint_dir / 'stage3_diverse_error.zip'
        model.save(error_model_path)
        print(f"出错模型已保存: {error_model_path}")
        raise

    finally:
        train_env.close()
        eval_env.close()


if __name__ == '__main__':
    main()
