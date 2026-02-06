#!/usr/bin/env python3
"""
候选点生成原型

功能：
- 计算每个 free cell 的度数（4-连通邻居数量）
- 选择度 ≥ 3 的路口点（junction points）
- 随机抽样补齐到目标数量 R（默认 12）
- 输出 candidates.json

用途：
- Day 8 的 coverage baseline
- 会合点候选集
- 任务分配的参考点

用法：
    python scripts/gen_candidates.py maps/map_01.map
    python scripts/gen_candidates.py maps/map_01.map --num-candidates 20
    python scripts/gen_candidates.py maps/test_ros.yaml --output outputs/candidates.json
"""

import sys
import json
import argparse
from pathlib import Path
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.map import auto_load_map, neighbors


def compute_cell_degrees(grid_map, connectivity=4):
    """
    计算每个 free cell 的度数（邻居数量）。

    Args:
        grid_map: GridMap 对象
        connectivity: 连通性（4 或 8）

    Returns:
        字典 {(i, j): degree}
    """
    degrees = {}

    for cell in grid_map.free_cells:
        i, j = cell
        neighbor_list = neighbors.get_neighbors(i, j, grid_map.grid, connectivity)
        degrees[cell] = len(neighbor_list)

    return degrees


def select_junction_points(degrees, min_degree=3):
    """
    选择度数 ≥ min_degree 的路口点。

    Args:
        degrees: 度数字典 {(i, j): degree}
        min_degree: 最小度数阈值

    Returns:
        路口点列表 [(i, j), ...]
    """
    junctions = [cell for cell, deg in degrees.items() if deg >= min_degree]
    return junctions


def sample_additional_points(all_cells, existing_points, num_additional, seed=42):
    """
    从剩余点中随机抽样补齐。

    Args:
        all_cells: 所有 free cells
        existing_points: 已选择的点
        num_additional: 需要补充的数量
        seed: 随机种子

    Returns:
        补充的点列表
    """
    # 找出未被选择的点
    existing_set = set(existing_points)
    remaining = [cell for cell in all_cells if cell not in existing_set]

    if len(remaining) == 0:
        return []

    # 随机抽样
    np.random.seed(seed)
    num_to_sample = min(num_additional, len(remaining))
    sampled_indices = np.random.choice(len(remaining), size=num_to_sample, replace=False)
    sampled_points = [remaining[idx] for idx in sampled_indices]

    return sampled_points


def generate_candidates(grid_map, num_candidates=12, min_degree=3, seed=42):
    """
    生成候选点集。

    策略：
    1. 选择所有度 ≥ min_degree 的路口点
    2. 如果不足 num_candidates，随机抽样补齐
    3. 如果超过 num_candidates，随机抽样缩减

    Args:
        grid_map: GridMap 对象
        num_candidates: 目标候选点数量
        min_degree: 最小度数阈值
        seed: 随机种子

    Returns:
        候选点信息字典
    """
    # 计算度数
    degrees = compute_cell_degrees(grid_map, connectivity=4)

    # 选择路口点
    junctions = select_junction_points(degrees, min_degree)

    print(f"路口点（度 ≥ {min_degree}）: {len(junctions)} 个")

    # 根据数量调整
    if len(junctions) >= num_candidates:
        # 路口点已经足够，随机抽样缩减
        np.random.seed(seed)
        selected_indices = np.random.choice(len(junctions), size=num_candidates, replace=False)
        selected_points = [junctions[idx] for idx in selected_indices]
        print(f"从路口点中随机抽样 {num_candidates} 个")
    else:
        # 路口点不足，补充随机点
        num_additional = num_candidates - len(junctions)
        additional_points = sample_additional_points(
            grid_map.free_cells, junctions, num_additional, seed
        )
        selected_points = junctions + additional_points
        print(f"补充随机点 {len(additional_points)} 个")

    # 构建候选点信息
    candidates_info = {
        'map_info': {
            'map_id': 'unknown',
            'width': grid_map.width,
            'height': grid_map.height,
            'resolution': grid_map.resolution,
            'origin': list(grid_map.origin),
            'free_cells': len(grid_map.free_cells),
        },
        'generation_params': {
            'num_candidates': num_candidates,
            'min_degree': min_degree,
            'seed': seed,
            'connectivity': 4,
        },
        'statistics': {
            'total_junctions': len(junctions),
            'selected_junctions': min(len(junctions), num_candidates),
            'random_points': max(0, num_candidates - len(junctions)),
            'final_count': len(selected_points),
        },
        'candidates': []
    }

    # 添加候选点详细信息
    for idx, cell in enumerate(selected_points):
        i, j = cell
        x, y = grid_map.cell_to_world(i, j)
        degree = degrees[cell]
        is_junction = cell in junctions

        candidates_info['candidates'].append({
            'id': idx,
            'cell': [int(i), int(j)],
            'world': [float(x), float(y)],
            'degree': int(degree),
            'is_junction': bool(is_junction),
        })

    return candidates_info


