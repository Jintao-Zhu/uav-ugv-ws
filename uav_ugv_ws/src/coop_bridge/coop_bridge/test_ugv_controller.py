#!/usr/bin/env python3
"""
UGV 控制器测试节点

测试 PI 反馈线性化控制器的基本功能
"""

import rclpy
from rclpy.node import Node
from .ugv_controller import UGVController


class UGVControllerTestNode(Node):
    """
    测试节点：让 3 个 UGV 移动到指定目标点
    """

    def __init__(self):
        super().__init__('ugv_controller_test')

        # 动态发现 UGV 数量
        self.num_ugvs = self.count_ugv_topics()
        self.get_logger().info(f'Found {self.num_ugvs} UGVs')

        if self.num_ugvs == 0:
            self.get_logger().error('No UGVs found! Make sure TurtleBots are spawned.')
            return

        # 创建控制器
        self.ugv_controllers = [
            UGVController(self, i) for i in range(self.num_ugvs)
        ]

        # 设置测试目标（根据 map_01.map 和初始位置选择安全路径）
        # 初始位置: tb3_0(3,2), tb3_1(10,5), tb3_2(17,18)
        # 地图 20x20，障碍物位置：
        #   - wall_3: (6,4) 附近
        #   - wall_4: (12.5,8) 附近
        #   - wall_5: (7,12) 附近
        #   - wall_6: (14,16) 附近
        # 选择空旷且距离适中的目标点
        test_targets = [
            (6.5, 10.5),   # tb3_0: 从西南 → 中部偏西（避开 wall_3 和 wall_5）
            (15.5, 10.5),  # tb3_1: 从中部 → 中部偏东（避开 wall_4）
            (10.5, 15.5),  # tb3_2: 从东北 → 中部偏北（避开 wall_6）
        ]

        for i, controller in enumerate(self.ugv_controllers):
            if i < len(test_targets):
                x, y = test_targets[i]
                controller.set_target(x, y)
                self.get_logger().info(f'tb3_{i} target set to ({x}, {y})')

        # 控制循环（10Hz）
        self.timer = self.create_timer(0.1, self.control_loop)
        self.all_reached = False

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

    def control_loop(self):
        """
        主控制循环
        """
        # 执行控制
        for controller in self.ugv_controllers:
            controller.control_step()

        # 检查是否所有 UGV 都到达目标
        if not self.all_reached and self.all_ugvs_at_target():
            self.all_reached = True
            self.get_logger().info('✅ All UGVs reached their targets!')

            # 打印每个 UGV 的最终位置
            for i, controller in enumerate(self.ugv_controllers):
                if controller.current_pose:
                    self.get_logger().info(
                        f'tb3_{i} final position: '
                        f'({controller.current_pose.x:.2f}, '
                        f'{controller.current_pose.y:.2f})')

    def all_ugvs_at_target(self):
        """
        检查所有 UGV 是否到达目标

        Returns:
            bool: True 表示全部到达
        """
        return all(c.is_at_target() for c in self.ugv_controllers)


def main(args=None):
    rclpy.init(args=args)
    node = UGVControllerTestNode()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
