#!/usr/bin/env python3
"""
Day9 Step 3 验证：Observation Space

验证标准：
1. reset() 返回 obs，obs 中所有 key 都固定存在、shape 固定、dtype 合理（float32）
2. 任何一步 obs 不允许 NaN/Inf（跑 1 episode 后统计 np.isfinite(obs).all() 为 True）
3. FlattenObservation wrapper 正常工作
"""

import sys
from pathlib import Path
import yaml
import numpy as np

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.env.core import AGCoopEnv
from agcoop.env.wrappers import FlattenObservation


def test_observation_space(config_path: str):
    """
    测试 observation space 基本功能

    Args:
        config_path: 配置文件路径
    """
    print("=" * 70)
    print("Day9 Step 3: Observation Space 基本功能测试")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 创建环境
    env = AGCoopEnv(
        config,
        output_dir=None,
        enable_logging=False,
        method="rl",
        planner="none"
    )

    # 1. 检查 observation_space 属性
    print("1. Observation Space 属性检查:")
    obs_space = env.observation_space
    print(f"   observation_space: {obs_space}")
    print(f"   observation_space.spaces.keys(): {list(obs_space.spaces.keys())}")
    print()

    for key, space in obs_space.spaces.items():
        print(f"   - {key}: {space}")
        print(f"     shape: {space.shape}, dtype: {space.dtype}")

    print()

    # 2. 测试 reset() 返回的观测
    print("2. 测试 reset() 返回的观测:")
    obs = env.reset()

    print(f"   obs type: {type(obs)}")
    print(f"   obs keys: {list(obs.keys())}")
    print()

    # 验证所有 key 都存在
    expected_keys = set(obs_space.spaces.keys())
    actual_keys = set(obs.keys())

    if expected_keys == actual_keys:
        print("   ✓ 所有 key 都存在")
    else:
        print(f"   ✗ Key 不匹配:")
        print(f"     Expected: {expected_keys}")
        print(f"     Actual: {actual_keys}")
        print(f"     Missing: {expected_keys - actual_keys}")
        print(f"     Extra: {actual_keys - expected_keys}")
        return False

    print()

    # 验证 shape 和 dtype
    print("3. 验证 shape 和 dtype:")
    all_valid = True

    for key in expected_keys:
        expected_shape = obs_space[key].shape
        expected_dtype = obs_space[key].dtype
        actual_shape = obs[key].shape
        actual_dtype = obs[key].dtype

        shape_match = expected_shape == actual_shape
        dtype_match = expected_dtype == actual_dtype

        status = "✓" if (shape_match and dtype_match) else "✗"
        print(f"   {status} {key}:")
        print(f"     Expected: shape={expected_shape}, dtype={expected_dtype}")
        print(f"     Actual:   shape={actual_shape}, dtype={actual_dtype}")

        if not shape_match or not dtype_match:
            all_valid = False

    print()

    if not all_valid:
        print("   ✗ Shape 或 dtype 不匹配")
        return False

    # 验证没有 NaN/Inf
    print("4. 验证初始观测没有 NaN/Inf:")
    has_nan_inf = False

    for key, value in obs.items():
        is_finite = np.all(np.isfinite(value))
        status = "✓" if is_finite else "✗"
        print(f"   {status} {key}: np.isfinite().all() = {is_finite}")

        if not is_finite:
            has_nan_inf = True
            nan_count = np.sum(np.isnan(value))
            inf_count = np.sum(np.isinf(value))
            print(f"     NaN count: {nan_count}, Inf count: {inf_count}")

    print()

    if has_nan_inf:
        print("   ✗ 初始观测包含 NaN/Inf")
        return False

    print("   ✓ 初始观测没有 NaN/Inf")
    print()

    return True


