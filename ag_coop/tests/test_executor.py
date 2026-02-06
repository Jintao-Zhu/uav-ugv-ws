#!/usr/bin/env python3
"""
VirtualUAVExecutor 单元测试

验证：
1. 任务分配和完成流程
2. 飞行时间估算（Chebyshev 距离）
3. UAV 状态转换（空闲 -> 忙碌 -> 空闲）
4. 任务完成后 UAV 位置更新
5. 延迟完成和 tardiness 计算
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.tasks import Task, TaskManager, VirtualUAVExecutor, estimate_travel_time


def test_estimate_travel_time():
    """测试：飞行时间估算"""
    print("\n测试：飞行时间估算")

    # Chebyshev 距离测试
    test_cases = [
        ((0, 0), (3, 4), 4),  # max(3, 4) = 4
        ((0, 0), (5, 2), 5),  # max(5, 2) = 5
        ((1, 1), (1, 1), 0),  # 同一位置
        ((0, 0), (10, 10), 10),  # 对角线
    ]

    service_time = 2

    for uav_cell, task_cell, expected_travel in test_cases:
        total_time = estimate_travel_time(uav_cell, task_cell, service_time)
        expected_total = expected_travel + service_time

        assert total_time == expected_total, \
            f"估算错误: {uav_cell} -> {task_cell}, 期望 {expected_total}, 实际 {total_time}"

        print(f"  ✓ {uav_cell} -> {task_cell}: travel={expected_travel}, total={total_time}")


def test_executor_basic_flow():
    """测试：基本任务执行流程"""
    print("\n测试：基本任务执行流程")

    # 创建任务管理器
    manager = TaskManager(max_active=10, top_m=3)

    # 添加任务
    task = Task(id=0, release_t=0, cell=(5, 5), deadline_t=100)
    manager.add_task(task)

    # 创建执行器
    executor = VirtualUAVExecutor(uav_cell=(0, 0), service_time=2)

    print(f"  初始状态: uav_cell={executor.uav_cell}, busy={executor.uav_busy}")

    # 第一步：分配任务
    completed = executor.step(t=0, task_manager=manager, policy="earliest_deadline")

    assert completed is None, "第一步不应该完成任务"
    assert executor.uav_busy, "UAV 应该变为忙碌"
    assert executor.current_task_id == 0, "应该分配任务 0"
    assert executor.remaining_time == 7, "剩余时间应为 7（travel=5 + service=2）"

    print(f"  分配后: busy={executor.uav_busy}, task_id={executor.current_task_id}, remaining={executor.remaining_time}")

    # 执行 6 步（还未完成）
    for t in range(1, 7):
        completed = executor.step(t, manager, policy="earliest_deadline")
        assert completed is None, f"第 {t} 步不应该完成任务"
        assert executor.uav_busy, f"第 {t} 步 UAV 应该仍然忙碌"

    print(f"  执行 6 步后: remaining={executor.remaining_time}")

    # 第 7 步：完成任务
    completed = executor.step(t=7, task_manager=manager, policy="earliest_deadline")

    assert completed == 0, "第 7 步应该完成任务 0"
    assert not executor.uav_busy, "UAV 应该变为空闲"
    assert executor.current_task_id is None, "当前任务应为 None"
    assert executor.uav_cell == (5, 5), "UAV 应该移动到任务位置"

    print(f"  完成后: busy={executor.uav_busy}, uav_cell={executor.uav_cell}")

    # 验证任务状态
    task = manager.get_task(0)
    assert task.status == "done", "任务应该标记为完成"
    assert task.completed_t == 7, "完成时刻应为 7"
    assert task.tardiness == 0, "按时完成，tardiness 应为 0"

    print(f"  任务状态: status={task.status}, completed_t={task.completed_t}, tardiness={task.tardiness}")


def test_executor_multiple_tasks():
    """测试：连续执行多个任务"""
    print("\n测试：连续执行多个任务")

    manager = TaskManager(max_active=10, top_m=3)

    # 添加 3 个任务
    tasks = [
        Task(id=0, release_t=0, cell=(2, 2), deadline_t=100),
        Task(id=1, release_t=0, cell=(5, 5), deadline_t=100),
        Task(id=2, release_t=0, cell=(8, 8), deadline_t=100),
    ]

    for task in tasks:
        manager.add_task(task)

    executor = VirtualUAVExecutor(uav_cell=(0, 0), service_time=2)

    completed_tasks = []

    # 执行 30 步
    for t in range(30):
        completed = executor.step(t, manager, policy="earliest_deadline")
        if completed is not None:
            completed_tasks.append(completed)
            print(f"  t={t}: 完成任务 {completed}, uav_cell={executor.uav_cell}")

    # 验证完成了 3 个任务
    assert len(completed_tasks) == 3, f"应该完成 3 个任务，实际完成 {len(completed_tasks)}"
    assert completed_tasks == [0, 1, 2], "任务完成顺序应为 [0, 1, 2]"

    print(f"  ✓ 完成任务: {completed_tasks}")

    # 验证统计
    stats = manager.get_stats()
    assert stats['total_completed'] == 3
    assert stats['completion_rate'] == 1.0

    print(f"  ✓ 统计: total_completed={stats['total_completed']}, completion_rate={stats['completion_rate']:.2%}")


def test_executor_tardiness():
    """测试：延迟完成和 tardiness 计算"""
    print("\n测试：延迟完成和 tardiness 计算")

    manager = TaskManager(max_active=10, top_m=3)

    # 添加一个 deadline 很紧的任务
    task = Task(id=0, release_t=0, cell=(10, 10), deadline_t=10)
    manager.add_task(task)

    executor = VirtualUAVExecutor(uav_cell=(0, 0), service_time=2)

    # 执行直到任务完成
    completed = None
    for t in range(20):
        completed = executor.step(t, manager, policy="earliest_deadline")
        if completed is not None:
            break

    # 验证任务延迟完成
    task = manager.get_task(0)
    assert task.status == "done", "任务应该完成"
    assert task.completed_t > task.deadline_t, "任务应该延迟完成"
    assert task.tardiness > 0, "tardiness 应该 > 0"

    print(f"  ✓ 任务延迟完成:")
    print(f"    - deadline_t: {task.deadline_t}")
    print(f"    - completed_t: {task.completed_t}")
    print(f"    - tardiness: {task.tardiness}")


def test_executor_expiration():
    """测试：任务过期"""
    print("\n测试：任务过期")

    manager = TaskManager(max_active=10, top_m=3)

    # 添加两个任务，一个 deadline 很近
    tasks = [
        Task(id=0, release_t=0, cell=(10, 10), deadline_t=5),  # 很快过期
        Task(id=1, release_t=0, cell=(2, 2), deadline_t=100),  # 正常
    ]

    for task in tasks:
        manager.add_task(task)

    executor = VirtualUAVExecutor(uav_cell=(0, 0), service_time=2)

    # 执行 20 步，每步检查过期任务
    for t in range(20):
        # 过期超时任务
        manager.expire_overdue_tasks(t)

        # 执行一步
        executor.step(t, manager, policy="earliest_deadline")

    # 验证任务 0 过期
    task0 = manager.get_task(0)
    assert task0.status == "expired", "任务 0 应该过期"

    # 验证任务 1 完成
    task1 = manager.get_task(1)
    assert task1.status == "done", "任务 1 应该完成"

    print(f"  ✓ 任务 0: status={task0.status} (过期)")
    print(f"  ✓ 任务 1: status={task1.status} (完成)")

    # 验证统计
    stats = manager.get_stats()
    assert stats['total_expired'] == 1
    assert stats['total_completed'] == 1

    print(f"  ✓ 统计: expired={stats['total_expired']}, completed={stats['total_completed']}")


def test_executor_edf_policy():
    """测试：EDF 策略选择任务"""
    print("\n测试：EDF 策略选择任务")

    manager = TaskManager(max_active=10, top_m=3)

    # 添加 3 个任务，不同 deadline
    tasks = [
        Task(id=0, release_t=0, cell=(2, 2), deadline_t=100),
        Task(id=1, release_t=0, cell=(3, 3), deadline_t=50),   # 最早 deadline
        Task(id=2, release_t=0, cell=(4, 4), deadline_t=75),
    ]

    for task in tasks:
        manager.add_task(task)

    executor = VirtualUAVExecutor(uav_cell=(0, 0), service_time=2)

    # 第一步：应该选择任务 1（deadline=50）
    executor.step(t=0, task_manager=manager, policy="earliest_deadline")

    assert executor.current_task_id == 1, "应该选择任务 1（最早 deadline）"

    print(f"  ✓ EDF 策略选择任务 {executor.current_task_id} (deadline={tasks[1].deadline_t})")


def test_executor_reset():
    """测试：reset() 重置执行器"""
    print("\n测试：reset() 重置执行器")

    manager = TaskManager(max_active=10, top_m=3)

    task = Task(id=0, release_t=0, cell=(5, 5), deadline_t=100)
    manager.add_task(task)

    executor = VirtualUAVExecutor(uav_cell=(0, 0), service_time=2)

    # 执行几步
    for t in range(3):
        executor.step(t, manager, policy="earliest_deadline")

    assert executor.uav_busy, "执行器应该忙碌"

    # 重置
    executor.reset(initial_cell=(10, 10))

    assert not executor.uav_busy, "重置后应该空闲"
    assert executor.current_task_id is None, "重置后当前任务应为 None"
    assert executor.uav_cell == (10, 10), "重置后位置应为 (10, 10)"

    print(f"  ✓ 重置后: busy={executor.uav_busy}, uav_cell={executor.uav_cell}")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("VirtualUAVExecutor 单元测试")
    print("=" * 60)

    try:
        test_estimate_travel_time()
        test_executor_basic_flow()
        test_executor_multiple_tasks()
        test_executor_tardiness()
        test_executor_expiration()
        test_executor_edf_policy()
        test_executor_reset()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        print()

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
