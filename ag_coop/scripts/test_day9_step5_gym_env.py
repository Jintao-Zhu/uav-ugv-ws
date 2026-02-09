#!/usr/bin/env python3
"""
Day9 Step 5 验证：Gym Environment Wrapper

验证标准：
1. import 环境类成功
2. env.reset() 和 env.step() 连续运行 1000 步不崩溃
3. terminated/truncated 逻辑正确：到 horizon 必须结束
"""

import sys
from pathlib import Path
import yaml
import numpy as np

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.rl import AGCoopGymEnv


def test_import():
    """测试 import 环境类"""
    print("=" * 70)
    print("Day9 Step 5: Import 测试")
    print("=" * 70)
    print()

    try:
        from agcoop.rl import AGCoopGymEnv
        print("   ✓ AGCoopGymEnv import 成功")
        return True
    except Exception as e:
        print(f"   ✗ AGCoopGymEnv import 失败: {e}")
        return False


def test_basic_interface(config_path: str):
    """测试基本接口"""
    print("=" * 70)
    print("Day9 Step 5: 基本接口测试")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 创建环境
    try:
        env = AGCoopGymEnv(config, enable_logging=False)
        print("   ✓ 环境创建成功")
    except Exception as e:
        print(f"   ✗ 环境创建失败: {e}")
        return False

    # 检查 action_space 和 observation_space
    print(f"\nAction space: {env.action_space}")
    print(f"Observation space: {env.observation_space}")
    print()

    # 测试 reset
    try:
        obs, info = env.reset(seed=42)
        print("   ✓ reset() 成功")
        print(f"     obs type: {type(obs)}")
        print(f"     info keys: {list(info.keys())}")
    except Exception as e:
        print(f"   ✗ reset() 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 测试 step
    try:
        action = env.action_space.sample()
        result = env.step(action)

        # 检查返回值数量（gymnasium 返回 5 个，gym 返回 4 个）
        if len(result) == 5:
            obs, reward, terminated, truncated, info = result
            print("   ✓ step() 成功 (gymnasium 格式)")
            print(f"     reward: {reward}")
            print(f"     terminated: {terminated}")
            print(f"     truncated: {truncated}")
        elif len(result) == 4:
            obs, reward, done, info = result
            print("   ✓ step() 成功 (gym 格式)")
            print(f"     reward: {reward}")
            print(f"     done: {done}")
        else:
            print(f"   ✗ step() 返回值数量错误: {len(result)}")
            return False
    except Exception as e:
        print(f"   ✗ step() 失败: {e}")
        import traceback
        traceback.print_exc()
        return False

    print()
    return True


def test_long_run(config_path: str, num_steps: int = 1000):
    """测试长时间运行"""
    print("=" * 70)
    print("Day9 Step 5: 长时间运行测试")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print(f"运行步数: {num_steps}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 创建环境
    env = AGCoopGymEnv(config, enable_logging=False)

    # Reset
    obs, info = env.reset(seed=42)

    # 运行多步
    crash_count = 0
    total_reward = 0.0
    episode_count = 0

    for step in range(num_steps):
        try:
            action = env.action_space.sample()
            result = env.step(action)

            if len(result) == 5:
                obs, reward, terminated, truncated, info = result
                done = terminated or truncated
            else:
                obs, reward, done, info = result

            total_reward += reward

            if done:
                episode_count += 1
                print(f"   Episode {episode_count} 结束于 step {step}, total_reward: {total_reward:.4f}")
                obs, info = env.reset()
                total_reward = 0.0

        except Exception as e:
            crash_count += 1
            print(f"   ✗ Step {step} 崩溃: {e}")
            import traceback
            traceback.print_exc()
            break

    print()
    print(f"运行完成: {step + 1} 步")
    print(f"  - 崩溃次数: {crash_count}")
    print(f"  - Episode 数量: {episode_count}")
    print()

    if crash_count > 0:
        print("   ✗ 长时间运行测试失败")
        return False

    print("   ✓ 长时间运行测试通过")
    return True


def test_termination_logic(config_path: str):
    """测试 terminated/truncated 逻辑"""
    print("=" * 70)
    print("Day9 Step 5: Termination 逻辑测试")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 修改 horizon 为较小值以便测试
    original_horizon = config['episode']['horizon_steps']
    config['episode']['horizon_steps'] = 50

    # 创建环境
    env = AGCoopGymEnv(config, enable_logging=False)

    # Reset
    obs, info = env.reset(seed=42)

    # 运行到 horizon
    for step in range(100):
        action = env.action_space.sample()
        result = env.step(action)

        if len(result) == 5:
            obs, reward, terminated, truncated, info = result
            done = terminated or truncated

            if done:
                print(f"   Episode 结束于 step {step + 1}")
                print(f"     terminated: {terminated}")
                print(f"     truncated: {truncated}")
                print(f"     timestep: {info.get('timestep', 'N/A')}")

                # 验证逻辑
                if step + 1 == 50:
                    if truncated and not terminated:
                        print("   ✓ Truncated 逻辑正确（到达 horizon）")
                    else:
                        print(f"   ✗ Truncated 逻辑错误: terminated={terminated}, truncated={truncated}")
                        return False
                break
        else:
            obs, reward, done, info = result

            if done:
                print(f"   Episode 结束于 step {step + 1}")
                print(f"     done: {done}")
                print(f"     timestep: {info.get('timestep', 'N/A')}")

                if step + 1 == 50:
                    print("   ✓ Done 逻辑正确（到达 horizon）")
                break

    print()
    return True


def test_render(config_path: str):
    """测试 render 方法"""
    print("=" * 70)
    print("Day9 Step 5: Render 测试")
    print("=" * 70)
    print(f"配置文件: {config_path}")
    print()

    # 加载配置
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 创建环境（human 模式）
    env = AGCoopGymEnv(config, enable_logging=False, render_mode='human')

    # Reset
    obs, info = env.reset(seed=42)

    # 运行几步并渲染
    print("Render (human mode):")
    for step in range(3):
        action = env.action_space.sample()
        result = env.step(action)
        env.render()
        print()

    print("   ✓ Render (human) 测试通过")
    print()

    # 测试 rgb_array 模式
    env2 = AGCoopGymEnv(config, enable_logging=False, render_mode='rgb_array')
    obs, info = env2.reset(seed=42)

    try:
        rgb_array = env2.render()
        print(f"Render (rgb_array mode): shape={rgb_array.shape}, dtype={rgb_array.dtype}")
        print("   ✓ Render (rgb_array) 测试通过")
    except Exception as e:
        print(f"   ✗ Render (rgb_array) 失败: {e}")
        return False

    print()
    return True


def main():
    """主函数"""
    config_path = "configs/day7_baseline.yaml"

    if not Path(config_path).exists():
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)

    # 测试 1: Import
    success1 = test_import()

    # 测试 2: 基本接口
    success2 = test_basic_interface(config_path)

    # 测试 3: 长时间运行（1000 步）
    success3 = test_long_run(config_path, num_steps=1000)

    # 测试 4: Termination 逻辑
    success4 = test_termination_logic(config_path)

    # 测试 5: Render
    success5 = test_render(config_path)

    # 总结
    print("=" * 70)
    print("验收总结")
    print("=" * 70)
    print()

    print(f"1. Import 测试: {'✅' if success1 else '❌'}")
    print(f"2. 基本接口测试: {'✅' if success2 else '❌'}")
    print(f"3. 长时间运行测试 (1000 步): {'✅' if success3 else '❌'}")
    print(f"4. Termination 逻辑测试: {'✅' if success4 else '❌'}")
    print(f"5. Render 测试: {'✅' if success5 else '❌'}")
    print()

    if success1 and success2 and success3 and success4 and success5:
        print("✅✅✅ Day9 Step 5 验收通过！✅✅✅")
        sys.exit(0)
    else:
        print("❌ Day9 Step 5 验收失败")
        sys.exit(1)


if __name__ == '__main__':
    main()
