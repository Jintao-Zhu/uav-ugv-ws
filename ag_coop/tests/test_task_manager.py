#!/usr/bin/env python3
"""
TaskManager 单元测试

验证：
1. 任务添加和容量限制
2. 任务状态转换（active -> assigned -> done）
3. 任务过期处理
4. Top-M 任务选择（EDF, Random）
5. 统计信息正确性
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.tasks import Task, TaskManager


def test_task_manager_add_and_capacity():
    """测试：任务添加和容量限制"""
    print("\n测试：任务添加和容量限制")

    manager = TaskManager(max_active=5, top_m=3)

    # 添加 5 个任务（容量内）
    for i in range(5):
        task = Task(id=i, release_t=0, cell=(i, i), deadline_t=100)
        success = manager.add_task(task)
        assert success, f"任务 {i} 添加失败"

    assert manager.num_active == 5
    print(f"  ✓ 添加 5 个任务成功，活跃任务数: {manager.num_active}")

    # 尝试添加第 6 个任务（超过容量）
    task6 = Task(id=5, release_t=0, cell=(5, 5), deadline_t=100)
    success = manager.add_task(task6)
    assert not success, "容量满时应该添加失败"
    assert manager.num_active == 5
    print(f"  ✓ 容量满时添加失败，活跃任务数保持: {manager.num_active}")


def test_task_manager_state_transitions():
    """测试：任务状态转换"""
    print("\n测试：任务状态转换")

    manager = TaskManager(max_active=10, top_m=3)

    # 添加任务
    task = Task(id=0, release_t=0, cell=(1, 1), deadline_t=100)
    manager.add_task(task)

    assert manager.num_active == 1
    assert manager.num_assigned == 0
    assert manager.num_done == 0
    print(f"  ✓ 初始状态: active={manager.num_active}, assigned={manager.num_assigned}, done={manager.num_done}")

    # active -> assigned
    manager.mark_assigned(0, t=10)
    assert manager.num_active == 0
    assert manager.num_assigned == 1
    assert manager.num_done == 0
    print(f"  ✓ 分配后: active={manager.num_active}, assigned={manager.num_assigned}, done={manager.num_done}")

    # assigned -> done
    manager.mark_completed(0, t=50)
    assert manager.num_active == 0
    assert manager.num_assigned == 0
    assert manager.num_done == 1
    print(f"  ✓ 完成后: active={manager.num_active}, assigned={manager.num_assigned}, done={manager.num_done}")

    # 验证 tardiness
    task = manager.get_task(0)
    assert task.tardiness == 0, f"任务按时完成，tardiness 应为 0，实际为 {task.tardiness}"
    print(f"  ✓ tardiness: {task.tardiness} (按时完成)")


def test_task_manager_tardiness():
    """测试：延迟完成的 tardiness 计算"""
    print("\n测试：延迟完成的 tardiness 计算")

    manager = TaskManager(max_active=10, top_m=3)

    # 添加任务
    task = Task(id=0, release_t=0, cell=(1, 1), deadline_t=100)
    manager.add_task(task)

    # 延迟完成（t=120 > deadline=100）
    manager.mark_completed(0, t=120)

    task = manager.get_task(0)
    assert task.tardiness == 20, f"tardiness 应为 20，实际为 {task.tardiness}"
    print(f"  ✓ 延迟完成: deadline={task.deadline_t}, completed_t={task.completed_t}, tardiness={task.tardiness}")

    # 验证统计
    stats = manager.get_stats()
    assert stats['total_tardiness'] == 20
    assert stats['avg_tardiness'] == 20.0
    print(f"  ✓ 统计: total_tardiness={stats['total_tardiness']}, avg_tardiness={stats['avg_tardiness']:.1f}")


def test_task_manager_expiration():
    """测试：任务过期处理"""
    print("\n测试：任务过期处理")

    manager = TaskManager(max_active=10, top_m=3)

    # 添加 3 个任务，不同 deadline
    tasks = [
        Task(id=0, release_t=0, cell=(0, 0), deadline_t=50),
        Task(id=1, release_t=0, cell=(1, 1), deadline_t=100),
        Task(id=2, release_t=0, cell=(2, 2), deadline_t=150),
    ]

    for task in tasks:
        manager.add_task(task)

    # 分配任务 1
    manager.mark_assigned(1, t=10)

    assert manager.num_active == 2
    assert manager.num_assigned == 1
    print(f"  ✓ 初始: active={manager.num_active}, assigned={manager.num_assigned}")

    # t=100: 任务 0 过期（active），任务 1 过期（assigned）
    manager.expire_overdue_tasks(t=100)

    assert manager.num_active == 1  # 只剩任务 2
    assert manager.num_assigned == 0
    assert manager.num_expired == 2  # 任务 0 和 1
    print(f"  ✓ t=100 后: active={manager.num_active}, assigned={manager.num_assigned}, expired={manager.num_expired}")

    # 验证统计
    stats = manager.get_stats()
    assert stats['total_expired'] == 2
    print(f"  ✓ 统计: total_expired={stats['total_expired']}")


def test_task_manager_top_m_edf():
    """测试：Top-M 任务选择（EDF 策略）"""
    print("\n测试：Top-M 任务选择（EDF 策略）")

    manager = TaskManager(max_active=10, top_m=3)

    # 添加 5 个任务，不同 deadline
    tasks = [
        Task(id=0, release_t=0, cell=(0, 0), deadline_t=100),
        Task(id=1, release_t=0, cell=(1, 1), deadline_t=50),
        Task(id=2, release_t=0, cell=(2, 2), deadline_t=150),
        Task(id=3, release_t=0, cell=(3, 3), deadline_t=75),
        Task(id=4, release_t=0, cell=(4, 4), deadline_t=200),
    ]

    for task in tasks:
        manager.add_task(task)

    # 获取 Top-3（EDF）
    top_tasks = manager.get_top_m(t=0, policy="earliest_deadline")

    assert len(top_tasks) == 3
    assert top_tasks[0].id == 1  # deadline=50
    assert top_tasks[1].id == 3  # deadline=75
    assert top_tasks[2].id == 0  # deadline=100

    print(f"  ✓ Top-3 (EDF): {[t.id for t in top_tasks]}")
    print(f"  ✓ Deadlines: {[t.deadline_t for t in top_tasks]}")


def test_task_manager_top_m_random():
    """测试：Top-M 任务选择（Random 策略）"""
    print("\n测试：Top-M 任务选择（Random 策略）")

    manager = TaskManager(max_active=10, top_m=3, seed=42)

    # 添加 5 个任务
    tasks = [
        Task(id=i, release_t=0, cell=(i, i), deadline_t=100 + i * 10)
        for i in range(5)
    ]

    for task in tasks:
        manager.add_task(task)

    # 获取 Top-3（Random）
    top_tasks1 = manager.get_top_m(t=0, policy="random")
    top_tasks2 = manager.get_top_m(t=0, policy="random")

    assert len(top_tasks1) == 3
    assert len(top_tasks2) == 3

    # 两次调用应该不同（随机）
    ids1 = [t.id for t in top_tasks1]
    ids2 = [t.id for t in top_tasks2]

    print(f"  ✓ Top-3 (Random) 第一次: {ids1}")
    print(f"  ✓ Top-3 (Random) 第二次: {ids2}")

    # 验证可复现性（重置后）
    manager.reset()
    for task in tasks:
        manager.add_task(task)

    top_tasks3 = manager.get_top_m(t=0, policy="random")
    ids3 = [t.id for t in top_tasks3]

    assert ids3 == ids1, "重置后应该生成相同的随机序列"
    print(f"  ✓ 重置后 Top-3 (Random): {ids3} (与第一次一致)")


def test_task_manager_stats():
    """测试：统计信息正确性"""
    print("\n测试：统计信息正确性")

    manager = TaskManager(max_active=10, top_m=3)

    # 添加 5 个任务
    for i in range(5):
        task = Task(id=i, release_t=0, cell=(i, i), deadline_t=100)
        manager.add_task(task)

    # 完成 3 个任务（2 个按时，1 个延迟）
    manager.mark_completed(0, t=50)   # 按时
    manager.mark_completed(1, t=80)   # 按时
    manager.mark_completed(2, t=120)  # 延迟 20

    # 过期 1 个任务
    manager.expire_overdue_tasks(t=100)

    # 获取统计
    stats = manager.get_stats()

    assert stats['total_added'] == 5
    assert stats['total_completed'] == 3
    assert stats['total_expired'] == 2  # 任务 3 和 4
    assert stats['num_active'] == 0
    assert stats['num_done'] == 3
    assert stats['num_expired'] == 2
    assert stats['completion_rate'] == 3 / 5
    assert stats['expiration_rate'] == 2 / 5
    assert stats['total_tardiness'] == 20
    assert stats['avg_tardiness'] == 20 / 3

    print(f"  ✓ 统计信息:")
    print(f"    - total_added: {stats['total_added']}")
    print(f"    - total_completed: {stats['total_completed']}")
    print(f"    - total_expired: {stats['total_expired']}")
    print(f"    - completion_rate: {stats['completion_rate']:.2%}")
    print(f"    - expiration_rate: {stats['expiration_rate']:.2%}")
    print(f"    - total_tardiness: {stats['total_tardiness']}")
    print(f"    - avg_tardiness: {stats['avg_tardiness']:.2f}")


def test_task_manager_reset():
    """测试：reset() 重置管理器"""
    print("\n测试：reset() 重置管理器")

    manager = TaskManager(max_active=10, top_m=3)

    # 添加并完成一些任务
    for i in range(3):
        task = Task(id=i, release_t=0, cell=(i, i), deadline_t=100)
        manager.add_task(task)
        manager.mark_completed(i, t=50)

    stats_before = manager.get_stats()
    assert stats_before['total_added'] == 3
    assert stats_before['total_completed'] == 3

    # 重置
    manager.reset()

    stats_after = manager.get_stats()
    assert stats_after['total_added'] == 0
    assert stats_after['total_completed'] == 0
    assert manager.num_active == 0
    assert manager.num_done == 0

    print(f"  ✓ 重置前: total_added={stats_before['total_added']}, total_completed={stats_before['total_completed']}")
    print(f"  ✓ 重置后: total_added={stats_after['total_added']}, total_completed={stats_after['total_completed']}")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("TaskManager 单元测试")
    print("=" * 60)

    try:
        test_task_manager_add_and_capacity()
        test_task_manager_state_transitions()
        test_task_manager_tardiness()
        test_task_manager_expiration()
        test_task_manager_top_m_edf()
        test_task_manager_top_m_random()
        test_task_manager_stats()
        test_task_manager_reset()

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
