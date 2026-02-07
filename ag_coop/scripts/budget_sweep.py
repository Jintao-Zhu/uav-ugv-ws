"""
Budget Sweep 实验：测试不同时间预算对 MAPF 性能的影响

测试配置：
- Map: map_01
- Agents: 3
- Steps: 100
- K: 5, H: 40
- Seed: 42
- Budget: [0, 1, 2, 5, 10, 50, 100, 300] ms
"""

import sys
import json
import subprocess
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_budget_test(budget_ms: int, out_dir: Path):
    """运行单个 budget 测试"""
    cmd = [
        "python", "scripts/test_mapf_integration.py",
        "--steps", "100",
        "--K", "5",
        "--H", "40",
        "--n", "3",
        "--seed", "42",
        "--budget_ms", str(budget_ms),
        "--goal_radius", "15",
        "--out_dir", str(out_dir)
    ]

    print(f"  Budget {budget_ms} ms...", end=" ", flush=True)

    try:
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"✗ 失败")
            return None

        # 读取 metrics
        metrics_path = out_dir / "metrics.json"
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)

        print(f"✓ 成功")
        return metrics

    except Exception as e:
        print(f"✗ 异常: {e}")
        return None


def main():
    print("=" * 80)
    print("Budget Sweep 实验")
    print("=" * 80)
    print()

    # 测试不同的 budget
    budgets = [0, 1, 2, 5, 10, 50, 100, 300]

    base_out_dir = project_root / "outputs" / "budget_sweep"
    base_out_dir.mkdir(parents=True, exist_ok=True)

    results = []

    print("运行测试:")
    print("-" * 80)

    for budget in budgets:
        out_dir = base_out_dir / f"budget_{budget}ms"
        out_dir.mkdir(parents=True, exist_ok=True)

        metrics = run_budget_test(budget, out_dir)
        if metrics is not None:
            results.append({
                'budget_ms': budget,
                'metrics': metrics
            })

    print()
    print("=" * 80)
    print("实验结果")
    print("=" * 80)
    print()

    # 打印表格
    print(f"{'Budget (ms)':<12} {'Success Rate':<15} {'Timeout Rate':<15} {'Mean Time (ms)':<18} {'P95 Time (ms)':<18} {'Expanded Nodes':<18} {'Fallback %':<12}")
    print("-" * 120)

    for r in results:
        budget = r['budget_ms']
        m = r['metrics']

        success_rate = m['mapf_success_calls'] / m['mapf_calls'] * 100 if m['mapf_calls'] > 0 else 0
        timeout_rate = m['mapf_timeout_calls'] / m['mapf_calls'] * 100 if m['mapf_calls'] > 0 else 0
        fallback_rate = m['fallback_wait_steps'] / m['steps'] * 100

        print(f"{budget:<12} {success_rate:<15.1f} {timeout_rate:<15.1f} {m['mapf_mean_plan_time_ms']:<18.2f} {m['mapf_p95_plan_time_ms']:<18.2f} {m['mapf_expanded_mean_per_call']:<18.1f} {fallback_rate:<12.1f}")

    # 保存结果
    summary = {
        'config': {
            'map': 'map_01',
            'n_agents': 3,
            'steps': 100,
            'K': 5,
            'H': 40,
            'seed': 42
        },
        'budgets': budgets,
        'results': results
    }

    summary_path = base_out_dir / "summary.json"
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print()
    print(f"结果已保存到: {summary_path}")
    print()

    # 生成 LaTeX 表格
    latex_path = base_out_dir / "table.tex"
    with open(latex_path, 'w') as f:
        f.write("\\begin{table}[h]\n")
        f.write("\\centering\n")
        f.write("\\caption{MAPF Performance vs Time Budget}\n")
        f.write("\\begin{tabular}{ccccccc}\n")
        f.write("\\hline\n")
        f.write("Budget & Success & Timeout & Mean Time & P95 Time & Expanded & Fallback \\\\\n")
        f.write("(ms) & Rate (\\%) & Rate (\\%) & (ms) & (ms) & Nodes & (\\%) \\\\\n")
        f.write("\\hline\n")

        for r in results:
            budget = r['budget_ms']
            m = r['metrics']
            success_rate = m['mapf_success_calls'] / m['mapf_calls'] * 100 if m['mapf_calls'] > 0 else 0
            timeout_rate = m['mapf_timeout_calls'] / m['mapf_calls'] * 100 if m['mapf_calls'] > 0 else 0
            fallback_rate = m['fallback_wait_steps'] / m['steps'] * 100

            f.write(f"{budget} & {success_rate:.1f} & {timeout_rate:.1f} & {m['mapf_mean_plan_time_ms']:.2f} & {m['mapf_p95_plan_time_ms']:.2f} & {m['mapf_expanded_mean_per_call']:.0f} & {fallback_rate:.1f} \\\\\n")

        f.write("\\hline\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")

    print(f"LaTeX 表格已保存到: {latex_path}")


if __name__ == "__main__":
    main()
