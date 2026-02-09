#!/usr/bin/env python3
"""
Day9 Step 6: Random Policy Smoke Test

Day9 最终验收：使用随机策略运行多个 episodes，验证环境稳定性

验收标准：
1. 连续 10 episodes（不同 seed）全部跑完，无 crash
2. 无 NaN/Inf（obs、reward、关键 metrics）
3. 输出目录完整（metrics.json + rollout.jsonl）
"""

import sys
from pathlib import Path
import yaml
import numpy as np
import json
import argparse
from typing import Dict, Any, List

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.rl import AGCoopGymEnv


def check_for_nan_inf(value, name: str) -> bool:
    """
    检查值是否包含 NaN/Inf

    Args:
        value: 要检查的值（可以是 scalar、array、dict）
        name: 值的名称（用于错误信息）

    Returns:
        True 如果包含 NaN/Inf，False 否则
    """
    if isinstance(value, dict):
        for k, v in value.items():
            if check_for_nan_inf(v, f"{name}.{k}"):
                return True
        return False
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            if check_for_nan_inf(v, f"{name}[{i}]"):
                return True
        return False
    elif isinstance(value, np.ndarray):
        if not np.all(np.isfinite(value)):
            print(f"  ✗ {name} contains NaN/Inf")
            return True
        return False
    elif isinstance(value, (int, float)):
        if not np.isfinite(value):
            print(f"  ✗ {name} = {value} (NaN/Inf)")
            return True
        return False
    else:
        return False


