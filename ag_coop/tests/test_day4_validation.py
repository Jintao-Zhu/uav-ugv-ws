#!/usr/bin/env python3
"""
Day4 验收测试：使用校准后的参数

验收要点：
1. miss_rate 非零且合理（10%-40%）
2. mean_tardiness 可能为 0（取决于 EDF 策略效果）
3. completion_rate 合理（50%-80%）
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.tasks import TaskStream, TaskConfig, TaskManager, VirtualUAVExecutor
from agcoop.map import auto_load_map


def run_validation_episode():
    """运行验收 episode"""
    print("=" * 60)
    print("Day4 验收测试（使用校准后的参数）")
    print("=" * 60)

    # 使用校准后的参数
    config = {
        'horizon_steps': 500,
        'arrival_rate': 0.1,  # 校准后
        'deadline_min': 25,
        'deadline_max': 60,
        'max_active': 20,
        'top_m': 5,
        'service_time': 2,
        'seed': 42,
        'map_path': 'maps/map_01.map'
    }

    print(f"\n配置参数:")
    for k, v in config.items():
        print(f"  {k}: {v}")

    # 加载地图
    grid_map = auto_load_map(config['map_path'])

    # 创建任务配置
    task_config = TaskConfig(
        enabled=True,
        arrival_rate=config['arrival_rate'],
        deadline_min=config['deadline_min'],
        deadline_max=config['deadline_max'],
        max_active=config['max_active'],
        top_m=config['top_m'],
        service_time=config['service_time']
    )

    # 创建组件
    task_stream = TaskStream(task_config, grid_map.free_cells, seed=config['seed'])
    task_manager = TaskManager(max_active=config['max_active'], top_m=config['top_m'], seed=config['seed'])
    executor = VirtualUAVExecutor(uav_cell=grid_map.free_cells[0], service_time=config['service_time'])

    # 运行 episode（记录每步的 active_tasks 用于计算平均值）
    print(f"\n运行 {config['horizon_steps']} 步...")
    active_tasks_history = []

    for t in range(config['horizon_steps']):
        new_tasks = task_stream.generate_tasks(t, task_manager.num_active)
        for task in new_tasks:
            task_manager.add_task(task)

        task_manager.expire_overdue_tasks(t)
        executor.step(t, task_manager, policy="earliest_deadline")

        # 记录每步的 active 任务数
        active_tasks_history.append(task_manager.num_active)

        if (t + 1) % 100 == 0:
            print(f"  t={t+1}: active={task_manager.num_active}, done={task_manager.num_done}, expired={task_manager.num_expired}")

    # 获取 metrics
    stats = task_manager.get_stats()
    stream_stats = task_stream.get_stats()

    metrics = {
        # 任务统计
        'total_generated': stream_stats['total_generated'],
        'total_dropped': stream_stats['total_dropped'],
        'total_added': stats['total_added'],
        'total_completed': stats['total_completed'],
        'total_expired': stats['total_expired'],

        # 任务指标
        'completion_rate': stats['completion_rate'],
        'miss_rate': stats['total_expired'] / max(1, stats['total_added']),
        'mean_tardiness': stats['avg_tardiness'],

        # 完成时间分布
        'mean_completion_time': stats['mean_completion_time'],
        'p95_completion_time': stats['p95_completion_time'],

        # Slack 分析
        'mean_slack_at_assignment': stats['mean_slack_at_assignment'],
        'mean_slack_at_completion': stats['mean_slack_at_completion'],

        # 系统拥塞程度
        'avg_active_tasks': sum(active_tasks_history) / len(active_tasks_history),
        'active_tasks_end': task_manager.num_active,
    }

    # 打印 metrics
    print(f"\n{'='*60}")
    print(f"Metrics 结果")
    print(f"{'='*60}")
    print(f"\n任务统计:")
    print(f"  total_generated: {metrics['total_generated']}")
    print(f"  total_dropped: {metrics['total_dropped']}")
    print(f"  total_added: {metrics['total_added']}")
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

    print(f"\n系统拥塞程度:")
    print(f"  avg_active_tasks: {metrics['avg_active_tasks']:.2f}")
    print(f"  active_tasks_end: {metrics['active_tasks_end']}")

    # 验收检查
    print(f"\n{'='*60}")
    print(f"验收检查")
    print(f"{'='*60}")

    checks = []

    # 检查 1: miss_rate 在合理范围
    if 0.1 <= metrics['miss_rate'] <= 0.4:
        checks.append(("✓", f"miss_rate 在目标范围 ({metrics['miss_rate']:.2%})"))
    elif metrics['miss_rate'] < 0.1:
        checks.append(("⚠", f"miss_rate 偏低 ({metrics['miss_rate']:.2%})，压力不够"))
    else:
        checks.append(("⚠", f"miss_rate 偏高 ({metrics['miss_rate']:.2%})，压力过大"))

    # 检查 2: completion_rate 合理
    if 0.5 <= metrics['completion_rate'] <= 0.8:
        checks.append(("✓", f"completion_rate 合理 ({metrics['completion_rate']:.2%})"))
    else:
        checks.append(("⚠", f"completion_rate 可能不合理 ({metrics['completion_rate']:.2%})"))

    # 检查 3: 有任务完成
    if metrics['total_completed'] > 0:
        checks.append(("✓", f"有任务完成 ({metrics['total_completed']} 个)"))
    else:
        checks.append(("✗", "没有任务完成"))

    # 检查 4: 有任务过期
    if metrics['total_expired'] > 0:
        checks.append(("✓", f"有任务过期 ({metrics['total_expired']} 个)"))
    else:
        checks.append(("⚠", "没有任务过期"))

    # 检查 5: mean_tardiness（可能为 0）
    if metrics['mean_tardiness'] > 0:
        checks.append(("✓", f"有延迟完成 (tardiness={metrics['mean_tardiness']:.2f})"))
    else:
        checks.append(("ℹ", "所有完成的任务都按时完成（EDF 策略有效）"))

    for status, msg in checks:
        print(f"  {status} {msg}")

    # 保存 metrics
    output_dir = Path(__file__).parent.parent / "outputs" / "day4_validation"
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / "metrics.json", 'w') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Metrics 已保存: {output_dir / 'metrics.json'}")

    return metrics


def main():
    metrics = run_validation_episode()

    print(f"\n{'='*60}")
    print(f"✓ Day4 验收测试完成！")
    print(f"{'='*60}")
    print()


if __name__ == "__main__":
    main()
