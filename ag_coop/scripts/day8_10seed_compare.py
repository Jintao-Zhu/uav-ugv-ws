#!/usr/bin/env python3
"""
Day8 Step 6.2: 10-Seed 批量对比实验

扩展到 seeds 0-9，输出均值±std，验证 coverage 方法的稳健性。
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


def run_one_seed(config, seed, method, out_dir, enable_relay=False):
    """运行单个 seed"""
    config['episode']['seed'] = seed
    config['mapf']['enabled'] = False

    # 根据方法设置 relay
    if 'relay' not in config:
        config['relay'] = {}
    config['relay']['enabled'] = enable_relay

    # relay UGV 使用 UGV 1（不是 carrier）
    if enable_relay:
        config['relay']['relay_ugv_id'] = 1
        # Day8 Step 6.2 FIX: risk_margin=0 表示只在实际 outage 时触发 relay
        config['relay']['risk_margin'] = 0.0  # 只在 SNR < threshold 时触发

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
        'std': float(np.std(values, ddof=1)),  # 样本标准差
        'min': float(np.min(values)),
        'max': float(np.max(values)),
        'median': float(np.median(values)),
    }


def main():
    print("=" * 70)
    print("Day8 Step 6.2: 10-Seed 批量对比实验")
    print("=" * 70)
    print()

    # 配置
    config_path = "configs/day7_baseline.yaml"
    seeds = list(range(10))  # 0-9
    methods = ["greedy", "coverage"]

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
    print(f"方法: {methods}")
    print(f"SNR 阈值: {base_config['comm']['snr_threshold_db']} dB")
    print()

    # 运行实验
    all_results = []

    for method in methods:
        print(f"运行 {method}...")
        enable_relay = (method == "coverage")

        for seed in seeds:
            config = copy.deepcopy(base_config)
            out_dir = Path('outputs') / f"day8_10seed_{method}_seed{seed}"

            print(f"  seed={seed} (relay={enable_relay})...", end=" ", flush=True)

            metrics = run_one_seed(config, seed, method, out_dir, enable_relay=enable_relay)

            result = {
                'method': method,
                'seed': seed,
                'steps': metrics['steps'],
                'tasks_completed': metrics['tasks_completed'],
                'total_tasks': metrics['total_tasks'],
                'completion_rate': metrics['completion_rate'],
                'deadline_miss': metrics['deadline_miss'],
                'deadline_miss_rate': metrics['deadline_miss_rate'],
                'mean_tardiness': metrics['mean_tardiness'],
                # Day8 Step 5: 使用 nc 指标
                'outage_steps_nc': metrics.get('outage_steps_nc', 0),
                'outage_percent_nc': metrics.get('outage_percent_nc', 0.0),
                'snr_best_nc_mean': metrics.get('snr_best_nc_mean', 0.0),
                'snr_best_nc_min': metrics.get('snr_best_nc_min', 0.0),
                # legacy 指标（用于对照）
                'outage_percent_all': metrics.get('outage_percent', 0.0),
                'snr_best_all_mean': metrics.get('snr_best_mean', 0.0),
                'mean_step_motion': metrics.get('mean_step_motion', 0),
                'runtime_sec': round(metrics['runtime_sec'], 3),
            }
            all_results.append(result)

            print(f"完成 (tasks={result['tasks_completed']}, "
                  f"outage_nc={result['outage_percent_nc']:.1f}%)")

        print()

    # 保存结果
    summary_dir = Path('outputs') / 'day8_10seed_summary'
    summary_dir.mkdir(parents=True, exist_ok=True)

    with open(summary_dir / 'results.json', 'w') as f:
        json.dump(all_results, f, indent=2)

    # 统计分析
    print("=" * 70)
    print("统计分析（10 seeds）")
    print("=" * 70)
    print()

    # 按方法汇总
    greedy_results = [r for r in all_results if r['method'] == 'greedy']
    coverage_results = [r for r in all_results if r['method'] == 'coverage']

    # 提取指标
    metrics_to_analyze = [
        ('tasks_completed', 'Tasks'),
        ('outage_percent_nc', 'Outage_NC%'),
        ('deadline_miss_rate', 'MissRate%'),
        ('mean_step_motion', 'Motion'),
    ]

    stats_summary = {}

    for metric_key, metric_name in metrics_to_analyze:
        greedy_values = [r[metric_key] for r in greedy_results]
        coverage_values = [r[metric_key] for r in coverage_results]

        greedy_stats = compute_stats(greedy_values)
        coverage_stats = compute_stats(coverage_values)

        stats_summary[metric_key] = {
            'greedy': greedy_stats,
            'coverage': coverage_stats,
        }

        print(f"{metric_name}:")
        print(f"  Greedy:   {greedy_stats['mean']:.2f} ± {greedy_stats['std']:.2f} "
              f"[{greedy_stats['min']:.2f}, {greedy_stats['max']:.2f}]")
        print(f"  Coverage: {coverage_stats['mean']:.2f} ± {coverage_stats['std']:.2f} "
              f"[{coverage_stats['min']:.2f}, {coverage_stats['max']:.2f}]")
        print()

    # 计算改善
    print("=" * 70)
    print("改善分析")
    print("=" * 70)
    print()

    greedy_outage_mean = stats_summary['outage_percent_nc']['greedy']['mean']
    coverage_outage_mean = stats_summary['outage_percent_nc']['coverage']['mean']
    outage_abs_reduction = greedy_outage_mean - coverage_outage_mean
    outage_rel_reduction = (outage_abs_reduction / greedy_outage_mean * 100) if greedy_outage_mean > 0 else 0

    greedy_tasks_mean = stats_summary['tasks_completed']['greedy']['mean']
    coverage_tasks_mean = stats_summary['tasks_completed']['coverage']['mean']
    tasks_abs_change = coverage_tasks_mean - greedy_tasks_mean
    tasks_rel_change = (tasks_abs_change / greedy_tasks_mean * 100) if greedy_tasks_mean > 0 else 0

    print(f"Outage_NC 改善:")
    print(f"  绝对降幅: {outage_abs_reduction:+.2f}% ({greedy_outage_mean:.1f}% → {coverage_outage_mean:.1f}%)")
    print(f"  相对降幅: {outage_rel_reduction:+.1f}%")
    print()
    print(f"Tasks 影响:")
    print(f"  绝对变化: {tasks_abs_change:+.2f} ({greedy_tasks_mean:.1f} → {coverage_tasks_mean:.1f})")
    print(f"  相对变化: {tasks_rel_change:+.1f}%")
    print()

    # Per-seed 差值分析
    print("=" * 70)
    print("Per-Seed 差值分析")
    print("=" * 70)
    print()

    print("Δoutage_nc = greedy - coverage (每个 seed):")
    positive_count = 0
    for seed in seeds:
        greedy_outage = next(r['outage_percent_nc'] for r in greedy_results if r['seed'] == seed)
        coverage_outage = next(r['outage_percent_nc'] for r in coverage_results if r['seed'] == seed)
        delta = greedy_outage - coverage_outage
        if delta > 0:
            positive_count += 1
        print(f"  seed={seed}: Δ={delta:+6.2f}% (greedy={greedy_outage:5.1f}%, coverage={coverage_outage:5.1f}%)")

    print()
    print(f"正向改善的 seed 数量: {positive_count}/{len(seeds)}")
    print()

    # 验收标准检查
    print("=" * 70)
    print("验收标准检查")
    print("=" * 70)
    print()

    # 标准 1: Outage 显著降低
    outage_pass = (outage_rel_reduction >= 30) or (outage_abs_reduction >= 5)
    print(f"1. Outage_NC 显著降低 (均值):")
    print(f"   - 相对降幅 ≥30%: {outage_rel_reduction:.1f}% {'✓' if outage_rel_reduction >= 30 else '✗'}")
    print(f"   - 绝对降幅 ≥5%:  {outage_abs_reduction:.1f}% {'✓' if outage_abs_reduction >= 5 else '✗'}")
    print(f"   结果: {'✅ PASS' if outage_pass else '❌ FAIL'}")
    print()

    # 标准 2: Tasks 不塌陷
    tasks_pass = tasks_rel_change >= -20
    print(f"2. Tasks 不塌陷 (下降不超过 20%):")
    print(f"   - 相对变化: {tasks_rel_change:+.1f}%")
    print(f"   结果: {'✅ PASS' if tasks_pass else '❌ FAIL'}")
    print()

    # 标准 3: 大多数 seed 正向改善
    majority_pass = positive_count >= len(seeds) * 0.7  # 至少 70%
    print(f"3. 大多数 seed 正向改善 (≥70%):")
    print(f"   - 正向改善比例: {positive_count}/{len(seeds)} = {positive_count/len(seeds)*100:.0f}%")
    print(f"   结果: {'✅ PASS' if majority_pass else '❌ FAIL'}")
    print()

    # 总体结果
    overall_pass = outage_pass and tasks_pass and majority_pass
    print("=" * 70)
    if overall_pass:
        print("✅✅✅ 验收通过！Coverage 方法在 10-seed 上稳健改善 Outage ✅✅✅")
    else:
        print("❌ 验收未通过")
    print("=" * 70)
    print()

    print(f"详细结果: {summary_dir / 'results.json'}")

    # 保存统计报告
    report = {
        'config': config_path,
        'snr_threshold_db': base_config['comm']['snr_threshold_db'],
        'seeds': seeds,
        'n_seeds': len(seeds),
        'stats': stats_summary,
        'improvement': {
            'outage_abs_reduction': outage_abs_reduction,
            'outage_rel_reduction': outage_rel_reduction,
            'tasks_abs_change': tasks_abs_change,
            'tasks_rel_change': tasks_rel_change,
        },
        'per_seed_analysis': {
            'positive_count': positive_count,
            'positive_ratio': positive_count / len(seeds),
        },
        'acceptance': {
            'outage_pass': outage_pass,
            'tasks_pass': tasks_pass,
            'majority_pass': majority_pass,
            'overall_pass': overall_pass,
        }
    }

    with open(summary_dir / 'stats_report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"统计报告: {summary_dir / 'stats_report.json'}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
