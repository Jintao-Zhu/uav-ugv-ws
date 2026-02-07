"""
Day6 Step 2 验收测试：Space-Time A*

验证：
1. 无障碍无预留：能在 H 内到达并返回长度 H+1 的 path（到达后 stay）
2. 加 vertex 预留阻塞关键格：A* 能绕行或选择 WAIT
3. 强制 timeout：把 budget 设极小（如 0.1ms），必须返回 timeout=True
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.map import auto_load_map
from agcoop.mapf.reservation import ReservationTable
from agcoop.mapf.astar import SpaceTimeAStar


def test_basic_pathfinding():
    """测试 1: 无障碍无预留的基本路径规划"""
    print("\n" + "=" * 80)
    print("测试 1: 无障碍无预留的基本路径规划")
    print("=" * 80)

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建空的预留表
    reservation_table = ReservationTable()

    # 创建 A* 规划器
    astar = SpaceTimeAStar(grid_map, reservation_table, connectivity=4)

    # 规划路径
    start = (5, 5)
    goal = (10, 10)
    H = 20
    agent_id = 0

    print(f"  起点: {start}")
    print(f"  终点: {goal}")
    print(f"  时间窗 H: {H}")

    path, timeout = astar.search(start, goal, H, agent_id, time_budget_ms=1000)

    # 检查结果
    assert not timeout, "不应该超时"
    assert path is not None, "应该找到路径"
    print(f"  ✓ 找到路径，长度: {len(path)}")

    # 检查路径起点和终点
    assert path[0] == start, f"路径起点应该是 {start}"
    assert path[-1] == goal, f"路径终点应该是 {goal}"
    print(f"  ✓ 路径起点和终点正确")

    # 检查路径长度（应该是 H+1）
    assert len(path) == H + 1, f"路径长度应该是 {H+1}（到达后 stay）"
    print(f"  ✓ 路径长度正确: {len(path)} = H+1")

    # 检查到达目标后是否 stay
    # 找到第一次到达目标的时刻
    first_arrival = None
    for t, cell in enumerate(path):
        if cell == goal:
            first_arrival = t
            break

    assert first_arrival is not None, "应该到达目标"
    print(f"  ✓ 第一次到达目标: t={first_arrival}")

    # 检查之后是否一直 stay
    for t in range(first_arrival, len(path)):
        assert path[t] == goal, f"到达目标后应该 stay，但 t={t} 时位置是 {path[t]}"
    print(f"  ✓ 到达目标后正确 stay")

    # 打印路径前几步
    print(f"  路径前 10 步: {path[:10]}")

    print("\n✓ 无障碍无预留的基本路径规划测试通过")
    return True


def test_pathfinding_with_reservation():
    """测试 2: 带预留约束的路径规划（绕行或 WAIT）"""
    print("\n" + "=" * 80)
    print("测试 2: 带预留约束的路径规划")
    print("=" * 80)

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建预留表
    reservation_table = ReservationTable()

    # Agent 0 的路径（阻塞关键格）
    # 假设 Agent 1 想从 (5, 5) 到 (10, 5)
    # Agent 0 占用了 (7, 5) 在 t=2
    start = (5, 5)
    goal = (10, 5)
    blocked_cell = (7, 5)
    blocked_t = 2
    agent_0 = 0
    agent_1 = 1

    reservation_table.reserve_vertex(blocked_cell, blocked_t, agent_0)
    print(f"  Agent {agent_0} 预留了 {blocked_cell} 在 t={blocked_t}")

    # 创建 A* 规划器
    astar = SpaceTimeAStar(grid_map, reservation_table, connectivity=4)

    # Agent 1 规划路径
    H = 20
    print(f"  Agent {agent_1} 从 {start} 到 {goal}")
    print(f"  时间窗 H: {H}")

    path, timeout = astar.search(start, goal, H, agent_1, time_budget_ms=1000)

    # 检查结果
    assert not timeout, "不应该超时"
    assert path is not None, "应该找到路径（绕行或 WAIT）"
    print(f"  ✓ 找到路径，长度: {len(path)}")

    # 检查路径是否避开了预留的格子
    if blocked_t < len(path):
        assert path[blocked_t] != blocked_cell, f"路径在 t={blocked_t} 不应该经过 {blocked_cell}"
        print(f"  ✓ 路径成功避开了预留的格子")
        print(f"    t={blocked_t} 时位置: {path[blocked_t]} (预留的是 {blocked_cell})")

    # 检查路径起点和终点
    assert path[0] == start, f"路径起点应该是 {start}"
    print(f"  ✓ 路径起点正确")

    # 检查是否最终到达目标
    assert goal in path, f"路径应该到达目标 {goal}"
    print(f"  ✓ 路径到达目标")

    # 打印路径前几步
    print(f"  路径前 10 步: {path[:10]}")

    print("\n✓ 带预留约束的路径规划测试通过")
    return True


def test_timeout():
    """测试 3: 超时处理"""
    print("\n" + "=" * 80)
    print("测试 3: 超时处理")
    print("=" * 80)

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建空的预留表
    reservation_table = ReservationTable()

    # 创建 A* 规划器
    astar = SpaceTimeAStar(grid_map, reservation_table, connectivity=4)

    # 规划一条较长的路径，但给极小的时间预算
    start = (5, 5)
    goal = (50, 50)  # 很远的目标
    H = 100
    agent_id = 0
    time_budget_ms = 0.1  # 极小的时间预算

    print(f"  起点: {start}")
    print(f"  终点: {goal}")
    print(f"  时间窗 H: {H}")
    print(f"  时间预算: {time_budget_ms} ms")

    path, timeout = astar.search(start, goal, H, agent_id, time_budget_ms=time_budget_ms)

    # 检查结果
    assert timeout, "应该超时"
    assert path is None, "超时时应该返回 None"
    print(f"  ✓ 正确检测到超时")

    print("\n✓ 超时处理测试通过")
    return True


def test_wait_action():
    """测试 4: WAIT 动作"""
    print("\n" + "=" * 80)
    print("测试 4: WAIT 动作")
    print("=" * 80)

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建预留表
    reservation_table = ReservationTable()

    # 场景：Agent 1 想从 (5, 5) 到 (7, 5)
    # Agent 0 占用了 (6, 5) 在 t=1 和 t=2
    # Agent 1 需要在 (5, 5) WAIT
    start = (5, 5)
    goal = (7, 5)
    agent_0 = 0
    agent_1 = 1

    # Agent 0 占用中间格子
    reservation_table.reserve_vertex((6, 5), 1, agent_0)
    reservation_table.reserve_vertex((6, 5), 2, agent_0)
    print(f"  Agent {agent_0} 占用了 (6, 5) 在 t=1 和 t=2")

    # 创建 A* 规划器
    astar = SpaceTimeAStar(grid_map, reservation_table, connectivity=4)

    # Agent 1 规划路径
    H = 10
    print(f"  Agent {agent_1} 从 {start} 到 {goal}")

    path, timeout = astar.search(start, goal, H, agent_1, time_budget_ms=1000)

    # 检查结果
    assert not timeout, "不应该超时"
    assert path is not None, "应该找到路径"
    print(f"  ✓ 找到路径，长度: {len(path)}")

    # 检查是否有 WAIT 动作（连续两个时刻在同一位置）
    has_wait = False
    for t in range(len(path) - 1):
        if path[t] == path[t + 1]:
            has_wait = True
            print(f"  ✓ 检测到 WAIT 动作: t={t} 在 {path[t]}")
            break

    # 注意：也可能通过绕行避开，所以 WAIT 不是必须的
    if not has_wait:
        print(f"  ℹ 路径通过绕行避开了阻塞（没有使用 WAIT）")

    # 检查路径是否避开了预留的格子
    if 1 < len(path):
        assert path[1] != (6, 5), "路径在 t=1 不应该经过 (6, 5)"
    if 2 < len(path):
        assert path[2] != (6, 5), "路径在 t=2 不应该经过 (6, 5)"
    print(f"  ✓ 路径成功避开了预留的格子")

    # 打印路径
    print(f"  完整路径: {path}")

    print("\n✓ WAIT 动作测试通过")
    return True


def test_path_validity():
    """测试 5: 路径有效性检查"""
    print("\n" + "=" * 80)
    print("测试 5: 路径有效性检查")
    print("=" * 80)

    # 加载地图
    map_path = project_root / "maps" / "map_01.map"
    grid_map = auto_load_map(str(map_path))

    # 创建空的预留表
    reservation_table = ReservationTable()

    # 创建 A* 规划器
    astar = SpaceTimeAStar(grid_map, reservation_table, connectivity=4)

    # 规划路径
    start = (5, 5)
    goal = (10, 10)
    H = 20
    agent_id = 0

    path, timeout = astar.search(start, goal, H, agent_id, time_budget_ms=1000)

    assert path is not None, "应该找到路径"
    print(f"  找到路径，长度: {len(path)}")

    # 检查路径的每一步是否有效
    for t in range(len(path) - 1):
        current = path[t]
        next_cell = path[t + 1]

        # 检查是否是有效移动（WAIT 或相邻）
        if current == next_cell:
            # WAIT 动作
            print(f"  t={t}: WAIT 在 {current}")
        else:
            # 移动动作，检查是否相邻
            dx = abs(current[0] - next_cell[0])
            dy = abs(current[1] - next_cell[1])

            if astar.connectivity == 4:
                assert (dx == 1 and dy == 0) or (dx == 0 and dy == 1), \
                    f"4-邻接下，{current} 和 {next_cell} 不相邻"
            else:
                assert dx <= 1 and dy <= 1, \
                    f"8-邻接下，{current} 和 {next_cell} 不相邻"

        # 检查是否在地图内
        assert 0 <= next_cell[0] < grid_map.width, "x 坐标越界"
        assert 0 <= next_cell[1] < grid_map.height, "y 坐标越界"

        # 检查是否是障碍
        assert grid_map.is_free(next_cell[0], next_cell[1]), \
            f"{next_cell} 是障碍"

    print(f"  ✓ 路径的每一步都有效")

    print("\n✓ 路径有效性检查测试通过")
    return True


def main():
    """运行所有测试"""
    print("=" * 80)
    print("Day6 Step 2 验收测试：Space-Time A*")
    print("=" * 80)

    tests = [
        ("无障碍无预留的基本路径规划", test_basic_pathfinding),
        ("带预留约束的路径规划", test_pathfinding_with_reservation),
        ("超时处理", test_timeout),
        ("WAIT 动作", test_wait_action),
        ("路径有效性检查", test_path_validity),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success))
        except AssertionError as e:
            print(f"\n✗ 测试失败: {name}")
            print(f"  断言错误: {e}")
            results.append((name, False))
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
        print("✓ Day6 Step 2 验收通过")
        print("=" * 80)
        print("\n验收标准：")
        print("  ✓ 无障碍无预留：能在 H 内到达并返回长度 H+1 的 path")
        print("  ✓ 加 vertex 预留阻塞关键格：A* 能绕行或选择 WAIT")
        print("  ✓ 强制 timeout：把 budget 设极小，必须返回 timeout=True")
        print("  ✓ WAIT 动作正常工作")
        print("  ✓ 路径有效性检查通过")
    else:
        print("\n✗ 部分测试失败，请检查")
        sys.exit(1)


if __name__ == "__main__":
    main()
