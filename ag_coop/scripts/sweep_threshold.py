#!/usr/bin/env python3
"""
阈值 sweep 工具：校准 snr_threshold_db

目标：找到让 outage_percent 落在 5%~30% 区间的阈值

用法：
    python scripts/sweep_threshold.py --map maps/map_01.map --ugv "2,2;10,10;15,15"
    python scripts/sweep_threshold.py --map maps/test_small.map --ugv "1,1;8,8"
"""

import sys
import json
import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.map import auto_load_map
from agcoop.comm import CommConfig, compute_best_snr


def sweep_thresholds(
    grid_map,
    ugv_cells: list,
    base_config: CommConfig,
    thresholds: list
) -> list:
    """
    扫描多个阈值，计算每个阈值的 outage_percent

    Args:
        grid_map: GridMap 对象
        ugv_cells: UGV 位置列表
        base_config: 基础通信配置
        thresholds: 阈值列表（dB）

    Returns:
        结果列表，每项为 {threshold, outage_percent, outage_count, total_cells}
    """
    results = []

    print(f"\n扫描阈值...")
    print(f"  阈值范围: {min(thresholds):.1f} ~ {max(thresholds):.1f} dB")
    print(f"  阈值数量: {len(thresholds)}")
    print(f"  Free cells: {len(grid_map.free_cells)}")

    for threshold_db in thresholds:
        # 创建新配置
        config = CommConfig(
            enabled=True,
            tx_power_db=base_config.tx_power_db,
            pathloss_n=base_config.pathloss_n,
            obstacle_penalty_db=base_config.obstacle_penalty_db,
            snr_threshold_db=threshold_db,
            eps_m=base_config.eps_m
        )

        # 计算所有 free cell 的 outage
        outage_count = 0
        for i, j in grid_map.free_cells:
            snr_best, best_ugv_id, outage = compute_best_snr(
                (i, j), ugv_cells, grid_map, config
            )
            if outage:
                outage_count += 1

        total_cells = len(grid_map.free_cells)
        outage_percent = (outage_count / total_cells * 100) if total_cells > 0 else 0.0

        results.append({
            'threshold_db': threshold_db,
            'outage_percent': outage_percent,
            'outage_count': outage_count,
            'total_cells': total_cells
        })

        print(f"  threshold={threshold_db:+6.1f} dB: outage={outage_percent:5.1f}% ({outage_count}/{total_cells})")

    return results


def visualize_sweep(results: list, output_path: Path, target_range=(5.0, 30.0)):
    """
    可视化 sweep 结果

    Args:
        results: sweep 结果列表
        output_path: 输出图片路径
        target_range: 目标 outage 范围 (min%, max%)
    """
    thresholds = [r['threshold_db'] for r in results]
    outage_percents = [r['outage_percent'] for r in results]

    fig, ax = plt.subplots(figsize=(12, 6))

    # 绘制曲线
    ax.plot(thresholds, outage_percents, 'o-', linewidth=2, markersize=8,
            color='steelblue', label='Outage %')

    # 标注目标区间
    ax.axhspan(target_range[0], target_range[1], alpha=0.2, color='green',
               label=f'Target Range ({target_range[0]:.0f}%-{target_range[1]:.0f}%)')

    # 找到落在目标区间的阈值
    candidates = [r for r in results
                  if target_range[0] <= r['outage_percent'] <= target_range[1]]

    if candidates:
        # 标注推荐阈值（取中间值）
        mid_idx = len(candidates) // 2
        recommended = candidates[mid_idx]
        ax.axvline(recommended['threshold_db'], color='red', linestyle='--',
                   linewidth=2, label=f"Recommended: {recommended['threshold_db']:.1f} dB")
        ax.scatter([recommended['threshold_db']], [recommended['outage_percent']],
                   s=200, c='red', marker='*', zorder=10, edgecolors='black', linewidths=2)

    # 设置坐标轴
    ax.set_xlabel('SNR Threshold (dB)', fontsize=12, weight='bold')
    ax.set_ylabel('Outage Percent (%)', fontsize=12, weight='bold')
    ax.set_title('Threshold Sweep: SNR Threshold vs Outage %', fontsize=14, weight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11)

    # 设置 y 轴范围
    ax.set_ylim(-5, 105)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"\n✓ Sweep 图表已保存: {output_path}")


