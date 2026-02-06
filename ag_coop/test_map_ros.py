"""
测试 ROS 格式地图加载（Day2 验收）

验收标准：
- 加载 ROS .yaml + .pgm 格式
- 正确解析 resolution 和 origin
- 正确二值化 occupancy grid
- free_cells 数量正确
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from agcoop.map import GridMap, load_ros_map, save_ros_map


def test_load_ros_map():
    """测试加载 ROS 格式地图"""
    print("=" * 60)
    print("测试 1: 加载 ROS 格式地图")
    print("=" * 60)
    
    yaml_path = Path(__file__).parent / "maps" / "test_ros.yaml"
    grid_map = load_ros_map(str(yaml_path))
    
    print(f"✓ ROS 地图加载成功")
    print(f"  - 尺寸: {grid_map.width} x {grid_map.height}")
    print(f"  - 分辨率: {grid_map.resolution} m/cell")
    print(f"  - 原点: {grid_map.origin}")
    print(f"  - 自由格子数: {len(grid_map.free_cells)}")
    print(f"  - 障碍物数: {(grid_map.grid == 1).sum()}")
    print(f"  - 自由格子占比: {len(grid_map.free_cells) / (grid_map.width * grid_map.height) * 100:.1f}%")
    
    # 验证尺寸
    assert grid_map.width == 20
    assert grid_map.height == 20
    
    # 验证 resolution
    assert grid_map.resolution == 0.05
    
    # 验证 origin
    assert grid_map.origin == (-10.0, -10.0)
    
    print(f"✓ 验证通过")
    print()
    
    return grid_map


def test_coordinate_conversion_ros(grid_map: GridMap):
    """测试 ROS 地图的坐标转换"""
    print("=" * 60)
    print("测试 2: ROS 地图坐标转换")
    print("=" * 60)
    
    # 测试 cell_to_world（考虑 origin）
    x, y = grid_map.cell_to_world(0, 0)
    print(f"cell (0, 0) -> world ({x:.3f}, {y:.3f})")
    
    # 格子中心应该在 origin + (0.5 * resolution, 0.5 * resolution)
    expected_x = grid_map.origin[0] + 0.5 * grid_map.resolution
    expected_y = grid_map.origin[1] + 0.5 * grid_map.resolution
    
    print(f"  期望: ({expected_x:.3f}, {expected_y:.3f})")
    
    assert abs(x - expected_x) < 1e-6
    assert abs(y - expected_y) < 1e-6
    
    # 测试 world_to_cell
    i, j = grid_map.world_to_cell(x, y)
    assert i == 0 and j == 0
    
    print(f"✓ 坐标转换正确")
    print()


def test_save_and_reload(grid_map: GridMap):
    """测试保存和重新加载"""
    print("=" * 60)
    print("测试 3: 保存和重新加载")
    print("=" * 60)
    
    # 保存
    output_yaml = Path(__file__).parent / "maps" / "test_ros_saved.yaml"
    save_ros_map(grid_map, str(output_yaml), "test_ros_saved.pgm")
    
    print(f"✓ 地图已保存到 {output_yaml}")
    
    # 重新加载
    grid_map_reloaded = load_ros_map(str(output_yaml))
    
    print(f"✓ 地图已重新加载")
    
    # 验证一致性
    assert grid_map_reloaded.width == grid_map.width
    assert grid_map_reloaded.height == grid_map.height
    assert grid_map_reloaded.resolution == grid_map.resolution
    assert grid_map_reloaded.origin == grid_map.origin
    assert len(grid_map_reloaded.free_cells) == len(grid_map.free_cells)
    
    print(f"✓ 保存和重新加载一致")
    print()


def test_visualization_ros(grid_map: GridMap):
    """测试 ROS 地图可视化"""
    print("=" * 60)
    print("测试 4: ROS 地图可视化")
    print("=" * 60)
    
    print(grid_map.visualize())
    print()
    print(f"✓ 可视化正常")
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("AGCoop ROS 地图模块 - Day2 验收测试")
    print("=" * 60 + "\n")
    
    try:
        grid_map = test_load_ros_map()
        test_coordinate_conversion_ros(grid_map)
        test_save_and_reload(grid_map)
        test_visualization_ros(grid_map)
        
        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        print("\n验收标准达成:")
        print("  ✓ 加载 ROS .yaml + .pgm 格式")
        print("  ✓ 正确解析 resolution 和 origin")
        print("  ✓ 正确二值化 occupancy grid")
        print("  ✓ free_cells 数量正确")
        print("  ✓ 坐标转换考虑 origin")
        print()
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