def visualize_candidates(grid_map, candidates_info, output_path):
    """
    可视化候选点（可选）。

    Args:
        grid_map: GridMap 对象
        candidates_info: 候选点信息
        output_path: 输出图片路径
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("警告：matplotlib 未安装，跳过可视化")
        return

    fig, ax = plt.subplots(figsize=(10, 10))

    # 显示地图
    ax.imshow(grid_map.grid, cmap='gray_r', origin='lower', interpolation='nearest')

    # 绘制候选点
    junctions = []
    random_points = []

    for cand in candidates_info['candidates']:
        i, j = cand['cell']
        if cand['is_junction']:
            junctions.append((j, i))  # matplotlib 使用 (x, y) = (j, i)
        else:
            random_points.append((j, i))

    # 绘制路口点（红色）
    if junctions:
        jx, jy = zip(*junctions)
        ax.scatter(jx, jy, c='red', s=100, marker='o', edgecolors='black',
                   linewidths=2, label=f'Junction points ({len(junctions)})', zorder=3)

    # 绘制随机点（蓝色）
    if random_points:
        rx, ry = zip(*random_points)
        ax.scatter(rx, ry, c='blue', s=100, marker='s', edgecolors='black',
                   linewidths=2, label=f'Random points ({len(random_points)})', zorder=3)

    # 标注候选点 ID
    for cand in candidates_info['candidates']:
        i, j = cand['cell']
        ax.text(j, i, str(cand['id']), fontsize=8, color='white', weight='bold',
                ha='center', va='center', zorder=4)

    ax.set_xlabel('j (column / x)', fontsize=12)
    ax.set_ylabel('i (row / y)', fontsize=12)
    ax.set_title(f'Candidate Points (R={len(candidates_info["candidates"])})', fontsize=14)
    ax.legend(loc='upper right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"可视化已保存: {output_path}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='候选点生成工具')
    parser.add_argument('map_path', type=str, help='地图文件路径')
    parser.add_argument('--num-candidates', type=int, default=12,
                        help='候选点数量（默认：12）')
    parser.add_argument('--min-degree', type=int, default=3,
                        help='路口点最小度数（默认：3）')
    parser.add_argument('--seed', type=int, default=42,
                        help='随机种子（默认：42）')
    parser.add_argument('--output', type=str, default=None,
                        help='输出 JSON 路径（默认：与地图同目录）')
    parser.add_argument('--visualize', action='store_true',
                        help='生成可视化图片')
    args = parser.parse_args()

    # 检查地图文件
    map_path = Path(args.map_path)
    if not map_path.exists():
        print(f"错误：地图文件不存在: {map_path}")
        sys.exit(1)

    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = map_path.parent / f"{map_path.stem}_candidates.json"

    # 加载地图
    print(f"加载地图: {map_path}")
    try:
        grid_map = auto_load_map(str(map_path))
    except Exception as e:
        print(f"错误：无法加载地图: {e}")
        sys.exit(1)

    print(f"地图加载成功:")
    print(f"  - 尺寸: {grid_map.width}x{grid_map.height}")
    print(f"  - 自由格子: {len(grid_map.free_cells)}")

    # 生成候选点
    print(f"\n生成候选点（目标数量: {args.num_candidates}）")
    candidates_info = generate_candidates(
        grid_map,
        num_candidates=args.num_candidates,
        min_degree=args.min_degree,
        seed=args.seed
    )

    # 更新 map_id
    candidates_info['map_info']['map_id'] = map_path.stem

    # 保存 JSON
    with open(output_path, 'w') as f:
        json.dump(candidates_info, f, indent=2, ensure_ascii=False)

    print(f"\n候选点已保存: {output_path}")

    # 输出统计
    print("\n统计信息:")
    print(f"  - 路口点: {candidates_info['statistics']['total_junctions']} 个")
    print(f"  - 选中路口点: {candidates_info['statistics']['selected_junctions']} 个")
    print(f"  - 随机补充点: {candidates_info['statistics']['random_points']} 个")
    print(f"  - 最终候选点: {candidates_info['statistics']['final_count']} 个")

    # 可视化（可选）
    if args.visualize:
        viz_path = output_path.parent / f"{output_path.stem}_viz.png"
        print(f"\n生成可视化...")
        visualize_candidates(grid_map, candidates_info, viz_path)

    print("\n✓ 候选点生成完成！")


if __name__ == "__main__":
    main()
