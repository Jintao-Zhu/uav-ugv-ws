"""
Day6 Step 7: 冲突校验脚本

离线验证 trace 中是否有碰撞。

用法:
    python scripts/check_collisions.py --trace outputs/.../trace.jsonl
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Tuple, Optional


def check_collisions(trace_path: str) -> Tuple[bool, Optional[str]]:
    """
    检查 trace 中是否有碰撞

    Args:
        trace_path: trace.jsonl 文件路径

    Returns:
        (ok, error_message)
    """
    # 读取 trace
    trace = []
    with open(trace_path, 'r') as f:
        for line in f:
            trace.append(json.loads(line))

    if not trace:
        return False, "Trace 为空"

    # 逐步检查
    prev_positions = None

    for entry in trace:
        t = entry['t']
        positions = [tuple(pos) for pos in entry['ugv_positions']]
        n = len(positions)

        # 检查 vertex collision
        for i in range(n):
            for j in range(i + 1, n):
                if positions[i] == positions[j]:
                    error = f"Vertex collision at t={t}: agent {i} and {j} at {positions[i]}"
                    return False, error

        # 检查 edge collision (swap)
        if prev_positions is not None:
            for i in range(n):
                for j in range(i + 1, n):
                    if positions[i] == prev_positions[j] and positions[j] == prev_positions[i]:
                        error = f"Edge collision at t={t}: agent {i} and {j} swap positions ({prev_positions[i]} <-> {prev_positions[j]})"
                        return False, error

        prev_positions = positions

    return True, None


def main():
    parser = argparse.ArgumentParser(description='冲突校验脚本')
    parser.add_argument('--trace', type=str, required=True, help='trace.jsonl 文件路径')

    args = parser.parse_args()

    trace_path = Path(args.trace)
    if not trace_path.exists():
        print(f"✗ Trace 文件不存在: {trace_path}")
        sys.exit(1)

    print("=" * 80)
    print("Day6 Step 7: 冲突校验")
    print("=" * 80)
    print(f"Trace 文件: {trace_path}")
    print()

    # 检查碰撞
    ok, error = check_collisions(str(trace_path))

    if ok:
        print("✓ 碰撞检测通过：无冲突")
        print()
        print("验收结果: ok=true")
    else:
        print(f"✗ 碰撞检测失败")
        print(f"  错误: {error}")
        print()
        print("验收结果: ok=false")
        sys.exit(1)


if __name__ == "__main__":
    main()
