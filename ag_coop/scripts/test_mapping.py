#!/usr/bin/env python3
"""
坐标映射单元测试脚本

测试内容：
1. 随机抽 50 个 free cells，验证往返转换（cell -> world -> cell）
2. 随机抽 50 个 world 点，验证往返转换（world -> cell -> world）
3. 输出详细的测试报告（mapping_report.json）

验收标准：
- 所有测试通过
- 最大误差在可接受范围内
- 越界次数为 0
"""

import sys
import json
import argparse
from pathlib import Path
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.map import auto_load_map, mapping


def test_cell_to_world_to_cell(grid_map, n_samples=50, seed=42, test_all=False):
    """
    测试 cell -> world -> cell 往返转换。

    Args:
        grid_map: GridMap 对象
        n_samples: 采样数量（test_all=False 时使用）
        seed: 随机种子
        test_all: 是否测试所有 free cells（True 时忽略 n_samples）

    Returns:
        测试结果字典
    """
    np.random.seed(seed)

    results = {
        'test_name': 'cell_to_world_to_cell',
        'test_all': test_all,
        'n_samples': 0,
        'pass_count': 0,
        'fail_count': 0,
        'failures': [],
    }

    # 选择测试集
    if test_all:
        # 测试所有 free cells
        test_cells = grid_map.free_cells
        results['n_samples'] = len(test_cells)
    else:
        # 随机采样
        if len(grid_map.free_cells) < n_samples:
            n_samples = len(grid_map.free_cells)
        results['n_samples'] = n_samples
        sampled_indices = np.random.choice(len(grid_map.free_cells), size=n_samples, replace=False)
        test_cells = [grid_map.free_cells[idx] for idx in sampled_indices]

    for cell in test_cells:
        i, j = cell

        # cell -> world
        x, y = mapping.cell_to_world(i, j, grid_map.origin, grid_map.resolution)

        # world -> cell
        i2, j2 = mapping.world_to_cell(x, y, grid_map.origin, grid_map.resolution)

        # 验证
        if i2 == i and j2 == j:
            results['pass_count'] += 1
        else:
            results['fail_count'] += 1
            results['failures'].append({
                'original_cell': [int(i), int(j)],
                'world': [float(x), float(y)],
                'recovered_cell': [int(i2), int(j2)],
            })

    return results


def test_world_to_cell_to_world(grid_map, n_samples=50, seed=42):
    """
    测试 world -> cell -> world 往返转换。

    Args:
        grid_map: GridMap 对象
        n_samples: 采样数量
        seed: 随机种子

    Returns:
        测试结果字典
    """
    np.random.seed(seed + 1)  # 不同的种子

    results = {
        'test_name': 'world_to_cell_to_world',
        'n_samples': n_samples,
        'pass_count': 0,
        'fail_count': 0,
        'max_error': 0.0,
        'mean_error': 0.0,
        'out_of_bounds_count': 0,
        'failures': [],
    }

    # 计算地图的世界坐标边界
    x_min = grid_map.origin[0]
    y_min = grid_map.origin[1]
    x_max = x_min + grid_map.width * grid_map.resolution
    y_max = y_min + grid_map.height * grid_map.resolution

    errors = []

    for _ in range(n_samples):
        # 随机生成世界坐标（在地图边界内）
        x = np.random.uniform(x_min, x_max)
        y = np.random.uniform(y_min, y_max)

        # world -> cell
        i, j = mapping.world_to_cell(x, y, grid_map.origin, grid_map.resolution)

        # 检查是否越界
        if not mapping.in_bounds(i, j, grid_map.height, grid_map.width):
            results['out_of_bounds_count'] += 1
            results['failures'].append({
                'original_world': [float(x), float(y)],
                'cell': [int(i), int(j)],
                'error': 'out_of_bounds',
            })
            continue

        # cell -> world（返回格子中心）
        x2, y2 = mapping.cell_to_world(i, j, grid_map.origin, grid_map.resolution)

        # 验证：world2 应该在该 cell 的范围内
        x_min_cell, y_min_cell, x_max_cell, y_max_cell = mapping.get_cell_bounds(
            i, j, grid_map.origin, grid_map.resolution
        )

        # 检查原始点是否在 cell 边界内
        if x_min_cell <= x <= x_max_cell and y_min_cell <= y <= y_max_cell:
            # 计算误差（原始点到格子中心的距离）
            error = np.sqrt((x - x2)**2 + (y - y2)**2)
            errors.append(error)

            # 误差应该小于半个格子的对角线长度
            max_allowed_error = grid_map.resolution * np.sqrt(2) / 2
            if error <= max_allowed_error:
                results['pass_count'] += 1
            else:
                results['fail_count'] += 1
                results['failures'].append({
                    'original_world': [float(x), float(y)],
                    'cell': [int(i), int(j)],
                    'recovered_world': [float(x2), float(y2)],
                    'error': float(error),
                    'max_allowed_error': float(max_allowed_error),
                })
        else:
            # 原始点不在 cell 边界内（不应该发生）
            results['fail_count'] += 1
            results['failures'].append({
                'original_world': [float(x), float(y)],
                'cell': [int(i), int(j)],
                'cell_bounds': [float(x_min_cell), float(y_min_cell),
                               float(x_max_cell), float(y_max_cell)],
                'error': 'point_outside_cell_bounds',
            })

    # 统计误差
    if errors:
        results['max_error'] = float(np.max(errors))
        results['mean_error'] = float(np.mean(errors))
    else:
        results['max_error'] = 0.0
        results['mean_error'] = 0.0

    return results


