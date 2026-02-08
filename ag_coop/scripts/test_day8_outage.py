#!/usr/bin/env python3
"""
Day8 Step 1: 测试 outage 工况

验证通信参数调整后是否能产生 outage > 5%
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv
from agcoop.utils.seeding import seed_everything
import json
import yaml


def run_outage_test(config_path: str, output_name: str, seed: int = 0):
    """
    运行 outage 测试

    Args:
        config_path: 配置文件路径
        output_name: 输出目录名称
        seed: 随机种子
    """
    print(f"=" * 60)
    print(f"Day8 Step 1: Outage 测试")
    print(f"=" * 60)
    print(f"配置文件: {config_path}")
    print(f"输出目录: outputs/{output_name}")
    print(f"随机种子: {seed}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['episode']['seed'] = seed
    config['mapf']['enabled'] = False  # 使用 greedy 方法

    # 设置随机种子
    seed_everything(seed)

    # 创建环境
    env = AGCoopEnv(
        config,
        output_dir=f"outputs/{output_name}",
        enable_logging=True,
        method="greedy",
        planner="none"
    )

    # 运行
    print("开始运行...")
    state = env.reset()
    done = False
    step_count = 0
    outage_count = 0

    while not done:
        state, reward, done, info = env.step()

        # 统计 outage（从 state 中获取）
        if hasattr(state, 'outage') and state.outage:
            outage_count += 1

        step_count += 1

        # 每 100 步打印一次进度
        if step_count % 100 == 0:
            current_outage_pct = (outage_count / step_count) * 100
            print(f"  步数: {step_count}, 当前 outage: {outage_count} ({current_outage_pct:.2f}%)")

    print(f"\n运行完成！总步数: {step_count}")

    # 读取最终 metrics
    metrics_path = Path(f"outputs/{output_name}/metrics.json")
    if metrics_path.exists():
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)

        print(f"\n" + "=" * 60)
        print("最终指标:")
        print("=" * 60)
        print(f"  总步数: {metrics.get('total_steps', 0)}")
        print(f"  Outage 次数: {metrics.get('outage_count', 0)}")
        print(f"  Outage 百分比: {metrics.get('outage_percent', 0):.2f}%")
        print(f"  平均 SNR: {metrics.get('snr_mean', 0):.2f} dB")
        print(f"  最小 SNR: {metrics.get('snr_min', 0):.2f} dB")
        print(f"  最大 SNR: {metrics.get('snr_max', 0):.2f} dB")
        print()
        print(f"  任务完成数: {metrics.get('task_completed', 0)}")
        print(f"  任务过期数: {metrics.get('task_missed', 0)}")
        print(f"  完成率: {metrics.get('task_completion_rate', 0):.2f}%")
        print()

        outage_pct = metrics.get('outage_percent', 0)
        if outage_pct > 5.0:
            print(f"✓ 成功！Outage 百分比 {outage_pct:.2f}% > 5%")
            print(f"  该配置满足 Day8 Step 1 的要求")
        elif outage_pct > 0:
            print(f"⚠ Outage 百分比 {outage_pct:.2f}% > 0% 但 < 5%")
            print(f"  建议进一步调整通信参数")
        else:
            print(f"✗ 失败！Outage 百分比为 0%")
            print(f"  需要调整通信参数以产生 outage")

        print("=" * 60)

        return metrics
    else:
        print(f"错误: 未找到 metrics.json")
        return None


def main():
    """主函数"""
    # 测试配置
    config_path = "configs/day8_outage_test.yaml"
    output_name = "day8_outage_test_seed0"
    seed = 0

    # 检查配置文件是否存在
    if not Path(config_path).exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    # 运行测试
    metrics = run_outage_test(config_path, output_name, seed)

    if metrics is None:
        sys.exit(1)

    # 检查是否满足要求
    outage_pct = metrics.get('outage_percent', 0)
    if outage_pct > 5.0:
        print(f"\n✓ Day8 Step 1 完成！")
        print(f"  可以使用以下命令查看可视化:")
        print(f"  python scripts/visualize.py --run outputs/{output_name}")
        sys.exit(0)
    else:
        print(f"\n⚠ 需要进一步调整参数")
        sys.exit(1)


if __name__ == '__main__':
    main()
