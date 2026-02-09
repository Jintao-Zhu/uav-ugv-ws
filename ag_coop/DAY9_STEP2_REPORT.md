# Day9 Step 2 完成报告

## 目标

设计 action space（先"可训"，再"聪明"）

## 实现内容

### 1. Action Space 设计

**格式**: `MultiDiscrete([M+1, R+1])`

- **task_choice** ∈ {0..M}:
  - 0: 不指定任务（退化为默认策略）
  - 1..M: 从 Top-M 任务中选择第 i-1 个任务（按 deadline 排序）

- **relay_target** ∈ {0..R}:
  - 0: 不指定 relay（保持当前策略）
  - 1..R: 从候选点集合中选择第 i-1 个候选点

**配置参数**:
- M = `config['tasks']['top_m']` (默认 5)
- R = `config['rendezvous']['candidate_count']` (默认 12)

### 2. 实现的方法

#### 2.1 `action_space` 属性

**文件**: `agcoop/env/core.py`

```python
@property
def action_space(self):
    """
    返回 gym.spaces.MultiDiscrete([M+1, R+1])
    """
    if self._action_space is None:
        try:
            from gymnasium import spaces
        except ImportError:
            from gym import spaces

        self._action_space = spaces.MultiDiscrete([self.top_m + 1, self.candidate_count + 1])

    return self._action_space
```

#### 2.2 `_apply_rl_action()` 方法

**功能**: 解析 RL action 并返回 UGV 目标

**输入**:
- `action`: [task_choice, relay_target]
- `current_positions`: {agent_id: (i, j)} cell 坐标

**输出**:
- `goals`: {agent_id: (i, j)} 目标 cell 坐标
- `action_valid`: action 是否有效
- `error_msg`: 错误信息（如果有）

**关键逻辑**:

1. **解析 action**:
   ```python
   task_choice = int(action[0])
   relay_target = int(action[1])
   ```

2. **验证并 clamp 越界索引**:
   ```python
   if task_choice < 0 or task_choice > self.top_m:
       task_choice = np.clip(task_choice, 0, self.top_m)
       error_msg = f"task_choice out of range, clamped to {task_choice}"
   ```

3. **获取 Top-M 任务**（按 deadline 排序）:
   ```python
   active_tasks = self.state.get_active_tasks()
   active_tasks_sorted = sorted(active_tasks, key=lambda t: t.deadline)
   top_m_tasks = active_tasks_sorted[:self.top_m]
   ```

4. **为 carrier UGV 分配任务目标**:
   ```python
   if task_choice > 0 and task_choice <= len(top_m_tasks):
       selected_task = top_m_tasks[task_choice - 1]
       task_cell = self.grid_map.world_to_cell(...)
       goals[carrier_id] = task_cell
   ```

5. **为非 carrier UGV 分配 relay 目标**:
   ```python
   if relay_target > 0 and relay_target <= len(self.candidate_relays):
       selected_relay = self.candidate_relays[relay_target - 1]
       for i in range(self.n_ugv):
           if i != carrier_id:
               goals[i] = selected_relay
   ```

#### 2.3 修改 `step()` 函数

**优先级**: action > heuristic

```python
if is_decision_step:
    if action is not None:
        # RL 策略：应用 action
        goals, action_valid, action_error = self._apply_rl_action(action, current_positions)
        action_applied = True
    elif self.method in ["greedy", "coverage", "comm_greedy"]:
        # Heuristic 策略
        goals = self._compute_xxx_goals(current_positions)
        action_applied = True

    if action_applied:
        self.ugv_controller.set_goals(goals)
```

#### 2.4 添加 RL Controller 初始化

**文件**: `agcoop/env/core.py` (reset 方法)

```python
elif self.method == "rl" and self.grid_map is not None:
    # Day9 Step 2: RL Controller
    from agcoop.controllers import UGVGreedyController

    K = self.decision_period
    self.ugv_controller = UGVGreedyController(
        K=K,
        grid_map=self.grid_map,
        connectivity=4
    )

    goals = {i: starts[i] for i in starts}
    self.ugv_controller.reset(starts, goals)

    print(f"RL Controller 初始化: K={K}")
```

### 3. 验证脚本

#### 3.1 基础验证

**文件**: `scripts/test_day9_step2_action_space.py`

**测试内容**:
- action_space.sample() 可用
- 各种 action 组合（有效、越界、边界）
- 随机运行 100 步不崩溃

#### 3.2 决策步验证

**文件**: `scripts/test_day9_step2_decision_action.py`

**测试内容**:
- 在决策步应用 action
- 验证 action_applied = True
- 验证越界 action 被 clamp 并标记为无效

## 验收结果

