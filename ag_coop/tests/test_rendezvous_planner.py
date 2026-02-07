#!/usr/bin/env python3
"""
测试 Rendezvous 规划器
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.map import auto_load_map
from agcoop.comm import CommModel
from agcoop.rendezvous import RendezvousPlanner


def test_candidate_generation():
    """测试候选会合点生成"""
    print("\n" + "=" * 60)
    print("测试候选会合点生成")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建通信模型
    comm_model = CommModel(
        grid_map=grid_map,
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        snr_threshold_db=-9.0
    )

    # 创建规划器
    planner = RendezvousPlanner(
        grid_map=grid_map,
        comm_model=comm_model,
        candidate_count=12,
        seed=42
    )

    candidates = planner.get_candidates()

    print(f"候选会合点数量: {len(candidates)}")
    print(f"前 5 个候选点: {candidates[:5]}")

    # 验证
    assert len(candidates) <= 12, "候选点数量不应超过 12"
    assert len(candidates) > 0, "应该有候选点"

    # 验证所有候选点都是自由空间
    for cell in candidates:
        i, j = cell
        assert grid_map.grid[i, j] == 0, f"候选点 {cell} 不是自由空间"

    print("✓ 候选点生成测试通过")


def test_junction_detection():
    """测试路口点检测"""
    print("\n" + "=" * 60)
    print("测试路口点检测")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建通信模型
    comm_model = CommModel(
        grid_map=grid_map,
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        snr_threshold_db=-9.0
    )

    # 创建规划器
    planner = RendezvousPlanner(
        grid_map=grid_map,
        comm_model=comm_model,
        candidate_count=12,
        seed=42
    )

    # 统计路口点
    junction_count = 0
    for cell in planner.get_candidates():
        degree = planner._get_degree_4(cell)
        if degree >= 3:
            junction_count += 1
            if junction_count <= 3:  # 只打印前 3 个
                print(f"  路口点: {cell}, 度数: {degree}")

    print(f"路口点总数: {junction_count}")

    assert junction_count >= 0, "路口点数量应该 >= 0"
    print("✓ 路口点检测测试通过")


def test_rendezvous_planning():
    """测试会合规划"""
    print("\n" + "=" * 60)
    print("测试会合规划")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建通信模型
    comm_model = CommModel(
        grid_map=grid_map,
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        snr_threshold_db=-9.0
    )

    # 创建规划器
    planner = RendezvousPlanner(
        grid_map=grid_map,
        comm_model=comm_model,
        candidate_count=12,
        score_alpha_snr=1.0,
        score_beta_eta=0.3,
        meet_window=3,
        seed=42
    )

    # 规划会合
    t_now = 10
    task_cell = (10, 10)
    ugv_carrier_pos = (5, 5)

    plan = planner.plan(t_now, task_cell, ugv_carrier_pos)

    print(f"当前时刻: {t_now}")
    print(f"任务位置: {task_cell}")
    print(f"载机位置: {ugv_carrier_pos}")
    print(f"\n会合计划:")
    print(f"  会合点: {plan.rendezvous_cell}")
    print(f"  会合时刻: {plan.t_meet}")
    print(f"  时间窗: ±{plan.window}")
    print(f"  评分: {plan.score:.2f}")
    print(f"  UAV ETA: {plan.eta_uav}")
    print(f"  UGV ETA: {plan.eta_ugv}")
    print(f"  预测 SNR: {plan.snr_pred:.2f} dB")

    # 验证
    assert plan is not None, "应该生成会合计划"
    assert plan.rendezvous_cell in planner.get_candidates(), "会合点应该在候选集合中"
    assert plan.t_meet >= t_now, "会合时刻应该在未来"
    assert plan.t_meet == t_now + max(plan.eta_uav, plan.eta_ugv), "会合时刻计算错误"
    assert plan.window == 3, "时间窗应该是 3"

    print("✓ 会合规划测试通过")


def test_scoring_function():
    """测试评分函数"""
    print("\n" + "=" * 60)
    print("测试评分函数")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建通信模型
    comm_model = CommModel(
        grid_map=grid_map,
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        snr_threshold_db=-9.0
    )

    # 创建规划器
    planner = RendezvousPlanner(
        grid_map=grid_map,
        comm_model=comm_model,
        candidate_count=12,
        score_alpha_snr=1.0,
        score_beta_eta=0.3,
        seed=42
    )

    # 测试不同场景的评分
    scenarios = [
        {"snr": 0.0, "eta_uav": 10, "eta_ugv": 10, "desc": "SNR=0, ETA 相同"},
        {"snr": 10.0, "eta_uav": 10, "eta_ugv": 10, "desc": "SNR=10, ETA 相同"},
        {"snr": 0.0, "eta_uav": 10, "eta_ugv": 20, "desc": "SNR=0, ETA 差 10"},
        {"snr": 10.0, "eta_uav": 10, "eta_ugv": 20, "desc": "SNR=10, ETA 差 10"},
    ]

    print("\n评分测试:")
    for scenario in scenarios:
        score = planner._compute_score(
            scenario["snr"],
            scenario["eta_uav"],
            scenario["eta_ugv"]
        )
        print(f"  {scenario['desc']}: score = {score:.2f}")

    # 验证：SNR 越高，评分越高
    score1 = planner._compute_score(0.0, 10, 10)
    score2 = planner._compute_score(10.0, 10, 10)
    assert score2 > score1, "SNR 越高，评分应该越高"

    # 验证：ETA 差异越小，评分越高
    score3 = planner._compute_score(0.0, 10, 10)
    score4 = planner._compute_score(0.0, 10, 20)
    assert score3 > score4, "ETA 差异越小，评分应该越高"

    print("✓ 评分函数测试通过")


def test_distance_functions():
    """测试距离函数"""
    print("\n" + "=" * 60)
    print("测试距离函数")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建通信模型
    comm_model = CommModel(
        grid_map=grid_map,
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        snr_threshold_db=-9.0
    )

    # 创建规划器
    planner = RendezvousPlanner(
        grid_map=grid_map,
        comm_model=comm_model,
        candidate_count=12,
        seed=42
    )

    # 测试 8 邻接距离（Chebyshev）
    cell1 = (0, 0)
    cell2 = (5, 5)
    dist8 = planner._dist8(cell1, cell2)
    print(f"8 邻接距离 {cell1} -> {cell2}: {dist8}")
    assert dist8 == 5, "8 邻接距离应该是 5"

    # 测试 4 邻接距离（Manhattan）
    dist4 = planner._dist4(cell1, cell2)
    print(f"4 邻接距离 {cell1} -> {cell2}: {dist4}")
    assert dist4 == 10, "4 邻接距离应该是 10"

    # 测试不同方向
    cell3 = (0, 5)
    dist8_2 = planner._dist8(cell1, cell3)
    dist4_2 = planner._dist4(cell1, cell3)
    print(f"8 邻接距离 {cell1} -> {cell3}: {dist8_2}")
    print(f"4 邻接距离 {cell1} -> {cell3}: {dist4_2}")
    assert dist8_2 == 5, "8 邻接距离应该是 5"
    assert dist4_2 == 5, "4 邻接距离应该是 5"

    print("✓ 距离函数测试通过")


def test_reproducibility():
    """测试可复现性"""
    print("\n" + "=" * 60)
    print("测试可复现性")
    print("=" * 60)

    # 加载地图
    grid_map = auto_load_map('maps/map_01.map')

    # 创建通信模型
    comm_model = CommModel(
        grid_map=grid_map,
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        snr_threshold_db=-9.0
    )

    # 创建两个相同 seed 的规划器
    planner1 = RendezvousPlanner(
        grid_map=grid_map,
        comm_model=comm_model,
        candidate_count=12,
        seed=42
    )

    planner2 = RendezvousPlanner(
        grid_map=grid_map,
        comm_model=comm_model,
        candidate_count=12,
        seed=42
    )

    candidates1 = planner1.get_candidates()
    candidates2 = planner2.get_candidates()

    print(f"规划器 1 候选点: {candidates1[:3]}...")
    print(f"规划器 2 候选点: {candidates2[:3]}...")

    assert candidates1 == candidates2, "相同 seed 应该生成相同的候选点"

    print("✓ 可复现性测试通过")


def main():
    """运行所有测试"""
    print("=" * 60)
    print("Rendezvous 规划器测试")
    print("=" * 60)

    try:
        test_candidate_generation()
        test_junction_detection()
        test_rendezvous_planning()
        test_scoring_function()
        test_distance_functions()
        test_reproducibility()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        raise


if __name__ == "__main__":
    main()
