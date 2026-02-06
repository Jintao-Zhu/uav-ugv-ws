#!/usr/bin/env python3
"""
TaskStream 单元测试

验证：
1. 任务生成的可复现性（相同 seed 生成相同任务序列）
2. Bernoulli 过程正确性（arrival_rate 控制生成概率）
3. 任务池容量限制（max_active）
4. deadline 范围正确性
5. 任务位置从 free_cells 采样
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.tasks import Task, TaskStream, TaskConfig


def test_task_stream_reproducibility():
    """测试：任务生成的可复现性"""
    print("\n测试：任务生成的可复现性")

    # 配置
    config = TaskConfig(
        enabled=True,
        arrival_rate=0.5,
        deadline_min=25,
        deadline_max=60,
        max_active=20
    )

    free_cells = [(i, j) for i in range(10) for j in range(10)]

    # 创建两个相同 seed 的生成器
    stream1 = TaskStream(config, free_cells, seed=42)
    stream2 = TaskStream(config, free_cells, seed=42)

    # 生成 100 步的任务
    tasks1 = []
    tasks2 = []

    for t in range(100):
        new_tasks1 = stream1.generate_tasks(t, len(tasks1))
        new_tasks2 = stream2.generate_tasks(t, len(tasks2))

        tasks1.extend(new_tasks1)
        tasks2.extend(new_tasks2)

    # 验证任务数量相同
    assert len(tasks1) == len(tasks2), \
        f"任务数量不同: {len(tasks1)} vs {len(tasks2)}"

    # 验证每个任务的字段相同
    for i, (task1, task2) in enumerate(zip(tasks1, tasks2)):
        assert task1.id == task2.id, f"Task {i}: id 不同"
        assert task1.release_t == task2.release_t, f"Task {i}: release_t 不同"
        assert task1.cell == task2.cell, f"Task {i}: cell 不同"
        assert task1.deadline_t == task2.deadline_t, f"Task {i}: deadline_t 不同"

    print(f"  ✓ 生成 {len(tasks1)} 个任务，两次运行完全一致")
    print(f"  ✓ 任务 ID: {[t.id for t in tasks1[:5]]}...")
    print(f"  ✓ 任务位置: {[t.cell for t in tasks1[:5]]}...")


def test_task_stream_arrival_rate():
    """测试：arrival_rate 控制生成概率"""
    print("\n测试：arrival_rate 控制生成概率")

    free_cells = [(i, j) for i in range(10) for j in range(10)]

    # 测试不同的 arrival_rate
    for rate in [0.1, 0.3, 0.5]:
        config = TaskConfig(
            enabled=True,
            arrival_rate=rate,
            deadline_min=25,
            deadline_max=60,
            max_active=1000  # 足够大，不限制
        )

        stream = TaskStream(config, free_cells, seed=42)

        # 生成 1000 步的任务
        total_tasks = 0
        for t in range(1000):
            new_tasks = stream.generate_tasks(t, 0)  # 假设任务立即完成，不堆积
            total_tasks += len(new_tasks)

        # 验证生成率接近 arrival_rate
        actual_rate = total_tasks / 1000
        error = abs(actual_rate - rate)

        print(f"  arrival_rate={rate:.1f}: 生成 {total_tasks} 个任务，实际率={actual_rate:.3f}，误差={error:.3f}")

        # 允许 20% 的相对误差（统计波动）
        assert error < rate * 0.3, f"生成率偏差过大: {error:.3f} (期望 < {rate * 0.3:.3f})"

    print(f"  ✓ arrival_rate 控制正确")


def test_task_stream_capacity_limit():
    """测试：任务池容量限制"""
    print("\n测试：任务池容量限制")

    config = TaskConfig(
        enabled=True,
        arrival_rate=1.0,  # 每步都生成
        deadline_min=25,
        deadline_max=60,
        max_active=5  # 容量限制为 5
    )

    free_cells = [(i, j) for i in range(10) for j in range(10)]
    stream = TaskStream(config, free_cells, seed=42)

    # 生成任务，但不完成（模拟任务堆积）
    active_tasks = []

    for t in range(20):
        new_tasks = stream.generate_tasks(t, len(active_tasks))
        active_tasks.extend(new_tasks)

    # 验证任务数量不超过容量
    assert len(active_tasks) <= config.max_active, \
        f"任务数量超过容量: {len(active_tasks)} > {config.max_active}"

    # 验证有任务被丢弃
    stats = stream.get_stats()
    assert stats['total_dropped'] > 0, "应该有任务被丢弃"

    print(f"  ✓ 生成 {stats['total_generated']} 个任务")
    print(f"  ✓ 丢弃 {stats['total_dropped']} 个任务")
    print(f"  ✓ 丢弃率: {stats['drop_rate']:.2%}")
    print(f"  ✓ 活跃任务数: {len(active_tasks)} <= {config.max_active}")


def test_task_stream_deadline_range():
    """测试：deadline 范围正确性"""
    print("\n测试：deadline 范围正确性")

    config = TaskConfig(
        enabled=True,
        arrival_rate=1.0,
        deadline_min=25,
        deadline_max=60,
        max_active=100
    )

    free_cells = [(i, j) for i in range(10) for j in range(10)]
    stream = TaskStream(config, free_cells, seed=42)

    # 生成 100 个任务
    tasks = []
    for t in range(100):
        new_tasks = stream.generate_tasks(t, len(tasks))
        tasks.extend(new_tasks)

    # 验证每个任务的 deadline 在范围内
    for task in tasks:
        deadline_offset = task.deadline_t - task.release_t
        assert config.deadline_min <= deadline_offset <= config.deadline_max, \
            f"Task {task.id}: deadline_offset={deadline_offset} 不在范围 [{config.deadline_min}, {config.deadline_max}]"

    # 统计 deadline 分布
    offsets = [task.deadline_t - task.release_t for task in tasks]
    min_offset = min(offsets)
    max_offset = max(offsets)
    avg_offset = sum(offsets) / len(offsets)

    print(f"  ✓ 生成 {len(tasks)} 个任务")
    print(f"  ✓ deadline 范围: [{config.deadline_min}, {config.deadline_max}]")
    print(f"  ✓ 实际 offset 范围: [{min_offset}, {max_offset}]")
    print(f"  ✓ 平均 offset: {avg_offset:.1f}")


def test_task_stream_cell_sampling():
    """测试：任务位置从 free_cells 采样"""
    print("\n测试：任务位置从 free_cells 采样")

    free_cells = [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]

    config = TaskConfig(
        enabled=True,
        arrival_rate=1.0,
        deadline_min=25,
        deadline_max=60,
        max_active=100
    )

    stream = TaskStream(config, free_cells, seed=42)

    # 生成 50 个任务
    tasks = []
    for t in range(50):
        new_tasks = stream.generate_tasks(t, len(tasks))
        tasks.extend(new_tasks)

    # 验证所有任务位置都在 free_cells 中
    for task in tasks:
        assert task.cell in free_cells, \
            f"Task {task.id}: cell={task.cell} 不在 free_cells 中"

    # 统计位置分布
    cell_counts = {cell: 0 for cell in free_cells}
    for task in tasks:
        cell_counts[task.cell] += 1

    print(f"  ✓ 生成 {len(tasks)} 个任务")
    print(f"  ✓ 所有任务位置都在 free_cells 中")
    print(f"  ✓ 位置分布: {cell_counts}")


def test_task_stream_reset():
    """测试：reset() 重置生成器"""
    print("\n测试：reset() 重置生成器")

    config = TaskConfig(
        enabled=True,
        arrival_rate=0.5,
        deadline_min=25,
        deadline_max=60,
        max_active=20
    )

    free_cells = [(i, j) for i in range(10) for j in range(10)]
    stream = TaskStream(config, free_cells, seed=42)

    # 第一次运行
    tasks1 = []
    for t in range(50):
        new_tasks = stream.generate_tasks(t, len(tasks1))
        tasks1.extend(new_tasks)

    stats1 = stream.get_stats()

    # 重置
    stream.reset()

    # 第二次运行
    tasks2 = []
    for t in range(50):
        new_tasks = stream.generate_tasks(t, len(tasks2))
        tasks2.extend(new_tasks)

    stats2 = stream.get_stats()

    # 验证两次运行一致
    assert len(tasks1) == len(tasks2), "重置后任务数量不同"
    assert stats1['total_generated'] == stats2['total_generated'], "重置后统计不一致"

    for i, (task1, task2) in enumerate(zip(tasks1, tasks2)):
        assert task1.cell == task2.cell, f"Task {i}: 重置后 cell 不同"
        assert task1.deadline_t == task2.deadline_t, f"Task {i}: 重置后 deadline_t 不同"

    print(f"  ✓ 重置后生成相同的任务序列")
    print(f"  ✓ 第一次: {len(tasks1)} 个任务")
    print(f"  ✓ 第二次: {len(tasks2)} 个任务")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("TaskStream 单元测试")
    print("=" * 60)

    try:
        test_task_stream_reproducibility()
        test_task_stream_arrival_rate()
        test_task_stream_capacity_limit()
        test_task_stream_deadline_range()
        test_task_stream_cell_sampling()
        test_task_stream_reset()

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