def generate_report(grid_map, test1_results, test2_results, output_path):
    """
    生成测试报告。

    Args:
        grid_map: GridMap 对象
        test1_results: 测试1结果
        test2_results: 测试2结果
        output_path: 输出路径
    """
    report = {
        'map_info': {
            'width': grid_map.width,
            'height': grid_map.height,
            'resolution': grid_map.resolution,
            'origin': list(grid_map.origin),
            'free_cells': len(grid_map.free_cells),
        },
        'test_1_cell_to_world_to_cell': {
            'test_all': test1_results['test_all'],
            'n_samples': test1_results['n_samples'],
            'pass_count': test1_results['pass_count'],
            'fail_count': test1_results['fail_count'],
            'pass_rate': round(test1_results['pass_count'] / test1_results['n_samples'] * 100, 2),
            'failures': test1_results['failures'][:5],  # 只保留前5个失败
        },
        'test_2_world_to_cell_to_world': {
            'n_samples': test2_results['n_samples'],
            'pass_count': test2_results['pass_count'],
            'fail_count': test2_results['fail_count'],
            'pass_rate': round(test2_results['pass_count'] / test2_results['n_samples'] * 100, 2),
            'max_error': test2_results['max_error'],
            'mean_error': test2_results['mean_error'],
            'out_of_bounds_count': test2_results['out_of_bounds_count'],
            'failures': test2_results['failures'][:5],  # 只保留前5个失败
        },
        'overall': {
            'all_tests_passed': (test1_results['fail_count'] == 0 and
                                test2_results['fail_count'] == 0 and
                                test2_results['out_of_bounds_count'] == 0),
            'total_samples': test1_results['n_samples'] + test2_results['n_samples'],
            'total_pass': test1_results['pass_count'] + test2_results['pass_count'],
            'total_fail': test1_results['fail_count'] + test2_results['fail_count'],
        }
    }

    # 保存报告
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='坐标映射单元测试')
    parser.add_argument('map_path', type=str, help='地图文件路径')
    parser.add_argument('--n-samples', type=int, default=50,
                        help='每个测试的采样数量（默认：50）')
    parser.add_argument('--test-all', action='store_true',
                        help='测试所有 free cells（忽略 --n-samples）')
    parser.add_argument('--seed', type=int, default=42,
                        help='随机种子（默认：42）')
    parser.add_argument('--output', type=str, default=None,
                        help='输出报告路径（默认：与地图同目录）')
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
        output_path = map_path.parent / f"{map_path.stem}_mapping_report.json"

    # 加载地图
    print(f"加载地图: {map_path}")
    try:
        grid_map = auto_load_map(str(map_path))
    except Exception as e:
        print(f"错误：无法加载地图: {e}")
        sys.exit(1)

    print(f"地图加载成功:")
    print(f"  - 尺寸: {grid_map.width}x{grid_map.height}")
    print(f"  - 分辨率: {grid_map.resolution}")
    print(f"  - 原点: {grid_map.origin}")
    print(f"  - 自由格子: {len(grid_map.free_cells)}")

    # 测试1: cell -> world -> cell
    if args.test_all:
        print(f"\n测试 1: cell -> world -> cell（所有 {len(grid_map.free_cells)} 个 free cells）")
    else:
        print(f"\n测试 1: cell -> world -> cell（{args.n_samples} 个样本）")
    test1_results = test_cell_to_world_to_cell(grid_map, args.n_samples, args.seed, args.test_all)
    print(f"  - 通过: {test1_results['pass_count']}/{test1_results['n_samples']}")
    print(f"  - 失败: {test1_results['fail_count']}/{test1_results['n_samples']}")

    # 测试2: world -> cell -> world
    print(f"\n测试 2: world -> cell -> world（{args.n_samples} 个样本）")
    test2_results = test_world_to_cell_to_world(grid_map, args.n_samples, args.seed)
    print(f"  - 通过: {test2_results['pass_count']}/{test2_results['n_samples']}")
    print(f"  - 失败: {test2_results['fail_count']}/{test2_results['n_samples']}")
    print(f"  - 最大误差: {test2_results['max_error']:.6f} 米")
    print(f"  - 平均误差: {test2_results['mean_error']:.6f} 米")
    print(f"  - 越界次数: {test2_results['out_of_bounds_count']}")

    # 生成报告
    print(f"\n生成测试报告: {output_path}")
    report = generate_report(grid_map, test1_results, test2_results, output_path)

    # 输出总结
    print("\n" + "=" * 60)
    if report['overall']['all_tests_passed']:
        print("✓ 所有测试通过！")
    else:
        print("✗ 部分测试失败")
    print("=" * 60)

    print(f"\n总结:")
    print(f"  - 总样本数: {report['overall']['total_samples']}")
    print(f"  - 通过: {report['overall']['total_pass']}")
    print(f"  - 失败: {report['overall']['total_fail']}")
    print(f"  - 测试报告: {output_path}")

    # 如果有失败，返回非零退出码
    if not report['overall']['all_tests_passed']:
        sys.exit(1)


if __name__ == "__main__":
    main()
