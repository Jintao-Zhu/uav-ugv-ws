#!/usr/bin/env python3
"""
Day6.5 回归测试 4: 输出完整性校验

验证点：
1. metrics 字段齐全
2. trace 字段齐全
3. 逻辑一致性：
   - mapf_p95_plan_time_ms >= mapf_mean_plan_time_ms
   - mapf_calls = 1 + ceil(steps / K)
   - mapf_success_calls + mapf_timeout_calls + mapf_fail_calls = mapf_calls
   - fallback_wait_steps 与 MAPF 失败次数一致
"""

import sys
import json
import argparse
from pathlib import Path
from math import ceil


def validate_output_integrity(metrics_path: str, trace_path: str, K: int, steps: int) -> tuple[bool, list[str]]:
    """
    验证输出完整性和逻辑一致性

    Returns:
        (ok, errors)
    """
    errors = []

    # 读取 metrics
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    # 读取 trace
    trace = []
    with open(trace_path, 'r') as f:
        for line in f:
            trace.append(json.loads(line))

    # 1. 检查 metrics 必需字段
    required_metrics_fields = [
        'collision_free',
        'mapf_calls',
        'mapf_success_calls',
        'mapf_timeout_calls',
        'mapf_fail_calls',
        'mapf_mean_plan_time_ms',
        'mapf_p95_plan_time_ms',
        'fallback_wait_steps',
        'steps',
    ]

    for field in required_metrics_fields:
        if field not in metrics:
            errors.append(f"metrics.json 缺少字段: {field}")

    # 2. 检查 trace 必需字段
    if trace:
        required_trace_fields = [
            't',
            'ugv_positions',
            'decision_step',
            'mapf_called',
        ]

        first_entry = trace[0]
        for field in required_trace_fields:
            if field not in first_entry:
                errors.append(f"trace.jsonl 缺少字段: {field}")

    # 3. 验证逻辑一致性

    # 3.1 mapf_p95 >= mapf_mean
    if 'mapf_p95_plan_time_ms' in metrics and 'mapf_mean_plan_time_ms' in metrics:
        p95 = metrics['mapf_p95_plan_time_ms']
        mean = metrics['mapf_mean_plan_time_ms']
        if p95 < mean:
            errors.append(f"mapf_p95_plan_time_ms ({p95}) < mapf_mean_plan_time_ms ({mean})")

    # 3.2 mapf_calls = floor((steps-1) / K) + 1
    # 决策步时间戳：t=1, 1+K, 1+2K, ... 中 <= steps 的数量
    if 'mapf_calls' in metrics and 'steps' in metrics:
        expected_calls = (steps - 1) // K + 1
        actual_calls = metrics['mapf_calls']
        if actual_calls != expected_calls:
            errors.append(
                f"mapf_calls 不符合公式: 实际={actual_calls}, "
                f"期望={expected_calls} (steps={steps}, K={K})"
            )

    # 3.3 mapf_success + timeout + fail = mapf_calls
    if all(k in metrics for k in ['mapf_success_calls', 'mapf_timeout_calls', 'mapf_fail_calls', 'mapf_calls']):
        success = metrics['mapf_success_calls']
        timeout = metrics['mapf_timeout_calls']
        fail = metrics['mapf_fail_calls']
        total = metrics['mapf_calls']

        if success + timeout + fail != total:
            errors.append(
                f"MAPF 调用次数不一致: success({success}) + timeout({timeout}) + fail({fail}) "
                f"= {success + timeout + fail} != mapf_calls({total})"
            )

    # 3.4 fallback_wait_steps 与 MAPF 失败次数一致
    if 'fallback_wait_steps' in metrics:
        fallback_steps = metrics['fallback_wait_steps']

        # 从 trace 统计实际 fallback 步数
        actual_fallback_steps = 0
        for entry in trace:
            if entry.get('fallback', False) or entry.get('mapf_fallback', False):
                actual_fallback_steps += 1

        # 允许一定误差（因为最后一步可能不完整）
        if abs(fallback_steps - actual_fallback_steps) > K:
            errors.append(
                f"fallback_wait_steps 不一致: metrics={fallback_steps}, "
                f"trace 统计={actual_fallback_steps}"
            )

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description='输出完整性校验')
    parser.add_argument('--metrics', type=str, required=True, help='metrics.json 文件路径')
    parser.add_argument('--trace', type=str, required=True, help='trace.jsonl 文件路径')
    parser.add_argument('--K', type=int, required=True, help='决策周期')
    parser.add_argument('--steps', type=int, required=True, help='总步数')

    args = parser.parse_args()

    metrics_path = Path(args.metrics)
    trace_path = Path(args.trace)

    if not metrics_path.exists():
        print(f"✗ Metrics 文件不存在: {metrics_path}")
        sys.exit(1)

    if not trace_path.exists():
        print(f"✗ Trace 文件不存在: {trace_path}")
        sys.exit(1)

    print("=" * 80)
    print("Day6.5 回归测试 4: 输出完整性校验")
    print("=" * 80)
    print(f"Metrics 文件: {metrics_path}")
    print(f"Trace 文件: {trace_path}")
    print(f"决策周期 K: {args.K}")
    print(f"总步数: {args.steps}")
    print()

    ok, errors = validate_output_integrity(str(metrics_path), str(trace_path), args.K, args.steps)

    if ok:
        print("✓ 输出完整性校验通过")
        print()
        print("验收结果: ok=true")
    else:
        print("✗ 输出完整性校验失败")
        print()
        for error in errors:
            print(f"  - {error}")
        print()
        print("验收结果: ok=false")
        sys.exit(1)


if __name__ == "__main__":
    main()
