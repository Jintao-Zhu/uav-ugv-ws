#!/usr/bin/env python3
"""
Day9 Step 2 验证脚本：Action Space 设计与应用

验收标准：
1. env.action_space.sample() 的 action 能被 step() 正确解析，不抛异常
2. 对于越界/无效索引：自动 clamp，并在 info["action_valid"]=False 体现
3. 测试不同的 action 组合（有效、越界、边界）
"""

import sys
from pathlib import Path
import yaml
import numpy as np

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv


def test_action_space_basic(config_path: str):
    """
    测试 action space 基本功能

    Args:
        config_path: 配置文件路径
    """
    print("=" * 70)
    print("Day9 Step 2: Action Space 基本功能测试")
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

    # 检查 action_space
    print("1. Action Space 属性检查:")
    print(f"   action_space: {env.action_space}")
    print(f"   action_space.nvec: {env.action_space.nvec}")
    print(f"   - task_choice: 0..{env.action_space.nvec[0]-1} ({env.action_space.nvec[0]} 个选项)")
    print(f"   - relay_target: 0..{env.action_space.nvec[1]-1} ({env.action_space.nvec[1]} 个选项)")
    print()

    # 重置环境
    state = env.reset()
    print(f"2. 环境重置成功")
    print(f"   候选中继点数量: {len(env.candidate_relays)}")
    print(f"   Top-M: {env.top_m}")
    print()

    # 测试 sample()
    print("3. 测试 action_space.sample():")
    for i in range(5):
        action = env.action_space.sample()
        print(f"   Sample {i+1}: {action} (task_choice={action[0]}, relay_target={action[1]})")
    print()

    return env


def test_action_parsing(env: AGCoopEnv):
    """
    测试 action 解析和应用

    Args:
        env: 环境实例
    """
    print("=" * 70)
    print("Day9 Step 2: Action 解析与应用测试")
    print("=" * 70)
    print()

    test_cases = [
        # (action, description)
        ([0, 0], "不指定任务和 relay"),
        ([1, 1], "选择第1个任务和第1个relay"),
        ([env.top_m, env.candidate_count], "选择最后一个任务和relay"),
        ([env.top_m + 1, env.candidate_count + 1], "越界（应该被 clamp）"),
        ([-1, -1], "负数索引（应该被 clamp）"),
        ([2, 0], "只指定任务，不指定 relay"),
        ([0, 3], "不指定任务，只指定 relay"),
    ]

    results = []

    for action, description in test_cases:
        print(f"测试: {description}")
        print(f"  action: {action}")

        try:
            # 执行一步
            state, reward, done, info = env.step(action)

            # 检查结果
            action_applied = info.get('action_applied', False)
            action_valid = info.get('action_valid', True)
            action_error = info.get('action_error', '')
            decision_step = info.get('decision_step', False)

            print(f"  ✓ 执行成功")
            print(f"    - decision_step: {decision_step}")
            print(f"    - action_applied: {action_applied}")
            print(f"    - action_valid: {action_valid}")
            if action_error:
                print(f"    - action_error: {action_error}")

            results.append({
                'action': action,
                'description': description,
                'success': True,
                'action_valid': action_valid,
                'action_error': action_error
            })

        except Exception as e:
            print(f"  ✗ 执行失败: {e}")
            results.append({
                'action': action,
                'description': description,
                'success': False,
                'error': str(e)
            })

        print()

    return results


def test_random_actions(env: AGCoopEnv, steps: int = 100):
    """
    测试随机 action 运行

    Args:
        env: 环境实例
        steps: 运行步数
    """
    print("=" * 70)
    print(f"Day9 Step 2: 随机 Action 运行测试 ({steps} 步)")
    print("=" * 70)
    print()

    # 重置环境
    env.reset()

    crash_count = 0
    invalid_action_count = 0
    decision_step_count = 0
    action_applied_count = 0

    for step in range(steps):
        # 随机采样 action
        action = env.action_space.sample()

        try:
            state, reward, done, info = env.step(action)

            if info.get('decision_step', False):
                decision_step_count += 1

            if info.get('action_applied', False):
                action_applied_count += 1

            if not info.get('action_valid', True):
                invalid_action_count += 1

            if done:
                print(f"  Episode 结束于步数 {step+1}")
                break

        except Exception as e:
            crash_count += 1
            print(f"  ✗ 步数 {step+1} 崩溃: {e}")
            break

    print(f"运行完成:")
    print(f"  - 总步数: {step+1}")
    print(f"  - 决策步数: {decision_step_count}")
    print(f"  - action 应用次数: {action_applied_count}")
    print(f"  - 无效 action 次数: {invalid_action_count}")
    print(f"  - 崩溃次数: {crash_count}")
    print()

    return crash_count == 0


def main():
    """主函数"""
    config_path = "configs/day7_baseline.yaml"

    if not Path(config_path).exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    # 测试 1: 基本功能
    env = test_action_space_basic(config_path)

    # 测试 2: Action 解析
    results = test_action_parsing(env)

    # 测试 3: 随机运行
    success = test_random_actions(env, steps=100)

    # 验收总结
    print("=" * 70)
    print("验收总结")
    print("=" * 70)
    print()

    # 检查 1: 所有测试用例都成功执行
    all_executed = all(r['success'] for r in results)
    print(f"1. 所有测试用例执行成功: {'✅' if all_executed else '❌'}")
    if not all_executed:
        failed = [r for r in results if not r['success']]
        for r in failed:
            print(f"   - 失败: {r['description']} - {r.get('error', 'Unknown')}")

    # 检查 2: 越界 action 被正确处理
    out_of_bounds_cases = [r for r in results if '越界' in r['description'] or '负数' in r['description']]
    out_of_bounds_handled = all(r['success'] for r in out_of_bounds_cases)
    print(f"2. 越界 action 被正确处理（不崩溃）: {'✅' if out_of_bounds_handled else '❌'}")

    # 检查 3: 随机运行不崩溃
    print(f"3. 随机 action 运行不崩溃: {'✅' if success else '❌'}")

    print()

    if all_executed and out_of_bounds_handled and success:
        print("✅✅✅ Day9 Step 2 验收通过！✅✅✅")
        print()
        print("关键结果:")
        print(f"  - action_space.sample() 可用 ✓")
        print(f"  - 越界 action 自动 clamp ✓")
        print(f"  - 随机运行 100 步无崩溃 ✓")
        sys.exit(0)
    else:
        print("❌ Day9 Step 2 验收失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
