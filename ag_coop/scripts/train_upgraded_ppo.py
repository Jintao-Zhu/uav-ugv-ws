#!/usr/bin/env python3
"""
终极版PPO训练脚本 - UAV独立飞行系统

核心升级：
1. 动作空间扩展：从78种 → 1248种（增加16维UAV飞行控制）
2. 状态空间升级：5D UAV状态（mode, x, y, battery, carrier_id）
3. 训练步数：1.5M步（应对复杂的飞行和电量学习）
4. 高熵探索：ent_coef=0.015（强制UAV起飞探索）
5. 多进程加速：8个并行环境

目标：
- 任务完成数：48-52（超越baseline的44.90）
- 总奖励：35-45（超越Static-Center的29.68）
- Deadline miss：<12（优于当前12.90）
"""

import sys
import os
from pathlib import Path
import yaml
from typing import Callable

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

    # 覆盖地图路径
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


def linear_schedule(initial_value: float) -> Callable[[float], float]:
    """
    线性学习率衰减函数

    从initial_value线性衰减到initial_value/3
    """
    def func(progress_remaining: float) -> float:
        # progress_remaining从1.0（开始）降到0.0（结束）
        return progress_remaining * initial_value + (1 - progress_remaining) * (initial_value / 3)

    return func


def main():
    print("\n" + "="*70)
    print("🚀 终极版PPO训练 - 山区救险地图（Map_02 Bionic）")
    print("="*70)

    # ==================== 1. 核心配置 ====================
    MAP_PATH = "maps/map_02.map"
    N_ENVS = 8                  # 8个并行环境
    TOTAL_TIMESTEPS = 1_500_000 # 1.5M步

    print(f"\n配置:")
    print(f"  - 地图: {MAP_PATH}")
    print(f"  - 并行环境数: {N_ENVS}")
    print(f"  - 总训练步数: {TOTAL_TIMESTEPS:,}")
    print(f"  - 预计训练时间: 3-4小时（取决于硬件）")

    # ==================== 2. 创建并行训练环境 ====================
    print("\n创建并行训练环境...")
    envs = SubprocVecEnv([make_env_wrapper(MAP_PATH, i) for i in range(N_ENVS)])
    envs = VecMonitor(envs)  # 添加Monitor方便TensorBoard记录

    # 创建独立的评估环境
    print("创建评估环境...")
    eval_env = SubprocVecEnv([make_env_wrapper(MAP_PATH, 999)])
    eval_env = VecMonitor(eval_env)

    # ==================== 3. 设置回调函数 ====================
    SAVE_DIR = project_root / "outputs" / "upgraded_ppo_map02"
    SAVE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n模型保存目录: {SAVE_DIR}")

    # 最佳模型保存回调（根据总奖励）
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=str(SAVE_DIR / "best_model"),
        log_path=str(SAVE_DIR),
        eval_freq=10000,  # 每10000步评估一次
        deterministic=True,
        render=False,
        verbose=1
    )

    # 定期检查点保存
    checkpoint_callback = CheckpointCallback(
        save_freq=50000,  # 每50000步保存一次
        save_path=str(SAVE_DIR / "checkpoints"),
        name_prefix="ppo_checkpoint",
        verbose=1
    )

    # ==================== 4. 初始化PPO模型 ====================
    print("\n初始化PPO智能体...")

    policy_kwargs = dict(
        net_arch=[256, 128, 64],  # 增加第一层容量，处理5D UAV状态
    )

    model = PPO(
        "MultiInputPolicy",
        envs,
        learning_rate=linear_schedule(0.0003),  # 线性衰减学习率
        n_steps=2048,           # 每收集2048*8=16384步更新一次
        batch_size=256,         # 更大的Batch Size稳定梯度
        n_epochs=10,
        gamma=0.99,             # 长期折扣因子，考虑电量耗尽的远期惩罚
        ent_coef=0.015,         # 🔥 核心魔法参数：强制探索飞行
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
    print(f"  - 熵系数: 0.015 (强制探索)")
    print(f"  - Batch size: 256")
    print(f"  - N steps: 2048")

    # ==================== 5. 开始训练 ====================
    print("\n" + "="*70)
    print("开始训练！")
    print("="*70)
    print("\n预期训练阶段:")
    print("  阶段1 (0-300k步): 坠机与试错期")
    print("    - 奖励可能跌到-100以下")
    print("    - UAV学习飞行和电量管理")
    print("\n  阶段2 (300k-800k步): 觉醒的空中基站")
    print("    - 奖励开始陡升")
    print("    - 学会充电和通信覆盖")
    print("    - 逼近Static-Center性能（+29.68）")
    print("\n  阶段3 (800k-1.5M步): 超越人类规则")
    print("    - 奖励突破30分大关")
    print("    - 学会预判飞行和动态优化")
    print("    - 目标：35-45分，48-52任务")
    print("\n" + "="*70)

    print("\n启动TensorBoard监控:")
    print(f"  tensorboard --logdir {SAVE_DIR / 'tb_logs'}")
    print()

    try:
        model.learn(
            total_timesteps=TOTAL_TIMESTEPS,
            callback=[eval_callback, checkpoint_callback],
            tb_log_name="PPO_A2G_Joint_Scheduling"
        )

        # ==================== 6. 保存最终模型 ====================
        final_model_path = SAVE_DIR / "final_model"
        model.save(str(final_model_path))

        print("\n" + "="*70)
        print("✅ 训练圆满完成！")
        print("="*70)
        print(f"\n模型保存位置:")
        print(f"  - 最佳模型: {SAVE_DIR / 'best_model'}")
        print(f"  - 最终模型: {final_model_path}")
        print(f"  - 检查点: {SAVE_DIR / 'checkpoints'}")
        print(f"\n下一步:")
        print(f"  1. 查看TensorBoard: tensorboard --logdir {SAVE_DIR / 'tb_logs'}")
        print(f"  2. 评估模型: python scripts/evaluate_ppo.py")
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
