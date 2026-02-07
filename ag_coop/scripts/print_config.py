"""
打印配置文件内容

用于验证配置是否正确加载
"""

import sys
from pathlib import Path
import yaml
import argparse

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def print_config(config_path: str):
    """打印配置文件内容"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    print("=" * 80)
    print("配置文件内容")
    print("=" * 80)
    print(yaml.dump(config, default_flow_style=False, allow_unicode=True))

    # 重点检查 MAPF 配置
    if 'mapf' in config:
        print("\n" + "=" * 80)
        print("MAPF 配置（重点）")
        print("=" * 80)
        mapf_config = config['mapf']
        print(f"  enabled: {mapf_config.get('enabled', 'N/A')}")
        print(f"  H: {mapf_config.get('H', 'N/A')}")
        print(f"  time_budget_ms: {mapf_config.get('time_budget_ms', 'N/A')}")
        print(f"  connectivity: {mapf_config.get('connectivity', 'N/A')}")
        print(f"  priority: {mapf_config.get('priority', 'N/A')}")
    else:
        print("\n⚠️  警告：配置文件中未找到 'mapf' 字段")


def main():
    parser = argparse.ArgumentParser(description='打印配置文件内容')
    parser.add_argument(
        '--config',
        type=str,
        default='configs/default.yaml',
        help='配置文件路径（默认：configs/default.yaml）'
    )
    args = parser.parse_args()

    config_path = project_root / args.config
    if not config_path.exists():
        print(f"✗ 配置文件不存在: {config_path}")
        sys.exit(1)

    print_config(config_path)
    print("\n✓ 配置文件加载成功")


if __name__ == "__main__":
    main()
