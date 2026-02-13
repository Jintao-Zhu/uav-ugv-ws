# UAV-UGV 协同系统

基于通信约束和任务流的 UAV-UGV 协同路径规划与任务分配系统，集成 ROS 2 Jazzy + Gazebo Harmonic + PX4 SITL 仿真环境。

## 项目概述

本项目实现了一个多机器人协同系统，包含：
- **UAV（无人机）**：PX4 x500 四旋翼，负责执行动态生成的任务
- **UGV（地面车）**：TurtleBot3 Burger，作为通信中继节点，支持 UAV 与基站通信
- **任务流**：动态生成的时间敏感任务（带 deadline）
- **通信模型**：基于距离和障碍物的 SNR 计算
- **仿真环境**：Gazebo Harmonic 物理仿真 + ROS 2 Jazzy 通信框架
- **导航系统**：Nav2 自主导航（全局规划 + 局部避障）

## 项目结构

```
uav-ugv-ws/
├── ag_coop/                      # 任务规划核心代码（Python）
│   ├── agcoop/
│   │   ├── map/                  # 地图加载与处理
│   │   ├── comm/                 # 通信模型（SNR 计算）
│   │   ├── tasks/                # 任务系统
│   │   └── env/                  # RL 环境（Gymnasium）
│   ├── configs/                  # 配置文件
│   ├── maps/                     # 地图文件
│   ├── scripts/                  # 校准脚本
│   └── tests/                    # 单元测试
│
├── uav_ugv_ws/                   # ROS 2 工作空间
│   └── src/
│       ├── uav_ugv_bringup/      # 仿真启动包
│       │   ├── launch/           # Launch 文件
│       │   │   ├── bringup_all.launch.py       # 主启动文件
│       │   │   ├── spawn_turtlebot.launch.py   # TurtleBot3 生成（支持多机）
│       │   │   ├── nav2_simple_launch.py       # Nav2 导航
│       │   │   └── nav2_launch.py              # Nav2 完整版
│       │   ├── config/           # 配置文件
│       │   │   └── nav2_params.yaml            # Nav2 参数
│       │   └── uav_ugv_bringup/  # Python 节点
│       │       └── circle_demo.py              # UAV+UGV 圆周演示
│       ├── px4_msgs/             # PX4 消息定义
│       └── px4_ros_com/          # PX4-ROS 2 通信
│
├── PX4-Autopilot/                # PX4 固件（v1.17）
├── Micro-XRCE-DDS-Agent/         # DDS Agent
├── DEVLOG.md                     # 详细开发日志
└── README.md                     # 本文件
```

## 开发进度

### 阶段一：任务规划核心（ag_coop）

#### ✅ Day1-4：基础系统
- **Day1**：地图加载（GridMap）+ 坐标系统
- **Day2**：通信模型（SNR 计算，距离衰减 + 障碍物惩罚）
- **Day3**：通信阈值校准（推荐 `snr_threshold_db = -9.0`）
- **Day4**：任务系统（Task/TaskStream/TaskManager/VirtualUAVExecutor）

#### ✅ Day8-9：强化学习环境
- **Day8**：通信感知启发式基线（Communication-Aware Heuristic）
- **Day9**：Gymnasium 环境设计（`UAVUGVEnv`）
- **Day10**：PPO 训练集成（Stable-Baselines3）

### 阶段二：ROS 2 仿真集成

#### ✅ Day11：PX4 + TurtleBot3 联合仿真
- 搭建 ROS 2 Jazzy + Gazebo Harmonic + PX4 v1.17 环境
- 解决 ROS 2 Jazzy + XRCE-DDS 兼容性（切换到 CycloneDDS）
- 实现 UAV offboard 圆周飞行 + UGV 地面环绕演示
- 修复 Gazebo Harmonic DiffDrive 插件话题命名问题

#### ✅ Day12：Nav2 导航系统
- 配置 Nav2 自主导航（NavfnPlanner + DWB 局部规划器）
- 修复 TF 树（添加 robot_state_publisher + TF 桥接）
- 解决 velocity_smoother 激活问题（改为直接发布 cmd_vel）
- 调参优化（允许后退、增强障碍物回避、调整膨胀半径）
- 验证仿真时间同步（/clock 桥接）

