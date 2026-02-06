#!/usr/bin/env python3
"""
通信检查工具：生成 SNR heatmap

功能：
- 输入地图和 UGV 位置
- 对所有 free cell 作为 UAV 位置，计算 snr_best
- 输出 SNR heatmap 和元数据

用法：
    python scripts/inspect_comm.py --map maps/map_01.map --ugv "1,1;10,3;5,15"
    python scripts/inspect_comm.py --map maps/test_small.map --ugv "2,2;7,7"
"""

import sys
import json
import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.map import auto_load_map
from agcoop.comm import CommConfig, compute_best_snr


def parse_ugv_positions(ugv_str: str) -> list:
    """
    解析 UGV 位置字符串

    Args:
        ugv_str: 格式 "i1,j1;i2,j2;i3,j3"

    Returns:
        [(i1, j1), (i2, j2), ...]

    Example:
        >>> parse_ugv_positions("1,1;10,3;5,15")
        [(1, 1), (10, 3), (5, 15)]
    """
    positions = []
    for pos_str in ugv_str.split(';'):
        i, j = map(int, pos_str.split(','))
        positions.append((i, j))
    return positions


def compute_snr_heatmap(grid_map, ugv_cells: list, comm_config: CommConfig):
    """
    计算 SNR heatmap

    Args:
        grid_map: GridMap 对象
        ugv_cells: UGV 位置列表 [(i, j), ...]
        comm_config: 通信配置

    Returns:
        snr_heatmap: shape (height, width)，free cell 为 SNR 值，obstacle 为 NaN
    """
    height, width = grid_map.height, grid_map.width
    snr_heatmap = np.full((height, width), np.nan)

    print(f"计算 SNR heatmap...")
    print(f"  地图尺寸: {width}x{height}")
    print(f"  Free cells: {len(grid_map.free_cells)}")
    print(f"  UGV 数量: {len(ugv_cells)}")

    # 对每个 free cell 计算 SNR
    for idx, (i, j) in enumerate(grid_map.free_cells):
        if (idx + 1) % 50 == 0:
            print(f"  进度: {idx+1}/{len(grid_map.free_cells)}")

        # 计算该位置作为 UAV 时的最佳 SNR
        snr_best, best_ugv_id, outage = compute_best_snr(
            (i, j), ugv_cells, grid_map, comm_config
        )

        snr_heatmap[i, j] = snr_best

    print(f"  完成！")

    return snr_heatmap


