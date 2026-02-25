#!/usr/bin/env python3
"""
课程学习训练结果可视化脚本
生成适合论文发表的高质量图表
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
from tensorboard.backend.event_processing import event_accumulator
from pathlib import Path

# 设置论文级别的绘图风格
plt.rcParams['font.size'] = 12
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['legend.fontsize'] = 11
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['lines.linewidth'] = 2
plt.rcParams['grid.alpha'] = 0.3


def load_tensorboard_data(tb_dir):
    """加载 TensorBoard 数据"""
    stages_data = {}

    for stage_dir in sorted(os.listdir(tb_dir)):
        stage_path = os.path.join(tb_dir, stage_dir)
        if not os.path.isdir(stage_path):
            continue

        ea = event_accumulator.EventAccumulator(stage_path)
        ea.Reload()

        available_tags = ea.Tags()['scalars']
        stage_metrics = {}

        for tag in available_tags:
            events = ea.Scalars(tag)
            steps = [e.step for e in events]
            values = [e.value for e in events]
            stage_metrics[tag] = {'steps': steps, 'values': values}

        stages_data[stage_dir] = stage_metrics

    return stages_data


def plot_training_curves(stages_data, output_dir):
    """绘制训练曲线（带阶段标注）"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Curriculum Learning Training Dynamics', fontsize=18, fontweight='bold')

    # 定义关键指标
    metrics = [
        ('rollout/ep_rew_mean', 'Average Episode Reward', axes[0, 0]),
        ('train/entropy_loss', 'Policy Entropy Loss', axes[0, 1]),
        ('train/value_loss', 'Value Function Loss', axes[1, 0]),
        ('train/learning_rate', 'Learning Rate', axes[1, 1]),
    ]

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Stage 1, 2, 3
    stage_names = ['Stage 1: Map_03', 'Stage 2: Map_01', 'Stage 3: Map_02']

    for tag, title, ax in metrics:
        for idx, (stage_dir, stage_metrics) in enumerate(sorted(stages_data.items())):
            if tag in stage_metrics:
                data = stage_metrics[tag]
                ax.plot(data['steps'], data['values'],
                       label=stage_names[idx], color=colors[idx], alpha=0.8)

        ax.set_xlabel('Training Steps')
        ax.set_ylabel(title)
        ax.set_title(title)
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 添加阶段分界线
        ax.axvline(x=300000, color='red', linestyle='--', alpha=0.5, linewidth=1)
        ax.axvline(x=600000, color='red', linestyle='--', alpha=0.5, linewidth=1)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'training_curves.png'), dpi=300, bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, 'training_curves.pdf'), bbox_inches='tight')
    print(f"✓ 训练曲线已保存: {output_dir}/training_curves.png")
    plt.close()


def plot_evaluation_comparison(eval_results, output_dir):
    """绘制评估结果对比（带误差棒）"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # 读取评估结果
    with open(eval_results, 'r') as f:
        data = json.load(f)

    results = data['results']
    seeds = [r['seed'] for r in results]
    tasks_completed = [r['tasks_completed'] for r in results]
    deadline_miss = [r['deadline_miss'] for r in results]

    # 子图1：每个种子的完成任务数
    ax1.bar(range(len(seeds)), tasks_completed, color='steelblue', alpha=0.7)
    ax1.axhline(y=np.mean(tasks_completed), color='red', linestyle='--',
                label=f'Mean: {np.mean(tasks_completed):.2f}')
    ax1.axhline(y=35, color='green', linestyle='--', alpha=0.5, label='Target: 35')
    ax1.set_xlabel('Test Seed')
    ax1.set_ylabel('Tasks Completed')
    ax1.set_title('Tasks Completed per Test Seed')
    ax1.set_xticks(range(len(seeds)))
    ax1.set_xticklabels([str(s) for s in seeds], rotation=45)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # 子图2：统计摘要
    stats = {
        'Mean': np.mean(tasks_completed),
        'Std': np.std(tasks_completed),
        'Min': np.min(tasks_completed),
        'Max': np.max(tasks_completed),
    }

    ax2.bar(stats.keys(), stats.values(), color=['steelblue', 'orange', 'red', 'green'], alpha=0.7)
    ax2.set_ylabel('Value')
    ax2.set_title('Performance Statistics')
    ax2.grid(True, alpha=0.3)

    # 添加数值标签
    for i, (k, v) in enumerate(stats.items()):
        ax2.text(i, v + 0.5, f'{v:.2f}', ha='center', va='bottom', fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'evaluation_results.png'), dpi=300, bbox_inches='tight')
    plt.savefig(os.path.join(output_dir, 'evaluation_results.pdf'), bbox_inches='tight')
    print(f"✓ 评估结果已保存: {output_dir}/evaluation_results.png")
    plt.close()


def generate_latex_table(eval_results, output_dir):
    """生成 LaTeX 表格"""
    with open(eval_results, 'r') as f:
        data = json.load(f)

    results = data['results']
    tasks_completed = [r['tasks_completed'] for r in results]

    latex_table = r"""
\begin{table}[htbp]
\centering
\caption{Curriculum Learning Evaluation Results on Map\_02}
\label{tab:curriculum_results}
\begin{tabular}{lc}
\hline
\textbf{Metric} & \textbf{Value} \\
\hline
Mean Tasks Completed & $%.2f \pm %.2f$ \\
Minimum & $%d$ \\
Maximum & $%d$ \\
Median & $%.1f$ \\
\hline
\end{tabular}
\end{table}
""" % (
        np.mean(tasks_completed),
        np.std(tasks_completed),
        np.min(tasks_completed),
        np.max(tasks_completed),
        np.median(tasks_completed)
    )

    latex_file = os.path.join(output_dir, 'results_table.tex')
    with open(latex_file, 'w') as f:
        f.write(latex_table)

    print(f"✓ LaTeX 表格已保存: {latex_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='绘制课程学习训练结果')
    parser.add_argument('--tb_dir', type=str, required=True, help='TensorBoard 日志目录')
    parser.add_argument('--eval_results', type=str, required=True, help='评估结果 JSON 文件')
    parser.add_argument('--output_dir', type=str, default='outputs/figures', help='输出目录')

    args = parser.parse_args()

    # 创建输出目录
    os.makedirs(args.output_dir, exist_ok=True)

    print("=" * 70)
    print("课程学习结果可视化")
    print("=" * 70)
    print()

    # 加载 TensorBoard 数据
    print("加载 TensorBoard 数据...")
    stages_data = load_tensorboard_data(args.tb_dir)
    print(f"✓ 已加载 {len(stages_data)} 个阶段的数据")
    print()

    # 绘制训练曲线
    print("绘制训练曲线...")
    plot_training_curves(stages_data, args.output_dir)
    print()

    # 绘制评估结果
    print("绘制评估结果...")
    plot_evaluation_comparison(args.eval_results, args.output_dir)
    print()

    # 生成 LaTeX 表格
    print("生成 LaTeX 表格...")
    generate_latex_table(args.eval_results, args.output_dir)
    print()

    print("=" * 70)
    print("所有图表已生成完毕！")
    print(f"输出目录: {args.output_dir}")
    print("=" * 70)


if __name__ == '__main__':
    main()
