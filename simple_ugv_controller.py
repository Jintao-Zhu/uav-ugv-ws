#!/usr/bin/env python3
"""
简单的UGV控制器 - 直接控制三台TurtleBot3移动到目标点

使用方法:
    python3 simple_ugv_controller.py
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import math


class SimpleUGVController(Node):
    def __init__(self):
        super().__init__('simple_ugv_controller')

        # 定义三台UGV的目标位置 (x, y)
        self.targets = [
            (5.0, 5.0),   # tb3_0 目标
            (10.0, 10.0), # tb3_1 目标
            (15.0, 5.0)   # tb3_2 目标
        ]

        # 控制参数
        self.linear_gain = 0.5   # 线速度增益
        self.angular_gain = 1.0  # 角速度增益
        self.goal_threshold = 0.2  # 到达目标的阈值(米)

        # 存储每台UGV的当前位置
        self.current_poses = [None, None, None]
        self.goals_reached = [False, False, False]

        # 创建订阅者和发布者
        self.odom_subs = []
        self.cmd_pubs = []

        for i in range(3):
            # 订阅里程计
            odom_sub = self.create_subscription(
                Odometry,
                f'/tb3_{i}/odom',
                lambda msg, idx=i: self.odom_callback(msg, idx),
                10
            )
            self.odom_subs.append(odom_sub)

            # 发布速度命令
            cmd_pub = self.create_publisher(Twist, f'/tb3_{i}/cmd_vel', 10)
            self.cmd_pubs.append(cmd_pub)

        # 创建控制循环定时器 (10Hz)
        self.timer = self.create_timer(0.1, self.control_loop)

        self.get_logger().info('Simple UGV Controller initialized')
        self.get_logger().info(f'Targets: {self.targets}')

    def odom_callback(self, msg, ugv_id):
        """接收里程计数据"""
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y

        # 从四元数计算yaw角
        orientation = msg.pose.pose.orientation
        yaw = self.quaternion_to_yaw(orientation)

        self.current_poses[ugv_id] = (x, y, yaw)

    def quaternion_to_yaw(self, q):
        """将四元数转换为yaw角"""
        siny_cosp = 2 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1 - 2 * (q.y * q.y + q.z * q.z)
        return math.atan2(siny_cosp, cosy_cosp)

    def control_loop(self):
        """主控制循环"""
        all_reached = True

        for i in range(3):
            if self.current_poses[i] is None:
                all_reached = False
                continue

            if self.goals_reached[i]:
                continue

            # 获取当前位置和目标
            x, y, yaw = self.current_poses[i]
            target_x, target_y = self.targets[i]

            # 计算到目标的距离和角度
            dx = target_x - x
            dy = target_y - y
            distance = math.sqrt(dx**2 + dy**2)
            target_angle = math.atan2(dy, dx)

            # 计算角度误差
            angle_error = target_angle - yaw
            # 归一化到[-pi, pi]
            while angle_error > math.pi:
                angle_error -= 2 * math.pi
            while angle_error < -math.pi:
                angle_error += 2 * math.pi

            # 创建速度命令
            cmd = Twist()

            if distance < self.goal_threshold:
                # 到达目标，停止
                cmd.linear.x = 0.0
                cmd.angular.z = 0.0
                self.goals_reached[i] = True
                self.get_logger().info(f'UGV {i} reached target!')
            else:
                # 计算控制命令
                cmd.linear.x = min(self.linear_gain * distance, 0.5)  # 限制最大速度
                cmd.angular.z = self.angular_gain * angle_error
                all_reached = False

            # 发布命令
            self.cmd_pubs[i].publish(cmd)

        # 检查是否所有UGV都到达目标
        if all_reached and not all(self.goals_reached):
            self.get_logger().info('All UGVs reached their targets!')
            for i in range(3):
                self.goals_reached[i] = True


def main(args=None):
    rclpy.init(args=args)
    controller = SimpleUGVController()

    try:
        rclpy.spin(controller)
    except KeyboardInterrupt:
        pass
    finally:
        # 停止所有UGV
        for pub in controller.cmd_pubs:
            stop_cmd = Twist()
            pub.publish(stop_cmd)

        controller.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
