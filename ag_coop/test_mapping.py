"""
测试坐标映射（Day2 验收）

验收标准：
- 任意 free cell → world center → world_to_cell 应回到原 cell（100%）
- 边界检查正确
- clip_to_bounds 正确
- world_to_cell_checked 越界抛出异常
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from agcoop.map import GridMap, load_movingai_map, mapping


def test_roundtrip_conversion():
    """测试往返转换（cell -> world -> cell）"""
    print("=" * 60)
    print("测试 1: 往返转换（100% 一致性）")
    print("=" * 60)
    
    # 加载地图
    map_path = Path(__file__).parent / "maps" / "map_01.map"
    grid_map = load_movingai_map(str(map_path))
    
    print(f"地图: {grid_map.width}x{grid_map.height}")
    print(f"自由格子数: {len(grid_map.free_cells)}")
    
    # 测试所有自由格子
    success_count = 0
    fail_count = 0
    
    for i, j in grid_map.free_cells:
        # cell -> world
        x, y = grid_map.cell_to_world(i, j)
        
        # world -> cell
        i_back, j_back = grid_map.world_to_cell(x, y)
        
        # 验证
        if i_back == i and j_back == j:
            success_count += 1
        else:
            fail_count += 1
            if fail_count <= 5:  # 只打印前 5 个失败
                print(f"  ✗ cell ({i}, {j}) -> world ({x:.3f}, {y:.3f}) -> cell ({i_back}, {j_back})")
    
    print(f"\n往返转换结果:")
    print(f"  - 成功: {success_count}/{len(grid_map.free_cells)} ({success_count/len(grid_map.free_cells)*100:.1f}%)")
    print(f"  - 失败: {fail_count}/{len(grid_map.free_cells)}")
    
    assert fail_count == 0, f"往返转换失败 {fail_count} 次"
    print(f"✓ 100% 往返转换一致")
    print()


def test_boundary_functions():
    """测试边界相关函数"""
    print("=" * 60)
    print("测试 2: 边界函数")
    print("=" * 60)
    
    height, width = 20, 20
    
    # 测试 in_bounds
    assert mapping.in_bounds(0, 0, height, width) == True
    assert mapping.in_bounds(19, 19, height, width) == True
    assert mapping.in_bounds(-1, 0, height, width) == False
    assert mapping.in_bounds(0, -1, height, width) == False
    assert mapping.in_bounds(20, 0, height, width) == False
    assert mapping.in_bounds(0, 20, height, width) == False
    
    print(f"✓ in_bounds 正确")
    
    # 测试 clip_to_bounds
    assert mapping.clip_to_bounds(-1, -1, height, width) == (0, 0)
    assert mapping.clip_to_bounds(25, 25, height, width) == (19, 19)
    assert mapping.clip_to_bounds(10, 10, height, width) == (10, 10)
    
    print(f"✓ clip_to_bounds 正确")
    print()


def test_world_to_cell_checked():
    """测试带检查的世界坐标转换"""
    print("=" * 60)
    print("测试 3: world_to_cell_checked（越界检查）")
    print("=" * 60)
    
    origin = (0.0, 0.0)
    resolution = 0.2
    height, width = 20, 20
    
    # 测试正常情况
    try:
        i, j = mapping.world_to_cell_checked(1.0, 1.0, origin, resolution, height, width)
        print(f"✓ 正常坐标 (1.0, 1.0) -> cell ({i}, {j})")
    except ValueError as e:
        print(f"✗ 不应该抛出异常: {e}")
        raise
    
    # 测试越界情况
    try:
        i, j = mapping.world_to_cell_checked(100.0, 100.0, origin, resolution, height, width)
        print(f"✗ 越界坐标应该抛出异常，但返回了 ({i}, {j})")
        raise AssertionError("应该抛出 ValueError")
    except ValueError as e:
        print(f"✓ 越界坐标正确抛出异常: {e}")
    
    print()


def test_get_cell_bounds():
    """测试获取格子边界"""
    print("=" * 60)
    print("测试 4: get_cell_bounds")
    print("=" * 60)
    
    origin = (0.0, 0.0)
    resolution = 0.2
    
    # 测试 cell (0, 0)
    x_min, y_min, x_max, y_max = mapping.get_cell_bounds(0, 0, origin, resolution)
    print(f"cell (0, 0) 边界: ({x_min:.2f}, {y_min:.2f}) -> ({x_max:.2f}, {y_max:.2f})")
    
    assert x_min == 0.0
    assert y_min == 0.0
    assert x_max == 0.2
    assert y_max == 0.2
    
    # 测试 cell (5, 10)
    x_min, y_min, x_max, y_max = mapping.get_cell_bounds(5, 10, origin, resolution)
    print(f"cell (5, 10) 边界: ({x_min:.2f}, {y_min:.2f}) -> ({x_max:.2f}, {y_max:.2f})")
    
    assert abs(x_min - 2.0) < 1e-6
    assert abs(y_min - 1.0) < 1e-6
    assert abs(x_max - 2.2) < 1e-6
    assert abs(y_max - 1.2) < 1e-6
    
    print(f"✓ get_cell_bounds 正确")
    print()


def test_with_different_origins():
    """测试不同 origin 的情况"""
    print("=" * 60)
    print("测试 5: 不同 origin")
    print("=" * 60)
    
    # 测试负 origin（ROS 常见情况）
    origin = (-10.0, -10.0)
    resolution = 0.05
    
    # cell (0, 0) 的中心应该在 (-10.0 + 0.025, -10.0 + 0.025)
    x, y = mapping.cell_to_world(0, 0, origin, resolution)
    print(f"origin={origin}, cell (0, 0) -> world ({x:.3f}, {y:.3f})")
    
    expected_x = origin[0] + 0.5 * resolution
    expected_y = origin[1] + 0.5 * resolution
    
    assert abs(x - expected_x) < 1e-6
    assert abs(y - expected_y) < 1e-6
    
    # 往返转换
    i, j = mapping.world_to_cell(x, y, origin, resolution)
    assert i == 0 and j == 0
    
    print(f"✓ 负 origin 处理正确")
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("AGCoop 坐标映射 - Day2 验收测试")
    print("=" * 60 + "\n")
    
    try:
        test_roundtrip_conversion()
        test_boundary_functions()
        test_world_to_cell_checked()
        test_get_cell_bounds()
        test_with_different_origins()
        
        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        print("\n验收标准达成:")
        print("  ✓ 任意 free cell → world center → world_to_cell 回到原 cell（100%）")
        print("  ✓ 边界检查正确（in_bounds, clip_to_bounds）")
        print("  ✓ world_to_cell_checked 越界正确抛出异常")
        print("  ✓ get_cell_bounds 正确")
        print("  ✓ 不同 origin 处理正确")
        print()
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
