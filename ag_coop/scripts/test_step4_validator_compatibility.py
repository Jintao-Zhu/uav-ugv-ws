"""
Day6.5 Step 4: 验证 core.py 输出与 Day6 validator 兼容性

验证：
1. 生成 trace.jsonl 和 metrics.json
2. 运行 validate_day6_outputs.py 验证
3. 运行 check_collisions.py 验证
"""

import sys
import subprocess
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yaml
from agcoop.env.core import AGCoopEnv


def test_validator_compatibility():
    """测试 validator 兼容性"""
    print("=" * 80)
    print("Test: Validator 兼容性")
    print("=" * 80)
    print()

    # 加载配置
    config_path = project_root / "configs" / "default.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # 启用 MAPF
    config['mapf']['enabled'] = True
    config['mapf']['H'] = 40
    config['mapf']['time_budget_ms'] = 300
    config['episode']['horizon_steps'] = 30
    config['episode']['map_path'] = 'maps/map_01.map'

    # 创建环境（启用日志记录）
    output_dir = 'outputs/test_step4_validator'
    env = AGCoopEnv(config, output_dir=output_dir, enable_logging=True)
    print(f"✓ 环境创建成功")
    print(f"  输出目录: {output_dir}")
    print()

    # Reset
    state = env.reset()
    print(f"✓ Reset 成功")
    print(f"  - UGV 数量: {len(state.ugv_positions)}")
    print(f"  - UGV 初始位置: {state.ugv_positions}")
    print()

    # 运行 episode
    print(f"运行 30 步...")
    for i in range(30):
        state, reward, done, info = env.step()

    print(f"✓ Episode 完成")
    print()

    # 关闭环境（保存 metrics）
    env.close()
    print(f"✓ 环境关闭，metrics 已保存")
    print()

    # 验证文件存在
    out_dir = project_root / output_dir
    trace_path = out_dir / 'trace.jsonl'
    metrics_path = out_dir / 'metrics.json'

    assert trace_path.exists(), f"trace.jsonl 不存在: {trace_path}"
    assert metrics_path.exists(), f"metrics.json 不存在: {metrics_path}"
    print(f"✓ 输出文件存在")
    print(f"  - trace.jsonl: {trace_path}")
    print(f"  - metrics.json: {metrics_path}")
    print()

    return str(out_dir)


def run_validators(output_dir: str):
    """运行 Day6 validators"""
    print("=" * 80)
    print("运行 Day6 Validators")
    print("=" * 80)
    print()

    # 1. 运行 validate_day6_outputs.py
    print("1. 运行 validate_day6_outputs.py...")
    print("-" * 80)
    validator_script = project_root / "scripts" / "validate_day6_outputs.py"
    result = subprocess.run(
        [sys.executable, str(validator_script), "--dir", output_dir],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    if result.returncode != 0:
        print(f"✗ validate_day6_outputs.py 失败 (返回码: {result.returncode})")
        return False
    else:
        print(f"✓ validate_day6_outputs.py 通过")
    print()

    # 2. 运行 check_collisions.py
    print("2. 运行 check_collisions.py...")
    print("-" * 80)
    collision_script = project_root / "scripts" / "check_collisions.py"
    trace_path = Path(output_dir) / "trace.jsonl"
    result = subprocess.run(
        [sys.executable, str(collision_script), "--trace", str(trace_path)],
        capture_output=True,
        text=True
    )

    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)

    if result.returncode != 0:
        print(f"✗ check_collisions.py 失败 (返回码: {result.returncode})")
        return False
    else:
        print(f"✓ check_collisions.py 通过")
    print()

    return True


def main():
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "Day6.5 Step 4: Validator 兼容性测试" + " " * 23 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    try:
        # 生成输出
        output_dir = test_validator_compatibility()

        # 运行 validators
        validators_ok = run_validators(output_dir)

        # 总结
        print("=" * 80)
        print("验收结果")
        print("=" * 80)

        if validators_ok:
            print("✓ 所有 validators 通过")
            print()
            print("✓ Day6.5 Step 4 验收通过")
            print()
            print("关键成果:")
            print("  ✓ trace.jsonl 包含 Day6 期望的所有字段")
            print("  ✓ metrics.json 包含 Day6 期望的所有字段")
            print("  ✓ validate_day6_outputs.py 直接通过")
            print("  ✓ check_collisions.py 直接通过")
            print()
        else:
            print("✗ 部分 validators 失败")
            sys.exit(1)

    except AssertionError as e:
        print(f"✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ 异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