def visualize_snr_heatmap(
    grid_map,
    snr_heatmap: np.ndarray,
    ugv_cells: list,
    comm_config: CommConfig,
    output_path: Path
):
    """
    可视化 SNR heatmap

    Args:
        grid_map: GridMap 对象
        snr_heatmap: SNR heatmap 数组
        ugv_cells: UGV 位置列表
        comm_config: 通信配置
        output_path: 输出图片路径
    """
    fig, ax = plt.subplots(figsize=(12, 10))

    # 计算 SNR 范围（忽略 NaN）
    valid_snr = snr_heatmap[~np.isnan(snr_heatmap)]
    snr_min = np.min(valid_snr)
    snr_max = np.max(valid_snr)
    snr_mean = np.mean(valid_snr)

    print(f"\nSNR 统计:")
    print(f"  最小值: {snr_min:.2f} dB")
    print(f"  最大值: {snr_max:.2f} dB")
    print(f"  平均值: {snr_mean:.2f} dB")

    # 创建颜色映射（绿色=好，黄色=中等，红色=差）
    # 使用 RdYlGn_r（reversed）：红色=低 SNR，绿色=高 SNR
    cmap = plt.cm.RdYlGn
    norm = mcolors.Normalize(vmin=snr_min, vmax=snr_max)

    # 绘制 heatmap
    im = ax.imshow(
        snr_heatmap,
        cmap=cmap,
        norm=norm,
        origin='lower',
        interpolation='nearest',
        aspect='equal'
    )

    # 添加 colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('SNR (dB)', fontsize=12, weight='bold')

    # 标注 UGV 位置（蓝色方块）
    for idx, (i, j) in enumerate(ugv_cells):
        ax.scatter(j, i, c='blue', s=300, marker='s', edgecolors='white',
                   linewidths=3, label='UGV' if idx == 0 else '', zorder=10)
        ax.text(j, i, f'UGV{idx}', fontsize=10, color='white', weight='bold',
                ha='center', va='center', zorder=11)

    # 标注 outage 阈值线
    threshold = comm_config.snr_threshold_db
    ax.contour(snr_heatmap, levels=[threshold], colors='black', linewidths=2,
               linestyles='--', origin='lower')

    # 设置坐标轴
    ax.set_xlabel('j (column / x-index)', fontsize=12, weight='bold')
    ax.set_ylabel('i (row / y-index)', fontsize=12, weight='bold')
    ax.set_title(
        f'SNR Heatmap\n'
        f'Map: {grid_map.width}x{grid_map.height}, '
        f'UGVs: {len(ugv_cells)}, '
        f'Threshold: {threshold:.1f} dB',
        fontsize=14, weight='bold'
    )

    # 添加网格
    ax.set_xticks(np.arange(-0.5, grid_map.width, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, grid_map.height, 1), minor=True)
    ax.grid(which='minor', color='gray', linestyle=':', linewidth=0.3, alpha=0.3)

    # 添加图例
    ax.legend(loc='upper right', fontsize=12)

    # 添加说明文本
    info_text = (
        f"验证要点：\n"
        f"1. 离 UGV 越近，SNR 越高（颜色越绿）\n"
        f"2. 障碍后方出现阴影区（SNR 更低）\n"
        f"3. 黑色虚线：outage 阈值 ({threshold:.1f} dB)\n\n"
        f"SNR 范围：\n"
        f"  Min: {snr_min:.2f} dB\n"
        f"  Max: {snr_max:.2f} dB\n"
        f"  Mean: {snr_mean:.2f} dB"
    )

    ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"\n✓ Heatmap 已保存: {output_path}")


