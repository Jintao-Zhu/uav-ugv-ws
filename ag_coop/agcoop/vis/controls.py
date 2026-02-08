"""
控制状态和事件处理

处理键盘、鼠标事件，管理播放状态
"""

from dataclasses import dataclass
from typing import Optional
import pygame


@dataclass
class ControlState:
    """控制状态"""
    t: int = 0  # 当前时间步
    paused: bool = False  # 是否暂停
    speed: float = 1.0  # 播放速度倍率
    show_grid: bool = True  # 是否显示网格线
    show_tasks: bool = True  # 是否显示任务
    show_goals: bool = True  # 是否显示目标
    show_candidates: bool = True  # 是否显示候选点（Day8 Step 2）
    max_t: int = 0  # 最大时间步
    _accumulated_steps: float = 0.0  # 累积的步数（用于平滑播放）


def handle_event(event: pygame.event.Event, state: ControlState) -> ControlState:
    """
    处理事件

    Args:
        event: pygame 事件
        state: 当前控制状态

    Returns:
        更新后的控制状态
    """
    if event.type == pygame.KEYDOWN:
        # Space: 暂停/继续
        if event.key == pygame.K_SPACE:
            state.paused = not state.paused

        # R: 重启
        elif event.key == pygame.K_r:
            state.t = 0

        # ↑: 加速
        elif event.key == pygame.K_UP:
            state.speed = min(state.speed * 2, 16.0)

        # ↓: 减速
        elif event.key == pygame.K_DOWN:
            state.speed = max(state.speed / 2, 0.125)

        # →: 单步前进（暂停状态下）
        elif event.key == pygame.K_RIGHT:
            if state.paused:
                state.t = min(state.t + 1, state.max_t - 1)

        # ←: 单步后退（暂停状态下）
        elif event.key == pygame.K_LEFT:
            if state.paused:
                state.t = max(state.t - 1, 0)

        # G: 显示/隐藏网格线
        elif event.key == pygame.K_g:
            state.show_grid = not state.show_grid

        # T: 显示/隐藏任务
        elif event.key == pygame.K_t:
            state.show_tasks = not state.show_tasks

        # O: 显示/隐藏目标
        elif event.key == pygame.K_o:
            state.show_goals = not state.show_goals

        # C: 显示/隐藏候选点（Day8 Step 2）
        elif event.key == pygame.K_c:
            state.show_candidates = not state.show_candidates

    return state


def update_time(state: ControlState, dt_ms: float, fps: float) -> int:
    """
    更新时间步

    Args:
        state: 控制状态
        dt_ms: 距离上次更新的时间（毫秒）
        fps: 目标帧率

    Returns:
        新的时间步
    """
    if state.paused:
        return state.t

    # 计算应该前进多少步
    # speed=1.0 时，每秒前进 fps/10 步（例如 fps=60 时，每秒 6 步）
    # 如果 dt_ms=0（第一帧），使用 1000/fps 作为默认值
    if dt_ms == 0:
        dt_ms = 1000.0 / fps

    steps_per_second = fps / 10.0 * state.speed
    steps_to_advance = (dt_ms / 1000.0) * steps_per_second

    # 使用累积方式，避免因为取整导致的步数丢失
    state._accumulated_steps += steps_to_advance
    steps_to_take = int(state._accumulated_steps)
    state._accumulated_steps -= steps_to_take

    new_t = state.t + steps_to_take
    return min(new_t, state.max_t - 1)
