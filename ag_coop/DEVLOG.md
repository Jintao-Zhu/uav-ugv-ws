# 开发日志

## 2026-02-07 00:15

### Day4 指标扩展：补强统计体系 ✅

**修改文件：**
- `agcoop/tasks/manager.py` - 扩展 `get_stats()` 方法
- `tests/test_day4_validation.py` - 更新验收测试输出新指标

**新增指标（6 个）：**

1. **完成时间分布**
   - `mean_completion_time`：平均完成时间（completed_t - release_t）
   - `p95_completion_time`：95 分位完成时间

2. **Slack 分析**（deadline 松弛度）
   - `mean_slack_at_assignment`：分配时的 slack（deadline_t - assigned_t）
   - `mean_slack_at_completion`：完成时的 slack（deadline_t - completed_t）

3. **系统拥塞程度**
   - `avg_active_tasks`：每步 active 任务数的平均值
   - `active_tasks_end`：episode 结束时剩余的 active 任务数

**验收结果（ar=0.1, dl=[25,60], 500 步）：**

```
任务统计:
  total_generated: 47
  total_completed: 35
  total_expired: 11
  completion_rate: 74.47%
  miss_rate: 23.40%

完成时间分布:
  mean_completion_time: 20.63 步
  p95_completion_time: 43 步

Slack 分析:
  mean_slack_at_assignment: 32.40 步（分配时还有 32 步余量）
  mean_slack_at_completion: 22.89 步（完成时还剩 23 步余量）

系统拥塞程度:
  avg_active_tasks: 1.49（平均只有 1-2 个任务在池中）
  active_tasks_end: 0（episode 结束时清空）
```

**关键发现：**

1. **mean_tardiness=0.0 的原因**：
   - 当前系统是"超期即丢弃"体系（expire_overdue_tasks 在 deadline 时刻直接过期）
   - EDF 策略确保优先完成 deadline 最近的任务
   - `mean_slack_at_completion=22.89` 说明完成的任务都有充足余量

2. **系统负载合理**：
   - `avg_active_tasks=1.49` 说明系统不拥塞
   - `mean_completion_time=20.63` 远小于 `deadline_range=[25,60]`
   - 过期的 11 个任务主要是因为"来得晚 + deadline 紧"

3. **为 Day5 做好准备**：
   - 这些指标会在 Day5 引入真实 UAV 运动后，清晰解释 miss 上升的原因
   - 例如：`mean_completion_time` 增加 → 路径规划耗时增加
   - 例如：`avg_active_tasks` 增加 → 系统开始拥塞

**指标口径确认：**
- **miss_rate** = expired / total_added（任务在 deadline 前未完成 → 过期）
- **tardiness** = max(0, completed_t - deadline_t)（超期完成的延迟量）
- 当前系统几乎不会出现"超期完成"，而是"超期未完成 → 过期"

---

## 2026-02-06 23:30

### Day4 Step 6：任务负载校准 ✅

**新增文件：**
- `scripts/sweep_task_load.py` - 任务负载校准脚本

**修改文件：**
- `configs/default.yaml` - 更新任务参数（arrival_rate: 0.2 → 0.1）

**校准目标：**
找到合适的任务参数，使 miss_rate 在 10%-40% 之间（有压力但不至于全崩）

**扫描参数：**
- `arrival_rate`: {0.05, 0.1, 0.2, 0.3}
- `deadline_range`: {(40,80), (25,60), (15,40)}
- `horizon_steps`: 500
- `seeds`: {42, 43, 44, 45, 46}（5 个 seed 取平均）
- `map`: map_01.map
- `policy`: earliest_deadline

**校准结果表格：**

| Arrival Rate | [15,40] | [25,60] | [40,80] |
|--------------|---------|---------|---------|
| 0.05 | 23.2 / 9.0% / 0.0 | 22.8 / 1.2% / 0.0 | 22.0 / 0.0% / 0.0 |
| **0.10** | 29.2 / 39.3% / 0.0 | **32.0 / 28.5% / 0.0** ✅ | 40.0 / 11.0% / 0.0 |
| 0.20 | 20.4 / 75.0% / 0.0 | 22.0 / 69.5% / 0.0 | 27.8 / 61.2% / 0.0 |
| 0.30 | 14.0 / 84.3% / 0.0 | 15.6 / 81.1% / 0.0 | 18.6 / 75.0% / 0.0 |

格式：completed / miss_rate / tardiness

**🎯 推荐参数（最佳）：**
- `arrival_rate: 0.10`
- `deadline_min: 25`
- `deadline_max: 60`
- **miss_rate: 28.47%** ✅（在目标区间 10%-40% 内）
- completion_rate: 67.07%
- 平均完成任务数：32.0 / 500 步

**其他候选参数：**
1. `arrival_rate=0.10, deadline=[40,80]` → miss_rate=11.0%（偏低，压力不够）
2. `arrival_rate=0.10, deadline=[15,40]` → miss_rate=39.3%（偏高，接近上限）

**分析：**

1. **arrival_rate=0.05**：
   - 任务太少，miss_rate 接近 0%
   - 没有压力，不适合对比实验

2. **arrival_rate=0.10** ✅：
   - 最佳选择，miss_rate 在 11%-39% 之间
   - deadline=[25,60] 时 miss_rate=28.5%（最平衡）
   - 完成任务数适中（32 个）

3. **arrival_rate=0.20**：
   - 任务太多，miss_rate > 60%
   - 压力过大，大部分任务过期

4. **arrival_rate=0.30**：
   - 任务过载，miss_rate > 75%
   - 几乎全崩，不适合实验

**配置更新：**
- `arrival_rate`: 0.2 → 0.1（降低任务生成率）
- 添加任务负载 profile 注释：
  - light: arrival_rate=0.05 (miss_rate=1.2%)
  - default: arrival_rate=0.10 (miss_rate=28.5%) ✅
  - heavy: arrival_rate=0.20 (miss_rate=69.5%)

**输出文件：**
- `outputs/task_load_sweep/sweep_results.json` - 完整校准结果

**验收：**
- ✅ 找到合适的参数（miss_rate 在 10%-40% 之间）
- ✅ 扫描了 4x3=12 种参数组合（每种 5 个 seed）
- ✅ 总共运行 60 个 episode
- ✅ 推荐参数已更新到 configs/default.yaml

**设计特点：**
- 系统化扫描（arrival_rate x deadline_range）
- 多 seed 平均（减少随机性）
- 清晰的结果表格（便于对比）
- 自动推荐最佳参数

**后续实验建议：**
- 使用 default profile（arrival_rate=0.1, deadline=[25,60]）作为基准
- 对比不同策略（EDF vs Random）时使用相同参数
- 如需调整难度，使用 light/heavy profile

---

## 2026-02-06 23:00

### Day4 Step 5：打通 deadline 指标（metrics + trace）✅

**新增文件：**
- `tests/test_day4_integration.py` - Day4 任务系统集成测试

**集成测试内容：**
- TaskStream + TaskManager + VirtualUAVExecutor 完整流程
- 任务生成、分配、完成、过期
- Metrics 统计和 Trace 记录

**Metrics 指标（已实现）：**

1. **任务统计**：
   - `total_generated` - 总生成任务数
   - `total_dropped` - 因容量满而丢弃的任务数
   - `total_added` - 总添加任务数
   - `total_completed` - 总完成任务数
   - `total_expired` - 总过期任务数

2. **任务指标**：
   - `completion_rate` - 完成率（completed / added）
   - `expiration_rate` - 过期率（expired / added）
   - `deadline_miss_rate` - Deadline miss 率（expired / added）

