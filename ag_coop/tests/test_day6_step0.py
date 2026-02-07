"""
Day6 Step 0 验收测试：MAPF 接口冻结

验证：
1. MAPF 配置可以正确加载
2. plan_mapf() 接口可以正确导入
3. 无循环依赖/路径错误
"""

import sys
from pathlib import Path
import yaml

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_mapf_config_loading():
    """测试 MAPF 配置加载"""
    print("\n" + "=" * 80)
    print("测试 1: MAPF 配置加载")
    print("=" * 80)

    config_path = project_root / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 检查 MAPF 配置字段
    assert 'mapf' in config, "配置文件中缺少 'mapf' 字段"

    mapf_config = config['mapf']
    required_fields = ['enabled', 'H', 'time_budget_ms', 'connectivity', 'priority']

    for field in required_fields:
        assert field in mapf_config, f"MAPF 配置中缺少 '{field}' 字段"
        print(f"  ✓ {field}: {mapf_config[field]}")

    print("\n✓ MAPF 配置加载成功")
    return True


def test_mapf_import():
    """测试 MAPF 模块导入"""
    print("\n" + "=" * 80)
    print("测试 2: MAPF 模块导入")
    print("=" * 80)

    try:
        from agcoop.mapf import MAPFPlanner, MAPFResult
        print("  ✓ 成功导入 MAPFPlanner")
        print("  ✓ 成功导入 MAPFResult")
    except ImportError as e:
        print(f"  ✗ 导入失败: {e}")
        return False

    print("\n✓ MAPF 模块导入成功")
    return True


def test_mapf_interface():
    """测试 MAPF 接口定义"""
    print("\n" + "=" * 80)
    print("测试 3: MAPF 接口定义")
    print("=" * 80)

    from agcoop.mapf import MAPFPlanner, MAPFResult
    from agcoop.map import auto_load_map

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建 MAPF 规划器
    planner = MAPFPlanner(
        grid_map=grid_map,
        connectivity=4,
        time_budget_ms=1000
    )
    print("  ✓ MAPFPlanner 初始化成功")

    # 测试 plan_mapf 接口
    starts = {0: (1, 1), 1: (2, 2)}
    goals = {0: (5, 5), 1: (6, 6)}
    H = 10

    result = planner.plan_mapf(
        starts=starts,
        goals=goals,
        H=H,
        priority_order=[0, 1],
        fixed_reservations=None
    )
    print("  ✓ plan_mapf() 调用成功")

    # 检查返回类型
    assert isinstance(result, MAPFResult), "返回类型不是 MAPFResult"
    print("  ✓ 返回类型正确 (MAPFResult)")

    # 检查返回字段
    assert hasattr(result, 'success'), "MAPFResult 缺少 'success' 字段"
    assert hasattr(result, 'paths'), "MAPFResult 缺少 'paths' 字段"
    assert hasattr(result, 'makespan'), "MAPFResult 缺少 'makespan' 字段"
    assert hasattr(result, 'sum_of_costs'), "MAPFResult 缺少 'sum_of_costs' 字段"
    assert hasattr(result, 'solve_time_ms'), "MAPFResult 缺少 'solve_time_ms' 字段"
    assert hasattr(result, 'num_agents'), "MAPFResult 缺少 'num_agents' 字段"
    print("  ✓ MAPFResult 字段完整")

    print(f"\n  返回结果: {result}")

    print("\n✓ MAPF 接口定义正确")
    return True


def test_mapf_validation():
    """测试 MAPF 解验证功能"""
    print("\n" + "=" * 80)
    print("测试 4: MAPF 解验证")
    print("=" * 80)

    from agcoop.mapf import MAPFPlanner
    from agcoop.map import auto_load_map

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    planner = MAPFPlanner(grid_map=grid_map)

    # 测试无碰撞的路径
    valid_paths = {
        0: [(1, 1), (2, 1), (3, 1)],
        1: [(1, 2), (2, 2), (3, 2)]
    }
    is_valid, error = planner.validate_solution(valid_paths)
    assert is_valid, f"有效路径被判定为无效: {error}"
    print("  ✓ 无碰撞路径验证通过")

    # 测试有 vertex collision 的路径
    collision_paths = {
        0: [(1, 1), (2, 1), (3, 1)],
        1: [(1, 2), (2, 1), (3, 2)]  # t=1 时与 agent 0 碰撞
    }
    is_valid, error = planner.validate_solution(collision_paths)
    assert not is_valid, "有碰撞的路径被判定为有效"
    print(f"  ✓ Vertex collision 检测成功: {error}")

    # 测试有 edge collision 的路径
    swap_paths = {
        0: [(1, 1), (2, 1)],
        1: [(2, 1), (1, 1)]  # 交换位置
    }
    is_valid, error = planner.validate_solution(swap_paths)
    assert not is_valid, "交换位置的路径被判定为有效"
    print(f"  ✓ Edge collision 检测成功: {error}")

    print("\n✓ MAPF 解验证功能正常")
    return True


def main():
    """运行所有测试"""
    print("=" * 80)
    print("Day6 Step 0 验收测试：MAPF 接口冻结")
    print("=" * 80)

    tests = [
        ("MAPF 配置加载", test_mapf_config_loading),
        ("MAPF 模块导入", test_mapf_import),
        ("MAPF 接口定义", test_mapf_interface),
        ("MAPF 解验证", test_mapf_validation),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except Exception as e:
            print(f"\n✗ 测试失败: {name}")
            print(f"  错误: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # 打印总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    for name, success in results:
        status = "✓" if success else "✗"
        print(f"  {status} {name}")

    all_passed = all(success for _, success in results)

    if all_passed:
        print("\n" + "=" * 80)
        print("✓ Day6 Step 0 验收通过")
        print("=" * 80)
        print("\n验收标准：")
        print("  ✓ MAPF 配置字段完整（enabled, H, time_budget_ms, connectivity, priority）")
        print("  ✓ plan_mapf() 接口可以正确导入")
        print("  ✓ 无循环依赖/路径错误")
        print("  ✓ MAPFResult 数据结构完整")
        print("  ✓ 解验证功能正常")
    else:
        print("\n✗ 部分测试失败，请检查")
        sys.exit(1)


if __name__ == "__main__":
    main()
