#!/usr/bin/env python3
"""
Occupancy Grid → Gazebo SDF World 转换器

读取 MovingAI .map 文件，将 occupied cells 合并为矩形 box，
输出 Gazebo Harmonic 可用的 .sdf world 文件。

用法:
    python scripts/grid_to_world.py maps/map_01.map -o worlds/map_01.sdf
    python scripts/grid_to_world.py maps/map_01.map -o worlds/map_01.sdf --wall-height 1.5
"""

import argparse
import sys
import os
from pathlib import Path
from typing import List, Tuple

import numpy as np


def load_map(file_path: str) -> Tuple[np.ndarray, int, int]:
    """加载 MovingAI .map 文件，返回 (grid, height, width)。"""
    with open(file_path, 'r') as f:
        lines = f.readlines()

    height = width = None
    map_start = None
    for idx, line in enumerate(lines):
        line = line.strip()
        if line.startswith('height'):
            height = int(line.split()[1])
        elif line.startswith('width'):
            width = int(line.split()[1])
        elif line.startswith('map'):
            map_start = idx + 1
            break

    grid = np.zeros((height, width), dtype=np.int8)
    for i in range(height):
        row = lines[map_start + i].strip()
        for j in range(width):
            grid[i, j] = 0 if row[j] == '.' else 1
    return grid, height, width


def merge_rectangles(grid: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """
    贪心矩形合并：将 obstacle cells 合并为尽量少的矩形。

    算法：逐行扫描，对每个未访问的 obstacle cell，
    先向右扩展到最宽，再向下扩展到最高（保持宽度不变）。

    Args:
        grid: shape (H, W), 1=obstacle, 0=free

    Returns:
        矩形列表 [(i_min, j_min, i_max, j_max), ...]
        其中 i_max, j_max 是包含的（inclusive）
    """
    H, W = grid.shape
    visited = np.zeros_like(grid, dtype=bool)
    rects = []

    for i in range(H):
        for j in range(W):
            if grid[i, j] != 1 or visited[i, j]:
                continue

            # 向右扩展
            j_max = j
            while j_max + 1 < W and grid[i, j_max + 1] == 1 and not visited[i, j_max + 1]:
                j_max += 1

            # 向下扩展（保持宽度）
            i_max = i
            while i_max + 1 < H:
                row_ok = True
                for jj in range(j, j_max + 1):
                    if grid[i_max + 1, jj] != 1 or visited[i_max + 1, jj]:
                        row_ok = False
                        break
                if not row_ok:
                    break
                i_max += 1

            # 标记已访问
            visited[i:i_max + 1, j:j_max + 1] = True
            rects.append((i, j, i_max, j_max))

    return rects


def rects_to_sdf(rects: List[Tuple[int, int, int, int]],
                 origin: Tuple[float, float],
                 resolution: float,
                 wall_height: float) -> str:
    """
    将合并后的矩形列表转换为 SDF <model> 片段。

    每个矩形变成一个 static box model，放在地面上（z = wall_height/2）。
    """
    models = []
    for idx, (i_min, j_min, i_max, j_max) in enumerate(rects):
        # 矩形在 cell 坐标中的范围
        # 左下角 cell 的左下角 world 坐标
        x_min = origin[0] + j_min * resolution
        y_min = origin[1] + i_min * resolution
        # 右上角 cell 的右上角 world 坐标
        x_max = origin[0] + (j_max + 1) * resolution
        y_max = origin[1] + (i_max + 1) * resolution

        # box 中心和尺寸
        cx = (x_min + x_max) / 2.0
        cy = (y_min + y_max) / 2.0
        cz = wall_height / 2.0
        sx = x_max - x_min
        sy = y_max - y_min

        models.append(f"""    <model name="wall_{idx}">
      <static>true</static>
      <pose>{cx:.4f} {cy:.4f} {cz:.4f} 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box><size>{sx:.4f} {sy:.4f} {wall_height:.4f}</size></box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box><size>{sx:.4f} {sy:.4f} {wall_height:.4f}</size></box>
          </geometry>
          <material>
            <ambient>0.5 0.5 0.5 1</ambient>
            <diffuse>0.7 0.7 0.7 1</diffuse>
          </material>
        </visual>
      </link>
    </model>""")

    return "\n\n".join(models)


def generate_world_sdf(map_path: str, wall_height: float = 1.5,
                       resolution: float = 0.2) -> str:
    """
    从 .map 文件生成完整的 SDF world 字符串。
    """
    grid, height, width = load_map(map_path)
    origin = (0.0, 0.0)
    rects = merge_rectangles(grid)

    world_w = width * resolution
    world_h = height * resolution

    print(f"Grid: {width}x{height}, resolution={resolution}m")
    print(f"World: {world_w:.1f}m x {world_h:.1f}m")
    print(f"Obstacles: {int(grid.sum())} cells → {len(rects)} merged boxes")

    obstacle_models = rects_to_sdf(rects, origin, resolution, wall_height)

    sdf = f"""<?xml version="1.0" ?>
<sdf version="1.9">
  <world name="grid_world">

    <!-- 物理引擎 -->
    <physics name="1ms" type="ignored">
      <max_step_size>0.001</max_step_size>
      <real_time_factor>1.0</real_time_factor>
    </physics>

    <!-- 必要插件 -->
    <plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
    <plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
    <plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
    <plugin filename="gz-sim-sensors-system" name="gz::sim::systems::Sensors">
      <render_engine>ogre2</render_engine>
    </plugin>
    <plugin filename="gz-sim-contact-system" name="gz::sim::systems::Contact"/>

    <!-- 光照 -->
    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.8 0.8 0.8 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.5 0.1 -0.9</direction>
    </light>

    <!-- 地面 -->
    <model name="ground_plane">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <plane><normal>0 0 1</normal><size>{world_w + 2:.1f} {world_h + 2:.1f}</size></plane>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <plane><normal>0 0 1</normal><size>{world_w + 2:.1f} {world_h + 2:.1f}</size></plane>
          </geometry>
          <material>
            <ambient>0.8 0.8 0.8 1</ambient>
            <diffuse>0.8 0.8 0.8 1</diffuse>
          </material>
        </visual>
      </link>
    </model>

    <!-- 障碍物（从 occupancy grid 合并生成） -->
{obstacle_models}

  </world>
</sdf>
"""
    return sdf


def main():
    parser = argparse.ArgumentParser(description="Occupancy Grid → Gazebo SDF World")
    parser.add_argument("map_file", help=".map 文件路径")
    parser.add_argument("-o", "--output", default=None, help="输出 .sdf 文件路径")
    parser.add_argument("--wall-height", type=float, default=1.5, help="墙体高度 (m)")
    parser.add_argument("--resolution", type=float, default=0.2, help="栅格分辨率 (m/cell)")
    args = parser.parse_args()

    sdf = generate_world_sdf(args.map_file, args.wall_height, args.resolution)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(sdf)
        print(f"Written to {out_path}")
    else:
        print(sdf)


if __name__ == "__main__":
    main()
