import os
from launch import LaunchDescription
from launch.actions import (
    ExecuteProcess, IncludeLaunchDescription, SetEnvironmentVariable,
    TimerAction, OpaqueFunction, Shutdown
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable


def kill_existing_processes(context, *args, **kwargs):
    """关闭已运行的 Gazebo、PX4 和 MicroXRCEAgent 进程"""
    import time
    for sig in ['TERM', '9']:
        for proc in ['gz sim', 'ruby', 'px4', 'MicroXRCEAgent']:
            os.system(f'pkill -{sig} -f "{proc}" 2>/dev/null')
        time.sleep(1)
    return []


def generate_launch_description():
    # --- 路径定义 ---
    px4_dir = '/home/anders/anders/ART_MAPF/uav-ugv-ws/PX4-Autopilot'
    px4_build_dir = f'{px4_dir}/build/px4_sitl_default'
    dds_agent_bin = '/usr/local/bin/MicroXRCEAgent'

    spawn_turtlebot_launch = os.path.join(
        os.path.dirname(__file__), 'spawn_turtlebot.launch.py'
    )

    # --- 环境变量 ---
    env_vars = [
        SetEnvironmentVariable('RMW_IMPLEMENTATION', 'rmw_cyclonedds_cpp'),
        # PX4 Gazebo 资源路径 + ag_coop worlds
        SetEnvironmentVariable(
            name='GZ_SIM_RESOURCE_PATH',
            value=[
                f'{px4_dir}/Tools/simulation/gz/models',
                ':',
                f'{px4_dir}/Tools/simulation/gz/worlds',
                ':',
                '/home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop/worlds',  # 添加ag_coop worlds路径
                ':',
                EnvironmentVariable('GZ_SIM_RESOURCE_PATH', default_value=''),
            ]
        ),
        SetEnvironmentVariable(
            name='GZ_SIM_SYSTEM_PLUGIN_PATH',
            value=[
                f'{px4_build_dir}/src/modules/simulation/gz_plugins',
                ':',
                EnvironmentVariable('GZ_SIM_SYSTEM_PLUGIN_PATH', default_value=''),
            ]
        ),
    ]

    # 1. PX4 SITL — 由 PX4 自己启动 Gazebo（非 standalone 模式）
    #    px4-rc.gzsim 会：启动 gz sim server → 启动 GUI → 等 world 就绪 → spawn x500
    px4_sitl = ExecuteProcess(
        cmd=[
            'bash', '-c',
            f'cd {px4_build_dir}/rootfs && '
            f'source ./gz_env.sh && '
            f'export PX4_GZ_WORLD=default && '  # 先恢复使用default world
            f'export PX4_GZ_MODEL_POSE=10,14,0.5,0,0,0 && '
            f'export PX4_SIM_MODEL=gz_x500 && '
            f'export GZ_IP=127.0.0.1 && '
            f'{px4_build_dir}/bin/px4'
        ],
        output='screen',
        name='px4_sitl',
        on_exit=Shutdown()
    )

    # 2. Spawn 3 台 TurtleBot（延迟 15 秒，等 PX4 启动 Gazebo 并 spawn x500 完成）
    spawn_turtlebot = TimerAction(
        period=15.0,
        actions=[
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(spawn_turtlebot_launch)
            )
        ]
    )

    # 3. Micro-XRCE-DDS-Agent（延迟 10 秒，PX4 起来后就可以连）
    dds_agent = TimerAction(
        period=10.0,
        actions=[
            ExecuteProcess(
                cmd=[dds_agent_bin, 'udp4', '-p', '8888'],
                output='screen',
                name='micro_xrce_dds_agent'
            )
        ]
    )

    return LaunchDescription([
        OpaqueFunction(function=kill_existing_processes),
        *env_vars,
        px4_sitl,
        spawn_turtlebot,
        dds_agent,
    ])
