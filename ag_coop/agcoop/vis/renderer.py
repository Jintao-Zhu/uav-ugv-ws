"""
渲染器

使用 pygame 绘制地图、UGV、任务、HUD 等
"""

from typing import List, Tuple, Dict, Any, Optional
import pygame
from .io_runs import GridMap
from .task_tracker import Task, TaskTracker


# 颜色定义
COLOR_BG = (240, 240, 240)  # 背景
COLOR_GRID = (200, 200, 200)  # 网格线
COLOR_OBSTACLE = (60, 60, 60)  # 障碍物
COLOR_FREE = (255, 255, 255)  # 可通行区域
COLOR_TEXT = (20, 20, 20)  # 文本
COLOR_HUD_BG = (250, 250, 250)  # HUD 背景

# UGV 颜色（不同 agent 不同颜色）
UGV_COLORS = [
    (255, 100, 100),  # 红色
    (100, 150, 255),  # 蓝色
    (100, 200, 100),  # 绿色
    (255, 200, 100),  # 橙色
    (200, 100, 255),  # 紫色
    (100, 255, 200),  # 青色
]

# 任务颜色
COLOR_TASK_LOW = (100, 255, 100)  # 不紧急（绿色）
COLOR_TASK_HIGH = (255, 100, 100)  # 紧急（红色）
COLOR_TASK_COMPLETED = (150, 150, 255)  # 已完成（蓝色）
COLOR_TASK_MISSED = (150, 150, 150)  # 已过期（灰色）

# 目标颜色
COLOR_GOAL = (255, 200, 50)  # 目标点（黄色）

# 候选点颜色
COLOR_CANDIDATE = (100, 200, 255)  # 候选中继点（浅蓝色）


