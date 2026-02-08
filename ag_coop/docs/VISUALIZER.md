# AGCoop Visualizer

离线回放和可视化 AGCoop 实验结果的工具。

## 功能特性

- ✅ **离线回放**：从 `outputs/<run_dir>/` 加载并回放实验结果
- ✅ **地图显示**：显示网格地图，障碍物和可通行区域
- ✅ **UGV 轨迹**：实时显示 UGV 位置和移动轨迹
- ✅ **任务可视化**：显示任务的出现、完成、过期状态
- ✅ **交互控制**：暂停/继续、加速/减速、单步前进/后退、重启
- ✅ **HUD 信息**：显示时间步、决策步、MAPF 状态、通信指标等

## 快速开始

### 1. 生成实验数据

首先运行实验生成输出数据（会自动生成 `tasks.json`）：

```bash
# 运行 greedy baseline
python scripts/run_day7_baselines.py --method greedy --seed 0

# 运行 MAPF
python scripts/run_day7_baselines.py --method mapf --seed 0
```

### 2. 启动可视化器

```bash
python scripts/visualize.py --run outputs/day7_greedy_seed0
```

### 3. 交互控制

可视化器启动后，可以使用以下快捷键：

| 快捷键 | 功能 |
|--------|------|
| **Space** | 暂停/继续播放 |
| **↑** | 加速（2x, 4x, 8x, 16x） |
| **↓** | 减速（0.5x, 0.25x, 0.125x） |
| **→** | 单步前进（暂停时） |
| **←** | 单步后退（暂停时） |
| **R** | 重启（回到 t=0） |
| **G** | 显示/隐藏网格线 |
| **T** | 显示/隐藏任务 |
| **O** | 显示/隐藏目标点 |
| **ESC/Q** | 退出 |

## 命令行参数

```bash
python scripts/visualize.py --help
```

可用参数：

- `--run <dir>`: 运行目录路径（必需）
- `--fps <int>`: 目标帧率（默认 60）
- `--cell-px <int>`: 每个格子的像素大小（默认 30）
- `--start-t <int>`: 起始时间步（默认 0）

示例：

```bash
# 使用更大的格子尺寸
python scripts/visualize.py --run outputs/day7_greedy_seed0 --cell-px 40

# 从第 100 步开始播放
python scripts/visualize.py --run outputs/day7_greedy_seed0 --start-t 100

# 降低帧率（适合慢速机器）
python scripts/visualize.py --run outputs/day7_greedy_seed0 --fps 30
```

## 数据格式

Visualizer 从以下文件加载数据：

### 必需文件

1. **`config_resolved.yaml`** - 实验配置
2. **`trace.jsonl`** - 逐步状态记录
3. **`init.json`** - 初始状态
4. **`metrics.json`** - 最终指标

### 可选文件

5. **`tasks.json`** - 任务信息（用于任务可视化）

`tasks.json` 格式：

```json
{
  "schema_version": 1,
  "grid": {
    "width": 20,
    "height": 20
  },
  "tasks": [
    {
      "id": 0,
      "cell": [9, 5],
      "release_t": 16,
      "deadline_t": 45,
      "completed_t": 31,
      "status": "completed"
    }
  ]
}
```

## 可视化元素

### 地图

- **白色格子**：可通行区域
- **深灰色格子**：障碍物
- **浅灰色线**：网格线（可用 G 键切换）

### UGV

- **彩色圆圈**：UGV 当前位置
  - 红色：UGV 0
  - 蓝色：UGV 1
  - 绿色：UGV 2
  - ...
- **圆圈内数字**：UGV ID

### 任务

- **绿色方块**：不紧急任务（距离 deadline 较远）
- **红色方块**：紧急任务（接近 deadline）
- **蓝色方块**：刚完成的任务（显示 3 步）
- **灰色方块**：已过期未完成的任务

### 目标点

- **黄色 X 标记**：UGV 当前目标位置

### HUD 信息栏

显示以下信息：

- **第一行**：时间步、播放速度、播放状态
- **第二行**：决策步标记、MAPF 调用状态和耗时
- **第三行**：通信状态（outage、SNR）、活跃任务数、完成任务
- **第四行**：快捷键提示

## 测试

运行数据加载测试（不需要显示窗口）：

```bash
python scripts/test_visualizer.py
```

## 架构

Visualizer 模块结构：

```
agcoop/vis/
  __init__.py         # 模块入口
  io_runs.py          # 数据加载（RunData, GridMap）
  task_tracker.py     # 任务跟踪（TaskTracker）
  renderer.py         # 渲染器（Renderer）
  controls.py         # 控制状态和事件处理

scripts/
  visualize.py        # CLI 入口
  test_visualizer.py  # 测试脚本
```

## 依赖

- `pygame >= 2.0`
- `pyyaml`
- `numpy`

## 故障排除

### 问题：窗口无法显示

如果在无显示器的服务器上运行，可以使用虚拟显示：

```bash
# 安装 xvfb
sudo apt-get install xvfb

# 使用虚拟显示运行
xvfb-run python scripts/visualize.py --run outputs/day7_greedy_seed0
```

### 问题：tasks.json 不存在

旧的输出目录可能没有 `tasks.json`。重新运行实验即可生成：

```bash
python scripts/run_day7_baselines.py --method greedy --seed 0
```

### 问题：播放速度太快/太慢

使用 `↑` 和 `↓` 键调整播放速度，或使用 `--fps` 参数：

```bash
# 降低帧率
python scripts/visualize.py --run outputs/day7_greedy_seed0 --fps 30
```

## 开发历史

- **2026-02-08**: 初始版本，支持地图、UGV、任务、HUD 显示和交互控制
