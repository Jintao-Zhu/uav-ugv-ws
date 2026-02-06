#!/usr/bin/env python3
"""
一键运行脚本：运行一个完整的 episode 并输出日志

用法：
    python scripts/run_one_episode.py
    python scripts/run_one_episode.py --config configs/default.yaml --seed 42
    python scripts/run_one_episode.py --seed 123 --out_name my_run
"""

import sys
import argparse
import yaml
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.env.core import AGCoopEnv
from agcoop.utils.seeding import seed_everything


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='运行一个完整的 AGCoop episode')
    parser.add_argument('--config', type=str, default='configs/default.yaml',
                        help='配置文件路径（默认：configs/default.yaml）')
    parser.add_argument('--seed', type=int, default=None,
                        help='随机种子（覆盖配置文件中的 seed）')
    parser.add_argument('--out_name', type=str, default=None,
                        help='输出目录名称（默认按 seed 命名）')
    parser.add_argument('--method', type=str, default='static',
                        help='方法名称（默认：static）')
    parser.add_argument('--planner', type=str, default='none',
                        help='规划器名称（默认：none）')
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 1. 加载配置
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"错误：配置文件不存在: {config_path}")
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 2. 覆盖 seed（如果指定）
    if args.seed is not None:
        config['episode']['seed'] = args.seed

    seed = config['episode']['seed']

    # 3. 设置输出目录
    if args.out_name:
        output_dir = Path('outputs') / args.out_name
    else:
        output_dir = Path('outputs') / f"seed_{seed}"

    print("=" * 60)
    print("AGCoop - 运行 Episode")
    print("=" * 60)
    print(f"配置文件: {config_path}")
    print(f"随机种子: {seed}")
    print(f"Horizon: {config['episode']['horizon_steps']} 步")
    print(f"输出目录: {output_dir}")
    print("=" * 60)

    # 4. 设置随机种子
    seed_everything(seed)

    # 5. 创建环境
    env = AGCoopEnv(
        config,
        output_dir=str(output_dir),
        enable_logging=True,
        method=args.method,
        planner=args.planner
    )

    # 6. 重置环境
    state = env.reset()
    print(f"\n环境已重置")
    print(f"  - UGV 数量: {len(state.ugv_positions)}")
    print(f"  - UAV 数量: {config['robots']['n_uav']}")
    print(f"  - 任务到达率: {config['tasks']['arrival_rate']}")

    # 7. 运行 episode
    print(f"\n开始运行...")
    step_count = 0
    done = False
    start_time = datetime.now()

    # 每 10% 打印一次进度
    progress_interval = max(1, config['episode']['horizon_steps'] // 10)

    while not done:
        state, reward, done, info = env.step()
        step_count += 1

        # 打印进度
        if step_count % progress_interval == 0 or done:
            progress = (step_count / config['episode']['horizon_steps']) * 100
            print(f"  进度: {progress:5.1f}% ({step_count}/{config['episode']['horizon_steps']}) | "
                  f"完成: {info['tasks_completed']:3d} | "
                  f"活跃: {info['active_tasks']:3d} | "
                  f"outage: {info['outage_steps']:3d}")

    # 8. 关闭环境
    env.close()

    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()

    # 9. 输出最终结果
    print("\n" + "=" * 60)
    print("✓ Episode 完成")
    print("=" * 60)
    print(f"总步数: {step_count}")
    print(f"完成任务: {state.tasks_completed}")
    print(f"总任务数: {len(state.task_pool)}")
    print(f"活跃任务: {len(state.get_active_tasks())}")
    print(f"超期任务: {state.deadline_miss}")
    print(f"延迟总和: {state.tardiness_sum}")
    print(f"Outage 步数: {state.outage_steps} ({state.outage_steps/step_count*100:.1f}%)")
    print(f"运行时间: {elapsed:.2f} 秒")
    print("=" * 60)

    # 10. 验证输出文件
    print(f"\n输出文件:")
    trace_file = output_dir / "trace.jsonl"
    metrics_file = output_dir / "metrics.json"
    config_file = output_dir / "config_resolved.yaml"

    all_exist = True
    for file_path, name in [(trace_file, "trace.jsonl"),
                            (metrics_file, "metrics.json"),
                            (config_file, "config_resolved.yaml")]:
        if file_path.exists():
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name} (不存在)")
            all_exist = False

    if all_exist:
        # 验证 trace 行数
        with open(trace_file, 'r') as f:
            trace_lines = len(f.readlines())
        if trace_lines == step_count:
            print(f"\n✓ trace.jsonl 行数验证通过 ({trace_lines} 行)")
        else:
            print(f"\n✗ trace.jsonl 行数不匹配: 期望 {step_count}，实际 {trace_lines}")

    print(f"\n所有输出已保存到: {output_dir.absolute()}")


if __name__ == "__main__":
    main()
