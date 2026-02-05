"""Run a single episode with seeding and config resolution."""
import argparse
import random
import numpy as np
from pathlib import Path

from agcoop.utils.seeding import seed_everything
from agcoop.utils.io import load_config, save_resolved_config


def generate_initial_positions(n_robots: int, map_size: int = 10):
    """Generate random initial positions for robots."""
    positions = []
    for _ in range(n_robots):
        x = random.randint(0, map_size - 1)
        y = random.randint(0, map_size - 1)
        positions.append((x, y))
    return positions


def generate_task_stream(n_tasks: int, map_size: int = 10):
    """Generate a dummy task stream."""
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

    # Load config
    config = load_config(args.config)

    # Override seed from CLI if provided
    if args.seed is not None:
        config["episode"]["seed"] = args.seed

    # Override output dir if provided
    if args.output_dir is not None:
        config["logging"]["out_dir"] = args.output_dir

    # Set random seeds
    seed = config["episode"]["seed"]
    seed_everything(seed)
    print(f"Using seed: {seed}")

    # Save resolved config for reproducibility
    output_dir = config["logging"]["out_dir"]
    save_resolved_config(config, output_dir)

    # Generate dummy initial positions and task stream
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
