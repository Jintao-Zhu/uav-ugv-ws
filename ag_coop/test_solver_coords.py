#!/usr/bin/env python3
"""
测试外部求解器坐标转换

验证：
- to_solver_coords() 和 from_solver_coords() 互为逆操作
- 角落格子的转换正确
- format_solver_instance() 和 parse_solver_solution() 正确
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.map import mapping


def test_solver_coords_conversion():
    """测试求解器坐标转换"""
    print("=" * 60)
    print("测试：求解器坐标转换")
    print("=" * 60)

    height = 10
    width = 10

    # 测试角落格子
    test_cases = [
        ((0, 0), "左下角"),
        ((0, width-1), "右下角"),
        ((height-1, 0), "左上角"),
        ((height-1, width-1), "右上角"),
        ((5, 5), "中心"),
    ]

    print(f"\n地图尺寸: {height}x{width}")
    print(f"内部坐标约定: i=row(y, 0=底部), j=col(x, 0=左侧)")
    print(f"求解器坐标约定: x=col, y=row(0=顶部)\n")

    for (i, j), desc in test_cases:
        # 内部 -> 求解器
        solver_x, solver_y = mapping.to_solver_coords(i, j, height)

        # 求解器 -> 内部
        i2, j2 = mapping.from_solver_coords(solver_x, solver_y, height)

        # 验证往返转换
        success = (i2 == i and j2 == j)
        status = "✓" if success else "✗"

        print(f"{status} {desc:10s}: 内部({i:2d},{j:2d}) <-> 求解器({solver_x:2d},{solver_y:2d}) -> 内部({i2:2d},{j2:2d})")

        if not success:
            raise AssertionError(f"往返转换失败: ({i},{j}) -> ({solver_x},{solver_y}) -> ({i2},{j2})")

    print("\n✓ 所有转换测试通过")


def test_format_solver_instance():
    """测试求解器实例格式化"""
    print("\n" + "=" * 60)
    print("测试：求解器实例格式化")
    print("=" * 60)

    height = 10

    # 内部坐标（左下角 -> 右上角）
    start_cells = [(0, 0), (0, 5)]
    goal_cells = [(9, 9), (9, 5)]

    print(f"\n起点（内部坐标）: {start_cells}")
    print(f"终点（内部坐标）: {goal_cells}")

    # 格式化为求解器实例
    instance = mapping.format_solver_instance(start_cells, goal_cells, height)

    print(f"\n求解器实例:")
    for i, agent in enumerate(instance['agents']):
        print(f"  Agent {i}: start={agent['start']}, goal={agent['goal']}")

    # 验证
    expected_starts = [(0, 9), (5, 9)]  # 求解器坐标
    expected_goals = [(9, 0), (5, 0)]

    for i, agent in enumerate(instance['agents']):
        assert agent['start'] == list(expected_starts[i]), f"Agent {i} start 错误"
        assert agent['goal'] == list(expected_goals[i]), f"Agent {i} goal 错误"

    print("\n✓ 实例格式化正确")


def test_parse_solver_solution():
    """测试求解器解析"""
    print("\n" + "=" * 60)
    print("测试：求解器解析")
    print("=" * 60)

    height = 10

    # 求解器返回的路径（求解器坐标）
    solver_solution = [
        [(0, 9), (1, 9), (2, 9)],  # Agent 0: 从左下角向右
        [(5, 9), (5, 8), (5, 7)],  # Agent 1: 从中间向上
    ]

    print(f"\n求解器解（求解器坐标）:")
    for i, path in enumerate(solver_solution):
        print(f"  Agent {i}: {path}")

    # 解析为内部坐标
    internal_solution = mapping.parse_solver_solution(solver_solution, height)

    print(f"\n内部坐标解:")
    for i, path in enumerate(internal_solution):
        print(f"  Agent {i}: {path}")

    # 验证
    expected_internal = [
        [(0, 0), (0, 1), (0, 2)],  # Agent 0: 从左下角向右
        [(0, 5), (1, 5), (2, 5)],  # Agent 1: 从底部向上
    ]

    for i, path in enumerate(internal_solution):
        assert path == expected_internal[i], f"Agent {i} 路径解析错误"

    print("\n✓ 解析正确")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("外部求解器坐标转换测试")
    print("=" * 60 + "\n")

    try:
        test_solver_coords_conversion()
        test_format_solver_instance()
        test_parse_solver_solution()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        print("\n验收标准达成:")
        print("  ✓ to_solver_coords() 和 from_solver_coords() 互为逆操作")
        print("  ✓ 角落格子转换正确")
        print("  ✓ format_solver_instance() 正确")
        print("  ✓ parse_solver_solution() 正确")
        print()

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