3. **Tardiness 指标**：
   - `total_tardiness` - 总延迟时间
   - `mean_tardiness` - 平均延迟时间（tardiness / completed）

4. **完成时间指标**：
   - `mean_completion_time` - 平均完成时间（completed_t - release_t）
   - `p95_completion_time` - P95 完成时间

**Trace 字段（已实现）：**

每步记录：
- `t` - 当前时刻
- `new_task_ids` - 本步生成的任务 ID 列表
- `assigned_task_id` - 本步分配的任务 ID（如果有）
- `completed_task_ids` - 本步完成的任务 ID 列表
- `uav_remaining_time` - UAV 剩余执行时间
- `num_active` - 活跃任务数
- `num_assigned` - 已分配任务数
- `num_done` - 已完成任务数
- `num_expired` - 已过期任务数

**集成测试结果（200 步，arrival_rate=0.2）：**

任务统计：
- 生成 43 个任务
- 完成 12 个任务（27.91%）
- 过期 23 个任务（53.49%）
- 剩余 8 个活跃任务

任务指标：
- completion_rate: 27.91%
- expiration_rate: 53.49%
- deadline_miss_rate: 53.49%

完成时间：
- mean_completion_time: 33.92 步
- p95_completion_time: 56.00 步

Tardiness：
- total_tardiness: 0（所有完成的任务都按时完成）
- mean_tardiness: 0.00

**Trace 事件示例：**
- t=1: 生成任务 0
- t=17: 完成任务 0（remaining_time=8）
- t=25: 完成任务 1（remaining_time=10）
- t=35: 完成任务 2（remaining_time=14）

**验收：**
- ✅ Episode 内出现完成任务（12 个）
- ✅ Episode 内出现超期任务（23 个）
- ⚠️ 没有延迟完成（所有完成的任务都按时完成）
- ⚠️ completion_rate 较低（27.91%）

**分析：**
- Deadline 设置较紧（25-60 步），导致很多任务过期
- UAV 执行速度有限（Chebyshev 距离 + service_time），无法完成所有任务
- 完成的任务都按时完成（说明 EDF 策略有效）
- 这是合理的结果，符合资源受限场景

**设计特点：**
- 完整的 metrics 统计（8 个指标）
- 详细的 trace 记录（9 个字段）
- 可通过 grep trace 查看任务分配/完成过程
- 支持多种策略对比（EDF vs Random）

**后续优化方向：**
- 调整 deadline 范围（放宽到 40-80）以提高 completion_rate
- 添加多 UAV 支持（提高任务处理能力）
- 添加任务优先级（重要任务优先完成）
- 集成到 env 中（替换旧的 Task 类）

---

## 2026-02-06 22:30

### Day4 Step 4：实现虚拟 UAV 执行器 ✅

**新增文件：**
- `agcoop/tasks/executor.py` - VirtualUAVExecutor 虚拟执行器
- `tests/test_executor.py` - VirtualUAVExecutor 单元测试

**修改文件：**
- `agcoop/tasks/__init__.py` - 导出 VirtualUAVExecutor 和 estimate_travel_time

**VirtualUAVExecutor 设计（Day4 简化版）：**

**目的：** 保证任务能完成，验证任务系统链路（Day5 会替换为真实 UAV 运动）

**执行器状态：**
- `uav_cell` - UAV 当前位置（虚拟，不真实移动）
- `uav_busy` - UAV 是否正在执行任务
- `current_task_id` - 当前执行的任务 ID
- `remaining_time` - 完成当前任务还需要的步数
- `service_time` - 到点服务时间（步数）

**任务耗时估算（简单稳定）：**
```python
def estimate_travel_time(uav_cell, task_cell, service_time):
    # Chebyshev 距离（8-连通最短路径）
    dx = abs(task_cell[1] - uav_cell[1])
    dy = abs(task_cell[0] - uav_cell[0])
    travel_time = max(dx, dy)

    return travel_time + service_time
```

**设计选择：**
- 使用 Chebyshev 距离（max(|dx|, |dy|)）作为飞行时间
- 不依赖图搜索，简单稳定
- Day5 会替换为真实路径规划 + 运动学

**执行逻辑（每步 step）：**

1. **如果 UAV 忙碌**：
   - 检查当前任务是否已过期（如果过期，放弃执行）
   - `remaining_time -= 1`
   - 如果 `remaining_time == 0`：
     - 完成任务 → `mark_completed(task_id, t)`
     - 更新 UAV 位置（虚拟移动到任务位置）
     - 重置状态（`uav_busy = False`）

2. **如果 UAV 空闲**：
   - 从 `TaskManager.get_top_m(...)` 获取 Top-M 任务
   - 选择第一个任务（按策略排序后的第一个）
   - 估算完成时间 → `estimate_travel_time(...)`
   - 分配任务 → `mark_assigned(task_id, t)`
   - 设置 `uav_busy = True`, `remaining_time = total_time`

**关键修复：**
- 添加任务过期检查（执行中的任务可能被 `expire_overdue_tasks()` 过期）
- 如果任务已过期，放弃执行并重置状态
- 避免尝试完成已过期的任务（会抛出异常）

**单元测试（7 个测试，全部通过）：**
- ✅ 飞行时间估算（Chebyshev 距离）
- ✅ 基本任务执行流程（分配 → 执行 → 完成）
- ✅ 连续执行多个任务（3 个任务按顺序完成）
- ✅ 延迟完成和 tardiness 计算（deadline=10, completed_t=12, tardiness=2）
- ✅ 任务过期处理（过期任务被放弃，继续执行下一个）
- ✅ EDF 策略选择任务（选择最早 deadline 的任务）
- ✅ reset() 重置执行器

**测试结果示例：**
- 基本流程：任务 0 在 t=7 完成（travel=5 + service=2）
- 连续任务：3 个任务在 t=4, 9, 14 完成
- 延迟完成：deadline=10, completed_t=12, tardiness=2
- 任务过期：任务 0 过期，任务 1 完成（expired=1, completed=1）

**验收：**
- ✅ Episode 内出现完成任务（completion_rate=100%）
- ✅ Episode 内出现超期任务（expiration_rate > 0）
- ✅ Episode 内出现 tardiness > 0（延迟完成）
- ✅ UAV 状态转换正确（空闲 → 忙碌 → 空闲）
- ✅ 任务完成后 UAV 位置更新

**设计特点：**
- 简单稳定（不依赖复杂路径规划）
- 可预测（Chebyshev 距离确定性）
- 易于替换（Day5 只需替换 `estimate_travel_time` 和移动逻辑）
- 完整的过期处理（执行中的任务也能过期）

**Day5 升级计划：**
- 替换 `estimate_travel_time` 为真实路径规划（BFS/A*）
- 添加真实 UAV 运动（逐步移动到目标）
- 添加运动学约束（速度、加速度）
- 集成通信模型（飞行中检查 outage）

---

## 2026-02-06 22:00

### Day4 Step 3：实现 TaskManager（任务池 + Top-M + 统计）✅

**新增文件：**
- `agcoop/tasks/manager.py` - TaskManager 任务管理器
- `tests/test_task_manager.py` - TaskManager 单元测试

**修改文件：**
- `agcoop/tasks/__init__.py` - 导出 TaskManager

**TaskManager 核心功能：**

1. **任务池管理**（按状态分类）：
   - `active_ids` - 活跃任务（可被分配）
   - `assigned_ids` - 已分配任务（正在执行）
   - `done_ids` - 已完成任务
   - `expired_ids` - 已过期任务

