"""
IO 工具：加载运行数据

从 outputs/<run_dir>/ 加载配置、trace、metrics 等
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
import json


class RunData:
    """运行数据容器"""

    def __init__(self, run_dir: str):
        self.run_dir = Path(run_dir)
        self.config: Dict[str, Any] = {}
        self.init: Dict[str, Any] = {}
        self.metrics: Dict[str, Any] = {}
        self.trace: List[Dict[str, Any]] = []

    def __repr__(self):
        return (
            f"RunData(run_dir={self.run_dir}, "
            f"steps={len(self.trace)}, "
            f"n_agents={self.init.get('n_agents', 0)})"
        )


def load_run(run_dir: str) -> RunData:
    """
    加载运行数据

    Args:
        run_dir: 输出目录路径（如 outputs/day7_greedy_seed0）

    Returns:
        RunData 对象
    """
    run_data = RunData(run_dir)
    run_path = Path(run_dir)

    # 加载 config_resolved.yaml
    config_file = run_path / "config_resolved.yaml"
    if config_file.exists():
        with open(config_file, 'r') as f:
            run_data.config = yaml.safe_load(f)
    else:
        raise FileNotFoundError(f"Config file not found: {config_file}")

    # 加载 init.json
    init_file = run_path / "init.json"
    if init_file.exists():
        with open(init_file, 'r') as f:
            run_data.init = json.load(f)

    # 加载 metrics.json
    metrics_file = run_path / "metrics.json"
    if metrics_file.exists():
        with open(metrics_file, 'r') as f:
            run_data.metrics = json.load(f)

    # 加载 trace.jsonl
    trace_file = run_path / "trace.jsonl"
    if trace_file.exists():
        with open(trace_file, 'r') as f:
            for line in f:
                if line.strip():
                    run_data.trace.append(json.loads(line))
    else:
        raise FileNotFoundError(f"Trace file not found: {trace_file}")

    return run_data


class GridMap:
    """网格地图"""

    def __init__(self, width: int, height: int, grid: List[List[bool]]):
        self.width = width
        self.height = height
        self.grid = grid  # grid[i][j] = True 表示可通行

    def is_free(self, i: int, j: int) -> bool:
        """检查格子是否可通行"""
        if 0 <= i < self.height and 0 <= j < self.width:
            return self.grid[i][j]
        return False

    def __repr__(self):
        return f"GridMap(width={self.width}, height={self.height})"


def load_grid_map(map_path: str) -> Optional[GridMap]:
    """
    加载网格地图（MovingAI 格式）

    Args:
        map_path: 地图文件路径

    Returns:
        GridMap 对象，如果文件不存在返回 None
    """
    map_file = Path(map_path)
    if not map_file.exists():
        return None

    with open(map_file, 'r') as f:
        lines = f.readlines()

    # 解析头部
    header = {}
    for i, line in enumerate(lines[:4]):
        if line.strip():
            parts = line.strip().split()
            if len(parts) == 2:
                key, value = parts
                header[key] = value if key == 'type' else int(value)

    width = header['width']
    height = header['height']

    # 解析地图
    grid = []
    for line in lines[4:]:
        if line.strip():
            row = []
            for char in line.strip():
                # '.' 表示可通行，'@' 表示障碍
                row.append(char == '.')
            grid.append(row)

    return GridMap(width, height, grid)
