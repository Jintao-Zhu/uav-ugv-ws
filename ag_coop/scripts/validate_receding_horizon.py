#!/usr/bin/env python3
"""
Day6.5 回归测试 1: Receding Horizon 执行验证

验证点：
1. 每 K 步调用一次 MAPF
2. 其余步执行缓存路径
3. 调用次数 = 1 + ceil(steps / K)
"""

import sys
import json
import argparse
from pathlib import Path
from math import ceil


def validate_receding_horizon(trace_path: str, K: int, steps: int) -> tuple[bool, list[str]]:
    """
    验证 Receding Horizon 执行逻辑

    Returns:
        (ok, errors)
    """
    errors = []

    # 读取 trace
    trace = []
    with open(trace_path, 'r') as f:
        for line in f:
            trace.append(json.loads(line))

    if not trace:
        return False, ["Trace 为空"]

    # 1. 统计决策步
    decision_steps = []
    for entry in trace:
        if entry.get('decision_step', False):
            decision_steps.append(entry['t'])

    # 2. 验证决策步间隔
    if len(decision_steps) > 1:
        for i in range(1, len(decision_steps)):
            interval = decision_steps[i] - decision_steps[i-1]
            if interval != K:
                errors.append(f"决策步间隔错误: t={decision_steps[i-1]} 到 t={decision_steps[i]} 间隔={interval}, 期望={K}")

    # 3. 验证调用次数公式
    # 决策步时间戳：t=1, 1+K, 1+2K, ... 中 <= steps 的数量
    # 公式：floor((steps - 1) / K) + 1
    expected_calls = (steps - 1) // K + 1
    actual_calls = len(decision_steps)

    if actual_calls != expected_calls:
        errors.append(f"MAPF 调用次数错误: 实际={actual_calls}, 期望={expected_calls} (steps={steps}, K={K})")

    # 4. 验证非决策步不调用 MAPF
    for entry in trace:
        if not entry.get('decision_step', False):
            if entry.get('mapf_called', False):
                errors.append(f"非决策步调用了 MAPF: t={entry['t']}")

    # 5. 验证决策步调用 MAPF
    for entry in trace:
        if entry.get('decision_step', False):
            if not entry.get('mapf_called', False):
                errors.append(f"决策步未调用 MAPF: t={entry['t']}")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description='Receding Horizon 执行验证')
    parser.add_argument('--trace', type=str, required=True, help='trace.jsonl 文件路径')
    parser.add_argument('--K', type=int, required=True, help='决策周期')
    parser.add_argument('--steps', type=int, required=True, help='总步数')

    args = parser.parse_args()

    trace_path = Path(args.trace)
    if not trace_path.exists():
        print(f"✗ Trace 文件不存在: {trace_path}")
        sys.exit(1)

    print("=" * 80)
    print("Day6.5 回归测试 1: Receding Horizon 执行验证")
    print("=" * 80)
    print(f"Trace 文件: {trace_path}")
    print(f"决策周期 K: {args.K}")
    print(f"总步数: {args.steps}")
    print()

    ok, errors = validate_receding_horizon(str(trace_path), args.K, args.steps)

    if ok:
        print("✓ Receding Horizon 验证通过")
        print()
        print("验收结果: ok=true")
    else:
        print("✗ Receding Horizon 验证失败")
        print()
        for error in errors:
            print(f"  - {error}")
        print()
        print("验收结果: ok=false")
        sys.exit(1)


if __name__ == "__main__":
    main()
