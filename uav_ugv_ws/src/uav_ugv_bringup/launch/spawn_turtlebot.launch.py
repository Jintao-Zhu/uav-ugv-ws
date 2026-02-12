import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node

# 3 台 UGV 的配置：名称 + 出生位置（在 20x20m 地图的 free cell 内）
ROBOTS = [
    {'name': 'tb3_0', 'x': '3.0',  'y': '2.0',  'z': '0.1'},
    {'name': 'tb3_1', 'x': '10.0', 'y': '10.0', 'z': '0.1'},
    {'name': 'tb3_2', 'x': '16.0', 'y': '18.0', 'z': '0.1'},
]


def make_robot_sdf(sdf_template: str, name: str) -> str:
    """替换 SDF 中的话题名，使每台车有独立的 Gazebo 话题。

    Gazebo Harmonic 的 DiffDrive 插件不会自动给相对话题加模型前缀，
    所以需要手动把 cmd_vel → /{name}/cmd_vel 等。
    """
    sdf = sdf_template
    # DiffDrive 插件话题
    sdf = sdf.replace('<topic>cmd_vel</topic>',
                       f'<topic>/{name}/cmd_vel</topic>')
    sdf = sdf.replace('<odom_topic>odom</odom_topic>',
                       f'<odom_topic>/{name}/odom</odom_topic>')
    # DiffDrive TF frame（不加 / 前缀，是 frame_id 不是话题）
    sdf = sdf.replace('<frame_id>odom</frame_id>',
                       f'<frame_id>{name}/odom</frame_id>')
    sdf = sdf.replace('<child_frame_id>base_footprint</child_frame_id>',
                       f'<child_frame_id>{name}/base_footprint</child_frame_id>')
    # JointStatePublisher 话题
    sdf = sdf.replace('<topic>joint_states</topic>',
                       f'<topic>/{name}/joint_states</topic>')
    # LiDAR 话题和 frame
    sdf = sdf.replace('<topic>scan</topic>',
                       f'<topic>/{name}/scan</topic>')
    sdf = sdf.replace('<gz_frame_id>base_scan</gz_frame_id>',
                       f'<gz_frame_id>{name}/base_scan</gz_frame_id>')
    return sdf


def generate_launch_description():
    # 模型路径 & 读取 SDF 模板
    model_path = os.path.join(
        get_package_share_directory('turtlebot3_gazebo'),
        'models', 'turtlebot3_burger', 'model.sdf'
    )
    with open(model_path, 'r') as f:
        sdf_template = f.read()

    # URDF（用于 robot_state_publisher）
    urdf_file = os.path.join(
        get_package_share_directory('turtlebot3_description'),
        'urdf', 'turtlebot3_burger.urdf'
    )
    robot_description = xacro.process_file(urdf_file).toxml()

    # /clock 桥接（Gazebo → ROS 2）
    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        name='clock_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen'
    )

    ld = LaunchDescription([clock_bridge])

    for robot in ROBOTS:
        name = robot['name']

        # 1. Spawn 小车到已运行的 Gazebo
        robot_sdf = make_robot_sdf(sdf_template, name)
        spawn = Node(
            package='ros_gz_sim',
            executable='create',
            name=f'spawn_{name}',
            arguments=[
                '-name', name,
                '-string', robot_sdf,
                '-x', robot['x'],
                '-y', robot['y'],
                '-z', robot['z'],
            ],
            output='screen'
        )

        # 2. robot_state_publisher
        rsp = Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            namespace=name,
            parameters=[{
                'robot_description': robot_description,
                'use_sim_time': True,
                'frame_prefix': f'{name}/',
            }],
            output='screen'
        )

        # 3. 话题桥接：Gazebo ↔ ROS 2
        bridge = Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            name=f'bridge_{name}',
            arguments=[
                f'/{name}/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
                f'/{name}/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
                f'/{name}/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
                f'/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
                f'/{name}/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
            ],
            output='screen'
        )

        ld.add_action(spawn)
        ld.add_action(rsp)
        ld.add_action(bridge)

    return ld
