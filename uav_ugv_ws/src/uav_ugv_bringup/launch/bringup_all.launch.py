import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription, SetEnvironmentVariable, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():
    # 使用 CycloneDDS 解决 Jazzy + XRCE-DDS type hash 兼容性问题
    set_rmw = SetEnvironmentVariable('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp')
    # --- 路径定义 ---
    px4_dir = '/home/anders/anders/ART_MAPF/uav-ugv-ws/PX4-Autopilot'
    dds_agent_bin = '/usr/local/bin/MicroXRCEAgent'

    spawn_turtlebot_launch = os.path.join(
        os.path.dirname(__file__), 'spawn_turtlebot.launch.py'
    )

    # 0. 预热 Gazebo（首次启动时初始化资源缓存，跑1步后自动退出）
    gz_warmup = ExecuteProcess(
        cmd=['gz', 'sim', '-s', '--iterations', '1'],
        output='log',
        name='gz_warmup'
    )

    # 1. 启动 PX4 SITL (gz_x500)（延迟 3 秒，等预热完成）
    px4_sitl = TimerAction(
        period=3.0,
        actions=[
            ExecuteProcess(
                cmd=[
                    'bash', '-c',
                    f'cd {px4_dir} && make px4_sitl gz_x500'
                ],
                output='screen',
                name='px4_sitl'
            )
        ]
    )

    # 2. 启动 Micro-XRCE-DDS-Agent（延迟 5 秒，等 PX4 先起来）
    dds_agent = TimerAction(
        period=5.0,
        actions=[
            ExecuteProcess(
                cmd=[dds_agent_bin, 'udp4', '-p', '8888'],
                output='screen',
                name='micro_xrce_dds_agent'
            )
        ]
    )

    # 3. 启动 TurtleBot3（延迟 10 秒，等 Gazebo 世界加载完成）
    spawn_turtlebot = TimerAction(
        period=10.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(spawn_turtlebot_launch)
            )
        ]
    )

    return LaunchDescription([
        set_rmw,
        gz_warmup,
        px4_sitl,
        dds_agent,
        spawn_turtlebot,
    ])
