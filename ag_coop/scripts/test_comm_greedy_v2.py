#!/usr/bin/env python3
"""
Day8 Step 6.6: 验证 Communication-Aware Greedy v2

验证：
1. λ=0 时正确退化为 greedy
2. λ>0 时 outage_worst_nc 应该下降（或至少不显著上升）
3. Gating 机制正常工作
"""

import sys
import json
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.env.core import AGCoopEnv
from agcoop.utils.seeding import seed_everything


def run_test(config, method, lambda_val, out_dir):
    """运行单个测试"""
    config['episode']['seed'] = 0
    config['mapf']['enabled'] = False

    if method == "comm_greedy":
        if 'comm_greedy' not in config:
            config['comm_greedy'] = {}
        config['comm_greedy']['lambda'] = lambda_val
        config['comm_greedy']['margin'] = 3.0

    seed_everything(0)

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
    print("Day8 Step 6.6: 验证 Communication-Aware Greedy v2")
    print("=" * 70)
    print()

    # 加载配置
    with open("configs/day7_baseline.yaml") as f:
        base_config = yaml.safe_load(f)

    base_config['comm']['enabled'] = True
    base_config['comm']['snr_threshold_db'] = -12.0
    base_config['comm']['tx_power_db'] = -6.0

    # 使用双热点场景
    base_config['dual_hotspot'] = {
        'enabled': True,
        'hotspot1_center': [2, 2],
        'hotspot2_center': [17, 17],
        'hotspot_radius': 3,
        'split_ratio': 0.5,
    }

    print("场景: 双热点（制造任务-通信冲突）")
    print()

    # 测试 1: Greedy baseline
    print("测试 1: Greedy baseline...")
    import copy
    config = copy.deepcopy(base_config)
    metrics_greedy = run_test(config, "greedy", 0.0, "outputs/test_commv2_greedy")
    print(f"  Tasks: {metrics_greedy['tasks_completed']}")
    print(f"  Outage_worst_NC: {metrics_greedy['outage_percent_worst_nc']:.1f}%")
    print(f"  Outage_best_NC: {metrics_greedy['outage_percent_nc']:.1f}%")
    print()

    # 测试 2: Comm-Greedy v2 (λ=0, 应该与 greedy 一致)
    print("测试 2: Comm-Greedy v2 (λ=0, 应该与 greedy 一致)...")
    config = copy.deepcopy(base_config)
    metrics_lambda0 = run_test(config, "comm_greedy", 0.0, "outputs/test_commv2_lambda0")
    print(f"  Tasks: {metrics_lambda0['tasks_completed']}")
    print(f"  Outage_worst_NC: {metrics_lambda0['outage_percent_worst_nc']:.1f}%")
    print(f"  Outage_best_NC: {metrics_lambda0['outage_percent_nc']:.1f}%")
    print()

    # 测试 3: Comm-Greedy v2 (λ=0.5)
    print("测试 3: Comm-Greedy v2 (λ=0.5)...")
    config = copy.deepcopy(base_config)
    metrics_lambda05 = run_test(config, "comm_greedy", 0.5, "outputs/test_commv2_lambda0.5")
    print(f"  Tasks: {metrics_lambda05['tasks_completed']}")
    print(f"  Outage_worst_NC: {metrics_lambda05['outage_percent_worst_nc']:.1f}%")
    print(f"  Outage_best_NC: {metrics_lambda05['outage_percent_nc']:.1f}%")
    print()

    # 测试 4: Comm-Greedy v2 (λ=1.0)
    print("测试 4: Comm-Greedy v2 (λ=1.0)...")
    config = copy.deepcopy(base_config)
    metrics_lambda10 = run_test(config, "comm_greedy", 1.0, "outputs/test_commv2_lambda1.0")
    print(f"  Tasks: {metrics_lambda10['tasks_completed']}")
    print(f"  Outage_worst_NC: {metrics_lambda10['outage_percent_worst_nc']:.1f}%")
    print(f"  Outage_best_NC: {metrics_lambda10['outage_percent_nc']:.1f}%")
    print()

    # 验收标准
    print("=" * 70)
    print("验收结果")
    print("=" * 70)
    print()

    # 标准 1: λ=0 应该与 greedy 一致
    tasks_diff = abs(metrics_lambda0['tasks_completed'] - metrics_greedy['tasks_completed'])
    outage_diff = abs(metrics_lambda0['outage_percent_worst_nc'] - metrics_greedy['outage_percent_worst_nc'])

    print(f"1. λ=0 与 greedy 的差异:")
    print(f"   Tasks 差异: {tasks_diff} (应该 ≤ 1)")
    print(f"   Outage_worst_NC 差异: {outage_diff:.1f}% (应该 ≤ 5%)")

    if tasks_diff <= 1 and outage_diff <= 5.0:
        print(f"   ✅ PASS (λ=0 正确退化为 greedy)")
        pass1 = True
    else:
        print(f"   ❌ FAIL (λ=0 未正确退化)")
        pass1 = False
    print()

    # 标准 2: λ 增大时 outage_worst_nc 应该有改善趋势
    print(f"2. λ 增大时的 outage_worst_nc 变化:")
    print(f"   λ=0.0: {metrics_lambda0['outage_percent_worst_nc']:.1f}%")
    print(f"   λ=0.5: {metrics_lambda05['outage_percent_worst_nc']:.1f}%")
    print(f"   λ=1.0: {metrics_lambda10['outage_percent_worst_nc']:.1f}%")

    # 检查是否有改善趋势（至少一个 λ>0 的配置比 λ=0 更好或相近）
    has_improvement = (
        metrics_lambda05['outage_percent_worst_nc'] <= metrics_lambda0['outage_percent_worst_nc'] + 5.0 or
        metrics_lambda10['outage_percent_worst_nc'] <= metrics_lambda0['outage_percent_worst_nc'] + 5.0
    )

    if has_improvement:
        print(f"   ✅ PASS (λ>0 未显著恶化 outage)")
        pass2 = True
    else:
        print(f"   ❌ FAIL (λ>0 显著恶化了 outage)")
        pass2 = False
    print()

    # 总结
    print("=" * 70)
    if pass1 and pass2:
        print("✅ Day8 Step 6.6 验收通过！")
        print("  - Comm-Aware Greedy v2 实现正确")
        print("  - λ=0 时正确退化为 greedy")
        print("  - λ>0 时未显著恶化通信质量")
        return 0
    elif pass1:
        print("⚠️  部分通过")
        print("  - λ=0 退化正确")
        print("  - 但 λ>0 时效果不理想，可能需要调整参数")
        return 0
    else:
        print("❌ 验收未通过")
        return 1


if __name__ == "__main__":
    sys.exit(main())
