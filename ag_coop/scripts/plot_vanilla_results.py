#!/usr/bin/env python3
"""
简化版可扩展性结果可视化 - 仅 Vanilla PPO
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np

# 设置论文级绘图风格
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.size'] = 10
plt.rcParams['figure.dpi'] = 300

project_root = Path(__file__).parent.parent

# 加载最新结果
results_dir = project_root / "outputs" / "scalability_tests"
json_files = list(results_dir.glob("scalability_test_*.json"))
latest_file = max(json_files, key=lambda p: p.stat().st_mtime)

print(f"加载结果: {latest_file}")

with open(latest_file, 'r') as f:
    results = json.load(f)

# 创建输出目录
output_dir = results_dir / "plots"
output_dir.mkdir(exist_ok=True)

# 提取数据
loads = ['Low Load', 'Medium Load', 'High Load']
load_values = [20, 40, 80]

vanilla_rewards = []
vanilla_tasks = []
vanilla_outages = []

for load in loads:
    if 'Vanilla_PPO' in results[load]:
        vanilla_rewards.append(results[load]['Vanilla_PPO']['mean_reward'])
        vanilla_tasks.append(results[load]['Vanilla_PPO']['mean_tasks'])
        vanilla_outages.append(results[load]['Vanilla_PPO']['mean_outage'])

# 绘图 1: 性能指标对比
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

# 奖励
axes[0].plot(load_values, vanilla_rewards, 'o-', linewidth=2.5, markersize=10,
            color='#1976D2', label='Vanilla PPO')
axes[0].set_xlabel('Task Load', fontsize=11, fontweight='bold')
axes[0].set_ylabel('Average Reward', fontsize=11, fontweight='bold')
axes[0].set_title('Reward vs Task Load', fontsize=12, fontweight='bold')
axes[0].grid(True, alpha=0.3, linestyle='--')
axes[0].legend()

# 任务完成
axes[1].plot(load_values, vanilla_tasks, 'o-', linewidth=2.5, markersize=10,
            color='#2E7D32', label='Vanilla PPO')
axes[1].set_xlabel('Task Load', fontsize=11, fontweight='bold')
axes[1].set_ylabel('Tasks Completed', fontsize=11, fontweight='bold')
axes[1].set_title('Tasks Completed vs Task Load', fontsize=12, fontweight='bold')
axes[1].grid(True, alpha=0.3, linestyle='--')
axes[1].legend()

# 通信中断
axes[2].plot(load_values, vanilla_outages, 'o-', linewidth=2.5, markersize=10,
            color='#D32F2F', label='Vanilla PPO')
axes[2].set_xlabel('Task Load', fontsize=11, fontweight='bold')
axes[2].set_ylabel('Outage Steps', fontsize=11, fontweight='bold')
axes[2].set_title('Outage Steps vs Task Load', fontsize=12, fontweight='bold')
axes[2].grid(True, alpha=0.3, linestyle='--')
axes[2].legend()

plt.tight_layout()
plt.savefig(output_dir / "vanilla_ppo_scalability.pdf", format='pdf', bbox_inches='tight')
print(f"✓ 图表已保存: {output_dir / 'vanilla_ppo_scalability.pdf'}")
plt.close()

# 生成 LaTeX 表格
latex = []
latex.append("\\begin{table}[t]")
latex.append("\\centering")
latex.append("\\caption{Vanilla PPO Scalability Test Results}")
latex.append("\\label{tab:vanilla_ppo_scalability}")
latex.append("\\begin{tabular}{lccc}")
latex.append("\\hline")
latex.append("\\textbf{Task Load} & \\textbf{Reward} & \\textbf{Tasks} & \\textbf{Outage} \\\\")
latex.append("\\hline")

for i, load in enumerate(loads):
    latex.append(f"{load_values[i]} tasks & {vanilla_rewards[i]:.2f} & {vanilla_tasks[i]:.0f} & {vanilla_outages[i]:.0f} \\\\")

latex.append("\\hline")
latex.append("\\end{tabular}")
latex.append("\\end{table}")

latex_str = "\n".join(latex)
latex_file = output_dir / "vanilla_ppo_table.tex"

with open(latex_file, 'w') as f:
    f.write(latex_str)

print(f"✓ LaTeX 表格已保存: {latex_file}")
print("\n预览:")
print(latex_str)

print("\n" + "="*70)
print("✅ 图表生成完成")
print("="*70)
print(f"\n输出文件:")
print(f"  - {output_dir / 'vanilla_ppo_scalability.pdf'}")
print(f"  - {output_dir / 'vanilla_ppo_table.tex'}")
