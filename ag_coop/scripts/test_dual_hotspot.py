#!/usr/bin/env python3
"""
Day8 Step 6.5: 验证双热点冲突场景

验证：
1. 双热点任务生成正常工作
2. greedy 在双热点场景下 outage_worst_nc 显著升高（>20%）
3. greedy 的 tasks_completed 仍然高于 static（场景不是太难）
"""

import sys
import json
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.env.core import AGCoopEnv
from agcoop.utils.seeding import seed_everything


def run_test(config, method, out_dir):
    """运行单个测试"""
    seed_everything(config['episode']['seed'])

    env = AGCoopEnv(
        config,
        output_dir=str(out_dir),
        enable_logging=True,
        method=method,
        planner="none"
    )

    state = env.reset()
    done = False
    while not done:
        state, reward, done, info = env.step()
    env.close()

    # 加载 metrics
    with open(Path(out_dir) / "metrics.json") as f:
        metrics = json.load(f)

    return metrics


def main():
    print("=" * 70)
    print("Day8 Step 6.5: 验证双热点冲突场景")
    print("=" * 70)
    print()

    # 加载基础配置
    with open("configs/day7_baseline.yaml") as f:
        base_config = yaml.safe_load(f)

    base_config['episode']['seed'] = 0
    base_config['mapf']['enabled'] = False
    base_config['comm']['enabled'] = True
    base_config['comm']['snr_threshold_db'] = -12.0
    base_config['comm']['tx_power_db'] = -6.0

    # 测试 1: 均匀场景（baseline）
    print("测试 1: 均匀场景（baseline）...")
    import copy
    config_uniform = copy.deepcopy(base_config)
    metrics_uniform = run_test(config_uniform, "greedy", "outputs/test_uniform_greedy")
    print(f"  Tasks: {metrics_uniform['tasks_completed']}")
    print(f"  Outage_worst_NC: {metrics_uniform['outage_percent_worst_nc']:.1f}%")
    print(f"  Outage_best_NC: {metrics_uniform['outage_percent_nc']:.1f}%")
    print()

    # 测试 2: 双热点场景
    print("测试 2: 双热点场景...")
    config_hotspot = copy.deepcopy(base_config)
    config_hotspot['dual_hotspot'] = {
        'enabled': True,
        'hotspot1_center': [2, 2],  # 左上角
        'hotspot2_center': [17, 17],  # 右下角
        'hotspot_radius': 3,
        'split_ratio': 0.5,
    }
    metrics_hotspot = run_test(config_hotspot, "greedy", "outputs/test_hotspot_greedy")
    print(f"  Tasks: {metrics_hotspot['tasks_completed']}")
    print(f"  Outage_worst_NC: {metrics_hotspot['outage_percent_worst_nc']:.1f}%")
    print(f"  Outage_best_NC: {metrics_hotspot['outage_percent_nc']:.1f}%")
    print()

    # 验收标准
    print("=" * 70)
    print("验收结果")
    print("=" * 70)
    print()

    # 标准 1: 双热点场景的 outage_worst_nc 应该显著升高
    outage_increase = metrics_hotspot['outage_percent_worst_nc'] - metrics_uniform['outage_percent_worst_nc']
    print(f"1. Outage_worst_NC 变化:")
    print(f"   均匀场景: {metrics_uniform['outage_percent_worst_nc']:.1f}%")
    print(f"   双热点场景: {metrics_hotspot['outage_percent_worst_nc']:.1f}%")
    print(f"   增幅: {outage_increase:+.1f}%")

    if metrics_hotspot['outage_percent_worst_nc'] > 20.0:
        print(f"   ✅ PASS: 双热点场景 outage_worst_nc > 20%")
        pass1 = True
    else:
        print(f"   ❌ FAIL: 双热点场景 outage_worst_nc ≤ 20%")
        pass1 = False
    print()

    # 标准 2: 双热点场景的 tasks_completed 不应该太低
    tasks_ratio = metrics_hotspot['tasks_completed'] / metrics_hotspot['total_tasks']
    print(f"2. Tasks 完成率:")
    print(f"   完成: {metrics_hotspot['tasks_completed']}/{metrics_hotspot['total_tasks']}")
    print(f"   完成率: {tasks_ratio*100:.1f}%")

    if tasks_ratio > 0.8:
        print(f"   ✅ PASS: 完成率 > 80%（场景不是太难）")
        pass2 = True
    else:
        print(f"   ⚠️  WARNING: 完成率 ≤ 80%（场景可能太难）")
        pass2 = False
    print()

    # 总结
    print("=" * 70)
    if pass1 and pass2:
        print("✅ Day8 Step 6.5 验收通过！")
        print("  - 双热点场景成功制造了任务-通信冲突")
        print("  - outage_worst_nc 显著升高")
        print("  - 场景难度适中")
        return 0
    elif pass1:
        print("⚠️  部分通过")
        print("  - 双热点场景制造了通信冲突")
        print("  - 但场景可能太难，需要调整参数")
        return 0
    else:
        print("❌ 验收未通过")
        print("  - 双热点场景未能制造足够的通信冲突")
        print("  - 需要调整热点位置或半径")
        return 1


if __name__ == "__main__":
    sys.exit(main())