def save_comm_meta(
    grid_map,
    ugv_cells: list,
    comm_config: CommConfig,
    snr_heatmap: np.ndarray,
    output_path: Path
):
    """
    保存通信元数据

    Args:
        grid_map: GridMap 对象
        ugv_cells: UGV 位置列表
        comm_config: 通信配置
        snr_heatmap: SNR heatmap 数组
        output_path: 输出 JSON 路径
    """
    # 计算统计信息
    valid_snr = snr_heatmap[~np.isnan(snr_heatmap)]
    snr_min = float(np.min(valid_snr))
    snr_max = float(np.max(valid_snr))
    snr_mean = float(np.mean(valid_snr))
    snr_std = float(np.std(valid_snr))

    # 计算 outage 比例
    outage_count = np.sum(valid_snr < comm_config.snr_threshold_db)
    outage_percent = (outage_count / len(valid_snr) * 100) if len(valid_snr) > 0 else 0.0

    meta = {
        'map_info': {
            'width': grid_map.width,
            'height': grid_map.height,
            'resolution': grid_map.resolution,
            'origin': list(grid_map.origin),
            'free_cells': len(grid_map.free_cells),
        },
        'ugv_positions': {
            'count': len(ugv_cells),
            'cells': [{'i': int(i), 'j': int(j)} for i, j in ugv_cells],
            'world': [
                {'x': float(x), 'y': float(y)}
                for i, j in ugv_cells
                for x, y in [grid_map.cell_to_world(i, j)]
            ],
        },
        'comm_config': {
            'tx_power_db': comm_config.tx_power_db,
            'pathloss_n': comm_config.pathloss_n,
            'obstacle_penalty_db': comm_config.obstacle_penalty_db,
            'snr_threshold_db': comm_config.snr_threshold_db,
            'eps_m': comm_config.eps_m,
        },
        'snr_statistics': {
            'min': round(snr_min, 2),
            'max': round(snr_max, 2),
            'mean': round(snr_mean, 2),
            'std': round(snr_std, 2),
            'outage_count': int(outage_count),
            'outage_percent': round(outage_percent, 2),
        },
    }

    with open(output_path, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"✓ 元数据已保存: {output_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='通信检查工具：生成 SNR heatmap')
    parser.add_argument('--map', type=str, required=True, help='地图文件路径')
    parser.add_argument('--ugv', type=str, required=True,
                        help='UGV 位置（格式："i1,j1;i2,j2;i3,j3"）')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='输出目录（默认：outputs/comm_inspect/<map_id>）')
    parser.add_argument('--tx-power', type=float, default=0.0,
                        help='发射功率（dB，默认：0.0）')
    parser.add_argument('--pathloss-n', type=float, default=2.0,
                        help='路径损耗指数（默认：2.0）')
    parser.add_argument('--obstacle-penalty', type=float, default=6.0,
                        help='障碍衰减（dB，默认：6.0）')
    parser.add_argument('--threshold', type=float, default=-20.0,
                        help='Outage 阈值（dB，默认：-20.0）')
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("通信检查工具：SNR Heatmap")
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
    print(f"  - 分辨率: {grid_map.resolution} m/cell")
    print(f"  - 自由格子: {len(grid_map.free_cells)}")

    # 解析 UGV 位置
    print(f"\n解析 UGV 位置: {args.ugv}")
    try:
        ugv_cells = parse_ugv_positions(args.ugv)
    except Exception as e:
        print(f"错误：无法解析 UGV 位置: {e}")
        print("格式示例：\"1,1;10,3;5,15\"")
        sys.exit(1)

    print(f"✓ UGV 位置:")
    for idx, (i, j) in enumerate(ugv_cells):
        x, y = grid_map.cell_to_world(i, j)
        print(f"  UGV {idx}: cell({i}, {j}) -> world({x:.2f}, {y:.2f})")

    # 验证 UGV 位置
    for idx, (i, j) in enumerate(ugv_cells):
        if not grid_map.is_free(i, j):
            print(f"警告：UGV {idx} 位置 ({i}, {j}) 不是 free cell！")

    # 创建通信配置
    comm_config = CommConfig(
        enabled=True,
        tx_power_db=args.tx_power,
        pathloss_n=args.pathloss_n,
        obstacle_penalty_db=args.obstacle_penalty,
        snr_threshold_db=args.threshold,
        eps_m=0.05
    )

    print(f"\n通信配置:")
    print(f"  - tx_power_db: {comm_config.tx_power_db}")
    print(f"  - pathloss_n: {comm_config.pathloss_n}")
    print(f"  - obstacle_penalty_db: {comm_config.obstacle_penalty_db}")
    print(f"  - snr_threshold_db: {comm_config.snr_threshold_db}")

    # 确定输出目录
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        map_id = map_path.stem
        output_dir = Path(__file__).parent.parent / "outputs" / "comm_inspect" / map_id

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n输出目录: {output_dir}")

    # 计算 SNR heatmap
    print()
    snr_heatmap = compute_snr_heatmap(grid_map, ugv_cells, comm_config)

    # 可视化
    heatmap_path = output_dir / "snr_heatmap.png"
    visualize_snr_heatmap(grid_map, snr_heatmap, ugv_cells, comm_config, heatmap_path)

    # 保存元数据
    meta_path = output_dir / "comm_meta.json"
    save_comm_meta(grid_map, ugv_cells, comm_config, snr_heatmap, meta_path)

    print("\n" + "=" * 60)
    print("✓ 完成！")
    print("=" * 60)
    print(f"\n输出文件:")
    print(f"  - {heatmap_path}")
    print(f"  - {meta_path}")
    print()


if __name__ == "__main__":
    main()
