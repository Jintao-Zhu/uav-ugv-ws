import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import GroupAction
from launch_ros.actions import Node, PushRosNamespace

# 与 spawn_turtlebot.launch.py 保持一致
ROBOTS = ['tb3_0', 'tb3_1', 'tb3_2']


def generate_launch_description():
    pkg_dir = get_package_share_directory('uav_ugv_bringup')
    nav2_params_file = os.path.join(pkg_dir, 'config', 'nav2_params.yaml')

    nav2_bringup_dir = get_package_share_directory('nav2_bringup')
    rviz_config = os.path.join(nav2_bringup_dir, 'rviz', 'nav2_default_view.rviz')

    ld = LaunchDescription()

    for name in ROBOTS:
        # 每台 UGV 的 Nav2 节点都放在各自的 namespace 下
        # 话题自动变为 /tb3_X/cmd_vel, /tb3_X/scan 等
        # TF frame 需要加前缀：tb3_X/odom, tb3_X/base_link
        frame_overrides = {
            'global_frame': f'{name}/odom',
            'robot_base_frame': f'{name}/base_link',
        }
        # costmap 的 frame 参数嵌套在 local_costmap/global_costmap 下
        costmap_frame_overrides = {
            'local_costmap.local_costmap.global_frame': f'{name}/odom',
            'local_costmap.local_costmap.robot_base_frame': f'{name}/base_link',
            'global_costmap.global_costmap.global_frame': f'{name}/odom',
            'global_costmap.global_costmap.robot_base_frame': f'{name}/base_link',
        }

        nav2_group = GroupAction([
            PushRosNamespace(name),

            Node(
                package='nav2_controller',
                executable='controller_server',
                output='screen',
                parameters=[nav2_params_file, frame_overrides]
            ),
            Node(
                package='nav2_planner',
                executable='planner_server',
                output='screen',
                parameters=[nav2_params_file, costmap_frame_overrides]
            ),
            Node(
                package='nav2_behaviors',
                executable='behavior_server',
                output='screen',
                parameters=[nav2_params_file, frame_overrides]
            ),
            Node(
                package='nav2_bt_navigator',
                executable='bt_navigator',
                output='screen',
                parameters=[nav2_params_file, frame_overrides]
            ),
            Node(
                package='nav2_lifecycle_manager',
                executable='lifecycle_manager',
                output='screen',
                parameters=[{
                    'use_sim_time': True,
                    'autostart': True,
                    'node_names': [
                        'controller_server',
                        'planner_server',
                        'behavior_server',
                        'bt_navigator',
                    ]
                }]
            ),
        ])
        ld.add_action(nav2_group)

    # RViz（只需一个）
    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        arguments=['-d', rviz_config, '--ros-args', '--log-level', 'warn'],
        parameters=[{'use_sim_time': True}],
        output='screen'
    )
    ld.add_action(rviz_node)

    return ld
