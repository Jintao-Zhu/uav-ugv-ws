#!/usr/bin/env python3
"""
Day3: 坐标系验证

任务：
1. 在 preview 图上标注 5 个随机 free cell 的 (x_idx, y_idx)（scatter）
2. 肉眼确认点都落在白区（free cells）
3. 从一个测试实例中抽取一条 (sx, sy, gx, gy)，在图上标注 start/goal
4. 确认是否需要 y-flip（这一步能一次性排雷）

验收标准：
- 5 个随机点都落在白色区域（free cells）
- start/goal 标注清晰可见
- 坐标系方向正确（无需 y-flip）
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from agcoop.map import auto_load_map


def visualize_map_with_coords(grid_map, output_path, num_samples=5, seed=42):
    """
    可视化地图并标注随机 free cells 和测试实例

    Args:
        grid_map: GridMap 对象
        output_path: 输出图片路径
        num_samples: 随机采样的 free cell 数量
        seed: 随机种子
    """
    np.random.seed(seed)

    # 随机选择 5 个 free cells
    if len(grid_map.free_cells) < num_samples:
        print(f"警告：free cells 数量不足 {num_samples}，使用全部 {len(grid_map.free_cells)} 个")
        sampled_cells = grid_map.free_cells
    else:
        indices = np.random.choice(len(grid_map.free_cells), size=num_samples, replace=False)
        sampled_cells = [grid_map.free_cells[idx] for idx in indices]

    # 生成一个测试实例：从左下角到右上角
    # 内部坐标：(0, 0) = 左下角，(height-1, width-1) = 右上角
    start_cell = None
    goal_cell = None

    # 找一个靠近左下角的 free cell 作为 start
    for i in range(grid_map.height):
        for j in range(grid_map.width):
            if grid_map.is_free(i, j):
                start_cell = (i, j)
                break
        if start_cell:
            break

    # 找一个靠近右上角的 free cell 作为 goal
    for i in range(grid_map.height - 1, -1, -1):
        for j in range(grid_map.width - 1, -1, -1):
            if grid_map.is_free(i, j):
                goal_cell = (i, j)
                break
        if goal_cell:
            break

    if not start_cell or not goal_cell:
        print("错误：无法找到合适的 start/goal")
        return

    # 创建图形
    fig, ax = plt.subplots(figsize=(12, 10))

    # 显示地图（origin='lower' 表示 i=0 在底部）
    ax.imshow(grid_map.grid, cmap='gray_r', origin='lower', interpolation='nearest')

    # 标注 5 个随机 free cells
    for idx, (i, j) in enumerate(sampled_cells):
        # matplotlib 使用 (x, y) = (j, i)
        ax.scatter(j, i, c='cyan', s=200, marker='o', edgecolors='blue',
                   linewidths=2, label='Random free cells' if idx == 0 else '', zorder=3)

        # 标注坐标 (x_idx, y_idx) = (j, i)
        ax.text(j, i + 0.5, f'({j},{i})', fontsize=10, color='blue', weight='bold',
                ha='center', va='bottom', zorder=4,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8))

    # 标注 start（绿色）
    si, sj = start_cell
    ax.scatter(sj, si, c='green', s=300, marker='*', edgecolors='darkgreen',
               linewidths=2, label='Start', zorder=5)
    ax.text(sj, si - 1, f'START\n({sj},{si})', fontsize=12, color='darkgreen', weight='bold',
            ha='center', va='top', zorder=6,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.9))

    # 标注 goal（红色）
    gi, gj = goal_cell
    ax.scatter(gj, gi, c='red', s=300, marker='*', edgecolors='darkred',
               linewidths=2, label='Goal', zorder=5)
    ax.text(gj, gi + 1, f'GOAL\n({gj},{gi})', fontsize=12, color='darkred', weight='bold',
            ha='center', va='bottom', zorder=6,
            bbox=dict(boxstyle='round,pad=0.5', facecolor='lightcoral', alpha=0.9))

    # 设置坐标轴
    ax.set_xlabel('j (column / x-index)', fontsize=14, weight='bold')
    ax.set_ylabel('i (row / y-index)', fontsize=14, weight='bold')
    ax.set_title(
        f'Day3: 坐标系验证\n'
        f'地图尺寸: {grid_map.width}x{grid_map.height}, '
        f'Free cells: {len(grid_map.free_cells)}\n'
        f'坐标约定: (j, i) = (x-index, y-index), origin=lower-left',
        fontsize=14, weight='bold'
    )

    # 添加网格
    ax.set_xticks(np.arange(-0.5, grid_map.width, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, grid_map.height, 1), minor=True)
    ax.grid(which='minor', color='gray', linestyle=':', linewidth=0.5, alpha=0.5)

    # 添加图例
    ax.legend(loc='upper right', fontsize=12)

    # 添加说明文本
    info_text = (
        f"验证要点：\n"
        f"1. 青色圆点应全部落在白色区域（free cells）\n"
        f"2. START（绿星）和 GOAL（红星）应在白色区域\n"
        f"3. 坐标 (j, i) 对应 (列, 行)，原点在左下角\n"
        f"4. 如果标注位置正确，则无需 y-flip\n\n"
        f"测试实例：\n"
        f"  Start: cell({si}, {sj}) = (i={si}, j={sj})\n"
        f"  Goal:  cell({gi}, {gj}) = (i={gi}, j={gj})"
    )

    ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"✓ 可视化已保存: {output_path}")

    # 输出详细信息
    print("\n" + "=" * 60)
    print("随机采样的 5 个 free cells:")
    print("=" * 60)
    for idx, (i, j) in enumerate(sampled_cells):
        x, y = grid_map.cell_to_world(i, j)
        print(f"  {idx+1}. cell({i:2d}, {j:2d}) -> world({x:6.2f}, {y:6.2f})")

    print("\n" + "=" * 60)
    print("测试实例（内部坐标）:")
    print("=" * 60)
    sx_world, sy_world = grid_map.cell_to_world(si, sj)
    gx_world, gy_world = grid_map.cell_to_world(gi, gj)
    print(f"  Start: cell({si}, {sj}) -> world({sx_world:.2f}, {sy_world:.2f})")
    print(f"  Goal:  cell({gi}, {gj}) -> world({gx_world:.2f}, {gy_world:.2f})")

    # 验证坐标系
    print("\n" + "=" * 60)
    print("坐标系验证:")
    print("=" * 60)
    print(f"  内部坐标约定: (i, j) = (row, col)")
    print(f"  - i: 行索引，0 = 底部，{grid_map.height-1} = 顶部")
    print(f"  - j: 列索引，0 = 左侧，{grid_map.width-1} = 右侧")
    print(f"  可视化约定: origin='lower' (i=0 在底部)")
    print(f"  matplotlib 绘图: scatter(j, i) = scatter(x, y)")

    # 检查是否需要 y-flip
    print("\n" + "=" * 60)
    print("Y-flip 检查:")
    print("=" * 60)

    # 检查 start 是否在底部
    if si < grid_map.height / 2:
        print(f"  ✓ Start 在底部 (i={si} < {grid_map.height/2:.1f})")
    else:
        print(f"  ✗ Start 在顶部 (i={si} >= {grid_map.height/2:.1f})")

    # 检查 goal 是否在顶部
    if gi > grid_map.height / 2:
        print(f"  ✓ Goal 在顶部 (i={gi} > {grid_map.height/2:.1f})")
    else:
        print(f"  ✗ Goal 在底部 (i={gi} <= {grid_map.height/2:.1f})")

    # 检查图像显示
    print(f"\n  图像显示检查:")
    print(f"  - 如果 START（绿星）在图像底部，则坐标系正确")
    print(f"  - 如果 GOAL（红星）在图像顶部，则坐标系正确")
    print(f"  - 如果位置相反，则需要 y-flip")

    print("\n" + "=" * 60)
    print("结论:")
    print("=" * 60)
    print("  请打开图片，肉眼确认：")
    print("  1. 所有青色圆点都在白色区域（free cells）")
    print("  2. START（绿星）在左下角附近")
    print("  3. GOAL（红星）在右上角附近")
    print("  4. 坐标标注与实际位置一致")
    print("\n  如果以上都正确，则坐标系无需调整！")
    print("=" * 60)


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Day3: 坐标系验证")
    print("=" * 60 + "\n")

    # 使用 test_small.map
    map_path = Path(__file__).parent / "maps" / "test_small.map"

    if not map_path.exists():
        print(f"错误：地图文件不存在: {map_path}")
        sys.exit(1)

    # 加载地图
    print(f"加载地图: {map_path}")
    try:
        grid_map = auto_load_map(str(map_path))
    except Exception as e:
        print(f"错误：无法加载地图: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print(f"✓ 地图加载成功:")
    print(f"  - 尺寸: {grid_map.width}x{grid_map.height}")
    print(f"  - 分辨率: {grid_map.resolution} m/cell")
    print(f"  - 原点: {grid_map.origin}")
    print(f"  - 自由格子: {len(grid_map.free_cells)}")

    # 生成可视化
    output_path = Path(__file__).parent / "outputs" / "day3_coord_verification.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"\n生成可视化...")
    visualize_map_with_coords(grid_map, output_path, num_samples=5, seed=42)

    print("\n" + "=" * 60)
    print("✓ Day3 验证完成！")
    print("=" * 60)
    print(f"\n请查看图片: {output_path}")
    print("确认所有标注点都在正确位置。\n")


if __name__ == "__main__":
    main()
