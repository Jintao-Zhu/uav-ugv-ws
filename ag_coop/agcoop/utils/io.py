"""I/O utilities for configuration and logging."""
import yaml
from pathlib import Path
from typing import Any, Dict


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to YAML config file

    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def save_resolved_config(config: Dict[str, Any], output_dir: str, filename: str = "config_resolved.yaml") -> None:
    """
    Save the resolved configuration to a YAML file for reproducibility.

    Args:
        config: Resolved configuration dictionary
        output_dir: Directory to save the config
        filename: Name of the output file (default: config_resolved.yaml)
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    config_file = output_path / filename
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"Resolved config saved to: {config_file}")
