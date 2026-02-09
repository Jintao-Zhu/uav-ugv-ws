#!/usr/bin/env python3
"""
Day9 Step 1 扩展验证：测试不同的 K 值

验证决策步逻辑在不同决策周期下都正确工作
"""

import sys
from pathlib import Path
import yaml

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv


def test_with_K(config_path: str, K: int, steps: int = 500):
    """
    测试特定 K 值下的决策步时机

    Args:
        config_path: 配置文件路径
        K: 决策周期
        steps: 运行步数

    Returns:
        是否通过验证
    """
    print(f"\n{'='*70}")
    print(f"测试 K={K}, steps={steps}")
    print(f"{'='*70}")

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 覆盖参数
    config['episode']['horizon_steps'] = steps
    config['episode']['decision_period'] = K

    # 创建环境
    env = AGCoopEnv(
        config,
        output_dir=None,
        enable_logging=False,
        method="greedy",
        planner="none"
    )

    # 重置环境
    state = env.reset()

    # 统计变量
    decision_step_count = 0
    action_applied_count = 0
    non_decision_with_action = []

    # 运行
    done = False
    step_count = 0

    while not done:
        state, reward, done, info = env.step()
        step_count += 1

        is_decision_step = info.get('decision_step', False)
        action_applied = info.get('action_applied', False)

        if is_decision_step:
            decision_step_count += 1
        if action_applied:
            action_applied_count += 1
        if not is_decision_step and action_applied:
            non_decision_with_action.append(step_count - 1)

    # 验证
    expected_decision_steps = steps // K

    print(f"期望决策步数: {expected_decision_steps}")
    print(f"实际决策步数: {decision_step_count}")
    print(f"非决策步违规: {len(non_decision_with_action)}")

    check1 = (decision_step_count == expected_decision_steps)
    check2 = (len(non_decision_with_action) == 0)

    if check1 and check2:
        print(f"✅ K={K} 测试通过")
        return True
    else:
        print(f"❌ K={K} 测试失败")
        if not check1:
            print(f"   - 决策步数量错误: {decision_step_count} != {expected_decision_steps}")
        if not check2:
            print(f"   - 非决策步违规: {len(non_decision_with_action)} 次")
        return False


def main():
    """主函数"""
    config_path = "configs/day7_baseline.yaml"

    if not Path(config_path).exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    print("=" * 70)
    print("Day9 Step 1 扩展验证：多个 K 值测试")
    print("=" * 70)

    # 测试不同的 K 值
    test_cases = [
        (3, 300),   # K=3, 300步 → 100 决策步
        (5, 500),   # K=5, 500步 → 100 决策步
        (8, 400),   # K=8, 400步 → 50 决策步
        (10, 500),  # K=10, 500步 → 50 决策步
    ]

    results = []
    for K, steps in test_cases:
        success = test_with_K(config_path, K, steps)
        results.append((K, steps, success))

    # 总结
    print("\n" + "=" * 70)
    print("测试总结")
    print("=" * 70)

    all_pass = all(success for _, _, success in results)

    for K, steps, success in results:
        status = "✅" if success else "❌"
        print(f"{status} K={K}, steps={steps}: {'通过' if success else '失败'}")

    print()
    if all_pass:
        print("✅✅✅ 所有测试通过！✅✅✅")
        sys.exit(0)
    else:
        print("❌ 部分测试失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
