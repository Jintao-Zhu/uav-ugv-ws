#!/usr/bin/env python3
"""
Vanilla PPO Baseline - 无任何改进的标准PPO

学术目的：作为消融实验的对照组，证明V4改进的有效性
与V4的区别：
1. 固定熵系数 (0.01) - 无动态衰减
2. 标准学习率衰减 (降至0) - 无保底机制
3. 标准网络架构 [64, 64] - 无扩展容量
4. 标准奖励函数 - 无进取型调整
"""

import sys
import os
from pathlib import Path
import yaml
from typing import Callable
import numpy as np

from stable_baselines3 import PPO
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


def make_env_wrapper(map_path, rank, base_seed=20000):
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
    print("🔬 Vanilla PPO Baseline Training (消融实验对照组)")
    print("=" * 70)

    # 配置
    MAP_PATH = "maps/map_02.map"
    N_ENVS = 8
    TOTAL_TIMESTEPS = 1_200_000

    print(f"\n配置:")
    print(f"  - 地图: {MAP_PATH}")
    print(f"  - 并行环境数: {N_ENVS}")
    print(f"  - 总训练步数: {TOTAL_TIMESTEPS:,}")
    print(f"\nVanilla PPO 特征:")
    print(f"  - 固定熵系数: 0.01 (无动态调整)")
    print(f"  - 标准学习率: 0.0003 → 0 (无保底)")
    print(f"  - 标准网络: [64, 64] (无扩展)")
    print(f"  - 标准奖励: 无进取型调整")

    # 创建环境
    print("\n创建并行训练环境...")
    envs = SubprocVecEnv([make_env_wrapper(MAP_PATH, i) for i in range(N_ENVS)])
    envs = VecMonitor(envs)

    print("创建评估环境...")
    eval_env = SubprocVecEnv([make_env_wrapper(MAP_PATH, 998)])
    eval_env = VecMonitor(eval_env)

    # 设置保存目录
    SAVE_DIR = project_root / "outputs" / "vanilla_ppo_baseline_map02"
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
        name_prefix="vanilla_ppo",
        verbose=1
    )

    # 初始化 Vanilla PPO
    print("\n初始化 Vanilla PPO...")

    # 标准网络架构
    policy_kwargs = dict(
        net_arch=[64, 64],  # SB3默认架构
    )

    model = PPO(
        "MultiInputPolicy",
        envs,
        learning_rate=3e-4,  # 标准学习率，会衰减到0
        n_steps=2048,
        batch_size=64,  # 标准batch size
        n_epochs=10,
        gamma=0.99,
        ent_coef=0.01,  # 固定熵系数
        clip_range=0.2,
        vf_coef=0.5,
        max_grad_norm=0.5,
        policy_kwargs=policy_kwargs,
        tensorboard_log=str(SAVE_DIR / "tb_logs"),
        verbose=1
    )

    print("\n模型配置:")
    print(f"  - 策略网络: {policy_kwargs['net_arch']}")
    print(f"  - 学习率: 0.0003 (标准衰减)")
    print(f"  - 熵系数: 0.01 (固定)")
    print(f"  - Batch size: 64")

    # 开始训练
    print("\n" + "=" * 70)
    print("开始 Vanilla PPO 训练")
    print("=" * 70)

    try:
        model.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=[eval_callback, checkpoint_callback],
            tb_log_name="Vanilla_PPO"
        )

        # 保存最终模型
        final_model_path = SAVE_DIR / "final_model"
        model.save(str(final_model_path))

        print("\n" + "=" * 70)
        print("✅ Vanilla PPO 训练完成")
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
