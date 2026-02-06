#!/usr/bin/env python3
"""
通信模型单元测试

测试内容：
1. 距离变大，SNR 降低
2. blocked 增加，SNR 降低
3. threshold 检查 outage 正确
4. 输出数值不是 NaN/inf
"""

import sys
from pathlib import Path
import numpy as np

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from agcoop.comm import comm_model
from agcoop.map import GridMap


def test_snr_decreases_with_distance():
    """测试：距离变大，SNR 降低"""
    config = comm_model.CommConfig(
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        snr_threshold_db=-20.0,
        eps_m=0.05
    )

    # 计算不同距离的 SNR
    snr_1m = comm_model.compute_snr(1.0, 0, config)
    snr_10m = comm_model.compute_snr(10.0, 0, config)
    snr_100m = comm_model.compute_snr(100.0, 0, config)

    print(f"  SNR @ 1m:   {snr_1m:.2f} dB")
    print(f"  SNR @ 10m:  {snr_10m:.2f} dB")
    print(f"  SNR @ 100m: {snr_100m:.2f} dB")

    # 验证：距离越大，SNR 越低
    assert snr_1m > snr_10m, f"SNR 应该随距离降低：{snr_1m} > {snr_10m}"
    assert snr_10m > snr_100m, f"SNR 应该随距离降低：{snr_10m} > {snr_100m}"

    # 验证：数值不是 NaN/inf
    assert not np.isnan(snr_1m), "SNR 不应该是 NaN"
    assert not np.isinf(snr_1m), "SNR 不应该是 inf"
    assert not np.isnan(snr_100m), "SNR 不应该是 NaN"
    assert not np.isinf(snr_100m), "SNR 不应该是 inf"

    print("✓ 距离变大，SNR 降低测试通过")


def test_snr_decreases_with_obstacles():
    """测试：blocked 增加，SNR 降低"""
    config = comm_model.CommConfig(
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        snr_threshold_db=-20.0,
        eps_m=0.05
    )

    # 固定距离，不同遮挡数
    distance = 10.0
    snr_0_blocked = comm_model.compute_snr(distance, 0, config)
    snr_1_blocked = comm_model.compute_snr(distance, 1, config)
    snr_5_blocked = comm_model.compute_snr(distance, 5, config)

    print(f"  SNR (0 blocked): {snr_0_blocked:.2f} dB")
    print(f"  SNR (1 blocked): {snr_1_blocked:.2f} dB")
    print(f"  SNR (5 blocked): {snr_5_blocked:.2f} dB")

    # 验证：遮挡越多，SNR 越低
    assert snr_0_blocked > snr_1_blocked, f"SNR 应该随遮挡降低：{snr_0_blocked} > {snr_1_blocked}"
    assert snr_1_blocked > snr_5_blocked, f"SNR 应该随遮挡降低：{snr_1_blocked} > {snr_5_blocked}"

    # 验证：每个障碍扣 6 dB
    expected_diff = config.obstacle_penalty_db
    actual_diff = snr_0_blocked - snr_1_blocked
    assert abs(actual_diff - expected_diff) < 0.01, f"每个障碍应该扣 {expected_diff} dB，实际 {actual_diff}"

    print("✓ blocked 增加，SNR 降低测试通过")


def test_outage_threshold():
    """测试：threshold 检查 outage 正确"""
    config = comm_model.CommConfig(
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        snr_threshold_db=-20.0,
        eps_m=0.05
    )

    # 创建简单地图（无障碍）
    grid = np.zeros((10, 10), dtype=int)
    grid_map = GridMap(width=10, height=10, grid=grid, resolution=0.2)

    # UAV 在 (0, 0)，UGV 在不同距离
    uav_cell = (0, 0)
    ugv_near = (0, 2)   # 近距离，SNR 高
    ugv_far = (9, 9)    # 远距离，但可能还不够远

    # 测试近距离（应该不 outage）
    snr_best, best_id, outage = comm_model.compute_best_snr(
        uav_cell, [ugv_near], grid_map, config
    )
    print(f"  近距离: SNR={snr_best:.2f} dB, outage={outage}")
    assert not outage, f"近距离不应该 outage（SNR={snr_best:.2f} > {config.snr_threshold_db}）"

    # 测试远距离 + 障碍（确保 outage）
    # 创建有障碍的地图
    grid_with_obstacles = np.zeros((20, 20), dtype=int)
    # 在对角线上放置多个障碍
    for i in range(5, 15):
        grid_with_obstacles[i, i] = 1
    grid_map_blocked = GridMap(width=20, height=20, grid=grid_with_obstacles, resolution=0.2)

    ugv_very_far = (19, 19)  # 非常远 + 穿过多个障碍
    snr_best, best_id, outage = comm_model.compute_best_snr(
        uav_cell, [ugv_very_far], grid_map_blocked, config
    )
    print(f"  远距离+障碍: SNR={snr_best:.2f} dB, outage={outage}")
    assert outage, f"远距离+障碍应该 outage（SNR={snr_best:.2f} < {config.snr_threshold_db}）"

    # 测试阈值边界
    # 使用更严格的阈值
    config_strict = comm_model.CommConfig(
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        snr_threshold_db=0.0,  # 严格阈值
        eps_m=0.05
    )

    snr_best, best_id, outage = comm_model.compute_best_snr(
        uav_cell, [ugv_far], grid_map, config_strict
    )
    print(f"  严格阈值: SNR={snr_best:.2f} dB, threshold=0.0 dB, outage={outage}")
    assert outage, f"严格阈值应该 outage（SNR={snr_best:.2f} < 0.0）"

    print("✓ outage threshold 测试通过")


