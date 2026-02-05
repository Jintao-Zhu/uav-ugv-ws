"""运行单个 episode，支持随机种子和配置解析。"""
import argparse
import random
import numpy as np
from pathlib import Path

from agcoop.utils.seeding import seed_everything
from agcoop.utils.io import load_config, save_resolved_config


def generate_initial_positions(n_robots: int, map_size: int = 10):
    """生成机器人的随机初始位置。"""
    positions = []
    for _ in range(n_robots):
        x = random.randint(0, map_size - 1)
        y = random.randint(0, map_size - 1)
        positions.append((x, y))
    return positions


def generate_task_stream(n_tasks: int, map_size: int = 10):
    """生成 dummy 任务流。"""
    tasks = []
    for i in range(n_tasks):
        start = (random.randint(0, map_size - 1), random.randint(0, map_size - 1))
        goal = (random.randint(0, map_size - 1), random.randint(0, map_size - 1))
        arrival = np.random.poisson(lam=10) + i * 5
        deadline = arrival + random.randint(50, 100)
        tasks.append({
            "id": i,
            "start": start,
            "goal": goal,
            "arrival_step": arrival,
            "deadline": deadline
        })
    return tasks


def main():
    parser = argparse.ArgumentParser(description="Run one episode")
    parser.add_argument("--config", type=str, default="configs/default.yaml",
                        help="Path to config file")
    parser.add_argument("--seed", type=int, default=None,
                        help="Override seed from config")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Override output directory")
    args = parser.parse_args()

    # 加载配置
    config = load_config(args.config)

    # 如果 CLI 提供了 seed，则覆盖配置中的 seed
    if args.seed is not None:
        config["episode"]["seed"] = args.seed

    # 如果提供了输出目录，则覆盖
    if args.output_dir is not None:
        config["logging"]["out_dir"] = args.output_dir

    # 设置随机种子
    seed = config["episode"]["seed"]
    seed_everything(seed)
    print(f"Using seed: {seed}")

    # 保存最终解析后的配置，用于实验复现
    output_dir = config["logging"]["out_dir"]
    save_resolved_config(config, output_dir)

    # 生成 dummy 初始位置和任务流
    n_robots = config["robots"]["n_ugv"] + config["robots"]["n_uav"]
    positions = generate_initial_positions(n_robots)
    print(f"Initial positions: {positions}")

    tasks = generate_task_stream(n_tasks=5)
    print(f"Task stream:")
    for task in tasks:
        print(f"  Task {task['id']}: {task['start']} -> {task['goal']} "
              f"(arrive@{task['arrival_step']}, deadline@{task['deadline']})")


if __name__ == "__main__":
    main()
