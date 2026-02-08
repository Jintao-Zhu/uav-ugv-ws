#!/usr/bin/env python3
"""
Day8 Step 6.3: Communication-Aware Greedy 10-Seed 批量实验

测试不同 λ 值对通信质量的影响
"""

import sys
import json
import yaml
from pathlib import Path
import copy
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.env.core import AGCoopEnv
from agcoop.utils.seeding import seed_everything


def run_one_seed(config, seed, method, lambda_val, out_dir):
    """运行单个 seed"""
    config['episode']['seed'] = seed
    config['mapf']['enabled'] = False

    # 设置 comm_greedy 参数
    if method == "comm_greedy":
        if 'comm_greedy' not in config:
            config['comm_greedy'] = {}
        config['comm_greedy']['lambda'] = lambda_val
        config['comm_greedy']['radius'] = 8.0

    seed_everything(seed)

    env = AGCoopEnv(
        config,
        output_dir=str(out_dir),
        enable_logging=True,
        method=method,
        planner="none"
    )

    state = env.reset()

    step_count = 0
    done = False
    while not done:
        state, reward, done, info = env.step()
        step_count += 1

    env.close()

    # 加载 metrics
    with open(Path(out_dir) / "metrics.json") as f:
        metrics = json.load(f)

    return metrics


def compute_stats(values):
    """计算统计量"""
    values = np.array(values)
    return {
        'mean': float(np.mean(values)),
        'std': float(np.std(values, ddof=1)),
        'min': float(np.min(values)),
        'max': float(np.max(values)),
    }


