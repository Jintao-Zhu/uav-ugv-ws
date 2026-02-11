import os
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

    # 2. 【关键修复】设置环境变量
    # 这一步告诉 Gazebo：去 /opt/ros/jazzy/share 下面找 turtlebot3_description 这些网格文件
    # 注意：我们使用 AppendEnvironmentVariable，这样不会覆盖掉系统原本的路径
    set_gz_resource_path = AppendEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=os.path.join(get_package_share_directory('turtlebot3_gazebo'), '..', '..') 
        # 上面这行的意思是：定位到 /opt/ros/jazzy/share 目录
    )

    # 3. 定义通信桥梁
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
        ],
        output='screen'
    )

    # 4. 生成小车
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
        set_gz_resource_path,  # 先执行环境变量设置
        bridge,
        spawn_robot
    ])