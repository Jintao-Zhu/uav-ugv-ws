#!/usr/bin/env python3
"""
测试 UGV PI 控制器的 launch 文件
"""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='coop_bridge',
            executable='test_ugv_controller',
            name='ugv_controller_test',
            output='screen',
            parameters=[],
        ),
    ])
