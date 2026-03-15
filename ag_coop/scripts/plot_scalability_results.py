#!/usr/bin/env python3
"""
可扩展性结果可视化 - 生成论文级图表

输入: scalability_test_*.json
输出:
  - scalability_comparison.pdf (对比柱状图)
  - scalability_heatmap.pdf (性能热力图)
  - scalability_table.tex (LaTeX 表格)
"""

import sys
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# 设置论文级绘图风格
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 10
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['savefig.bbox'] = 'tight'

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_latest_results(results_dir):
    """加载最新的测试结果"""
    results_dir = Path(results_dir)
    json_files = list(results_dir.glob("scalability_test_*.json"))

    if not json_files:
        raise FileNotFoundError(f"未找到结果文件: {results_dir}")

    # 按修改时间排序，取最新的
    latest_file = max(json_files, key=lambda p: p.stat().st_mtime)

    print(f"加载结果文件: {latest_file}")

    with open(latest_file, 'r') as f:
        results = json.load(f)

    return results, latest_file


def plot_comparison_bars(results, output_path):
    """绘制对比柱状图"""

    # 提取数据
    load_names = list(results.keys())
    policy_names = list(results[load_names[0]].keys())

    # 准备数据矩阵
    n_loads = len(load_names)
    n_policies = len(policy_names)

    # 三个指标
    metrics = ['mean_reward', 'mean_tasks', 'mean_outage']
    metric_labels = ['Average Reward', 'Tasks Completed', 'Outage Steps']

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))

    x = np.arange(n_loads)
    width = 0.2

    # 颜色方案
    colors = {
        'PPO_V4': '#2E7D32',        # 深绿色（最好）
        'Vanilla_PPO': '#1976D2',   # 蓝色
        'DQN': '#F57C00',           # 橙色
        'Dynamic_Heuristic': '#757575'  # 灰色（baseline）
    }

    for metric_idx, (metric, label) in enumerate(zip(metrics, metric_labels)):
        ax = axes[metric_idx]

        for policy_idx, policy_name in enumerate(policy_names):
            values = []
            errors = []

            for load_name in load_names:
                if policy_name in results[load_name]:
                    values.append(results[load_name][policy_name][metric])
                    errors.append(results[load_name][policy_name].get(f'std_{metric.split("_")[1]}', 0))
                else:
                    values.append(0)
                    errors.append(0)

            offset = width * (policy_idx - n_policies/2 + 0.5)
            bars = ax.bar(x + offset, values, width,
                         label=policy_name.replace('_', ' '),
                         color=colors.get(policy_name, '#999999'),
                         yerr=errors, capsize=3, alpha=0.8)

        ax.set_xlabel('Task Load', fontsize=11, fontweight='bold')
        ax.set_ylabel(label, fontsize=11, fontweight='bold')
        ax.set_title(f'{label} vs Task Load', fontsize=12, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(['Low\n(20 tasks)', 'Medium\n(40 tasks)', 'High\n(80 tasks)'])
        ax.legend(loc='best', fontsize=9)
        ax.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()
    plt.savefig(output_path, format='pdf', bbox_inches='tight')
    print(f"✓ 对比柱状图已保存: {output_path}")
    plt.close()


def plot_heatmap(results, output_path):
    """绘制性能热力图"""

    load_names = list(results.keys())
    policy_names = list(results[load_names[0]].keys())

    # 构建数据矩阵（使用 mean_reward）
    data = np.zeros((len(policy_names), len(load_names)))

    for i, policy_name in enumerate(policy_names):
        for j, load_name in enumerate(load_names):
            if policy_name in results[load_name]:
                data[i, j] = results[load_name][policy_name]['mean_reward']

    # 绘制热力图
    fig, ax = plt.subplots(figsize=(8, 6))

    sns.heatmap(data,
                annot=True,
                fmt='.2f',
                cmap='RdYlGn',
                xticklabels=['Low (20)', 'Medium (40)', 'High (80)'],
                yticklabels=[p.replace('_', ' ') for p in policy_names],
                cbar_kws={'label': 'Average Reward'},
                linewidths=0.5,
                ax=ax)

    ax.set_xlabel('Task Load', fontsize=12, fontweight='bold')
    ax.set_ylabel('Policy', fontsize=12, fontweight='bold')
    ax.set_title('Performance Heatmap: Average Reward', fontsize=14, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, format='pdf', bbox_inches='tight')
    print(f"✓ 性能热力图已保存: {output_path}")
    plt.close()


def generate_latex_table(results, output_path):
    """生成 LaTeX 表格"""

    load_names = list(results.keys())
    policy_names = list(results[load_names[0]].keys())

    latex = []
    latex.append("\\begin{table}[t]")
    latex.append("\\centering")
    latex.append("\\caption{Scalability Test Results: Performance under Different Task Loads}")
    latex.append("\\label{tab:scalability}")
    latex.append("\\begin{tabular}{l|ccc|ccc|ccc}")
    latex.append("\\hline")
    latex.append("\\multirow{2}{*}{\\textbf{Policy}} & \\multicolumn{3}{c|}{\\textbf{Low Load (20)}} & \\multicolumn{3}{c|}{\\textbf{Medium Load (40)}} & \\multicolumn{3}{c}{\\textbf{High Load (80)}} \\\\")
    latex.append(" & Reward & Tasks & Outage & Reward & Tasks & Outage & Reward & Tasks & Outage \\\\")
    latex.append("\\hline")

    for policy_name in policy_names:
        row = [policy_name.replace('_', ' ')]

        for load_name in load_names:
            if policy_name in results[load_name]:
                r = results[load_name][policy_name]
                row.append(f"{r['mean_reward']:.2f}")
                row.append(f"{r['mean_tasks']:.1f}")
                row.append(f"{r['mean_outage']:.1f}")
            else:
                row.extend(["-", "-", "-"])

        latex.append(" & ".join(row) + " \\\\")

    latex.append("\\hline")
    latex.append("\\end{tabular}")
    latex.append("\\end{table}")

    latex_str = "\n".join(latex)

    with open(output_path, 'w') as f:
        f.write(latex_str)

    print(f"✓ LaTeX 表格已保存: {output_path}")
    print("\n预览:")
    print(latex_str)


def plot_performance_degradation(results, output_path):
    """绘制性能退化曲线"""

    load_names = list(results.keys())
    policy_names = list(results[load_names[0]].keys())

    # 计算相对于低负载的性能保持率
    fig, ax = plt.subplots(figsize=(10, 6))

    colors = {
        'PPO_V4': '#2E7D32',
        'Vanilla_PPO': '#1976D2',
        'DQN': '#F57C00',
        'Dynamic_Heuristic': '#757575'
    }

    markers = ['o', 's', '^', 'D']

    for policy_idx, policy_name in enumerate(policy_names):
        rewards = []

        for load_name in load_names:
            if policy_name in results[load_name]:
                rewards.append(results[load_name][policy_name]['mean_reward'])
            else:
                rewards.append(0)

        # 归一化到低负载性能
        if rewards[0] > 0:
            normalized = [r / rewards[0] * 100 for r in rewards]
        else:
            normalized = [0] * len(rewards)

        ax.plot([20, 40, 80], normalized,
               marker=markers[policy_idx % len(markers)],
               linewidth=2.5,
               markersize=10,
               label=policy_name.replace('_', ' '),
               color=colors.get(policy_name, '#999999'))

    ax.set_xlabel('Task Load (number of tasks)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Performance Retention (%)', fontsize=12, fontweight='bold')
    ax.set_title('Scalability: Performance Retention under Increasing Load',
                fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_ylim([0, 110])

    # 添加参考线
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.5, label='Baseline (100%)')

    plt.tight_layout()
    plt.savefig(output_path, format='pdf', bbox_inches='tight')
    print(f"✓ 性能退化曲线已保存: {output_path}")
    plt.close()


def main():
    """主函数"""

    print("\n" + "=" * 70)
    print("📊 可扩展性结果可视化")
    print("=" * 70)

    # 加载结果
    results_dir = project_root / "outputs" / "scalability_tests"

    try:
        results, results_file = load_latest_results(results_dir)
    except FileNotFoundError as e:
        print(f"\n✗ 错误: {e}")
        print("\n请先运行可扩展性测试:")
        print("  python scripts/evaluate_scalability.py")
        return

    # 创建输出目录
    output_dir = results_dir / "plots"
    output_dir.mkdir(exist_ok=True)

    print(f"\n输出目录: {output_dir}")

    # 生成图表
    print("\n生成图表...")

    # 1. 对比柱状图
    plot_comparison_bars(results, output_dir / "scalability_comparison.pdf")

    # 2. 性能热力图
    plot_heatmap(results, output_dir / "scalability_heatmap.pdf")

    # 3. 性能退化曲线
    plot_performance_degradation(results, output_dir / "performance_degradation.pdf")

    # 4. LaTeX 表格
    generate_latex_table(results, output_dir / "scalability_table.tex")

    print("\n" + "=" * 70)
    print("✅ 所有图表生成完成")
    print("=" * 70)
    print(f"\n输出文件:")
    print(f"  - {output_dir / 'scalability_comparison.pdf'}")
    print(f"  - {output_dir / 'scalability_heatmap.pdf'}")
    print(f"  - {output_dir / 'performance_degradation.pdf'}")
    print(f"  - {output_dir / 'scalability_table.tex'}")
    print("\n这些图表可以直接用于论文！")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n✗ 绘图失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
