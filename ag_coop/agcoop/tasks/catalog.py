"""
Day8 Step 6.1: 任务目录管理

用于固化任务流，确保不同方法在同一 seed 下使用完全相同的任务集合。
"""

import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np


class TaskCatalog:
    """
    任务目录：预生成所有任务，确保实验公平性

    每个任务包含：
    - task_id: 任务 ID
    - release_t: 释放时间步
    - position: 任务位置 (world 坐标)
    - cell: 任务位置 (cell 坐标)
    - deadline_t: 截止时间步
    """

    def __init__(self):
        self.tasks = []  # List[Dict]

    def generate(
        self,
        horizon_steps: int,
        arrival_rate: float,
        deadline_min: int,
        deadline_max: int,
        grid_map,
        rng: np.random.Generator
    ) -> None:
        """
        预生成整个 episode 的所有任务

        Args:
            horizon_steps: episode 总步数
            arrival_rate: 任务到达率（每步概率）
            deadline_min: 最小 deadline offset
            deadline_max: 最大 deadline offset
            grid_map: GridMap 对象（用于选择任务位置）
            rng: 随机数生成器
        """
        self.tasks = []
        task_id = 0

        # 预先获取所有空闲格子
        free_cells = []
        if grid_map is not None:
            for r in range(grid_map.height):
                for c in range(grid_map.width):
                    if grid_map.is_free(r, c):
                        free_cells.append((r, c))

        # 为每个时间步生成任务
        for t in range(horizon_steps):
            if rng.random() < arrival_rate:
                # 选择任务位置
                if free_cells:
                    cell = free_cells[rng.integers(0, len(free_cells))]
                    position = grid_map.cell_to_world(cell[0], cell[1])
                else:
                    cell = (0, 0)
                    position = (0.0, 0.0)

                # 生成 deadline
                deadline_offset = rng.integers(deadline_min, deadline_max + 1)
                deadline_t = t + deadline_offset

                # 添加任务
                task = {
                    'task_id': int(task_id),
                    'release_t': int(t),
                    'position': [float(position[0]), float(position[1])],
                    'cell': [int(cell[0]), int(cell[1])],
                    'deadline_t': int(deadline_t),
                }
                self.tasks.append(task)
                task_id += 1

    def save(self, filepath: Path) -> None:
        """保存任务目录到 JSON 文件"""
        with open(filepath, 'w') as f:
            json.dump({
                'tasks': self.tasks,
                'total_tasks': len(self.tasks),
            }, f, indent=2)

    def load(self, filepath: Path) -> None:
        """从 JSON 文件加载任务目录"""
        with open(filepath, 'r') as f:
            data = json.load(f)
            self.tasks = data['tasks']

    def get_tasks_at_time(self, t: int) -> List[Dict]:
        """获取在时间 t 释放的所有任务"""
        return [task for task in self.tasks if task['release_t'] == t]

    def get_all_tasks(self) -> List[Dict]:
        """获取所有任务"""
        return self.tasks

    def __len__(self) -> int:
        return len(self.tasks)

    def compute_hash(self) -> str:
        """计算任务目录的哈希值（用于验证一致性）"""
        import hashlib
        # 将任务列表转换为稳定的字符串表示
        task_str = json.dumps(self.tasks, sort_keys=True)
        return hashlib.sha256(task_str.encode()).hexdigest()[:16]


def generate_and_save_catalog(
    output_dir: Path,
    horizon_steps: int,
    arrival_rate: float,
    deadline_min: int,
    deadline_max: int,
    grid_map,
    seed: int,
    dual_hotspot_config: Optional[dict] = None
) -> TaskCatalog:
    """
    生成并保存任务目录

    Args:
        output_dir: 输出目录
        horizon_steps: episode 总步数
        arrival_rate: 任务到达率
        deadline_min: 最小 deadline offset
        deadline_max: 最大 deadline offset
        grid_map: GridMap 对象
        seed: 随机种子
        dual_hotspot_config: 双热点配置（可选，Day8 Step 6.5）

    Returns:
        TaskCatalog 对象
    """
    # 创建独立的 RNG（不影响环境的其他随机过程）
    rng = np.random.default_rng(seed)

    # Day8 Step 6.5: 如果启用双热点，使用双热点生成器
    if dual_hotspot_config and dual_hotspot_config.get('enabled', False):
        from agcoop.tasks.dual_hotspot import DualHotspotTaskGenerator

        hotspot_gen = DualHotspotTaskGenerator(
            grid_map=grid_map,
            hotspot1_center=tuple(dual_hotspot_config['hotspot1_center']),
            hotspot2_center=tuple(dual_hotspot_config['hotspot2_center']),
            hotspot_radius=dual_hotspot_config.get('hotspot_radius', 3),
            split_ratio=dual_hotspot_config.get('split_ratio', 0.5)
        )

        tasks = hotspot_gen.generate_catalog(
            horizon_steps=horizon_steps,
            arrival_rate=arrival_rate,
            deadline_min=deadline_min,
            deadline_max=deadline_max,
            seed=seed
        )

        catalog = TaskCatalog()
        catalog.tasks = tasks
    else:
        # 原逻辑：均匀随机生成
        catalog = TaskCatalog()
        catalog.generate(
            horizon_steps=horizon_steps,
            arrival_rate=arrival_rate,
            deadline_min=deadline_min,
            deadline_max=deadline_max,
            grid_map=grid_map,
            rng=rng
        )

    # 保存到文件
    output_dir.mkdir(parents=True, exist_ok=True)
    catalog.save(output_dir / 'tasks_catalog.json')

    return catalog


def load_catalog(output_dir: Path) -> Optional[TaskCatalog]:
    """
    加载任务目录

    Args:
        output_dir: 输出目录

    Returns:
        TaskCatalog 对象，如果文件不存在则返回 None
    """
    catalog_path = output_dir / 'tasks_catalog.json'
    if not catalog_path.exists():
        return None

    catalog = TaskCatalog()
    catalog.load(catalog_path)
    return catalog
