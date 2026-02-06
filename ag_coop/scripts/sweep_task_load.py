#!/usr/bin/env python3
"""
任务负载校准脚本

目标：找到合适的任务参数，使 miss_rate 在 10%-40% 之间

扫描参数：
- arrival_rate: {0.05, 0.1, 0.2, 0.3}
- deadline_range: {(40,80), (25,60), (15,40)}

固定参数：
- horizon_steps: 500
- seed: {42, 43, 44, 45, 46}（5 个 seed 取平均）
- map: map_01.map
- policy: earliest_deadline

输出：
- 表格（arrival_rate x deadline_range）
- 每个格子显示：tasks_completed, miss_rate, mean_tardiness
- 推荐参数（miss_rate 在 10%-40% 之间）
"""

import sys
from pathlib import Path
import json
from typing import List, Tuple, Dict

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.tasks import TaskStream, TaskConfig, TaskManager, VirtualUAVExecutor
from agcoop.map import auto_load_map


def run_single_episode(
    horizon_steps: int,
    arrival_rate: float,
    deadline_min: int,
    deadline_max: int,
    seed: int,
    map_path: str = "maps/map_01.map"
) -> Dict:
    """
    运行单个 episode

    Returns:
        metrics 字典
    """
    # 加载地图
    grid_map = auto_load_map(map_path)

    # 创建任务配置
    task_config = TaskConfig(
        enabled=True,
        arrival_rate=arrival_rate,
        deadline_min=deadline_min,
        deadline_max=deadline_max,
        max_active=20,
        top_m=5,
        service_time=2
    )

    # 创建任务流生成器
    task_stream = TaskStream(task_config, grid_map.free_cells, seed=seed)

    # 创建任务管理器
    task_manager = TaskManager(max_active=20, top_m=5, seed=seed)

    # 创建虚拟执行器
    initial_cell = grid_map.free_cells[0]
    executor = VirtualUAVExecutor(uav_cell=initial_cell, service_time=2)

    # 运行 episode
    for t in range(horizon_steps):
        # 生成新任务
        new_tasks = task_stream.generate_tasks(t, task_manager.num_active)
        for task in new_tasks:
            task_manager.add_task(task)

        # 过期超时任务
        task_manager.expire_overdue_tasks(t)

        # 执行器执行一步
        executor.step(t, task_manager, policy="earliest_deadline")

    # 获取统计
    stats = task_manager.get_stats()

    return {
        'total_added': stats['total_added'],
        'total_completed': stats['total_completed'],
        'total_expired': stats['total_expired'],
        'completion_rate': stats['completion_rate'],
        'miss_rate': stats['total_expired'] / max(1, stats['total_added']),
        'mean_tardiness': stats['avg_tardiness'],
    }


def run_sweep(
    horizon_steps: int = 500,
    arrival_rates: List[float] = [0.05, 0.1, 0.2, 0.3],
    deadline_ranges: List[Tuple[int, int]] = [(40, 80), (25, 60), (15, 40)],
    seeds: List[int] = [42, 43, 44, 45, 46],
    map_path: str = "maps/map_01.map"
) -> Dict:
    """
    运行参数扫描

    Returns:
        results: {(arrival_rate, deadline_range): metrics}
    """
    results = {}

    total_runs = len(arrival_rates) * len(deadline_ranges) * len(seeds)
    current_run = 0

    print(f"\n{'='*60}")
    print(f"任务负载校准")
    print(f"{'='*60}")
    print(f"  horizon_steps: {horizon_steps}")
    print(f"  arrival_rates: {arrival_rates}")
    print(f"  deadline_ranges: {deadline_ranges}")
    print(f"  seeds: {seeds}")
    print(f"  total_runs: {total_runs}")
    print()

    for arrival_rate in arrival_rates:
        for deadline_range in deadline_ranges:
            deadline_min, deadline_max = deadline_range

            # 运行多个 seed
            metrics_list = []

            for seed in seeds:
                current_run += 1
                print(f"  [{current_run}/{total_runs}] arrival_rate={arrival_rate:.2f}, deadline=[{deadline_min},{deadline_max}], seed={seed}...", end='')

                metrics = run_single_episode(
                    horizon_steps=horizon_steps,
                    arrival_rate=arrival_rate,
                    deadline_min=deadline_min,
                    deadline_max=deadline_max,
                    seed=seed,
                    map_path=map_path
                )

                metrics_list.append(metrics)
                print(f" done (completed={metrics['total_completed']}, miss_rate={metrics['miss_rate']:.2%})")

            # 计算平均值
            avg_metrics = {
                'total_added': sum(m['total_added'] for m in metrics_list) / len(metrics_list),
                'total_completed': sum(m['total_completed'] for m in metrics_list) / len(metrics_list),
                'total_expired': sum(m['total_expired'] for m in metrics_list) / len(metrics_list),
                'completion_rate': sum(m['completion_rate'] for m in metrics_list) / len(metrics_list),
                'miss_rate': sum(m['miss_rate'] for m in metrics_list) / len(metrics_list),
                'mean_tardiness': sum(m['mean_tardiness'] for m in metrics_list) / len(metrics_list),
            }

            results[(arrival_rate, deadline_range)] = avg_metrics

    return results


