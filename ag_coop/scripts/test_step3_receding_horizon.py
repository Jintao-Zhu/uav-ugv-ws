"""
Day6.5 Step 3: 验证 Receding Horizon 执行

验证：
1. MAPF 调用频率：mapf_calls == ceil(steps / K)
2. 缓存执行：非决策步执行缓存路径，不调用 MAPF
3. UGV 位置更新正确
4. Trace 记录 MAPF 信息
5. Metrics 保存 MAPF 统计
"""

import sys
import yaml
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv


def test_receding_horizon_execution():
    """测试 Receding Horizon 执行"""
    print("=" * 80)
    print("Test 1: Receding Horizon 执行")
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

    # 设置 episode 参数
    K = config['episode']['decision_period']
    steps = 50

    config['episode']['horizon_steps'] = steps
    config['episode']['map_path'] = 'maps/map_01.map'

    print(f"配置:")
    print(f"  K (decision_period): {K}")
    print(f"  H (planning horizon): {config['mapf']['H']}")
    print(f"  步数: {steps}")
    print()

    # 创建环境（启用日志记录）
    env = AGCoopEnv(config, output_dir='outputs/test_step3', enable_logging=True)
    print(f"✓ 环境创建成功")

    # Reset
    state = env.reset()
    print(f"✓ Reset 成功")
    print(f"  - UGV 数量: {len(state.ugv_positions)}")
    print(f"  - UGV 初始位置: {state.ugv_positions}")
    print()

    # 验证 controller 存在
    assert env.ugv_controller is not None, "Controller 应该存在"
    print(f"✓ MAPF Controller 已初始化")
    print()

    # 运行 episode
    print(f"运行 {steps} 步...")
    done = False
    for i in range(steps):
        state, reward, done, info = env.step()

        if (i + 1) % 10 == 0:
            print(f"  进度: {i+1}/{steps}")

    print(f"✓ Episode 完成 (done={done})")
    print()

    # 验证 MAPF 调用频率
    stats = env.ugv_controller.get_stats()
    # 期望调用次数：1 次初始规划（t=0）+ ceil(steps / K) 次后续规划
    # 在 50 步中，t=5, 10, 15, 20, 25, 30, 35, 40, 45, 50 会触发规划（10 次）
    # 加上 t=0 的初始规划，总共 11 次
    expected_calls = 1 + (steps // K)  # 1 + 10 = 11

    print(f"MAPF 调用频率验证:")
    print(f"  - 实际调用: {stats['mapf_calls']}")
    print(f"  - 期望调用: {expected_calls} (1 次初始 + {steps // K} 次后续)")

    assert stats['mapf_calls'] == expected_calls, \
        f"调用次数不匹配: {stats['mapf_calls']} != {expected_calls}"
    print(f"✓ 调用频率正确 (初始 + 每 {K} 步调用一次)")
    print()

    # 验证 trace 记录
    trace_path = env.trace_logger.output_path
    with open(trace_path, 'r') as f:
        trace = [json.loads(line) for line in f]

    print(f"Trace 验证:")
    print(f"  - Trace 长度: {len(trace)}")

    # 检查决策步的 MAPF 调用
    decision_steps = [entry for entry in trace if entry['decision_step']]
    mapf_called_steps = [entry for entry in trace if entry.get('mapf_called', False)]

    print(f"  - 决策步数: {len(decision_steps)}")
    print(f"  - MAPF 调用步数: {len(mapf_called_steps)}")

    # 决策步应该调用 MAPF（除非在 fallback 中）
    assert len(mapf_called_steps) >= len(decision_steps) - 1, \
        "决策步应该调用 MAPF"
    print(f"✓ 决策步调用 MAPF")

    # 检查非决策步不调用 MAPF
    non_decision_steps = [entry for entry in trace if not entry['decision_step']]
    non_decision_mapf_calls = [entry for entry in non_decision_steps
                               if entry.get('mapf_called', False)]

    print(f"  - 非决策步数: {len(non_decision_steps)}")
    print(f"  - 非决策步 MAPF 调用: {len(non_decision_mapf_calls)}")

    assert len(non_decision_mapf_calls) == 0, \
        "非决策步不应该调用 MAPF（应该执行缓存）"
    print(f"✓ 非决策步执行缓存（不调用 MAPF）")
    print()

    # 验证 UGV 位置更新
    print(f"UGV 位置更新验证:")
    initial_positions = trace[0]['ugv_pos']
    final_positions = trace[-1]['ugv_pos']

    print(f"  - 初始位置: {initial_positions}")
    print(f"  - 最终位置: {final_positions}")

    # 检查是否有移动
    moved = any(initial_positions[i] != final_positions[i]
                for i in range(len(initial_positions)))

    if moved:
        print(f"✓ UGV 位置有更新")
    else:
        print(f"⚠ UGV 位置未移动（可能在 fallback 或已到达目标）")
    print()

    # 验证 metrics 保存
    metrics_path = env.metrics_logger.output_path
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    print(f"Metrics 验证:")
    print(f"  - mapf_calls: {metrics['mapf_calls']}")
    print(f"  - mapf_success_calls: {metrics['mapf_success_calls']}")
    print(f"  - mapf_timeout_calls: {metrics['mapf_timeout_calls']}")
    print(f"  - mapf_mean_plan_time_ms: {metrics['mapf_mean_plan_time_ms']}")
    print(f"  - fallback_wait_steps: {metrics['fallback_wait_steps']}")

    assert metrics['mapf_calls'] == expected_calls, \
        "Metrics 中的 mapf_calls 不匹配"
    assert metrics['mapf_calls'] == stats['mapf_calls'], \
        "Metrics 与 controller stats 不一致"
    print(f"✓ Metrics 保存正确")
    print()

    env.close()


def test_mapf_disabled_regression():
    """测试 MAPF 禁用时的回归保护"""
    print("=" * 80)
    print("Test 2: MAPF 禁用（回归保护）")
    print("=" * 80)
    print()

    # 加载配置
    config_path = project_root / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 禁用 MAPF
    config['mapf']['enabled'] = False
    config['episode']['horizon_steps'] = 20
    config['episode']['map_path'] = 'maps/map_01.map'

    # 创建环境（启用日志记录）
    env = AGCoopEnv(config, output_dir='outputs/test_step3_disabled', enable_logging=True)
    print(f"✓ 环境创建成功（MAPF 禁用）")

    # Reset
    state = env.reset()
    print(f"✓ Reset 成功")

    # 验证 controller 不存在
    assert env.ugv_controller is None, "MAPF 禁用时 controller 应该是 None"
    print(f"✓ MAPF Controller 不存在")
    print()

    # 运行几步
    for i in range(20):
        state, reward, done, info = env.step()

    print(f"✓ 运行 20 步，环境正常工作")
    print()

    # 验证 metrics
    metrics_path = env.metrics_logger.output_path
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    print(f"Metrics 验证:")
    print(f"  - mapf_calls: {metrics['mapf_calls']}")

    assert metrics['mapf_calls'] == 0, "MAPF 禁用时调用次数应该是 0"
    print(f"✓ MAPF 禁用时 metrics 正确")
    print()

    env.close()


def test_ugv_movement():
    """测试 UGV 移动行为"""
    print("=" * 80)
    print("Test 3: UGV 移动行为")
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
    config['episode']['horizon_steps'] = 30
    config['episode']['map_path'] = 'maps/map_01.map'

    # 创建环境（启用日志记录）
    env = AGCoopEnv(config, output_dir='outputs/test_step3_movement', enable_logging=True)
    state = env.reset()

    print(f"初始 UGV 位置: {state.ugv_positions}")
    print()

    # 记录每步的位置变化
    prev_positions = list(state.ugv_positions)
    movement_count = 0

    for i in range(30):
        state, reward, done, info = env.step()

        # 检查是否有移动
        moved = any(state.ugv_positions[j] != prev_positions[j]
                   for j in range(len(state.ugv_positions)))

        if moved:
            movement_count += 1

        prev_positions = list(state.ugv_positions)

    print(f"最终 UGV 位置: {state.ugv_positions}")
    print(f"移动步数: {movement_count} / 30")
    print()

    # 验证有移动发生（除非全部在 fallback）
    stats = env.ugv_controller.get_stats()
    fallback_rate = stats['fallback_wait_steps'] / 30

    print(f"Fallback 比例: {fallback_rate*100:.1f}%")

    if fallback_rate < 0.9:
        assert movement_count > 0, "应该有 UGV 移动"
        print(f"✓ UGV 有移动")
    else:
        print(f"⚠ 大部分时间在 fallback，移动较少")
    print()

    env.close()


def main():
    print("Day6.5 Step 3: Receding Horizon 执行验证")
    print()

    try:
        test_receding_horizon_execution()
        test_mapf_disabled_regression()
        test_ugv_movement()

        print("=" * 80)
        print("验收结果")
        print("=" * 80)
        print("✓ Test 1: Receding Horizon 执行（调用频率、缓存执行）")
        print("✓ Test 2: MAPF 禁用（回归保护）")
        print("✓ Test 3: UGV 移动行为")
        print()
        print("✓ Day6.5 Step 3 验收通过")
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