### 基础测试

```
✅ 所有测试用例执行成功
✅ 越界 action 被正确处理（不崩溃）
✅ 随机 action 运行不崩溃

关键结果:
  - action_space.sample() 可用 ✓
  - 越界 action 自动 clamp ✓
  - 随机运行 100 步无崩溃 ✓
```

### 决策步测试

```
✅ 所有决策步都应用了 action
✅ 越界 action 被正确处理

测试用例:
  - [1, 1]: 选择第1个任务和第1个relay ✓
  - [2, 3]: 选择第2个任务和第3个relay ✓
  - [0, 5]: 不指定任务，只指定relay ✓
  - [3, 0]: 只指定任务，不指定relay ✓
  - [10, 20]: 越界索引（被 clamp 到 [5, 12]）✓
```

## 验收标准达成

✅ **标准 1**: `env.action_space.sample()` 的 action 能被 `step()` 正确解析，不抛异常

✅ **标准 2**: 对于越界/无效索引：自动 clamp，并在 `info["action_valid"]=False` 体现

✅ **标准 3**: 随机 action 运行稳定，不崩溃

## 关键设计决策

### 1. 高层选择 vs 低层执行

**设计原则**: RL 只做"高层选择"，底层移动用现有实现

- **RL 决定**: 选哪个任务、选哪个 relay 点
- **底层执行**: BFS/MAPF 规划路径、避障、执行移动

**优势**:
- Action space 小（M+1 × R+1，默认 6×13=78 个离散选项）
- 不易崩溃（底层路径规划已验证）
- 易于训练（离散 action，MultiDiscrete）

### 2. 任务选择策略

**Top-M 按 deadline 排序**:
```python
active_tasks_sorted = sorted(active_tasks, key=lambda t: t.deadline)
top_m_tasks = active_tasks_sorted[:self.top_m]
```

**原因**:
- 优先考虑紧急任务（EDF - Earliest Deadline First）
- 限制 action space 大小（只看前 M 个）
- 符合实际应用场景（deadline-aware）

### 3. 安全回退机制

**越界处理**:
```python
if task_choice < 0 or task_choice > self.top_m:
    task_choice = np.clip(task_choice, 0, self.top_m)
    error_msg = "task_choice out of range, clamped"
    action_valid = False
```

**无效位置处理**:
```python
if not self.grid_map.is_free(ti, tj):
    error_msg = "selected task is not free"
    # 回退到当前位置
    goals[carrier_id] = current_positions[carrier_id]
```

**保证**: 即使 RL 输出无效 action，环境也不会崩溃

### 4. 信息透明化

**info 字典**:
```python
info = {
    'decision_step': is_decision_step,
    'action_applied': action_applied,
    'action_valid': action_valid,
    'action_error': action_error,
    ...
}
```

**用途**:
- 调试 RL 训练
- 监控 action 有效性
- 分析失败原因

## Action Space 示例

**配置**: M=5, R=12

**Action Space**: `MultiDiscrete([6, 13])`

**示例 action**:
- `[0, 0]`: 不指定任务和 relay（保持默认）
- `[1, 5]`: 选择 deadline 最紧急的任务，relay 到第 5 个候选点
- `[3, 0]`: 选择第 3 紧急的任务，不指定 relay
- `[0, 8]`: 不指定任务，relay 到第 8 个候选点

## 与 Day8 Heuristic 的对比

| 维度 | Day8 Heuristic | Day9 RL |
|------|----------------|---------|
| 任务选择 | Greedy (最近) | RL 学习 (Top-M) |
| Relay 选择 | Coverage (固定规则) | RL 学习 (候选点) |
| 通信权重 | 固定 λ | RL 隐式学习 |
| 适应性 | 固定策略 | 动态学习 |

## 下一步（Day9 Step 3）

定义 observation space：
- UGV/UAV 状态
- Top-M 任务信息
- 通信质量摘要
- 候选点摘要

## 文件清单

### 修改的文件
- `agcoop/env/core.py`:
  - 添加 `action_space` 属性
  - 添加 `_apply_rl_action()` 方法
  - 修改 `step()` 函数支持 RL action
  - 添加 RL controller 初始化

### 新增的文件
- `scripts/test_day9_step2_action_space.py`: 基础验证脚本
- `scripts/test_day9_step2_decision_action.py`: 决策步验证脚本
- `DAY9_STEP2_REPORT.md`: 本报告

## 运行验证

```bash
# 基础验证
python scripts/test_day9_step2_action_space.py

# 决策步验证
python scripts/test_day9_step2_decision_action.py
```

---

**Day9 Step 2 状态**: ✅ **完成并验收通过**

**日期**: 2026-02-09
