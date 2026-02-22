#!/usr/bin/env python3
"""
CoopBridgeNode - 连接 ag_coop 决策层和 Gazebo 仿真

架构：
    ag_coop (Prioritized Planning) → CoopBridgeNode (时间同步 + 坐标转换) → PI Controller → Gazebo

参考：
    - GitHub MAPF 仓库的时间同步机制
    - 严格遵循原始代码的控制流程
"""

import sys
import os
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Point, PoseStamped
from nav_msgs.msg import Path
from enum import Enum
from tf2_ros import Buffer, TransformListener

# 添加 ag_coop 到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../ag_coop'))

from agcoop.env.core import AGCoopEnv
from agcoop.map.io_text import load_movingai_map
from .ugv_controller import UGVController


class StepState(Enum):
    """执行状态"""
    PLANNING = 1    # ag_coop 规划中
    EXECUTING = 2   # 机器人执行中
    COMPLETED = 3   # 任务完成


class CoopBridgeNode(Node):
    """
    CoopBridge 主节点

    功能：
    1. 运行 ag_coop 环境进行路径规划
    2. 将 ag_coop 的格子坐标转换为 Gazebo 世界坐标
    3. 使用时间同步机制协调多机器人执行
    4. 调用 PI 控制器驱动机器人

    参考 GitHub MAPF 仓库的核心逻辑：
    - all_robots_arrived_in_waypoints(): 时间同步
    - cbs_time_schedule: 全局时间步
    - drive_robots_to_cbs_waypoints(): 主控制循环
    """

    def __init__(self):
        super().__init__('coop_bridge')

        # ========== 参数配置 ==========
        # 地图参数（与 ag_coop 保持一致）
        self.map_file = '/home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop/maps/map_01.map'
        self.grid_size = 20  # ag_coop 地图是 20x20
        # cell_resolution 将在 reset() 后从 grid_map 获取，以确保与 ag_coop 一致
        self.cell_resolution = None  # 延迟初始化

        # 缩放因子：Gazebo 世界 (20m×20m) vs ag_coop 地图 (4m×4m)
        self.scale_factor = 5.0  # 临时修复，用于验证坐标转换逻辑

        # 到达阈值（与 GitHub 仓库完全一致）
        self.THRE_ROBOT_ON_TARGET = 0.1  # 米

        # 控制循环频率
        self.control_frequency = 10.0  # Hz

        # ========== 动态发现 UGV 数量 ==========
        self.num_ugvs = self.count_ugv_topics()
        self.get_logger().info(f'Found {self.num_ugvs} UGVs')

        if self.num_ugvs == 0:
            self.get_logger().error('No UGVs found! Exiting.')
            sys.exit(1)

        # ========== 初始化 ag_coop 环境 ==========
        self.get_logger().info('Initializing ag_coop environment...')
        try:
            # 创建 AGCoopEnv 配置（字典格式）
            config = {
                'episode': {
                    'horizon_steps': 500,
                    'decision_period': 5,
                    'seed': 0,
                    'map_path': self.map_file
                },
                'robots': {
                    'n_ugv': self.num_ugvs,
                    'n_uav': 1
                },
                'tasks': {
                    'enabled': True,
                    'arrival_rate': 0.5,  # 增加到 50% 概率，让任务更频繁出现
                    'deadline_min': 25,
                    'deadline_max': 60,
                    'top_m': 5
                },
                'comm': {
                    'enabled': True,
                    'snr_threshold_db': -12.0
                },
                'mapf': {
                    'enabled': True,
                    'H': 10,
                    'time_budget_ms': 1000,
                    'connectivity': 4
                },
                'ugv': {
                    'carrier_id': 0
                },
                'rendezvous': {
                    'candidate_count': 12
                }
            }

            # 创建环境
            self.coop_env = AGCoopEnv(
                config=config,
                output_dir=None,
                enable_logging=False,
                method='static'  # 使用 static 方法，让 MAPF 控制 UGV 移动
            )
            self.grid_map = self.coop_env.grid_map
            self.get_logger().info('ag_coop environment initialized')
        except Exception as e:
            self.get_logger().error(f'Failinitialize ag_coop: {e}')
            import traceback
            traceback.print_exc()
            sys.exit(1)

        # ========== 创建 UGV 控制器 ==========
        self.ugv_controllers = [
            UGVController(self, i) for i in range(self.num_ugvs)
        ]
        self.get_logger().info(f'Created {self.num_ugvs} UGV controllers')

        # ========== TF Buffer 和 Listener ==========
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.get_logger().info('TF buffer and listener initialized')

        # ========== 路径发布器（用于 RViz 可视化） ==========
        self.path_publishers = [
            self.create_publisher(Path, f'/tb3_{i}/planned_path', 10)
            for i in range(self.num_ugvs)
        ]
        self.get_logger().info(f'Created {self.num_ugvs} path publishers for RViz')

        # ========== 状态变量（参考 GitHub 仓库） ==========
        self.step_state = StepState.PLANNING
        self.current_step = 0  # 类似 cbs_time_schedule
        self.max_steps = 0  # 类似 max(max_cbs_times)
        self.target_waypoints = [[] for _ in range(self.num_ugvs)]  # 每个 UGV 的航点序列
        self.distance_to_target = [0.0 for _ in range(self.num_ugvs)]

        # 任务完成标志
        self.task_completed = False
        self.episode_count = 0

        # ========== 控制循环（10Hz） ==========
        self.timer = self.create_timer(1.0 / self.control_frequency, self.control_loop)

        self.get_logger().info('CoopBridgeNode initialized, starting control loop...')

    def count_ugv_topics(self):
        """
        动态发现 UGV 数量（通过检测 /tb3_X/cmd_vel 话题）

        参考 GitHub 仓库的 count_robot_topics()

        Returns:
            int: UGV 数量
        """
        topic_list = self.get_topic_names_and_types()
        ugv_count = 0
        for topic, _ in topic_list:
            if topic.startswith('/tb3_') and topic.endswith('/cmd_vel'):
                ugv_count += 1
        return ugv_count

    def control_loop(self):
        """
        主控制循环

        参考 GitHub 仓库的 drive_robots_to_cbs_waypoints()

        状态机：
        1. PLANNING: 调用 ag_coop 规划路径
        2. EXECUTING: 执行当前时间步的航点
        3. COMPLETED: 任务完成
        """
        if self.step_state == StepState.PLANNING:
            self.planning_step()
        elif self.step_state == StepState.EXECUTING:
            self.executing_step()
        elif self.step_state == StepState.COMPLETED:
            self.completed_step()

    def planning_step(self):
        """
        规划阶段：调用 ag_coop 进行路径规划

        参考 GitHub 仓库的 call_cbs_planner() 和 get_data_from_yaml()
        """
        self.get_logger().info('=== Planning Phase ===')

        try:
            # 等待所有 UGV 的 TF 可用
            self.get_logger().info('Waiting for UGV transforms to be available...')
            all_tf_ready = True

            for ugv_id in range(self.num_ugvs):
                frame_name = f'tb3_{ugv_id}/base_footprint'
                timeout_sec = 5.0
                start_time = self.get_clock().now()

                while rclpy.ok():
                    if self.tf_buffer.can_transform('map', frame_name, rclpy.time.Time()):
                        self.get_logger().info(f'UGV {ugv_id} TF ready: map → {frame_name}')
                        break

                    elapsed = (self.get_clock().now() - start_time).nanoseconds / 1e9
                    if elapsed > timeout_sec:
                        self.get_logger().warning(
                            f'Timeout waiting for TF: map → {frame_name} (waited {elapsed:.1f}s)'
                        )
                        all_tf_ready = False
                        break

                    time.sleep(0.1)

            if not all_tf_ready:
                self.get_logger().warning('Not all TF transforms are ready, proceeding anyway...')

            # 重置 ag_coop 环境
            obs = self.coop_env.reset()
            self.get_logger().info(f'ag_coop environment reset')

            # 在 reset() 之后获取 grid_map（因为地图是在 reset() 时加载的）
            if self.grid_map is None:
                self.grid_map = self.coop_env.grid_map
                self.cell_resolution = self.grid_map.resolution  # 使用地图的实际分辨率
                self.get_logger().info(f'Grid map obtained: {self.grid_map.width}x{self.grid_map.height}, resolution={self.cell_resolution}m/cell')
                self.get_logger().info(f'Using scale factor: {self.scale_factor} (Gazebo world is {self.scale_factor}x larger)')
                self.get_logger().info(f'Effective resolution: {self.cell_resolution * self.scale_factor}m/cell')

            # 同步 ag_coop 的初始位置与 Gazebo 中 UGV 的实际位置
            # ag_coop reset() 会随机生成初始位置，但我们需要使用 Gazebo 中的真实位置
            self.get_logger().info('Synchronizing UGV initial positions from Gazebo to ag_coop...')
            for ugv_id in range(self.num_ugvs):
                controller = self.ugv_controllers[ugv_id]
                if controller.current_pose is not None:
                    # Gazebo 坐标 (0-20m) 转换为 ag_coop 坐标 (0-4m)
                    agcoop_x = controller.current_pose.x / self.scale_factor
                    agcoop_y = controller.current_pose.y / self.scale_factor
                    self.coop_env.state.ugv_positions[ugv_id] = (agcoop_x, agcoop_y)
                    self.get_logger().info(
                        f'UGV {ugv_id}: Gazebo ({controller.current_pose.x:.2f}, {controller.current_pose.y:.2f}) '
                        f'→ ag_coop ({agcoop_x:.2f}, {agcoop_y:.2f})'
                    )
                else:
                    self.get_logger().warning(f'UGV {ugv_id}: No odometry received yet, using ag_coop random position')

            # 运行 ag_coop 直到完成（获取完整路径）
            done = False
            step_count = 0
            max_steps = 200  # 防止无限循环

            # 存储每个 UGV 的路径（ag_coop 世界坐标）
            ugv_paths = [[] for _ in range(self.num_ugvs)]

            while not done and step_count < max_steps:
                # AGCoopEnv 使用 greedy 方法，不需要 action（传 None）
                obs, reward, done, info = self.coop_env.step(action=None)

                # 记录每个 UGV 的位置（直接存储 ag_coop 世界坐标）
                for i in range(self.num_ugvs):
                    world_pos = self.coop_env.state.ugv_positions[i]
                    ugv_paths[i].append(world_pos)  # 存储 (x, y) 元组

                step_count += 1

            if done:
                self.get_logger().info(f'ag_coop planning completed in {step_count} steps')
            else:
                self.get_logger().warning(f'ag_coop planning timeout after {max_steps} steps')

            # 转换路径为 Gazebo 坐标
            self.target_waypoints = [[] for _ in range(self.num_ugvs)]
            for ugv_id in range(self.num_ugvs):
                self.get_logger().info(f'UGV {ugv_id} path (ag_coop world): {ugv_paths[ugv_id][:5]}...')
                for agcoop_pos in ugv_paths[ugv_id]:
                    gazebo_point = self.agcoop_world_to_gazebo_world(
                        agcoop_pos[0], agcoop_pos[1]
                    )
                    self.target_waypoints[ugv_id].append(gazebo_point)

            # 计算最大步数
            self.max_steps = max(len(path) for path in self.target_waypoints)
            self.get_logger().info(f'Max waypoints to execute: {self.max_steps}')

            # 打印每个 UGV 的路径（Gazebo 世界坐标）
            for ugv_id in range(self.num_ugvs):
                path_str = ' → '.join([f'({p.x:.1f},{p.y:.1f})' for p in self.target_waypoints[ugv_id][:5]])
                self.get_logger().info(f'UGV {ugv_id} path (Gazebo, first 5): {path_str}...')

            # 发布路径到 RViz
            self.publish_paths()

            # 切换到执行阶段
            self.current_step = 0
            self.step_state = StepState.EXECUTING
            self.get_logger().info('Switching to EXECUTING phase')

        except Exception as e:
            self.get_logger().error(f'Planning failed: {e}')
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def executing_step(self):
        """
        执行阶段：驱动机器人到当前时间步的航点

        参考 GitHub 仓库的 drive_robots_to_cbs_waypoints() 和 all_robots_arrived_in_waypoints()
        """
        # 检查是否所有机器人都到达了最终目标
        if self.all_robots_arrived_final_waypoint():
            self.get_logger().info('✅ All UGVs reached final targets!')
            self.step_state = StepState.COMPLETED
            return

        # 检查是否所有机器人都到达了当前时间步的航点
        if self.all_robots_arrived_in_waypoints():
            if self.current_step < self.max_steps - 1:
                self.current_step += 1
                self.get_logger().info(
                    f'All robots arrived at waypoint {self.current_step - 1}, '
                    f'moving to waypoint {self.current_step} / {self.max_steps - 1}'
                )

        # 为每个 UGV 设置当前目标并执行控制
        for ugv_id in range(self.num_ugvs):
            target_waypoint = self.get_next_target_waypoint(ugv_id)
            if target_waypoint:
                # 设置目标（只在目标改变时设置）
                controller = self.ugv_controllers[ugv_id]
                if controller.target_pose is None or \
                   abs(controller.target_pose[0] - target_waypoint.x) > 0.01 or \
                   abs(controller.target_pose[1] - target_waypoint.y) > 0.01:
                    controller.set_target(target_waypoint.x, target_waypoint.y)

                # 执行控制步
                controller.control_step()

    def completed_step(self):
        """
        完成阶段：任务完成后的处理
        """
        if not self.task_completed:
            self.task_completed = True
            self.episode_count += 1

            # 停止所有机器人
            for controller in self.ugv_controllers:
                controller.halt()

            # 打印最终位置
            self.get_logger().info('=== Final Positions ===')
            for ugv_id, controller in enumerate(self.ugv_controllers):
                if controller.current_pose:
                    self.get_logger().info(
                        f'UGV {ugv_id}: ({controller.current_pose.x:.2f}, '
                        f'{controller.current_pose.y:.2f})'
                    )

            self.get_logger().info(f'Episode {self.episode_count} completed!')

            # 可以选择重新规划或退出
            # self.step_state = StepState.PLANNING  # 重新规划
            # self.task_completed = False

    def all_robots_arrived_in_waypoints(self):
        """
        检查所有 UGV 是否到达当前时间步的航点

        参考 GitHub 仓库的 all_robots_arrived_in_waypoints()

        Returns:
            bool: True 表示全部到达
        """
        number_of_robots_in_waypoints = 0

        for ugv_id in range(self.num_ugvs):
            controller = self.ugv_controllers[ugv_id]
            target_waypoint = self.get_next_target_waypoint(ugv_id)

            if controller.current_pose is None or target_waypoint is None:
                continue

            # 计算距离
            dx = target_waypoint.x - controller.current_pose.x
            dy = target_waypoint.y - controller.current_pose.y
            distance = (dx**2 + dy**2) ** 0.5
            self.distance_to_target[ugv_id] = distance

            if distance < self.THRE_ROBOT_ON_TARGET:
                number_of_robots_in_waypoints += 1

        return number_of_robots_in_waypoints == self.num_ugvs

    def all_robots_arrived_final_waypoint(self):
        """
        检查所有 UGV 是否到达最终目标

        参考 GitHub 仓库的 all_robots_arrived_cbs_final_waypoint()

        Returns:
            bool: True 表示全部到达最终目标
        """
        number_of_robots_at_final = 0

        for ugv_id in range(self.num_ugvs):
            controller = self.ugv_controllers[ugv_id]

            if len(self.target_waypoints[ugv_id]) == 0:
                continue

            # 最后一个航点
            final_waypoint = self.target_waypoints[ugv_id][-1]

            if controller.current_pose is None:
                continue

            # 计算距离
            dx = final_waypoint.x - controller.current_pose.x
            dy = final_waypoint.y - controller.current_pose.y
            distance = (dx**2 + dy**2) ** 0.5

            if distance < self.THRE_ROBOT_ON_TARGET:
                number_of_robots_at_final += 1

        return number_of_robots_at_final == self.num_ugvs

    def get_next_target_waypoint(self, ugv_id):
        """
        获取 UGV 的下一个目标航点

        参考 GitHub 仓库的 get_next_target_waypoint()

        Args:
            ugv_id: UGV ID

        Returns:
            Point: 目标航点，如果没有则返回 None
        """
        if len(self.target_waypoints[ugv_id]) == 0:
            return None

        # 如果当前步数超过路径长度，返回最后一个航点（停留）
        if self.current_step >= len(self.target_waypoints[ugv_id]):
            return self.target_waypoints[ugv_id][-1]

        return self.target_waypoints[ugv_id][self.current_step]

    def publish_paths(self):
        """
        发布规划路径到 RViz

        将每个 UGV 的航点序列转换为 nav_msgs/Path 消息并发布
        """
        for ugv_id in range(self.num_ugvs):
            path_msg = Path()
            path_msg.header.frame_id = 'map'
            path_msg.header.stamp = self.get_clock().now().to_msg()

            # 将航点转换为 PoseStamped
            for waypoint in self.target_waypoints[ugv_id]:
                pose_stamped = PoseStamped()
                pose_stamped.header.frame_id = 'map'
                pose_stamped.header.stamp = path_msg.header.stamp
                pose_stamped.pose.position = waypoint
                pose_stamped.pose.orientation.w = 1.0  # 默认朝向
                path_msg.poses.append(pose_stamped)

            # 发布路径
            self.path_publishers[ugv_id].publish(path_msg)

        self.get_logger().info(f'Published {self.num_ugvs} paths to RViz')

    def cell_to_world(self, cell):
        """
        将 ag_coop 的格子坐标转换为 Gazebo 世界坐标

        NOTE: This method is currently not used in the main path planning flow.
        We now use agcoop_world_to_gazebo_world() to directly scale world coordinates.
        Kept for potential future use with cell-based MAPF solutions.

        ag_coop 坐标系统（mapping.py:4-11）：
        - origin = (0, 0) 表示 cell(0,0) 左下角在 world 中的位置
        - i 是行索引（对应 y 方向，从上到下）
        - j 是列索引（对应 x 方向，从左到右）
        - cell center: x = origin[0] + (j + 0.5) * resolution
        -              y = origin[1] + (i + 0.5) * resolution

        Gazebo 坐标系统：
        - 标准 ROS 坐标系
        - 北墙（顶部）：y = 0.5
        - 南墙（底部）：y = 19.5

        转换公式（无需反转）：
        - x = (col + 0.5) * resolution * scale_factor
        - y = (row + 0.5) * resolution * scale_factor

        Args:
            cell: (row, col) 格子坐标

        Returns:
            Point: 世界坐标
        """
        row, col = cell

        # 直接转换，无需反转（ag_coop 的 row 0 已经对应 y = 0.5）
        x = (col + 0.5) * self.cell_resolution * self.scale_factor
        y = (row + 0.5) * self.cell_resolution * self.scale_factor

        return Point(x=x, y=y, z=0.0)

    def agcoop_world_to_gazebo_world(self, agcoop_x: float, agcoop_y: float) -> Point:
        """
        Convert ag_coop world coordinates (0-4m) to Gazebo world coordinates (0-20m)

        ag_coop uses a 20×20 grid with 0.2m resolution = 4m×4m world
        Gazebo uses a 20m×20m world
        Scale factor = 20m / 4m = 5.0

        Args:
            agcoop_x: x coordinate in ag_coop world (0-4m)
            agcoop_y: y coordinate in ag_coop world (0-4m)

        Returns:
            Point: Gazebo world coordinates (0-20m)
        """
        gazebo_x = agcoop_x * self.scale_factor
        gazebo_y = agcoop_y * self.scale_factor

        return Point(x=gazebo_x, y=gazebo_y, z=0.0)


def main(args=None):
    rclpy.init(args=args)
    node = CoopBridgeNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
