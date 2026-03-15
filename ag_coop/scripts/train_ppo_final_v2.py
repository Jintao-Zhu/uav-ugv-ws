#!/usr/bin/env python3
"""
终极版PPO训练脚本 - 动态熵衰减 + 保底学习率 + 进取型奖励

这是通往顶会 SOTA 模型的最后一次冲刺！

核心创新：
1. 动态熵衰减：0.015 → 0.002 (前期探索，后期收敛)
2. 保底学习率：0.0004 → 0.0001 (永不归零，持续纠错)
3. 进取型奖励：r_task = 1.8 (鼓励勇敢接单)

目标：
- 任务完成数：48-50
- 总奖励：55+
- 超越所有Baseline
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
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback, BaseCallback

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv


# ==========================================
# 1. 核心回调与调度器定义
# ==========================================

class EntropyDecayCallback(BaseCallback):
    """
    动态熵衰减回调函数：
    前期保持高熵 (0.015) 强制探索飞行；
    后期平滑衰减至低熵 (0.002) 锁定最优策略，防止乱飞坠机。
    """
    def __init__(self, initial_ent=0.015, final_ent=0.002, end_step=1000000, verbose=0):
        super().__init__(verbose)
        self.initial_ent = initial_ent
        self.final_ent = final_ent
        self.end_step = end_step

    def _on_step(self) -> bool:
        # 计算当前的衰减比例 (0.0 到 1.0)
        fraction = min(1.0, self.num_timesteps / self.end_step)
        # 线性插值计算当前熵系数
        current_ent = self.initial_ent - fraction * (self.initial_ent - self.final_ent)
        # 动态修改 PPO 模型的熵系数
        self.model.ent_coef = current_ent
        # 记录到 TensorBoard，方便你盯盘
        self.logger.record("train/dynamic_ent_coef", current_ent)
        return True


def linear_schedule_with_min(initial_value: float, min_value: float = 0.0001) -> Callable[[float], float]:
    """
    带保底底线的学习率衰减函数：
    防止后期学习率降为 0 导致策略僵化无法纠错。
    """
    def func(progress_remaining: float) -> float:
        # progress_remaining 从 1.0 降到 0.0
        lr = progress_remaining * initial_value
        return max(lr, min_value)  # 永远不低于 min_value
    return func


def load_config(map_path):
    """加载配置文件"""
    config_path = project_root / 'configs' / 'curriculum_learning.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['episode']['map_path'] = map_path
    config['episode']['horizon_steps'] = 500

    return config


def make_env_wrapper(map_path, rank, base_seed=10000):
    """
    创建带有独立随机种子的并行环境

    Args:
        map_path: 地图文件路径
        rank: 环境编号（用于生成不同的随机种子）
        base_seed: 基础种子
    """
    def _init():
        env_seed = base_seed + rank
        set_random_seed(env_seed)

        # 加载配置
        config = load_config(map_path)

        # 创建环境
        env = AGCoopEnv(config, method='rl', planner='PIBT')

        # 设置环境种子
        env.seed = env_seed

        return env

    return _init


# ==========================================
# 2. 训练主程序
# ==========================================
def main():
    print("\n" + "=" * 70)
    print("🚀 启动终极 PPO 训练 (动态熵 + 保底 LR + 进取奖励)")
    print("=" * 70)

    # ==================== 核心配置 ====================
    MAP_PATH = "maps/map_02.map"
    N_ENVS = 8
    # 既然有回调保护，我们可以放心跑到 1.2M 步确保彻底收敛
    TOTAL_TIMESTEPS = 1_200_000

    print(f"\n配置:")
    print(f"  - 地图: {MAP_PATH}")
    print(f"  - 并行环境数: {N_ENVS}")
    print(f"  - 总训练步数: {TOTAL_TIMESTEPS:,}")
    print(f"  - 预计训练时间: 2.5-3.5小时")

    # ==================== 创建并行训练环境 ====================
    print("\n创建并行训练环境...")
    envs = SubprocVecEnv([make_env_wrapper(MAP_PATH, i) for i in range(N_ENVS)])
    envs = VecMonitor(envs)

    print("创建评估环境...")
    eval_env = SubprocVecEnv([make_env_wrapper(MAP_PATH, 999)])
    eval_env = VecMonitor(eval_env)

    # ==================== 设置回调函数 ====================
    SAVE_DIR = project_root / "outputs" / "ppo_v4_golden_ratio_map02"
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n模型保存目录: {SAVE_DIR}")

    # Eval 回调：每 16000 步评估一次，保存最高分模型
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=str(SAVE_DIR / "best_model"),
        log_path=str(SAVE_DIR),
        eval_freq=16000,
        deterministic=True,
        render=False,
        verbose=1
    )

    # 定期检查点保存
    checkpoint_callback = CheckpointCallback(
        save_freq=50000,
        save_path=str(SAVE_DIR / "checkpoints"),
        name_prefix="ppo_final_v2",
        verbose=1
    )

    # 实例化我们的动态熵衰减回调 (在 100 万步时衰减到底)
    entropy_callback = EntropyDecayCallback(
        initial_ent=0.015,
        final_ent=0.002,
        end_step=1000000,
        verbose=1
    )

    # ==================== 初始化PPO模型 ====================
    print("\n初始化PPO智能体...")

    # 扩大网络容量，应对 16 维动作空间和 5 维无人机状态
    policy_kwargs = dict(
        net_arch=[256, 128, 64],
    )

    model = PPO(
        "MultiInputPolicy",
        envs,
        learning_rate=linear_schedule_with_min(0.0004, min_value=0.0001),  # 起始0.0004，保底0.0001
        n_steps=2048,
        batch_size=256,
        n_epochs=10,
        gamma=0.99,
        ent_coef=0.015,  # 初始值，会被回调函数覆盖
        clip_range=0.2,
        vf_coef=0.5,
        max_grad_norm=0.5,
        policy_kwargs=policy_kwargs,
        tensorboard_log=str(SAVE_DIR / "tb_logs"),
        verbose=1
    )

    print("\n模型配置:")
    print(f"  - 策略网络: {policy_kwargs['net_arch']}")
    print(f"  - 学习率: 0.0004 → 0.0001 (带保底)")
    print(f"  - 熵系数: 0.015 → 0.002 (动态衰减)")
    print(f"  - 任务奖励: 1.8 (进取型)")
    print(f"  - Batch size: 256")
    print(f"  - N steps: 2048")

    # ==================== 开始训练 ====================
    print("\n" + "=" * 70)
    print("开始终极冲刺！")
    print("=" * 70)
    print("\n预期训练阶段:")
    print("  阶段1 (0-300k步): 坠机与试错期")
    print("    - 奖励可能跌到-100以下")
    print("    - UAV学习飞行和电量管理")
    print("\n  阶段2 (300k-800k步): 觉醒的空中基站")
    print("    - 奖励开始陡升")
    print("    - 学会充电和通信覆盖")
    print("    - 逼近Static-Center性能（+29.68）")
    print("\n  阶段3 (800k-1.2M步): 超越人类规则 🔥")
    print("    - 熵系数降低，策略稳定")
    print("    - 保底学习率持续纠错")
    print("    - 奖励突破60分大关")
    print("    - 目标：48-50任务，55+奖励")
    print("\n" + "=" * 70)

    print("\n启动TensorBoard监控:")
    print(f"  tensorboard --logdir {SAVE_DIR / 'tb_logs'} --port 6006")
    print("\n重点监控指标:")
    print("  - train/dynamic_ent_coef: 熵系数衰减曲线")
    print("  - rollout/ep_rew_mean: 总奖励（V4黄金比例：预期80-120分）")
    print("  - 🎯 核心指标：tasks_completed（目标：46-48）")
    print("  - 🎯 通信中断：outage步数（目标：140-160步）")
    print()

    try:
        # 将三个 Callback 一起传入
        model.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=[eval_callback, checkpoint_callback, entropy_callback],
            tb_log_name="PPO_V4_GoldenRatio"
        )

        # ==================== 保存最终模型 ====================
        final_model_path = SAVE_DIR / "final_model"
        model.save(str(final_model_path))

        print("\n" + "=" * 70)
        print("✅ 终极训练圆满完成！")
        print("=" * 70)
        print(f"\n模型保存位置:")
        print(f"  - 最佳模型: {SAVE_DIR / 'best_model'}")
        print(f"  - 最终模型: {final_model_path}")
        print(f"  - 检查点: {SAVE_DIR / 'checkpoints'}")
        print(f"\n下一步:")
        print(f"  1. 查看TensorBoard: tensorboard --logdir {SAVE_DIR / 'tb_logs'}")
        print(f"  2. 评估模型: python scripts/evaluate_ppo.py --model {SAVE_DIR / 'best_model' / 'best_model.zip'}")
        print()

    except KeyboardInterrupt:
        print("\n\n训练被用户中断！")
        print("保存当前模型...")
        model.save(str(SAVE_DIR / "interrupted_model"))
        print(f"模型已保存: {SAVE_DIR / 'interrupted_model'}")

    finally:
        envs.close()
        eval_env.close()
        print("环境已关闭。")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ 训练失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
