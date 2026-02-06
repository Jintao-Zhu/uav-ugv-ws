#!/usr/bin/env python3
"""
Step 5: 两组最小实验验证

验证：
1. 调高阈值（更苛刻）→ outage 上升
2. 调低阈值（更宽松）→ outage 下降
3. trace 里 snr_best 有波动，不是常数
"""

import sys
from pathlib import Path
import yaml
import json

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from agcoop.env.core import AGCoopEnv


def run_experiment(threshold_db: float, experiment_name: str):
    """
    运行一次实验

    Args:
        threshold_db: SNR 阈值（dB）
        experiment_name: 实验名称
    """
    print("\n" + "=" * 60)
    print(f"实验: {experiment_name}")
    print(f"SNR 阈值: {threshold_db} dB")
    print("=" * 60)

    # 加载配置
    config_path = Path(__file__).parent / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 修改配置
    config['comm']['enabled'] = True
    config['comm']['snr_threshold_db'] = threshold_db
    config['episode']['horizon_steps'] = 200  # 短 episode

    # 创建环境
    output_dir = Path(__file__).parent / "outputs" / f"step5_{experiment_name}"
    env = AGCoopEnv(config, output_dir=str(output_dir), enable_logging=True)

    # 运行 episode
    print("\n运行 episode...")
    state = env.reset()
    for t in range(config['episode']['horizon_steps']):
        state, reward, done, info = env.step()
        if (t + 1) % 50 == 0:
            print(f"  进度: {t+1}/{config['episode']['horizon_steps']}")
        if done:
            break

    env.close()

    # 读取 metrics
    metrics_path = output_dir / "metrics.json"
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    print(f"\n结果:")
    print(f"  snr_best_mean:  {metrics['snr_best_mean']:.2f} dB")
    print(f"  snr_best_min:   {metrics['snr_best_min']:.2f} dB")
    print(f"  outage_percent: {metrics['outage_percent']:.2f}%")
    print(f"  outage_steps:   {metrics['outage_steps']}/{metrics['steps']}")
    print(f"  max_outage_streak: {metrics['max_outage_streak']}")

    # 读取 trace 前几行，检查 snr_best 波动
    trace_path = output_dir / "trace.jsonl"
    snr_values = []
    with open(trace_path, 'r') as f:
        for i, line in enumerate(f):
            if i >= 10:  # 只读前 10 行
                break
            trace_entry = json.loads(line)
            snr_values.append(trace_entry['snr_best'])

    print(f"\ntrace 前 10 步的 snr_best:")
    print(f"  {[f'{s:.2f}' for s in snr_values]}")

    # 检查波动
    snr_std = sum((s - sum(snr_values)/len(snr_values))**2 for s in snr_values) ** 0.5 / len(snr_values)
    print(f"  标准差: {snr_std:.2f} dB")

    if snr_std > 0.01:
        print(f"  ✓ snr_best 有波动（不是常数）")
    else:
        print(f"  ⚠ snr_best 几乎不变（可能 UGV 都在原点）")

    return metrics


def main():
    """运行两组实验"""
    print("\n" + "=" * 60)
    print("Step 5: 两组最小实验验证")
    print("=" * 60)

    # 实验 1: 调高阈值（更苛刻）
    metrics_strict = run_experiment(-5.0, "strict_threshold")

    # 实验 2: 调低阈值（更宽松）
    metrics_loose = run_experiment(-40.0, "loose_threshold")

    # 对比结果
    print("\n" + "=" * 60)
    print("对比结果")
    print("=" * 60)

    print(f"\n实验 1（严格阈值 -5.0 dB）:")
    print(f"  outage_percent: {metrics_strict['outage_percent']:.2f}%")
    print(f"  outage_steps:   {metrics_strict['outage_steps']}")

    print(f"\n实验 2（宽松阈值 -40.0 dB）:")
    print(f"  outage_percent: {metrics_loose['outage_percent']:.2f}%")
    print(f"  outage_steps:   {metrics_loose['outage_steps']}")

    # 验证
    print("\n" + "=" * 60)
    print("验收")
    print("=" * 60)

    outage_diff = abs(metrics_strict['outage_percent'] - metrics_loose['outage_percent'])
    print(f"\noutage_percent 差异: {outage_diff:.2f}%")

    if outage_diff > 1.0:
        print("✓ outage_percent 明显不同（差异 > 1%）")
    else:
        print("⚠ outage_percent 差异不明显（可能 UGV 都在原点，SNR 很高）")

    # 检查严格阈值是否导致更多 outage
    if metrics_strict['outage_percent'] >= metrics_loose['outage_percent']:
        print("✓ 严格阈值导致更多 outage（符合预期）")
    else:
        print("⚠ 严格阈值反而 outage 更少（不符合预期，可能数据问题）")

    print("\n" + "=" * 60)
    print("✓ Step 5 完成！")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
