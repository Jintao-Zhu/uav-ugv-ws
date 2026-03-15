#!/usr/bin/env python3
"""
DQN Baseline - 经典值函数方法

学术目的：证明在当前动作空间下 Actor-Critic (PPO) 架构的优越性
与PPO的区别：
1. 值函数方法 (Q-learning) vs 策略梯度
2. 离散动作空间处理方式不同
3. 探索策略：epsilon-greedy vs 熵正则化
"""

import sys
import os
from pathlib import Path
import yaml
import numpy as np

from stable_baselines3 import DQN
from stable_baselines3.common.vec_env import SubprocVecEnv, VecMonitor
from stable_baselines3.common.utils import set_random_seed
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv


def load_config(map_path):
    """加载配置文件"""
    config_path = project_root / 'configs' / 'curriculum_learning.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['episode']['map_path'] = map_path
    config['episode']['horizon_steps'] = 500

    return config


def make_env_wrapper(map_path, rank, base_seed=30000):
    """创建环境"""
    def _init():
        env_seed = base_seed + rank
        set_random_seed(env_seed)
        config = load_config(map_path)
        env = AGCoopEnv(config, method='rl', planner='PIBT')
        env.seed = env_seed
        return env
    return _init


def main():
    print("\n" + "=" * 70)
    print("🔬 DQN Baseline Training (值函数方法对照)")
    print("=" * 70)

    # 配置
    MAP_PATH = "maps/map_02.map"
    N_ENVS = 8
    TOTAL_TIMESTEPS = 1_200_000

    print(f"\n配置:")
    print(f"  - 地图: {MAP_PATH}")
    print(f"  - 并行环境数: {N_ENVS}")
    print(f"  - 总训练步数: {TOTAL_TIMESTEPS:,}")
    print(f"\nDQN 特征:")
    print(f"  - 算法: Deep Q-Network (值函数方法)")
    print(f"  - 探索策略: Epsilon-greedy (1.0 → 0.05)")
    print(f"  - 经验回放: 100k buffer")
    print(f"  - 目标网络: 每10k步更新")

    # 创建环境
    print("\n创建并行训练环境...")
    envs = SubprocVecEnv([make_env_wrapper(MAP_PATH, i) for i in range(N_ENVS)])
    envs = VecMonitor(envs)

    print("创建评估环境...")
    eval_env = SubprocVecEnv([make_env_wrapper(MAP_PATH, 997)])
    eval_env = VecMonitor(eval_env)

    # 设置保存目录
    SAVE_DIR = project_root / "outputs" / "dqn_baseline_map02"
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n模型保存目录: {SAVE_DIR}")

    # 回调函数
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=str(SAVE_DIR / "best_model"),
        log_path=str(SAVE_DIR),
        eval_freq=16000,
        deterministic=True,
        render=False,
        verbose=1
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=50000,
        save_path=str(SAVE_DIR / "checkpoints"),
        name_prefix="dqn",
        verbose=1
    )

    # 初始化 DQN
    print("\n初始化 DQN...")

    # DQN网络架构
    policy_kwargs = dict(
        net_arch=[256, 128],  # Q网络架构
    )

    model = DQN(
        "MultiInputPolicy",
        envs,
        learning_rate=1e-4,
        buffer_size=100000,  # 经验回放缓冲区
        learning_starts=10000,  # 开始学习前的随机探索步数
        batch_size=128,
        tau=1.0,  # 目标网络软更新系数
        gamma=0.99,
        train_freq=4,  # 每4步训练一次
        gradient_steps=1,
        target_update_interval=10000,  # 目标网络更新频率
        exploration_fraction=0.3,  # 前30%步数进行探索衰减
        exploration_initial_eps=1.0,  # 初始探索率
        exploration_final_eps=0.05,  # 最终探索率
        max_grad_norm=10,
        policy_kwargs=policy_kwargs,
        tensorboard_log=str(SAVE_DIR / "tb_logs"),
        verbose=1
    )

    print("\n模型配置:")
    print(f"  - Q网络: {policy_kwargs['net_arch']}")
    print(f"  - 学习率: 0.0001")
    print(f"  - Buffer size: 100k")
    print(f"  - Exploration: 1.0 → 0.05")
    print(f"  - Target update: 每10k步")

    # 开始训练
    print("\n" + "=" * 70)
    print("开始 DQN 训练")
    print("=" * 70)
    print("\nDQN 训练特点:")
    print("  - 前10k步: 纯随机探索填充buffer")
    print("  - 10k-360k步: 高探索率 (1.0 → 0.05)")
    print("  - 360k+步: 低探索率 (0.05) 稳定策略")

    try:
        model.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=[eval_callback, checkpoint_callback],
            tb_log_name="DQN"
        )

        # 保存最终模型
        final_model_path = SAVE_DIR / "final_model"
        model.save(str(final_model_path))

        print("\n" + "=" * 70)
        print("✅ DQN 训练完成")
        print("=" * 70)
        print(f"\n模型保存位置:")
        print(f"  - 最佳模型: {SAVE_DIR / 'best_model'}")
        print(f"  - 最终模型: {final_model_path}")

    except KeyboardInterrupt:
        print("\n训练被中断")
        model.save(str(SAVE_DIR / "interrupted_model"))

    finally:
        envs.close()
        eval_env.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ 训练失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
