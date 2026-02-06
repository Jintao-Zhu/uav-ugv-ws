#!/usr/bin/env python3
"""
Task 数据结构单元测试

验证：
1. Task 创建和字段验证
2. 状态转换（active -> assigned -> done）
3. 过期处理（expired）
4. JSON 序列化和反序列化
5. 辅助方法（time_to_deadline 等）
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.tasks import Task


def test_task_creation():
    """测试：Task 创建和字段验证"""
    print("\n测试：Task 创建和字段验证")

    # 创建基本任务
    task = Task(
        id=1,
        release_t=10,
        cell=(5, 8),
        deadline_t=100
    )

    assert task.id == 1
    assert task.release_t == 10
    assert task.cell == (5, 8)
    assert task.deadline_t == 100
    assert task.assigned_t is None
    assert task.completed_t is None
    assert task.status == "active"
    assert task.tardiness == 0

    print(f"  ✓ Task 创建成功: {task}")

    # 测试字段验证
    try:
        bad_task = Task(id=2, release_t=100, cell=(1, 1), deadline_t=50)
        assert False, "应该抛出异常（deadline < release）"
    except AssertionError as e:
        print(f"  ✓ 字段验证正确: {e}")


def test_task_state_transitions():
    """测试：任务状态转换"""
    print("\n测试：任务状态转换")

    task = Task(id=1, release_t=10, cell=(5, 8), deadline_t=100)

    # active -> assigned
    assert task.is_active()
    task.assign(t=20)
    assert task.is_assigned()
    assert task.assigned_t == 20
    assert task.status == "assigned"
    print(f"  ✓ active -> assigned: {task}")

    # assigned -> done
    task.complete(t=50)
    assert task.is_done()
    assert task.completed_t == 50
    assert task.status == "done"
    assert task.tardiness == 0  # 50 < 100，无延迟
    print(f"  ✓ assigned -> done (on time): {task}")

    # 测试延迟完成
    task2 = Task(id=2, release_t=10, cell=(3, 4), deadline_t=100)
    task2.assign(t=20)
    task2.complete(t=120)  # 超过 deadline
    assert task2.tardiness == 20  # 120 - 100 = 20
    print(f"  ✓ 延迟完成: tardiness={task2.tardiness}")


def test_task_expiration():
    """测试：任务过期"""
    print("\n测试：任务过期")

    task = Task(id=1, release_t=10, cell=(5, 8), deadline_t=100)

    # 未分配直接过期
    task.expire(t=100)
    assert task.is_expired()
    assert task.status == "expired"
    print(f"  ✓ 未分配任务过期: {task}")

    # 已分配但未完成，过期
    task2 = Task(id=2, release_t=10, cell=(3, 4), deadline_t=100)
    task2.assign(t=20)
    task2.expire(t=100)
    assert task2.is_expired()
    print(f"  ✓ 已分配任务过期: {task2}")


def test_task_json_serialization():
    """测试：JSON 序列化和反序列化"""
    print("\n测试：JSON 序列化和反序列化")

    # 创建任务
    task = Task(
        id=42,
        release_t=10,
        cell=(5, 8),
        deadline_t=100,
        assigned_t=20,
        completed_t=50,
        status="done",
        tardiness=0
    )

    # 转换为字典
    task_dict = task.to_dict()
    assert task_dict['id'] == 42
    assert task_dict['cell'] == [5, 8]  # list 格式
    assert task_dict['status'] == "done"
    print(f"  ✓ to_dict(): {task_dict}")

    # 转换为 JSON
    task_json = task.to_json()
    print(f"  ✓ to_json(): {task_json}")

    # 从字典恢复
    task_restored = Task.from_dict(task_dict)
    assert task_restored.id == task.id
    assert task_restored.cell == task.cell
    assert task_restored.status == task.status
    print(f"  ✓ from_dict(): {task_restored}")

    # 从 JSON 恢复
    task_from_json = Task.from_json(task_json)
    assert task_from_json.id == task.id
    assert task_from_json.cell == task.cell
    assert task_from_json.status == task.status
    print(f"  ✓ from_json(): {task_from_json}")


def test_task_helper_methods():
    """测试：辅助方法"""
    print("\n测试：辅助方法")

    task = Task(id=1, release_t=10, cell=(5, 8), deadline_t=100)

    # time_to_deadline
    assert task.time_to_deadline(t=50) == 50  # 100 - 50
    assert task.time_to_deadline(t=100) == 0
    assert task.time_to_deadline(t=120) == -20  # 已过期
    print(f"  ✓ time_to_deadline(t=50): {task.time_to_deadline(50)}")
    print(f"  ✓ time_to_deadline(t=100): {task.time_to_deadline(100)}")
    print(f"  ✓ time_to_deadline(t=120): {task.time_to_deadline(120)}")

    # 状态查询
    assert task.is_active()
    assert not task.is_assigned()
    assert not task.is_done()
    assert not task.is_expired()
    print(f"  ✓ 状态查询方法正确")


def test_task_coordinate_convention():
    """测试：坐标约定"""
    print("\n测试：坐标约定")

    # cell = (i, j) = (row, col)
    task = Task(id=1, release_t=10, cell=(5, 8), deadline_t=100)
    i, j = task.cell
    assert i == 5  # row
    assert j == 8  # col
    print(f"  ✓ 坐标约定: cell=(i={i}, j={j}) = (row, col)")

    # JSON 序列化后恢复
    task_json = task.to_json()
    task_restored = Task.from_json(task_json)
    assert task_restored.cell == (5, 8)
    assert isinstance(task_restored.cell, tuple)
    print(f"  ✓ JSON 序列化保持坐标格式: {task_restored.cell}")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Task 数据结构单元测试")
    print("=" * 60)

    try:
        test_task_creation()
        test_task_state_transitions()
        test_task_expiration()
        test_task_json_serialization()
        test_task_helper_methods()
        test_task_coordinate_convention()

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