#### ✅ Day13：多机 UGV 独立控制
- 实现 3 台 TurtleBot3 独立控制（动态 SDF 话题替换）
- 修复 Gazebo Harmonic 话题命名问题（SDF 相对路径不加模型前缀）
- 使用 `-string` 参数动态生成 SDF（替换 cmd_vel/odom/scan 等话题）

#### ✅ Day14：PX4 ROS 2 通信要点
- 发现 `ros2 topic pub` 无法控制 PX4（QoS 不匹配）
- 必须用 Python 节点 + 手动设置 QoS（BEST_EFFORT + TRANSIENT_LOCAL）
- 新版 PX4 话题带 `_v1` 后缀（如 `vehicle_status_v1`）
- Offboard 起飞流程：持续发 setpoint → 切 offboard + ARM → 发目标位置

## 快速开始

### 环境要求

- Ubuntu 24.04 LTS（推荐 WSL2）
- ROS 2 Jazzy
- Gazebo Harmonic
- Python 3.12+
- PX4 Autopilot v1.17

### 系统依赖安装

```bash
# ROS 2 Jazzy（参考官方文档）
# Gazebo Harmonic
sudo apt install gz-harmonic

# ROS 2 - Gazebo 桥接
sudo apt install ros-jazzy-ros-gz

# Nav2 导航
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup

# CycloneDDS（必需，用于 PX4 通信）
sudo apt install ros-jazzy-rmw-cyclonedds-cpp

# Python 依赖（ag_coop）
pip install numpy pyyaml gymnasium stable-baselines3
```

### 环境配置

在 `~/.bashrc` 中添加：

```bash
# ROS 2 Jazzy
source /opt/ros/jazzy/setup.bash

# 使用 CycloneDDS（必需，FastRTPS 无法与 PX4 XRCE-DDS 通信）
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# 工作空间
source ~/anders/ART_MAPF/uav-ugv-ws/uav_ugv_ws/install/setup.bash

# 过滤 CycloneDDS 警告（可选）
export RCUTILS_CONSOLE_OUTPUT_FORMAT="[{severity}] [{name}]: {message}"
```

### 编译 ROS 2 工作空间

```bash
cd uav_ugv_ws
colcon build --symlink-install
source install/setup.bash
```

### 运行仿真

#### 方式一：使用启动脚本（推荐）

```bash
# 在项目根目录
./start.sh
```

该脚本会自动启动：
1. PX4 SITL（Gazebo 中的 x500 四旋翼）
2. Micro-XRCE-DDS Agent（PX4-ROS 2 桥接）
3. TurtleBot3 生成（可配置数量）
4. ROS 2 - Gazebo 桥接

#### 方式二：手动启动

```bash
# Terminal 1 - PX4 SITL
cd PX4-Autopilot
make px4_sitl gz_x500

# 在 PX4 shell 中配置参数（禁用 RC 和数据链路丢失保护）
param set COM_RCL_EXCEPT 4
param set NAV_RCL_ACT 0
param set NAV_DLL_ACT 0

# Terminal 2 - DDS Agent
cd Micro-XRCE-DDS-Agent
MicroXRCEAgent udp4 -p 8888

# Terminal 3 - 生成 TurtleBot3（3 台）
source uav_ugv_ws/install/setup.bash
ros2 launch uav_ugv_bringup spawn_turtlebot.launch.py num_robots:=3

# Terminal 4 - 运行演示（UAV + UGV 圆周运动）
ros2 run uav_ugv_bringup circle_demo
```

### 运行 Nav2 导航

```bash
# 启动 Nav2（在 TurtleBot3 已生成的情况下）
ros2 launch uav_ugv_bringup nav2_simple_launch.py

# 在 RViz 中设置目标点
# 使用 "2D Goal Pose" 工具点击地图设置导航目标
```

### 测试多机 UGV 独立控制

```bash
# 生成 3 台 TurtleBot3
ros2 launch uav_ugv_bringup spawn_turtlebot.launch.py num_robots:=3

# 分别控制每台车
ros2 topic pub --once /tb3_0/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
ros2 topic pub --once /tb3_1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
ros2 topic pub --once /tb3_2/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
```

## 任务规划系统（ag_coop）

### 运行测试