def run_episode(
    env: AGCoopGymEnv,
    seed: int,
    horizon: int,
    dump_dir: Path,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    运行一个 episode（随机策略）

    Args:
        env: 环境
        seed: 随机种子
        horizon: episode 长度
        dump_dir: 输出目录
        verbose: 是否打印详细信息

    Returns:
        metrics 字典
    """
    # 创建输出目录
    dump_dir.mkdir(parents=True, exist_ok=True)

    # Reset
    obs, info = env.reset(seed=seed)

    # 检查初始 obs
    if check_for_nan_inf(obs, "obs[0]"):
        raise ValueError(f"Initial observation contains NaN/Inf")

    # 初始化统计
    total_reward = 0.0
    episode_length = 0
    nan_inf_count = 0

    # Rollout 数据
    rollout_data = []

    # 运行 episode
    for step in range(horizon):
        # 随机采样 action
        action = env.action_space.sample()

        # Step
        result = env.step(action)

        if len(result) == 5:
            obs, reward, terminated, truncated, info = result
            done = terminated or truncated
        else:
            obs, reward, done, info = result
            terminated = done
            truncated = False

        # 检查 NaN/Inf
        has_nan_inf = False
        if check_for_nan_inf(obs, f"obs[{step+1}]"):
            has_nan_inf = True
        if check_for_nan_inf(reward, f"reward[{step+1}]"):
            has_nan_inf = True

        if has_nan_inf:
            nan_inf_count += 1

        # 累积统计
        total_reward += reward
        episode_length += 1

        # 记录 rollout 数据
        rollout_entry = {
            'step': step + 1,
            'action': action.tolist() if isinstance(action, np.ndarray) else action,
            'reward': float(reward),
            'done': bool(done),
            'timestep': info.get('timestep', step + 1),
            'tasks_completed': info.get('tasks_completed', 0),
            'deadline_miss': info.get('deadline_miss', 0),
            'outage_steps': info.get('outage_steps', 0),
        }

        # 添加 reward components（如果有）
        if 'reward_components' in info:
            rollout_entry['reward_components'] = {
                k: float(v) for k, v in info['reward_components'].items()
            }

        rollout_data.append(rollout_entry)

        if verbose and (step + 1) % 100 == 0:
            print(f"  Step {step + 1}/{horizon}, reward: {reward:.4f}, total_reward: {total_reward:.4f}")

        if done:
            if verbose:
                print(f"  Episode 结束于 step {step + 1}")
            break

    # 获取最终 metrics
    final_state = env.unwrapped.state
    final_metrics_dict = env.unwrapped.get_metrics()

    # 构建 metrics 字典（对齐 Day7/Day8 格式）
    metrics = {
        # Episode 信息
        'seed': seed,
        'steps': episode_length,
        'horizon': horizon,
        'K': env.unwrapped.config.get('rl', {}).get('decision_period_K', 5),
        'n_agents': env.unwrapped.config.get('robots', {}).get('n_ugv', 3) + env.unwrapped.config.get('robots', {}).get('n_uav', 1),

        # RL 特定
        'total_reward': float(total_reward),
        'mean_reward': float(total_reward / episode_length) if episode_length > 0 else 0.0,

        # Task metrics
        'tasks_completed': final_state.tasks_completed,
        'deadline_miss': final_state.deadline_miss,
        'deadline_miss_rate': final_metrics_dict.get('deadline_miss_rate', 0.0),
        'mean_tardiness': final_metrics_dict.get('mean_tardiness', 0.0),
        'completion_rate': final_metrics_dict.get('completion_rate', 0.0),

        # Communication metrics
        'outage_steps': final_state.outage_steps,
        'outage_percent_worst_nc': final_metrics_dict.get('outage_percent_worst_nc', 0.0),
        'snr_best_nc_mean': final_metrics_dict.get('snr_best_nc_mean', 0.0),
        'snr_best_nc_min': final_metrics_dict.get('snr_best_nc_min', 0.0),

        # MAPF metrics（如果有）
        'mapf_calls': final_metrics_dict.get('mapf_calls', 0),
        'mapf_success': final_metrics_dict.get('mapf_success', 0),
        'mapf_timeout': final_metrics_dict.get('mapf_timeout', 0),
        'mapf_success_rate': final_metrics_dict.get('mapf_success_rate', 0.0),

        # 验收相关
        'nan_inf_count': nan_inf_count,
        'crashed': False,
    }

    # 保存 metrics.json
    metrics_path = dump_dir / 'metrics.json'
    with open(metrics_path, 'w') as f:
        json.dump(metrics, f, indent=2)

    # 保存 rollout.jsonl
    rollout_path = dump_dir / 'rollout.jsonl'
    with open(rollout_path, 'w') as f:
        for entry in rollout_data:
            f.write(json.dumps(entry) + '\n')

    if verbose:
        print(f"  Saved metrics to {metrics_path}")
        print(f"  Saved rollout to {rollout_path}")

    return metrics


def print_obs_structure(env: AGCoopGymEnv):
    """打印 observation 结构"""
    print("=" * 70)
    print("Observation Structure")
    print("=" * 70)
    print()

    obs_space = env.observation_space

    if hasattr(obs_space, 'spaces'):
        # Dict observation space
        print("Observation Space: Dict")
        print()
        for key in sorted(obs_space.spaces.keys()):
            space = obs_space[key]
            print(f"  {key}:")
            print(f"    shape: {space.shape}")
            print(f"    dtype: {space.dtype}")
            print(f"    low: {space.low.min()}")
            print(f"    high: {space.high.max()}")
    else:
        # Box observation space
        print("Observation Space: Box")
        print(f"  shape: {obs_space.shape}")
        print(f"  dtype: {obs_space.dtype}")
        print(f"  low: {obs_space.low.min()}")
        print(f"  high: {obs_space.high.max()}")

    print()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Day9 Random Policy Smoke Test')
    parser.add_argument('--config', type=str, default='configs/day7_baseline.yaml',
                        help='配置文件路径')
    parser.add_argument('--seed', type=int, default=1000,
                        help='起始随机种子')
    parser.add_argument('--episodes', type=int, default=10,
                        help='运行的 episode 数量')
    parser.add_argument('--horizon', type=int, default=None,
                        help='Episode 长度（默认使用配置文件中的值）')
    parser.add_argument('--dump_dir', type=str, default='outputs/day9_random',
                        help='输出目录')
    parser.add_argument('--verbose', action='store_true',
                        help='打印详细信息')

    args = parser.parse_args()

    # 加载配置
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 设置 horizon
    if args.horizon is not None:
        config['episode']['horizon_steps'] = args.horizon
    horizon = config['episode']['horizon_steps']

    print("=" * 70)
    print("Day9 Step 6: Random Policy Smoke Test")
    print("=" * 70)
    print(f"配置文件: {args.config}")
    print(f"起始种子: {args.seed}")
    print(f"Episode 数量: {args.episodes}")
    print(f"Horizon: {horizon}")
    print(f"输出目录: {args.dump_dir}")
    print()

    # 创建环境（用于打印 obs 结构）
    print("创建环境...")
    env = AGCoopGymEnv(config, enable_logging=False)
    print()

    # 打印 observation 结构
    print_obs_structure(env)

    # 运行多个 episodes
    print("=" * 70)
    print("运行 Episodes")
    print("=" * 70)
    print()

    all_metrics = []
    crash_count = 0
    nan_inf_episodes = 0

    for i in range(args.episodes):
        seed = args.seed + i
        dump_dir = Path(args.dump_dir) / f"seed{seed}"

        print(f"Episode {i+1}/{args.episodes} (seed={seed})")

        try:
            # 运行 episode
            metrics = run_episode(env, seed, horizon, dump_dir, verbose=args.verbose)

            # 检查 NaN/Inf
            if metrics['nan_inf_count'] > 0:
                nan_inf_episodes += 1
                print(f"  ⚠ Episode 包含 {metrics['nan_inf_count']} 个 NaN/Inf")

            # 打印关键指标
            print(f"  ✓ Episode 完成")
            print(f"    Steps: {metrics['steps']}")
            print(f"    Total reward: {metrics['total_reward']:.4f}")
            print(f"    Tasks completed: {metrics['tasks_completed']}")
            print(f"    Deadline miss rate: {metrics['deadline_miss_rate']:.2f}%")
            print(f"    Outage percent (worst_nc): {metrics['outage_percent_worst_nc']:.2f}%")
            print()

            all_metrics.append(metrics)

        except Exception as e:
            crash_count += 1
            print(f"  ✗ Episode 崩溃: {e}")
            import traceback
            traceback.print_exc()
            print()

            # 记录崩溃
            metrics = {
                'seed': seed,
                'crashed': True,
                'error': str(e),
            }
            all_metrics.append(metrics)

    # 关闭环境
    env.close()

    # 汇总统计
    print("=" * 70)
    print("汇总统计")
    print("=" * 70)
    print()

    print(f"总 episodes: {args.episodes}")
    print(f"成功完成: {args.episodes - crash_count}")
    print(f"崩溃: {crash_count}")
    print(f"包含 NaN/Inf: {nan_inf_episodes}")
    print()

    if crash_count == 0 and nan_inf_episodes == 0:
        # 计算平均指标
        successful_metrics = [m for m in all_metrics if not m.get('crashed', False)]

        if successful_metrics:
            avg_reward = np.mean([m['total_reward'] for m in successful_metrics])
            avg_tasks = np.mean([m['tasks_completed'] for m in successful_metrics])
            avg_miss_rate = np.mean([m['deadline_miss_rate'] for m in successful_metrics])
            avg_outage = np.mean([m['outage_percent_worst_nc'] for m in successful_metrics])

            print("平均指标:")
            print(f"  Total reward: {avg_reward:.4f}")
            print(f"  Tasks completed: {avg_tasks:.2f}")
            print(f"  Deadline miss rate: {avg_miss_rate:.2f}%")
            print(f"  Outage percent (worst_nc): {avg_outage:.2f}%")
            print()

    # 保存汇总 metrics
    summary_path = Path(args.dump_dir) / 'summary.json'
    summary = {
        'config': args.config,
        'seed_start': args.seed,
        'episodes': args.episodes,
        'horizon': horizon,
        'crash_count': crash_count,
        'nan_inf_episodes': nan_inf_episodes,
        'all_metrics': all_metrics,
    }

    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"汇总保存到: {summary_path}")
    print()

    # 验收结果
    print("=" * 70)
    print("Day9 Step 6 验收结果")
    print("=" * 70)
    print()

    print(f"1. 连续 {args.episodes} episodes 全部跑完: {'✅' if crash_count == 0 else '❌'}")
    print(f"2. 无 NaN/Inf: {'✅' if nan_inf_episodes == 0 else '❌'}")
    print(f"3. 输出目录完整: {'✅' if crash_count == 0 else '❌'}")
    print()

    if crash_count == 0 and nan_inf_episodes == 0:
        print("✅✅✅ Day9 Step 6 验收通过！✅✅✅")
        sys.exit(0)
    else:
        print("❌ Day9 Step 6 验收失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
