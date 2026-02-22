#!/usr/bin/env python3
"""
地图发布节点 - 将 ag_coop 的 .map 格式转换为 ROS OccupancyGrid

功能：
1. 加载 ag_coop 的 MovingAI 格式地图
2. 转换为 ROS nav_msgs/OccupancyGrid 消息
3. 发布到 /map 话题供 RViz 显示
"""

import sys
import os
import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from geometry_msgs.msg import Pose

# 添加 ag_coop 到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../ag_coop'))
from agcoop.map.io_text import load_movingai_map


class MapPublisher(Node):
    """
    地图发布节点

    将 ag_coop 的离散格子地图转换为 ROS 占据栅格地图
    """

    def __init__(self):
        super().__init__('map_publisher')

        # 参数配置
        self.map_file = '/home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop/maps/map_01.map'
        self.scale_factor = 5.0  # 与 coop_bridge 保持一致

        try:
            # 加载地图（ag_coop 格式）
            self.get_logger().info(f'Loading map from: {self.map_file}')
            grid_map = load_movingai_map(self.map_file, resolution=0.2)
            self.get_logger().info(
                f'Map loaded: {grid_map.width}x{grid_map.height}, '
                f'resolution={grid_map.resolution}m/cell'
            )

            # 创建 OccupancyGrid 消息
            self.map_msg = OccupancyGrid()
            self.map_msg.header.frame_id = 'map'

            # 地图元信息
            self.map_msg.info.resolution = grid_map.resolution * self.scale_factor
            self.map_msg.info.width = grid_map.width
            self.map_msg.info.height = grid_map.height

            # 设置原点（地图左下角在世界坐标系中的位置）
            self.map_msg.info.origin = Pose()
            self.map_msg.info.origin.position.x = 0.0
            self.map_msg.info.origin.position.y = 0.0
            self.map_msg.info.origin.position.z = 0.0
            self.map_msg.info.origin.orientation.w = 1.0

            # 转换地图数据
            # ag_coop: 0=free, 1=obstacle
            # ROS OccupancyGrid: 0=free, 100=obstacle, -1=unknown
            data = []
            for i in range(grid_map.height):
                for j in range(grid_map.width):
                    if grid_map.grid[i, j] == 1:
                        data.append(100)  # 障碍物
                    else:
                        data.append(0)    # 自由空间
            self.map_msg.data = data

            self.get_logger().info(
                f'OccupancyGrid created:\n'
                f'  Size: {self.map_msg.info.width}x{self.map_msg.info.height} cells\n'
                f'  Resolution: {self.map_msg.info.resolution}m/cell\n'
                f'  Origin: ({self.map_msg.info.origin.position.x}, {self.map_msg.info.origin.position.y})\n'
                f'  World size: {self.map_msg.info.width * self.map_msg.info.resolution}m x '
                f'{self.map_msg.info.height * self.map_msg.info.resolution}m\n'
                f'  Data points: {len(self.map_msg.data)}\n'
                f'  Obstacles: {sum(1 for x in self.map_msg.data if x == 100)}'
            )

            # 创建发布器
            self.publisher = self.create_publisher(OccupancyGrid, '/map', 10)

            # 定时发布（1Hz，地图是静态的不需要高频率）
            self.timer = self.create_timer(1.0, self.publish_map)

            self.get_logger().info('Map publisher initialized successfully')

        except Exception as e:
            self.get_logger().error(f'Failed to initialize map publisher: {e}')
            import traceback
            traceback.print_exc()
            sys.exit(1)

    def publish_map(self):
        """发布地图消息"""
        self.map_msg.header.stamp = self.get_clock().now().to_msg()
        self.publisher.publish(self.map_msg)


def main(args=None):
    rclpy.init(args=args)
    node = MapPublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
