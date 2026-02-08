#!/usr/bin/env python3
"""
Day8 Step 6.7: 绘制 Trade-off 曲线

从实验结果生成 trade-off 曲线图
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path


def main():
    # 加载结果
    results_file = Path("outputs/day8_final_summary/results.json")
    with open(results_file) as f:
        all_results = json.load(f)

    # 按场景分组
    scenarios = ['uniform', 'dual_hotspot']
    lambdas = [0.0, 0.2, 0.5, 1.0]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for idx, scenario in enumerate(scenarios):
        ax = axes[idx]

        # 提取数据
        scenario_results = [r for r in all_results if r['scenario'] == scenario]

        # 按 λ 分组并计算均值
        lambda_data = {}
        for lambda_val in lambdas:
            if lambda_val == 0.0:
                group = [r for r in scenario_results if r['method'] == 'greedy']
            else:
                group = [r for r in scenario_results
                        if r['method'] == 'comm_greedy' and r['lambda'] == lambda_val]

            if group:
                lambda_data[lambda_val] = {
                    'tasks_mean': np.mean([r['tasks_completed'] for r in group]),
                    'tasks_std': np.std([r['tasks_completed'] for r in group]),
                    'outage_worst_mean': np.mean([r['outage_percent_worst_nc'] for r in group]),
                    'outage_worst_std': np.std([r['outage_percent_worst_nc'] for r in group]),
                    'miss_rate_mean': np.mean([r['deadline_miss_rate'] for r in group]),
                }

        # 绘制 trade-off 曲线
        tasks_means = [lambda_data[l]['tasks_mean'] for l in lambdas if l in lambda_data]
        outage_means = [lambda_data[l]['outage_worst_mean'] for l in lambdas if l in lambda_data]
        outage_stds = [lambda_data[l]['outage_worst_std'] for l in lambdas if l in lambda_data]

        # 主曲线
        ax.errorbar(tasks_means, outage_means, yerr=outage_stds,
                   marker='o', markersize=8, linewidth=2, capsize=5,
                   label='Comm-Aware Greedy v2')

        # 标注 λ 值
        for i, lambda_val in enumerate([l for l in lambdas if l in lambda_data]):
            ax.annotate(f'λ={lambda_val}',
                       (tasks_means[i], outage_means[i]),
                       textcoords="offset points",
                       xytext=(10, -10),
                       ha='left',
                       fontsize=9)

        # 标注 baseline
        if 0.0 in lambda_data:
            ax.plot(lambda_data[0.0]['tasks_mean'],
                   lambda_data[0.0]['outage_worst_mean'],
                   'r*', markersize=15, label='Greedy Baseline')

        ax.set_xlabel('Tasks Completed', fontsize=12)
        ax.set_ylabel('Outage (worst_nc) %', fontsize=12)
        ax.set_title(f'Trade-off Curve: {scenario.replace("_", " ").title()}', fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend()

        # 设置 y 轴范围
        ax.set_ylim([min(outage_means) - 5, max(outage_means) + 5])

    plt.tight_layout()

    # 保存图片
    output_dir = Path("outputs/day8_final_summary")
    output_file = output_dir / "tradeoff_curves.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"Trade-off 曲线已保存: {output_file}")

    # 也保存为 PDF（论文用）
    output_file_pdf = output_dir / "tradeoff_curves.pdf"
    plt.savefig(output_file_pdf, bbox_inches='tight')
    print(f"PDF 版本已保存: {output_file_pdf}")

    plt.show()


if __name__ == "__main__":
    main()
