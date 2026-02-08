#!/usr/bin/env python3
"""
AGCoop Visualizer

离线回放 AGCoop 实验结果

用法:
    python scripts/visualize.py --run outputs/day7_greedy_seed0
    python scripts/visualize.py --run outputs/day6_5_core_normal_seed0 --fps 30 --cell-px 40
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pygame
from agcoop.vis import (
    load_run, load_grid_map, load_tasks,
    Renderer, ControlState, handle_event, update_time
)


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="AGCoop Visualizer")
    parser.add_argument('--run', type=str, required=True,
                       help='运行目录路径（如 outputs/day7_greedy_seed0）')
    parser.add_argument('--fps', type=int, default=60,
                       help='目标帧率（默认 60）')
    parser.add_argument('--cell-px', type=int, default=30,
                       help='每个格子的像素大小（默认 30）')
    parser.add_argument('--start-t', type=int, default=0,
                       help='起始时间步（默认 0）')
    return parser.parse_args()


def run_visualizer(run_dir: str, fps: int = 60, cell_px: int = 30, start_t: int = 0):
    """
    运行可视化器

    Args:
        run_dir: 运行目录路径
        fps: 目标帧率
        cell_px: 每个格子的像素大小
        start_t: 起始时间步
    """
    print(f"加载运行数据: {run_dir}")

    # 加载数据
    run_data = load_run(run_dir)
    print(f"  - 配置: {run_data.config['episode']['horizon_steps']} 步, "
          f"{run_data.init['n_agents']} 个 UGV")
    print(f"  - Trace: {len(run_data.trace)} 步")

    # 加载地图
    map_path = run_data.config['episode']['map_path']
    if map_path != 'none':
        grid_map = load_grid_map(map_path)
        print(f"  - 地图: {map_path} ({grid_map.width}x{grid_map.height})")
    else:
        grid_map = None
        print(f"  - 地图: 无")

    # 加载任务
    task_tracker = load_tasks(run_dir)
    if task_tracker:
        print(f"  - 任务: {len(task_tracker.tasks)} 个")
    else:
        print(f"  - 任务: 无 tasks.json")

    # 加载候选中继点（Day8 Step 2）
    candidate_relays = run_data.init.get('candidate_relays', [])
    if candidate_relays:
        print(f"  - 候选中继点: {len(candidate_relays)} 个")
    else:
        print(f"  - 候选中继点: 无")

    # 获取网格尺寸
    if grid_map:
        grid_width = grid_map.width
        grid_height = grid_map.height
    else:
        grid_width = 20
        grid_height = 20

    # 初始化渲染器
    renderer = Renderer(grid_width, grid_height, cell_px, grid_map)
    print(f"\n窗口尺寸: {renderer.window_width}x{renderer.window_height}")

    # 初始化控制状态
    control = ControlState(
        t=start_t,
        paused=False,
        speed=1.0,
        show_grid=True,
        show_tasks=True,
        show_goals=True,
        max_t=len(run_data.trace)
    )
    # Day8 Step 2: 添加候选点显示控制
    control.show_candidates = True  # 默认显示候选点

    # 主循环
    clock = pygame.time.Clock()
    running = True

    print("\n开始播放...")
    print("快捷键:")
    print("  Space: 暂停/继续")
    print("  ↑/↓: 加速/减速")
    print("  ←/→: 单步前进/后退（暂停时）")
    print("  R: 重启")
    print("  G: 显示/隐藏网格线")
    print("  T: 显示/隐藏任务")
    print("  O: 显示/隐藏目标")
    print("  C: 显示/隐藏候选点")
    print("  ESC/Q: 退出")

    while running:
        # 处理事件
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                else:
                    control = handle_event(event, control)

        # 更新时间
        dt = clock.get_time()
        new_t = update_time(control, dt, fps)
        if new_t != control.t:
            control.t = new_t
            # 循环播放
            if control.t >= control.max_t - 1:
                control.t = 0

        # 获取当前步的数据
        if 0 <= control.t < len(run_data.trace):
            step_data = run_data.trace[control.t]
        else:
            step_data = {}

        # 获取插值后的 UGV 位置（用于平滑移动）
        ugv_positions_interpolated = step_data.get('ugv_positions', [])
        if control._accumulated_steps > 0 and control.t + 1 < len(run_data.trace):
            # 在当前帧和下一帧之间插值
            next_step_data = run_data.trace[control.t + 1]
            if 'ugv_positions' in step_data and 'ugv_positions' in next_step_data:
                current_pos = step_data['ugv_positions']
                next_pos = next_step_data['ugv_positions']
                alpha = control._accumulated_steps  # 0-1 之间的插值系数

                ugv_positions_interpolated = []
                for i in range(len(current_pos)):
                    if i < len(next_pos):
                        interp_x = current_pos[i][0] * (1 - alpha) + next_pos[i][0] * alpha
                        interp_y = current_pos[i][1] * (1 - alpha) + next_pos[i][1] * alpha
                        ugv_positions_interpolated.append([interp_x, interp_y])
                    else:
                        ugv_positions_interpolated.append(current_pos[i])

        # 渲染
        renderer.clear()
        renderer.draw_grid(control.show_grid)

        # 绘制候选点（Day8 Step 2）
        if control.show_candidates and candidate_relays:
            renderer.draw_candidates(candidate_relays)

        # 绘制任务
        if control.show_tasks and task_tracker:
            renderer.draw_tasks(task_tracker, control.t)

        # 绘制 UGV（使用插值位置，并传递目标信息用于绘制路径）
        ugv_goals = step_data.get('ugv_goals') if control.show_goals else None
        # UAV carrier ID: 如果 uav_state 是整数，表示 UAV onboard 在该 UGV 上
        uav_state = step_data.get('uav_state')
        uav_carrier_id = uav_state if isinstance(uav_state, int) else None
        if ugv_positions_interpolated:
            renderer.draw_ugvs(ugv_positions_interpolated, ugv_goals, grid_map,
                             show_paths=True, uav_carrier_id=uav_carrier_id)

        # 绘制目标点
        if control.show_goals and 'ugv_goals' in step_data:
            renderer.draw_goals(step_data['ugv_goals'])

        # 绘制 HUD
        renderer.draw_hud(
            control.t,
            control.max_t,
            control.speed,
            control.paused,
            step_data,
            run_data.metrics
        )

        renderer.flip()

        # 控制帧率
        clock.tick(fps)

    # 清理
    renderer.close()
    print("\n可视化器已关闭")


def main():
    """主函数"""
    args = parse_args()

    # 检查运行目录是否存在
    run_path = Path(args.run)
    if not run_path.exists():
        print(f"错误: 运行目录不存在: {args.run}")
        sys.exit(1)

    # 运行可视化器
    try:
        run_visualizer(args.run, args.fps, args.cell_px, args.start_t)
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