```bash
cd ag_coop

# 运行所有测试
python -m pytest tests/

# 运行任务系统验收测试
python tests/test_day4_validation.py
```

### 校准脚本

```bash
# 任务负载校准
python scripts/sweep_task_load.py

# 通信阈值校准
python scripts/sweep_comm_threshold.py
```

### 配置参数（ag_coop/configs/default.yaml）

#### 任务参数（已校准）

```yaml
tasks:
  enabled: true
  arrival_process: "bernoulli"
  arrival_rate: 0.1             # 每步生成任务概率
  deadline_min: 25              # 最小 deadline（步数）
  deadline_max: 60              # 最大 deadline（步数）
  max_active: 20                # 任务池最大容量
  top_m: 5                      # Top-M 任务数量
  service_time: 2               # 到点服务时间（步数）
```

**任务负载 Profile：**
- **Light**：`arrival_rate=0.05, deadline=[25,60]` → miss_rate=1.2%
- **Default**：`arrival_rate=0.10, deadline=[25,60]` → miss_rate=23.4% ✅
- **Heavy**：`arrival_rate=0.20, deadline=[25,60]` → miss_rate=69.5%

#### 通信参数（已校准）

```yaml
comm:
  enabled: true
  tx_power_db: 0.0              # 基准 SNR
  pathloss_n: 2.0               # 距离衰减指数
  obstacle_penalty_db: 6.0      # 每穿过一个障碍格扣多少 dB
  snr_threshold_db: -9.0        # outage 阈值
  eps_m: 0.05                   # 避免 log(0) 的小量
```

**通信 Profile：**
- **Relaxed**：`snr_threshold_db=-12.0` → outage=6%
- **Default**：`snr_threshold_db=-9.0` → outage=14% ✅
- **Strict**：`snr_threshold_db=-7.0` → outage=26%

## 关键技术要点

### PX4 ROS 2 通信

**QoS 配置（必需）**：PX4 XRCE-DDS 使用 `BEST_EFFORT` + `TRANSIENT_LOCAL`，必须手动设置 QoS：

```python
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

px4_qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)

# 订阅 PX4 话题
self.create_subscription(VehicleStatus, '/fmu/out/vehicle_status_v1', callback, px4_qos)

# 发布到 PX4
self.create_publisher(VehicleCommand, '/fmu/in/vehicle_command', px4_qos)
```

**注意**：
- `ros2 topic pub` 无法控制 PX4（QoS 不匹配）
- 新版 PX4 话题带 `_v1` 后缀（如 `vehicle_status_v1`）
- `timestamp` 字段必须填写（微秒），不能为 0

### Gazebo Harmonic 多机器人

**话题命名问题**：SDF 插件中的相对话题名不会自动加模型前缀，多机场景必须手动替换为绝对路径：

```python
def make_robot_sdf(sdf_template: str, name: str) -> str:
    sdf = sdf_template
    sdf = sdf.replace('<topic>cmd_vel</topic>', f'<topic>/{name}/cmd_vel</topic>')
    sdf = sdf.replace('<odom_topic>odom</odom_topic>', f'<odom_topic>/{name}/odom</odom_topic>')
    # ... 其他话题替换
    return sdf
```

**ros_gz_bridge 方向**：
- `]` = ROS2→Gazebo（用于 cmd_vel）
- `[` = Gazebo→ROS2（用于 scan/odom/tf）

### Nav2 导航调参经验

**关键参数**：
- `min_vel_x: -0.1`（允许后退，使 backup recovery 生效）
- `inflation_radius: 0.75`（增大膨胀半径，远离墙壁）
- `BaseObstacle.scale: 0.08`（增强障碍物回避权重）
- `required_movement_radius: 0.3`（更快检测卡住）
- `movement_time_allowance: 5s`（更快触发 recovery）

### WSL2 优化

**GUI 修复**（添加到 `~/.bashrc`）：
```bash
alias fix-gui='sudo killall -9 Xwayland; sleep 1; xclock &'
```

**日志过滤**：
```bash
# 过滤 CycloneDDS 警告
alias ros2-clean='ros2 2>&1 | grep -v "Failed to parse type hash"'
```

## 开发日志

详细的开发日志请参考 [DEVLOG.md](DEVLOG.md)。

## 许可证

MIT License

## 联系方式

如有问题，请联系项目维护者。
