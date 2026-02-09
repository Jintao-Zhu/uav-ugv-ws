#!/usr/bin/env python3
"""
Day9 Step 2 扩展验证：在决策步测试 action 应用

确保 RL action 在决策步被正确应用
"""

import sys
from pathlib import Path
import yaml
import numpy as np

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv


def test_action_on_decision_steps(config_path: str):
    """
    测试 action 在决策步的应用

    Args:
        config_path: 配置文件路径
    """
    print("=" * 70)
    print("Day9 Step 2 扩展验证：决策步 Action 应用测试")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 创建环境
    env = AGCoopEnv(
        config,
        output_dir=None,
        enable_logging=False,
        method="rl",  # 使用 RL 方法
        planner="none"
    )

    K = config['episode'].get('decision_period', 5)
    print(f"决策周期 K = {K}")
    print()

    # 重置环境
    state = env.reset()

    # 测试用例
    test_cases = [
        ([1, 1], "选择第1个任务和第1个relay"),
        ([2, 3], "选择第2个任务和第3个relay"),
        ([0, 5], "不指定任务，只指定relay"),
        ([3, 0], "只指定任务，不指定relay"),
        ([10, 20], "越界索引（应该被 clamp）"),
    ]

    results = []

    for action, description in test_cases:
        print(f"测试: {description}")
        print(f"  action: {action}")

        # 运行到下一个决策步
        while True:
            state, reward, done, info = env.step(action)

            if info.get('decision_step', False):
                # 到达决策步
                action_applied = info.get('action_applied', False)
                action_valid = info.get('action_valid', True)
                action_error = info.get('action_error', '')

                print(f"  ✓ 决策步 t={info['timestep']}")
                print(f"    - action_applied: {action_applied}")
                print(f"    - action_valid: {action_valid}")
                if action_error:
                    print(f"    - action_error: {action_error}")

                results.append({
                    'action': action,
                    'description': description,
                    'action_applied': action_applied,
                    'action_valid': action_valid,
                    'action_error': action_error
                })
                break

            if done:
                print(f"  ⚠️  Episode 结束，未到达决策步")
                break

        print()

    # 验收检查
    print("=" * 70)
    print("验收检查")
    print("=" * 70)
    print()

    # 检查 1: 所有决策步都应用了 action
    all_applied = all(r['action_applied'] for r in results)
    print(f"1. 所有决策步都应用了 action: {'✅' if all_applied else '❌'}")
    if not all_applied:
        not_applied = [r for r in results if not r['action_applied']]
        for r in not_applied:
            print(f"   - 未应用: {r['description']}")

    # 检查 2: 越界 action 被标记为无效或被 clamp
    out_of_bounds = [r for r in results if '越界' in r['description']]
    if out_of_bounds:
        # 越界 action 应该有 error 信息（被 clamp）
        has_error = any(r['action_error'] for r in out_of_bounds)
        print(f"2. 越界 action 被正确处理: {'✅' if has_error else '⚠️  (无错误信息但未崩溃)'}")

    print()

    if all_applied:
        print("✅✅✅ 决策步 Action 应用测试通过！✅✅✅")
        return True
    else:
        print("❌ 决策步 Action 应用测试失败")
        return False


def main():
    """主函数"""
    config_path = "configs/day7_baseline.yaml"

    if not Path(config_path).exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    success = test_action_on_decision_steps(config_path)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
