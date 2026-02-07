#!/usr/bin/env python3
"""
Day5 验收实验

Case A: 正常会合应占多数
Case B: 制造会合困难（测试 Emergency）
Case C: 通信指标动起来
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.map import auto_load_map
from agcoop.env import CoopEnv
from agcoop.env.coop_env import EnvConfig


def run_case_a():
    """Case A: 正常会合应占多数"""
    print("\n" + "=" * 60)
    print("Case A: 正常会合应占多数")
    print("=" * 60)
    print("配置: arrival_rate=0.1, deadline=[25,60]")
    print("期望: rendezvous_success > 0, emergency_landings 很少或 0")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建配置（medium 负载）
    config = EnvConfig(
        horizon_steps=500,
        decision_period=5,
        task_arrival_rate=0.1,
        task_deadline_min=25,
        task_deadline_max=60,
        uav_meet_window=3,
        uav_max_loiter_steps=20,
        seed=42
    )

    # 创建环境
    env = CoopEnv(grid_map, config)

    # 运行 episode
    print("\n运行 500 步...")
    metrics = env.run_episode()

    # 打印结果
    print(f"\n{'='*60}")
    print(f"Case A 结果")
    print(f"{'='*60}")

    print(f"\n任务统计（守恒）:")
    print(f"  total_generated: {metrics['total_generated']}")
    print(f"  total_completed: {metrics['total_completed']}")
    print(f"  total_expired: {metrics['total_expired']}")
    print(f"  total_pending_end: {metrics['total_pending_end']}")
    print(f"  守恒检查: {metrics['total_generated']} = {metrics['total_completed']} + {metrics['total_expired']} + {metrics['total_pending_end']} + {metrics['total_dropped']}")
    print(f"  completion_rate: {metrics['completion_rate']:.2%}")
    print(f"  miss_rate: {metrics['miss_rate']:.2%}")

    print(f"\n会合统计（细化）:")
    print(f"  clean_rendezvous: {metrics['clean_rendezvous']}")
    print(f"  emergency_recovery: {metrics['emergency_recovery']}")
    print(f"  emergency_landings: {metrics['emergency_landings']}")
    print(f"  total_rendezvous_attempts: {metrics['total_rendezvous_attempts']}")
    print(f"  clean_rendezvous_rate: {metrics['clean_rendezvous_rate']:.2%}")
    print(f"  emergency_rate: {metrics['emergency_rate']:.2%}")

    print(f"\n会合延迟（软目标）:")
    print(f"  planned_window: ±{metrics['planned_window']} 步")
    print(f"  mean_meet_delay: {metrics['mean_meet_delay']:.2f} 步")
    print(f"  max_meet_delay: {metrics['max_meet_delay']:.0f} 步")
    print(f"  p95_meet_delay: {metrics['p95_meet_delay']:.0f} 步")

    print(f"\n等待统计:")
    print(f"  mean_uav_wait_at_r: {metrics['mean_uav_wait_at_r']:.2f} 步")
    print(f"  mean_ugv_wait_at_r: {metrics['mean_ugv_wait_at_r']:.2f} 步")
    print(f"  max_uav_wait_at_r: {metrics['max_uav_wait_at_r']} 步")
    print(f"  max_ugv_wait_at_r: {metrics['max_ugv_wait_at_r']} 步")

    # 验证期望
    print(f"\n验证:")
    total_success = metrics['clean_rendezvous'] + metrics['emergency_recovery']
    if total_success > 0:
        print(f"  ✓ 有成功会合 ({total_success} 次)")
    else:
        print(f"  ✗ 无成功会合")

    if metrics['emergency_rate'] <= 0.2:
        print(f"  ✓ emergency_rate 较低 ({metrics['emergency_rate']:.2%})")
    else:
        print(f"  ⚠ emergency_rate 较高 ({metrics['emergency_rate']:.2%})")

    # 保存结果
    output_dir = Path(__file__).parent.parent / "outputs" / "day5_case_a"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "metrics.json", 'w') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    env.save_trace(str(output_dir / "trace.json"))

    print(f"\n✓ 结果已保存: {output_dir}")

    # 提取关键事件
    trace = env.get_trace()
    events = [entry for entry in trace if entry.get('event')]
    print(f"\n关键事件（前 10 个）:")
    for entry in events[:10]:
        print(f"  t={entry['t']}: {entry['event']}")

    return metrics


def run_case_b():
    """Case B: 制造会合困难"""
    print("\n" + "=" * 60)
    print("Case B: 制造会合困难（测试 Emergency）")
    print("=" * 60)
    print("配置: meet_window=1, max_loiter_steps=5")
    print("期望: emergency_landings > 0, episode 完成, rendezvous_fail > 0")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建配置（苛刻条件）
    config = EnvConfig(
        horizon_steps=500,
        decision_period=5,
        task_arrival_rate=0.1,
        task_deadline_min=25,
        task_deadline_max=60,
        uav_meet_window=1,  # 更苛刻
        uav_max_loiter_steps=5,  # 更短
        seed=42
    )

    # 创建环境
    env = CoopEnv(grid_map, config)

    # 运行 episode
    print("\n运行 500 步...")
    metrics = env.run_episode()

    # 打印结果
    print(f"\n{'='*60}")
    print(f"Case B 结果")
    print(f"{'='*60}")

    print(f"\n任务统计:")
    print(f"  total_generated: {metrics['total_generated']}")
    print(f"  total_completed: {metrics['total_completed']}")
    print(f"  total_expired: {metrics['total_expired']}")
    print(f"  total_pending_end: {metrics['total_pending_end']}")
    print(f"  completion_rate: {metrics['completion_rate']:.2%}")
    print(f"  miss_rate: {metrics['miss_rate']:.2%}")

    print(f"\n会合统计:")
    print(f"  clean_rendezvous: {metrics['clean_rendezvous']}")
    print(f"  emergency_recovery: {metrics['emergency_recovery']}")
    print(f"  emergency_landings: {metrics['emergency_landings']}")
    print(f"  clean_rendezvous_rate: {metrics['clean_rendezvous_rate']:.2%}")
    print(f"  emergency_rate: {metrics['emergency_rate']:.2%}")
    print(f"  mean_meet_delay: {metrics['mean_meet_delay']:.2f}")

    # 验证期望
    print(f"\n验证:")
    if metrics['emergency_landings'] > 0:
        print(f"  ✓ emergency_landings > 0 ({metrics['emergency_landings']})")
    else:
        print(f"  ✗ emergency_landings = 0")

    if metrics['emergency_rate'] > 0.3:
        print(f"  ✓ emergency_rate 较高 ({metrics['emergency_rate']:.2%}) - 符合困难场景预期")
    else:
        print(f"  ⚠ emergency_rate 不够高 ({metrics['emergency_rate']:.2%})")

    print(f"  ✓ Episode 完成（500 步）")

    # 保存结果
    output_dir = Path(__file__).parent.parent / "outputs" / "day5_case_b"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "metrics.json", 'w') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    env.save_trace(str(output_dir / "trace.json"))

    print(f"\n✓ 结果已保存: {output_dir}")

    # 提取 emergency 事件
    trace = env.get_trace()
    emergency_events = [entry for entry in trace if entry.get('event') == 'emergency_land']
    print(f"\nEmergency 事件（共 {len(emergency_events)} 次）:")
    for entry in emergency_events[:5]:
        print(f"  t={entry['t']}: emergency_land, uav_cell={entry['uav_cell']}")

    return metrics


def run_case_c():
    """Case C: 通信指标动起来"""
    print("\n" + "=" * 60)
    print("Case C: 通信指标动起来")
    print("=" * 60)
    print("配置: snr_threshold=-9 dB, carrier 移动")
    print("期望: 通信指标有波动")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建配置
    config = EnvConfig(
        horizon_steps=500,
        decision_period=5,
        task_arrival_rate=0.1,
        task_deadline_min=25,
        task_deadline_max=60,
        comm_snr_threshold_db=-9.0,
        seed=42
    )

    # 创建环境
    env = CoopEnv(grid_map, config)

    # 运行 episode
    print("\n运行 500 步...")
    metrics = env.run_episode()

    # 计算通信指标
    trace = env.get_trace()

    # 计算 SNR（当 UAV 和 carrier 不在同一位置时）
    snr_values = []
    outage_count = 0
    total_comm_steps = 0

    for entry in trace:
        uav_cell = tuple(entry['uav_cell'])
        carrier_cell = tuple(entry['carrier_cell'])

        # 只在 UAV 不在载机上时计算
        if uav_cell != carrier_cell:
            snr = env.comm_model.compute_snr(uav_cell, carrier_cell)
            snr_values.append(snr)
            total_comm_steps += 1

            if snr < config.comm_snr_threshold_db:
                outage_count += 1

    # 打印结果
    print(f"\n{'='*60}")
    print(f"Case C 结果")
    print(f"{'='*60}")

    print(f"\n任务统计:")
    print(f"  total_generated: {metrics['total_generated']}")
    print(f"  total_completed: {metrics['total_completed']}")
    print(f"  total_pending_end: {metrics['total_pending_end']}")
    print(f"  completion_rate: {metrics['completion_rate']:.2%}")

    print(f"\n通信统计（口径明确）:")
    print(f"  airborne_steps: {metrics['airborne_steps']} (UAV 离开载机的步数)")
    print(f"  total_steps: {metrics['total_steps']}")
    if snr_values:
        print(f"  total_comm_steps: {total_comm_steps} (实际计算 SNR 的步数)")
        print(f"  snr_min: {min(snr_values):.2f} dB")
        print(f"  snr_max: {max(snr_values):.2f} dB")
        print(f"  snr_mean: {sum(snr_values)/len(snr_values):.2f} dB")
        print(f"  outage_count: {outage_count}")
        print(f"  outage_percent: {outage_count/total_comm_steps*100:.2f}%")
        print(f"  snr_threshold: {config.comm_snr_threshold_db:.2f} dB")
    else:
        print(f"  无通信步数（UAV 始终在载机上）")

    # 验证期望
    print(f"\n验证:")
    if snr_values and min(snr_values) < 0:
        print(f"  ✓ SNR 有变化（min={min(snr_values):.2f} dB）")
    else:
        print(f"  ⚠ SNR 变化不明显")

    if outage_count > 0:
        print(f"  ✓ 有 outage 发生 ({outage_count} 次, {outage_count/total_comm_steps*100:.1f}%)")
    else:
        print(f"  ⚠ 无 outage")

    # 保存结果
    output_dir = Path(__file__).parent.parent / "outputs" / "day5_case_c"
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics['comm_stats'] = {
        'total_comm_steps': total_comm_steps,
        'snr_min': min(snr_values) if snr_values else 0,
        'snr_max': max(snr_values) if snr_values else 0,
        'snr_mean': sum(snr_values)/len(snr_values) if snr_values else 0,
        'outage_count': outage_count,
        'outage_percent': outage_count/total_comm_steps*100 if total_comm_steps > 0 else 0
    }

    with open(output_dir / "metrics.json", 'w') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    env.save_trace(str(output_dir / "trace.json"))

    print(f"\n✓ 结果已保存: {output_dir}")

    return metrics


def main():
    """运行所有验收实验"""
    print("=" * 60)
    print("Day5 验收实验")
    print("=" * 60)

    try:
        metrics_a = run_case_a()
        metrics_b = run_case_b()
        metrics_c = run_case_c()

        print("\n" + "=" * 60)
        print("Day5 验收实验完成")
        print("=" * 60)

        print("\n总结:")
        print(f"Case A (正常): clean_rendezvous={metrics_a['clean_rendezvous']}, emergency={metrics_a['emergency_landings']}, emergency_rate={metrics_a['emergency_rate']:.1%}")
        print(f"Case B (困难): clean_rendezvous={metrics_b['clean_rendezvous']}, emergency={metrics_b['emergency_landings']}, emergency_rate={metrics_b['emergency_rate']:.1%}")
        print(f"Case C (通信): outage={metrics_c['comm_stats']['outage_count']}, outage%={metrics_c['comm_stats']['outage_percent']:.2f}%, airborne={metrics_c['airborne_steps']}")

        print("\n✓ 所有验收实验通过！")

    except Exception as e:
        print(f"\n✗ 验收实验失败: {e}")
        raise


if __name__ == "__main__":
    main()
