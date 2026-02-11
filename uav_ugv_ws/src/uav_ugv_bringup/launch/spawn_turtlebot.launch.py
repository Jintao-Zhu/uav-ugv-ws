import os
import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import AppendEnvironmentVariable
from launch_ros.actions import Node

def generate_launch_description():
    robot_name = 'turtlebot3_burger'
    x_pos = '2.0'
    y_pos = '0.0'
    z_pos = '0.5'

    # 1. 查找模型路径
    try:
        model_path = os.path.join(
            get_package_share_directory('turtlebot3_gazebo'),
            'models',
            'turtlebot3_burger',
            'model.sdf'
        )
        print(f"DEBUG: Found model file at: {model_path}")
    except Exception as e:
        print(f"Error finding model file: {e}")
        return LaunchDescription([])

    # 2. 设置环境变量，让 Gazebo 找到 turtlebot3_description 的网格文件
    set_gz_resource_path = AppendEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=os.path.join(get_package_share_directory('turtlebot3_gazebo'), '..', '..')
    )

    # 3. 解析 URDF 用于 robot_state_publisher
    urdf_file = os.path.join(
        get_package_share_directory('turtlebot3_description'),
        'urdf',
        'turtlebot3_burger.urdf'
    )
    robot_description = xacro.process_file(urdf_file).toxml()

    # 4. robot_state_publisher：发布静态 TF（base_link -> base_scan 等）
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{
            'robot_description': robot_description,
            'use_sim_time': True,
        }],
        output='screen'
    )

    # 5. 通信桥梁：桥接 Gazebo 话题到 ROS 2
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
        ],
        output='screen'
    )

    # 6. 生成小车
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', robot_name,
            '-file', model_path,
            '-x', x_pos,
            '-y', y_pos,
            '-z', z_pos
        ],
        output='screen'
    )

    return LaunchDescription([
        set_gz_resource_path,
        robot_state_publisher,
        bridge,
        spawn_robot,
    ])