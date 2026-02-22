#!/usr/bin/env python3
"""
Launch file for CoopBridgeNode
启动 ag_coop 与 Gazebo 的桥接节点
"""

import os
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """
    生成 launch 描述
    启动 CoopBridgeNode，连接 ag_coop 决策层和 Gazebo 仿真
    """
    # 1. 动态获取 Home 目录，避免硬编码用户名
    home_dir = os.path.expanduser('~')
    ag_coop_path = os.path.join(home_dir, 'anders/ART_MAPF/uav-ugv-ws/ag_coop')

    # 2. 获取当前系统已有的 PYTHONPATH (也就是 source setup.bash 带来的那些)
    current_pythonpath = os.environ.get('PYTHONPATH', '')

    # 3. 安全拼接：将 ag_coop_path 加到最前面，保留原有的 ROS 2 路径
    if current_pythonpath:
        new_pythonpath = f"{ag_coop_path}:{current_pythonpath}"
    else:
        new_pythonpath = ag_coop_path

    coop_bridge_node = Node(
        package='coop_bridge',
        executable='coop_bridge_node',
        name='coop_bridge',
        output='screen',
        parameters=[{
            'use_sim_time': True,
        }],
        # 4. 使用拼接后的安全路径
        additional_env={'PYTHONPATH': new_pythonpath},
    )

    return LaunchDescription([
        coop_bridge_node,
    ])