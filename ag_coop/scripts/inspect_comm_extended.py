#!/usr/bin/env python3
"""
通信检查工具（扩展版）：生成 SNR heatmap + 一致性检查

新增功能：
1. best_ugv 分区图 - 验证 UGV 选择逻辑
2. blocked_count heatmap - 验证障碍遮挡计数

用法：
    python scripts/inspect_comm_extended.py --map maps/map_01.map --ugv "2,2;10,10;15,15"
    python scripts/inspect_comm_extended.py --map maps/test_small.map --ugv "1,1;8,8"
"""

import sys
import json
import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.patches import Rectangle

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.map import auto_load_map
from agcoop.comm import CommConfig, compute_best_snr, compute_snr_to_ugvs, count_blocked_cells


def parse_ugv_positions(ugv_str: str) -> list:
    """解析 UGV 位置字符串"""
    positions = []
    for pos_str in ugv_str.split(';'):
        i, j = map(int, pos_str.split(','))
        positions.append((i, j))
    return positions


def compute_extended_heatmaps(grid_map, ugv_cells: list, comm_config: CommConfig):
    """
    计算扩展热力图

    Returns:
        snr_heatmap: SNR 值
        best_ugv_heatmap: 最佳 UGV ID
        blocked_heatmap: 障碍遮挡数量
    """
    height, width = grid_map.height, grid_map.width
    snr_heatmap = np.full((height, width), np.nan)
    best_ugv_heatmap = np.full((height, width), -1, dtype=int)
    blocked_heatmap = np.full((height, width), np.nan)

    print(f"计算扩展热力图...")
    print(f"  地图尺寸: {width}x{height}")
    print(f"  Free cells: {len(grid_map.free_cells)}")
    print(f"  UGV 数量: {len(ugv_cells)}")

    for idx, (i, j) in enumerate(grid_map.free_cells):
        if (idx + 1) % 50 == 0:
            print(f"  进度: {idx+1}/{len(grid_map.free_cells)}")

        # 计算 SNR 和最佳 UGV
        snr_best, best_ugv_id, outage = compute_best_snr(
            (i, j), ugv_cells, grid_map, comm_config
        )
        snr_heatmap[i, j] = snr_best
        best_ugv_heatmap[i, j] = best_ugv_id

        # 计算到最佳 UGV 的障碍数量
        if best_ugv_id >= 0:
            blocked_count = count_blocked_cells(grid_map, (i, j), ugv_cells[best_ugv_id])
            blocked_heatmap[i, j] = blocked_count

    print(f"  完成！")

    return snr_heatmap, best_ugv_heatmap, blocked_heatmap


def visualize_snr_heatmap(
    grid_map,
    snr_heatmap: np.ndarray,
    ugv_cells: list,
    comm_config: CommConfig,
    output_path: Path
):
    """可视化 SNR heatmap（原版）"""
    fig, ax = plt.subplots(figsize=(12, 10))

    valid_snr = snr_heatmap[~np.isnan(snr_heatmap)]
    snr_min = np.min(valid_snr)
    snr_max = np.max(valid_snr)
    snr_mean = np.mean(valid_snr)

    cmap = plt.cm.RdYlGn
    norm = mcolors.Normalize(vmin=snr_min, vmax=snr_max)

    im = ax.imshow(
        snr_heatmap,
        cmap=cmap,
        norm=norm,
        origin='lower',
        interpolation='nearest',
        aspect='equal'
    )

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('SNR (dB)', fontsize=12, weight='bold')

    # 标注 UGV
    for idx, (i, j) in enumerate(ugv_cells):
        ax.scatter(j, i, c='blue', s=300, marker='s', edgecolors='white',
                   linewidths=3, label='UGV' if idx == 0 else '', zorder=10)
        ax.text(j, i, f'UGV{idx}', fontsize=10, color='white', weight='bold',
                ha='center', va='center', zorder=11)

    # 阈值线
    threshold = comm_config.snr_threshold_db
    ax.contour(snr_heatmap, levels=[threshold], colors='black', linewidths=2,
               linestyles='--', origin='lower')

    ax.set_xlabel('j (column / x-index)', fontsize=12, weight='bold')
    ax.set_ylabel('i (row / y-index)', fontsize=12, weight='bold')
    ax.set_title(
        f'SNR Heatmap\n'
        f'Map: {grid_map.width}x{grid_map.height}, '
        f'UGVs: {len(ugv_cells)}, '
        f'Threshold: {threshold:.1f} dB',
        fontsize=14, weight='bold'
    )

    ax.set_xticks(np.arange(-0.5, grid_map.width, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, grid_map.height, 1), minor=True)
    ax.grid(which='minor', color='gray', linestyle=':', linewidth=0.3, alpha=0.3)

    ax.legend(loc='upper right', fontsize=12)

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

    print(f"✓ SNR Heatmap 已保存: {output_path}")


