#!/bin/bash
# UAV-UGV 联合仿真启动脚本
# 在 shell 层面设置所有 Gazebo 环境变量，确保所有子进程（包括 Gazebo server）都能继承

set -e

PX4_DIR="$HOME/anders/ART_MAPF/uav-ugv-ws/PX4-Autopilot"
PX4_BUILD="$PX4_DIR/build/px4_sitl_default"
WS_DIR="$HOME/anders/ART_MAPF/uav-ugv-ws/uav_ugv_ws"

# PX4 Gazebo 资源路径
export GZ_SIM_RESOURCE_PATH="${PX4_DIR}/Tools/simulation/gz/models:${PX4_DIR}/Tools/simulation/gz/worlds${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
export GZ_SIM_SYSTEM_PLUGIN_PATH="${PX4_BUILD}/src/modules/simulation/gz_plugins${GZ_SIM_SYSTEM_PLUGIN_PATH:+:$GZ_SIM_SYSTEM_PLUGIN_PATH}"
export PX4_GZ_MODELS="${PX4_DIR}/Tools/simulation/gz/models"

# Source ROS 2 workspace
source "$WS_DIR/install/setup.bash"

echo "=== 环境变量 ==="
echo "GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH"
echo "GZ_SIM_SYSTEM_PLUGIN_PATH=$GZ_SIM_SYSTEM_PLUGIN_PATH"
echo "PX4_GZ_MODELS=$PX4_GZ_MODELS"
echo "================"

ros2 launch uav_ugv_bringup bringup_all.launch.py
