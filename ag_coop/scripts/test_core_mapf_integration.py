"""
Day6.5 Step 2: 测试 MAPF Controller 集成到 core.py

验证：
1. enable_mapf=false 时，环境行为与 Day5/Day1 不变（回归保护）
2. enable_mapf=true 时，reset 后 controller 存在且状态正常
"""

import sys
import yaml
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv


def test_mapf_disabled():
    """测试 MAPF 禁用时的回归保护"""
    print("=" * 80)
    print("Test 1: MAPF 禁用（回归保护）")
    print("=" * 80)
    print()

    # 加载配置
    config_path = project_root / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 确保 MAPF 禁用
    config['mapf']['enabled'] = False

    # 创建环境
    env = AGCoopEnv(config)
    print(f"✓ 环境创建成功（MAPF 禁用）")

    # Reset
    state = env.reset()
    print(f"✓ Reset 成功")
    print(f"  - UGV 数量: {len(state.ugv_positions)}")
    print(f"  - UGV 位置: {state.ugv_positions}")
    print()

    # 验证 MAPF controller 不存在
    assert env.ugv_controller is None, "MAPF 禁用时 controller 应该是 None"
    assert env.mapf_wrapper is None, "MAPF 禁用时 wrapper 应该是 None"
    print(f"✓ MAPF controller 不存在（符合预期）")
    print()

    # 运行几步，确保环境正常工作
    for i in range(10):
        state, reward, done, info = env.step()

    print(f"✓ 运行 10 步，环境正常工作")
    print(f"  - 当前时间步: {state.t}")
    print(f"  - UGV 位置: {state.ugv_positions}")
    print()

    env.close()


def test_mapf_enabled():
    """测试 MAPF 启用时的初始化"""
    print("=" * 80)
    print("Test 2: MAPF 启用")
    print("=" * 80)
    print()

    # 加载配置
    config_path = project_root / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 启用 MAPF
    config['mapf']['enabled'] = True
    config['mapf']['H'] = 40
    config['mapf']['time_budget_ms'] = 300

    # 创建环境
    env = AGCoopEnv(config)
    print(f"✓ 环境创建成功（MAPF 启用）")

    # Reset
    state = env.reset()
    print(f"✓ Reset 成功")
    print(f"  - UGV 数量: {len(state.ugv_positions)}")
    print(f"  - UGV 位置: {state.ugv_positions}")
    print()

    # 验证 MAPF controller 存在
    assert env.ugv_controller is not None, "MAPF 启用时 controller 应该存在"
    assert env.mapf_wrapper is not None, "MAPF 启用时 wrapper 应该存在"
    print(f"✓ MAPF controller 存在")
    print()

    # 验证 controller 状态
    assert env.ugv_controller.K == config['episode']['decision_period'], "K 应该等于 decision_period"
    assert env.ugv_controller.H == config['mapf']['H'], "H 应该等于配置值"
    assert env.ugv_controller.budget_ms == config['mapf']['time_budget_ms'], "budget_ms 应该等于配置值"
    print(f"✓ Controller 配置正确")
    print(f"  - K: {env.ugv_controller.K}")
    print(f"  - H: {env.ugv_controller.H}")
    print(f"  - budget_ms: {env.ugv_controller.budget_ms}")
    print()

    # 验证 controller 初始状态（Day6.5 Step 3: 现在会执行初始规划）
    # 如果初始规划成功，path_cache 应该存在
    if env.ugv_controller.path_cache is not None:
        print(f"✓ Controller 初始规划成功，path_cache 已创建")
        assert env.ugv_controller.cache_start_t == 0, "初始规划后 cache_start_t 应该是 0"
    else:
        print(f"⚠ Controller 初始规划失败，进入 fallback")
        assert env.ugv_controller.fallback_wait_remaining > 0, "规划失败应该进入 fallback"

    print(f"  - path_cache: {'存在' if env.ugv_controller.path_cache else 'None'}")
    print(f"  - cache_start_t: {env.ugv_controller.cache_start_t}")
    print(f"  - fallback_wait_remaining: {env.ugv_controller.fallback_wait_remaining}")
    print()

    # 验证统计计数器（初始规划算一次调用）
    assert env.ugv_controller.mapf_calls == 1, "初始规划后 mapf_calls 应该是 1"
    if env.ugv_controller.path_cache is not None:
        assert env.ugv_controller.mapf_success_calls == 1, "初始规划成功后 mapf_success_calls 应该是 1"
    print(f"✓ Controller 统计计数器正确")
    print(f"  - mapf_calls: {env.ugv_controller.mapf_calls}")
    print(f"  - mapf_success_calls: {env.ugv_controller.mapf_success_calls}")
    print(f"  - expanded_nodes_total: {env.ugv_controller.expanded_nodes_total}")
    print()

    # 验证 goals 已设置
    assert env.ugv_controller.current_goals is not None, "current_goals 应该已设置"
    assert len(env.ugv_controller.current_goals) == env.n_ugv, "goals 数量应该等于 UGV 数量"
    print(f"✓ Controller goals 已设置")
    print(f"  - goals: {env.ugv_controller.current_goals}")
    print()

    env.close()


def test_mapf_no_map():
    """测试没有地图时 MAPF 不初始化"""
    print("=" * 80)
    print("Test 3: MAPF 启用但无地图")
    print("=" * 80)
    print()

    # 加载配置
    config_path = project_root / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 启用 MAPF 但不加载地图
    config['mapf']['enabled'] = True
    config['episode']['map_path'] = 'none'

    # 创建环境
    env = AGCoopEnv(config)
    print(f"✓ 环境创建成功（MAPF 启用，无地图）")

    # Reset
    state = env.reset()
    print(f"✓ Reset 成功")
    print()

    # 验证 MAPF controller 不存在（因为没有地图）
    assert env.ugv_controller is None, "无地图时 controller 应该是 None"
    assert env.mapf_wrapper is None, "无地图时 wrapper 应该是 None"
    print(f"✓ MAPF controller 不存在（无地图，符合预期）")
    print()

    env.close()


def main():
    print("Day6.5 Step 2: MAPF Controller 集成测试")
    print()

    try:
        test_mapf_disabled()
        test_mapf_enabled()
        test_mapf_no_map()

        print("=" * 80)
        print("验收结果")
        print("=" * 80)
        print("✓ Test 1: MAPF 禁用（回归保护）")
        print("✓ Test 2: MAPF 启用（controller 正常初始化）")
        print("✓ Test 3: MAPF 启用但无地图（controller 不初始化）")
        print()
        print("✓ Day6.5 Step 2 验收通过")
        print()

    except AssertionError as e:
        print(f"✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
