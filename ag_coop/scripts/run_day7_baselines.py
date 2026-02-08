#!/usr/bin/env python3
"""
Day7 Baseline 入口脚本

用法：
    # 单次运行
    python scripts/run_day7_baselines.py --method static --seed 0
    python scripts/run_day7_baselines.py --method greedy --seed 0
    python scripts/run_day7_baselines.py --method coverage --seed 0

    # 批量运行 10 seeds + 汇总
    python scripts/run_day7_baselines.py --batch --seeds 0-9 --methods static,greedy,coverage
"""

import sys
import json
import argparse
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.env.core import AGCoopEnv
from agcoop.utils.seeding import seed_everything


def run_one(config, seed, method, out_dir):
    """运行一个 episode"""
    config['episode']['seed'] = seed

    # greedy/coverage 不需要 mapf.enabled
    if method in ["greedy", "coverage"]:
        config['mapf']['enabled'] = False
    elif method == "mapf":
        config['mapf']['enabled'] = True

    seed_everything(seed)

    env = AGCoopEnv(
        config,
        output_dir=str(out_dir),
        enable_logging=True,
        method=method,
        planner="none"
    )

    state = env.reset()

    step_count = 0
    done = False
    while not done:
        state, reward, done, info = env.step()
        step_count += 1

    env.close()
    return step_count


def load_metrics(out_dir):
    """加载 metrics.json"""
    with open(Path(out_dir) / "metrics.json") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description='Day7 Baseline 入口')
    parser.add_argument('--config', type=str, default='configs/day7_baseline.yaml')
    parser.add_argument('--method', type=str, default='static',
                        help='方法: static, greedy, mapf, coverage')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--steps', type=int, default=None,
                        help='覆盖 horizon_steps')
    parser.add_argument('--out', type=str, default=None,
                        help='输出目录名')

    # 批量模式
    parser.add_argument('--batch', action='store_true',
                        help='批量运行多个 seed/method')
    parser.add_argument('--seeds', type=str, default='0-9',
                        help='seed 范围, 如 0-9')
    parser.add_argument('--methods', type=str, default='static,greedy',
                        help='方法列表, 逗号分隔')

    args = parser.parse_args()

    # 加载配置
    with open(args.config) as f:
        base_config = yaml.safe_load(f)

    if args.steps:
        base_config['episode']['horizon_steps'] = args.steps

    if args.batch:
        # 批量模式
        start, end = map(int, args.seeds.split('-'))
        seeds = list(range(start, end + 1))
        methods = args.methods.split(',')

        print("=" * 70)
        print("Day7 Baseline 批量运行")
        print("=" * 70)
        print(f"  方法: {methods}")
        print(f"  Seeds: {seeds}")
        print(f"  Steps: {base_config['episode']['horizon_steps']}")
        print()

        all_results = []

        for method in methods:
            for seed in seeds:
                import copy
                config = copy.deepcopy(base_config)

                out_dir = Path('outputs') / f"day7_{method}_seed{seed}"
                print(f"  运行 {method}/seed{seed}...", end=" ", flush=True)

                run_one(config, seed, method, out_dir)
                m = load_metrics(out_dir)

                row = {
                    'method': method,
                    'seed': seed,
                    'steps': m['steps'],
                    'tasks_completed': m['tasks_completed'],
                    'total_tasks': m['total_tasks'],
                    'deadline_miss': m['deadline_miss'],
                    'deadline_miss_rate': m['deadline_miss_rate'],
                    'mean_tardiness': m['mean_tardiness'],
                    'outage_percent': m['outage_percent'],
                    'mean_step_motion': m.get('mean_step_motion', 0),
                    'runtime_sec': round(m['runtime_sec'], 2),
                }
                all_results.append(row)
                print(f"完成 (tasks={row['tasks_completed']}, "
                      f"miss_rate={row['deadline_miss_rate']}%, "
                      f"outage={row['outage_percent']}%)")

        # 汇总表
        summary_dir = Path('outputs') / 'day7_summary'
        summary_dir.mkdir(parents=True, exist_ok=True)

        # 保存详细结果
        with open(summary_dir / 'results.json', 'w') as f:
            json.dump(all_results, f, indent=2)

        # 按方法汇总
        print()
        print("=" * 70)
        print("汇总结果")
        print("=" * 70)
        print(f"{'method':<10} {'completed':>10} {'miss_rate%':>10} "
              f"{'tardiness':>10} {'outage%':>10} {'motion':>10}")
        print("-" * 70)

        for method in methods:
            rows = [r for r in all_results if r['method'] == method]
            n = len(rows)
            avg_completed = sum(r['tasks_completed'] for r in rows) / n
            avg_miss_rate = sum(r['deadline_miss_rate'] for r in rows) / n
            avg_tardiness = sum(r['mean_tardiness'] for r in rows) / n
            avg_outage = sum(r['outage_percent'] for r in rows) / n
            avg_motion = sum(r['mean_step_motion'] for r in rows) / n

            print(f"{method:<10} {avg_completed:>10.1f} {avg_miss_rate:>10.1f} "
                  f"{avg_tardiness:>10.1f} {avg_outage:>10.1f} {avg_motion:>10.3f}")

        print()
        print(f"详细结果: {summary_dir / 'results.json'}")

    else:
        # 单次模式
        import copy
        config = copy.deepcopy(base_config)
        config['episode']['seed'] = args.seed

        if args.out:
            out_dir = Path('outputs') / args.out
        else:
            out_dir = Path('outputs') / f"day7_{args.method}_seed{args.seed}"

        print("=" * 60)
        print(f"Day7 Baseline: method={args.method}, seed={args.seed}")
        print("=" * 60)

        step_count = run_one(config, args.seed, args.method, out_dir)
        m = load_metrics(out_dir)

        print(f"\n完成 {step_count} 步")
        print(f"  tasks_completed: {m['tasks_completed']}")
        print(f"  deadline_miss_rate: {m['deadline_miss_rate']}%")
        print(f"  outage_percent: {m['outage_percent']}%")
        print(f"  mean_step_motion: {m.get('mean_step_motion', 0)}")
        print(f"  输出: {out_dir}")


if __name__ == "__main__":
    main()