def print_results_table(results: Dict):
    """打印结果表格"""
    print(f"\n{'='*60}")
    print(f"结果表格")
    print(f"{'='*60}")

    # 提取所有 arrival_rate 和 deadline_range
    arrival_rates = sorted(set(k[0] for k in results.keys()))
    deadline_ranges = sorted(set(k[1] for k in results.keys()))

    # 打印表头
    print(f"\n{'Arrival Rate':<15}", end='')
    for dr in deadline_ranges:
        print(f"{'[' + str(dr[0]) + ',' + str(dr[1]) + ']':<25}", end='')
    print()
    print('-' * (15 + 25 * len(deadline_ranges)))

    # 打印每行
    for ar in arrival_rates:
        print(f"{ar:<15.2f}", end='')
        for dr in deadline_ranges:
            metrics = results.get((ar, dr))
            if metrics:
                # 显示：completed / miss_rate / tardiness
                completed = metrics['total_completed']
                miss_rate = metrics['miss_rate']
                tardiness = metrics['mean_tardiness']
                print(f"{completed:>6.1f} / {miss_rate:>5.1%} / {tardiness:>4.1f}  ", end='')
            else:
                print(f"{'N/A':<25}", end='')
        print()

    print()
    print("格式：completed / miss_rate / tardiness")


def find_recommendations(results: Dict, target_miss_rate: Tuple[float, float] = (0.1, 0.4)):
    """找到推荐参数"""
    print(f"\n{'='*60}")
    print(f"推荐参数（miss_rate 在 {target_miss_rate[0]:.0%}-{target_miss_rate[1]:.0%} 之间）")
    print(f"{'='*60}")

    recommendations = []

    for (arrival_rate, deadline_range), metrics in results.items():
        miss_rate = metrics['miss_rate']
        if target_miss_rate[0] <= miss_rate <= target_miss_rate[1]:
            recommendations.append({
                'arrival_rate': arrival_rate,
                'deadline_range': deadline_range,
                'metrics': metrics
            })

    if recommendations:
        # 按 miss_rate 排序（接近中间值优先）
        target_mid = (target_miss_rate[0] + target_miss_rate[1]) / 2
        recommendations.sort(key=lambda x: abs(x['metrics']['miss_rate'] - target_mid))

        print(f"\n找到 {len(recommendations)} 个候选参数:\n")

        for i, rec in enumerate(recommendations, 1):
            ar = rec['arrival_rate']
            dr = rec['deadline_range']
            m = rec['metrics']

            print(f"{i}. arrival_rate={ar:.2f}, deadline=[{dr[0]},{dr[1]}]")
            print(f"   - total_added: {m['total_added']:.1f}")
            print(f"   - total_completed: {m['total_completed']:.1f}")
            print(f"   - completion_rate: {m['completion_rate']:.2%}")
            print(f"   - miss_rate: {m['miss_rate']:.2%}")
            print(f"   - mean_tardiness: {m['mean_tardiness']:.2f}")
            print()

        # 推荐第一个
        best = recommendations[0]
        print(f"🎯 推荐参数:")
        print(f"   arrival_rate: {best['arrival_rate']:.2f}")
        print(f"   deadline_min: {best['deadline_range'][0]}")
        print(f"   deadline_max: {best['deadline_range'][1]}")
        print(f"   → miss_rate: {best['metrics']['miss_rate']:.2%}")

    else:
        print(f"\n⚠ 没有参数落在目标区间")
        print(f"   建议调整 arrival_rate 或 deadline_range")


def save_results(results: Dict, output_path: Path):
    """保存结果到 JSON"""
    # 转换 key 为字符串（JSON 不支持 tuple key）
    results_json = {}
    for (arrival_rate, deadline_range), metrics in results.items():
        key = f"ar_{arrival_rate:.2f}_dl_{deadline_range[0]}_{deadline_range[1]}"
        results_json[key] = {
            'arrival_rate': arrival_rate,
            'deadline_min': deadline_range[0],
            'deadline_max': deadline_range[1],
            **metrics
        }

    with open(output_path, 'w') as f:
        json.dump(results_json, f, indent=2, ensure_ascii=False)

    print(f"\n✓ 结果已保存: {output_path}")


def main():
    """主函数"""
    print("=" * 60)
    print("Day4 任务负载校准脚本")
    print("=" * 60)

    # 运行 sweep
    results = run_sweep(
        horizon_steps=500,
        arrival_rates=[0.05, 0.1, 0.2, 0.3],
        deadline_ranges=[(40, 80), (25, 60), (15, 40)],
        seeds=[42, 43, 44, 45, 46],
        map_path="maps/map_01.map"
    )

    # 打印结果表格
    print_results_table(results)

    # 找到推荐参数
    find_recommendations(results, target_miss_rate=(0.1, 0.4))

    # 保存结果
    output_dir = Path(__file__).parent.parent / "outputs" / "task_load_sweep"
    output_dir.mkdir(parents=True, exist_ok=True)
    save_results(results, output_dir / "sweep_results.json")

    print(f"\n{'='*60}")
    print(f"✓ 校准完成！")
    print(f"{'='*60}")
    print()


if __name__ == "__main__":
    main()
