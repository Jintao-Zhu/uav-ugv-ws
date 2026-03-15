#!/usr/bin/env python3
"""
一键式训练与评估流程 - 应对审稿人意见

功能:
1. 训练 Vanilla PPO baseline
2. 训练 DQN baseline
3. 运行可扩展性测试
4. 生成论文图表
5. 生成审稿人回复材料

使用方法:
  python scripts/run_full_pipeline.py --mode all
  python scripts/run_full_pipeline.py --mode train_only
  python scripts/run_full_pipeline.py --mode eval_only
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
import time

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Pipeline:
    def __init__(self):
        self.project_root = project_root
        self.scripts_dir = project_root / "scripts"
        self.outputs_dir = project_root / "outputs"

        # 模型路径
        self.model_paths = {
            'vanilla_ppo': self.outputs_dir / "vanilla_ppo_baseline_map02" / "best_model" / "best_model.zip",
            'dqn': self.outputs_dir / "dqn_baseline_map02" / "best_model" / "best_model.zip",
            'ppo_v4': self.outputs_dir / "ppo_v4_golden_ratio_map02" / "best_model" / "best_model.zip",
        }

        self.log_file = self.outputs_dir / f"pipeline_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)

        with open(self.log_file, 'a') as f:
            f.write(log_msg + "\n")

    def run_command(self, command, description):
        """运行命令并记录（实时显示输出）"""
        self.log(f"\n{'='*70}")
        self.log(f"开始: {description}")
        self.log(f"命令: {command}")
        self.log(f"{'='*70}\n")

        start_time = time.time()

        try:
            # 使用 Popen 实时显示输出
            process = subprocess.Popen(
                command,
                shell=True,
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # 实时打印输出
            for line in process.stdout:
                print(line, end='')
                sys.stdout.flush()

            process.wait()

            elapsed = time.time() - start_time

            if process.returncode == 0:
                self.log(f"\n✓ 完成: {description} (耗时: {elapsed/60:.1f} 分钟)")
                return True
            else:
                self.log(f"\n✗ 失败: {description} (耗时: {elapsed/60:.1f} 分钟)")
                return False

        except Exception as e:
            elapsed = time.time() - start_time
            self.log(f"\n✗ 失败: {description} (耗时: {elapsed/60:.1f} 分钟)")
            self.log(f"错误信息: {e}")
            return False

    def check_model_exists(self, model_name):
        """检查模型是否存在"""
        model_path = self.model_paths.get(model_name)
        if model_path and model_path.exists():
            self.log(f"✓ 模型已存在: {model_name} ({model_path})")
            return True
        else:
            self.log(f"✗ 模型不存在: {model_name}")
            return False

    def train_vanilla_ppo(self, force=False):
        """训练 Vanilla PPO"""
        if not force and self.check_model_exists('vanilla_ppo'):
            self.log("跳过 Vanilla PPO 训练（模型已存在）")
            return True

        command = "python3 scripts/train_vanilla_ppo.py"
        return self.run_command(command, "训练 Vanilla PPO Baseline")

    def train_dqn(self, force=False):
        """训练 DQN"""
        if not force and self.check_model_exists('dqn'):
            self.log("跳过 DQN 训练（模型已存在）")
            return True

        command = "python3 scripts/train_dqn_baseline.py"
        return self.run_command(command, "训练 DQN Baseline")

    def evaluate_scalability(self):
        """运行可扩展性测试"""
        command = "python3 scripts/evaluate_scalability.py"
        return self.run_command(command, "可扩展性评估")

    def plot_results(self):
        """生成图表"""
        command = "python3 scripts/plot_scalability_results.py"
        return self.run_command(command, "生成论文图表")

    def generate_report(self):
        """生成总结报告"""
        self.log("\n" + "="*70)
        self.log("📊 流程执行总结")
        self.log("="*70)

        # 检查模型状态
        self.log("\n模型状态:")
        for model_name, model_path in self.model_paths.items():
            status = "✓ 存在" if model_path.exists() else "✗ 缺失"
            self.log(f"  {model_name}: {status}")

        # 检查结果文件
        self.log("\n结果文件:")
        scalability_dir = self.outputs_dir / "scalability_tests"
        if scalability_dir.exists():
            json_files = list(scalability_dir.glob("scalability_test_*.json"))
            if json_files:
                latest = max(json_files, key=lambda p: p.stat().st_mtime)
                self.log(f"  ✓ 可扩展性测试结果: {latest}")
            else:
                self.log(f"  ✗ 未找到可扩展性测试结果")

            plot_dir = scalability_dir / "plots"
            if plot_dir.exists():
                pdf_files = list(plot_dir.glob("*.pdf"))
                self.log(f"  ✓ 生成图表: {len(pdf_files)} 个 PDF 文件")
            else:
                self.log(f"  ✗ 未找到图表文件")

        self.log(f"\n完整日志: {self.log_file}")

    def run_full_pipeline(self, force_train=False):
        """运行完整流程"""
        self.log("\n" + "="*70)
        self.log("🚀 开始完整训练与评估流程")
        self.log("="*70)

        start_time = time.time()

        # 阶段 1: 训练 Baselines
        self.log("\n【阶段 1/4】训练学习类 Baselines")

        success_vanilla = self.train_vanilla_ppo(force=force_train)
        success_dqn = self.train_dqn(force=force_train)

        if not (success_vanilla and success_dqn):
            self.log("\n⚠️  部分训练失败，但继续执行评估...")

        # 阶段 2: 可扩展性评估
        self.log("\n【阶段 2/4】可扩展性评估")

        # 检查是否有足够的模型进行评估
        available_models = sum([
            self.check_model_exists('vanilla_ppo'),
            self.check_model_exists('dqn'),
            self.check_model_exists('ppo_v4')
        ])

        if available_models < 2:
            self.log("⚠️  可用模型不足 2 个，跳过评估")
        else:
            self.evaluate_scalability()

        # 阶段 3: 生成图表
        self.log("\n【阶段 3/4】生成论文图表")
        self.plot_results()

        # 阶段 4: 生成报告
        self.log("\n【阶段 4/4】生成总结报告")
        self.generate_report()

        elapsed = time.time() - start_time
        self.log(f"\n总耗时: {elapsed/3600:.2f} 小时")

        self.log("\n" + "="*70)
        self.log("✅ 流程执行完成")
        self.log("="*70)

    def run_train_only(self, force=False):
        """仅训练"""
        self.log("\n" + "="*70)
        self.log("🚀 开始训练 Baselines")
        self.log("="*70)

        self.train_vanilla_ppo(force=force)
        self.train_dqn(force=force)

        self.log("\n✅ 训练完成")

    def run_eval_only(self):
        """仅评估"""
        self.log("\n" + "="*70)
        self.log("🚀 开始评估与绘图")
        self.log("="*70)

        self.evaluate_scalability()
        self.plot_results()
        self.generate_report()

        self.log("\n✅ 评估完成")


def main():
    parser = argparse.ArgumentParser(
        description="一键式训练与评估流程 - 应对审稿人意见"
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['all', 'train_only', 'eval_only'],
        default='all',
        help='运行模式: all (完整流程), train_only (仅训练), eval_only (仅评估)'
    )

    parser.add_argument(
        '--force-train',
        action='store_true',
        help='强制重新训练（即使模型已存在）'
    )

    args = parser.parse_args()

    pipeline = Pipeline()

    if args.mode == 'all':
        pipeline.run_full_pipeline(force_train=args.force_train)
    elif args.mode == 'train_only':
        pipeline.run_train_only(force=args.force_train)
    elif args.mode == 'eval_only':
        pipeline.run_eval_only()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  流程被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n✗ 流程失败: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
