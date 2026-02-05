"""配置和日志的 I/O 工具。"""
import yaml
from pathlib import Path
from typing import Any, Dict


def load_config(config_path: str) -> Dict[str, Any]:
    """
    从 YAML 文件加载配置。

    Args:
        config_path: YAML 配置文件路径

    Returns:
        配置字典
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def save_resolved_config(config: Dict[str, Any], output_dir: str, filename: str = "config_resolved.yaml") -> None:
    """
    保存最终解析后的配置到 YAML 文件，用于实验复现。

    Args:
        config: 解析后的配置字典
        output_dir: 保存配置的目录
        filename: 输出文件名（默认：config_resolved.yaml）
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    config_file = output_path / filename
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"Resolved config saved to: {config_file}")
