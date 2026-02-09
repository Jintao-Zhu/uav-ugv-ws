#!/usr/bin/env python3
"""
Day9 Step 1 验证脚本：决策步时机与 action 应用

验收标准：
1. 所有 decision_step=False 的步不应用 action（info["action_applied"]=False）
2. 决策步数量严格等于 steps // K（例如 500 步、K=5 → 100 次决策步）
"""

import sys
from pathlib import Path
import yaml

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv


def test_decision_step_timing(config_path: str, steps: int = 500):
    """
    测试决策步时机

    Args:
        config_path: 配置文件路径
        steps: 运行步数
    """
    print("=" * 70)
    print("Day9 Step 1: 决策步时机验证")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print(f"运行步数: {steps}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 覆盖 horizon_steps
    config['episode']['horizon_steps'] = steps

    # 获取决策周期 K
    K = config['episode'].get('decision_period', 5)
    print(f"决策周期 K = {K}")
    print()

    # 创建环境
    env = AGCoopEnv(
        config,
        output_dir=None,  # 不记录日志
        enable_logging=False,
        method="greedy",
        planner="none"
    )

    # 重置环境
    state = env.reset()

    # 统计变量
    decision_step_count = 0
    action_applied_count = 0
    non_decision_with_action = []  # 记录非决策步但应用了 action 的时刻
    decision_without_action = []   # 记录决策步但未应用 action 的时刻

    print("开始运行...")
    done = False
    step_count = 0

    while not done:
        # 执行一步（不传入 action，测试默认行为）
        state, reward, done, info = env.step()
        step_count += 1

        # 提取决策步信息
        is_decision_step = info.get('decision_step', False)
        action_applied = info.get('action_applied', False)

        # 统计
        if is_decision_step:
            decision_step_count += 1
            if not action_applied:
                decision_without_action.append(step_count - 1)  # t 从 0 开始
        else:
            if action_applied:
                non_decision_with_action.append(step_count - 1)

        if action_applied:
            action_applied_count += 1

        # 每 100 步打印一次进度
        if step_count % 100 == 0:
            print(f"  步数: {step_count}, 决策步: {decision_step_count}, action应用: {action_applied_count}")

    print(f"\n运行完成！总步数: {step_count}")
    print()

    # 验收检查
    print("=" * 70)
    print("验收检查")
    print("=" * 70)

    # 检查 1: 决策步数量
    expected_decision_steps = steps // K
    print(f"\n1. 决策步数量检查:")
    print(f"   期望决策步数: {expected_decision_steps} (steps={steps}, K={K})")
    print(f"   实际决策步数: {decision_step_count}")

    if decision_step_count == expected_decision_steps:
        print("   ✅ 通过：决策步数量正确")
        check1_pass = True
    else:
        print(f"   ❌ 失败：决策步数量不匹配（差异: {decision_step_count - expected_decision_steps}）")
        check1_pass = False

    # 检查 2: 非决策步不应用 action
    print(f"\n2. 非决策步 action 应用检查:")
    print(f"   非决策步但应用了 action 的次数: {len(non_decision_with_action)}")

    if len(non_decision_with_action) == 0:
        print("   ✅ 通过：所有非决策步都未应用 action")
        check2_pass = True
    else:
        print(f"   ❌ 失败：以下非决策步错误地应用了 action:")
        for t in non_decision_with_action[:10]:  # 只显示前 10 个
            print(f"      t={t} (t % K = {t % K})")
        if len(non_decision_with_action) > 10:
            print(f"      ... 还有 {len(non_decision_with_action) - 10} 个")
        check2_pass = False

    # 检查 3: 决策步应该应用 action（对于 greedy 方法）
    print(f"\n3. 决策步 action 应用检查:")
    print(f"   决策步但未应用 action 的次数: {len(decision_without_action)}")

    if len(decision_without_action) == 0:
        print("   ✅ 通过：所有决策步都应用了 action")
        check3_pass = True
    else:
        print(f"   ⚠️  警告：以下决策步未应用 action（可能是没有任务或其他原因）:")
        for t in decision_without_action[:10]:
            print(f"      t={t}")
        if len(decision_without_action) > 10:
            print(f"      ... 还有 {len(decision_without_action) - 10} 个")
        check3_pass = True  # 这不算失败，可能是正常情况

    # 总结
    print()
    print("=" * 70)
    print("验收总结")
    print("=" * 70)

    all_pass = check1_pass and check2_pass and check3_pass

    if all_pass:
        print("✅✅✅ Day9 Step 1 验收通过！✅✅✅")
        print()
        print("关键结果:")
        print(f"  - 决策步数量: {decision_step_count}/{expected_decision_steps} ✓")
        print(f"  - 非决策步不应用 action: {len(non_decision_with_action)} 次违规 ✓")
        print(f"  - action 应用总次数: {action_applied_count}")
        return True
    else:
        print("❌ Day9 Step 1 验收失败")
        print()
        print("失败原因:")
        if not check1_pass:
            print(f"  - 决策步数量不正确")
        if not check2_pass:
            print(f"  - 非决策步错误地应用了 action")
        return False


def main():
    """主函数"""
    # 使用 Day7 baseline 配置
    config_path = "configs/day7_baseline.yaml"

    # 检查配置文件是否存在
    if not Path(config_path).exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    # 运行测试
    success = test_decision_step_timing(config_path, steps=500)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