def save_sweep_results(
    results: list,
    grid_map,
    ugv_cells: list,
    base_config: CommConfig,
    output_path: Path,
    target_range=(5.0, 30.0)
):
    """
    保存 sweep 结果到 JSON

    Args:
        results: sweep 结果列表
        grid_map: GridMap 对象
        ugv_cells: UGV 位置列表
        base_config: 基础通信配置
        output_path: 输出 JSON 路径
        target_range: 目标 outage 范围
    """
    # 找到推荐阈值
    candidates = [r for r in results
                  if target_range[0] <= r['outage_percent'] <= target_range[1]]

    if candidates:
        mid_idx = len(candidates) // 2
        recommended = candidates[mid_idx]
    else:
        # 如果没有落在目标区间的，选择最接近的
        target_mid = (target_range[0] + target_range[1]) / 2
        recommended = min(results, key=lambda r: abs(r['outage_percent'] - target_mid))

    data = {
        'map_info': {
            'width': grid_map.width,
            'height': grid_map.height,
            'resolution': grid_map.resolution,
            'free_cells': len(grid_map.free_cells),
        },
        'ugv_positions': {
            'count': len(ugv_cells),
            'cells': [{'i': int(i), 'j': int(j)} for i, j in ugv_cells],
        },
        'base_config': {
            'tx_power_db': base_config.tx_power_db,
            'pathloss_n': base_config.pathloss_n,
            'obstacle_penalty_db': base_config.obstacle_penalty_db,
            'eps_m': base_config.eps_m,
        },
        'target_range': {
            'min_percent': target_range[0],
            'max_percent': target_range[1],
        },
        'recommended_threshold': {
            'threshold_db': recommended['threshold_db'],
            'outage_percent': recommended['outage_percent'],
            'outage_count': recommended['outage_count'],
            'note': f"Recommended threshold for {target_range[0]:.0f}%-{target_range[1]:.0f}% outage range"
        },
        'sweep_results': results,
    }

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✓ Sweep 结果已保存: {output_path}")


