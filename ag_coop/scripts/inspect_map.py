#!/usr/bin/env python3
"""
地图检查工具

功能：
- 加载地图并输出元数据（map_meta.json）
- 生成地图预览图（map_preview.png）
- 用于验证地图加载正确性（特别是上下翻转问题）

用法：
    python scripts/inspect_map.py maps/map_01.map
    python scripts/inspect_map.py maps/test_ros.yaml --output-dir outputs/map_inspect
"""

import sys
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.map import auto_load_map, GridMap


def generate_map_meta(grid_map: GridMap, map_path: str) -> dict:
    """
    生成地图元数据。

    Args:
        grid_map: GridMap 对象
        map_path: 地图文件路径

    Returns:
        元数据字典
    """
    # 统计自由格子和障碍格子
    free_count = len(grid_map.free_cells)
    total_cells = grid_map.width * grid_map.height
    obstacle_count = total_cells - free_count

    # 构建元数据
    meta = {
        'map_id': Path(map_path).stem,
        'map_path': str(map_path),
        'width': grid_map.width,
        'height': grid_map.height,
        'total_cells': total_cells,
        'free_count': free_count,
        'obstacle_count': obstacle_count,
        'free_percent': round(free_count / total_cells * 100, 2),
        'resolution': grid_map.resolution,
        'origin': list(grid_map.origin),
        'frame': grid_map.frame,
        'connectivity_default': 4,
        'coordinate_convention': {
            'index_order': 'row_col',  # (i, j) = (row, col) = (y_index, x_index)
            'origin_location': 'lower_left',  # origin at cell(0,0) lower-left corner
            'y_axis_direction': 'up',  # y increases upward (standard Cartesian)
            'cell_center_offset': 0.5,  # cell center at (i+0.5, j+0.5) * resolution
            'note': 'i=row(y), j=col(x); world_x = origin_x + (j+0.5)*resolution'
        }
    }

    return meta


def generate_map_preview(grid_map: GridMap, output_path: str, show_grid: bool = False):
    """
    生成地图预览图。

    Args:
        grid_map: GridMap 对象
        output_path: 输出图片路径
        show_grid: 是否显示网格线
    """
    # 创建图形
    fig, ax = plt.subplots(figsize=(10, 10))

    # 显示地图（0=白色/自由，1=黑色/障碍）
    # 注意：imshow 默认 origin='upper'，需要翻转以匹配我们的坐标系
    ax.imshow(grid_map.grid, cmap='gray_r', origin='lower', interpolation='nearest')

    # 添加网格线（可选）
    if show_grid:
        ax.set_xticks(np.arange(-0.5, grid_map.width, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, grid_map.height, 1), minor=True)
        ax.grid(which='minor', color='gray', linestyle='-', linewidth=0.5, alpha=0.3)

    # 设置坐标轴
    ax.set_xlabel('j (column / x)', fontsize=12)
    ax.set_ylabel('i (row / y)', fontsize=12)
    ax.set_title(f'Map Preview: {grid_map.width}x{grid_map.height} '
                 f'({len(grid_map.free_cells)} free cells, '
                 f'{len(grid_map.free_cells) / (grid_map.width * grid_map.height) * 100:.1f}%)',
                 fontsize=14)

    # 添加图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='white', edgecolor='black', label='Free'),
        Patch(facecolor='black', edgecolor='black', label='Obstacle')
    ]
    ax.legend(handles=legend_elements, loc='upper right')

    # 保存图片
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"地图预览已保存: {output_path}")


