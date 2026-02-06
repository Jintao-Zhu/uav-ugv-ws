"""
测试地图模块（Day2 验收）

验收标准：
- 加载 MovingAI .map 格式地图
- 正确计算 free_cells 数量
- 边界检查不崩溃
- 坐标转换正确
- 邻居查询正确
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from agcoop.map import GridMap, load_movingai_map, auto_load_map


def test_load_movingai():
    """测试加载 MovingAI 格式地图"""
    print("=" * 60)
    print("测试 1: 加载 MovingAI 格式地图")
    print("=" * 60)
    
    map_path = Path(__file__).parent / "maps" / "test_small.map"
    grid_map = load_movingai_map(str(map_path))
    
    print(f"✓ 地图加载成功")
    print(f"  - 尺寸: {grid_map.width} x {grid_map.height}")
    print(f"  - 分辨率: {grid_map.resolution} m/cell")
    print(f"  - 自由格子数: {len(grid_map.free_cells)}")
    print(f"  - 障碍物数: {(grid_map.grid == 1).sum()}")
    
    # 验证尺寸
    assert grid_map.width == 10
    assert grid_map.height == 10
    
    # 验证自由格子数（10x10 地图，边界全是障碍物，内部有一些障碍物）
    expected_free = 10 * 10 - (grid_map.grid == 1).sum()
    assert len(grid_map.free_cells) == expected_free
    
    print(f"✓ 验证通过")
    print()
    
    return grid_map


def test_boundary_check(grid_map: GridMap):
    """测试边界检查"""
    print("=" * 60)
    print("测试 2: 边界检查")
    print("=" * 60)
    
    # 测试边界内
    assert grid_map.in_bounds(0, 0) == True
    assert grid_map.in_bounds(5, 5) == True
    assert grid_map.in_bounds(9, 9) == True
    
    # 测试边界外
    assert grid_map.in_bounds(-1, 0) == False
    assert grid_map.in_bounds(0, -1) == False
    assert grid_map.in_bounds(10, 0) == False
    assert grid_map.in_bounds(0, 10) == False
    
    print(f"✓ 边界检查正确")
    
    # 测试 is_free（边界外应该返回 False）
    assert grid_map.is_free(-1, 0) == False
    assert grid_map.is_free(100, 100) == False
    
    # 测试边界上的障碍物
    assert grid_map.is_free(0, 0) == False  # 左上角是障碍物
    
    # 测试内部自由格子
    assert grid_map.is_free(1, 1) == True  # 内部应该是自由的
    
    print(f"✓ is_free 检查正确")
    print()


def test_coordinate_conversion(grid_map: GridMap):
    """测试坐标转换"""
    print("=" * 60)
    print("测试 3: 坐标转换")
    print("=" * 60)
    
    # 测试 cell_to_world
    x, y = grid_map.cell_to_world(0, 0)
    print(f"cell (0, 0) -> world ({x:.2f}, {y:.2f})")
    
    # 格子中心应该在 (0.5 * resolution, 0.5 * resolution)
    expected_x = 0.0 + 0.5 * grid_map.resolution
    expected_y = 0.0 + 0.5 * grid_map.resolution
    assert abs(x - expected_x) < 1e-6
    assert abs(y - expected_y) < 1e-6
    
    # 测试 world_to_cell
    i, j = grid_map.world_to_cell(x, y)
    assert i == 0 and j == 0
    
    print(f"✓ 坐标转换正确")
    print()


def test_neighbors(grid_map: GridMap):
    """测试邻居查询"""
    print("=" * 60)
    print("测试 4: 邻居查询")
    print("=" * 60)
    
    # 找一个内部的自由格子
    test_cell = (1, 1)
    
    # 4-连通
    neighbors_4 = grid_map.get_neighbors(test_cell[0], test_cell[1], connectivity=4)
    print(f"cell {test_cell} 的 4-连通邻居: {len(neighbors_4)} 个")
    
    # 8-连通
    neighbors_8 = grid_map.get_neighbors(test_cell[0], test_cell[1], connectivity=8)
    print(f"cell {test_cell} 的 8-连通邻居: {len(neighbors_8)} 个")
    
    # 8-连通应该 >= 4-连通
    assert len(neighbors_8) >= len(neighbors_4)
    
    # 所有邻居都应该是自由格子
    for ni, nj in neighbors_4:
        assert grid_map.is_free(ni, nj)
    
    for ni, nj in neighbors_8:
        assert grid_map.is_free(ni, nj)
    
    print(f"✓ 邻居查询正确")
    print()


def test_visualization(grid_map: GridMap):
    """测试可视化"""
    print("=" * 60)
    print("测试 5: 地图可视化")
    print("=" * 60)
    
    print(grid_map.visualize())
    print()
    print(f"✓ 可视化正常")
    print()


def test_auto_load():
    """测试自动加载"""
    print("=" * 60)
    print("测试 6: 自动格式检测")
    print("=" * 60)
    
    map_path = Path(__file__).parent / "maps" / "test_small.map"
    grid_map = auto_load_map(str(map_path))
    
    print(f"✓ 自动加载成功")
    print(f"  - 尺寸: {grid_map.width} x {grid_map.height}")
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("AGCoop 地图模块 - Day2 验收测试")
    print("=" * 60 + "\n")
    
    try:
        grid_map = test_load_movingai()
        test_boundary_check(grid_map)
        test_coordinate_conversion(grid_map)
        test_neighbors(grid_map)
        test_visualization(grid_map)
        test_auto_load()
        
        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        print("\n验收标准达成:")
        print("  ✓ 加载 MovingAI .map 格式地图")
        print("  ✓ 正确计算 free_cells 数量")
        print("  ✓ 边界检查不崩溃")
        print("  ✓ 坐标转换正确")
        print("  ✓ 邻居查询正确")
        print()
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
