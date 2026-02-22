"""
RViz 可视化启动文件

功能：
1. 启动地图发布节点（将 ag_coop 地图转换为 ROS OccupancyGrid）
2. 启动 RViz2 并加载预配置文件

使用方法：
    ros2 launch uav_ugv_bringup rviz.launch.py
    ros2 launch uav_ugv_bringup rviz.launch.py rviz_config:=default.rviz
"""

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    # 设置 ag_coop 路径
    home_dir = os.path.expanduser('~')
    ag_coop_path = os.path.join(home_dir, 'anders/ART_MAPF/uav-ugv-ws/ag_coop')

    # 获取当前 PYTHONPATH 并添加 ag_coop
    current_pythonpath = os.environ.get('PYTHONPATH', '')
    if current_pythonpath:
        new_pythonpath = f"{ag_coop_path}:{current_pythonpath}"
    else:
        new_pythonpath = ag_coop_path

    # 声明参数：RViz 配置文件名
    config_arg = DeclareLaunchArgument(
        'rviz_config',
        default_value='simple.rviz',
        description='RViz config file name (simple.rviz or default.rviz)'
    )

    # RViz 配置文件路径（使用 PathJoinSubstitution）
    rviz_config = PathJoinSubstitution([
        get_package_share_directory('uav_ugv_bringup'),
        'rviz',
        LaunchConfiguration('rviz_config')
    ])

    return LaunchDescription([
        config_arg,

        # 静态 TF 发布节点（map → tb3_X/odom）
        Node(
            package='coop_bridge',
            executable='static_tf_publisher',
            name='static_tf_publisher',
            output='screen',
            parameters=[{'use_sim_time': True}]
        ),

        # 地图发布节点
        Node(
            package='coop_bridge',
            executable='map_publisher',
            name='map_publisher',
            output='screen',
            parameters=[{'use_sim_time': False}],  # 暂时禁用 sim_time 测试
            additional_env={'PYTHONPATH': new_pythonpath}
        ),

        # RViz2
        Node(
            package='rviz2',
            executable='rviz2',
            name='rviz2',
            arguments=['-d', rviz_config],
            parameters=[{'use_sim_time': True}],
            output='screen'
        ),
    ])