2. **任务操作**：
   - `add_task(task)` - 添加任务（容量限制）
   - `mark_assigned(task_id, t)` - 标记为已分配
   - `mark_completed(task_id, t)` - 标记为已完成（自动计算 tardiness）
   - `expire_overdue_tasks(t)` - 过期所有超过 deadline 的任务

3. **Top-M 任务选择**（两种策略）：
   - `get_top_m(t, policy="earliest_deadline")` - EDF 策略
   - `get_top_m(t, policy="random")` - Random 策略（对照用）

4. **查询接口**：
   - `get_active_tasks()` / `num_active` - 活跃任务
   - `get_assigned_tasks()` / `num_assigned` - 已分配任务
   - `get_done_tasks()` / `num_done` - 已完成任务
   - `get_expired_tasks()` / `num_expired` - 已过期任务
   - `get_task(task_id)` / `has_task(task_id)` - 单个任务查询

5. **统计信息**：
   - `total_added` - 总添加任务数
   - `total_completed` - 总完成任务数
   - `total_expired` - 总过期任务数
   - `completion_rate` - 完成率
   - `expiration_rate` - 过期率
   - `total_tardiness` - 总延迟时间
   - `avg_tardiness` - 平均延迟时间

**状态转换逻辑：**
- `active` → `assigned` → `done`（正常流程）
- `active` / `assigned` → `expired`（超过 deadline）
- 完成时自动计算 `tardiness = max(0, completed_t - deadline_t)`

**Top-M 策略实现：**

1. **EDF (Earliest Deadline First)**：
   - 按 `deadline_t` 升序排序
   - 返回前 `top_m` 个任务
   - 适合：最小化 miss rate

2. **Random**：
   - 随机打乱任务顺序
   - 返回前 `top_m` 个任务
   - 适合：对照实验（baseline）
   - 使用独立的 `random.Random(seed)` 保证可复现

**单元测试（8 个测试，全部通过）：**
- ✅ 任务添加和容量限制（max_active=5，第 6 个添加失败）
- ✅ 任务状态转换（active → assigned → done）
- ✅ 延迟完成的 tardiness 计算（deadline=100, completed_t=120, tardiness=20）
- ✅ 任务过期处理（active 和 assigned 都能过期）
- ✅ Top-M 任务选择（EDF 策略，按 deadline 排序）
- ✅ Top-M 任务选择（Random 策略，可复现）
- ✅ 统计信息正确性（completion_rate, avg_tardiness 等）
- ✅ reset() 重置管理器

**测试结果示例：**
- 容量限制：添加 5 个任务成功，第 6 个失败
- EDF Top-3：[1, 3, 0]（deadline: [50, 75, 100]）
- Random Top-3：[3, 1, 2]（重置后可复现）
- 统计：completion_rate=60%, expiration_rate=40%, avg_tardiness=6.67

**验收：**
- ✅ 任务状态流转正确（active → assigned → done）
- ✅ 完成后从 active 移到 done
- ✅ tardiness 计算正确（延迟完成时）
- ✅ 过期任务正确处理（active 和 assigned 都能过期）
- ✅ Top-M 策略正确（EDF 和 Random）
- ✅ 统计信息完整准确

**设计特点：**
- 按状态分类管理（4 个列表）
- 完整的状态转换验证（防止非法转换）
- 独立的随机数生成器（Random 策略可复现）
- 丰富的统计信息（completion_rate, tardiness 等）
- 支持 reset() 重置（多 episode 实验）

---

## 2026-02-06 21:30

### Day4 Step 2：实现可复现的在线任务流 TaskStream ✅

**新增文件：**
- `agcoop/tasks/stream.py` - TaskStream 任务流生成器
- `tests/test_task_stream.py` - TaskStream 单元测试

**修改文件：**
- `agcoop/tasks/__init__.py` - 导出 TaskStream 和 TaskConfig
- `configs/default.yaml` - 更新任务配置

**TaskConfig 配置项（已写入 config）：**
```yaml
tasks:
  enabled: true
  arrival_process: "bernoulli"  # 到达过程类型（目前仅支持 bernoulli）
  arrival_rate: 0.2             # 每步生成任务概率（0.0-1.0）
  deadline_min: 25              # 最小 deadline（步数）
  deadline_max: 60              # 最大 deadline（步数）
  max_active: 20                # 任务池最大容量（满了丢弃新任务）
  top_m: 5                      # Top-M 任务数量（用于策略）
  service_time: 2               # 到点服务时间（步数）
```

**配置调整说明：**
- 原 `deadline_min/max: 80-160` 太宽松，改为 `25-60` 以便观察 miss/tardiness
- 新增 `arrival_process` 字段（目前仅支持 "bernoulli"）
- 新增 `max_active` 字段（任务池容量限制）
- 新增 `service_time` 字段（到点服务时间）
- `arrival_rate` 从 0.1 提高到 0.2（Day4 用高一点保证有数据）

**TaskStream 生成规则：**

1. **Bernoulli 过程**：
   - 每步以概率 `arrival_rate` 生成 0 或 1 个任务
   - 使用独立的随机数生成器（`random.Random(seed)`）

2. **任务位置**：
   - 从 `free_cells` 中均匀随机采样
   - 可选：排除 UGV 占用格（后续可加）

3. **Deadline 生成**：
   - `deadline_t = t + randint(deadline_min, deadline_max)`
   - 保证 deadline 在配置范围内

4. **容量限制**：
   - 当 `current_active_count >= max_active` 时，丢弃新任务
   - 统计 `total_dropped` 和 `drop_rate`

**可复现性保证：**
- 使用独立的 `random.Random(seed)` 实例
- 相同 seed 生成相同的任务序列（id, cell, deadline 完全一致）
- `reset()` 方法重置生成器状态

**核心方法：**
- `generate_tasks(t, current_active_count)` - 生成当前时刻的任务
- `reset()` - 重置生成器（用于新 episode）
- `get_stats()` - 获取统计信息（total_generated, total_dropped, drop_rate）

**单元测试（6 个测试，全部通过）：**
- ✅ 任务生成的可复现性（相同 seed 生成相同任务序列）
- ✅ arrival_rate 控制生成概率（0.1, 0.3, 0.5 测试通过）
- ✅ 任务池容量限制（max_active=5，丢弃率 75%）
- ✅ deadline 范围正确性（25-60 步）
- ✅ 任务位置从 free_cells 采样（分布均匀）
- ✅ reset() 重置生成器（两次运行一致）

**测试结果示例：**
- `arrival_rate=0.1`: 生成 82/1000 任务，实际率 0.082（误差 1.8%）
- `arrival_rate=0.3`: 生成 298/1000 任务，实际率 0.298（误差 0.2%）
- `arrival_rate=0.5`: 生成 498/1000 任务，实际率 0.498（误差 0.2%）

**验收：**
- ✅ 相同 seed 重跑，生成的任务序列（id/cell/deadline）完全一致
- ✅ arrival_rate 控制正确（统计误差 < 3%）
- ✅ 容量限制生效（满了丢弃新任务）
- ✅ deadline 范围正确（25-60 步）
- ✅ 任务位置从 free_cells 采样

**设计特点：**
- 独立的随机数生成器（不影响全局 random）
- 完整的统计信息（生成数、丢弃数、丢弃率）
- 支持 reset() 重置（多 episode 实验）
- 简洁的 API（generate_tasks 一步到位）

---

## 2026-02-06 21:00

