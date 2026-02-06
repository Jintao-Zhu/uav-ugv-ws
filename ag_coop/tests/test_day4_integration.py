#!/usr/bin/env python3
"""
Day4 任务系统集成测试

验证：
1. TaskStream + TaskManager + VirtualUAVExecutor 完整流程
2. 任务生成、分配、完成、过期
3. Metrics 统计（completion_rate, deadline_miss_rate, tardiness 等）
4. Trace 记录（new_tasks, assigned_task, completed_tasks 等）
"""

import sys
from pathlib import Path
import json

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.tasks import Task, TaskStream, TaskConfig, TaskManager, VirtualUAVExecutor
from agcoop.map import auto_load_map


def run_episode(
    horizon_steps: int = 200,
    arrival_rate: float = 0.2,
    deadline_min: int = 25,
    deadline_max: int = 60,
    max_active: int = 20,
    top_m: int = 5,
    service_time: int = 2,
    policy: str = "earliest_deadline",
    seed: int = 42,
    map_path: str = "maps/map_01.map"
):
    """
    运行一个完整的 episode

    Returns:
        metrics, trace
    """
    print(f"\n{'='*60}")
    print(f"运行 Episode")
    print(f"{'='*60}")
    print(f"  horizon_steps: {horizon_steps}")
    print(f"  arrival_rate: {arrival_rate}")
    print(f"  deadline: [{deadline_min}, {deadline_max}]")
    print(f"  policy: {policy}")
    print(f"  seed: {seed}")

    # 加载地图
    grid_map = auto_load_map(map_path)
    print(f"\n地图加载:")
    print(f"  - 尺寸: {grid_map.width}x{grid_map.height}")
    print(f"  - Free cells: {len(grid_map.free_cells)}")

    # 创建任务配置
    task_config = TaskConfig(
        enabled=True,
        arrival_rate=arrival_rate,
        deadline_min=deadline_min,
        deadline_max=deadline_max,
        max_active=max_active,
        top_m=top_m,
        service_time=service_time
    )

    # 创建任务流生成器
    task_stream = TaskStream(task_config, grid_map.free_cells, seed=seed)

    # 创建任务管理器
    task_manager = TaskManager(max_active=max_active, top_m=top_m, seed=seed)

    # 创建虚拟执行器
    initial_cell = grid_map.free_cells[0]  # 从第一个 free cell 开始
    executor = VirtualUAVExecutor(uav_cell=initial_cell, service_time=service_time)

    print(f"\n初始状态:")
    print(f"  - UAV 位置: {executor.uav_cell}")

    # Trace 记录
    trace = []

    # Metrics 累计
    completion_times = []

    # 运行 episode
    print(f"\n运行 episode...")
    for t in range(horizon_steps):
        # 1. 生成新任务
        new_tasks = task_stream.generate_tasks(t, task_manager.num_active)
        new_task_ids = []
        for task in new_tasks:
            success = task_manager.add_task(task)
            if success:
                new_task_ids.append(task.id)

        # 2. 过期超时任务
        task_manager.expire_overdue_tasks(t)

        # 3. 执行器执行一步
        completed_task_id = executor.step(t, task_manager, policy=policy)

        # 4. 记录 trace
        trace_entry = {
            't': t,
            'new_task_ids': new_task_ids,
            'assigned_task_id': executor.current_task_id if executor.uav_busy and executor.remaining_time == estimate_travel_time(executor.uav_cell, task_manager.get_task(executor.current_task_id).cell if executor.current_task_id else (0, 0), service_time) else None,
            'completed_task_ids': [completed_task_id] if completed_task_id is not None else [],
            'uav_remaining_time': executor.remaining_time,
            'num_active': task_manager.num_active,
            'num_assigned': task_manager.num_assigned,
            'num_done': task_manager.num_done,
            'num_expired': task_manager.num_expired,
        }
        trace.append(trace_entry)

        # 5. 记录完成时间
        if completed_task_id is not None:
            task = task_manager.get_task(completed_task_id)
            completion_time = task.completed_t - task.release_t
            completion_times.append(completion_time)

        # 进度显示
        if (t + 1) % 50 == 0:
            print(f"  t={t+1}: active={task_manager.num_active}, done={task_manager.num_done}, expired={task_manager.num_expired}")

    # 计算 metrics
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
        'expiration_rate': stats['expiration_rate'],
        'deadline_miss_rate': stats['total_expired'] / max(1, stats['total_added']),  # 过期即 miss

        # Tardiness 指标
        'total_tardiness': stats['total_tardiness'],
        'mean_tardiness': stats['avg_tardiness'],

        # 完成时间指标
        'mean_completion_time': sum(completion_times) / max(1, len(completion_times)),
        'p95_completion_time': sorted(completion_times)[int(len(completion_times) * 0.95)] if completion_times else 0,

        # Episode 信息
        'horizon_steps': horizon_steps,
        'policy': policy,
        'seed': seed,
    }

    return metrics, trace


