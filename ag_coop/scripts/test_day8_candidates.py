#!/usr/bin/env python3
"""
Day8 Step 2: 测试候选中继点生成

验证：
1. 相同 seed + map 生成完全一致的 R
2. 候选点数量 = R
3. 所有候选点都在 free cell 上
"""

import sys
from pathlib import Path
import json

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv
from agcoop.utils.seeding import seed_everything
import yaml


def test_candidate_generation(config_path: str, seed: int, num_runs: int = 3):
    """
    测试候选点生成的确定性

    Args:
        config_path: 配置文件路径
        seed: 随机种子
        num_runs: 运行次数
    """
    print("=" * 60)
    print("Day8 Step 2: 候选中继点生成测试")
    print("=" * 60)
    print(f"配置文件: {config_path}")
    print(f"随机种子: {seed}")
    print(f"运行次数: {num_runs}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['episode']['seed'] = seed
    config['mapf']['enabled'] = False

    # 多次运行，收集候选点
    all_candidates = []

    for run_id in range(num_runs):
        print(f"运行 {run_id + 1}/{num_runs}...")

        # 重置随机种子（确保每次都一样）
        seed_everything(seed)

        # 创建环境
        output_name = f"test_candidates_run{run_id}_seed{seed}"
        env = AGCoopEnv(
            config,
            output_dir=f"outputs/{output_name}",
            enable_logging=True,
            method="greedy",
            planner="none"
        )

        # Reset 会生成候选点
        state = env.reset()

        # 读取 init.json
        init_path = Path(f"outputs/{output_name}/init.json")
        with open(init_path, 'r') as f:
            init_data = json.load(f)

        candidates = init_data.get('candidate_relays', [])
        all_candidates.append(candidates)

        print(f"  候选点数量: {len(candidates)}")
        print(f"  前 3 个: {candidates[:3]}")

    # 验证一致性
    print()
    print("=" * 60)
    print("验证结果:")
    print("=" * 60)

    # 检查数量
    expected_count = config.get('rendezvous', {}).get('candidate_count', 12)
    all_same_count = all(len(c) == expected_count for c in all_candidates)
    print(f"✓ 候选点数量: {len(all_candidates[0])} (期望 {expected_count})")
    if not all_same_count:
        print(f"  ✗ 警告: 不同运行的数量不一致")

    # 检查一致性
    first_candidates = all_candidates[0]
    all_identical = all(c == first_candidates for c in all_candidates)

    if all_identical:
        print(f"✓ 确定性验证通过: {num_runs} 次运行生成完全一致的候选点")
    else:
        print(f"✗ 确定性验证失败: 不同运行生成了不同的候选点")
        for i, c in enumerate(all_candidates):
            print(f"  运行 {i}: {c[:3]}...")

    # 检查候选点是否在 free cell 上
    print()
    print("候选点详情:")
    print(f"  总数: {len(first_candidates)}")
    print(f"  坐标范围: i=[{min(c[0] for c in first_candidates)}, {max(c[0] for c in first_candidates)}], "
          f"j=[{min(c[1] for c in first_candidates)}, {max(c[1] for c in first_candidates)}]")

    # 显示所有候选点
    print()
    print("所有候选点 (i, j):")
    for i, cell in enumerate(first_candidates):
        print(f"  {i+1:2d}. {cell}")

    # 分析候选点类型（需要重新加载地图）
    print()
    print("分析候选点类型...")
    seed_everything(seed)
    env = AGCoopEnv(
        config,
        output_dir=f"outputs/test_candidates_analysis_seed{seed}",
        enable_logging=False,
        method="greedy",
        planner="none"
    )
    env.reset()

    if env.grid_map:
        from agcoop.rendezvous.candidate_generator import _find_intersection_points

        # 获取所有 free cells
        free_cells = []
        for i in range(env.grid_map.height):
            for j in range(env.grid_map.width):
                if env.grid_map.is_free(i, j):
                    free_cells.append((i, j))

        # 找到 intersection 点
        intersection_points = _find_intersection_points(env.grid_map, free_cells)

        # 统计候选点类型
        n_intersection = sum(1 for c in first_candidates if tuple(c) in intersection_points)
        print(f"  Intersection 点: {n_intersection}/{len(first_candidates)}")
        print(f"  其他点: {len(first_candidates) - n_intersection}/{len(first_candidates)}")

    print()
    print("=" * 60)
    if all_identical and all_same_count:
        print("✓✓✓ Day8 Step 2 测试通过！✓✓✓")
    else:
        print("✗ 测试失败，需要检查代码")
    print("=" * 60)

    return all_identical and all_same_count


def main():
    """主函数"""
    config_path = "configs/day8_outage_test_v2.yaml"
    seed = 42

    # 检查配置文件是否存在
    if not Path(config_path).exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    # 运行测试
    success = test_candidate_generation(config_path, seed, num_runs=3)

    if success:
        print()
        print("下一步: 在 visualizer 中显示候选点")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
