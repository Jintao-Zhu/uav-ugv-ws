#!/usr/bin/env python3
"""
简化版PPO训练脚本 - UAV独立飞行系统

使用DummyVecEnv（单进程）避免环境兼容性问题
适合快速验证训练流程
"""

import sys
import os
from pathlib import Path
import yaml
from typing import Callable

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
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


def make_env(map_path, seed=0):
    """创建环境"""
    def _init():
        config = load_config(map_path)
        env = AGCoopEnv(config, method='rl', planner='PIBT')
        env.seed = seed
        env = Monitor(env)  # 包装Monitor用于记录
        return env
    return _init


def linear_schedule(initial_value: float) -> Callable[[float], float]:
    """线性学习率衰减"""
    def func(progress_remaining: float) -> float:
        return progress_remaining * initial_value + (1 - progress_remaining) * (initial_value / 3)
    return func


def main():
    print("\n" + "="*70)
    print("🚀 PPO训练 - 山区救险地图（Map_02）")
    print("="*70)

    # 配置
    MAP_PATH = "maps/map_02.map"
    TOTAL_TIMESTEPS = 500_000  # 先用500k步快速验证

    print(f"\n配置:")
    print(f"  - 地图: {MAP_PATH}")
    print(f"  - 总训练步数: {TOTAL_TIMESTEPS:,}")

    # 创建环境
    print("\n创建训练环境...")
    env = DummyVecEnv([make_env(MAP_PATH, seed=42)])

    print("创建评估环境...")
    eval_env = DummyVecEnv([make_env(MAP_PATH, seed=999)])

    # 设置保存目录
    SAVE_DIR = project_root / "outputs" / "ppo_map02_simple"
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n模型保存目录: {SAVE_DIR}")

    # 回调函数
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=str(SAVE_DIR / "best_model"),
        log_path=str(SAVE_DIR),
        eval_freq=5000,
        deterministic=True,
        render=False,
        verbose=1
    )

    checkpoint_callback = CheckpointCallback(
        save_freq=25000,
        save_path=str(SAVE_DIR / "checkpoints"),
        name_prefix="ppo_checkpoint",
        verbose=1
    )

    # 初始化PPO
    print("\n初始化PPO智能体...")

    policy_kwargs = dict(
        net_arch=[256, 128, 64],
    )

    model = PPO(
        "MultiInputPolicy",
        env,
        learning_rate=linear_schedule(0.0003),
        n_steps=2048,
        batch_size=256,
        n_epochs=10,
        gamma=0.99,
        ent_coef=0.015,  # 强制探索
        clip_range=0.2,
        vf_coef=0.5,
        max_grad_norm=0.5,
        policy_kwargs=policy_kwargs,
        tensorboard_log=str(SAVE_DIR / "tb_logs"),
        verbose=1
    )

    print("\n模型配置:")
    print(f"  - 策略网络: {policy_kwargs['net_arch']}")
    print(f"  - 学习率: 0.0003 → 0.0001 (线性衰减)")
    print(f"  - 熵系数: 0.015")

    # 开始训练
    print("\n" + "="*70)
    print("开始训练！")
    print("="*70)
    print(f"\nTensorBoard监控:")
    print(f"  tensorboard --logdir {SAVE_DIR / 'tb_logs'}")
    print()

    try:
        model.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=[eval_callback, checkpoint_callback],
            tb_log_name="PPO_UAV_Flight"
        )

        # 保存最终模型
        final_model_path = SAVE_DIR / "final_model"
        model.save(str(final_model_path))

        print("\n" + "="*70)
        print("✅ 训练完成！")
        print("="*70)
        print(f"\n模型保存位置:")
        print(f"  - 最佳模型: {SAVE_DIR / 'best_model'}")
        print(f"  - 最终模型: {final_model_path}")
        print()

    except KeyboardInterrupt:
        print("\n\n训练被中断！")
        model.save(str(SAVE_DIR / "interrupted_model"))
        print(f"模型已保存: {SAVE_DIR / 'interrupted_model'}")

    finally:
        env.close()
        eval_env.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ 训练失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