def test_observation_consistency(config_path: str, num_steps: int = 100):
    """
    测试观测在整个 episode 中的一致性

    Args:
        config_path: 配置文件路径
        num_steps: 运行步数
    """
    print("=" * 70)
    print("Day9 Step 3: Observation 一致性测试")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print(f"运行步数: {num_steps}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 创建环境
    env = AGCoopEnv(
        config,
        output_dir=None,
        enable_logging=False,
        method="rl",
        planner="none"
    )

    obs = env.reset()

    # 统计
    nan_inf_count = 0
    shape_mismatch_count = 0
    dtype_mismatch_count = 0

    expected_keys = set(env.observation_space.spaces.keys())

    for step in range(num_steps):
        # 随机 action
        action = env.action_space.sample()

        # 执行一步
        obs, reward, done, info = env.step(action)

        # 检查 key
        if set(obs.keys()) != expected_keys:
            print(f"   ✗ Step {step}: Key 不匹配")
            return False

        # 检查 shape 和 dtype
        for key in expected_keys:
            expected_shape = env.observation_space[key].shape
            expected_dtype = env.observation_space[key].dtype

            if obs[key].shape != expected_shape:
                shape_mismatch_count += 1
                print(f"   ✗ Step {step}: {key} shape 不匹配: {obs[key].shape} != {expected_shape}")

            if obs[key].dtype != expected_dtype:
                dtype_mismatch_count += 1
                print(f"   ✗ Step {step}: {key} dtype 不匹配: {obs[key].dtype} != {expected_dtype}")

            # 检查 NaN/Inf
            if not np.all(np.isfinite(obs[key])):
                nan_inf_count += 1
                print(f"   ✗ Step {step}: {key} 包含 NaN/Inf")

        if done:
            print(f"   Episode 结束于 step {step}")
            break

    print()
    print(f"运行完成: {step + 1} 步")
    print(f"  - NaN/Inf 次数: {nan_inf_count}")
    print(f"  - Shape 不匹配次数: {shape_mismatch_count}")
    print(f"  - Dtype 不匹配次数: {dtype_mismatch_count}")
    print()

    if nan_inf_count > 0 or shape_mismatch_count > 0 or dtype_mismatch_count > 0:
        print("   ✗ 一致性测试失败")
        return False

    print("   ✓ 一致性测试通过")
    return True


def test_flatten_wrapper(config_path: str):
    """
    测试 FlattenObservation wrapper

    Args:
        config_path: 配置文件路径
    """
    print("=" * 70)
    print("Day9 Step 3: FlattenObservation Wrapper 测试")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 创建环境
    base_env = AGCoopEnv(
        config,
        output_dir=None,
        enable_logging=False,
        method="rl",
        planner="none"
    )

    # 包装环境
    env = FlattenObservation(base_env)

    print()

    # 1. 检查 observation_space
    print("1. Observation Space 检查:")
    print(f"   observation_space: {env.observation_space}")
    print(f"   shape: {env.observation_space.shape}")
    print(f"   dtype: {env.observation_space.dtype}")
    print()

    # 2. 测试 reset()
    print("2. 测试 reset():")
    obs = env.reset()
    print(f"   obs type: {type(obs)}")
    print(f"   obs shape: {obs.shape}")
    print(f"   obs dtype: {obs.dtype}")
    print(f"   obs range: [{obs.min():.4f}, {obs.max():.4f}]")
    print()

    # 验证 shape 匹配
    if obs.shape != env.observation_space.shape:
        print(f"   ✗ Shape 不匹配: {obs.shape} != {env.observation_space.shape}")
        return False

    # 验证 dtype 匹配
    if obs.dtype != env.observation_space.dtype:
        print(f"   ✗ Dtype 不匹配: {obs.dtype} != {env.observation_space.dtype}")
        return False

    # 验证没有 NaN/Inf
    if not np.all(np.isfinite(obs)):
        print(f"   ✗ 包含 NaN/Inf")
        return False

    print("   ✓ Reset 测试通过")
    print()

    # 3. 测试 step()
    print("3. 测试 step() (10 步):")
    for i in range(10):
        action = env.action_space.sample()
        obs, reward, done, info = env.step(action)

        # 验证
        if obs.shape != env.observation_space.shape:
            print(f"   ✗ Step {i}: Shape 不匹配")
            return False

        if not np.all(np.isfinite(obs)):
            print(f"   ✗ Step {i}: 包含 NaN/Inf")
            return False

        if done:
            print(f"   Episode 结束于 step {i}")
            break

    print(f"   ✓ Step 测试通过 ({i + 1} 步)")
    print()

    return True


def main():
    """主函数"""
    config_path = "configs/day7_baseline.yaml"

    if not Path(config_path).exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    # 测试 1: 基本功能
    success1 = test_observation_space(config_path)

    # 测试 2: 一致性
    success2 = test_observation_consistency(config_path, num_steps=100)

    # 测试 3: Flatten wrapper
    success3 = test_flatten_wrapper(config_path)

    # 总结
    print("=" * 70)
    print("验收总结")
    print("=" * 70)
    print()

    print(f"1. Observation space 基本功能: {'✅' if success1 else '❌'}")
    print(f"2. Observation 一致性测试: {'✅' if success2 else '❌'}")
    print(f"3. FlattenObservation wrapper: {'✅' if success3 else '❌'}")
    print()

    if success1 and success2 and success3:
        print("✅✅✅ Day9 Step 3 验收通过！✅✅✅")
        sys.exit(0)
    else:
        print("❌ Day9 Step 3 验收失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