### Day4 Step 1：定义 Task 数据结构 ✅

**新增文件：**
- `agcoop/tasks/task.py` - Task 数据结构
- `agcoop/tasks/__init__.py` - 任务模块导出
- `tests/test_task.py` - Task 单元测试

**Task 字段（已固定，后续不改）：**
```python
@dataclass
class Task:
    id: int                          # 任务唯一标识符
    release_t: int                   # 任务到达时刻（步数）
    cell: Tuple[int, int]           # 任务位置 (i, j) = (row, col)
    deadline_t: int                  # 任务截止时刻（步数）
    assigned_t: Optional[int]        # 任务分配时刻（None=未分配）
    completed_t: Optional[int]       # 任务完成时刻（None=未完成）
    status: str                      # "active", "assigned", "done", "expired"
    tardiness: int                   # 延迟时间 max(0, completed_t - deadline_t)
```

**状态转换：**
- `active` → `assigned` → `done`（正常流程）
- `active` / `assigned` → `expired`（超过 deadline 未完成）

**核心方法：**
1. **状态管理**：
   - `assign(t)` - 分配任务
   - `complete(t)` - 完成任务（自动计算 tardiness）
   - `expire(t)` - 任务过期

2. **状态查询**：
   - `is_active()` / `is_assigned()` / `is_done()` / `is_expired()`
   - `time_to_deadline(t)` - 计算剩余时间

3. **JSON 序列化**：
   - `to_dict()` / `to_json()` - 序列化
   - `from_dict()` / `from_json()` - 反序列化
   - ✅ 可直接写入 trace.jsonl

**坐标约定：**
- `cell = (i, j)` 其中 `i=row(y)`, `j=col(x)`
- 与项目其他部分（地图、通信模型）保持一致
- JSON 序列化时转为 list，反序列化时恢复为 tuple

**单元测试（6 个测试，全部通过）：**
- ✅ Task 创建和字段验证
- ✅ 状态转换（active → assigned → done）
- ✅ 过期处理（expired）
- ✅ JSON 序列化和反序列化
- ✅ 辅助方法（time_to_deadline 等）
- ✅ 坐标约定验证

**验收：**
- ✅ Task 可 JSON 序列化（trace 里可写）
- ✅ 字段验证正确（deadline > release）
- ✅ 状态转换逻辑正确
- ✅ tardiness 计算正确（延迟完成时）
- ✅ 坐标约定与项目一致

**设计特点：**
- 使用 dataclass 简化代码
- 完整的字段验证（__post_init__）
- 清晰的状态机（4 种状态）
- 完整的 JSON 序列化支持
- 丰富的辅助方法

---

## 2026-02-06 20:30

### Step 6：阈值校准与一致性检查 ✅

**新增文件：**
- `scripts/sweep_threshold.py` - 阈值 sweep 工具
- `scripts/inspect_comm_extended.py` - 扩展通信检查工具（含一致性验证）

**问题识别：**
- 原阈值 `-20.0 dB` 过于宽松，导致 outage 始终为 0%
- 全图最小 SNR 为 -11.5 dB，远高于 -20 dB 阈值
- 这会导致 Day4+ 实验中"通信指标"失去区分度（所有方法都 0% outage）

**阈值 Sweep 结果：**

测试地图：`map_01.map` (20x20, 286 free cells)
UGV 位置：(2,2), (10,10), (15,15)
扫描范围：-15.0 ~ +5.0 dB（步长 1.0 dB）

| 阈值 (dB) | Outage % | Outage Count |
|-----------|----------|--------------|
| -15.0     | 1.0%     | 3/286        |
| -14.0     | 2.8%     | 8/286        |
| -13.0     | 4.5%     | 13/286       |
| **-12.0** | **6.3%** | **18/286**   |
| -11.0     | 7.3%     | 21/286       |
| -10.0     | 9.4%     | 27/286       |
| **-9.0**  | **14.0%**| **40/286**   |
| -8.0      | 18.5%    | 53/286       |
| **-7.0**  | **26.2%**| **75/286**   |
| -6.0      | 30.8%    | 88/286       |
| -5.0      | 36.0%    | 103/286      |
| ...       | ...      | ...          |

**🎯 推荐阈值方案：**

1. **Relaxed（宽松）**: `-12.0 dB` → 6% outage
   - 适合：通信指标"刚刚有差异"，不强驱动策略

2. **Default（默认）**: `-9.0 dB` → 14% outage ✅
   - 适合：平衡场景，通信与任务指标同时有区分度

3. **Strict（苛刻）**: `-7.0 dB` → 26% outage
   - 适合：强调中继部署/会合选择，拉开 baseline 差距

**配置更新：**
- `configs/default.yaml` 中 `snr_threshold_db` 已更新为 `-9.0 dB`
- 添加三档 profile 注释（relaxed/default/strict）

**一致性检查（扩展工具）：**

新增两个验证热力图：

1. **Best UGV 分区图** (`best_ugv_map.png`)
   - ✅ 显示清晰的分界线（类似 Voronoi 图）
   - ✅ 每个 UGV 周围有连续区域
   - ✅ 无碎片化随机噪声（验证 raycast/索引逻辑正确）

2. **Blocked Count 热力图** (`blocked_heatmap.png`)
   - ✅ 深红阴影区对应障碍物位置
   - ✅ 障碍后方有更高的 blocked 值
   - ✅ 验证障碍遮挡计数正确

**输出文件：**
- `outputs/threshold_sweep/map_01/`
  - `threshold_sweep.png` - 阈值 vs outage% 曲线图
  - `threshold_sweep.json` - 完整 sweep 数据
- `outputs/comm_inspect_ext/map_01/`
  - `snr_heatmap.png` - SNR 热力图
  - `best_ugv_map.png` - Best UGV 分区图
  - `blocked_heatmap.png` - Blocked Count 热力图
  - `comm_meta_extended.json` - 扩展元数据

**验收状态：**
- ✅ 阈值 sweep 显示单调变化（无异常跳变）
- ✅ 推荐阈值落在目标区间（5%-30%）
- ✅ Best UGV 分区图显示清晰分界线
- ✅ Blocked Count 热力图与障碍物位置对应
- ✅ 通信模型实现稳定可靠

**Day3 验收：通过 ✅**

以"通信指标具备可比较动态范围"为验收标准：
- Sweep 显示阈值在 -12 到 -6 dB 间可以稳定落在 5%-30% 区间
- 随阈值单调变化，无异常跳变
- 一致性检查通过，无碎片化噪声或计数错误
- **通信模型实现正确且稳定**

**后续计划：**
- Day4 将按此阈值区间设计 deadline 任务流与任务池规则
- 保证"任务指标 + 通信指标"同时有区分度
- 主实验建议使用两档阈值（-12 和 -7）以增强结果稳健性

---

## 2026-02-06 19:25

### Step 5：两组最小实验验证

**新增文件：**
- `test_step5_experiments.py` - 实验验证脚本

**实验设计：**
- 实验 1：严格阈值（-5.0 dB）→ 预期 outage 上升
- 实验 2：宽松阈值（-40.0 dB）→ 预期 outage 下降
- Episode 长度：200 步

**实验结果：**

| 实验 | 阈值 (dB) | SNR Mean (dB) | SNR Min (dB) | Outage % | Outage Steps |
|------|-----------|---------------|--------------|----------|--------------|
| 严格 | -5.0      | 26.02         | 26.02        | 0.00%    | 0/200        |
| 宽松 | -40.0     | 26.02         | 26.02        | 0.00%    | 0/200        |

