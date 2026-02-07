"""
Day6 Test D: 统计验证

运行多个随机种子的长时间测试，验证 MAPF 系统的稳定性和性能。

场景：
- 10 个随机种子 (seeds=0..9)
- 每个运行 500 步
- 3 agents
- K=5, H=40
- 记录统计指标

预期：
- 平均成功率 >= 90%
- 平均 fallback 比例 <= 10%
- 无碰撞
- P95 规划时间在预算内
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_single_test(seed: int, out_dir: Path) -> Dict:
    """
    运行单个测试

    Returns:
        metrics dict
    """
    cmd = [
        "python", "scripts/test_mapf_integration.py",
        "--steps", "500",
        "--K", "5",
        "--H", "40",
        "--n", "3",
        "--seed", str(seed),
        "--budget_ms", "300",
        "--goal_radius", "15",
        "--out_dir", str(out_dir)
    ]

    print(f"  运行 seed={seed}...", end=" ", flush=True)

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=120  # 2分钟超时
        )

        if result.returncode != 0:
            print(f"✗ 失败 (返回码 {result.returncode})")
            print(f"    stderr: {result.stderr[:200]}")
            return None

        # 读取 metrics
        metrics_path = out_dir / "metrics.json"
        if not metrics_path.exists():
            print(f"✗ metrics.json 不存在")
            return None

        with open(metrics_path, 'r') as f:
            metrics = json.load(f)

        print(f"✓ 成功")
        return metrics

    except subprocess.TimeoutExpired:
        print(f"✗ 超时")
        return None
    except Exception as e:
        print(f"✗ 异常: {e}")
        return None


def main():
    print("=" * 80)
    print("Day6 Test D: 统计验证")
    print("=" * 80)
    print()

    # 设置输出目录
    base_out_dir = project_root / "outputs" / "test_statistical"
    base_out_dir.mkdir(parents=True, exist_ok=True)

    print(f"输出目录: {base_out_dir}")
    print()

    # 运行多个种子
    seeds = list(range(10))
    all_metrics = []

    print("运行测试:")
    print("-" * 80)

    for seed in seeds:
        out_dir = base_out_dir / f"seed_{seed}"
        out_dir.mkdir(parents=True, exist_ok=True)

        metrics = run_single_test(seed, out_dir)
        if metrics is not None:
            all_metrics.append(metrics)

    print()
    print(f"完成: {len(all_metrics)}/{len(seeds)} 成功")
    print()

    if len(all_metrics) == 0:
        print("✗ 所有测试都失败")
        sys.exit(1)

    # 统计分析
    print("=" * 80)
    print("统计分析")
    print("=" * 80)

    # 成功率
    success_rates = [m['mapf_success_calls'] / m['mapf_calls'] if m['mapf_calls'] > 0 else 0
                     for m in all_metrics]
    mean_success_rate = sum(success_rates) / len(success_rates)
    min_success_rate = min(success_rates)
    max_success_rate = max(success_rates)

    print(f"MAPF 成功率:")
    print(f"  平均: {mean_success_rate*100:.1f}%")
    print(f"  最小: {min_success_rate*100:.1f}%")
    print(f"  最大: {max_success_rate*100:.1f}%")
    print()

    # Fallback 比例
    fallback_rates = [m['fallback_wait_steps'] / m['steps'] for m in all_metrics]
    mean_fallback_rate = sum(fallback_rates) / len(fallback_rates)
    min_fallback_rate = min(fallback_rates)
    max_fallback_rate = max(fallback_rates)

    print(f"Fallback 比例:")
    print(f"  平均: {mean_fallback_rate*100:.1f}%")
    print(f"  最小: {min_fallback_rate*100:.1f}%")
    print(f"  最大: {max_fallback_rate*100:.1f}%")
    print()

    # 规划时间
    mean_plan_times = [m['mapf_mean_plan_time_ms'] for m in all_metrics]
    p95_plan_times = [m['mapf_p95_plan_time_ms'] for m in all_metrics]

    overall_mean_plan_time = sum(mean_plan_times) / len(mean_plan_times)
    overall_p95_plan_time = max(p95_plan_times)

    print(f"规划时间:")
    print(f"  平均 (跨所有 seeds): {overall_mean_plan_time:.2f} ms")
    print(f"  P95 (最大): {overall_p95_plan_time:.2f} ms")
    print()

    # 展开节点
    if 'expanded_nodes_total' in all_metrics[0]:
        expanded_totals = [m['expanded_nodes_total'] for m in all_metrics]
        expanded_means = [m['mapf_expanded_mean_per_call'] for m in all_metrics]

        overall_expanded_mean = sum(expanded_means) / len(expanded_means)

        print(f"展开节点:")
        print(f"  平均每次调用: {overall_expanded_mean:.1f}")
        print()

    # 移动指标
    if 'mean_step_motion' in all_metrics[0]:
        step_motions = [m['mean_step_motion'] for m in all_metrics]
        overall_step_motion = sum(step_motions) / len(step_motions)

        print(f"移动指标:")
        print(f"  平均每步移动 agent 数: {overall_step_motion:.2f}")
        print()

    # 碰撞检测
    all_collision_free = all(m.get('collision_free', True) for m in all_metrics)
    print(f"碰撞检测:")
    if all_collision_free:
        print(f"  ✓ 所有测试无碰撞")
    else:
        print(f"  ✗ 存在碰撞")
    print()

    # 验收标准
    print("=" * 80)
    print("验收标准")
    print("=" * 80)

    checks = []

    # 1. 平均成功率 >= 90%
    if mean_success_rate >= 0.90:
        print(f"  ✓ 平均成功率 >= 90%: {mean_success_rate*100:.1f}%")
        checks.append(True)
    else:
        print(f"  ✗ 平均成功率 < 90%: {mean_success_rate*100:.1f}%")
        checks.append(False)

    # 2. 平均 fallback 比例 <= 10%
    if mean_fallback_rate <= 0.10:
        print(f"  ✓ 平均 fallback 比例 <= 10%: {mean_fallback_rate*100:.1f}%")
        checks.append(True)
    else:
        print(f"  ✗ 平均 fallback 比例 > 10%: {mean_fallback_rate*100:.1f}%")
        checks.append(False)

    # 3. P95 规划时间在预算内
    budget_ms = 300
    if overall_p95_plan_time <= budget_ms + 10:
        print(f"  ✓ P95 规划时间在预算内: {overall_p95_plan_time:.2f} ms <= {budget_ms + 10} ms")
        checks.append(True)
    else:
        print(f"  ✗ P95 规划时间超出预算: {overall_p95_plan_time:.2f} ms > {budget_ms + 10} ms")
        checks.append(False)

    # 4. 无碰撞
    if all_collision_free:
        print(f"  ✓ 所有测试无碰撞")
        checks.append(True)
    else:
        print(f"  ✗ 存在碰撞")
        checks.append(False)

    # 5. 至少 8/10 测试成功
    if len(all_metrics) >= 8:
        print(f"  ✓ 至少 8/10 测试成功: {len(all_metrics)}/10")
        checks.append(True)
    else:
        print(f"  ✗ 少于 8/10 测试成功: {len(all_metrics)}/10")
        checks.append(False)

    print()

    # 总结
    if all(checks):
        print("✓ Day6 Test D (统计验证) 验收通过")
        print()
        print(f"总结: {len(all_metrics)}/10 测试成功，平均成功率 {mean_success_rate*100:.1f}%，")
        print(f"      平均 fallback {mean_fallback_rate*100:.1f}%，P95 规划时间 {overall_p95_plan_time:.2f} ms")
    else:
        print("✗ Day6 Test D (统计验证) 部分未通过")
        print()
        print(f"注意: 某些指标未达标，但这可能是参数需要调整")

    # 保存汇总统计
    summary = {
        'total_runs': len(seeds),
        'successful_runs': len(all_metrics),
        'mean_success_rate': mean_success_rate,
        'min_success_rate': min_success_rate,
        'max_success_rate': max_success_rate,
        'mean_fallback_rate': mean_fallback_rate,
        'min_fallback_rate': min_fallback_rate,
        'max_fallback_rate': max_fallback_rate,
        'overall_mean_plan_time_ms': overall_mean_plan_time,
        'overall_p95_plan_time_ms': overall_p95_plan_time,
        'all_collision_free': all_collision_free
    }

    if 'expanded_nodes_total' in all_metrics[0]:
        summary['overall_expanded_mean'] = overall_expanded_mean

    if 'mean_step_motion' in all_metrics[0]:
        summary['overall_step_motion'] = overall_step_motion

    summary_path = base_out_dir / "summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print()
    print(f"汇总统计已保存到: {summary_path}")


if __name__ == "__main__":
    main()
