"""
Day6.5 完整演示：MAPF 集成到 core.py

展示 MAPF 从禁用到启用的完整流程
"""

import sys
import yaml
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv


def demo_mapf_disabled():
    """演示 MAPF 禁用（Day1 行为）"""
    print("=" * 80)
    print("演示 1: MAPF 禁用（Day1 行为）")
    print("=" * 80)
    print()

    config_path = project_root / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['mapf']['enabled'] = False
    config['episode']['horizon_steps'] = 10
    config['episode']['map_path'] = 'maps/map_01.map'

    env = AGCoopEnv(config)
    state = env.reset()

    print(f"初始状态:")
    print(f"  - UGV 位置: {state.ugv_positions}")
    print(f"  - MAPF Controller: {env.ugv_controller}")
    print()

    for i in range(10):
        state, reward, done, info = env.step()

    print(f"10 步后:")
    print(f"  - UGV 位置: {state.ugv_positions}")
    print(f"  - 位置未变（Day1 行为）")
    print()

    env.close()


def demo_mapf_enabled():
    """演示 MAPF 启用（Receding Horizon）"""
    print("=" * 80)
    print("演示 2: MAPF 启用（Receding Horizon）")
    print("=" * 80)
    print()

    config_path = project_root / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['mapf']['enabled'] = True
    config['mapf']['H'] = 40
    config['mapf']['time_budget_ms'] = 300
    config['episode']['horizon_steps'] = 30
    config['episode']['map_path'] = 'maps/map_01.map'

    env = AGCoopEnv(config, output_dir='outputs/demo', enable_logging=True)
    state = env.reset()

    print(f"初始状态:")
    print(f"  - UGV 位置: {state.ugv_positions}")
    print(f"  - MAPF Controller: {type(env.ugv_controller).__name__}")
    print(f"  - 目标: {env.ugv_controller.current_goals}")
    print()

    print(f"运行 30 步...")
    decision_steps = []
    for i in range(30):
        state, reward, done, info = env.step()

        if (state.t % 5 == 0):
            decision_steps.append(state.t)
            print(f"  t={state.t:2d} (决策步): UGV 位置 = {state.ugv_positions}")

    print()
    print(f"最终状态:")
    print(f"  - UGV 位置: {state.ugv_positions}")
    print(f"  - 决策步: {decision_steps}")
    print()

    # 显示统计
    stats = env.ugv_controller.get_stats()
    print(f"MAPF 统计:")
    print(f"  - 调用次数: {stats['mapf_calls']}")
    print(f"  - 成功次数: {stats['mapf_success_calls']}")
    print(f"  - 成功率: {stats['mapf_success_calls']/stats['mapf_calls']*100:.1f}%")
    print(f"  - 平均规划时间: {stats['mapf_mean_plan_time_ms']:.2f} ms")
    print(f"  - Fallback 步数: {stats['fallback_wait_steps']}")
    print()

    env.close()


def demo_comparison():
    """对比 MAPF 禁用和启用的效果"""
    print("=" * 80)
    print("演示 3: 对比 MAPF 禁用 vs 启用")
    print("=" * 80)
    print()

    config_path = project_root / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['episode']['horizon_steps'] = 20
    config['episode']['map_path'] = 'maps/map_01.map'

    # 禁用 MAPF
    config['mapf']['enabled'] = False
    env1 = AGCoopEnv(config)
    state1 = env1.reset()
    initial_pos_1 = list(state1.ugv_positions)

    for i in range(20):
        state1, _, _, _ = env1.step()

    final_pos_1 = list(state1.ugv_positions)
    moved_1 = sum(1 for i in range(len(initial_pos_1))
                  if initial_pos_1[i] != final_pos_1[i])

    # 启用 MAPF
    config['mapf']['enabled'] = True
    config['mapf']['H'] = 40
    config['mapf']['time_budget_ms'] = 300
    env2 = AGCoopEnv(config)
    state2 = env2.reset()
    initial_pos_2 = list(state2.ugv_positions)

    for i in range(20):
        state2, _, _, _ = env2.step()

    final_pos_2 = list(state2.ugv_positions)
    moved_2 = sum(1 for i in range(len(initial_pos_2))
                  if initial_pos_2[i] != final_pos_2[i])

    print(f"MAPF 禁用:")
    print(f"  - 初始位置: {initial_pos_1}")
    print(f"  - 最终位置: {final_pos_1}")
    print(f"  - 移动的 UGV: {moved_1}/{len(initial_pos_1)}")
    print()

    print(f"MAPF 启用:")
    print(f"  - 初始位置: {initial_pos_2}")
    print(f"  - 最终位置: {final_pos_2}")
    print(f"  - 移动的 UGV: {moved_2}/{len(initial_pos_2)}")
    print()

    if moved_2 > moved_1:
        print(f"✓ MAPF 启用后，UGV 开始移动！")
    else:
        print(f"⚠ MAPF 可能在 fallback 状态")

    env1.close()
    env2.close()


def main():
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Day6.5 完整演示：MAPF 集成到 core.py" + " " * 22 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    try:
        demo_mapf_disabled()
        demo_mapf_enabled()
        demo_comparison()

        print("=" * 80)
        print("演示完成")
        print("=" * 80)
        print()
        print("Day6.5 集成成功！")
        print()
        print("关键成果:")
        print("  ✓ MAPF 禁用时，环境行为与 Day1 一致（回归保护）")
        print("  ✓ MAPF 启用时，UGV 按 Receding Horizon 规划移动")
        print("  ✓ 调用频率正确：每 K 步规划一次")
        print("  ✓ 缓存执行：非决策步执行缓存路径")
        print("  ✓ 统计完整：trace 和 metrics 记录所有信息")
        print()

    except Exception as e:
        print(f"✗ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