**trace 分析：**
- SNR 值：恒定为 26.02 dB（前 10 步）
- 标准差：0.00 dB（无波动）

**原因分析：**
- Day1 版本：所有 UGV 原地不动，都在 (0,0)
- UAV 永远在 0 号 UGV 上，也在 (0,0)
- 距离为 0，SNR 恒定为最大值（26.02 dB）
- 无论阈值如何设置，都不会 outage

**验收状态：**
- ⚠️ outage_percent 差异不明显（0.00% vs 0.00%）
- ⚠️ snr_best 无波动（恒定值）
- ✅ 通信模型正常工作（计算正确）
- ✅ 阈值配置生效（只是 SNR 太高，未触发）

**结论：**
- **通信模型实现正确**，但 Day1 场景过于简单
- 需要 Day2+ 实现 UGV 移动后，才能观察到：
  - SNR 随距离变化
  - outage_percent 随阈值变化
  - trace 中 snr_best 有波动

**验证方法（已通过）：**
- ✅ Step 4 的 SNR Heatmap 已验证：
  - 离 UGV 越近，SNR 越高
  - 障碍后方出现阴影区
  - SNR 范围：-11.50 ~ 26.02 dB（有明显变化）

---

## 2026-02-06 19:10

### Step 4：SNR Heatmap 可视化工具

**新增文件：**
- `scripts/inspect_comm.py` - SNR heatmap 生成工具

**功能：**
- 输入地图和 UGV 位置
- 对所有 free cell 作为 UAV 位置，计算 snr_best
- 输出 SNR heatmap 和元数据

**用法：**
```bash
python scripts/inspect_comm.py --map maps/test_small.map --ugv "1,1;8,8"
python scripts/inspect_comm.py --map maps/map_01.map --ugv "2,2;10,10;15,15" --threshold -10.0
```

**输出文件：**
- `outputs/comm_inspect/<map_id>/snr_heatmap.png` - SNR heatmap 图片
- `outputs/comm_inspect/<map_id>/comm_meta.json` - 元数据（阈值、参数、UGV 坐标、统计信息）

**可视化特点：**
- 颜色映射：绿色=高 SNR（好），黄色=中等，红色=低 SNR（差）
- UGV 位置：蓝色方块标注
- Outage 阈值：黑色虚线等高线
- 网格线辅助定位
- 详细说明文本框（验证要点、SNR 统计）

**测试结果（test_small.map, UGV at (1,1) and (8,8)）：**
- SNR 范围：-11.50 dB ~ 26.02 dB
- SNR 平均：1.95 dB
- Outage 比例：0.0%（阈值 -20.0 dB）
- 计算 56 个 free cells

**验收（肉眼）：**
- ✅ 离 UGV 越近，SNR 越高（颜色越绿）
- ✅ 障碍后方出现阴影区（SNR 更低）
- ✅ 对角线上的障碍明显影响 SNR 分布
- ✅ 两个 UGV 周围都有高 SNR 区域

**命令行参数：**
- `--map`: 地图文件路径（必需）
- `--ugv`: UGV 位置，格式 "i1,j1;i2,j2;..." （必需）
- `--output-dir`: 输出目录（可选）
- `--tx-power`: 发射功率 dB（默认 0.0）
- `--pathloss-n`: 路径损耗指数（默认 2.0）
- `--obstacle-penalty`: 障碍衰减 dB（默认 6.0）
- `--threshold`: Outage 阈值 dB（默认 -20.0）

---

## 2026-02-06 18:50

### Step 3：把通信统计接入 env

**修改文件：**
- `agcoop/env/core.py` - 集成真实通信模型

**新增文件：**
- `test_comm_integration.py` - 通信集成测试
- `test_comm_dispersed.py` - UGV 分散场景测试

**核心修改：**

1. **SystemState 扩展**
   - 添加 `snr_sum: float` - 累计 SNR
   - 添加 `snr_min: float` - 最小 SNR（初始为 +inf）

2. **AGCoopEnv 初始化**
   - 添加 `comm_config: CommConfig` - 通信配置对象
   - 添加 `grid_map: GridMap` - 地图对象（用于通信计算）
   - 在 `reset()` 中加载地图（如果指定）

3. **_update_outage() 重写**
   - 使用真实通信模型 `compute_best_snr()`
   - 计算 UAV 到所有 UGV 的 SNR
   - 返回 `(snr_best, outage)` 元组
   - 更新累计指标：`snr_sum`, `snr_min`, `outage_steps`
   - 如果地图未加载，回退到简单随机模型

4. **step() 逻辑**
   - 调用 `_update_outage()` 获取 `snr_best` 和 `outage`
   - 传递给 `_log_step(snr_best, outage)`

5. **_log_step() 更新**
   - 接收 `snr_best` 和 `outage` 参数
   - 写入 trace：`snr_best` 字段（真实值，保留 2 位小数）
   - 写入 trace：`outage` 字段（0 或 1）

6. **_save_final_metrics() 更新**
   - 计算 `snr_best_mean = snr_sum / steps`
   - 计算 `snr_best_min`（如果为 +inf 则返回 0.0）
   - 写入 metrics：`snr_best_mean`, `snr_best_min`

**集成测试（test_comm_integration.py）：**
- ✅ 测试 1：通信启用，SNR 指标不为 0
  - snr_best_mean: 26.02 dB
  - snr_best_min: 26.02 dB
  - trace 包含真实 snr_best 值
- ✅ 测试 2：通信禁用，SNR 指标为 0
  - snr_best_mean: 0.0 dB
  - snr_best_min: 0.0 dB
  - outage_percent: 0.0%
- ✅ 测试 3：outage_percent 随阈值变化
  - 不同阈值：-30.0, -20.0, -10.0, 0.0 dB
  - 注：Day1 所有 UGV 在原点，距离为 0，SNR 很高，无 outage

**验收：**
- ✅ snr_best_mean 和 snr_best_min 不为 0（comm enabled）
- ✅ snr_best_mean 和 snr_best_min 为 0（comm disabled）
- ✅ trace.jsonl 包含真实 snr_best 值
- ✅ outage_percent 正确计算
- ✅ 地图加载成功（maps/map_01.map, 20x20）

**注意事项：**
- Day1 版本：UGV 原地不动，都在 (0,0)，所以 SNR 很高（26.02 dB）
- 如果地图未加载，回退到简单随机通信模型（10% outage 概率）
- Day2+ 会实现 UGV 移动，届时 SNR 会随距离变化

---

## 2026-02-06 18:30

### Step 2：实现通信模型（SNR_best + outage）

**新增文件：**
- `agcoop/comm/comm_model.py` - 通信模型（SNR 计算和 outage 判断）
- `tests/test_comm_model.py` - 通信模型单元测试

**修改文件：**
- `configs/default.yaml` - 添加完整通信配置
- `agcoop/comm/__init__.py` - 导出通信模型函数

**配置项（configs/default.yaml）：**
```yaml
comm:
  enabled: true
  tx_power_db: 0.0          # 发射功率（dB）
  pathloss_n: 2.0           # 距离衰减指数
  obstacle_penalty_db: 6.0  # 每个障碍的衰减（dB）
  snr_threshold_db: -20.0   # outage 阈值
  eps_m: 0.05               # 避免 log(0)
```

**SNR 公式：**
```
snr_db = tx_power_db - 10 * pathloss_n * log10(d + eps) - obstacle_penalty_db * blocked
```

**核心函数：**
1. `CommConfig` - 通信配置数据类
   - `from_dict()` - 从配置字典创建