def generate_detailed_preview(grid_map: GridMap, output_path: str):
    """
    生成详细的地图预览（包含坐标标注）。

    Args:
        grid_map: GridMap 对象
        output_path: 输出图片路径
    """
    fig, ax = plt.subplots(figsize=(12, 10))

    # 显示地图
    ax.imshow(grid_map.grid, cmap='gray_r', origin='lower', interpolation='nearest')

    # 添加网格线
    ax.set_xticks(np.arange(-0.5, grid_map.width, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, grid_map.height, 1), minor=True)
    ax.grid(which='minor', color='gray', linestyle='-', linewidth=0.5, alpha=0.3)

    # 标注角落格子
    corners = [
        (0, 0, 'cell(0,0)\norigin'),
        (0, grid_map.width - 1, f'cell(0,{grid_map.width-1})'),
        (grid_map.height - 1, 0, f'cell({grid_map.height-1},0)'),
        (grid_map.height - 1, grid_map.width - 1, f'cell({grid_map.height-1},{grid_map.width-1})'),
    ]

    for i, j, label in corners:
        color = 'red' if grid_map.grid[i, j] == 0 else 'yellow'
        ax.plot(j, i, 'o', color=color, markersize=10, markeredgecolor='black', markeredgewidth=2)
        ax.text(j, i, f'  {label}', fontsize=8, color=color, weight='bold',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.7))

    # 设置坐标轴
    ax.set_xlabel('j (column / x)', fontsize=12)
    ax.set_ylabel('i (row / y)', fontsize=12)
    ax.set_title(f'Detailed Map Preview with Corner Labels\n'
                 f'{grid_map.width}x{grid_map.height}, '
                 f'resolution={grid_map.resolution}, origin={grid_map.origin}',
                 fontsize=14)

    # 添加图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='white', edgecolor='black', label='Free'),
        Patch(facecolor='black', edgecolor='black', label='Obstacle'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='red',
                   markersize=10, label='Free corner'),
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='yellow',
                   markersize=10, label='Obstacle corner'),
    ]
    ax.legend(handles=legend_elements, loc='upper right')

    # 保存图片
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"详细预览已保存: {output_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='地图检查工具')
    parser.add_argument('map_path', type=str, help='地图文件路径')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='输出目录（默认：与地图同目录）')
    parser.add_argument('--show-grid', action='store_true',
                        help='在预览图中显示网格线')
    parser.add_argument('--detailed', action='store_true',
                        help='生成详细预览（包含角落标注）')
    args = parser.parse_args()

    # 检查地图文件是否存在
    map_path = Path(args.map_path)
    if not map_path.exists():
        print(f"错误：地图文件不存在: {map_path}")
        sys.exit(1)

    # 确定输出目录
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = map_path.parent

    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载地图
    print(f"加载地图: {map_path}")
    try:
        grid_map = auto_load_map(str(map_path))
    except Exception as e:
        print(f"错误：无法加载地图: {e}")
        sys.exit(1)

    print(f"地图加载成功:")
    print(f"  - 尺寸: {grid_map.width}x{grid_map.height}")
    print(f"  - 自由格子: {len(grid_map.free_cells)} ({len(grid_map.free_cells) / (grid_map.width * grid_map.height) * 100:.1f}%)")
    print(f"  - 分辨率: {grid_map.resolution}")
    print(f"  - 原点: {grid_map.origin}")

    # 生成元数据
    meta = generate_map_meta(grid_map, str(map_path))
    meta_path = output_dir / f"{map_path.stem}_meta.json"

    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)

    print(f"\n元数据已保存: {meta_path}")

    # 生成预览图
    preview_path = output_dir / f"{map_path.stem}_preview.png"
    generate_map_preview(grid_map, str(preview_path), show_grid=args.show_grid)

    # 生成详细预览（可选）
    if args.detailed:
        detailed_path = output_dir / f"{map_path.stem}_detailed.png"
        generate_detailed_preview(grid_map, str(detailed_path))

    print("\n✓ 地图检查完成！")
    print(f"\n输出文件:")
    print(f"  - 元数据: {meta_path}")
    print(f"  - 预览图: {preview_path}")
    if args.detailed:
        print(f"  - 详细预览: {detailed_path}")

    print("\n请检查预览图，确认:")
    print("  1. 地图方向正确（没有上下翻转）")
    print("  2. 自由区域（白色）和障碍（黑色）符合预期")
    print("  3. 角落格子位置正确")


if __name__ == "__main__":
    main()