def visualize_best_ugv_map(
    grid_map,
    best_ugv_heatmap: np.ndarray,
    ugv_cells: list,
    output_path: Path
):
    """
    可视化 best_ugv 分区图

    验证要点：
    - 应该看到清晰的分界线（Voronoi 风格）
    - 不应该有碎片化的随机噪声
    """
    fig, ax = plt.subplots(figsize=(12, 10))

    n_ugv = len(ugv_cells)

    # 创建离散颜色映射
    colors = plt.cm.tab10(np.linspace(0, 1, n_ugv))
    cmap = mcolors.ListedColormap(colors)
    bounds = np.arange(-0.5, n_ugv + 0.5, 1)
    norm = mcolors.BoundaryNorm(bounds, cmap.N)

    # 绘制分区图
    im = ax.imshow(
        best_ugv_heatmap,
        cmap=cmap,
        norm=norm,
        origin='lower',
        interpolation='nearest',
        aspect='equal'
    )

    # 添加 colorbar
    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, ticks=range(n_ugv))
    cbar.set_label('Best UGV ID', fontsize=12, weight='bold')
    cbar.ax.set_yticklabels([f'UGV {i}' for i in range(n_ugv)])

    # 标注 UGV 位置
    for idx, (i, j) in enumerate(ugv_cells):
        ax.scatter(j, i, c='white', s=400, marker='*', edgecolors='black',
                   linewidths=3, label='UGV' if idx == 0 else '', zorder=10)
        ax.text(j, i+0.5, f'UGV{idx}', fontsize=10, color='black', weight='bold',
                ha='center', va='bottom', zorder=11,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    ax.set_xlabel('j (column / x-index)', fontsize=12, weight='bold')
    ax.set_ylabel('i (row / y-index)', fontsize=12, weight='bold')
    ax.set_title(
        f'Best UGV Partition Map\n'
        f'Map: {grid_map.width}x{grid_map.height}, UGVs: {len(ugv_cells)}',
        fontsize=14, weight='bold'
    )

    ax.set_xticks(np.arange(-0.5, grid_map.width, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, grid_map.height, 1), minor=True)
    ax.grid(which='minor', color='gray', linestyle=':', linewidth=0.3, alpha=0.3)

    ax.legend(loc='upper right', fontsize=12)

    # 添加验证说明
    info_text = (
        f"验证要点：\n"
        f"1. 应该看到清晰的分界线\n"
        f"   （类似 Voronoi 图）\n"
        f"2. 每个 UGV 周围有连续区域\n"
        f"3. 不应该有碎片化噪声\n\n"
        f"如果出现碎片化：\n"
        f"→ 可能是 raycast 或索引问题"
    )

    ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"✓ Best UGV Map 已保存: {output_path}")


def visualize_blocked_heatmap(
    grid_map,
    blocked_heatmap: np.ndarray,
    ugv_cells: list,
    output_path: Path
):
    """
    可视化 blocked_count heatmap

    验证要点：
    - 障碍后方应该有更高的 blocked 值
    - 深红阴影区应对应障碍物位置
    """
    fig, ax = plt.subplots(figsize=(12, 10))

    valid_blocked = blocked_heatmap[~np.isnan(blocked_heatmap)]
    blocked_min = int(np.min(valid_blocked))
    blocked_max = int(np.max(valid_blocked))
    blocked_mean = np.mean(valid_blocked)

    # 使用 Reds 颜色映射（白色=0，深红=多）
    cmap = plt.cm.Reds
    norm = mcolors.Normalize(vmin=blocked_min, vmax=blocked_max)

    im = ax.imshow(
        blocked_heatmap,
        cmap=cmap,
        norm=norm,
        origin='lower',
        interpolation='nearest',
        aspect='equal'
    )

    cbar = plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label('Blocked Cell Count', fontsize=12, weight='bold')

    # 标注 UGV
    for idx, (i, j) in enumerate(ugv_cells):
        ax.scatter(j, i, c='blue', s=300, marker='s', edgecolors='white',
                   linewidths=3, label='UGV' if idx == 0 else '', zorder=10)
        ax.text(j, i, f'UGV{idx}', fontsize=10, color='white', weight='bold',
                ha='center', va='center', zorder=11)

    # 叠加障碍物轮廓
    obstacle_mask = (grid_map.grid == 1)
    ax.contour(obstacle_mask, levels=[0.5], colors='black', linewidths=1.5,
               linestyles='-', origin='lower', alpha=0.5)

    ax.set_xlabel('j (column / x-index)', fontsize=12, weight='bold')
    ax.set_ylabel('i (row / y-index)', fontsize=12, weight='bold')
    ax.set_title(
        f'Blocked Cell Count Heatmap\n'
        f'Map: {grid_map.width}x{grid_map.height}, UGVs: {len(ugv_cells)}',
        fontsize=14, weight='bold'
    )

    ax.set_xticks(np.arange(-0.5, grid_map.width, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, grid_map.height, 1), minor=True)
    ax.grid(which='minor', color='gray', linestyle=':', linewidth=0.3, alpha=0.3)

    ax.legend(loc='upper right', fontsize=12)

    info_text = (
        f"验证要点：\n"
        f"1. 障碍后方应有更高 blocked 值\n"
        f"   （深红色阴影区）\n"
        f"2. 黑色轮廓：障碍物位置\n"
        f"3. 阴影区应对应障碍物\n\n"
        f"Blocked 统计：\n"
        f"  Min: {blocked_min}\n"
        f"  Max: {blocked_max}\n"
        f"  Mean: {blocked_mean:.2f}\n\n"
        f"如果阴影区不对应障碍：\n"
        f"→ raycast 计数可能有问题"
    )

    ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
            fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.9))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"✓ Blocked Heatmap 已保存: {output_path}")


