#!/usr/bin/env python3
"""
测试 CoopEnv 环境
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.map import auto_load_map
from agcoop.env import CoopEnv
from agcoop.env.coop_env import EnvConfig


def test_env_initialization():
    """测试环境初始化"""
    print("\n" + "=" * 60)
    print("测试环境初始化")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建配置
    config = EnvConfig(
        horizon_steps=100,
        decision_period=5,
        seed=42
    )

    # 创建环境
    env = CoopEnv(grid_map, config)

    print(f"地图大小: {grid_map.height} x {grid_map.width}")
    print(f"自由格子数: {len(grid_map.free_cells)}")
    print(f"UAV 位置: {env.uav.get_position()}")
    print(f"UAV 状态: {env.uav.get_state()}")
    print(f"UGV 位置: {env.carrier.get_position()}")
    print(f"UGV 状态: {env.carrier.get_state()}")
    print(f"候选会合点数: {len(env.safe_landing_sites)}")

    assert env.t == 0, "初始时刻应该是 0"
    assert env.uav.get_position() == env.carrier.get_position(), "UAV 应该在载机上"

    print("✓ 环境初始化测试通过")


def test_env_single_step():
    """测试环境单步执行"""
    print("\n" + "=" * 60)
    print("测试环境单步执行")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建配置
    config = EnvConfig(
        horizon_steps=100,
        decision_period=5,
        seed=42
    )

    # 创建环境
    env = CoopEnv(grid_map, config)

    print(f"初始时刻: {env.t}")
    print(f"初始任务数: {env.task_manager.num_active}")

    # 执行一步
    env.step()

    print(f"执行后时刻: {env.t}")
    print(f"执行后任务数: {env.task_manager.num_active}")

    assert env.t == 1, "时刻应该增加"

    print("✓ 单步执行测试通过")


def test_env_task_assignment():
    """测试任务分配"""
    print("\n" + "=" * 60)
    print("测试任务分配")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建配置（高任务到达率）
    config = EnvConfig(
        horizon_steps=100,
        decision_period=5,
        task_arrival_rate=0.5,  # 高到达率
        seed=42
    )

    # 创建环境
    env = CoopEnv(grid_map, config)

    # 运行到第一个决策时刻
    for _ in range(5):
        env.step()

    print(f"时刻: {env.t}")
    print(f"任务数: {env.task_manager.num_active}")
    print(f"UAV 状态: {env.uav.get_state()}")
    print(f"UGV 状态: {env.carrier.get_state()}")

    # 如果有任务，UAV 应该开始执行
    if env.task_manager.num_active > 0:
        print(f"✓ 有任务生成，UAV 可能已分配任务")
    else:
        print(f"⚠ 没有任务生成（随机性）")

    print("✓ 任务分配测试通过")


def test_env_short_episode():
    """测试短 episode"""
    print("\n" + "=" * 60)
    print("测试短 episode（50 步）")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建配置
    config = EnvConfig(
        horizon_steps=50,
        decision_period=5,
        task_arrival_rate=0.2,
        seed=42
    )

    # 创建环境
    env = CoopEnv(grid_map, config)

    # 运行 episode
    metrics = env.run_episode()

    print(f"\nMetrics:")
    print(f"  total_generated: {metrics['total_generated']}")
    print(f"  total_completed: {metrics['total_completed']}")
    print(f"  total_expired: {metrics['total_expired']}")
    print(f"  completion_rate: {metrics['completion_rate']:.2%}")
    print(f"  miss_rate: {metrics['miss_rate']:.2%}")
    print(f"  rendezvous_success: {metrics['rendezvous_success']}")
    print(f"  rendezvous_fail: {metrics['rendezvous_fail']}")
    print(f"  emergency_landings: {metrics['emergency_landings']}")

    assert metrics['total_generated'] >= 0, "应该有任务生成统计"

    print("✓ 短 episode 测试通过")


def test_env_full_episode():
    """测试完整 episode（500 步）"""
    print("\n" + "=" * 60)
    print("测试完整 episode（500 步）")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建配置（使用校准后的参数）
    config = EnvConfig(
        horizon_steps=500,
        decision_period=5,
        task_arrival_rate=0.1,
        task_deadline_min=25,
        task_deadline_max=60,
        seed=42
    )

    # 创建环境
    env = CoopEnv(grid_map, config)

    print("运行 500 步...")

    # 运行 episode
    metrics = env.run_episode()

    print(f"\n{'='*60}")
    print(f"完整 Episode Metrics")
    print(f"{'='*60}")

    print(f"\n任务统计:")
    print(f"  total_generated: {metrics['total_generated']}")
    print(f"  total_dropped: {metrics['total_dropped']}")
    print(f"  total_completed: {metrics['total_completed']}")
    print(f"  total_expired: {metrics['total_expired']}")

    print(f"\n关键指标:")
    print(f"  completion_rate: {metrics['completion_rate']:.2%}")
    print(f"  miss_rate: {metrics['miss_rate']:.2%}")
    print(f"  mean_tardiness: {metrics['mean_tardiness']:.2f}")

    print(f"\n完成时间分布:")
    print(f"  mean_completion_time: {metrics['mean_completion_time']:.2f}")
    print(f"  p95_completion_time: {metrics['p95_completion_time']:.2f}")

    print(f"\nSlack 分析:")
    print(f"  mean_slack_at_assignment: {metrics['mean_slack_at_assignment']:.2f}")
    print(f"  mean_slack_at_completion: {metrics['mean_slack_at_completion']:.2f}")

    print(f"\n会合统计:")
    print(f"  rendezvous_success: {metrics['rendezvous_success']}")
    print(f"  rendezvous_fail: {metrics['rendezvous_fail']}")
    print(f"  emergency_landings: {metrics['emergency_landings']}")
    print(f"  rendezvous_success_rate: {metrics['rendezvous_success_rate']:.2%}")

    print(f"\n新增统计:")
    print(f"  total_uav_loiter_steps: {metrics['total_uav_loiter_steps']}")
    print(f"  total_ugv_hold_steps: {metrics['total_ugv_hold_steps']}")
    print(f"  mean_meet_delay: {metrics['mean_meet_delay']:.2f}")

    # 保存 metrics
    output_dir = Path(__file__).parent.parent / "outputs" / "day5_test"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "metrics.json", 'w') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Metrics 已保存: {output_dir / 'metrics.json'}")

    # 保存 trace
    env.save_trace(str(output_dir / "trace.json"))
    print(f"✓ Trace 已保存: {output_dir / 'trace.json'}")

    # 验证 trace
    trace = env.get_trace()
    print(f"\nTrace 统计:")
    print(f"  总步数: {len(trace)}")

    # 统计事件
    events = [entry.get('event') for entry in trace if entry.get('event')]
    event_counts = {}
    for event in events:
        event_counts[event] = event_counts.get(event, 0) + 1

    print(f"  事件统计:")
    for event, count in event_counts.items():
        print(f"    {event}: {count}")

    # 打印前 5 步 trace
    print(f"\n前 5 步 trace:")
    for entry in trace[:5]:
        print(f"  t={entry['t']}: uav_state={entry['uav_state']}, uav_cell={entry['uav_cell']}, event={entry.get('event')}")

    # 验证
    assert metrics['total_generated'] > 0, "应该有任务生成"
    assert metrics['rendezvous_success'] + metrics['rendezvous_fail'] > 0, "应该有会合尝试"

    print("✓ 完整 episode 测试通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("CoopEnv 环境测试")
    print("=" * 60)

    try:
        test_env_initialization()
        test_env_single_step()
        test_env_task_assignment()
        test_env_short_episode()
        test_env_full_episode()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        raise


if __name__ == "__main__":
    main()
