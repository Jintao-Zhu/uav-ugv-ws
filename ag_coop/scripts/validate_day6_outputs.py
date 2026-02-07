"""
Day6 Step 8: 输出验证脚本

验证 metrics 和 trace 的完整性和正确性。

用法:
    python scripts/validate_day6_outputs.py --dir outputs/.../
"""

import sys
import json
import argparse
from pathlib import Path


def validate_metrics(metrics_path: str) -> bool:
    """验证 metrics.json"""
    print("验证 metrics.json:")

    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    # 必需字段
    required_fields = [
        'mapf_calls',
        'mapf_success_calls',
        'mapf_timeout_calls',
        'mapf_fail_calls',
        'mapf_mean_plan_time_ms',
        'mapf_p95_plan_time_ms',
        'fallback_wait_steps'
    ]

    all_ok = True

    for field in required_fields:
        if field not in metrics:
            print(f"  ✗ 缺少字段: {field}")
            all_ok = False
        elif metrics[field] is None:
            print(f"  ✗ 字段为 null: {field}")
            all_ok = False
        else:
            print(f"  ✓ {field}: {metrics[field]}")

    # 检查逻辑一致性
    if 'mapf_calls' in metrics and all(f in metrics for f in ['mapf_success_calls', 'mapf_timeout_calls', 'mapf_fail_calls']):
        total = metrics['mapf_success_calls'] + metrics['mapf_timeout_calls'] + metrics['mapf_fail_calls']
        if total == metrics['mapf_calls']:
            print(f"  ✓ 调用次数一致: {total} == {metrics['mapf_calls']}")
        else:
            print(f"  ✗ 调用次数不一致: {total} != {metrics['mapf_calls']}")
            all_ok = False

    # 检查 p95 >= mean
    if 'mapf_p95_plan_time_ms' in metrics and 'mapf_mean_plan_time_ms' in metrics:
        if metrics['mapf_p95_plan_time_ms'] >= metrics['mapf_mean_plan_time_ms']:
            print(f"  ✓ P95 >= Mean: {metrics['mapf_p95_plan_time_ms']:.2f} >= {metrics['mapf_mean_plan_time_ms']:.2f}")
        else:
            print(f"  ✗ P95 < Mean: {metrics['mapf_p95_plan_time_ms']:.2f} < {metrics['mapf_mean_plan_time_ms']:.2f}")
            all_ok = False

    return all_ok


def validate_trace(trace_path: str) -> bool:
    """验证 trace.jsonl"""
    print("\n验证 trace.jsonl:")

    trace = []
    with open(trace_path, 'r') as f:
        for line in f:
            trace.append(json.loads(line))

    print(f"  ✓ Trace 行数: {len(trace)}")

    # 检查决策步的 MAPF 字段
    decision_steps = [entry for entry in trace if entry.get('decision_step', False)]
    print(f"  ✓ 决策步数: {len(decision_steps)}")

    all_ok = True

    for i, entry in enumerate(decision_steps):
        t = entry['t']

        # 检查必需字段
        if 'mapf_called' not in entry:
            print(f"  ✗ t={t}: 缺少 mapf_called 字段")
            all_ok = False
            continue

        if entry['mapf_called']:
            # 如果调用了 MAPF，必须有这些字段
            if 'mapf_success' not in entry:
                print(f"  ✗ t={t}: 缺少 mapf_success 字段")
                all_ok = False

            if 'mapf_plan_time_ms' not in entry:
                print(f"  ✗ t={t}: 缺少 mapf_plan_time_ms 字段")
                all_ok = False
            elif entry['mapf_plan_time_ms'] is None:
                print(f"  ✗ t={t}: mapf_plan_time_ms 为 null")
                all_ok = False
            elif entry['mapf_plan_time_ms'] <= 0:
                print(f"  ✗ t={t}: mapf_plan_time_ms <= 0: {entry['mapf_plan_time_ms']}")
                all_ok = False

        # 检查 ugv_goals
        if 'ugv_goals' not in entry:
            print(f"  ✗ t={t}: 缺少 ugv_goals 字段")
            all_ok = False

        # 检查 fallback
        if 'fallback' not in entry:
            print(f"  ✗ t={t}: 缺少 fallback 字段")
            all_ok = False

    if all_ok:
        print(f"  ✓ 所有决策步字段完整")

    # 检查所有 mapf_plan_time_ms 都是正数
    plan_times = [entry['mapf_plan_time_ms'] for entry in decision_steps
                  if entry.get('mapf_called') and entry.get('mapf_plan_time_ms') is not None]

    if plan_times:
        all_positive = all(t > 0 for t in plan_times)
        if all_positive:
            print(f"  ✓ 所有 mapf_plan_time_ms 都是正数")
        else:
            print(f"  ✗ 存在非正数的 mapf_plan_time_ms")
            all_ok = False

    return all_ok


def main():
    parser = argparse.ArgumentParser(description='Day6 输出验证脚本')
    parser.add_argument('--dir', type=str, required=True, help='输出目录')

    args = parser.parse_args()

    out_dir = Path(args.dir)
    if not out_dir.exists():
        print(f"✗ 输出目录不存在: {out_dir}")
        sys.exit(1)

    print("=" * 80)
    print("Day6 Step 8: 输出验证")
    print("=" * 80)
    print(f"输出目录: {out_dir}")
    print()

    # 检查文件存在
    metrics_path = out_dir / 'metrics.json'
    trace_path = out_dir / 'trace.jsonl'

    if not metrics_path.exists():
        print(f"✗ metrics.json 不存在")
        sys.exit(1)

    if not trace_path.exists():
        print(f"✗ trace.jsonl 不存在")
        sys.exit(1)

    # 验证 metrics
    metrics_ok = validate_metrics(str(metrics_path))

    # 验证 trace
    trace_ok = validate_trace(str(trace_path))

    # 总结
    print()
    print("=" * 80)
    print("验证结果")
    print("=" * 80)

    if metrics_ok:
        print("  ✓ metrics.json 验证通过")
    else:
        print("  ✗ metrics.json 验证失败")

    if trace_ok:
        print("  ✓ trace.jsonl 验证通过")
    else:
        print("  ✗ trace.jsonl 验证失败")

    print()

    if metrics_ok and trace_ok:
        print("✓ Day6 Step 8 验收通过")
    else:
        print("✗ Day6 Step 8 验收失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
