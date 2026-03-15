#!/usr/bin/env python3
"""
紧急调试：EDF策略为何失败？

检查智能任务选择的实际行为
"""

import sys
from pathlib import Path
import yaml
import numpy as np

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv
from agcoop.policies.smart_baseline_policies import DynamicHeuristicSmartPolicy


def load_config():
    config_path = project_root / 'configs' / 'curriculum_learning.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    config['episode']['map_path'] = 'maps/map_02.map'
    config['episode']['horizon_steps'] = 100
    return config


def debug_edf_selection():
    print("\n" + "="*70)
    print("紧急调试：EDF任务选择行为分析")
    print("="*70)

    config = load_config()
    env = AGCoopEnv(config, method='rl', planner='PIBT')
    _ = env.reset()

    policy = DynamicHeuristicSmartPolicy(env)

    env.seed = 20000
    obs = env.reset()

    print("\n前10步的任务选择决策：")
    print("-" * 70)

    for step in range(10):
        # 显示tasks_topM
        tasks = obs['tasks_topM']
        print(f"\n步骤 {step}:")
        print(f"  tasks_topM:")
        for i, task in enumerate(tasks):
            available = task[3]
            deadline_norm = task[2]
            print(f"    任务{i}: available={available:.2f}, deadline_norm={deadline_norm:.3f}")

        # 策略决策
        action, _ = policy.predict(obs)
        task_choice = action[0]

        print(f"  → EDF选择: task_choice={task_choice}")

        # 环境交互
        obs, reward, done, info = env.step(action)

        if done:
            break

    print("\n" + "="*70)
    print("分析完成！")
    print("="*70)


if __name__ == "__main__":
    try:
        debug_edf_selection()
    except Exception as e:
        print(f"\n✗ 调试失败: {e}")
        import traceback
        traceback.print_exc()