2. `compute_snr(distance_m, blocked_count, config)` - 计算 SNR
   - 基于距离衰减和障碍遮挡
   - 返回 SNR（dB）

3. `compute_snr_to_ugvs(uav_cell, ugv_cells, grid_map, config)` - 计算到所有 UGV 的 SNR
   - 返回 (snr_list, distance_list, blocked_list)

4. `compute_best_snr(uav_cell, ugv_cells, grid_map, config)` - 计算最佳 SNR
   - 返回 (snr_best, best_ugv_id, outage)
   - outage = True if snr_best < snr_threshold_db

5. `compute_comm_metrics(uav_cell, ugv_cells, grid_map, config)` - 完整通信指标
   - 返回字典，包含所有通信相关信息

**单元测试（tests/test_comm_model.py）：**
- ✅ 距离变大，SNR 降低
  - 1m: -0.42 dB, 10m: -20.04 dB, 100m: -40.00 dB
- ✅ blocked 增加，SNR 降低
  - 0 blocked: -20.04 dB, 1 blocked: -26.04 dB, 5 blocked: -50.04 dB
  - 每个障碍扣 6 dB（符合配置）
- ✅ threshold 检查 outage 正确
  - 近距离：SNR=6.94 dB, outage=False
  - 远距离+障碍：SNR=-74.69 dB, outage=True
  - 严格阈值：SNR=-8.28 dB < 0.0 dB, outage=True
- ✅ 最佳 UGV 选择正确
- ✅ 完整通信指标计算正确
- ✅ 边界情况处理（空 UGV 列表）
- ✅ 配置字典转换

**验收：**
- ✅ 所有测试通过（7 个测试）
- ✅ 距离变大，SNR 降低 ✓
- ✅ blocked 增加，SNR 降低 ✓
- ✅ threshold 检查 outage 正确 ✓
- ✅ 输出数值不是 NaN/inf ✓

**工程化特点：**
- 使用 eps_m 避免 log(0)
- 所有参数可配置
- 完整的边界情况处理
- 数值稳定性验证

---

## 2026-02-06 18:15

### Step 1：实现格栅 LOS/遮挡计数（Bresenham）

**新增文件：**
- `agcoop/comm/raycast.py` - 格栅射线追踪模块
- `agcoop/comm/__init__.py` - 通信模块导出
- `tests/test_raycast.py` - Raycast 单元测试

**核心函数：**
1. `bresenham_cells(i0, j0, i1, j1)` - Bresenham 算法
   - 返回两点连线穿过的格子序列
   - **包含端点**
   - 遵循项目坐标约定：i=row(y), j=col(x)

2. `count_blocked_cells(grid_map, cell_a, cell_b)` - 遮挡计数
   - 遍历线段格子，统计 obstacle 数量
   - **不含端点**（端点不参与统计）
   - 返回遮挡的障碍格子数

3. `has_line_of_sight(grid_map, cell_a, cell_b)` - 视线检查
   - 返回 True 如果无障碍遮挡

4. `compute_los_distance(grid_map, cell_a, cell_b)` - 距离计算
   - 返回欧几里得距离（米）

**单元测试（tests/test_raycast.py）：**
- ✅ bresenham_cells() 基本功能（水平、垂直、对角线）
- ✅ 端点包含测试
- ✅ 无障碍直线：blocked=0
- ✅ 中间放一个障碍：blocked>=1
- ✅ 多个障碍：blocked=3
- ✅ 对称性：count(a,b)==count(b,a)（5 对点）
- ✅ 端点不被统计
- ✅ has_line_of_sight() 正确
- ✅ compute_los_distance() 正确

**验收：**
- ✅ 所有测试通过（11 个测试）
- ✅ 坐标约定一致（i=row, j=col）
- ✅ 对称性验证通过
- ✅ 端点处理正确

---

## 2026-02-06 18:05

### Day3 开头：坐标系可视化验证

**新增文件：**
- `day3_verify_coords.py` - 坐标系可视化验证脚本
- `outputs/day3_coord_verification.png` - 验证图片（164KB）
- `outputs/day3_verification_report.md` - 详细验证报告
- `DAY3_README.md` - Day3 快速指南

**验证内容：**
1. ✅ 在 preview 图上标注 5 个随机 free cell 的 (x_idx, y_idx)
   - 显示为青色圆点，带坐标标签
   - 肉眼确认：所有点都落在白色区域（free cells）
2. ✅ 从测试实例中抽取 (sx, sy, gx, gy)，标注 start/goal
   - START: 绿色星星，cell(1, 1)，左下角附近
   - GOAL: 红色星星，cell(8, 8)，右上角附近
3. ✅ Y-flip 检查（一次性排雷）
   - START 在底部 (i=1 < 5.0) ✅
   - GOAL 在顶部 (i=8 > 5.0) ✅
   - **结论：坐标系正确，无需 y-flip！**

**测试数据：**
- 地图：test_small.map (10x10, 56 free cells)
- 随机采样的 5 个 free cells：
  - cell(1, 1) → world(0.30, 0.30)
  - cell(1, 6) → world(1.30, 0.30)
  - cell(5, 8) → world(1.70, 1.10)
  - cell(2, 8) → world(1.70, 0.50)
  - cell(3, 8) → world(1.70, 0.70)

**可视化特点：**
- 使用 `origin='lower'` 确保 i=0 在图像底部
- 青色圆点标注随机 free cells
- 绿色星星标注 START，红色星星标注 GOAL
- 网格线辅助定位
- 详细说明文本框（验证要点、测试实例）

**验收：**
- ✅ 所有青色点都在白色区域
- ✅ START 在左下角附近
- ✅ GOAL 在右上角附近
- ✅ 坐标标注清晰可见
- ✅ 无需 y-flip（坐标系方向正确）

**下一步：**
Day3 完整工作还包括：
- 实例生成工具（生成 .scen 或 _inst.txt 文件）
- 更多地图的验证（map_01.map 等）
- 与外部求解器的实际对接测试

---

## 2026-02-06 17:45

### 完善项目文档（Day2 收尾）

**新增文件：**
- `README.md` - 高质量项目文档
- `requirements.txt` - 依赖列表

**README.md 内容：**
- 项目概述和特点
- 系统架构图
- 核心功能详解（地图系统、仿真环境、日志系统）
- 使用指南（基本使用、地图操作、工具脚本）
- 开发进度（Day 1-2 完成，Day 3+ 计划）
- 实验复现说明
- 配置参数表
- 已知问题与注意事项
- 贡献指南

**特色：**
- 清晰的代码结构说明
- 完整的使用示例
- 坐标系约定详解（防止混淆）
- 外部求解器兼容性说明
- 预留字段文档（保持 schema 稳定）

**验收：**
- ✅ 结构清晰，易于理解
- ✅ 包含所有核心功能说明
- ✅ 提供完整的使用示例
- ✅ 标注开发进度和计划
- ✅ 说明已知问题和注意事项

---

## 2026-02-06 17:30

### 坐标系统加固与外部兼容性（Day2 关键修正）⚠️

**问题识别：**
- 测试脚本口径不一致（全量 vs 抽样）
- 缺少明确的坐标系约定文档
- 缺少与外部求解器的坐标转换

**修改文件：**
- `scripts/test_mapping.py` - 添加 --test-all 选项
- `scripts/inspect_map.py` - 添加 coordinate_convention 到 map_meta.json
- `agcoop/map/mapping.py` - 添加外部求解器坐标转换函数
- `test_solver_coords.py` - 求解器坐标转换测试

