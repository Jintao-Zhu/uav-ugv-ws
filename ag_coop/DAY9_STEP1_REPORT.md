# Day9 Step 1 完成报告

## 目标

冻结"RL 控制点"与调用时机（只在决策步生效）

## 实现内容

### 1. 修改 `core.py` 的 `step()` 函数

**文件**: `agcoop/env/core.py`

**关键修改**:

1. **添加决策步判断**:
   ```python
   is_decision_step = (self.state.t % self.decision_period == 0)
   action_applied = False
   ```

2. **只在决策步应用 action**:
   ```python
   if is_decision_step:
       if self.method in ["greedy", "coverage", "comm_greedy"]:
           # 计算目标并应用
           goals = self._compute_xxx_goals(current_positions)
           self.ugv_controller.set_goals(goals)
           action_applied = True
       # Day9: 未来 RL 策略会在这里应用 action
   ```

3. **在 info 中返回决策步标志**:
   ```python
   info = {
       ...
       'decision_step': is_decision_step,
       'action_applied': action_applied,
   }
   ```

### 2. 验证脚本

**文件**: `scripts/test_day9_step1_decision_timing.py`

**验证内容**:
- 决策步数量 = steps // K
- 所有非决策步的 `action_applied = False`
- 所有决策步的 `action_applied = True`（对于 greedy 方法）

**扩展验证**: `scripts/test_day9_step1_multiple_K.py`
- 测试多个 K 值（3, 5, 8, 10）
- 确保逻辑在不同决策周期下都正确

## 验收结果

### 基础测试（K=5, steps=500）

```
✅ 决策步数量: 100/100 ✓
✅ 非决策步不应用 action: 0 次违规 ✓
✅ action 应用总次数: 100
```

### 扩展测试（多个 K 值）

```
✅ K=3, steps=300: 通过 (100 决策步)
✅ K=5, steps=500: 通过 (100 决策步)
✅ K=8, steps=400: 通过 (50 决策步)
✅ K=10, steps=500: 通过 (50 决策步)
```

## 验收标准达成

✅ **标准 1**: 在 rollout 的 trace 中，所有 `decision_step=false` 的 step 不读取/不应用 action（通过 `info["action_applied"]=False` 体现）

✅ **标准 2**: 决策步数量严格等于 `steps // K`（例如 500 步、K=5 → 100 次决策步）

## 关键设计

### 1. 决策步判断

```python
is_decision_step = (self.state.t % self.decision_period == 0)
```

- 与 Day6 的 receding horizon 结构一致
- t=0, K, 2K, 3K, ... 为决策步

### 2. Action 应用逻辑

```python
if is_decision_step:
    # 只在决策步更新目标
    if self.method in ["greedy", "coverage", "comm_greedy"]:
        goals = self._compute_goals(...)
        self.ugv_controller.set_goals(goals)
        action_applied = True
    # 未来 RL 会在这里应用 action
```

- 非决策步：继续执行缓存的路径（MAPF controller 的 receding horizon）
- 决策步：重新计算目标并规划

### 3. 信息透明化

```python
info = {
    'decision_step': is_decision_step,
    'action_applied': action_applied,
    ...
}
```

- 外部可以清楚地知道每一步是否为决策步
- 可以验证 action 是否被正确应用

## 为 Day9 后续步骤准备

### RL Action 接入点已预留

```python
if is_decision_step:
    if self.method in ["greedy", "coverage", "comm_greedy"]:
        # 现有 heuristic 方法
        ...
    elif action is not None:
        # Day9 Step 2+: RL action 应用
        goals = self._apply_rl_action(action, current_positions)
        self.ugv_controller.set_goals(goals)
        action_applied = True
```

### 配置参数

- `decision_period` (K): 从配置文件读取，默认 5
- `carrier_id`: 固定为 0（配置中写死）

## 下一步（Day9 Step 2）

定义 RL action 的具体结构：
- `action = (task_choice, relay_targets)`
- `task_choice`: 从 Top-M 任务中选择哪个
- `relay_targets`: 非 carrier UGV 的移动目标

## 文件清单

### 修改的文件
- `agcoop/env/core.py`: 修改 `step()` 函数

### 新增的文件
- `scripts/test_day9_step1_decision_timing.py`: 基础验证脚本
- `scripts/test_day9_step1_multiple_K.py`: 扩展验证脚本
- `DAY9_STEP1_REPORT.md`: 本报告

## 运行验证

```bash
# 基础验证
python scripts/test_day9_step1_decision_timing.py

# 扩展验证（多个 K 值）
python scripts/test_day9_step1_multiple_K.py
```

---

**Day9 Step 1 状态**: ✅ **完成并验收通过**

**日期**: 2026-02-09