class Renderer:
    """渲染器"""

    def __init__(self, width: int, height: int, cell_px: int, grid_map: Optional[GridMap] = None):
        """
        初始化渲染器

        Args:
            width: 网格宽度
            height: 网格高度
            cell_px: 每个格子的像素大小
            grid_map: 网格地图（可选）
        """
        self.width = width
        self.height = height
        self.cell_px = cell_px
        self.grid_map = grid_map

        # 计算窗口尺寸（地图 + HUD）
        self.map_width_px = width * cell_px
        self.map_height_px = height * cell_px
        self.hud_height = 120
        self.window_width = self.map_width_px
        self.window_height = self.map_height_px + self.hud_height

        # 初始化 pygame
        pygame.init()
        self.screen = pygame.display.set_mode((self.window_width, self.window_height))
        pygame.display.set_caption("AGCoop Visualizer")

        # 字体
        self.font_small = pygame.font.Font(None, 20)
        self.font_medium = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 32)

    def draw_grid(self, show_grid_lines: bool = True):
        """绘制网格地图"""
        # 绘制格子
        for i in range(self.height):
            for j in range(self.width):
                x = j * self.cell_px
                y = i * self.cell_px

                # 判断是否可通行
                if self.grid_map and not self.grid_map.is_free(i, j):
                    color = COLOR_OBSTACLE
                else:
                    color = COLOR_FREE

                pygame.draw.rect(self.screen, color, (x, y, self.cell_px, self.cell_px))

        # 绘制网格线
        if show_grid_lines:
            for i in range(self.height + 1):
                y = i * self.cell_px
                pygame.draw.line(self.screen, COLOR_GRID, (0, y), (self.map_width_px, y), 1)
            for j in range(self.width + 1):
                x = j * self.cell_px
                pygame.draw.line(self.screen, COLOR_GRID, (x, 0), (x, self.map_height_px), 1)

    def draw_tasks(self, task_tracker: Optional[TaskTracker], t: int):
        """绘制任务"""
        if not task_tracker:
            return

        # 绘制活跃任务
        active_tasks = task_tracker.get_active_tasks(t)
        for task in active_tasks:
            urgency = task_tracker.get_task_color_urgency(task, t)
            color = self._interpolate_color(COLOR_TASK_LOW, COLOR_TASK_HIGH, urgency)
            self._draw_task_marker(task.cell, color, size=0.6)

        # 绘制最近完成的任务（显示 3 步）
        completed_tasks = task_tracker.get_completed_tasks(t, window=3)
        for task in completed_tasks:
            self._draw_task_marker(task.cell, COLOR_TASK_COMPLETED, size=0.5, alpha=150)

        # 绘制过期任务
        missed_tasks = task_tracker.get_missed_tasks(t)
        for task in missed_tasks:
            self._draw_task_marker(task.cell, COLOR_TASK_MISSED, size=0.4, alpha=100)

    def _draw_task_marker(self, cell: Tuple[int, int], color: Tuple[int, int, int],
                          size: float = 0.6, alpha: int = 255):
        """绘制任务标记（方形，带边框和阴影）"""
        i, j = cell
        center_x = int((j + 0.5) * self.cell_px)
        center_y = int((i + 0.5) * self.cell_px)
        half_size = int(self.cell_px * size / 2)

        # 阴影
        shadow_offset = 2
        shadow_surf = pygame.Surface((half_size * 2 + 10, half_size * 2 + 10), pygame.SRCALPHA)
        pygame.draw.rect(shadow_surf, (0, 0, 0, 60),
                        (shadow_offset, shadow_offset, half_size * 2, half_size * 2))
        self.screen.blit(shadow_surf, (center_x - half_size - 5, center_y - half_size - 5))

        # 创建带透明度的 surface
        surf = pygame.Surface((half_size * 2, half_size * 2), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*color, alpha), (0, 0, half_size * 2, half_size * 2))

        # 边框
        border_color = tuple(max(0, c - 50) for c in color)
        pygame.draw.rect(surf, (*border_color, alpha), (0, 0, half_size * 2, half_size * 2), 2)

        self.screen.blit(surf, (center_x - half_size, center_y - half_size))

    def draw_ugvs(self, ugv_positions: List[List[float]], ugv_goals: Optional[Dict[str, List[int]]] = None,
                   grid_map: Optional[GridMap] = None, show_paths: bool = True, uav_carrier_id: Optional[int] = None):
        """
        绘制 UGV

        Args:
            ugv_positions: UGV 世界坐标 [[x, y], ...]
            ugv_goals: UGV 目标点 {agent_id: [i, j], ...}
            grid_map: 网格地图（用于坐标转换）
            show_paths: 是否显示规划路径
            uav_carrier_id: UAV 所在的 UGV ID（如果 UAV onboard）
        """
        resolution = 0.2
        origin_x = 0.0
        origin_y = 0.0

        for i, pos in enumerate(ugv_positions):
            color = UGV_COLORS[i % len(UGV_COLORS)]

            # 转换为格子坐标
            cell_j = int((pos[0] - origin_x) / resolution)
            cell_i = int((pos[1] - origin_y) / resolution)

            # 绘制规划路径（从当前位置到目标）
            if show_paths and ugv_goals and str(i) in ugv_goals:
                goal = ugv_goals[str(i)]
                goal_i, goal_j = goal

                # 当前位置的屏幕坐标
                current_x = int((cell_j + 0.5) * self.cell_px)
                current_y = int((cell_i + 0.5) * self.cell_px)

                # 目标位置的屏幕坐标
                goal_x = int((goal_j + 0.5) * self.cell_px)
                goal_y = int((goal_i + 0.5) * self.cell_px)

                # 绘制路径线（虚线效果）
                path_color = tuple(int(c * 0.7) for c in color)
                line_surf = pygame.Surface((self.map_width_px, self.map_height_px), pygame.SRCALPHA)

                # 绘制虚线
                dx = goal_x - current_x
                dy = goal_y - current_y
                distance = max(abs(dx), abs(dy))

                if distance > 0:
                    dash_length = 10
                    gap_length = 5
                    total_length = (dash_length + gap_length)

                    for d in range(0, int(distance), total_length):
                        t1 = d / distance
                        t2 = min((d + dash_length) / distance, 1.0)

                        x1 = int(current_x + dx * t1)
                        y1 = int(current_y + dy * t1)
                        x2 = int(current_x + dx * t2)
                        y2 = int(current_y + dy * t2)

                        pygame.draw.line(line_surf, (*path_color, 150), (x1, y1), (x2, y2), 2)

                self.screen.blit(line_surf, (0, 0))

            # 绘制圆形（带阴影效果）
            center_x = int((cell_j + 0.5) * self.cell_px)
            center_y = int((cell_i + 0.5) * self.cell_px)
            radius = int(self.cell_px * 0.4)

            # 阴影
            shadow_offset = 2
            shadow_surf = pygame.Surface((radius * 2 + 10, radius * 2 + 10), pygame.SRCALPHA)
            pygame.draw.circle(shadow_surf, (0, 0, 0, 80),
                             (radius + 5 + shadow_offset, radius + 5 + shadow_offset), radius)
            self.screen.blit(shadow_surf, (center_x - radius - 5, center_y - radius - 5))

            # 主体
            pygame.draw.circle(self.screen, color, (center_x, center_y), radius)
            pygame.draw.circle(self.screen, (0, 0, 0), (center_x, center_y), radius, 2)

            # 高光
            highlight_offset = int(radius * 0.3)
            highlight_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(highlight_surf, (255, 255, 255, 100),
                             (radius - highlight_offset, radius - highlight_offset),
                             int(radius * 0.3))
            self.screen.blit(highlight_surf, (center_x - radius, center_y - radius))

            # 绘制 ID
            text = self.font_small.render(str(i), True, (255, 255, 255))
            text_rect = text.get_rect(center=(center_x, center_y))
            self.screen.blit(text, text_rect)

            # 如果 UAV onboard 在这个 UGV 上，绘制 UAV
            if uav_carrier_id is not None and i == uav_carrier_id:
                # UAV 绘制在 UGV 上方偏右
                uav_offset_x = int(radius * 0.8)
                uav_offset_y = -int(radius * 0.8)
                uav_x = center_x + uav_offset_x
                uav_y = center_y + uav_offset_y
                uav_size = int(radius * 0.5)

                # UAV 三角形（表示无人机）
                uav_points = [
                    (uav_x, uav_y - uav_size),  # 顶点
                    (uav_x - uav_size, uav_y + uav_size),  # 左下
                    (uav_x + uav_size, uav_y + uav_size),  # 右下
                ]

                # UAV 主体（黄色三角形）
                pygame.draw.polygon(self.screen, (255, 200, 0), uav_points)
                pygame.draw.polygon(self.screen, (0, 0, 0), uav_points, 2)

    def draw_goals(self, ugv_goals: Dict[str, List[int]]):
        """绘制 UGV 目标点"""
        for agent_id, goal in ugv_goals.items():
            i, j = goal
            center_x = int((j + 0.5) * self.cell_px)
            center_y = int((i + 0.5) * self.cell_px)
            size = int(self.cell_px * 0.3)

            # 绘制 X 标记
            pygame.draw.line(self.screen, COLOR_GOAL,
                           (center_x - size, center_y - size),
                           (center_x + size, center_y + size), 3)
            pygame.draw.line(self.screen, COLOR_GOAL,
                           (center_x + size, center_y - size),
                           (center_x - size, center_y + size), 3)

    def draw_candidates(self, candidate_relays: List[List[int]]):
        """
        绘制候选中继点

        Args:
            candidate_relays: 候选点列表 [[i, j], ...]
        """
        for cell in candidate_relays:
            i, j = cell
            center_x = int((j + 0.5) * self.cell_px)
            center_y = int((i + 0.5) * self.cell_px)
            radius = int(self.cell_px * 0.25)

            # 绘制空心圆
            pygame.draw.circle(self.screen, COLOR_CANDIDATE, (center_x, center_y), radius, 2)

            # 绘制中心点
            pygame.draw.circle(self.screen, COLOR_CANDIDATE, (center_x, center_y), 2)

    def draw_hud(self, t: int, max_t: int, speed: float, paused: bool,
                 step_info: Dict[str, Any], metrics: Dict[str, Any]):
        """绘制 HUD（顶部信息栏）"""
        # HUD 背景
        hud_y = self.map_height_px
        pygame.draw.rect(self.screen, COLOR_HUD_BG, (0, hud_y, self.window_width, self.hud_height))
        pygame.draw.line(self.screen, COLOR_GRID, (0, hud_y), (self.window_width, hud_y), 2)

        # 第一行：时间、速度、状态
        y_offset = hud_y + 10
        line1_parts = [
            f"t: {t}/{max_t}",
            f"Speed: {speed:.2f}x",
            "PAUSED" if paused else "PLAYING",
        ]
        line1_text = "  |  ".join(line1_parts)
        text_surf = self.font_medium.render(line1_text, True, COLOR_TEXT)
        self.screen.blit(text_surf, (10, y_offset))

        # 第二行：决策步、MAPF 信息
        y_offset += 30
        decision_step = step_info.get('decision_step', False)
        mapf_called = step_info.get('mapf_called', False)
        mapf_success = step_info.get('mapf_success', None)
        mapf_time = step_info.get('mapf_plan_time_ms', None)

        line2_parts = []
        if decision_step:
            line2_parts.append("DECISION STEP")
        if mapf_called:
            status = "SUCCESS" if mapf_success else "TIMEOUT/FAIL"
            time_str = f"{mapf_time:.2f}ms" if mapf_time else "N/A"
            line2_parts.append(f"MAPF: {status} ({time_str})")

        if line2_parts:
            line2_text = "  |  ".join(line2_parts)
            text_surf = self.font_small.render(line2_text, True, COLOR_TEXT)
            self.screen.blit(text_surf, (10, y_offset))

        # 第三行：通信、任务统计
        y_offset += 25
        outage = step_info.get('outage', 0)
        snr_best = step_info.get('snr_best', 0)
        num_active_tasks = step_info.get('num_active_tasks', 0)
        task_completed_ids = step_info.get('task_completed_ids', [])

        line3_parts = [
            f"Outage: {outage}",
            f"SNR: {snr_best:.1f}dB",
            f"Active Tasks: {num_active_tasks}",
        ]
        if task_completed_ids:
            line3_parts.append(f"Completed: {task_completed_ids}")

        line3_text = "  |  ".join(line3_parts)
        text_surf = self.font_small.render(line3_text, True, COLOR_TEXT)
        self.screen.blit(text_surf, (10, y_offset))

        # 第四行：快捷键提示
        y_offset += 25
        hints = "Space: Pause  |  ↑↓: Speed  |  ←→: Step  |  R: Restart  |  G: Grid  |  T: Tasks  |  O: Goals"
        text_surf = self.font_small.render(hints, True, (100, 100, 100))
        self.screen.blit(text_surf, (10, y_offset))

    def _interpolate_color(self, color1: Tuple[int, int, int],
                          color2: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
        """颜色插值"""
        r = int(color1[0] * (1 - t) + color2[0] * t)
        g = int(color1[1] * (1 - t) + color2[1] * t)
        b = int(color1[2] * (1 - t) + color2[2] * t)
        return (r, g, b)

    def clear(self):
        """清空屏幕"""
        self.screen.fill(COLOR_BG)

    def flip(self):
        """刷新显示"""
        pygame.display.flip()

    def close(self):
        """关闭渲染器"""
        pygame.quit()
