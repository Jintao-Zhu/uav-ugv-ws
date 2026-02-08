#!/usr/bin/env python3
"""
Day8 Step 6.7: 完整实验矩阵

运行完整的 trade-off 实验：
- 场景：均匀 + 双热点
- 方法：greedy + comm-aware v2
- Seeds: 0-9
- λ: 0, 0.2, 0.5, 1.0

输出：
- Trade-off 曲线数据
- 统计分析报告
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


def run_one_experiment(config, seed, method, lambda_val, scenario, out_dir):
    """运行单个实验"""
    config['episode']['seed'] = seed
    config['mapf']['enabled'] = False

    # 设置 comm_greedy 参数
    if method == "comm_greedy":
        if 'comm_greedy' not in config:
            config['comm_greedy'] = {}
        config['comm_greedy']['lambda'] = lambda_val
        config['comm_greedy']['margin'] = 3.0

    seed_everything(seed)

    env = AGCoopEnv(
        config,
        output_dir=str(out_dir),
        enable_logging=True,
        method=method,
        planner="none"
    )

    state = env.reset()
    done = False
    while not done:
        state, reward, done, info = env.step()
    env.close()

    # 加载 metrics
    with open(Path(out_dir) / "metrics.json") as f:
        metrics = json.load(f)

    return {
        'scenario': scenario,
        'method': method,
        'lambda': lambda_val,
        'seed': seed,
        'tasks_completed': metrics['tasks_completed'],
        'total_tasks': metrics['total_tasks'],
        'completion_rate': metrics['completion_rate'],
        'deadline_miss_rate': metrics['deadline_miss_rate'],
        'outage_percent_nc': metrics['outage_percent_nc'],
        'outage_percent_worst_nc': metrics['outage_percent_worst_nc'],
        'snr_best_nc_mean': metrics['snr_best_nc_mean'],
        'snr_worst_nc_mean': metrics['snr_worst_nc_mean'],
        'mean_step_motion': metrics['mean_step_motion'],
    }


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
    print("Day8 Step 6.7: 完整实验矩阵")
    print("=" * 70)
    print()

    # 配置
    config_path = "configs/day7_baseline.yaml"
    seeds = list(range(10))  # 0-9
    lambdas = [0.0, 0.2, 0.5, 1.0]
    scenarios = ['uniform', 'dual_hotspot']

    # 加载基础配置
    with open(config_path) as f:
        base_config = yaml.safe_load(f)

    base_config['comm']['enabled'] = True
    base_config['comm']['snr_threshold_db'] = -12.0
    base_config['comm']['tx_power_db'] = -6.0

    print(f"配置文件: {config_path}")
    print(f"Seeds: {seeds}")
    print(f"λ 值: {lambdas}")
    print(f"场景: {scenarios}")
    print()

    # 运行实验
    all_results = []

    for scenario in scenarios:
        print(f"\n{'='*70}")
        print(f"场景: {scenario}")
        print(f"{'='*70}\n")

        # 配置场景
        if scenario == 'dual_hotspot':
            scenario_config = copy.deepcopy(base_config)
            scenario_config['dual_hotspot'] = {
                'enabled': True,
                'hotspot1_center': [2, 2],
                'hotspot2_center': [17, 17],
                'hotspot_radius': 3,
                'split_ratio': 0.5,
            }
        else:
            scenario_config = copy.deepcopy(base_config)

        # 运行 greedy baseline
        print(f"运行 greedy baseline...")
        for seed in seeds:
            config = copy.deepcopy(scenario_config)
            out_dir = Path('outputs') / f"day8_final_{scenario}_greedy_seed{seed}"

            print(f"  seed={seed}...", end=" ", flush=True)

            result = run_one_experiment(config, seed, "greedy", 0.0, scenario, out_dir)
            all_results.append(result)

            print(f"完成 (tasks={result['tasks_completed']}, "
                  f"outage_worst={result['outage_percent_worst_nc']:.1f}%)")

        print()

        # 运行 comm-aware greedy v2
        for lambda_val in lambdas:
            if lambda_val == 0.0:
                continue  # 已经在 greedy 中运行过了

            print(f"运行 comm-aware v2 (λ={lambda_val})...")
            for seed in seeds:
                config = copy.deepcopy(scenario_config)
                out_dir = Path('outputs') / f"day8_final_{scenario}_comm_lambda{lambda_val}_seed{seed}"

                print(f"  seed={seed}...", end=" ", flush=True)

                result = run_one_experiment(config, seed, "comm_greedy", lambda_val, scenario, out_dir)
                all_results.append(result)

                print(f"完成 (tasks={result['tasks_completed']}, "
                      f"outage_worst={result['outage_percent_worst_nc']:.1f}%)")

            print()

    # 保存结果
    summary_dir = Path('outputs') / 'day8_final_summary'
    summary_dir.mkdir(parents=True, exist_ok=True)

    with open(summary_dir / 'results.json', 'w') as f:
        json.dump(all_results, f, indent=2)

    print("\n" + "=" * 70)
    print("统计分析")
    print("=" * 70 + "\n")

    # 按场景和 λ 汇总
    for scenario in scenarios:
        print(f"\n{'='*70}")
        print(f"场景: {scenario.upper()}")
        print(f"{'='*70}\n")

        scenario_results = [r for r in all_results if r['scenario'] == scenario]

        # 按 λ 分组
        lambda_groups = {}
        for lambda_val in [0.0] + lambdas:
            if lambda_val == 0.0:
                # greedy
                group_results = [r for r in scenario_results if r['method'] == 'greedy']
            else:
                # comm-aware
                group_results = [r for r in scenario_results
                               if r['method'] == 'comm_greedy' and r['lambda'] == lambda_val]

            if not group_results:
                continue

            # 提取指标
            tasks = [r['tasks_completed'] for r in group_results]
            outage_worst = [r['outage_percent_worst_nc'] for r in group_results]
            outage_best = [r['outage_percent_nc'] for r in group_results]
            miss_rate = [r['deadline_miss_rate'] for r in group_results]

            lambda_groups[lambda_val] = {
                'tasks': compute_stats(tasks),
                'outage_worst_nc': compute_stats(outage_worst),
                'outage_best_nc': compute_stats(outage_best),
                'miss_rate': compute_stats(miss_rate),
            }

            method_name = "Greedy" if lambda_val == 0.0 else f"Comm-Aware (λ={lambda_val})"
            print(f"{method_name}:")
            print(f"  Tasks:           {lambda_groups[lambda_val]['tasks']['mean']:.2f} ± "
                  f"{lambda_groups[lambda_val]['tasks']['std']:.2f}")
            print(f"  Outage_worst_NC: {lambda_groups[lambda_val]['outage_worst_nc']['mean']:.2f}% ± "
                  f"{lambda_groups[lambda_val]['outage_worst_nc']['std']:.2f}%")
            print(f"  Outage_best_NC:  {lambda_groups[lambda_val]['outage_best_nc']['mean']:.2f}% ± "
                  f"{lambda_groups[lambda_val]['outage_best_nc']['std']:.2f}%")
            print(f"  Miss Rate:       {lambda_groups[lambda_val]['miss_rate']['mean']:.2f}% ± "
                  f"{lambda_groups[lambda_val]['miss_rate']['std']:.2f}%")
            print()

        # Trade-off 分析
        print(f"\nTrade-off 分析 ({scenario}):")
        print("-" * 70)

        baseline_outage = lambda_groups[0.0]['outage_worst_nc']['mean']
        baseline_tasks = lambda_groups[0.0]['tasks']['mean']

        print(f"Baseline (greedy): outage_worst={baseline_outage:.2f}%, tasks={baseline_tasks:.2f}")
        print()

        for lambda_val in lambdas:
            if lambda_val == 0.0 or lambda_val not in lambda_groups:
                continue

            outage = lambda_groups[lambda_val]['outage_worst_nc']['mean']
            tasks = lambda_groups[lambda_val]['tasks']['mean']

            outage_change = outage - baseline_outage
            tasks_change = tasks - baseline_tasks

            print(f"λ={lambda_val}:")
            print(f"  Outage_worst: {baseline_outage:.2f}% → {outage:.2f}% ({outage_change:+.2f}%)")
            print(f"  Tasks:        {baseline_tasks:.2f} → {tasks:.2f} ({tasks_change:+.2f})")
            print()

    # 保存统计报告
    report = {
        'config': config_path,
        'seeds': seeds,
        'lambdas': lambdas,
        'scenarios': scenarios,
        'results_count': len(all_results),
    }

    with open(summary_dir / 'stats_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 70)
    print("实验完成！")
    print("=" * 70)
    print(f"\n详细结果: {summary_dir / 'results.json'}")
    print(f"统计报告: {summary_dir / 'stats_report.json'}")
    print()
    print("下一步：使用这些数据绘制 trade-off 曲线")
    print("  - X 轴: tasks_completed 或 miss_rate")
    print("  - Y 轴: outage_worst_nc")
    print("  - 不同 λ 的点形成曲线")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
