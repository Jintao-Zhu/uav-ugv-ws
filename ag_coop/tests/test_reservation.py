"""
Day6 Step 1 验收测试：Reservation Table

验证：
1. vertex 冲突：同一 cell 同一 t 被占用 → is_vertex_free=False
2. edge swap：已预留 (b→a,t) 时，(a→b,t) 必须判 invalid
3. WAIT：u→u 不产生 swap 冲突，且能正常 reserve
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.mapf.reservation import ReservationTable


def test_vertex_conflict():
    """测试 1: vertex 冲突检测"""
    print("\n" + "=" * 80)
    print("测试 1: Vertex 冲突检测")
    print("=" * 80)

    table = ReservationTable()

    # Agent 0 预留 (1, 1) 在 t=5
    cell = (1, 1)
    t = 5
    agent_0 = 0

    table.reserve_vertex(cell, t, agent_0)
    print(f"  Agent {agent_0} 预留了 {cell} 在 t={t}")

    # 检查 Agent 0 自己能否使用（应该可以）
    is_free_for_0 = table.is_vertex_free(cell, t, agent_0)
    assert is_free_for_0, "Agent 0 应该能使用自己预留的顶点"
    print(f"  ✓ Agent {agent_0} 可以使用自己预留的顶点")

    # 检查 Agent 1 能否使用（应该不可以）
    agent_1 = 1
    is_free_for_1 = table.is_vertex_free(cell, t, agent_1)
    assert not is_free_for_1, "Agent 1 不应该能使用 Agent 0 预留的顶点"
    print(f"  ✓ Agent {agent_1} 不能使用 Agent {agent_0} 预留的顶点")

    # 检查其他时刻是否空闲（应该空闲）
    is_free_at_other_time = table.is_vertex_free(cell, t + 1, agent_1)
    assert is_free_at_other_time, "其他时刻应该空闲"
    print(f"  ✓ 同一位置在其他时刻 (t={t+1}) 空闲")

    # 检查其他位置是否空闲（应该空闲）
    other_cell = (2, 2)
    is_free_at_other_cell = table.is_vertex_free(other_cell, t, agent_1)
    assert is_free_at_other_cell, "其他位置应该空闲"
    print(f"  ✓ 其他位置 {other_cell} 在同一时刻空闲")

    print("\n✓ Vertex 冲突检测测试通过")
    return True


def test_edge_swap_conflict():
    """测试 2: Edge swap 冲突检测"""
    print("\n" + "=" * 80)
    print("测试 2: Edge Swap 冲突检测")
    print("=" * 80)

    table = ReservationTable()

    # Agent 0 预留 (b → a, t)
    a = (1, 1)
    b = (2, 2)
    t = 5
    agent_0 = 0
    agent_1 = 1

    table.reserve_edge(b, a, t, agent_0)
    print(f"  Agent {agent_0} 预留了边 {b} → {a} 在 t={t}")

    # 检查 Agent 1 能否使用 (a → b, t)（应该不可以，会发生 swap）
    is_edge_free = table.is_edge_free(a, b, t, agent_1)
    assert not is_edge_free, "反向边应该被检测为冲突（swap）"
    print(f"  ✓ Agent {agent_1} 不能使用反向边 {a} → {b}（会发生 swap）")

    # 检查 Agent 0 自己能否使用反向边（应该可以，因为是自己）
    is_edge_free_for_0 = table.is_edge_free(a, b, t, agent_0)
    assert is_edge_free_for_0, "Agent 0 应该能使用（虽然不合理，但不冲突）"
    print(f"  ✓ Agent {agent_0} 可以使用反向边（自己的预留）")

    # 检查其他时刻的边是否空闲（应该空闲）
    is_edge_free_at_other_time = table.is_edge_free(a, b, t + 1, agent_1)
    assert is_edge_free_at_other_time, "其他时刻的边应该空闲"
    print(f"  ✓ 同一边在其他时刻 (t={t+1}) 空闲")

    # 检查其他边是否空闲（应该空闲）
    c = (3, 3)
    is_other_edge_free = table.is_edge_free(a, c, t, agent_1)
    assert is_other_edge_free, "其他边应该空闲"
    print(f"  ✓ 其他边 {a} → {c} 空闲")

    print("\n✓ Edge Swap 冲突检测测试通过")
    return True


def test_wait_no_swap():
    """测试 3: WAIT 不产生 swap 冲突"""
    print("\n" + "=" * 80)
    print("测试 3: WAIT 不产生 Swap 冲突")
    print("=" * 80)

    table = ReservationTable()

    # Agent 0 在 (1, 1) WAIT（u → u）
    u = (1, 1)
    t = 5
    agent_0 = 0
    agent_1 = 1

    # WAIT 是 u → u，不应该预留边（或者预留但不影响其他边）
    table.reserve_move(u, u, t, agent_0)
    print(f"  Agent {agent_0} 在 {u} WAIT (t={t} → t={t+1})")

    # 检查 Agent 1 能否从其他位置移动到 u（应该不可以，因为 u 在 t+1 被占用）
    v = (2, 2)
    is_move_valid = table.is_move_valid(v, u, t, agent_1)
    assert not is_move_valid, "其他 agent 不能移动到被 WAIT 占用的位置"
    print(f"  ✓ Agent {agent_1} 不能从 {v} 移动到 {u}（目标被占用）")

    # 检查 Agent 1 能否从 u 移动到其他位置（应该可以，WAIT 不占用边）
    # 但是 u 在 t 时刻没有被 Agent 1 占用，所以这个测试不太合理
    # 改为：检查 WAIT 是否正确预留了顶点
    is_vertex_free = table.is_vertex_free(u, t + 1, agent_1)
    assert not is_vertex_free, "WAIT 应该预留目标顶点"
    print(f"  ✓ WAIT 正确预留了顶点 {u} 在 t={t+1}")

    # 检查 WAIT 是否产生 swap 冲突
    # Agent 1 尝试从 v 移动到 u，Agent 0 在 u WAIT
    # 这不是 swap（因为 Agent 0 没有离开 u），但 u 在 t+1 被占用
    # 所以 is_move_valid 应该返回 False（已在上面测试）

    # 新建一个场景：Agent 0 WAIT，Agent 1 尝试经过
    table2 = ReservationTable()
    table2.reserve_move(u, u, t, agent_0)

    # Agent 1 尝试从 v 移动到 w（不经过 u）
    w = (3, 3)
    is_move_valid_bypass = table2.is_move_valid(v, w, t, agent_1)
    assert is_move_valid_bypass, "Agent 1 应该能绕过 WAIT 的位置"
    print(f"  ✓ Agent {agent_1} 可以绕过 WAIT 的位置（{v} → {w}）")

    # 检查 WAIT 不会阻止其他边
    # Agent 1 从 v 移动到 w，不应该与 Agent 0 的 WAIT 冲突
    table2.reserve_move(v, w, t, agent_1)
    print(f"  ✓ Agent {agent_1} 成功预留了 {v} → {w}")

    print("\n✓ WAIT 不产生 Swap 冲突测试通过")
    return True


def test_move_validation():
    """测试 4: 移动有效性检查（综合测试）"""
    print("\n" + "=" * 80)
    print("测试 4: 移动有效性检查")
    print("=" * 80)

    table = ReservationTable()

    # 场景：Agent 0 从 (1,1) 移动到 (2,2)
    u = (1, 1)
    v = (2, 2)
    t = 5
    agent_0 = 0
    agent_1 = 1

    # 检查移动是否有效（应该有效）
    is_valid = table.is_move_valid(u, v, t, agent_0)
    assert is_valid, "空表中的移动应该有效"
    print(f"  ✓ Agent {agent_0} 可以从 {u} 移动到 {v} (t={t})")

    # 预留这次移动
    table.reserve_move(u, v, t, agent_0)
    print(f"  Agent {agent_0} 预留了移动 {u} → {v}")

    # 检查 Agent 1 能否在同一时刻移动到 v（应该不可以）
    w = (3, 3)
    is_valid_conflict = table.is_move_valid(w, v, t, agent_1)
    assert not is_valid_conflict, "Agent 1 不能移动到被占用的位置"
    print(f"  ✓ Agent {agent_1} 不能从 {w} 移动到 {v}（目标被占用）")

    # 检查 Agent 1 能否进行 swap（应该不可以）
    is_valid_swap = table.is_move_valid(v, u, t, agent_1)
    assert not is_valid_swap, "Agent 1 不能进行 swap"
    print(f"  ✓ Agent {agent_1} 不能从 {v} 移动到 {u}（会发生 swap）")

    # 检查 Agent 1 能否在其他时刻移动到 v（应该可以）
    is_valid_other_time = table.is_move_valid(w, v, t + 1, agent_1)
    assert is_valid_other_time, "Agent 1 应该能在其他时刻移动到 v"
    print(f"  ✓ Agent {agent_1} 可以在其他时刻 (t={t+1}) 移动到 {v}")

    print("\n✓ 移动有效性检查测试通过")
    return True


def test_path_reservation():
    """测试 5: 路径预留"""
    print("\n" + "=" * 80)
    print("测试 5: 路径预留")
    print("=" * 80)

    table = ReservationTable()

    # Agent 0 的路径
    path = [(1, 1), (2, 1), (3, 1), (3, 2), (3, 3)]
    agent_0 = 0

    table.reserve_path(path, agent_0)
    print(f"  Agent {agent_0} 预留了路径: {path}")

    # 检查路径上的每个顶点是否被正确预留
    for t, cell in enumerate(path):
        is_free_for_0 = table.is_vertex_free(cell, t, agent_0)
        assert is_free_for_0, f"Agent 0 应该能使用自己路径上的顶点 {cell} at t={t}"

        is_free_for_1 = table.is_vertex_free(cell, t, agent_id=1)
        assert not is_free_for_1, f"Agent 1 不应该能使用 Agent 0 路径上的顶点 {cell} at t={t}"

    print(f"  ✓ 路径上的所有顶点都被正确预留")

    # 检查路径上的边是否被正确预留
    for t in range(len(path) - 1):
        u = path[t]
        v = path[t + 1]

        is_move_valid_for_0 = table.is_move_valid(u, v, t, agent_0)
        assert is_move_valid_for_0, f"Agent 0 应该能使用自己路径上的边 {u} → {v} at t={t}"

        # Agent 1 不能进行 swap
        is_move_valid_for_1 = table.is_move_valid(v, u, t, agent_id=1)
        assert not is_move_valid_for_1, f"Agent 1 不能进行 swap {v} → {u} at t={t}"

    print(f"  ✓ 路径上的所有边都被正确预留")

    print("\n✓ 路径预留测试通过")
    return True


def main():
    """运行所有测试"""
    print("=" * 80)
    print("Day6 Step 1 验收测试：Reservation Table")
    print("=" * 80)

    tests = [
        ("Vertex 冲突检测", test_vertex_conflict),
        ("Edge Swap 冲突检测", test_edge_swap_conflict),
        ("WAIT 不产生 Swap 冲突", test_wait_no_swap),
        ("移动有效性检查", test_move_validation),
        ("路径预留", test_path_reservation),
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
        print("✓ Day6 Step 1 验收通过")
        print("=" * 80)
        print("\n验收标准：")
        print("  ✓ Vertex 冲突：同一 cell 同一 t 被占用 → is_vertex_free=False")
        print("  ✓ Edge Swap：已预留 (b→a,t) 时，(a→b,t) 必须判 invalid")
        print("  ✓ WAIT：u→u 不产生 swap 冲突，且能正常 reserve")
        print("  ✓ 移动有效性检查正确")
        print("  ✓ 路径预留功能正常")
    else:
        print("\n✗ 部分测试失败，请检查")
        sys.exit(1)


if __name__ == "__main__":
    main()
