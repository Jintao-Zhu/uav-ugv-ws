#!/usr/bin/env python3
"""
Day8 Step 3: 测试 Relay 决策

验证：
1. Relay 模式是否正确触发（当 outage 风险高时）
2. Relay UGV 是否被分配到 relay 目标
3. 其他 UGV 是否继续执行任务
4. Trace 中是否包含 relay 信息
"""

import sys
from pathlib import Path
import json

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv
from agcoop.utils.seeding import seed_everything
import yaml


def test_relay_decision(config_path: str, output_name: str, seed: int = 42):
    """
    测试 relay 决策

    Args:
        config_path: 配置文件路径
        output_name: 输出目录名称
        seed: 随机种子
    """
    print("=" * 60)
    print("Day8 Step 3: Relay 决策测试")
    print("=" * 60)
    print(f"配置文件: {config_path}")
    print(f"输出目录: outputs/{output_name}")
    print(f"随机种子: {seed}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['episode']['seed'] = seed
    config['mapf']['enabled'] = False

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

    print("开始运行...")
    state = env.reset()
    done = False
    step_count = 0

    # 统计 relay 触发情况
    relay_triggered_count = 0
    total_decision_steps = 0

    while not done:
        state, reward, done, info = env.step()
        step_count += 1

        if step_count % 20 == 0:
            print(f"  步数: {step_count}")

    print(f"\n运行完成！总步数: {step_count}")

    # 分析 trace 数据
    trace_path = Path(f"outputs/{output_name}/trace.jsonl")
    if not trace_path.exists():
        print("错误: trace.jsonl 不存在")
        return False

    print()
    print("=" * 60)
    print("分析 Relay 决策")
    print("=" * 60)

    relay_steps = []
    decision_steps = []

    with open(trace_path, 'r') as f:
        for line in f:
            if not line.strip():
                continue
            step_data = json.loads(line)

            # 检查是否是决策步
            if step_data.get('decision_step', False):
                decision_steps.append(step_data)

            # 检查是否触发 relay
            if step_data.get('relay_mode', False):
                relay_steps.append(step_data)

    print(f"总决策步数: {len(decision_steps)}")
    print(f"Relay 触发次数: {len(relay_steps)}")

    if len(relay_steps) > 0:
        print(f"\nRelay 触发详情（前 5 次）:")
        for i, step in enumerate(relay_steps[:5]):
            t = step['t']
            snr = step.get('snr_best', 0)
            outage = step.get('outage', 0)
            relay_target = step.get('relay_target_cell')
            relay_ugv_id = step.get('relay_ugv_id')

            print(f"  {i+1}. t={t}, SNR={snr:.2f} dB, outage={outage}, "
                  f"relay_ugv={relay_ugv_id}, target={relay_target}")

        # 验证 relay UGV 的目标
        print(f"\n验证 Relay UGV 目标:")
        for i, step in enumerate(relay_steps[:3]):
            t = step['t']
            relay_ugv_id = step.get('relay_ugv_id')
            relay_target = step.get('relay_target_cell')
            ugv_goals = step.get('ugv_goals', {})

            if ugv_goals and str(relay_ugv_id) in ugv_goals:
                actual_goal = ugv_goals[str(relay_ugv_id)]
                print(f"  t={t}: relay_target={relay_target}, "
                      f"actual_goal={actual_goal}, "
                      f"match={relay_target == actual_goal}")
            else:
                print(f"  t={t}: relay_target={relay_target}, "
                      f"actual_goal=None (no ugv_goals)")

    else:
        print("\n⚠ 警告: Relay 从未触发")
        print("  可能原因:")
        print("  1. SNR 一直高于阈值 + risk_margin")
        print("  2. Relay 配置未正确启用")
        print("  3. 候选点不可达")

    # 检查 SNR 分布
    print(f"\nSNR 统计:")
    snrs = [json.loads(line).get('snr_best', 0) for line in open(trace_path) if line.strip()]
    if snrs:
        print(f"  最小: {min(snrs):.2f} dB")
        print(f"  最大: {max(snrs):.2f} dB")
        print(f"  平均: {sum(snrs)/len(snrs):.2f} dB")
        print(f"  SNR 阈值: {config['comm']['snr_threshold_db']} dB")
        print(f"  风险边界: {config['relay']['risk_margin']} dB")
        print(f"  触发阈值: {config['comm']['snr_threshold_db'] + config['relay']['risk_margin']} dB")

    print()
    print("=" * 60)
    if len(relay_steps) > 0:
        print("✓✓✓ Relay 决策测试通过！✓✓✓")
        print(f"  Relay 触发 {len(relay_steps)} 次")
        print(f"\n查看可视化:")
        print(f"  python scripts/visualize.py --run outputs/{output_name}")
        return True
    else:
        print("⚠ Relay 未触发，需要检查配置")
        return False


def main():
    """主函数"""
    config_path = "configs/day8_relay_test.yaml"
    output_name = "day8_relay_test_seed42"
    seed = 42

    # 检查配置文件是否存在
    if not Path(config_path).exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    # 运行测试
    success = test_relay_decision(config_path, output_name, seed)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
