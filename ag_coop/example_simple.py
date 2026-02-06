"""
简单示例：运行一个完整的 episode

演示如何使用 AGCoopEnv 运行一个完整的仿真。
"""

import yaml
from pathlib import Path
from agcoop import AGCoopEnv, seed_everything


def main():
    print("=" * 60)
    print("AGCoop 环境 - 简单示例")
    print("=" * 60)
    print()

    # 1. 加载配置
    config_path = Path(__file__).parent / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    print(f"配置加载成功:")
    print(f"  - Horizon: {config['episode']['horizon_steps']} 步")
    print(f"  - UGV 数量: {config['robots']['n_ugv']}")
    print(f"  - UAV 数量: {config['robots']['n_uav']}")
    print(f"  - 任务到达率: {config['tasks']['arrival_rate']}")
    print(f"  - 随机种子: {config['episode']['seed']}")
    print()

    # 2. 设置随机种子（保证可复现）
    seed_everything(config['episode']['seed'])

    # 3. 创建环境
    env = AGCoopEnv(config)
    print("环境创建成功")
    print()

    # 4. 重置环境
    state = env.reset()
    print("环境已重置")
    print(f"  - 初始 UGV 位置: {state.ugv_positions}")
    print(f"  - UAV 在 UGV {state.uav_onboard_ugv_id} 上")
    print()

    # 5. 运行 episode
    print("开始运行 episode...")
    print()

    done = False
    step_count = 0

    while not done:
        # 执行一步
        state, reward, done, info = env.step()
        step_count += 1

        # 每 100 步打印一次状态
        if step_count % 100 == 0:
            print(f"步 {state.t}:")
            print(f"  - 活跃任务: {info['active_tasks']}")
            print(f"  - 完成任务: {info['tasks_completed']}")
            print(f"  - 超期任务: {info['deadline_miss']}")
            print(f"  - Outage 步数: {info['outage_steps']}")
            print()

    # 6. 打印最终结果
    print("=" * 60)
    print("Episode 完成！")
    print("=" * 60)
    print()

    metrics = env.get_metrics()
    print("最终指标:")
    print(f"  - 总步数: {state.t}")
    print(f"  - 总任务数: {metrics['total_tasks']}")
    print(f"  - 完成任务: {metrics['tasks_completed']}")
    print(f"  - 活跃任务: {metrics['active_tasks']}")
    print(f"  - 超期任务: {metrics['deadline_miss']}")
    print(f"  - 延迟总和: {metrics['tardiness_sum']}")
    print(f"  - Outage 步数: {metrics['outage_steps']}")
    print()

    # 7. 渲染最终状态
    print("最终状态:")
    print(env.render())
    print()

    print("=" * 60)
    print("示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
