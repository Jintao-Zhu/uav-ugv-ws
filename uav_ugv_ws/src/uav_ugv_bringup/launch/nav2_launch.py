import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    # Nav2 参数文件路径
    pkg_dir = get_package_share_directory('uav_ugv_bringup')
    nav2_params_file = os.path.join(pkg_dir, 'config', 'nav2_params.yaml')

    # Nav2 bringup 包路径
    nav2_bringup_dir = get_package_share_directory('nav2_bringup')

    # 启动 Nav2 导航栈（无地图模式）
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_bringup_dir, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'true',
            'params_file': nav2_params_file,
        }.items()
    )

    # RViz2 可视化
    rviz_config = os.path.join(nav2_bringup_dir, 'rviz', 'nav2_default_view.rviz')
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )

    return LaunchDescription([
        nav2_launch,
        rviz_node,
    ])
