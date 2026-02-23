#!/usr/bin/env python3
"""
UGV PI 反馈线性化控制器

移植自: https://github.com/eferreirafilho/mapf
源文件: planning/scripts/planner.py 的 command_robot() 函数

核心算法:
1. 计算目标方向和角度误差
2. 两阶段控制:
   - 阶段1: 角度误差大时，原地转向
   - 阶段2: 角度误差小时，前进并微调
3. PI 控制器（比例 + 积分）消除稳态误差
"""

import math
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from tf_transformations import euler_from_quaternion


class UGVController:
    """
    单个 UGV 的 PI 反馈线性化控制器

    适用于差速驱动机器人（如 TurtleBot3）
    """

    def __init__(self, node, robot_id):
        """
        初始化 UGV 控制器

        Args:
            node: ROS 2 节点实例
            robot_id: 机器人 ID（0, 1, 2, ...）
        """
        self.node = node
        self.robot_id = robot_id
        self.namespace = f'/tb3_{robot_id}'

        # 控制参数（直接从 GitHub 仓库复制）
        self.KP_linear = 0.25      # Controller "proportional" gain for linear velocity
        self.KI_linear = 0.05      # Controller "integral" gain for linear velocity
        self.KP_angular = 0.5      # Controller "proportional" gain for angular velocity
        self.KI_angular = 0.01     # Controller "integral" gain for angular velocity
        self.MAX_LINEAR_VELOCITY = 1.0
        self.MAX_ANGULAR_VELOCITY = 0.2
        self.ANGLE_THRE = 0.4      # Too small -> Jittering, too big -> Robots move in a straight line with wrong direction
        self.THRE_ROBOT_ON_TARGET = 0.1  # Threshold to consider that robot has reached a target

        # 状态变量
        self.current_pose = None        # 当前位置 (Point)
        self.current_orientation = None # 当前朝向 (弧度)
        self.target_pose = None         # 目标位置 (x, y)

        # PI 控制器积分项
        self.angular_integral = 0.0
        self.distance_integral = 0.0

        # ROS 2 接口
        self.cmd_vel_pub = node.create_publisher(
            Twist, f'{self.namespace}/cmd_vel', 10)
        self.odom_sub = node.create_subscription(
            Odometry, f'{self.namespace}/odom',
            self.odom_callback, 10)

        node.get_logger().info(f'UGVController initialized for {self.namespace}')

    def odom_callback(self, msg):
        """
        里程计回调函数，更新机器人位置和朝向

        Args:
            msg: Odometry 消息
        """
        # 首次接收odom数据时打印日志
        if self.current_pose is None:
            self.node.get_logger().info(f'{self.namespace}: First odom received')

        # 更新位置
        self.current_pose = msg.pose.pose.position

        # 更新朝向（从四元数转换为欧拉角）
        orientation = msg.pose.pose.orientation
        _, _, theta = euler_from_quaternion([
            orientation.x, orientation.y,
            orientation.z, orientation.w])
        self.current_orientation = theta

    def set_target(self, x, y):
        """
        设置目标位置

        Args:
            x: 目标 x 坐标（世界坐标系）
            y: 目标 y 坐标（世界坐标系）
        """
        self.target_pose = (x, y)
        self.node.get_logger().debug(
            f'{self.namespace}: New target set to ({x:.2f}, {y:.2f})')

    def is_at_target(self):
        """
        检查机器人是否到达目标

        Returns:
            bool: True 表示已到达，False 表示未到达
        """
        if self.current_pose is None or self.target_pose is None:
            return False

        # 计算距离
        dx = self.target_pose[0] - self.current_pose.x
        dy = self.target_pose[1] - self.current_pose.y
        distance = math.sqrt(dx*dx + dy*dy)

        # 到达判定
        if distance < self.THRE_ROBOT_ON_TARGET:
            # Anti-Windup: 清零积分项，防止积分饱和
            self.angular_integral = 0.0
            self.distance_integral = 0.0
            return True

        return False

    def control_step(self):
        """
        执行一步控制（核心算法）

        这是从 GitHub 仓库的 command_robot() 函数移植的核心逻辑
        """
        # 检查状态是否有效
        if self.current_pose is None or self.target_pose is None:
            return

        if self.current_orientation is None:
            return

        # 如果已到达目标，停止
        if self.is_at_target():
            self.halt()
            return

        # 创建速度指令
        cmd_vel = Twist()

        try:
            # 1. 计算位置误差
            error_x = self.target_pose[0] - self.current_pose.x
            error_y = self.target_pose[1] - self.current_pose.y

            # 2. 计算目标角度（使用 atan2 获取正确的角度）
            target_angle = math.atan2(error_y, error_x)

            # 3. 计算角度误差（考虑角度的周期性，归一化到 [-π, π]）
            angle_diff = target_angle - self.current_orientation
            if angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            elif angle_diff < -math.pi:
                angle_diff += 2 * math.pi

            # 4. PI 控制器 - 角速度
            angular_error = angle_diff
            self.angular_integral += angular_error
            angular_output = (self.KP_angular * angular_error +
                            self.KI_angular * self.angular_integral)

            # 5. 两阶段控制策略
            if abs(angle_diff) > self.ANGLE_THRE:
                # 阶段 1: 角度误差大 -> 原地转向
                cmd_vel.linear.x = 0.0
                cmd_vel.angular.z = angular_output
            else:
                # 阶段 2: 角度误差小 -> 前进并微调方向
                # PI 控制器 - 线速度
                distance_error = math.sqrt(error_x**2 + error_y**2)
                self.distance_integral += distance_error
                distance_output = (self.KP_linear * distance_error +
                                 self.KI_linear * self.distance_integral)

                cmd_vel.linear.x = distance_output
                cmd_vel.angular.z = angular_output  # 保持角度微调，而不是设为0

            # 6. 速度限幅
            cmd_vel.linear.x = max(min(cmd_vel.linear.x,
                                      self.MAX_LINEAR_VELOCITY), 0.0)
            cmd_vel.angular.z = max(min(cmd_vel.angular.z,
                                       self.MAX_ANGULAR_VELOCITY),
                                   -self.MAX_ANGULAR_VELOCITY)

            # 7. 发布速度指令
            self.cmd_vel_pub.publish(cmd_vel)

        except Exception as e:
            self.node.get_logger().error(
                f'{self.namespace}: Error in control_step: {str(e)}')

    def halt(self):
        """
        停止机器人（发送零速度指令）
        """
        cmd_vel = Twist()
        cmd_vel.linear.x = 0.0
        cmd_vel.linear.y = 0.0
        cmd_vel.linear.z = 0.0
        cmd_vel.angular.x = 0.0
        cmd_vel.angular.y = 0.0
        cmd_vel.angular.z = 0.0
        self.cmd_vel_pub.publish(cmd_vel)

    def get_distance_to_target(self):
        """
        获取到目标的距离

        Returns:
            float: 距离（米），如果状态无效返回 None
        """
        if self.current_pose is None or self.target_pose is None:
            return None

        dx = self.target_pose[0] - self.current_pose.x
        dy = self.target_pose[1] - self.current_pose.y
        return math.sqrt(dx*dx + dy*dy)
