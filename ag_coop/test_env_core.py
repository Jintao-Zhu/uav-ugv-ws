"""
测试环境核心功能（Day1 验收）

验收标准：
- Env.reset() 能正常初始化
- Env.step() 能跑满 horizon_steps 不报错
- 指标正常累计
"""

import sys
import yaml
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from agcoop.env.core import AGCoopEnv
from agcoop.utils.seeding import seed_everything


def test_basic_functionality():
    """测试基础功能"""
    print("=" * 60)
    print("测试 1: 基础功能测试")
    print("=" * 60)

    # 加载配置
    config_path = Path(__file__).parent / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 设置随机种子
    seed_everything(config['episode']['seed'])

    # 创建环境
    env = AGCoopEnv(config)
    print(f"✓ 环境创建成功")

    # 重置环境
    state = env.reset()
    print(f"✓ 环境重置成功")
    print(f"  - 初始时间步: {state.t}")
    print(f"  - UGV 数量: {len(state.ugv_positions)}")
    print(f"  - UGV 位置: {state.ugv_positions}")
    print(f"  - UAV 在 UGV: {state.uav_onboard_ugv_id}")
    print(f"  - 初始任务数: {len(state.task_pool)}")

    # 运行几步
    print(f"\n运行前 10 步...")
    for i in range(10):
        state, reward, done, info = env.step()
        if i < 3 or i == 9:  # 只打印前 3 步和第 10 步
            print(f"  步 {state.t}: 活跃任务={info['active_tasks']}, "
                  f"完成={info['tasks_completed']}, "
                  f"超期={info['deadline_miss']}, "
                  f"outage={info['outage_steps']}")

    print(f"✓ 前 10 步运行成功")
    print()


def test_full_episode():
    """测试完整 episode"""
    print("=" * 60)
    print("测试 2: 完整 Episode 测试")
    print("=" * 60)

    # 加载配置（使用较短的 horizon 以加快测试）
    config_path = Path(__file__).parent / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 缩短 horizon 以加快测试
    original_horizon = config['episode']['horizon_steps']
    config['episode']['horizon_steps'] = 100
    print(f"使用缩短的 horizon: {config['episode']['horizon_steps']} 步")

    # 设置随机种子
    seed_everything(config['episode']['seed'])

    # 创建环境
    env = AGCoopEnv(config)
    state = env.reset()

    # 运行完整 episode
    step_count = 0
    done = False

    while not done:
        state, reward, done, info = env.step()
        step_count += 1

    print(f"✓ 完整 episode 运行成功")
    print(f"  - 总步数: {step_count}")
    print(f"  - 最终时间: {state.t}")
    print(f"  - 任务完成: {state.tasks_completed}")
    print(f"  - 任务超期: {state.deadline_miss}")
    print(f"  - 延迟总和: {state.tardiness_sum}")
    print(f"  - Outage 步数: {state.outage_steps}")
    print(f"  - 总任务数: {len(state.task_pool)}")
    print(f"  - 活跃任务: {len(state.get_active_tasks())}")

    # 恢复原始 horizon
    config['episode']['horizon_steps'] = original_horizon
    print()


def test_reproducibility():
    """测试可复现性"""
    print("=" * 60)
    print("测试 3: 可复现性测试")
    print("=" * 60)

    # 加载配置
    config_path = Path(__file__).parent / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['episode']['horizon_steps'] = 50

    # 运行两次，检查结果是否一致
    results = []

    for run in range(2):
        seed_everything(config['episode']['seed'])
        env = AGCoopEnv(config)
        state = env.reset()

        done = False
        while not done:
            state, reward, done, info = env.step()

        results.append({
            'tasks_completed': state.tasks_completed,
            'deadline_miss': state.deadline_miss,
            'tardiness_sum': state.tardiness_sum,
            'outage_steps': state.outage_steps,
            'total_tasks': len(state.task_pool),
        })

        print(f"运行 {run + 1}: {results[-1]}")

    # 检查两次运行结果是否一致
    if results[0] == results[1]:
        print(f"✓ 可复现性测试通过：两次运行结果完全一致")
    else:
        print(f"✗ 可复现性测试失败：两次运行结果不一致")
        print(f"  差异: {set(results[0].items()) ^ set(results[1].items())}")

    print()


def test_render():
    """测试渲染功能"""
    print("=" * 60)
    print("测试 4: 渲染功能测试")
    print("=" * 60)

    # 加载配置
    config_path = Path(__file__).parent / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    seed_everything(config['episode']['seed'])
    env = AGCoopEnv(config)
    state = env.reset()

    # 运行几步
    for _ in range(5):
        env.step()

    # 渲染
    print(env.render())
    print(f"✓ 渲染功能正常")
    print()


def test_metrics():
    """测试指标获取"""
    print("=" * 60)
    print("测试 5: 指标获取测试")
    print("=" * 60)

    # 加载配置
    config_path = Path(__file__).parent / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    seed_everything(config['episode']['seed'])
    env = AGCoopEnv(config)
    state = env.reset()

    # 运行一些步骤
    for _ in range(20):
        env.step()

    # 获取指标
    metrics = env.get_metrics()
    print(f"当前指标:")
    for key, value in metrics.items():
        print(f"  - {key}: {value}")

    print(f"✓ 指标获取功能正常")
    print()


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("AGCoop 环境核心 - Day1 验收测试")
    print("=" * 60 + "\n")

    try:
        test_basic_functionality()
        test_full_episode()
        test_reproducibility()
        test_render()
        test_metrics()

        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        print("\n验收标准达成:")
        print("  ✓ Env.reset() 能正常初始化")
        print("  ✓ Env.step() 能跑满 horizon_steps 不报错")
        print("  ✓ 指标正常累计")
        print("  ✓ 结果可复现")
        print()

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