def save_extended_meta(
    grid_map,
    ugv_cells: list,
    comm_config: CommConfig,
    snr_heatmap: np.ndarray,
    best_ugv_heatmap: np.ndarray,
    blocked_heatmap: np.ndarray,
    output_path: Path
):
    """保存扩展元数据"""
    valid_snr = snr_heatmap[~np.isnan(snr_heatmap)]
    valid_blocked = blocked_heatmap[~np.isnan(blocked_heatmap)]

    # 统计每个 UGV 的覆盖区域
    ugv_coverage = {}
    for ugv_id in range(len(ugv_cells)):
        count = np.sum(best_ugv_heatmap == ugv_id)
        ugv_coverage[f'ugv_{ugv_id}'] = int(count)

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
            'min': round(float(np.min(valid_snr)), 2),
            'max': round(float(np.max(valid_snr)), 2),
            'mean': round(float(np.mean(valid_snr)), 2),
            'std': round(float(np.std(valid_snr)), 2),
            'outage_count': int(np.sum(valid_snr < comm_config.snr_threshold_db)),
            'outage_percent': round(float(np.sum(valid_snr < comm_config.snr_threshold_db) / len(valid_snr) * 100), 2),
        },
        'blocked_statistics': {
            'min': int(np.min(valid_blocked)),
            'max': int(np.max(valid_blocked)),
            'mean': round(float(np.mean(valid_blocked)), 2),
            'std': round(float(np.std(valid_blocked)), 2),
        },
        'ugv_coverage': ugv_coverage,
    }

    with open(output_path, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"✓ 扩展元数据已保存: {output_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='通信检查工具（扩展版）')
    parser.add_argument('--map', type=str, required=True, help='地图文件路径')
    parser.add_argument('--ugv', type=str, required=True,
                        help='UGV 位置（格式："i1,j1;i2,j2;i3,j3"）')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='输出目录（默认：outputs/comm_inspect_ext/<map_id>）')
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
    print("通信检查工具（扩展版）")
    print("=" * 60 + "\n")

    # 加载地图
    map_path = Path(args.map)
    if not map_path.exists():
        print(f"错误：地图文件不存在: {map_path}")
        sys.exit(1)

    print(f"加载地图: {map_path}")
    grid_map = auto_load_map(str(map_path))
    print(f"✓ 地图加载成功: {grid_map.width}x{grid_map.height}, {len(grid_map.free_cells)} free cells")

    # 解析 UGV 位置
    print(f"\n解析 UGV 位置: {args.ugv}")
    ugv_cells = parse_ugv_positions(args.ugv)
    print(f"✓ UGV 位置:")
    for idx, (i, j) in enumerate(ugv_cells):
        x, y = grid_map.cell_to_world(i, j)
        print(f"  UGV {idx}: cell({i}, {j}) -> world({x:.2f}, {y:.2f})")

    # 创建通信配置
    comm_config = CommConfig(
        enabled=True,
        tx_power_db=args.tx_power,
        pathloss_n=args.pathloss_n,
        obstacle_penalty_db=args.obstacle_penalty,
        snr_threshold_db=args.threshold,
        eps_m=0.05
    )

    # 确定输出目录
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        map_id = map_path.stem
        output_dir = Path(__file__).parent.parent / "outputs" / "comm_inspect_ext" / map_id

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n输出目录: {output_dir}")

    # 计算扩展热力图
    print()
    snr_heatmap, best_ugv_heatmap, blocked_heatmap = compute_extended_heatmaps(
        grid_map, ugv_cells, comm_config
    )

    # 生成可视化
    print("\n生成可视化...")
    visualize_snr_heatmap(grid_map, snr_heatmap, ugv_cells, comm_config,
                          output_dir / "snr_heatmap.png")
    visualize_best_ugv_map(grid_map, best_ugv_heatmap, ugv_cells,
                           output_dir / "best_ugv_map.png")
    visualize_blocked_heatmap(grid_map, blocked_heatmap, ugv_cells,
                              output_dir / "blocked_heatmap.png")

    # 保存元数据
    save_extended_meta(grid_map, ugv_cells, comm_config,
                       snr_heatmap, best_ugv_heatmap, blocked_heatmap,
                       output_dir / "comm_meta_extended.json")

    print("\n" + "=" * 60)
    print("✓ 完成！")
    print("=" * 60)
    print(f"\n输出文件:")
    print(f"  - {output_dir / 'snr_heatmap.png'}")
    print(f"  - {output_dir / 'best_ugv_map.png'}")
    print(f"  - {output_dir / 'blocked_heatmap.png'}")
    print(f"  - {output_dir / 'comm_meta_extended.json'}")
    print()


if __name__ == "__main__":
    main()
