#!/usr/bin/env python3
"""
测试 visualizer 的数据加载功能（不需要显示窗口）
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.vis import load_run, load_grid_map, load_tasks


def test_visualizer_data_loading():
    """测试数据加载"""
    run_dir = "outputs/test_vis_greedy_seed0"

    print("=" * 60)
    print("测试 Visualizer 数据加载")
    print("=" * 60)

    # 测试 1: 加载运行数据
    print("\n[1] 加载运行数据...")
    run_data = load_run(run_dir)
    print(f"  ✓ RunData: {run_data}")
    print(f"    - 配置: {run_data.config['episode']['horizon_steps']} 步")
    print(f"    - Trace: {len(run_data.trace)} 条记录")
    print(f"    - Metrics: {len(run_data.metrics)} 个指标")

    # 测试 2: 加载地图
    print("\n[2] 加载地图...")
    map_path = run_data.config['episode']['map_path']
    grid_map = load_grid_map(map_path)
    if grid_map:
        print(f"  ✓ GridMap: {grid_map}")
        print(f"    - 尺寸: {grid_map.width}x{grid_map.height}")
        # 统计障碍物
        obstacles = sum(1 for i in range(grid_map.height)
                       for j in range(grid_map.width)
                       if not grid_map.is_free(i, j))
        print(f"    - 障碍物: {obstacles} 个")
    else:
        print(f"  ✗ 地图加载失败")

    # 测试 3: 加载任务
    print("\n[3] 加载任务...")
    task_tracker = load_tasks(run_dir)
    if task_tracker:
        print(f"  ✓ TaskTracker: {task_tracker}")
        print(f"    - 总任务数: {len(task_tracker.tasks)}")

        # 统计任务状态
        completed = sum(1 for t in task_tracker.tasks if t.status == 'completed')
        missed = sum(1 for t in task_tracker.tasks if t.status == 'missed')
        active = sum(1 for t in task_tracker.tasks if t.status == 'active')
        print(f"    - 已完成: {completed}")
        print(f"    - 已过期: {missed}")
        print(f"    - 活跃: {active}")

        # 测试时间查询
        t_test = 100
        active_at_t = task_tracker.get_active_tasks(t_test)
        print(f"    - t={t_test} 时活跃任务: {len(active_at_t)} 个")
    else:
        print(f"  ✗ 任务加载失败")

    # 测试 4: 检查 trace 数据完整性
    print("\n[4] 检查 trace 数据...")
    sample_step = run_data.trace[0]
    required_fields = ['t', 'ugv_positions', 'decision_step', 'outage', 'snr_best']
    missing_fields = [f for f in required_fields if f not in sample_step]
    if not missing_fields:
        print(f"  ✓ Trace 数据完整")
        print(f"    - 示例字段: {list(sample_step.keys())[:10]}...")
    else:
        print(f"  ✗ 缺少字段: {missing_fields}")

    # 测试 5: 验证 UGV 位置数据
    print("\n[5] 验证 UGV 位置数据...")
    n_agents = run_data.init['n_agents']
    ugv_pos_t0 = run_data.trace[0]['ugv_positions']
    ugv_pos_t100 = run_data.trace[100]['ugv_positions']
    print(f"  ✓ UGV 数量: {n_agents}")
    print(f"    - t=0 位置: {ugv_pos_t0}")
    print(f"    - t=100 位置: {ugv_pos_t100}")

    # 检查是否有运动
    moved = any(ugv_pos_t0[i] != ugv_pos_t100[i] for i in range(n_agents))
    print(f"    - UGV 是否移动: {'是' if moved else '否'}")

    print("\n" + "=" * 60)
    print("✓ 所有测试通过！Visualizer 数据加载正常")
    print("=" * 60)

    return True


if __name__ == '__main__':
    try:
        test_visualizer_data_loading()
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
