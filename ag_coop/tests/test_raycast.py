#!/usr/bin/env python3
"""
Raycast 模块单元测试

测试内容：
1. bresenham_cells() 基本功能
2. count_blocked_cells() 无障碍情况
3. count_blocked_cells() 有障碍情况
4. 对称性：count(a, b) == count(b, a)
"""

import sys
from pathlib import Path
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.comm import raycast
from agcoop.map import GridMap


def test_bresenham_horizontal():
    """测试水平线"""
    cells = raycast.bresenham_cells(0, 0, 0, 3)
    expected = [(0, 0), (0, 1), (0, 2), (0, 3)]
    assert cells == expected, f"Expected {expected}, got {cells}"
    print("✓ 水平线测试通过")


def test_bresenham_vertical():
    """测试垂直线"""
    cells = raycast.bresenham_cells(0, 0, 3, 0)
    expected = [(0, 0), (1, 0), (2, 0), (3, 0)]
    assert cells == expected, f"Expected {expected}, got {cells}"
    print("✓ 垂直线测试通过")


def test_bresenham_diagonal():
    """测试对角线"""
    cells = raycast.bresenham_cells(0, 0, 2, 2)
    expected = [(0, 0), (1, 1), (2, 2)]
    assert cells == expected, f"Expected {expected}, got {cells}"
    print("✓ 对角线测试通过")


def test_bresenham_includes_endpoints():
    """测试端点包含"""
    cells = raycast.bresenham_cells(1, 1, 1, 1)
    assert len(cells) == 1, "单点应该返回 1 个格子"
    assert cells[0] == (1, 1), "单点应该是起点本身"
    print("✓ 端点包含测试通过")


def test_count_blocked_no_obstacles():
    """测试无障碍直线"""
    # 创建一个简单的地图（全部自由）
    grid = np.zeros((5, 5), dtype=int)
    grid_map = GridMap(width=5, height=5, grid=grid, resolution=0.2)

    # 测试水平线
    blocked = raycast.count_blocked_cells(grid_map, (0, 0), (0, 4))
    assert blocked == 0, f"无障碍直线应该返回 0，得到 {blocked}"
    print("✓ 无障碍直线测试通过")


def test_count_blocked_with_obstacles():
    """测试有障碍的情况"""
    # 创建地图，中间有障碍
    grid = np.zeros((5, 5), dtype=int)
    grid[0, 2] = 1  # 在 (0, 2) 放置障碍
    grid_map = GridMap(width=5, height=5, grid=grid, resolution=0.2)

    # 测试穿过障碍的直线
    blocked = raycast.count_blocked_cells(grid_map, (0, 0), (0, 4))
    assert blocked >= 1, f"有障碍的直线应该返回 >= 1，得到 {blocked}"
    print(f"✓ 有障碍测试通过（blocked={blocked}）")


def test_count_blocked_multiple_obstacles():
    """测试多个障碍"""
    # 创建地图，多个障碍
    grid = np.zeros((5, 5), dtype=int)
    grid[0, 1] = 1
    grid[0, 2] = 1
    grid[0, 3] = 1
    grid_map = GridMap(width=5, height=5, grid=grid, resolution=0.2)

    # 测试穿过多个障碍的直线
    blocked = raycast.count_blocked_cells(grid_map, (0, 0), (0, 4))
    assert blocked == 3, f"应该有 3 个障碍，得到 {blocked}"
    print(f"✓ 多障碍测试通过（blocked={blocked}）")


def test_symmetry():
    """测试对称性：count(a, b) == count(b, a)"""
    # 创建地图
    grid = np.zeros((10, 10), dtype=int)
    grid[2, 2] = 1
    grid[3, 3] = 1
    grid[5, 5] = 1
    grid_map = GridMap(width=10, height=10, grid=grid, resolution=0.2)

    # 测试多对点
    test_pairs = [
        ((0, 0), (9, 9)),
        ((0, 0), (0, 9)),
        ((0, 0), (9, 0)),
        ((1, 1), (8, 8)),
        ((2, 3), (7, 6)),
    ]

    for cell_a, cell_b in test_pairs:
        count_ab = raycast.count_blocked_cells(grid_map, cell_a, cell_b)
        count_ba = raycast.count_blocked_cells(grid_map, cell_b, cell_a)
        assert count_ab == count_ba, (
            f"对称性失败：count({cell_a}, {cell_b})={count_ab}, "
            f"count({cell_b}, {cell_a})={count_ba}"
        )

    print("✓ 对称性测试通过（5 对点）")


def test_endpoints_not_counted():
    """测试端点不被统计"""
    # 创建地图，端点是障碍
    grid = np.zeros((5, 5), dtype=int)
    grid[0, 0] = 1  # 起点是障碍
    grid[0, 4] = 1  # 终点是障碍
    grid_map = GridMap(width=5, height=5, grid=grid, resolution=0.2)

    # 端点不应该被统计
    blocked = raycast.count_blocked_cells(grid_map, (0, 0), (0, 4))
    assert blocked == 0, f"端点不应该被统计，得到 {blocked}"
    print("✓ 端点不统计测试通过")


def test_has_line_of_sight():
    """测试 has_line_of_sight() 函数"""
    # 创建地图
    grid = np.zeros((5, 5), dtype=int)
    grid[2, 2] = 1
    grid_map = GridMap(width=5, height=5, grid=grid, resolution=0.2)

    # 无障碍视线
    assert raycast.has_line_of_sight(grid_map, (0, 0), (0, 4)) == True
    assert raycast.has_line_of_sight(grid_map, (0, 0), (4, 0)) == True

    # 有障碍视线（穿过 (2, 2)）
    assert raycast.has_line_of_sight(grid_map, (0, 0), (4, 4)) == False

    print("✓ has_line_of_sight() 测试通过")


def test_compute_los_distance():
    """测试距离计算"""
    grid = np.zeros((5, 5), dtype=int)
    grid_map = GridMap(width=5, height=5, grid=grid, resolution=0.2)

    # 测试水平距离
    dist = raycast.compute_los_distance(grid_map, (0, 0), (0, 5))
    expected = 5 * 0.2  # 5 格 * 0.2 米/格 = 1.0 米
    assert abs(dist - expected) < 1e-6, f"Expected {expected}, got {dist}"

    # 测试对角距离
    dist = raycast.compute_los_distance(grid_map, (0, 0), (3, 4))
    expected = np.sqrt(3**2 + 4**2) * 0.2  # 5 格 * 0.2 = 1.0 米
    assert abs(dist - expected) < 1e-6, f"Expected {expected}, got {dist}"

    print("✓ compute_los_distance() 测试通过")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("Raycast 模块单元测试")
    print("=" * 60 + "\n")

    try:
        # Bresenham 算法测试
        print("测试 bresenham_cells():")
        test_bresenham_horizontal()
        test_bresenham_vertical()
        test_bresenham_diagonal()
        test_bresenham_includes_endpoints()

        print("\n测试 count_blocked_cells():")
        test_count_blocked_no_obstacles()
        test_count_blocked_with_obstacles()
        test_count_blocked_multiple_obstacles()
        test_endpoints_not_counted()

        print("\n测试对称性:")
        test_symmetry()

        print("\n测试辅助函数:")
        test_has_line_of_sight()
        test_compute_los_distance()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)

        print("\n验收标准达成:")
        print("  ✓ 无障碍直线：blocked=0")
        print("  ✓ 中间放一个障碍：blocked>=1")
        print("  ✓ 对称性：count(a,b)==count(b,a)")
        print("  ✓ 端点不被统计")
        print()

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
