#!/usr/bin/env python3
"""
Day 6.5 调试报告生成器

如果 Day6.5 任一验收没过，使用此脚本快速生成调试材料。

用法:
    python scripts/generate_debug_report.py --run outputs/test_step5_exp_b
    python scripts/generate_debug_report.py --run outputs/test_step5_exp_b --error-line 25

输出 4 个关键材料：
1. config_resolved.yaml（确认 K/H/budget/seed/n_agents）
2. metrics.json
3. trace.jsonl 截取（第一次出错前后 30 行，尤其是决策步附近）
4. check_collisions.py 的输出（若报冲突，附冲突类型 vertex/edge swap）
"""

import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Optional


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def extract_trace_context(trace_path: Path, error_line: Optional[int] = None, context: int = 30):
    """
    提取 trace 中关键部分

    Args:
        trace_path: trace.jsonl 路径
        error_line: 出错的行号（如果已知）
        context: 前后提取的行数

    Returns:
        提取的行列表
    """
    with open(trace_path, 'r') as f:
        lines = f.readlines()

    total_lines = len(lines)

    if error_line is not None:
        # 如果指定了错误行，提取前后 context 行
        start = max(0, error_line - context)
        end = min(total_lines, error_line + context + 1)
        return lines[start:end], start, end
    else:
        # 否则，查找第一个决策步（decision_step=true）附近
        decision_lines = []
        for i, line in enumerate(lines):
            try:
                entry = json.loads(line)
                if entry.get('decision_step', False):
                    decision_lines.append(i)
            except:
                pass

        if decision_lines:
            # 提取第一个决策步前后的内容
            first_decision = decision_lines[0]
            start = max(0, first_decision - 10)
            end = min(total_lines, first_decision + 20)
            return lines[start:end], start, end
        else:
            # 如果没有决策步，提取开头部分
            return lines[:min(30, total_lines)], 0, min(30, total_lines)


def generate_report(run_dir: Path, error_line: Optional[int] = None):
    """
    生成完整的调试报告

    Args:
        run_dir: 运行输出目录
        error_line: 出错的行号（可选）
    """
    print_section(f"Day 6.5 调试报告: {run_dir.name}")

    # 1. config_resolved.yaml
    config_path = run_dir / "config_resolved.yaml"
    if config_path.exists():
        print_section("1. config_resolved.yaml（确认 K/H/budget/seed/n_agents）")
        with open(config_path, 'r') as f:
            content = f.read()
        print(content)

        # 提取关键参数
        print("\n关键参数摘要:")
        for line in content.split('\n'):
            if any(key in line for key in ['n_ugv:', 'n_uav:', 'H:', 'time_budget_ms:', 'seed:', 'horizon_steps:']):
                print(f"  {line.strip()}")
    else:
        print(f"✗ 未找到 config_resolved.yaml")

    # 2. metrics.json
    metrics_path = run_dir / "metrics.json"
    if metrics_path.exists():
        print_section("2. metrics.json")
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)

        print(json.dumps(metrics, indent=2))

        # 提取关键指标
        print("\n关键指标摘要:")
        key_metrics = [
            'collision_free', 'mapf_calls', 'mapf_success_calls',
            'mapf_timeout_calls', 'mapf_fail_calls', 'completion_rate',
            'termination_reason', 'steps'
        ]
        for key in key_metrics:
            if key in metrics:
                print(f"  {key}: {metrics[key]}")
    else:
        print(f"✗ 未找到 metrics.json")

    # 3. trace.jsonl 截取
    trace_path = run_dir / "trace.jsonl"
    if trace_path.exists():
        print_section("3. trace.jsonl 截取（第一次出错前后 30 行）")

        lines, start, end = extract_trace_context(trace_path, error_line)

        print(f"提取行范围: {start} - {end}")
        print(f"总行数: {len(open(trace_path).readlines())}")
        print()

        for i, line in enumerate(lines, start=start):
            try:
                entry = json.loads(line)
                # 简化显示
                t = entry.get('t', '?')
                decision = '🔵' if entry.get('decision_step', False) else '  '
                ugv_pos = entry.get('ugv_positions', [])
                uav_pos = entry.get('uav_positions', [])

                print(f"[{i:3d}] t={t:3d} {decision} UGV:{ugv_pos} UAV:{uav_pos}")

                # 如果是决策步，显示更多信息
                if entry.get('decision_step', False):
                    if 'mapf_result' in entry:
                        result = entry['mapf_result']
                        print(f"       └─ MAPF: {result.get('status', 'unknown')} "
                              f"(time={result.get('plan_time_ms', 0):.2f}ms, "
                              f"expanded={result.get('expanded_nodes', 0)})")
            except Exception as e:
                print(f"[{i:3d}] (解析错误: {e})")
    else:
        print(f"✗ 未找到 trace.jsonl")

    # 4. check_collisions.py 输出
    print_section("4. check_collisions.py 输出")

    if trace_path.exists():
        try:
            result = subprocess.run(
                ['python', 'scripts/check_collisions.py', '--trace', str(trace_path)],
                capture_output=True,
                text=True,
                cwd=run_dir.parent.parent
            )

            print(result.stdout)
            if result.returncode != 0:
                print("✗ 冲突检测失败!")
                if result.stderr:
                    print(f"错误信息: {result.stderr}")
        except Exception as e:
            print(f"✗ 运行 check_collisions.py 失败: {e}")
    else:
        print("✗ 无 trace 文件，跳过冲突检测")

    # 总结
    print_section("调试建议")

    if metrics_path.exists():
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)

        suggestions = []

        if not metrics.get('collision_free', True):
            suggestions.append("❌ collision_free=false → 检查 controller bug（路径执行逻辑）")

        if metrics.get('mapf_fail_calls', 0) > 0:
            suggestions.append("❌ mapf_fail_calls > 0 → 检查 core 集成 bug（MAPF 调用失败）")

        if metrics.get('mapf_timeout_calls', 0) == metrics.get('mapf_calls', 0):
            suggestions.append("⚠️  所有 MAPF 调用都超时 → 检查 time_budget_ms 设置或 MAPF 性能")

        if metrics.get('completion_rate', 0) == 0 and metrics.get('total_tasks', 0) > 0:
            suggestions.append("⚠️  completion_rate=0 → 检查任务分配或路径规划逻辑")

        if not suggestions:
            suggestions.append("✓ 主要指标正常，可能是日志/口径 bug")

        for s in suggestions:
            print(f"  {s}")

    print("\n" + "=" * 80)
    print("报告生成完成")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Day 6.5 调试报告生成器')
    parser.add_argument('--run', type=str, required=True,
                        help='运行输出目录，例如 outputs/test_step5_exp_b')
    parser.add_argument('--error-line', type=int, default=None,
                        help='trace.jsonl 中出错的行号（可选）')

    args = parser.parse_args()

    run_dir = Path(args.run)
    if not run_dir.exists():
        print(f"✗ 运行目录不存在: {run_dir}")
        sys.exit(1)

    generate_report(run_dir, args.error_line)


if __name__ == "__main__":
    main()
