# AGCoop 环境核心 - 快速参考

## 安装和导入

```python
from agcoop import AGCoopEnv, SystemState, Task, seed_everything
import yaml
```

## 基本使用

### 1. 创建环境

```python
# 加载配置
with open("configs/default.yaml", 'r') as f:
    config = yaml.safe_load(f)

# 设置随机种子
seed_everything(config['episode']['seed'])

# 创建环境
env = AGCoopEnv(config)
```

### 2. 重置环境

```python
state = env.reset()

# state 包含:
# - state.t: 当前时间步
# - state.ugv_positions: UGV 位置列表
# - state.uav_onboard_ugv_id: UAV 所在 UGV 编号
# - state.task_pool: 任务列表
# - state.tasks_completed: 完成任务数
# - state.outage_steps: 通信中断步数
# - state.deadline_miss: 超期任务数
# - state.tardiness_sum: 延迟总和
```

### 3. 运行仿真

```python
done = False
while not done:
    state, reward, done, info = env.step()

    # info 包含:
    # - timestep: 当前时间步
    # - tasks_completed: 完成任务数
    # - outage_steps: 通信中断步数
    # - deadline_miss: 超期任务数
    # - tardiness_sum: 延迟总和
    # - active_tasks: 活跃任务数
```

### 4. 获取指标

```python
metrics = env.get_metrics()
# 返回字典:
# {
#     'tasks_completed': int,
#     'outage_steps': int,
#     'deadline_miss': int,
#     'tardiness_sum': int,
#     'total_tasks': int,
#     'active_tasks': int,
# }
```

### 5. 渲染状态

```python
print(env.render())
# 输出文本格式的状态信息
```

## 数据结构

### Task

```python
@dataclass
class Task:
    task_id: int                        # 任务 ID
    position: Tuple[float, float]       # 位置 (x, y)
    arrival_time: int                   # 到达时间
    deadline: int                       # 截止时间
    completed: bool = False             # 是否完成
    completion_time: Optional[int] = None  # 完成时间

    def is_overdue(self, current_time: int) -> bool
    def get_tardiness(self, current_time: int) -> int
```

### SystemState

```python
@dataclass
class SystemState:
    t: int                              # 当前时间步
    ugv_positions: List[Tuple[float, float]]  # UGV 位置
    uav_onboard_ugv_id: int             # UAV 所在 UGV
    task_pool: List[Task]               # 任务池

    # 指标
    tasks_completed: int
    outage_steps: int
    deadline_miss: int
    tardiness_sum: int

    # 方法
    def add_task(position, arrival_time, deadline) -> Task
    def complete_task(task_id, completion_time) -> bool
    def get_active_tasks() -> List[Task]
    def to_dict() -> Dict[str, Any]
```

## 配置文件

```yaml
episode:
  horizon_steps: 500      # 总步数
  decision_period: 5      # 决策周期
  map_path: "maps/map_01.map"
  seed: 0                 # 随机种子

robots:
  n_ugv: 3               # UGV 数量
  n_uav: 1               # UAV 数量

tasks:
  enabled: true          # 是否启用任务生成
  arrival_rate: 0.1      # 任务到达率（每步概率）
  deadline_min: 80       # 最小 deadline
  deadline_max: 160      # 最大 deadline
  top_m: 5               # Top-M 任务数

comm:
  enabled: true          # 是否启用通信模拟
  snr_threshold: 0.0     # SNR 阈值
  obstacle_penalty: 2.0  # 障碍物惩罚
  pathloss_n: 2.0        # 路径损耗指数

logging:
  out_dir: "outputs"     # 输出目录
  save_trace: true       # 保存轨迹
  save_metrics: true     # 保存指标
```

## Day1 限制

当前版本（Day1）的简化：

1. **UGV**: 原地不动，所有从 (0,0) 开始
2. **UAV**: 永远在 0 号 UGV 上，不飞行
3. **任务生成**: 简单随机，位置和 deadline 都随机
4. **任务完成**: 简单规则（距离 (0,0) < 5.0 自动完成）
5. **通信 outage**: 简单随机（10% 概率）
6. **地图**: 假设 100x100，无障碍物
7. **动作**: 不接受动作输入（action 参数被忽略）

## 完整示例

```python
import yaml
from agcoop import AGCoopEnv, seed_everything

# 加载配置
with open("configs/default.yaml", 'r') as f:
    config = yaml.safe_load(f)

# 设置随机种子
seed_everything(config['episode']['seed'])

# 创建环境
env = AGCoopEnv(config)

# 重置环境
state = env.reset()
print(f"初始状态: {state.to_dict()}")

# 运行 episode
done = False
while not done:
    state, reward, done, info = env.step()

    # 每 100 步打印一次
    if state.t % 100 == 0:
        print(f"步 {state.t}: {info}")

# 获取最终指标
metrics = env.get_metrics()
print(f"最终指标: {metrics}")

# 渲染最终状态
print(env.render())
```

## 测试

运行测试脚本：

```bash
python test_env_core.py
```

运行示例：

```bash
python example_simple.py
```

## 文件结构

```
ag_coop/
├── agcoop/
│   ├── __init__.py          # 包初始化
│   ├── env/
│   │   └── core.py          # 环境核心（~350 行）
│   └── utils/
│       └── seeding.py       # 随机种子工具
├── configs/
│   └── default.yaml         # 默认配置
├── test_env_core.py         # 测试脚本
├── example_simple.py        # 简单示例
├── DAY1_SUMMARY.md          # Day1 总结
└── QUICK_REFERENCE.md       # 本文件
```

## 下一步

Day2+ 将实现：

1. 真实的 UGV 移动和路径规划
2. UAV 起降和飞行逻辑
3. 基于距离的任务完成判断
4. 真实的通信模型（SNR 计算）
5. 地图加载和障碍物处理
6. 动作空间定义和处理

## 常见问题

**Q: 为什么任务完成数为 0？**

A: Day1 版本中，只有距离 (0,0) < 5.0 的任务会自动完成。由于任务位置是随机的（0-100 范围），大部分任务不会在原点附近，因此完成数通常为 0。这是正常的，Day2+ 会实现真实的任务完成逻辑。

**Q: 如何修改配置？**

A: 直接编辑 `configs/default.yaml` 文件，或在代码中修改配置字典。

**Q: 如何保证可复现性？**

A: 使用 `seed_everything()` 设置相同的随机种子，确保每次运行结果一致。

**Q: 如何添加自定义指标？**

A: 在 `SystemState` 类中添加新的字段，并在 `step()` 方法中更新。

## 联系和反馈

如有问题或建议，请查看项目文档或提交 issue。