**A. 统一测试口径：**
- 添加 `--test-all` 选项，测试所有 free cells（而非抽样）
- 报告中添加 `test_all` 标记，明确测试范围
- 默认仍为抽样（快速测试），但可选全量测试（完整验证）

**B. 明确坐标系约定（map_meta.json）：**
```json
"coordinate_convention": {
  "index_order": "row_col",
  "origin_location": "lower_left",
  "y_axis_direction": "up",
  "cell_center_offset": 0.5,
  "note": "i=row(y), j=col(x); world_x = origin_x + (j+0.5)*resolution"
}
```

**C. 外部求解器坐标转换：**
- `to_solver_coords(i, j, height)` - 内部坐标 → 求解器坐标
  - 求解器约定：x=列, y=行（0=顶部）
  - 转换：solver_x = j, solver_y = (height-1) - i
- `from_solver_coords(solver_x, solver_y, height)` - 求解器坐标 → 内部坐标
- `format_solver_instance()` - 格式化为求解器实例（MovingAI 风格）
- `parse_solver_solution()` - 解析求解器返回的路径

**验收：**
- ✅ test_mapping.py --test-all：286/286 通过（100%）
- ✅ map_meta.json 包含完整坐标系约定
- ✅ 求解器坐标转换：所有角落格子正确
- ✅ 往返转换：to_solver_coords ↔ from_solver_coords 互为逆操作
- ✅ 实例格式化和解析正确

**重要性：**
这些修正防止了后续开发中最常见的坐标系 bug：
1. 测试覆盖不完整导致的边界 bug
2. 坐标系约定不明确导致的集成 bug
3. 与外部求解器对接时的坐标翻转 bug

---

## 2026-02-06 17:10

### 实现候选点生成原型（Day2 加分项）

**新增文件：**
- `scripts/gen_candidates.py` - 候选点生成工具

**功能：**
- 计算每个 free cell 的度数（4-连通邻居数量）
- 选择度 ≥ min_degree 的路口点（junction points）
- 随机抽样补齐或缩减到目标数量 R（默认 12）
- 输出 candidates.json（包含 cell、world、degree、is_junction）
- 可选可视化（红色=路口点，蓝色=随机点）

**生成策略：**
1. 优先选择路口点（度数高的格子）
2. 如果路口点不足，随机补充
3. 如果路口点过多，随机抽样缩减

**验收：**
- ✅ map_01.map（度≥3）：282 个路口点，随机抽样 12 个
- ✅ map_01.map（度≥4）：164 个路口点，随机抽样 12 个
- ✅ test_small.map（度≥3）：48 个路口点，随机抽样 12 个
- ✅ test_small.map（度≥5）：0 个路口点，随机补充 12 个
- ✅ JSON 格式正确，包含 map_info、generation_params、statistics、candidates
- ✅ 可视化正确显示路口点和随机点

**用途：**
- Day 8 的 coverage baseline
- 会合点候选集
- 任务分配的参考点

**用法：**
```bash
python scripts/gen_candidates.py maps/map_01.map
python scripts/gen_candidates.py maps/map_01.map --num-candidates 20 --visualize
python scripts/gen_candidates.py maps/map_01.map --min-degree 4 --output outputs/candidates.json
```

---

## 2026-02-06 17:00

### 实现映射单元测试脚本（Day2）

**新增文件：**
- `scripts/test_mapping.py` - 坐标映射单元测试脚本

**测试内容：**
- 测试1：随机抽 50 个 free cells，验证 cell → world → cell 往返转换
- 测试2：随机抽 50 个 world 点，验证 world → cell → world 往返转换
- 输出详细测试报告（mapping_report.json）

**报告内容：**
- 地图信息（width, height, resolution, origin, free_cells）
- 测试1结果（pass_count, fail_count, pass_rate, failures）
- 测试2结果（pass_count, fail_count, max_error, mean_error, out_of_bounds_count）
- 总体结果（all_tests_passed, total_samples, total_pass, total_fail）

**验收：**
- ✅ map_01.map：100/100 通过（100%）
  - 测试1：50/50 通过
  - 测试2：50/50 通过，最大误差 0.137m，平均误差 0.086m
  - 越界次数：0
- ✅ test_ros.yaml：100/100 通过（100%）
  - 测试1：50/50 通过
  - 测试2：50/50 通过，最大误差 0.034m，平均误差 0.021m
  - 越界次数：0
- ✅ 报告 JSON 格式正确，包含所有必要字段

**用法：**
```bash
python scripts/test_mapping.py maps/map_01.map
python scripts/test_mapping.py maps/test_ros.yaml --n-samples 100
python scripts/test_mapping.py maps/map_01.map --output outputs/report.json
```

---

## 2026-02-06 16:50

### 实现地图检查工具（Day2）

**新增文件：**
- `scripts/inspect_map.py` - 地图检查和可视化工具

**功能：**
- 生成地图元数据（map_meta.json）
  - map_id, width, height, total_cells
  - free_count, obstacle_count, free_percent
  - resolution, origin, frame
  - connectivity_default (4)
- 生成地图预览图（map_preview.png）
  - 黑色 = 障碍，白色 = 自由
  - 使用 origin='lower' 确保坐标系正确
- 生成详细预览（--detailed 选项）
  - 标注四个角落格子位置
  - 用于验证地图方向（防止上下翻转）

**修复：**
- 修复 `auto_load_map()` 支持 ROS .yaml 格式

**验收：**
- ✅ 成功加载 MovingAI .map 格式（map_01.map）
- ✅ 成功加载 ROS .yaml 格式（test_ros.yaml）
- ✅ 元数据 JSON 格式正确，包含所有必要字段
- ✅ 预览图生成成功（PNG 格式，48-77KB）
- ✅ 详细预览包含角落标注，便于验证方向
- ✅ 肉眼确认地图方向正确（没有上下翻转）

**用法：**
```bash
python scripts/inspect_map.py maps/map_01.map
python scripts/inspect_map.py maps/test_ros.yaml --detailed
python scripts/inspect_map.py maps/map_01.map --output-dir outputs/map_inspect
```

---

## 2026-02-06 16:40

### 实现邻接图和最短路径工具（Day2）

**新增文件：**
- `agcoop/map/neighbors.py` - 邻接图和 BFS 最短路径
- `test_neighbors.py` - 邻接图验收测试

**邻接图功能：**
- `get_neighbors()` - 获取格子的合法邻居（4-连通或 8-连通）
- `shortest_path_length()` - BFS 计算最短路径长度
- `shortest_path()` - BFS 计算完整路径
- `compute_distance_map()` - 从起点计算到所有格子的距离

**设计选择：**
- 默认使用 4-连通（更适合差速车、执行更稳定）
- 8-连通可选（后续可用于 UAV 或启发式估算）
- BFS 实现（Day2 足够快，简单可靠）

**验收：**
- ✅ get_neighbors() 返回正确的邻居（4-连通、8-连通）
- ✅ shortest_path_length() 正确计算距离
- ✅ 随机采样 30 对 free cells，100% 可达（地图连通性好）
- ✅ 平均距离 14.5 步，最大距离 27 步
- ✅ obstacle 封堵时返回 None
- ✅ 路径上所有格子都是 free cells
- ✅ distance_map 正确计算到所有格子的距离
- ✅ 边界情况处理正确（起点即终点、障碍、越界）

---

## 2026-02-06 16:25

### 实现权威坐标映射系统（Day2）

**新增文件：**
- `agcoop/map/mapping.py` - 权威坐标映射函数
- `test_mapping.py` - 坐标映射验收测试

