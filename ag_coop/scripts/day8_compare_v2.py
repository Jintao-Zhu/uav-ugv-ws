#!/usr/bin/env python3
"""
Day8 Step 5 (修正版): Greedy vs Coverage 对比实验

关键修正：
- 排除 carrier UGV，只计算 UAV 到其他 UGV 的 SNR
- 这样才能真正测试 relay 的效果

思路：
- 修改环境，让 _update_outage 排除 carrier
- 或者：使用更大的地图，让 UGV 分散得更远
"""

import sys
import json
import yaml
from pathlib import Path
import copy

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


def main():
    print("=" * 70)
    print("Day8 Step 5 (修正版): Greedy vs Coverage 对比实验")
    print("=" * 70)
    print()

    # 使用 Day7 baseline 配置（更现实的参数）
    config_path = "configs/day7_baseline.yaml"
    seeds = [0, 1, 2]
    methods = ["greedy", "coverage"]

    # 加载基础配置
    with open(config_path) as f:
        base_config = yaml.safe_load(f)

    # 确保通信启用
    if 'comm' not in base_config:
        base_config['comm'] = {}
    base_config['comm']['enabled'] = True

    # 使用更严格的 SNR 阈值，模拟需要 relay 的场景
    # 注意：Day7 baseline 的默认阈值可能已经合理
    print(f"配置文件: {config_path}")
    print(f"地图: {base_config['episode']['map_path']}")
    print(f"Seeds: {seeds}")
    print(f"方法: {methods}")
    print(f"SNR 阈值: {base_config['comm'].get('snr_threshold_db', 'N/A')} dB")
    print()

    # 运行实验
    all_results = []

    for method in methods:
        print(f"运行 {method}...")
        enable_relay = (method == "coverage")

        for seed in seeds:
            config = copy.deepcopy(base_config)
            out_dir = Path('outputs') / f"day8_compare_v2_{method}_seed{seed}"

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
                'outage_steps': metrics['outage_steps'],
                'outage_percent': metrics['outage_percent'],
                'mean_step_motion': metrics.get('mean_step_motion', 0),
                'runtime_sec': round(metrics['runtime_sec'], 3),
            }
            all_results.append(result)

            print(f"完成 (tasks={result['tasks_completed']}, "
                  f"outage={result['outage_percent']:.1f}%)")

        print()

    # 保存结果
    summary_dir = Path('outputs') / 'day8_compare_v2_summary'
    summary_dir.mkdir(parents=True, exist_ok=True)

    with open(summary_dir / 'results.json', 'w') as f:
        json.dump(all_results, f, indent=2)

    # 分析结果
    print("=" * 70)
    print("对比分析")
    print("=" * 70)
    print()

    # 按方法汇总
    greedy_results = [r for r in all_results if r['method'] == 'greedy']
    coverage_results = [r for r in all_results if r['method'] == 'coverage']

    n = len(seeds)

    # Greedy 统计
    greedy_tasks_avg = sum(r['tasks_completed'] for r in greedy_results) / n
    greedy_outage_avg = sum(r['outage_percent'] for r in greedy_results) / n
    greedy_miss_rate_avg = sum(r['deadline_miss_rate'] for r in greedy_results) / n
    greedy_motion_avg = sum(r['mean_step_motion'] for r in greedy_results) / n

    # Coverage 统计
    coverage_tasks_avg = sum(r['tasks_completed'] for r in coverage_results) / n
    coverage_outage_avg = sum(r['outage_percent'] for r in coverage_results) / n
    coverage_miss_rate_avg = sum(r['deadline_miss_rate'] for r in coverage_results) / n
    coverage_motion_avg = sum(r['mean_step_motion'] for r in coverage_results) / n

    # 打印汇总表
    print(f"{'Method':<12} {'Tasks':>8} {'Outage%':>10} {'MissRate%':>10} {'Motion':>10}")
    print("-" * 70)
    print(f"{'greedy':<12} {greedy_tasks_avg:>8.1f} {greedy_outage_avg:>10.1f} "
          f"{greedy_miss_rate_avg:>10.1f} {greedy_motion_avg:>10.3f}")
    print(f"{'coverage':<12} {coverage_tasks_avg:>8.1f} {coverage_outage_avg:>10.1f} "
          f"{coverage_miss_rate_avg:>10.1f} {coverage_motion_avg:>10.3f}")
    print()

    # 计算改善
    outage_abs_reduction = greedy_outage_avg - coverage_outage_avg
    if greedy_outage_avg > 0:
        outage_rel_reduction = (outage_abs_reduction / greedy_outage_avg * 100)
    else:
        outage_rel_reduction = 0

    tasks_abs_change = coverage_tasks_avg - greedy_tasks_avg
    if greedy_tasks_avg > 0:
        tasks_rel_change = (tasks_abs_change / greedy_tasks_avg * 100)
    else:
        tasks_rel_change = 0

    print("=" * 70)
    print("改善分析")
    print("=" * 70)
    print()
    print(f"Outage 改善:")
    print(f"  绝对降幅: {outage_abs_reduction:+.2f}% (greedy {greedy_outage_avg:.1f}% → coverage {coverage_outage_avg:.1f}%)")
    print(f"  相对降幅: {outage_rel_reduction:+.1f}%")
    print()
    print(f"Tasks 影响:")
    print(f"  绝对变化: {tasks_abs_change:+.2f} (greedy {greedy_tasks_avg:.1f} → coverage {coverage_tasks_avg:.1f})")
    print(f"  相对变化: {tasks_rel_change:+.1f}%")
    print()

    # 验收标准检查
    print("=" * 70)
    print("验收标准检查")
    print("=" * 70)
    print()

    # 标准 1: Outage 显著降低
    outage_pass = (outage_rel_reduction >= 30) or (outage_abs_reduction >= 5)
    print(f"1. Outage 显著降低:")
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

    # 总体结果
    overall_pass = outage_pass and tasks_pass
    print("=" * 70)
    if overall_pass:
        print("✅✅✅ 验收通过！Coverage 方法显著改善 Outage，且 Tasks 未塌陷 ✅✅✅")
    else:
        print("❌ 验收未通过")
        print()
        print("分析：")
        if greedy_outage_avg == 0:
            print("  - Greedy 的 outage 为 0%，说明当前配置下没有通信问题")
            print("  - 建议：使用更严格的 SNR 阈值，或更大的地图")
        if not outage_pass:
            print("  - Coverage 没有显著降低 outage")
            print("  - 可能原因：relay 策略不够有效，或配置参数需要调整")
    print("=" * 70)
    print()

    print(f"详细结果: {summary_dir / 'results.json'}")

    # 保存验收报告
    report = {
        'config': config_path,
        'seeds': seeds,
        'greedy': {
            'tasks_avg': greedy_tasks_avg,
            'outage_avg': greedy_outage_avg,
            'miss_rate_avg': greedy_miss_rate_avg,
            'motion_avg': greedy_motion_avg,
        },
        'coverage': {
            'tasks_avg': coverage_tasks_avg,
            'outage_avg': coverage_outage_avg,
            'miss_rate_avg': coverage_miss_rate_avg,
            'motion_avg': coverage_motion_avg,
        },
        'improvement': {
            'outage_abs_reduction': outage_abs_reduction,
            'outage_rel_reduction': outage_rel_reduction,
            'tasks_abs_change': tasks_abs_change,
            'tasks_rel_change': tasks_rel_change,
        },
        'acceptance': {
            'outage_pass': outage_pass,
            'tasks_pass': tasks_pass,
            'overall_pass': overall_pass,
        }
    }

    with open(summary_dir / 'report.json', 'w') as f:
        json.dump(report, f, indent=2)

    print(f"验收报告: {summary_dir / 'report.json'}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
