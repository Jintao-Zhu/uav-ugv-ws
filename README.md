# AGCoop: Air-Ground Cooperative Multi-Agent System

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**AGCoop** 是一个用于研究空地协同多智能体系统的仿真平台，专注于 UAV-UGV 协作场景下的任务分配、路径规划和通信约束问题。

## 🎯 项目特点

- **完整的仿真环境**：支持多 UGV + 单 UAV 的协同任务执行
- **真实的通信模型**：考虑信号衰减、遮挡和 outage 约束
- **灵活的地图支持**：兼容 MovingAI benchmark 和 ROS map_server 格式
- **可复现的实验**：完整的日志系统和指标输出
- **模块化设计**：清晰的代码结构，易于扩展

## 📋 目录

- [快速开始](#快速开始)
- [系统架构](#系统架构)
- [核心功能](#核心功能)
- [使用指南](#使用指南)
- [开发进度](#开发进度)
- [贡献指南](#贡献指南)

## 🚀 快速开始

### 安装依赖

```bash
# 克隆仓库
cd uav-ugv-ws/ag_coop

# 安装依赖
pip install -r requirements.txt
```

### 运行示例

```bash
# 运行一个完整的 episode
python scripts/run_one_episode.py --seed 42

# 检查地图
python scripts/inspect_map.py maps/map_01.map --detailed

# 生成候选点
python scripts/gen_candidates.py maps/map_01.map --visualize

# 测试坐标映射
python scripts/test_mapping.py maps/map_01.map --test-all
```

## 🏗️ 系统架构

```
ag_coop/
├── agcoop/                 # 核心代码
│   ├── env/               # 仿真环境
│   │   └── core.py        # AGCoopEnv 主类
│   ├── map/               # 地图模块
│   │   ├── grid_map.py    # GridMap 数据结构
│   │   ├── io_text.py     # MovingAI 格式 I/O
│   │   ├── io_ros.py      # ROS 格式 I/O
│   │   ├── mapping.py     # 坐标映射（权威实现）
│   │   └── neighbors.py   # 邻接图和最短路径
│   └── utils/             # 工具函数
│       ├── logger.py      # 日志记录
│       └── io.py          # 文件 I/O
├── scripts/               # 工具脚本
│   ├── run_one_episode.py      # 一键运行
│   ├── inspect_map.py          # 地图检查
│   ├── gen_candidates.py       # 候选点生成
│   └── test_mapping.py         # 映射测试
├── configs/               # 配置文件
│   └── default.yaml       # 默认配置
├── maps/                  # 地图文件
│   ├── map_01.map         # MovingAI 格式
│   └── test_ros.yaml      # ROS 格式
└── outputs/               # 输出目录
    └── run_*/             # 实验结果
        ├── trace.jsonl           # 步骤记录
        ├── metrics.json          # 最终指标
        └── config_resolved.yaml  # 完整配置
```

## 🔧 核心功能

### 1. 地图系统

**支持格式：**
- MovingAI `.map` 格式（标准 MAPF benchmark）
- ROS `map_server` 格式（`.yaml` + `.pgm`）
- 简单文本格式（0/1 矩阵）

**核心功能：**
- 自动格式检测和加载
- 坐标系转换（world ↔ cell）
- 邻居查询（4-连通/8-连通）
- BFS 最短路径计算

**坐标系约定：**
```python
# 内部坐标：(i, j) = (row, col) = (y_index, x_index)
# - i: 行索引（y 方向，0 = 底部）
# - j: 列索引（x 方向，0 = 左侧）
# - origin: cell(0,0) 左下角的世界坐标

# 世界坐标：(x, y)
# - x = origin_x + (j + 0.5) * resolution
# - y = origin_y + (i + 0.5) * resolution
```

**外部求解器兼容：**
```python
from agcoop.map import mapping

# 转换为求解器坐标（MovingAI 风格）
solver_x, solver_y = mapping.to_solver_coords(i, j, height)

# 格式化为求解器实例
instance = mapping.format_solver_instance(starts, goals, height)
```

### 2. 仿真环境

**状态空间：**
- UGV 位置：`[(x, y), ...]`
- UAV 状态：当前搭载的 UGV ID
- 任务池：动态生成的任务列表
- 通信状态：outage 统计

**配置参数：**
```yaml
episode:
  horizon_steps: 100
  seed: 42
  decision_period: 5

robots:
  n_ugv: 3
  n_uav: 1

tasks:
  enabled: true
  arrival_rate: 0.1
  deadline_min: 20
  deadline_max: 50

comm:
  enabled: true
  snr_threshold: 0.0
```

### 3. 日志与指标

**输出文件：**

1. **trace.jsonl** - 每步记录
```json
{"t": 1, "ugv_pos": [[0,0],[0,0],[0,0]], "outage": 0, "decision_step": false, ...}
{"t": 2, "ugv_pos": [[0,0],[0,0],[0,0]], "outage": 1, "decision_step": false, ...}
```

2. **metrics.json** - 最终指标
```json
{
  "run_id": "map_01_N3_seed42_lambda0.1",
  "method": "static",
  "planner": "none",
  "tasks_completed": 15,
  "completion_rate": 75.0,
  "outage_percent": 12.5,
  "max_outage_streak": 3,
  "runtime_sec": 0.45,
  ...
}
```

3. **config_resolved.yaml** - 完整配置（用于复现）

## 📖 使用指南

### 基本使用

```python
from agcoop.env import AGCoopEnv
from agcoop.utils.io import load_config

# 加载配置
config = load_config('configs/default.yaml')

# 创建环境
env = AGCoopEnv(
    config,
    output_dir='outputs/my_run',
    enable_logging=True,
    method='greedy',
    planner='PIBT'
)

# 运行仿真
state = env.reset()
for t in range(config['episode']['horizon_steps']):
    state, reward, done, info = env.step()
    if done:
        break

# 获取指标
metrics = env.get_metrics()
print(f"Tasks completed: {metrics['tasks_completed']}")
```

### 地图操作

```python
from agcoop.map import auto_load_map, neighbors, mapping

# 加载地图
grid_map = auto_load_map('maps/map_01.map')

# 坐标转换
x, y = grid_map.cell_to_world(5, 10)
i, j = grid_map.world_to_cell(x, y)

# 最短路径
path = neighbors.shortest_path((0, 0), (10, 10), grid_map.grid)
dist = neighbors.shortest_path_length((0, 0), (10, 10), grid_map.grid)

# 距离地图
dist_map = neighbors.compute_distance_map((5, 5), grid_map.grid)
```

### 工具脚本

```bash
# 1. 运行实验
python scripts/run_one_episode.py \
    --config configs/default.yaml \
    --seed 42 \
    --method greedy \
    --planner PIBT

# 2. 检查地图
python scripts/inspect_map.py maps/map_01.map --detailed
# 输出：map_01_meta.json, map_01_preview.png, map_01_detailed.png

# 3. 生成候选点（用于 coverage baseline）
python scripts/gen_candidates.py maps/map_01.map \
    --num-candidates 12 \
    --min-degree 3 \
    --visualize
# 输出：map_01_candidates.json, map_01_candidates_viz.png

# 4. 测试坐标映射
python scripts/test_mapping.py maps/map_01.map --test-all
# 输出：map_01_mapping_report.json
```

## 📊 开发进度

### ✅ Day 1 - 基础框架
- [x] 环境核心（SystemState, AGCoopEnv）
- [x] 日志系统（TraceLogger, MetricsLogger）
- [x] 指标输出（metrics.json, trace.jsonl）
- [x] 一键运行脚本
- [x] 可复现性验证

### ✅ Day 2 - 地图系统
- [x] GridMap 数据结构
- [x] MovingAI .map 格式支持
- [x] ROS map_server 格式支持
- [x] 权威坐标映射系统（100% 往返精度）
- [x] 邻接图和 BFS 最短路径
- [x] 地图检查工具（预览图 + 元数据）
- [x] 映射单元测试（全量/抽样）
- [x] 候选点生成原型
- [x] **坐标系统加固与外部兼容性**

### 🚧 Day 3 - 通信模型（计划中）
- [ ] 信号传播模型（自由空间 + 遮挡）
- [ ] SNR 计算和 outage 判定
- [ ] 通信范围可视化
- [ ] 通信模型验收测试

### 🚧 Day 4+ - 高级功能（计划中）
- [ ] MAPF 规划器集成
- [ ] 任务分配策略
- [ ] 会合点选择
- [ ] Coverage baseline
- [ ] 强化学习接口

## 🔬 实验复现

所有实验都可以通过 seed 完全复现：

```bash
# 运行实验
python scripts/run_one_episode.py --seed 42 --out_name exp1

# 验证复现性
python scripts/run_one_episode.py --seed 42 --out_name exp2

# 比较结果
diff outputs/exp1/metrics.json outputs/exp2/metrics.json
# 除了 runtime_sec，所有指标应该完全一致
```

## 📝 配置说明

### 关键参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `horizon_steps` | 仿真步数 | 100 |
| `decision_period` | 决策周期 | 5 |
| `n_ugv` | UGV 数量 | 3 |
| `arrival_rate` | 任务到达率 | 0.1 |
| `deadline_min/max` | 任务截止时间范围 | 20-50 |
| `snr_threshold` | SNR 阈值 | 0.0 |

### 预留字段

为了保持 schema 稳定性，以下字段已预留（当前为占位值）：

**metrics.json:**
- `mapf_calls`, `mapf_success_calls`, `mapf_timeout_calls`
- `rendezvous_success`, `rendezvous_fail`, `emergency_landings`
- `snr_best_mean`, `snr_best_min`

**trace.jsonl:**
- `task_completed_ids`, `chosen_task_id`, `chosen_rendezvous`
- `mapf_called`, `mapf_success`, `mapf_plan_time_ms`
- `snr_best`

## 🐛 已知问题与注意事项

### 坐标系统
- **内部坐标**：`(i, j)` = `(row, col)`，`i=0` 在底部
- **求解器坐标**：`(x, y)` = `(col, row)`，`y=0` 在顶部
- 使用 `mapping.to_solver_coords()` 进行转换

### 地图格式
- MovingAI 格式：`@` = 障碍，`.` = 自由
- ROS 格式：高像素值 = 自由，低像素值 = 障碍
- 使用 `scripts/inspect_map.py` 验证地图方向

### 测试覆盖
- 默认抽样测试（快速）
- 使用 `--test-all` 进行全量测试（完整验证）

## 🤝 贡献指南

欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范
- 遵循 PEP 8
- 添加类型注解
- 编写单元测试
- 更新 DEVLOG.md

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📧 联系方式

- 项目主页：[GitHub Repository](https://github.com/yourusername/ag_coop)
- 问题反馈：[Issues](https://github.com/yourusername/ag_coop/issues)

## 🙏 致谢

- MovingAI benchmark 提供的地图格式标准
- ROS map_server 提供的地图格式规范
- 所有贡献者和测试者

---

**最后更新：** 2026-02-06
**版本：** Day 2 Complete