def test_best_snr_selection():
    """测试：正确选择最佳 UGV"""
    config = comm_model.CommConfig(
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        snr_threshold_db=-20.0,
        eps_m=0.05
    )

    # 创建地图，中间有障碍
    grid = np.zeros((10, 10), dtype=int)
    grid[5, 5] = 1  # 中心障碍
    grid_map = GridMap(width=10, height=10, grid=grid, resolution=0.2)

    # UAV 在 (0, 0)
    uav_cell = (0, 0)

    # 多个 UGV
    ugv_cells = [
        (0, 5),   # UGV 0: 中等距离，无障碍
        (9, 9),   # UGV 1: 远距离，可能有障碍
        (0, 2),   # UGV 2: 近距离，无障碍（应该是最佳）
    ]

    # 计算最佳 SNR
    snr_best, best_id, outage = comm_model.compute_best_snr(
        uav_cell, ugv_cells, grid_map, config
    )

    print(f"  Best UGV: {best_id}, SNR: {snr_best:.2f} dB, outage: {outage}")

    # 验证：最近的 UGV 应该是最佳
    assert best_id == 2, f"最近的 UGV 应该是最佳，得到 {best_id}"

    # 验证：数值不是 NaN/inf
    assert not np.isnan(snr_best), "SNR 不应该是 NaN"
    assert not np.isinf(snr_best), "SNR 不应该是 inf"

    print("✓ 最佳 UGV 选择测试通过")


def test_compute_comm_metrics():
    """测试：完整通信指标计算"""
    config = comm_model.CommConfig(
        tx_power_db=0.0,
        pathloss_n=2.0,
        obstacle_penalty_db=6.0,
        snr_threshold_db=-20.0,
        eps_m=0.05
    )

    # 创建地图
    grid = np.zeros((10, 10), dtype=int)
    grid[2, 2] = 1
    grid_map = GridMap(width=10, height=10, grid=grid, resolution=0.2)

    # UAV 和 UGV
    uav_cell = (0, 0)
    ugv_cells = [(0, 5), (5, 5), (0, 2)]

    # 计算指标
    metrics = comm_model.compute_comm_metrics(uav_cell, ugv_cells, grid_map, config)

    print(f"  SNR best: {metrics['snr_best']:.2f} dB")
    print(f"  Best UGV: {metrics['best_ugv_id']}")
    print(f"  Outage: {metrics['outage']}")
    print(f"  SNR list: {[f'{s:.2f}' for s in metrics['snr_list']]}")

    # 验证：返回字段完整
    assert 'snr_best' in metrics
    assert 'best_ugv_id' in metrics
    assert 'outage' in metrics
    assert 'snr_list' in metrics
    assert 'distance_list' in metrics
    assert 'blocked_list' in metrics

    # 验证：列表长度正确
    assert len(metrics['snr_list']) == len(ugv_cells)
    assert len(metrics['distance_list']) == len(ugv_cells)
    assert len(metrics['blocked_list']) == len(ugv_cells)

    # 验证：数值不是 NaN/inf
    assert not np.isnan(metrics['snr_best'])
    assert not np.isinf(metrics['snr_best'])
    for snr in metrics['snr_list']:
        assert not np.isnan(snr), "SNR 列表不应该包含 NaN"
        assert not np.isinf(snr), "SNR 列表不应该包含 inf"

    print("✓ 完整通信指标计算测试通过")


def test_empty_ugv_list():
    """测试：空 UGV 列表的边界情况"""
    config = comm_model.CommConfig()

    grid = np.zeros((10, 10), dtype=int)
    grid_map = GridMap(width=10, height=10, grid=grid, resolution=0.2)

    uav_cell = (0, 0)
    ugv_cells = []

    # 应该返回最差情况
    snr_best, best_id, outage = comm_model.compute_best_snr(
        uav_cell, ugv_cells, grid_map, config
    )

    assert best_id == -1, "空列表应该返回 -1"
    assert outage == True, "空列表应该 outage"
    assert np.isinf(snr_best) and snr_best < 0, "空列表应该返回 -inf"

    print("✓ 空 UGV 列表测试通过")


def test_config_from_dict():
    """测试：从字典创建配置"""
    config_dict = {
        'enabled': True,
        'tx_power_db': 10.0,
        'pathloss_n': 3.0,
        'obstacle_penalty_db': 8.0,
        'snr_threshold_db': -15.0,
        'eps_m': 0.1,
    }

    config = comm_model.CommConfig.from_dict(config_dict)

    assert config.enabled == True
    assert config.tx_power_db == 10.0
    assert config.pathloss_n == 3.0
    assert config.obstacle_penalty_db == 8.0
    assert config.snr_threshold_db == -15.0
    assert config.eps_m == 0.1

    print("✓ 配置字典转换测试通过")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("通信模型单元测试")
    print("=" * 60 + "\n")

    try:
        print("测试 1: 距离变大，SNR 降低")
        test_snr_decreases_with_distance()

        print("\n测试 2: blocked 增加，SNR 降低")
        test_snr_decreases_with_obstacles()

        print("\n测试 3: outage threshold 检查")
        test_outage_threshold()

        print("\n测试 4: 最佳 UGV 选择")
        test_best_snr_selection()

        print("\n测试 5: 完整通信指标计算")
        test_compute_comm_metrics()

        print("\n测试 6: 边界情况")
        test_empty_ugv_list()

        print("\n测试 7: 配置字典转换")
        test_config_from_dict()

        print("\n" + "=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)

        print("\n验收标准达成:")
        print("  ✓ 距离变大，SNR 降低")
        print("  ✓ blocked 增加，SNR 降低")
        print("  ✓ threshold 检查 outage 正确")
        print("  ✓ 输出数值不是 NaN/inf")
        print()

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