def main():
    print("=" * 70)
    print("Day8 Step 6.3: Communication-Aware Greedy 10-Seed 批量实验")
    print("=" * 70)
    print()

    # 配置
    config_path = "configs/day7_baseline.yaml"
    seeds = list(range(10))  # 0-9
    lambdas = [0.0, 1.0, 2.0, 5.0, 10.0]

    # 加载基础配置
    with open(config_path) as f:
        base_config = yaml.safe_load(f)

    # 调整通信参数
    base_config['comm']['enabled'] = True
    base_config['comm']['snr_threshold_db'] = -12.0
    base_config['comm']['tx_power_db'] = -6.0

    print(f"配置文件: {config_path}")
    print(f"地图: {base_config['episode']['map_path']}")
    print(f"Seeds: {seeds}")
    print(f"λ 值: {lambdas}")
    print(f"SNR 阈值: {base_config['comm']['snr_threshold_db']} dB")
    print()

    # 运行实验
    all_results = []

    for lambda_val in lambdas:
        print(f"运行 λ={lambda_val}...")

        for seed in seeds:
            config = copy.deepcopy(base_config)
            out_dir = Path('outputs') / f"day8_comm_greedy_lambda{lambda_val}_seed{seed}"

            print(f"  seed={seed}...", end=" ", flush=True)

            metrics = run_one_seed(config, seed, "comm_greedy", lambda_val, out_dir)

            result = {
                'lambda': lambda_val,
                'seed': seed,
                'steps': metrics['steps'],
                'tasks_completed': metrics['tasks_completed'],
                'total_tasks': metrics['total_tasks'],
                'completion_rate': metrics['completion_rate'],
                'deadline_miss': metrics['deadline_miss'],
                'deadline_miss_rate': metrics['deadline_miss_rate'],
                'outage_steps_nc': metrics.get('outage_steps_nc', 0),
                'outage_percent_nc': metrics.get('outage_percent_nc', 0.0),
                'snr_best_nc_mean': metrics.get('snr_best_nc_mean', 0.0),
                'mean_step_motion': metrics.get('mean_step_motion', 0),
                'runtime_sec': round(metrics['runtime_sec'], 3),
            }
            all_results.append(result)

            print(f"完成 (tasks={result['tasks_completed']}, "
                  f"outage_nc={result['outage_percent_nc']:.1f}%)")

        print()

    # 保存结果
    summary_dir = Path('outputs') / 'day8_comm_greedy_summary'
    summary_dir.mkdir(parents=True, exist_ok=True)

    with open(summary_dir / 'results.json', 'w') as f:
        json.dump(all_results, f, indent=2)

    # 统计分析
    print("=" * 70)
    print("统计分析（10 seeds × {} λ 值）".format(len(lambdas)))
    print("=" * 70)
    print()

    # 按 λ 汇总
    stats_by_lambda = {}

    for lambda_val in lambdas:
        lambda_results = [r for r in all_results if r['lambda'] == lambda_val]

        # 提取指标
        tasks = [r['tasks_completed'] for r in lambda_results]
        outage_nc = [r['outage_percent_nc'] for r in lambda_results]
        miss_rate = [r['deadline_miss_rate'] for r in lambda_results]
        motion = [r['mean_step_motion'] for r in lambda_results]

        stats_by_lambda[lambda_val] = {
            'tasks': compute_stats(tasks),
            'outage_nc': compute_stats(outage_nc),
            'miss_rate': compute_stats(miss_rate),
            'motion': compute_stats(motion),
        }

        print(f"λ = {lambda_val}:")
        print(f"  Tasks:      {stats_by_lambda[lambda_val]['tasks']['mean']:.2f} ± "
              f"{stats_by_lambda[lambda_val]['tasks']['std']:.2f}")
        print(f"  Outage_NC:  {stats_by_lambda[lambda_val]['outage_nc']['mean']:.2f}% ± "
              f"{stats_by_lambda[lambda_val]['outage_nc']['std']:.2f}%")
        print(f"  Miss Rate:  {stats_by_lambda[lambda_val]['miss_rate']['mean']:.2f}% ± "
              f"{stats_by_lambda[lambda_val]['miss_rate']['std']:.2f}%")
        print(f"  Motion:     {stats_by_lambda[lambda_val]['motion']['mean']:.2f} ± "
              f"{stats_by_lambda[lambda_val]['motion']['std']:.2f}")
        print()

    # Trade-off 分析
    print("=" * 70)
    print("Trade-off 分析（相对于 λ=0 baseline）")
    print("=" * 70)
    print()

    baseline_outage = stats_by_lambda[0.0]['outage_nc']['mean']
    baseline_tasks = stats_by_lambda[0.0]['tasks']['mean']

    print(f"Baseline (λ=0): Outage_NC={baseline_outage:.2f}%, Tasks={baseline_tasks:.2f}")
    print()

    best_lambda = None
    best_improvement = -float('inf')

    for lambda_val in lambdas[1:]:  # 跳过 λ=0
        outage = stats_by_lambda[lambda_val]['outage_nc']['mean']
        tasks = stats_by_lambda[lambda_val]['tasks']['mean']

        outage_reduction = baseline_outage - outage
        outage_rel_reduction = (outage_reduction / baseline_outage * 100) if baseline_outage > 0 else 0
        tasks_change = tasks - baseline_tasks
        tasks_rel_change = (tasks_change / baseline_tasks * 100) if baseline_tasks > 0 else 0

        print(f"λ = {lambda_val}:")
        print(f"  Outage_NC: {baseline_outage:.2f}% → {outage:.2f}% "
              f"({outage_reduction:+.2f}%, {outage_rel_reduction:+.1f}%)")
        print(f"  Tasks:     {baseline_tasks:.2f} → {tasks:.2f} "
              f"({tasks_change:+.2f}, {tasks_rel_change:+.1f}%)")

        # 检查是否满足验收标准
        if outage_reduction >= 5.0 and tasks_rel_change >= -10.0:
            print(f"  ✅ 满足验收标准 (outage ↓≥5%, tasks ↓≤10%)")
            if outage_reduction > best_improvement:
                best_improvement = outage_reduction
                best_lambda = lambda_val
        else:
            print(f"  ❌ 未满足验收标准")
        print()

    # 验收结果
    print("=" * 70)
    print("验收结果")
    print("=" * 70)
    print()

    if best_lambda is not None:
        print(f"✅✅✅ 验收通过！")
        print(f"最佳参数: λ = {best_lambda}")
        print(f"Outage_NC 改善: {best_improvement:.2f}% (绝对降幅)")
        print(f"Tasks 影响: {stats_by_lambda[best_lambda]['tasks']['mean'] - baseline_tasks:+.2f}")
    else:
        print(f"❌ 验收未通过")
        print(f"所有 λ 值都未满足验收标准（outage ↓≥5% 且 tasks ↓≤10%）")

    print()
    print("=" * 70)
    print()

    print(f"详细结果: {summary_dir / 'results.json'}")

    # 保存统计报告
    report = {
        'config': config_path,
        'snr_threshold_db': base_config['comm']['snr_threshold_db'],
        'seeds': seeds,
        'lambdas': lambdas,
        'stats_by_lambda': stats_by_lambda,
        'baseline': {
            'outage_nc': baseline_outage,
            'tasks': baseline_tasks,
        },
        'best_lambda': best_lambda,
        'best_improvement': best_improvement if best_lambda is not None else None,
    }

    with open(summary_dir / 'stats_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"统计报告: {summary_dir / 'stats_report.json'}")

    return 0 if best_lambda is not None else 1


if __name__ == "__main__":
    sys.exit(main())
