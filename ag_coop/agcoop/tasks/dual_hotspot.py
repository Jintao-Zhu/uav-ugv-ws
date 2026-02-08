"""
Day8 Step 6.5: 双热点任务生成器

构造"任务-通信冲突"场景：
- 两个相距很远的热点（左上 + 右下）
- 任务以 50/50 概率落在两个热点附近
- 制造"想拿高吞吐 → 必须分散；分散 → 通信必变差"的冲突
"""

import numpy as np
from typing import List, Tuple
from pathlib import Path


class DualHotspotTaskGenerator:
    """
    双热点任务生成器

    在地图的两个对角位置生成任务热点，制造任务-通信冲突。
    """

    def __init__(
        self,
        grid_map,
        hotspot1_center: Tuple[int, int],
        hotspot2_center: Tuple[int, int],
        hotspot_radius: int = 3,
        split_ratio: float = 0.5
    ):
        """
        初始化双热点生成器

        Args:
            grid_map: GridMap 对象
            hotspot1_center: 热点1中心 (row, col)
            hotspot2_center: 热点2中心 (row, col)
            hotspot_radius: 热点半径（格子数）
            split_ratio: 热点1的任务比例（0.5 表示 50/50）
        """
        self.grid_map = grid_map
        self.hotspot1_center = hotspot1_center
        self.hotspot2_center = hotspot2_center
        self.hotspot_radius = hotspot_radius
        self.split_ratio = split_ratio

        # 预计算每个热点的可用格子
        self.hotspot1_cells = self._get_hotspot_cells(hotspot1_center)
        self.hotspot2_cells = self._get_hotspot_cells(hotspot2_center)

        print(f"双热点任务生成器初始化:")
        print(f"  热点1: {hotspot1_center}, {len(self.hotspot1_cells)} 个可用格子")
        print(f"  热点2: {hotspot2_center}, {len(self.hotspot2_cells)} 个可用格子")
        print(f"  分配比例: {split_ratio:.0%} / {1-split_ratio:.0%}")

    def _get_hotspot_cells(self, center: Tuple[int, int]) -> List[Tuple[int, int]]:
        """获取热点范围内的所有可用格子"""
        cells = []
        center_r, center_c = center

        for r in range(max(0, center_r - self.hotspot_radius),
                      min(self.grid_map.height, center_r + self.hotspot_radius + 1)):
            for c in range(max(0, center_c - self.hotspot_radius),
                          min(self.grid_map.width, center_c + self.hotspot_radius + 1)):
                # 检查是否在半径内（曼哈顿距离）
                dist = abs(r - center_r) + abs(c - center_c)
                if dist <= self.hotspot_radius and self.grid_map.is_free(r, c):
                    cells.append((r, c))

        return cells

    def generate_task_position(self, rng: np.random.Generator) -> Tuple[float, float]:
        """
        生成一个任务位置（world 坐标）

        Args:
            rng: 随机数生成器

        Returns:
            (x, y) world 坐标
        """
        # 选择热点
        if rng.random() < self.split_ratio:
            # 热点1
            if not self.hotspot1_cells:
                # 如果热点1没有可用格子，回退到热点2
                cells = self.hotspot2_cells
            else:
                cells = self.hotspot1_cells
        else:
            # 热点2
            if not self.hotspot2_cells:
                # 如果热点2没有可用格子，回退到热点1
                cells = self.hotspot1_cells
            else:
                cells = self.hotspot2_cells

        if not cells:
            # 如果两个热点都没有可用格子，返回地图中心
            return (self.grid_map.width * self.grid_map.cell_size / 2,
                   self.grid_map.height * self.grid_map.cell_size / 2)

        # 从热点中随机选择一个格子
        cell = cells[rng.integers(0, len(cells))]

        # 转换为 world 坐标
        world_pos = self.grid_map.cell_to_world(cell[0], cell[1])

        return world_pos

    def generate_catalog(
        self,
        horizon_steps: int,
        arrival_rate: float,
        deadline_min: int,
        deadline_max: int,
        seed: int
    ) -> List[dict]:
        """
        生成双热点任务目录

        Args:
            horizon_steps: episode 总步数
            arrival_rate: 任务到达率
            deadline_min: 最小 deadline offset
            deadline_max: 最大 deadline offset
            seed: 随机种子

        Returns:
            任务列表
        """
        rng = np.random.default_rng(seed)
        tasks = []
        task_id = 0

        for t in range(horizon_steps):
            if rng.random() < arrival_rate:
                # 生成任务位置
                position = self.generate_task_position(rng)
                cell = self.grid_map.world_to_cell(position[0], position[1])

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
                tasks.append(task)
                task_id += 1

        return tasks


def create_dual_hotspot_config(base_config: dict, map_size: Tuple[int, int] = (20, 20)) -> dict:
    """
    创建双热点场景配置

    Args:
        base_config: 基础配置
        map_size: 地图大小 (height, width)

    Returns:
        修改后的配置
    """
    import copy
    config = copy.deepcopy(base_config)

    # 设置双热点参数
    height, width = map_size
    config['dual_hotspot'] = {
        'enabled': True,
        'hotspot1_center': [2, 2],  # 左上角
        'hotspot2_center': [height - 3, width - 3],  # 右下角
        'hotspot_radius': 3,
        'split_ratio': 0.5,
    }

    return config
