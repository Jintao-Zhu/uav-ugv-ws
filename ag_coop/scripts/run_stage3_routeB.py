#!/usr/bin/env python3
"""
路线B：非线性奖励重塑 + 高熵正则化

核心创新：
1. 非线性deadline惩罚：使用tanh函数实现有界惩罚
   - 惩罚上限：-1.20（保证净收益 = 1.5 - 1.2 = +0.3 > 0）
   - 核心理念："迟到总比不到好（Better late than never）"

2. 高熵正则化：ent_coef=0.015（继承成功经验）

3. 多种子训练：8个环境使用不同种子（10000-10007）

预期效果：
- 消除"躺平"策略，智能体在极端困难种子上也会积极接任务
- Seed 20006: 11 → 30+ (+173%)
- 平均完成任务数: 35.60 → 40+ (+12%)
- 标准差: 12.94 → < 8 (-38%)
- Trade-off: Tardiness会上升（这是必要的代价）

理论支撑：
- 打破了"不做任务以规避惩罚"的纳什均衡
- 通过奖励重塑（Reward Shaping）改变智能体的风险偏好
- 从"风险厌恶"转变为"适度风险承担"
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
    """
    def _init():
        # 计算当前环境的独立种子
        env_seed = base_seed + rank

        # 设置全局随机种子
        set_random_seed(env_seed)

        env_config = config.copy()

        if map_path is not None:
            env_config['episode']['map_path'] = map_path

        # 🔥 分布对齐：固定任务参数
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
    """创建多种子并行训练环境"""
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
    parser = argparse.ArgumentParser(description='路线B：非线性奖励重塑训练')
    parser.add_argument('--stage2_model', type=str, required=True,
                        help='Stage 2 模型路径')
    parser.add_argument('--config', type=str, default='configs/curriculum_learning.yaml',
                        help='配置文件路径')
    parser.add_argument('--n_envs', type=int, default=8,
                        help='并行环境数量')
    parser.add_argument('--base_seed', type=int, default=10000,
                        help='训练种子基准值')
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
                        help='探索系数（默认 0.015）')
    parser.add_argument('--timesteps', type=int, default=500000,
                        help='训练步数（默认 500k）')

    args = parser.parse_args()

    print("=" * 70)
    print("路线B：非线性奖励重塑 + 高熵正则化")
    print("=" * 70)
    print(f"Stage 2 模型: {args.stage2_model}")
    print(f"配置文件: {args.config}")
    print()
    print("核心创新:")
    print(f"  ✓ 非线性deadline惩罚: tanh函数，惩罚上限 -1.20")
    print(f"  ✓ 高熵正则化: ent_coef={args.ent_coef}")
    print(f"  ✓ 适度学习率: lr={args.learning_rate}")
    print(f"  ✓ 多种子训练: {args.n_envs} 个环境")
    print(f"  ✓ 训练步数: {args.timesteps:,} 步")
    print()
    print("理论基础:")
    print("  - 打破'躺平'纳什均衡")
    print("  - 奖励重塑改变风险偏好")
    print("  - '迟到总比不到好'策略")
    print()
    print("预期效果:")
    print("  - Seed 20006: 11 → 30+ (+173%)")
    print("  - 平均完成任务数: 35.60 → 40+ (+12%)")
    print("  - 标准差: 12.94 → < 8 (-38%)")
    print("  - Trade-off: Tardiness ↑ (必要代价)")
    print()

    # 加载配置
    config = load_config(args.config)

    # 创建输出目录
    if args.output_dir is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = Path(f'outputs/routeB_nonlinear_reward/run_{timestamp}')
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

    # 创建评估环境
    print("创建评估环境...")
    eval_env = create_diverse_training_env(
        config,
        'maps/map_02.map',
        1,
        args.eval_seed
    )

    # 加载 Stage 2 模型
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
        name_prefix='routeB',
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
        'strategy': 'nonlinear_deadline_penalty + high_entropy_regularization',
        'reward_shaping': {
            'max_penalty': -1.20,
            'steepness': 0.05,
            'function': 'tanh',
            'rationale': 'Better late than never - prevent overly conservative strategy'
        },
        'description': '非线性奖励重塑，打破躺平纳什均衡'
    }

    config_path = output_dir / 'training_config.json'
    with open(config_path, 'w') as f:
        json.dump(training_config, f, indent=2)
    print(f"训练配置已保存: {config_path}")
    print()

    # 开始训练
    print("=" * 70)
    print("开始训练 路线B (非线性奖励重塑)")
    print("=" * 70)
    print()
    print("训练策略:")
    print("  1. 非线性deadline惩罚（有界惩罚）")
    print("  2. 高熵正则化防止策略僵化")
    print("  3. 多种子训练增强泛化能力")
    print()
    print("预期训练动态:")
    print("  - 策略熵保持在 -3.7 左右")
    print("  - 训练奖励可能略低于高熵版（因为接受更多困难任务）")
    print("  - Deadline miss 会增加（这是预期的）")
    print("  - 但总完成任务数会显著提升")
    print()

    try:
        model.learn(
            total_timesteps=args.timesteps,
            callback=callback,
            log_interval=1,
            tb_log_name='routeB_nonlinear',
            reset_num_timesteps=False,
        )

        print()
        print("=" * 70)
        print("训练完成")
        print("=" * 70)

        # 保存最终模型
        final_model_path = output_dir / 'ppo_routeB_final.zip'
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
        print("  - 平均完成任务数: 40+ (vs 35.60)")
        print("  - 标准差: < 8 (vs 12.94)")
        print("  - 最小值: 30+ (vs 11)")
        print("  - Tardiness: ↑ (必要的trade-off)")
        print()

    except KeyboardInterrupt:
        print()
        print("训练被用户中断")
        interrupted_model_path = checkpoint_dir / 'routeB_interrupted.zip'
        model.save(interrupted_model_path)
        print(f"中断模型已保存: {interrupted_model_path}")

    except Exception as e:
        print()
        print(f"训练出错: {e}")
        import traceback
        traceback.print_exc()

        error_model_path = checkpoint_dir / 'routeB_error.zip'
        model.save(error_model_path)
        print(f"出错模型已保存: {error_model_path}")
        raise

    finally:
        train_env.close()
        eval_env.close()


if __name__ == '__main__':
    main()
