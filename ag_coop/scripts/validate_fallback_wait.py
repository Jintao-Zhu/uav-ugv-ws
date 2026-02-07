#!/usr/bin/env python3
"""
Day6.5 回归测试 2: Fallback WAIT 验证

验证点：
1. 超时/失败时全体 WAIT
2. 每 K 步重试 MAPF
3. fallback 期间位置不变
"""

import sys
import json
import argparse
from pathlib import Path


def validate_fallback_wait(trace_path: str, K: int) -> tuple[bool, list[str]]:
    """
    验证 Fallback WAIT 逻辑

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

    # 查找所有 MAPF 失败/超时的时刻
    mapf_fail_times = []
    for entry in trace:
        if entry.get('decision_step', False):
            if entry.get('mapf_called', False):
                success = entry.get('mapf_success', None)
                if success is False:  # 超时或失败
                    mapf_fail_times.append(entry['t'])

    if not mapf_fail_times:
        print("  (未检测到 MAPF 失败/超时，跳过 fallback 验证)")
        return True, []

    print(f"  检测到 {len(mapf_fail_times)} 次 MAPF 失败/超时: {mapf_fail_times}")
    print()

    # 对每次失败，验证后续行为
    for fail_t in mapf_fail_times:
        # 1. 验证失败后到下一个决策步之间，位置不变（WAIT）
        next_decision_t = fail_t + K

        # 获取失败时刻的位置
        fail_entry = next(e for e in trace if e['t'] == fail_t)
        fail_positions = fail_entry.get('ugv_positions', [])

        # 检查后续步骤的位置
        for entry in trace:
            t = entry['t']
            if fail_t < t < next_decision_t:
                current_positions = entry.get('ugv_positions', [])

                # 验证位置不变
                if current_positions != fail_positions:
                    errors.append(
                        f"Fallback 期间位置变化: t={t} (MAPF 失败于 t={fail_t})\n"
                        f"  失败时位置: {fail_positions}\n"
                        f"  当前位置: {current_positions}"
                    )

        # 2. 验证下一个决策步重新调用 MAPF
        next_decision_entry = next((e for e in trace if e['t'] == next_decision_t), None)
        if next_decision_entry:
            if not next_decision_entry.get('decision_step', False):
                errors.append(f"t={next_decision_t} 应该是决策步（MAPF 失败于 t={fail_t}）")
            if not next_decision_entry.get('mapf_called', False):
                errors.append(f"t={next_decision_t} 应该调用 MAPF（MAPF 失败于 t={fail_t}）")

    return len(errors) == 0, errors


def main():
    parser = argparse.ArgumentParser(description='Fallback WAIT 验证')
    parser.add_argument('--trace', type=str, required=True, help='trace.jsonl 文件路径')
    parser.add_argument('--K', type=int, required=True, help='决策周期')

    args = parser.parse_args()

    trace_path = Path(args.trace)
    if not trace_path.exists():
        print(f"✗ Trace 文件不存在: {trace_path}")
        sys.exit(1)

    print("=" * 80)
    print("Day6.5 回归测试 2: Fallback WAIT 验证")
    print("=" * 80)
    print(f"Trace 文件: {trace_path}")
    print(f"决策周期 K: {args.K}")
    print()

    ok, errors = validate_fallback_wait(str(trace_path), args.K)

    if ok:
        print("✓ Fallback WAIT 验证通过")
        print()
        print("验收结果: ok=true")
    else:
        print("✗ Fallback WAIT 验证失败")
        print()
        for error in errors:
            print(f"  - {error}")
        print()
        print("验收结果: ok=false")
        sys.exit(1)


if __name__ == "__main__":
    main()
