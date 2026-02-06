"""配置和日志的 I/O 工具。"""
import os
import yaml
import json
import hashlib
from pathlib import Path
from typing import Any, Dict


def compute_file_hash(file_path: str, algorithm: str = 'sha256') -> str:
    """
    计算文件的哈希值。

    Args:
        file_path: 文件路径
        algorithm: 哈希算法（sha256/md5/sha1）

    Returns:
        哈希值（十六进制字符串）
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return "none"

    hash_func = hashlib.new(algorithm)
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)

    return hash_func.hexdigest()[:16]  # 只取前 16 位，足够区分


def ensure_dir(directory: str) -> Path:
    """
    确保目录存在，如果不存在则创建。

    Args:
        directory: 目录路径

    Returns:
        Path 对象
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def atomic_write_json(data: Dict[str, Any], output_path: str) -> None:
    """
    原子写入 JSON 文件（先写临时文件，再重命名）。

    这样可以避免写入过程中断导致文件损坏。

    Args:
        data: 要写入的数据字典
        output_path: 输出文件路径
    """
    output_path = Path(output_path)
    ensure_dir(str(output_path.parent))

    # 临时文件路径
    tmp_path = output_path.with_suffix(output_path.suffix + '.tmp')

    try:
        # 写入临时文件
        with open(tmp_path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 原子重命名（在大多数文件系统上是原子操作）
        os.replace(tmp_path, output_path)

    except Exception as e:
        # 如果出错，清理临时文件
        if tmp_path.exists():
            tmp_path.unlink()
        raise e


def atomic_write_yaml(data: Dict[str, Any], output_path: str) -> None:
    """
    原子写入 YAML 文件（先写临时文件，再重命名）。

    Args:
        data: 要写入的数据字典
        output_path: 输出文件路径
    """
    output_path = Path(output_path)
    ensure_dir(str(output_path.parent))

    # 临时文件路径
    tmp_path = output_path.with_suffix(output_path.suffix + '.tmp')

    try:
        # 写入临时文件
        with open(tmp_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        # 原子重命名
        os.replace(tmp_path, output_path)

    except Exception as e:
        # 如果出错，清理临时文件
        if tmp_path.exists():
            tmp_path.unlink()
        raise e


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
    output_path = ensure_dir(output_dir) / filename
    atomic_write_yaml(config, str(output_path))
    print(f"Resolved config saved to: {output_path}")
