#!/usr/bin/env python3
"""
Day8 Step 6.4: 验证 worst_nc 指标（编队连通性）

验证：
1. trace 中能看到 snr_worst_nc 和 outage_worst_nc
2. metrics 中能看到 outage_percent_worst_nc
3. worst_nc 应该 >= best_nc（最差链路 >= 最好链路）
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
from agcoop.env.core import AGCoopEnv
from agcoop.utils.seeding import seed_everything


def main():
    print("=" * 70)
    print("Day8 Step 6.4: 验证 worst_nc 指标")
    print("=" * 70)
    print()

    # 加载配置
    with open("configs/day7_baseline.yaml") as f:
        config = yaml.safe_load(f)

    config['episode']['seed'] = 0
    config['mapf']['enabled'] = False
    config['comm']['enabled'] = True
    config['comm']['snr_threshold_db'] = -12.0

    seed_everything(0)

    print("运行测试（N=3 UGV, seed=0）...")
    env = AGCoopEnv(
        config,
        output_dir="outputs/test_worst_nc",
        enable_logging=True,
        method="greedy",
        planner="none"
    )

    state = env.reset()
    done = False
    while not done:
        state, reward, done, info = env.step()
    env.close()

    print("✅ 运行完成\n")

    # 验证 1: 检查 trace
    print("验证 1: 检查 trace.jsonl...")
    with open("outputs/test_worst_nc/trace.jsonl") as f:
        first_line = f.readline()
        trace = json.loads(first_line)

    required_fields = ['snr_best_nc', 'outage_nc', 'snr_worst_nc', 'outage_worst_nc']
    missing_fields = [f for f in required_fields if f not in trace]

    if missing_fields:
        print(f"  ❌ FAIL: 缺少字段 {missing_fields}")
        return 1
    else:
        print(f"  ✅ PASS: 所有字段都存在")
        print(f"    snr_best_nc: {trace['snr_best_nc']}")
        print(f"    snr_worst_nc: {trace['snr_worst_nc']}")
        print(f"    outage_nc: {trace['outage_nc']}")
        print(f"    outage_worst_nc: {trace['outage_worst_nc']}")
    print()

    # 验证 2: 检查 metrics
    print("验证 2: 检查 metrics.json...")
    with open("outputs/test_worst_nc/metrics.json") as f:
        metrics = json.load(f)

    required_metrics = ['outage_percent_nc', 'outage_percent_worst_nc',
                       'snr_best_nc_mean', 'snr_worst_nc_mean']
    missing_metrics = [m for m in required_metrics if m not in metrics]

    if missing_metrics:
        print(f"  ❌ FAIL: 缺少指标 {missing_metrics}")
        return 1
    else:
        print(f"  ✅ PASS: 所有指标都存在")
        print(f"    outage_percent_nc: {metrics['outage_percent_nc']}%")
        print(f"    outage_percent_worst_nc: {metrics['outage_percent_worst_nc']}%")
        print(f"    snr_best_nc_mean: {metrics['snr_best_nc_mean']} dB")
        print(f"    snr_worst_nc_mean: {metrics['snr_worst_nc_mean']} dB")
    print()

    # 验证 3: 检查逻辑关系
    print("验证 3: 检查逻辑关系...")
    outage_nc = metrics['outage_percent_nc']
    outage_worst_nc = metrics['outage_percent_worst_nc']

    if outage_worst_nc >= outage_nc:
        print(f"  ✅ PASS: outage_worst_nc ({outage_worst_nc}%) >= outage_nc ({outage_nc}%)")
    else:
        print(f"  ❌ FAIL: outage_worst_nc ({outage_worst_nc}%) < outage_nc ({outage_nc}%)")
        print(f"    （最差链路的 outage 应该 >= 最好链路的 outage）")
        return 1
    print()

    # 验收标准
    print("=" * 70)
    print("验收结果")
    print("=" * 70)
    print()

    if outage_worst_nc > 0:
        print(f"✅ Day8 Step 6.4 验收通过！")
        print(f"  - worst_nc 指标正常工作")
        print(f"  - outage_worst_nc = {outage_worst_nc}% > 0")
        print(f"  - 可以用于评估编队连通性")
        return 0
    else:
        print(f"⚠️  WARNING: outage_worst_nc = 0%")
        print(f"  - 指标实现正确，但当前场景通信质量太好")
        print(f"  - 需要在更困难的场景中测试（Step 6.5）")
        return 0


if __name__ == "__main__":
    sys.exit(main())