def print_summary(results: list, target_range=(5.0, 30.0)):
    """打印摘要"""
    print("\n" + "=" * 60)
    print("Sweep 摘要")
    print("=" * 60)

    # 找到推荐阈值
    candidates = [r for r in results
                  if target_range[0] <= r['outage_percent'] <= target_range[1]]

    if candidates:
        print(f"\n✓ 找到 {len(candidates)} 个候选阈值（outage 在 {target_range[0]:.0f}%-{target_range[1]:.0f}% 区间）:")
        for r in candidates:
            print(f"  - {r['threshold_db']:+6.1f} dB → {r['outage_percent']:5.1f}%")

        mid_idx = len(candidates) // 2
        recommended = candidates[mid_idx]
        print(f"\n🎯 推荐阈值: {recommended['threshold_db']:+.1f} dB")
        print(f"   → outage_percent: {recommended['outage_percent']:.1f}%")
        print(f"   → outage_count: {recommended['outage_count']}/{recommended['total_cells']}")
    else:
        print(f"\n⚠ 没有阈值落在目标区间 ({target_range[0]:.0f}%-{target_range[1]:.0f}%)")
        print("   建议调整阈值范围或目标区间")

        # 显示最接近的
        target_mid = (target_range[0] + target_range[1]) / 2
        closest = min(results, key=lambda r: abs(r['outage_percent'] - target_mid))
        print(f"\n最接近的阈值: {closest['threshold_db']:+.1f} dB")
        print(f"   → outage_percent: {closest['outage_percent']:.1f}%")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='阈值 sweep 工具：校准 snr_threshold_db')
    parser.add_argument('--map', type=str, required=True, help='地图文件路径')
    parser.add_argument('--ugv', type=str, required=True,
                        help='UGV 位置（格式："i1,j1;i2,j2;i3,j3"）')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='输出目录（默认：outputs/threshold_sweep/<map_id>）')
    parser.add_argument('--tx-power', type=float, default=0.0,
                        help='发射功率（dB，默认：0.0）')
    parser.add_argument('--pathloss-n', type=float, default=2.0,
                        help='路径损耗指数（默认：2.0）')
    parser.add_argument('--obstacle-penalty', type=float, default=6.0,
                        help='障碍衰减（dB，默认：6.0）')
    parser.add_argument('--threshold-min', type=float, default=-15.0,
                        help='最小阈值（dB，默认：-15.0）')
    parser.add_argument('--threshold-max', type=float, default=5.0,
                        help='最大阈值（dB，默认：5.0）')
    parser.add_argument('--threshold-step', type=float, default=1.0,
                        help='阈值步长（dB，默认：1.0）')
    parser.add_argument('--target-min', type=float, default=5.0,
                        help='目标 outage 最小值（%，默认：5.0）')
    parser.add_argument('--target-max', type=float, default=30.0,
                        help='目标 outage 最大值（%，默认：30.0）')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("阈值 Sweep 工具")
    print("=" * 60 + "\n")

    # 加载地图
    map_path = Path(args.map)
    if not map_path.exists():
        print(f"错误：地图文件不存在: {map_path}")
        sys.exit(1)

    print(f"加载地图: {map_path}")
    try:
        grid_map = auto_load_map(str(map_path))
    except Exception as e:
        print(f"错误：无法加载地图: {e}")
        sys.exit(1)

    print(f"✓ 地图加载成功:")
    print(f"  - 尺寸: {grid_map.width}x{grid_map.height}")
    print(f"  - 自由格子: {len(grid_map.free_cells)}")

    # 解析 UGV 位置
    print(f"\n解析 UGV 位置: {args.ugv}")
    try:
        ugv_cells = []
        for pos_str in args.ugv.split(';'):
            i, j = map(int, pos_str.split(','))
            ugv_cells.append((i, j))
    except Exception as e:
        print(f"错误：无法解析 UGV 位置: {e}")
        sys.exit(1)

    print(f"✓ UGV 位置:")
    for idx, (i, j) in enumerate(ugv_cells):
        print(f"  UGV {idx}: cell({i}, {j})")

    # 创建基础通信配置
    base_config = CommConfig(
        enabled=True,
        tx_power_db=args.tx_power,
        pathloss_n=args.pathloss_n,
        obstacle_penalty_db=args.obstacle_penalty,
        snr_threshold_db=0.0,  # 占位，会被覆盖
        eps_m=0.05
    )

    # 生成阈值列表
    thresholds = np.arange(args.threshold_min, args.threshold_max + args.threshold_step/2,
                           args.threshold_step).tolist()

    # 确定输出目录
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        map_id = map_path.stem
        output_dir = Path(__file__).parent.parent / "outputs" / "threshold_sweep" / map_id

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n输出目录: {output_dir}")

    # 运行 sweep
    target_range = (args.target_min, args.target_max)
    results = sweep_thresholds(grid_map, ugv_cells, base_config, thresholds)

    # 可视化
    plot_path = output_dir / "threshold_sweep.png"
    visualize_sweep(results, plot_path, target_range)

    # 保存结果
    json_path = output_dir / "threshold_sweep.json"
    save_sweep_results(results, grid_map, ugv_cells, base_config, json_path, target_range)

    # 打印摘要
    print_summary(results, target_range)

    print("\n" + "=" * 60)
    print("✓ 完成！")
    print("=" * 60)
    print(f"\n输出文件:")
    print(f"  - {plot_path}")
    print(f"  - {json_path}")
    print()


if __name__ == "__main__":
    main()
