#!/usr/bin/env python3
"""
静态 TF 发布器 - 发布 map → tb3_X/odom 变换

功能：
为每个 UGV 发布从 map 到 odom 的静态变换，使 RViz 能够正确显示所有坐标系
由于 Gazebo DiffDrive 插件不会从生成位置初始化里程计，我们需要从 Gazebo 读取
实际位置并发布偏移变换
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import StaticTransformBroadcaster


class StaticTFPublisher(Node):
    """
    静态 TF 发布器

    订阅 Gazebo 里程计，计算初始位置偏移，发布 map → tb3_X/odom 的静态变换
    """

    def __init__(self):
        super().__init__('static_tf_publisher')

        # 动态发现 UGV 数量
        self.num_ugvs = self.count_ugv_topics()
        self.get_logger().info(f'发现 {self.num_ugvs} 台 UGV')

        # 创建静态 TF 广播器
        self.tf_broadcaster = StaticTransformBroadcaster(self)

        # 存储每个 UGV 的初始位置（从 Gazebo 读取）
        self.initial_poses = {}
        self.odom_subscribers = []

        # 为每个 UGV 订阅里程计话题，获取初始位置
        for i in range(self.num_ugvs):
            sub = self.create_subscription(
                Odometry,
                f'/tb3_{i}/odom',
                lambda msg, ugv_id=i: self.odom_callback(msg, ugv_id),
                10
            )
            self.odom_subscribers.append(sub)

        self.get_logger().info('等待接收所有 UGV 的初始位置...')

        # 创建定时器，检查是否收到所有初始位置
        self.check_timer = self.create_timer(0.5, self.check_and_publish)

    def count_ugv_topics(self):
        """
        动态发现 UGV 数量（通过检测 /tb3_X/cmd_vel 话题）

        Returns:
            int: UGV 数量
        """
        topic_list = self.get_topic_names_and_types()
        ugv_count = 0
        for topic, _ in topic_list:
            if topic.startswith('/tb3_') and topic.endswith('/cmd_vel'):
                ugv_count += 1
        return ugv_count

    def odom_callback(self, msg: Odometry, ugv_id: int):
        """
        里程计回调 - 只记录第一次收到的位置作为初始位置

        Args:
            msg: 里程计消息
            ugv_id: UGV ID
        """
        if ugv_id not in self.initial_poses:
            # 记录初始位置（里程计坐标系中的位置，应该接近 0,0）
            x = msg.pose.pose.position.x
            y = msg.pose.pose.position.y
            z = msg.pose.pose.position.z
            self.initial_poses[ugv_id] = (x, y, z)
            self.get_logger().info(
                f'UGV {ugv_id} 初始里程计位置: ({x:.3f}, {y:.3f}, {z:.3f})'
            )

    def check_and_publish(self):
        """
        检查是否收到所有 UGV 的初始位置，如果是则发布静态变换
        """
        if len(self.initial_poses) == self.num_ugvs:
            self.publish_static_transforms()
            # 取消定时器，只发布一次
            self.check_timer.cancel()

    def publish_static_transforms(self):
        """
        发布静态 TF 变换（map → tb3_X/odom）

        由于 Gazebo DiffDrive 插件从 (0,0) 开始计数里程计，
        我们需要发布从 map 到 odom 的偏移变换，使得：
        map → tb3_X/odom → tb3_X/base_footprint
        最终得到正确的世界坐标
        """
        # 从 spawn_turtlebot.launch.py 中定义的生成位置
        spawn_positions = [
            (3.0, 2.0, 0.1),   # tb3_0
            (10.0, 5.0, 0.1),  # tb3_1
            (17.0, 18.0, 0.1), # tb3_2
        ]

        transforms = []
        for i in range(self.num_ugvs):
            if i >= len(spawn_positions):
                self.get_logger().warning(f'UGV {i} 没有定义生成位置，跳过')
                continue

            t = TransformStamped()
            t.header.stamp = self.get_clock().now().to_msg()
            t.header.frame_id = 'map'
            t.child_frame_id = f'tb3_{i}/odom'

            # 发布从 map 到 odom 的偏移
            # 由于 odom 从 (0,0) 开始，我们需要将其偏移到生成位置
            spawn_x, spawn_y, spawn_z = spawn_positions[i]
            odom_x, odom_y, odom_z = self.initial_poses.get(i, (0.0, 0.0, 0.0))

            # map → odom 的变换 = 生成位置 - 里程计初始位置
            t.transform.translation.x = spawn_x - odom_x
            t.transform.translation.y = spawn_y - odom_y
            t.transform.translation.z = spawn_z - odom_z
            t.transform.rotation.x = 0.0
            t.transform.rotation.y = 0.0
            t.transform.rotation.z = 0.0
            t.transform.rotation.w = 1.0

            transforms.append(t)

            self.get_logger().info(
                f'UGV {i}: map → odom 偏移 = ({t.transform.translation.x:.3f}, '
                f'{t.transform.translation.y:.3f}, {t.transform.translation.z:.3f})'
            )

        # 发布静态变换
        self.tf_broadcaster.sendTransform(transforms)
        self.get_logger().info(
            f'✓ 已发布 {len(transforms)} 个静态 TF 变换 (map → tb3_X/odom)'
        )


def main(args=None):
    rclpy.init(args=args)
    node = StaticTFPublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
