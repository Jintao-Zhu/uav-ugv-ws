#!/usr/bin/env python3
"""
Day8 Step 6.3: 测试 Communication-Aware Greedy

验证：
1. λ=0 时应该与 greedy 几乎一致
2. λ>0 时应该降低 outage_nc
"""

import sys
import json
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.env.core import AGCoopEnv
from agcoop.utils.seeding import seed_everything


def run_one_test(config, seed, method, lambda_val, out_dir):
    """运行单个测试"""
    config['episode']['seed'] = seed
    config['mapf']['enabled'] = False

    # 设置 comm_greedy 参数
    if method == "comm_greedy":
        if 'comm_greedy' not in config:
            config['comm_greedy'] = {}
        config['comm_greedy']['lambda'] = lambda_val
        config['comm_greedy']['radius'] = 8.0

    seed_everything(seed)

    env = AGCoopEnv(
        config,
        output_dir=str(out_dir),
        enable_logging=True,
        method=method,
        planner="none"
    )

    state = env.reset()

    step_count = 0
    done = False
    while not done:
        state, reward, done, info = env.step()
        step_count += 1

    env.close()

    # 加载 metrics
    with open(Path(out_dir) / "metrics.json") as f:
        metrics = json.load(f)

    return metrics


def main():
    print("=" * 70)
    print("Day8 Step 6.3: Communication-Aware Greedy 测试")
    print("=" * 70)
    print()

    # 配置
    config_path = "configs/day7_baseline.yaml"
    seed = 0

    # 加载基础配置
    with open(config_path) as f:
        base_config = yaml.safe_load(f)

    # 调整通信参数
    base_config['comm']['enabled'] = True
    base_config['comm']['snr_threshold_db'] = -12.0
    base_config['comm']['tx_power_db'] = -6.0

    print(f"配置文件: {config_path}")
    print(f"地图: {base_config['episode']['map_path']}")
    print(f"Seed: {seed}")
    print(f"SNR 阈值: {base_config['comm']['snr_threshold_db']} dB")
    print()

    # 测试 1: Greedy baseline
    print("测试 1: Greedy baseline...")
    import copy
    config = copy.deepcopy(base_config)
    out_dir = Path('outputs') / 'test_comm_greedy_baseline'
    metrics_greedy = run_one_test(config, seed, "greedy", 0.0, out_dir)
    print(f"  Tasks: {metrics_greedy['tasks_completed']}")
    print(f"  Outage_NC: {metrics_greedy['outage_percent_nc']:.1f}%")
    print(f"  Motion: {metrics_greedy['mean_step_motion']:.2f}")
    print()

    # 测试 2: Comm-Greedy with λ=0 (应该与 greedy 一致)
    print("测试 2: Comm-Greedy (λ=0, 应该与 greedy 一致)...")
    config = copy.deepcopy(base_config)
    out_dir = Path('outputs') / 'test_comm_greedy_lambda0'
    metrics_lambda0 = run_one_test(config, seed, "comm_greedy", 0.0, out_dir)
    print(f"  Tasks: {metrics_lambda0['tasks_completed']}")
    print(f"  Outage_NC: {metrics_lambda0['outage_percent_nc']:.1f}%")
    print(f"  Motion: {metrics_lambda0['mean_step_motion']:.2f}")
    print()

    # 测试 3: Comm-Greedy with λ=0.5
    print("测试 3: Comm-Greedy (λ=0.5)...")
    config = copy.deepcopy(base_config)
    out_dir = Path('outputs') / 'test_comm_greedy_lambda0.5'
    metrics_lambda05 = run_one_test(config, seed, "comm_greedy", 0.5, out_dir)
    print(f"  Tasks: {metrics_lambda05['tasks_completed']}")
    print(f"  Outage_NC: {metrics_lambda05['outage_percent_nc']:.1f}%")
    print(f"  Motion: {metrics_lambda05['mean_step_motion']:.2f}")
    print()

    # 测试 4: Comm-Greedy with λ=1.0
    print("测试 4: Comm-Greedy (λ=1.0)...")
    config = copy.deepcopy(base_config)
    out_dir = Path('outputs') / 'test_comm_greedy_lambda1.0'
    metrics_lambda10 = run_one_test(config, seed, "comm_greedy", 1.0, out_dir)
    print(f"  Tasks: {metrics_lambda10['tasks_completed']}")
    print(f"  Outage_NC: {metrics_lambda10['outage_percent_nc']:.1f}%")
    print(f"  Motion: {metrics_lambda10['mean_step_motion']:.2f}")
    print()

    # 验证
    print("=" * 70)
    print("验证结果")
    print("=" * 70)
    print()

    # 验证 1: λ=0 应该与 greedy 一致
    tasks_diff = abs(metrics_lambda0['tasks_completed'] - metrics_greedy['tasks_completed'])
    outage_diff = abs(metrics_lambda0['outage_percent_nc'] - metrics_greedy['outage_percent_nc'])

    print(f"1. λ=0 与 greedy 的差异:")
    print(f"   Tasks 差异: {tasks_diff} (应该 ≤ 1)")
    print(f"   Outage_NC 差异: {outage_diff:.1f}% (应该 ≤ 2%)")

    if tasks_diff <= 1 and outage_diff <= 2.0:
        print(f"   结果: ✅ PASS (λ=0 正确退化为 greedy)")
    else:
        print(f"   结果: ❌ FAIL (λ=0 未正确退化)")
    print()

    # 验证 2: λ 增大时 outage 应该有变化趋势
    print(f"2. λ 增大时的 outage_nc 变化:")
    print(f"   λ=0.0: {metrics_lambda0['outage_percent_nc']:.1f}%")
    print(f"   λ=0.5: {metrics_lambda05['outage_percent_nc']:.1f}%")
    print(f"   λ=1.0: {metrics_lambda10['outage_percent_nc']:.1f}%")

    # 检查是否有改善趋势（至少一个 λ>0 的配置比 λ=0 更好）
    has_improvement = (
        metrics_lambda05['outage_percent_nc'] < metrics_lambda0['outage_percent_nc'] or
        metrics_lambda10['outage_percent_nc'] < metrics_lambda0['outage_percent_nc']
    )

    if has_improvement:
        print(f"   结果: ✅ PASS (至少一个 λ>0 配置改善了 outage)")
    else:
        print(f"   结果: ⚠️  WARNING (λ>0 未改善 outage，可能需要调整参数)")
    print()

    print("=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
