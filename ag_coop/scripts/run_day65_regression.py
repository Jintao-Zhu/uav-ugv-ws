#!/usr/bin/env python3
"""
Day6.5 完整回归测试套件

运行所有 4 组回归测试：
1. Receding Horizon 执行验证
2. Fallback WAIT 验证
3. 离线碰撞校验
4. 输出完整性校验
"""

import sys
import subprocess
from pathlib import Path
import argparse


def run_test(name: str, cmd: list[str]) -> bool:
    """运行单个测试"""
    print("=" * 80)
    print(f"运行测试: {name}")
    print("=" * 80)
    print(f"命令: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode == 0:
        print()
        print(f"✓ {name} 通过")
        return True
    else:
        print()
        print(f"✗ {name} 失败")
        return False


def main():
    parser = argparse.ArgumentParser(description='Day6.5 完整回归测试套件')
    parser.add_argument('--run', type=str, required=True, help='运行输出目录')
    parser.add_argument('--K', type=int, default=5, help='决策周期（默认 5）')
    parser.add_argument('--steps', type=int, required=True, help='总步数')

    args = parser.parse_args()

    run_dir = Path(args.run)
    if not run_dir.exists():
        print(f"✗ 运行目录不存在: {run_dir}")
        sys.exit(1)

    metrics_path = run_dir / "metrics.json"
    trace_path = run_dir / "trace.jsonl"
    config_path = run_dir / "config_resolved.yaml"

    # 检查文件
    for path in [metrics_path, trace_path, config_path]:
        if not path.exists():
            print(f"✗ 文件不存在: {path}")
            sys.exit(1)

    print("=" * 80)
    print("Day6.5 完整回归测试套件")
    print("=" * 80)
    print(f"运行目录: {run_dir}")
    print(f"决策周期 K: {args.K}")
    print(f"总步数: {args.steps}")
    print()

    results = {}

    # 测试 1: Receding Horizon
    results['receding_horizon'] = run_test(
        "回归测试 1: Receding Horizon 执行验证",
        [
            'python', 'scripts/validate_receding_horizon.py',
            '--trace', str(trace_path),
            '--K', str(args.K),
            '--steps', str(args.steps)
        ]
    )
    print()

    # 测试 2: Fallback WAIT
    results['fallback_wait'] = run_test(
        "回归测试 2: Fallback WAIT 验证",
        [
            'python', 'scripts/validate_fallback_wait.py',
            '--trace', str(trace_path),
            '--K', str(args.K)
        ]
    )
    print()

    # 测试 3: 碰撞检测
    results['collision'] = run_test(
        "回归测试 3: 离线碰撞校验",
        [
            'python', 'scripts/check_collisions.py',
            '--trace', str(trace_path)
        ]
    )
    print()

    # 测试 4: 输出完整性
    results['output_integrity'] = run_test(
        "回归测试 4: 输出完整性校验",
        [
            'python', 'scripts/validate_output_integrity.py',
            '--metrics', str(metrics_path),
            '--trace', str(trace_path),
            '--K', str(args.K),
            '--steps', str(args.steps)
        ]
    )
    print()

    # 总结
    print("=" * 80)
    print("测试结果汇总")
    print("=" * 80)

    all_passed = True
    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {name:30s} {status}")
        if not passed:
            all_passed = False

    print()

    if all_passed:
        print("=" * 80)
        print("🎉 所有回归测试通过！Day6.5 验收完成！")
        print("=" * 80)
        sys.exit(0)
    else:
        print("=" * 80)
        print("❌ 部分测试失败，Day6.5 验收未通过")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    main()
