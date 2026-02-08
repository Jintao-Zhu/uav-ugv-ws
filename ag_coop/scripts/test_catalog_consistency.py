#!/usr/bin/env python3
"""
Day8 Step 6.1: 验证任务目录一致性

测试同一 seed 下，不同方法使用的任务目录是否完全一致。
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.env.core import AGCoopEnv
from agcoop.utils.seeding import seed_everything
import yaml
import copy


def run_and_get_catalog_hash(config, seed, method, out_dir):
    """运行环境并获取任务目录哈希"""
    config['episode']['seed'] = seed
    config['mapf']['enabled'] = False

    seed_everything(seed)

    env = AGCoopEnv(
        config,
        output_dir=str(out_dir),
        enable_logging=True,
        method=method,
        planner="none"
    )

    state = env.reset()
    env.close()

    # 读取任务目录
    catalog_path = out_dir / 'tasks_catalog.json'
    if not catalog_path.exists():
        return None, None

    with open(catalog_path) as f:
        catalog_data = json.load(f)

    # 计算哈希
    import hashlib
    catalog_str = json.dumps(catalog_data['tasks'], sort_keys=True)
    catalog_hash = hashlib.sha256(catalog_str.encode()).hexdigest()[:16]

    return catalog_data, catalog_hash


def main():
    print("=" * 70)
    print("Day8 Step 6.1: 任务目录一致性验证")
    print("=" * 70)
    print()

    # 配置
    config_path = "configs/day7_baseline.yaml"
    seed = 0
    methods = ["greedy", "coverage"]

    # 加载配置
    with open(config_path) as f:
        base_config = yaml.safe_load(f)

    # 调整通信参数
    base_config['comm']['enabled'] = True
    base_config['comm']['snr_threshold_db'] = -12.0

    print(f"配置: {config_path}")
    print(f"Seed: {seed}")
    print(f"方法: {methods}")
    print()

    # 运行两个方法
    catalogs = {}
    hashes = {}

    for method in methods:
        config = copy.deepcopy(base_config)
        out_dir = Path('outputs') / f"day8_catalog_test_{method}_seed{seed}"

        print(f"运行 {method}...", end=" ", flush=True)

        catalog_data, catalog_hash = run_and_get_catalog_hash(config, seed, method, out_dir)

        if catalog_data is None:
            print("❌ 任务目录未生成")
            return 1

        catalogs[method] = catalog_data
        hashes[method] = catalog_hash

        print(f"完成 (hash={catalog_hash}, tasks={catalog_data['total_tasks']})")

    print()
    print("=" * 70)
    print("一致性检查")
    print("=" * 70)
    print()

    # 检查哈希
    greedy_hash = hashes['greedy']
    coverage_hash = hashes['coverage']

    print(f"Greedy hash:   {greedy_hash}")
    print(f"Coverage hash: {coverage_hash}")
    print()

    if greedy_hash == coverage_hash:
        print("✅ 任务目录哈希一致！")
    else:
        print("❌ 任务目录哈希不一致！")
        return 1

    # 检查任务数量
    greedy_count = catalogs['greedy']['total_tasks']
    coverage_count = catalogs['coverage']['total_tasks']

    print(f"Greedy tasks:   {greedy_count}")
    print(f"Coverage tasks: {coverage_count}")
    print()

    if greedy_count == coverage_count:
        print("✅ 任务数量一致！")
    else:
        print("❌ 任务数量不一致！")
        return 1

    # 逐个检查任务
    greedy_tasks = catalogs['greedy']['tasks']
    coverage_tasks = catalogs['coverage']['tasks']

    mismatch_count = 0
    for i, (gt, ct) in enumerate(zip(greedy_tasks, coverage_tasks)):
        if gt != ct:
            if mismatch_count < 3:
                print(f"任务 {i} 不匹配:")
                print(f"  Greedy:   {gt}")
                print(f"  Coverage: {ct}")
            mismatch_count += 1

    if mismatch_count > 0:
        print(f"❌ 发现 {mismatch_count} 个任务不匹配！")
        return 1

    print("✅ 所有任务逐个匹配！")
    print()

    print("=" * 70)
    print("✅✅✅ 验收通过！任务目录完全一致 ✅✅✅")
    print("=" * 70)
    print()

    # 显示任务样本
    print("任务样本（前 5 个）:")
    for i, task in enumerate(greedy_tasks[:5]):
        print(f"  {i}. t={task['release_t']:3d}, pos={task['position']}, "
              f"cell={task['cell']}, deadline={task['deadline_t']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