def estimate_travel_time(uav_cell, task_cell, service_time):
    """估算飞行时间（Chebyshev 距离）"""
    dx = abs(task_cell[1] - uav_cell[1])
    dy = abs(task_cell[0] - uav_cell[0])
    return max(dx, dy) + service_time


def print_metrics(metrics):
    """打印 metrics"""
    print(f"\n{'='*60}")
    print(f"Metrics 统计")
    print(f"{'='*60}")

    print(f"\n任务统计:")
    print(f"  - total_generated: {metrics['total_generated']}")
    print(f"  - total_dropped: {metrics['total_dropped']}")
    print(f"  - total_added: {metrics['total_added']}")
    print(f"  - total_completed: {metrics['total_completed']}")
    print(f"  - total_expired: {metrics['total_expired']}")

    print(f"\n任务指标:")
    print(f"  - completion_rate: {metrics['completion_rate']:.2%}")
    print(f"  - expiration_rate: {metrics['expiration_rate']:.2%}")
    print(f"  - deadline_miss_rate: {metrics['deadline_miss_rate']:.2%}")

    print(f"\nTardiness 指标:")
    print(f"  - total_tardiness: {metrics['total_tardiness']}")
    print(f"  - mean_tardiness: {metrics['mean_tardiness']:.2f}")

    print(f"\n完成时间指标:")
    print(f"  - mean_completion_time: {metrics['mean_completion_time']:.2f}")
    print(f"  - p95_completion_time: {metrics['p95_completion_time']:.2f}")


def analyze_trace(trace):
    """分析 trace"""
    print(f"\n{'='*60}")
    print(f"Trace 分析")
    print(f"{'='*60}")

    # 统计事件
    total_new_tasks = sum(len(entry['new_task_ids']) for entry in trace)
    total_completed_tasks = sum(len(entry['completed_task_ids']) for entry in trace)

    # 找到有事件的步
    new_task_steps = [entry['t'] for entry in trace if entry['new_task_ids']]
    completed_task_steps = [entry['t'] for entry in trace if entry['completed_task_ids']]

    print(f"\n事件统计:")
    print(f"  - 生成任务的步数: {len(new_task_steps)}")
    print(f"  - 完成任务的步数: {len(completed_task_steps)}")
    print(f"  - 总生成任务数: {total_new_tasks}")
    print(f"  - 总完成任务数: {total_completed_tasks}")

    print(f"\n前 5 个生成任务的步:")
    for t in new_task_steps[:5]:
        entry = trace[t]
        print(f"  t={t}: new_task_ids={entry['new_task_ids']}")

    print(f"\n前 5 个完成任务的步:")
    for t in completed_task_steps[:5]:
        entry = trace[t]
        print(f"  t={t}: completed_task_ids={entry['completed_task_ids']}, remaining_time={entry['uav_remaining_time']}")


def main():
    """主函数"""
    print("=" * 60)
    print("Day4 任务系统集成测试")
    print("=" * 60)

    try:
        # 运行 episode
        metrics, trace = run_episode(
            horizon_steps=200,
            arrival_rate=0.2,
            deadline_min=25,
            deadline_max=60,
            policy="earliest_deadline",
            seed=42
        )

        # 打印 metrics
        print_metrics(metrics)

        # 分析 trace
        analyze_trace(trace)

        # 验收检查
        print(f"\n{'='*60}")
        print(f"验收检查")
        print(f"{'='*60}")

        checks = []

        # 检查 1: 有任务完成
        if metrics['total_completed'] > 0:
            checks.append(("✓", f"有任务完成 ({metrics['total_completed']} 个)"))
        else:
            checks.append(("✗", "没有任务完成"))

        # 检查 2: 有任务过期
        if metrics['total_expired'] > 0:
            checks.append(("✓", f"有任务过期 ({metrics['total_expired']} 个)"))
        else:
            checks.append(("⚠", "没有任务过期（可能 deadline 太宽松）"))

        # 检查 3: 有 tardiness
        if metrics['total_tardiness'] > 0:
            checks.append(("✓", f"有延迟完成 (tardiness={metrics['total_tardiness']})"))
        else:
            checks.append(("⚠", "没有延迟完成（所有任务按时完成）"))

        # 检查 4: completion_rate 合理
        if 0.3 <= metrics['completion_rate'] <= 0.9:
            checks.append(("✓", f"completion_rate 合理 ({metrics['completion_rate']:.2%})"))
        else:
            checks.append(("⚠", f"completion_rate 可能不合理 ({metrics['completion_rate']:.2%})"))

        for status, msg in checks:
            print(f"  {status} {msg}")

        print(f"\n{'='*60}")
        print(f"✓ 集成测试完成！")
        print(f"{'='*60}")
        print()

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
