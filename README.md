<div align="center">

# 🚁 UAV-UGV Cooperative System

**Communication-Constrained Multi-Robot Task Planning and Coordination**

[![ROS 2](https://img.shields.io/badge/ROS_2-Jazzy-blue.svg)](https://docs.ros.org/en/jazzy/index.html)
[![Gazebo](https://img.shields.io/badge/Gazebo-Harmonic-orange.svg)](https://gazebosim.org/)
[![PX4](https://img.shields.io/badge/PX4-v1.17-green.svg)](https://px4.io/)
[![Python](https://img.shields.io/badge/Python-3.12+-yellow.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Documentation](#-documentation) • [Citation](#-citation)

<img src="https://via.placeholder.com/800x400/1a1a1a/ffffff?text=UAV-UGV+Cooperative+System+Demo" alt="System Demo" width="800"/>

</div>

---

## 📋 Overview

This project implements a **multi-robot cooperative system** for communication-constrained task planning, featuring:

- **Heterogeneous Robots**: PX4 x500 quadrotor (UAV) for task execution + TurtleBot3 Burger (UGV) as communication relay
- **Dynamic Task Stream**: Time-sensitive tasks with deadlines and Bernoulli arrival process
- **Communication Model**: SNR-based connectivity with distance attenuation and obstacle penalties
- **Autonomous Navigation**: Nav2 stack with global planning (Dijkstra) and local obstacle avoidance (DWB)
- **High-Fidelity Simulation**: Gazebo Harmonic physics + ROS 2 Jazzy middleware + PX4 SITL
- **RL Environment**: Gymnasium-compatible environment with PPO baseline (Stable-Baselines3)

### 🎯 Key Capabilities

| Component | Description |
|-----------|-------------|
| **Task Planning** | EDF scheduling, Top-M task selection, deadline-aware execution |
| **Communication** | SNR calculation, outage detection, relay-based connectivity |
| **Multi-Robot Control** | Independent control of multiple UGVs with dynamic SDF generation |
| **Path Planning** | Nav2 integration with recovery behaviors (backup, spin, wait) |
| **RL Training** | PPO agent training with communication-aware reward shaping |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Gazebo Harmonic Simulator                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PX4 x500    │  │ TurtleBot3   │  │ TurtleBot3   │  ...     │
│  │  (UAV)       │  │ (UGV #0)     │  │ (UGV #1)     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          │ XRCE-DDS         │ ros_gz_bridge    │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                         ROS 2 Jazzy                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ PX4 Offboard │  │ Nav2 Stack   │  │ Task Manager │          │
│  │ Controller   │  │ (per UGV)    │  │ (Python)     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  RL Agent (PPO)      │
                  │  Gymnasium Env       │
                  └──────────────────────┘
```

---

## 📁 Repository Structure

```
uav-ugv-ws/
├── 📦 ag_coop/                          # Task planning core (Python)
│   ├── agcoop/
│   │   ├── map/                         # Grid map loader (.map format)
│   │   ├── comm/                        # SNR-based communication model
│   │   ├── tasks/                       # Task stream & manager
│   │   └── env/                         # Gymnasium RL environment
│   ├── configs/default.yaml             # Calibrated parameters
│   ├── maps/                            # Test maps (32×32 grid)
│   ├── scripts/                         # Calibration scripts
│   └── tests/                           # Unit tests (pytest)
│
├── 🤖 uav_ugv_ws/                       # ROS 2 workspace
│   └── src/
│       ├── uav_ugv_bringup/             # Simulation launch package
│       │   ├── launch/
│       │   │   ├── bringup_all.launch.py         # Main launcher
│       │   │   ├── spawn_turtlebot.launch.py     # Multi-UGV spawner
│       │   │   ├── nav2_simple_launch.py         # Nav2 navigation
│       │   │   └── nav2_launch.py                # Nav2 (full stack)
│       │   ├── config/nav2_params.yaml           # Tuned Nav2 parameters
│       │   └── uav_ugv_bringup/
│       │       └── circle_demo.py                # UAV+UGV circle demo
│       ├── px4_msgs/                    # PX4 message definitions
│       └── px4_ros_com/                 # PX4-ROS 2 bridge
│
├── 🛩️ PX4-Autopilot/                    # PX4 firmware (v1.17)
├── 🔌 Micro-XRCE-DDS-Agent/             # DDS agent for PX4
├── 📝 DEVLOG.md                         # Detailed development log
└── 📖 README.md                         # This file
```

---

## ✨ Features

### 🎓 Research Contributions

- **Communication-Aware Planning**: Joint optimization of task assignment and UGV relay positioning
- **Deadline-Constrained Scheduling**: EDF-based task selection with slack analysis
- **Hybrid Simulation**: Combines high-level task planning (Python) with low-level control (ROS 2/PX4)
- **Calibrated Workloads**: Systematic parameter sweeps for task arrival rate and communication thresholds

### 🛠️ Engineering Highlights

- **Multi-Robot Scalability**: Dynamic SDF generation for independent UGV control (tested with 3 robots)
- **QoS-Aware Communication**: Proper QoS profiles for PX4 XRCE-DDS compatibility
- **Robust Navigation**: Tuned Nav2 parameters with recovery behaviors for cluttered environments
- **WSL2 Optimization**: GPU acceleration fixes and GUI recovery scripts

---

## 🚀 Installation

### Prerequisites

- **OS**: Ubuntu 24.04 LTS (native or WSL2)
- **ROS 2**: Jazzy Jalisco
- **Gazebo**: Harmonic
- **Python**: 3.12+

### System Dependencies

```bash
# Install ROS 2 Jazzy (follow official guide)
# https://docs.ros.org/en/jazzy/Installation.html

# Install Gazebo Harmonic
sudo apt install gz-harmonic

# Install ROS 2 - Gazebo bridge
sudo apt install ros-jazzy-ros-gz

# Install Nav2 navigation stack
sudo apt install ros-jazzy-navigation2 ros-jazzy-nav2-bringup

# Install CycloneDDS (required for PX4 communication)
sudo apt install ros-jazzy-rmw-cyclonedds-cpp

# Install TurtleBot3 packages
sudo apt install ros-jazzy-turtlebot3*
```

### Python Dependencies

```bash
# For ag_coop task planning
pip install numpy pyyaml gymnasium stable-baselines3 torch
```

### Build ROS 2 Workspace

```bash
cd uav_ugv_ws
colcon build --symlink-install
source install/setup.bash
```

### Environment Configuration

Add to `~/.bashrc`:

```bash
# ROS 2 setup
source /opt/ros/jazzy/setup.bash

# Use CycloneDDS (required for PX4 XRCE-DDS compatibility)
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

# Workspace setup
source ~/anders/ART_MAPF/uav-ugv-ws/uav_ugv_ws/install/setup.bash

# Optional: Filter CycloneDDS warnings
export RCUTILS_CONSOLE_OUTPUT_FORMAT="[{severity}] [{name}]: {message}"
```

---

## 🎮 Quick Start

### Option 1: Automated Launch (Recommended)

```bash
# Launch full system (PX4 SITL + DDS Agent + TurtleBot3)
./start.sh
```

### Option 2: Manual Launch

#### Terminal 1: PX4 SITL

```bash
cd PX4-Autopilot
make px4_sitl gz_x500

# In PX4 shell, disable RC/datalink failsafes
param set COM_RCL_EXCEPT 4
param set NAV_RCL_ACT 0
param set NAV_DLL_ACT 0
```

#### Terminal 2: DDS Agent

```bash
cd Micro-XRCE-DDS-Agent
MicroXRCEAgent udp4 -p 8888
```

#### Terminal 3: Spawn Robots

```bash
source uav_ugv_ws/install/setup.bash

# Spawn 3 TurtleBot3 robots
ros2 launch uav_ugv_bringup spawn_turtlebot.launch.py num_robots:=3
```

#### Terminal 4: Run Demo

```bash
# UAV offboard circle + UGV ground circle
ros2 run uav_ugv_bringup circle_demo
```

### Run Nav2 Navigation

```bash
# Launch Nav2 for autonomous navigation
ros2 launch uav_ugv_bringup nav2_simple_launch.py

# Set goal in RViz using "2D Goal Pose" tool
```

### Test Multi-Robot Control

```bash
# Control individual UGVs
ros2 topic pub --once /tb3_0/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
ros2 topic pub --once /tb3_1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
ros2 topic pub --once /tb3_2/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.2}}"
```

---

## 📊 Task Planning System (ag_coop)

### Run Tests

```bash
cd ag_coop

# Run all unit tests
python -m pytest tests/ -v

# Run task system validation
python tests/test_day4_validation.py
```

### Calibration Scripts

```bash
# Sweep task arrival rate and deadline range
python scripts/sweep_task_load.py

# Sweep communication SNR threshold
python scripts/sweep_comm_threshold.py
```

### Configuration Parameters

#### Task Parameters (Calibrated)

```yaml
tasks:
  arrival_rate: 0.1          # Task generation probability per step
  deadline_min: 25           # Minimum deadline (steps)
  deadline_max: 60           # Maximum deadline (steps)
  max_active: 20             # Task pool capacity
  top_m: 5                   # Number of tasks to select (EDF)
  service_time: 2            # Service time at task location (steps)
```

**Workload Profiles:**

| Profile | `arrival_rate` | `deadline` | `miss_rate` | Description |
|---------|----------------|------------|-------------|-------------|
| Light   | 0.05           | [25, 60]   | 1.2%        | Low pressure |
| Default | 0.10           | [25, 60]   | 23.4% ✅    | Balanced |
| Heavy   | 0.20           | [25, 60]   | 69.5%       | High pressure |

#### Communication Parameters (Calibrated)

```yaml
comm:
  tx_power_db: 0.0           # Baseline SNR (dB)
  pathloss_n: 2.0            # Path loss exponent
  obstacle_penalty_db: 6.0   # Penalty per obstacle cell (dB)
  snr_threshold_db: -9.0     # Outage threshold (dB)
```

**Communication Profiles:**

| Profile | `snr_threshold_db` | Outage Rate | Description |
|---------|--------------------|-------------|-------------|
| Relaxed | -12.0              | 6%          | Lenient connectivity |
| Default | -9.0               | 14% ✅      | Balanced |
| Strict  | -7.0               | 26%         | Strict connectivity |

---

## 🔧 Technical Details

### PX4 ROS 2 Communication

**Critical**: PX4 XRCE-DDS uses `BEST_EFFORT` + `TRANSIENT_LOCAL` QoS. You **must** configure QoS manually:

```python
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy

px4_qos = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    durability=DurabilityPolicy.TRANSIENT_LOCAL,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,
)

# Subscribe to PX4 topics
self.create_subscription(VehicleStatus, '/fmu/out/vehicle_status_v1', callback, px4_qos)

# Publish to PX4
self.create_publisher(VehicleCommand, '/fmu/in/vehicle_command', px4_qos)
```

**Important Notes:**
- `ros2 topic pub` **will not work** with PX4 (QoS mismatch)
- PX4 v1.17 topics have `_v1` suffix (e.g., `vehicle_status_v1`)
- `timestamp` field must be filled (microseconds), cannot be 0

### Gazebo Harmonic Multi-Robot

**Topic Naming Issue**: SDF plugin relative topics do **not** auto-prefix with model name. For multi-robot scenarios, manually replace with absolute paths:

```python
def make_robot_sdf(sdf_template: str, name: str) -> str:
    sdf = sdf_template
    sdf = sdf.replace('<topic>cmd_vel</topic>', f'<topic>/{name}/cmd_vel</topic>')
    sdf = sdf.replace('<odom_topic>odom</odom_topic>', f'<odom_topic>/{name}/odom</odom_topic>')
    # ... other topic replacements
    return sdf
```

**ros_gz_bridge Direction:**
- `]` = ROS2→Gazebo (for `cmd_vel`)
- `[` = Gazebo→ROS2 (for `scan`, `odom`, `tf`)

### Nav2 Tuning Tips

**Key Parameters:**

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `min_vel_x` | -0.1 | Enable backward motion for recovery |
| `inflation_radius` | 0.75 | Keep distance from walls |
| `BaseObstacle.scale` | 0.08 | Increase obstacle avoidance weight |
| `required_movement_radius` | 0.3 | Faster stuck detection |
| `movement_time_allowance` | 5s | Faster recovery trigger |

### WSL2 Optimization

**GUI Recovery** (add to `~/.bashrc`):
```bash
alias fix-gui='sudo killall -9 Xwayland; sleep 1; xclock &'
```

**Log Filtering**:
```bash
alias ros2-clean='ros2 2>&1 | grep -v "Failed to parse type hash"'
```

---

## 📈 Development Timeline

### Phase 1: Task Planning Core (ag_coop)

| Day | Milestone | Status |
|-----|-----------|--------|
| Day 1-4 | Grid map, communication model, task system | ✅ |
| Day 8 | Communication-aware heuristic baseline | ✅ |
| Day 9 | Gymnasium environment design | ✅ |
| Day 10 | PPO training integration | ✅ |

### Phase 2: ROS 2 Simulation Integration

| Day | Milestone | Status |
|-----|-----------|--------|
| Day 11 | PX4 + TurtleBot3 joint simulation | ✅ |
| Day 12 | Nav2 navigation system | ✅ |
| Day 13 | Multi-UGV independent control | ✅ |
| Day 14 | PX4 ROS 2 communication refinement | ✅ |

---

## 📚 Documentation

- **[DEVLOG.md](DEVLOG.md)**: Detailed development log with troubleshooting notes
- **[ag_coop/README.md](ag_coop/README.md)**: Task planning system documentation
- **ROS 2 API**: Auto-generated from docstrings (coming soon)

---

## 🐛 Troubleshooting

### Issue: PX4 not receiving commands

**Solution**: Check QoS profile. Use `BEST_EFFORT` + `TRANSIENT_LOCAL` (see [PX4 ROS 2 Communication](#px4-ros-2-communication))

### Issue: TurtleBot3 not moving in Gazebo

**Solution**: Verify topic names with `gz topic -i -t /tb3_0/cmd_vel`. Ensure SDF uses absolute paths (see [Gazebo Harmonic Multi-Robot](#gazebo-harmonic-multi-robot))

### Issue: Nav2 robot stuck at corners

**Solution**: Tune `inflation_radius`, `BaseObstacle.scale`, and enable backward motion (see [Nav2 Tuning Tips](#nav2-tuning-tips))

### Issue: WSL2 Gazebo GUI not showing

**Solution**: Run `fix-gui` alias or manually restart Xwayland (see [WSL2 Optimization](#wsl2-optimization))

---

## 📄 Citation

If you use this work in your research, please cite:

```bibtex
@misc{uav-ugv-coop-2026,
  title={Communication-Constrained UAV-UGV Cooperative Task Planning},
  author={Your Name},
  year={2026},
  howpublished={\url{https://github.com/yourusername/uav-ugv-ws}}
}
```

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **PX4 Autopilot**: Open-source flight control software
- **ROS 2**: Robot Operating System 2
- **Gazebo**: High-fidelity robot simulator
- **Nav2**: Navigation framework for mobile robots
- **Stable-Baselines3**: Reliable RL implementations

---

<div align="center">

**[⬆ Back to Top](#-uav-ugv-cooperative-system)**

Made with ❤️ for robotics research

</div>