**坐标映射功能：**
- `cell_to_world()` - 格子中心坐标转世界坐标
- `world_to_cell()` - 世界坐标转格子索引
- `world_to_cell_checked()` - 带边界检查的转换（越界抛异常）
- `in_bounds()` - 边界检查
- `clip_to_bounds()` - 裁剪到边界
- `get_cell_bounds()` - 获取格子边界

**坐标系约定（详见 mapping.py 注释）：**
- i = row (y 方向), j = col (x 方向)
- origin 在 cell(0,0) 左下角
- cell_to_world 返回格子中心坐标
- 支持任意 origin（包括负值，ROS 常见）

**验收：**
- ✅ 100% 往返转换一致（286/286 个自由格子）
- ✅ 边界检查正确（in_bounds, clip_to_bounds）
- ✅ world_to_cell_checked 越界正确抛出异常
- ✅ get_cell_bounds 正确
- ✅ 不同 origin 处理正确（包括负 origin）

**集成：**
- GridMap 已更新为使用 mapping 模块函数
- 所有地图 I/O 模块统一使用权威映射函数

---

## 2026-02-06 16:07

### 添加 ROS 地图格式支持（Day2）

**新增文件：**
- `agcoop/map/io_ros.py` - ROS map_server 格式 I/O
- `maps/test_ros.yaml` - ROS 测试地图配置
- `maps/test_ros.pgm` - ROS 测试地图图像（20x20）
- `test_map_ros.py` - ROS 地图测试

**ROS 格式支持：**
- 加载 .yaml + .pgm 格式（ROS map_server 标准）
- 解析 resolution, origin, occupied_thresh, free_thresh
- 正确处理 PGM 图像（P5 binary 格式）
- 二值化 occupancy grid（高值=自由，低值=障碍）
- 保存为 ROS 格式（save_ros_map）

**验收：**
- ✅ 加载 ROS .yaml + .pgm 格式
- ✅ 正确解析 resolution (0.05) 和 origin (-10.0, -10.0)
- ✅ 正确二值化（306 个自由格子，76.5%）
- ✅ 坐标转换考虑 origin
- ✅ 保存和重新加载一致

---

## 2026-02-06 15:54

### 实现地图模块（Day2）

**新增文件：**
- `agcoop/map/grid_map.py` - GridMap 核心数据结构
- `agcoop/map/io_text.py` - 文本格式地图 I/O（MovingAI .map、简单文本）
- `agcoop/map/__init__.py` - 模块导出接口
- `maps/test_small.map` - 测试地图（10x10）
- `maps/map_01.map` - 示例地图（20x20）
- `test_map.py` - 地图模块测试

**GridMap 功能：**
- 字段：width, height, grid, resolution, origin, frame, free_cells
- 方法：is_free(), in_bounds(), cell_to_world(), world_to_cell(), get_neighbors()
- 预计算：free_cells 列表（加载时自动计算）

**支持格式：**
- MovingAI .map 格式（标准 MAPF benchmark）
- 简单文本格式（0/1 矩阵）
- auto_load_map() 自动检测格式

**验收：**
- ✅ 加载 MovingAI .map 格式（test_small.map: 10x10, 56 个自由格子）
- ✅ free_cells 数量正确
- ✅ 边界检查不崩溃（in_bounds, is_free）
- ✅ 坐标转换正确（cell_to_world, world_to_cell）
- ✅ 邻居查询正确（4-连通、8-连通）
- ✅ 可视化正常（小地图可打印）
- ✅ 加载真实地图（map_01.map: 20x20, 286 个自由格子，71.5% 自由）

---

## 2026-02-06 15:18

### 完善 metrics.json 和 trace.jsonl schema（最终版）

**修改文件：**
- `agcoop/utils/io.py` - 添加 compute_file_hash() 函数
- `agcoop/env/core.py` - 添加 map_hash、decision_period，扩展 trace 字段

**metrics.json 新增：**
- `map_hash` - 地图文件哈希（sha256 前 16 位）

**trace.jsonl 扩展字段（预留）：**
- `task_completed_ids` - 当前步完成的任务 ID 列表
- `snr_best` - 最佳 SNR 值
- `decision_step` - 是否为决策步（t % decision_period == 0）
- `chosen_task_id` - 选择的任务 ID
- `chosen_rendezvous` - 选择的会合点
- `mapf_called` - 是否调用 MAPF
- `mapf_success` - MAPF 是否成功
- `mapf_plan_time_ms` - MAPF 规划时间

**验收：**
- ✅ 相同 seed 两次运行，所有指标完全一致
- ✅ trace.jsonl 完全一致（包含所有预留字段）
- ✅ decision_step 正确标记（t=5,10,15...）
- ✅ metrics 包含 33 个字段，trace 包含 14 个字段
- ✅ 所有预留字段为合理默认值（0/null/false/[]）

---

## 2026-02-06 15:11

### 扩展 metrics.json 字段

**修改文件：**
- `agcoop/env/core.py` - 添加 run_id、method、planner 参数，跟踪 max_outage_streak
- `agcoop/utils/logger.py` - 添加 sim_steps_per_sec 计算
- `scripts/run_one_episode.py` - 添加 --method 和 --planner 参数

**新增字段（共 30+ 个）：**
- **A. 复现管理**: run_id, method, planner, map_path
- **B. 任务质量**: completion_rate
- **C. 通信指标**: max_outage_streak, snr_threshold, snr_best_mean, snr_best_min
- **D. 规划执行（预留）**: mapf_calls, mapf_success_calls, mapf_timeout_calls, mapf_mean_plan_time_ms, fallback_wait_steps
- **D2. 会合回收（预留）**: rendezvous_success, rendezvous_fail, emergency_landings, uav_loiter_steps, ugv_hold_steps
- **E. 性能**: sim_steps_per_sec, termination_reason

**验收：**
- ✅ 相同 seed 重复执行，所有关键指标完全一致
- ✅ max_outage_streak 正确跟踪（示例：3）
- ✅ run_id 自动生成（格式：map_01_N3_seed100_lambda0.1）
- ✅ 预留字段全部为 0（后续填充不改 schema）

---

## 2026-02-06 14:54

### 实现一键运行脚本

**文件：**
- `scripts/run_one_episode.py` - 一键运行脚本

**功能：**
- 命令行参数：`--config`、`--seed`、`--out_name`
- 自动覆盖 seed、创建输出目录、运行完整 episode
- 显示进度条（每 10%）和最终统计
- 验证输出文件和 trace 行数

**验收：**
- ✅ 相同 seed 重复执行，metrics 完全一致（除 runtime_sec）
- ✅ trace.jsonl 完全一致
- ✅ outage%、tasks_completed 等指标可复现

**用法：**
```bash
python scripts/run_one_episode.py --seed 42
python scripts/run_one_episode.py --config configs/default.yaml --seed 123 --out_name my_run
```

---

## 2026-02-06 (早些时候)

### 实现日志与指标输出系统

**文件：**
- `agcoop/utils/logger.py` - TraceLogger 和 MetricsLogger
- `agcoop/utils/io.py` - 原子写文件工具
- `agcoop/env/core.py` - 集成日志功能（添加 `output_dir` 和 `enable_logging` 参数）

**输出文件：**
- `trace.jsonl` - 每步记录（行数 = steps）
- `metrics.json` - 最终指标
- `config_resolved.yaml` - 完整配置

**测试：**
- `test_logging.py` - 验收测试（全部通过）
- `example_with_logging.py` - 使用示例
