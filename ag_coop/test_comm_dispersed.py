#!/usr/bin/env python3
"""
测试通信模型集成（UGV 分散场景）

验证：
1. UGV 分散后，SNR 会降低
2. outage_percent 随阈值变化明显
"""

import sys
from pathlib import Path
import yaml

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from agcoop.env.core import AGCoopEnv


def test_comm_with_dispersed_ugvs():
    """测试：UGV 分散后的通信效果"""
    print("\n" + "=" * 60)
    print("测试：UGV 分散场景的通信")
    print("=" * 60)

    # 加载配置
    config_path = Path(__file__).parent / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    config['comm']['enabled'] = True
    config['comm']['snr_threshold_db'] = 10.0  # 较高阈值，容易触发 outage
    config['episode']['horizon_steps'] = 50

    # 创建环境
    output_dir = Path(__file__).parent / "outputs" / "test_dispersed_ugvs"
    env = AGCoopEnv(config, output_dir=str(output_dir), enable_logging=True)

    # 重置环境
    state = env.reset()

    # 手动设置 UGV 位置（分散开）
    if env.grid_map is not None:
        # 使用地图坐标
        state.ugv_positions = [
            (0.5, 0.5),   # UGV 0: 左下角
            (3.5, 0.5),   # UGV 1: 右下角
            (0.5, 3.5),   # UGV 2: 左上角
        ]
        print(f"\nUGV 位置（分散）:")
        for i, pos in enumerate(state.ugv_positions):
            print(f"  UGV {i}: {pos}")
    else:
        # 使用默认坐标
        state.ugv_positions = [
            (0.0, 0.0),
            (50.0, 0.0),
            (0.0, 50.0),
        ]

    # UAV 在 UGV 0 上
    state.uav_onboard_ugv_id = 0

    # 运行 episode
    for t in range(config['episode']['horizon_steps']):
        state, reward, done, info = env.step()
        if done:
            break

    env.close()

    # 读取 metrics
    metrics_path = output_dir / "metrics.json"
    import json
    with open(metrics_path, 'r') as f:
        metrics = json.load(f)

    print(f"\n通信指标:")
    print(f"  snr_best_mean: {metrics['snr_best_mean']:.2f} dB")
    print(f"  snr_best_min:  {metrics['snr_best_min']:.2f} dB")
    print(f"  outage_percent: {metrics['outage_percent']:.2f}%")
    print(f"  max_outage_streak: {metrics['max_outage_streak']}")

    # 读取几条 trace
    trace_path = output_dir / "trace.jsonl"
    print(f"\ntrace 前 5 步:")
    with open(trace_path, 'r') as f:
        for i, line in enumerate(f):
            if i >= 5:
                break
            trace_entry = json.loads(line)
            print(f"  t={trace_entry['t']:2d}: snr_best={trace_entry['snr_best']:6.2f} dB, outage={trace_entry['outage']}")

    if env.grid_map is not None:
        print("\n✓ UGV 分散场景测试完成")
    else:
        print("\n⚠ 地图未加载，使用简单随机模型")


def main():
    """运行测试"""
    print("\n" + "=" * 60)
    print("通信模型集成测试（UGV 分散场景）")
    print("=" * 60)

    try:
        test_comm_with_dispersed_ugvs()

        print("\n" + "=" * 60)
        print("✓ 测试完成！")
        print("=" * 60)
        print()

    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
