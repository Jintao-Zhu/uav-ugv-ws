# UAV-UGV 协同系统（ag_coop）

基于通信约束和任务流的 UAV-UGV 协同路径规划与任务分配系统。

## 项目概述

本项目实现了一个多机器人协同系统，包含：
- **UAV（无人机）**：负责执行动态生成的任务
- **UGV（地面车）**：作为通信中继节点，支持 UAV 与基站通信
- **任务流**：动态生成的时间敏感任务（带 deadline）
- **通信模型**：基于距离和障碍物的 SNR 计算

## 项目结构

```
ag_coop/
├── agcoop/                 # 核心代码
│   ├── map/               # 地图加载与处理
│   ├── comm/              # 通信模型（SNR 计算）
│   ├── tasks/             # 任务系统（Day4）
│   │   ├── task.py        # Task 数据结构
│   │   ├── stream.py      # TaskStream 任务流生成器
│   │   ├── manager.py     # TaskManager 任务管理器
│   │   └── executor.py    # VirtualUAVExecutor 虚拟执行器
│   └── env/               # 环境（待实现）
├── configs/               # 配置文件
│   └── default.yaml       # 默认配置
├── maps/                  # 地图文件
│   └── map_01.map         # 测试地图（32x32）
├── scripts/               # 脚本工具
│   ├── sweep_comm_threshold.py  # 通信阈值校准
│   └── sweep_task_load.py       # 任务负载校准
├── tests/                 # 单元测试
└── outputs/               # 输出结果

```

## 开发进度

### ✅ Day1：坐标系统与地图加载
- 实现 `GridMap` 类（支持 `.map` 格式）
- 统一坐标系：`cell = (i, j)` 其中 `i=row(y), j=col(x)`
- 单元测试：`test_map.py`

### ✅ Day2：通信模型
- 实现 SNR 计算（距离衰减 + 障碍物惩罚）
- 公式：`SNR(dB) = P_tx - 10*n*log10(d+ε) - N_obs * penalty`
- 单元测试：`test_comm.py`

### ✅ Day3：通信阈值校准
- 实现 `sweep_comm_threshold.py` 扫描阈值 vs outage%
- 校准结果：`snr_threshold_db = -9.0` → outage=14%（平衡）
- 输出：SNR heatmap + metrics.json

### ✅ Day4：任务系统
- **Step 1-4**：实现完整任务流水线
  - `Task`：8 字段数据结构（id, release_t, cell, deadline_t, assigned_t, completed_t, status, tardiness）
  - `TaskStream`：Bernoulli 到达过程，可复现任务生成
  - `TaskManager`：任务池管理 + Top-M 选择（EDF/Random 策略）
  - `VirtualUAVExecutor`：虚拟执行器（Chebyshev 距离估算）

- **Step 5**：指标与 Trace 集成
  - 15 个指标：任务统计、完成时间分布、Slack 分析、系统拥塞
  - Trace 记录：每步的任务事件和状态

- **Step 6**：任务负载校准
  - 扫描 `arrival_rate × deadline_range`
  - 推荐参数：`arrival_rate=0.1, deadline=[25,60]` → miss_rate=23.4%

### 🚧 Day5：真实 UAV 运动（计划中）
- 集成 MAPF 路径规划（CBS/ECBS）
- 实现真实 UAV 运动（替换虚拟执行器）
- UAV-UGV 会合机制（rendezvous）

## 快速开始

### 安装依赖

```bash
pip install numpy pyyaml
```

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/

# 运行 Day4 验收测试
python tests/test_day4_validation.py
```

### 任务负载校准

```bash
# 扫描任务参数
python scripts/sweep_task_load.py

# 输出：outputs/task_load_sweep/sweep_results.json
```

### 通信阈值校准

```bash
# 扫描通信阈值
python scripts/sweep_comm_threshold.py

# 输出：outputs/comm_threshold_sweep/
```

## 配置说明

配置文件：`configs/default.yaml`

### 任务参数（已校准）

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
- **Light**：`arrival_rate=0.05, deadline=[25,60]` → miss_rate=1.2%（压力很小）
- **Default**：`arrival_rate=0.10, deadline=[25,60]` → miss_rate=23.4%（平衡）✅
- **Heavy**：`arrival_rate=0.20, deadline=[25,60]` → miss_rate=69.5%（压力大）

### 通信参数（已校准）

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
- **Relaxed**：`snr_threshold_db=-12.0` → outage=6%（通信宽松）
- **Default**：`snr_threshold_db=-9.0` → outage=14%（平衡）✅
- **Strict**：`snr_threshold_db=-7.0` → outage=26%（通信苛刻）

## 指标体系

### 任务统计（5 个）
- `total_generated`：生成的任务总数
- `total_dropped`：因容量满而丢弃的任务数
- `total_added`：加入任务池的任务数
- `total_completed`：完成的任务数
- `total_expired`：过期的任务数

### 关键指标（3 个）
- `completion_rate`：完成率（completed / added）
- `miss_rate`：错过率（expired / added）
- `mean_tardiness`：平均延迟（超期完成的延迟量）

### 完成时间分布（2 个）
- `mean_completion_time`：平均完成时间（completed_t - release_t）
- `p95_completion_time`：95 分位完成时间

### Slack 分析（2 个）
- `mean_slack_at_assignment`：分配时的 slack（deadline_t - assigned_t）
- `mean_slack_at_completion`：完成时的 slack（deadline_t - completed_t）

### 系统拥塞程度（2 个）
- `avg_active_tasks`：每步 active 任务数的平均值
- `active_tasks_end`：episode 结束时剩余的 active 任务数

## Day4 验收结果

使用校准后的参数（`arrival_rate=0.1, deadline=[25,60]`, 500 步）：

```json
{
  "total_generated": 47,
  "total_completed": 35,
  "total_expired": 11,
  "completion_rate": 0.7447,
  "miss_rate": 0.2340,
  "mean_tardiness": 0.0,
  "mean_completion_time": 20.63,
  "p95_completion_time": 43,
  "mean_slack_at_assignment": 32.40,
  "mean_slack_at_completion": 22.89,
  "avg_active_tasks": 1.49,
  "active_tasks_end": 0
}
```

**关键发现：**
- ✅ miss_rate=23.40% 在目标范围（10%-40%）
- ✅ completion_rate=74.47% 合理
- ✅ mean_tardiness=0.0（EDF 策略有效，所有完成任务都按时）
- ✅ avg_active_tasks=1.49（系统不拥塞）

## 开发日志

详细的开发日志请参考 [DEVLOG.md](DEVLOG.md)。

## 许可证

MIT License

## 联系方式

如有问题，请联系项目维护者。
