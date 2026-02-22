# CoopBridge 使用指南

## 概述

CoopBridge 是连接 ag_coop 决策层和 Gazebo 仿真的桥接节点，实现 UAV-UGV 协同路径规划和执行。

## 架构

```
┌─────────────────────────────────────┐
│  ag_coop (Prioritized Planning)    │  ← 路径规划 + 避障
│  - 读取地图障碍物                    │
│  - 规划无碰撞路径                    │
│  - 输出航点序列                      │
└──────────────┬──────────────────────┘
               │ 航点序列
               ↓
┌─────────────────────────────────────┐
│  CoopBridgeNode (时间同步)          │  ← 协调执行
│  - 坐标转换: 格子 → 世界坐标        │
│  - 全局时间步管理                    │
│  - 等待所有机器人到达当前航点        │
└──────────────┬──────────────────────┘
               │ 单个目标点
               ↓
┌─────────────────────────────────────┐
│  PI Controller (精确执行)           │  ← 底层控制
│  - 转向目标                          │
│  - 直线前进                          │
│  - 到达判定 (< 0.1m)                │
└─────────────────────────────────────┘
```

## 快速开始

### 1. 测试基础功能

```bash
# 测试 ag_coop 集成和坐标转换
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/uav_ugv_ws
python3 src/coop_bridge/scripts/test_coop_bridge.py
```

**预期输出**:
```
✅ 地图加载成功: 20x20
✅ ag_coop 环境初始化成功
✅ 所有坐标转换测试通过
✅ ag_coop 规划测试完成
🎉 所有测试通过！
```

### 2. 启动完整系统

**终端 1: 启动 Gazebo 仿真**
```bash
ros2 launch uav_ugv_bringup bringup_all.launch.py
```

等待 Gazebo 完全启动（约 20 秒），确保看到：
- 1 个 UAV（无人机）
- 3 个 UGV（TurtleBot3）

**终端 2: 启动 CoopBridgeNode**
```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/uav_ugv_ws
source install/setup.bash
ros2 launch coop_bridge coop_bridge.launch.py
```

### 3. 预期行为

1. **规划阶段**:
   - CoopBridgeNode 调用 ag_coop 进行路径规划
   - 打印每个 UGV 的航点序列
   - 示例: `UGV 0 path: (3.5,2.5) → (4.5,2.5) → (5.5,3.5) → ...`

2. **执行阶段**:
   - UGV 按照航点序列移动
   - **不会撞墙**（因为 ag_coop 规划了无碰撞路径）
   - 所有 UGV 到达当前航点后，才移动到下一个航点（时间同步）

3. **完成阶段**:
   - 所有 UGV 到达最终目标点
   - 打印 "✅ All UGVs reached final targets!"
   - 机器人停止移动

## 关键参数

### CoopBridgeNode 参数

```python
# 地图配置
map_file = '/home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop/maps/map_01.map'
grid_size = 20              # 地图大小 20x20
cell_resolution = 1.0       # 每个格子 1.0m

# 控制参数
THRE_ROBOT_ON_TARGET = 0.1  # 到达阈值（米）
control_frequency = 10.0    # 控制频率（Hz）
```

### PI 控制器参数

```python
KP_linear = 0.25      # 线速度比例增益
KI_linear = 0.05      # 线速度积分增益
KP_angular = 0.5      # 角速度比例增益
KI_angular = 0.01     # 角速度积分增益
ANGLE_THRE = 0.4      # 转向阈值（弧度）
```

## 坐标系统

### ag_coop 格子坐标
- 原点: 左上角 (0, 0)
- 格式: (row, col)
- 范围: 0-19

### Gazebo 世界坐标
- 原点: 左下角 (0, 0)
- 格式: (x, y)
- 范围: 0-20m

### 转换公式
```python
x = (col + 0.5) * 1.0  # 格子中心
y = (row + 0.5) * 1.0
```

## 故障排查

### 问题 1: "No UGVs found!"

**原因**: Gazebo 还没完全启动

**解决**: 等待 20 秒后再启动 CoopBridgeNode

### 问题 2: 机器人不动

**原因**: 可能是 odom 数据没有收到

**检查**:
```bash
ros2 topic echo /tb3_0/odom --field pose.pose.position
```

### 问题 3: 机器人撞墙

**原因**: 如果使用 CoopBridgeNode 还撞墙，说明坐标转换有问题

**检查**:
```bash
# 运行测试脚本验证坐标转换
python3 src/coop_bridge/scripts/test_coop_bridge.py
```

### 问题 4: "ModuleNotFoundError: No module named 'gymnasium'"

**解决**:
```bash
pip3 install gymnasium --break-system-packages
```

## 文件结构

```
coop_bridge/
├── coop_bridge/
│   ├── __init__.py
│   ├── coop_bridge_node.py      # 主节点
│   ├── ugv_controller.py         # PI 控制器
│   └── test_ugv_controller.py    # PI 控制器测试
├── launch/
│   ├── coop_bridge.launch.py           # 主启动文件
│   └── test_ugv_controller.launch.py   # 测试启动文件
├── scripts/
│   └── test_coop_bridge.py       # 快速测试脚本
├── package.xml
└── setup.py
```

## API 参考

### UGVController

```python
from coop_bridge.ugv_controller import UGVController

# 创建控制器
controller = UGVController(node, robot_id=0)

# 设置目标
controller.set_target(x=5.0, y=5.0)

# 执行控制步（在 10Hz 循环中调用）
controller.control_step()

# 检查是否到达
if controller.is_at_target():
    print("到达目标！")

# 停止机器人
controller.halt()
```

### CoopBridgeNode

CoopBridgeNode 是自动运行的，不需要手动调用 API。

## 下一步

1. **测试 CoopBridgeNode**
   - 验证 ag_coop 集成
   - 检查坐标转换
   - 观察时间同步机制

2. **添加 UAV 控制**
   - 实现 UAV 的 offboard 控制
   - 集成 UAV 和 UGV 的协同

3. **优化性能**
   - 调整控制参数
   - 优化路径规划
   - 改进时间同步

## 参考资料

- GitHub MAPF 仓库: https://github.com/eferreirafilho/mapf
- ag_coop 文档: `/home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop/`
- DEVLOG.md: 详细开发日志
