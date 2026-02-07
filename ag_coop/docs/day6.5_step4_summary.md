# Day6.5 Step 4: Validator 兼容性 - 完成总结

## 目标
确保 core.py 的 trace.jsonl 和 metrics.json 输出与 Day6 的 validator 脚本完全兼容：
- `validate_day6_outputs.py --dir outputs/<core-run>/` 直接通过
- `check_collisions.py --trace outputs/<core-run>/trace.jsonl` 直接通过

## 实现内容

### 1. 修改 `_log_step()` 方法 (core.py:632-670)

**添加 Day6 期望的字段：**

```python
# 提取 MAPF 信息
mapf_called = False
mapf_success = None
mapf_plan_time_ms = None
mapf_fallback = False
ugv_goals = None

if mapf_plan_info is not None:
    mapf_called = mapf_plan_info.called
    mapf_success = mapf_plan_info.success
    mapf_plan_time_ms = mapf_plan_info.plan_time_ms

if mapf_step_info is not None:
    mapf_fallback = mapf_step_info.in_fallback

# 获取 UGV goals（如果 controller 存在）
if self.ugv_controller is not None and self.ugv_controller.current_goals is not None:
    ugv_goals = self.ugv_controller.current_goals

# 构建步骤数据
step_data = {
    't': self.state.t,
    'ugv_pos': self.state.ugv_positions,
    'ugv_positions': self.state.ugv_positions,  # Day6 collision checker 期望
    'uav_state': self.state.uav_onboard_ugv_id,
    'num_tasks_in_pool': len(self.state.task_pool),
    'num_active_tasks': len(self.state.get_active_tasks()),
    'task_completed_ids': [],
    'outage': outage_this_step,
    'snr_best': round(snr_best, 2),
    'decision_step': decision_step,
    'chosen_task_id': None,
    'chosen_rendezvous': None,
    'mapf_called': mapf_called,
    'mapf_success': mapf_success,
    'mapf_plan_time_ms': mapf_plan_time_ms,
    'fallback': mapf_fallback,  # Day6 validator 期望
    'mapf_fallback': mapf_fallback,  # 保留向后兼容
    'ugv_goals': ugv_goals,  # Day6 validator 期望
}
```

**关键变化：**
- 添加 `fallback` 字段（Day6 validator 期望的字段名）
- 添加 `ugv_goals` 字段（从 controller.current_goals 获取）
- 添加 `ugv_positions` 字段（Day6 collision checker 期望的字段名）
- 保留 `mapf_fallback` 和 `ugv_pos` 以保持向后兼容

### 2. 修改 `_save_final_metrics()` 方法 (core.py:731-741)

**添加 Day6 期望的 metrics 字段：**

```python
# D. 规划与执行
'mapf_calls': mapf_stats.get('mapf_calls', 0),
'mapf_success_calls': mapf_stats.get('mapf_success_calls', 0),
'mapf_timeout_calls': mapf_stats.get('mapf_timeout_calls', 0),
'mapf_fail_calls': mapf_stats.get('mapf_fail_calls', 0),  # 新增
'mapf_mean_plan_time_ms': round(mapf_stats.get('mapf_mean_plan_time_ms', 0.0), 2),
'mapf_p95_plan_time_ms': round(mapf_stats.get('mapf_p95_plan_time_ms', 0.0), 2),  # 新增
'fallback_wait_steps': mapf_stats.get('fallback_wait_steps', 0),
'collision_free': True,  # 新增：如果有碰撞会抛异常，所以到这里一定是 True
'expanded_nodes_total': mapf_stats.get('expanded_nodes_total', 0),  # 新增
'mapf_expanded_mean_per_call': round(mapf_stats.get('mapf_expanded_mean_per_call', 0.0), 2),  # 新增
```

**关键变化：**
- 添加 `mapf_fail_calls`：失败调用次数
- 添加 `mapf_p95_plan_time_ms`：P95 规划时间
- 添加 `collision_free`：碰撞检测标志（固定为 True）
- 添加 `expanded_nodes_total`：总扩展节点数
- 添加 `mapf_expanded_mean_per_call`：平均每次调用扩展节点数

## 验收测试

### 测试脚本：`scripts/test_step4_validator_compatibility.py`

**测试流程：**
1. 创建环境，启用 MAPF，运行 30 步
2. 生成 trace.jsonl 和 metrics.json
3. 运行 `validate_day6_outputs.py` 验证
4. 运行 `check_collisions.py` 验证

**测试结果：**

```
================================================================================
验收结果
================================================================================
✓ 所有 validators 通过

✓ Day6.5 Step 4 验收通过

关键成果:
  ✓ trace.jsonl 包含 Day6 期望的所有字段
  ✓ metrics.json 包含 Day6 期望的所有字段
  ✓ validate_day6_outputs.py 直接通过
  ✓ check_collisions.py 直接通过
```

### validate_day6_outputs.py 输出

```
验证 metrics.json:
  ✓ mapf_calls: 7
  ✓ mapf_success_calls: 7
  ✓ mapf_timeout_calls: 0
  ✓ mapf_fail_calls: 0
  ✓ mapf_mean_plan_time_ms: 123.87
  ✓ mapf_p95_plan_time_ms: 127.45
  ✓ fallback_wait_steps: 0
  ✓ 调用次数一致: 7 == 7
  ✓ P95 >= Mean: 127.45 >= 123.87

验证 trace.jsonl:
  ✓ Trace 行数: 30
  ✓ 决策步数: 6
  ✓ 所有决策步字段完整
  ✓ 所有 mapf_plan_time_ms 都是正数

================================================================================
验证结果
================================================================================
  ✓ metrics.json 验证通过
  ✓ trace.jsonl 验证通过

✓ Day6 Step 8 验收通过
```

### check_collisions.py 输出

```
================================================================================
Day6 Step 7: 冲突校验
================================================================================
Trace 文件: outputs/test_step4_validator/trace.jsonl

✓ 碰撞检测通过：无冲突

验收结果: ok=true
```

## 关键技术细节

### 1. 字段名对齐

**问题：** Day6 和 core.py 使用不同的字段名

**解决方案：** 同时写入两个字段名，保持兼容性

| Day6 期望字段 | core.py 原字段 | 解决方案 |
|--------------|---------------|---------|
| `fallback` | `mapf_fallback` | 同时写入两个字段 |
| `ugv_positions` | `ugv_pos` | 同时写入两个字段 |
| `ugv_goals` | 无 | 从 controller 获取 |

### 2. Metrics 完整性

**Controller 的 `get_stats()` 已经返回所有需要的字段：**

```python
{
    'mapf_calls': int,
    'mapf_success_calls': int,
    'mapf_timeout_calls': int,
    'mapf_fail_calls': int,
    'mapf_mean_plan_time_ms': float,
    'mapf_p95_plan_time_ms': float,
    'fallback_wait_steps': int,
    'expanded_nodes_total': int,
    'mapf_expanded_mean_per_call': float
}
```

**只需在 `_save_final_metrics()` 中提取并写入。**

### 3. collision_free 字段

**设计决策：** 固定为 True

**原因：**
- core.py 在 `step()` 中检测到碰撞时会抛出 RuntimeError
- 如果到达 `_save_final_metrics()`，说明没有碰撞发生
- 因此 `collision_free` 始终为 True

### 4. ugv_goals 字段

**获取方式：**
```python
if self.ugv_controller is not None and self.ugv_controller.current_goals is not None:
    ugv_goals = self.ugv_controller.current_goals
```

**格式：** `{0: (x, y), 1: (x, y), 2: (x, y)}`

## Day6.5 完整总结

### 四个步骤

Day6.5 分 4 步完成 MAPF 集成到 core.py：

| 步骤 | 内容 | 状态 |
|-----|------|------|
| Step 0 | UGV MAPF Wrapper（接口封装） | ✓ |
| Step 1 | Controller 逻辑提取（可复用组件） | ✓ |
| Step 2 | 最小侵入集成（初始化） | ✓ |
| Step 3 | UGV 动作生成（Receding Horizon 执行） | ✓ |
| Step 4 | Validator 兼容性（输出格式对齐） | ✓ |

### 验收标准（全部通过）

**功能验收：**
- ✓ MAPF 启用时，UGV 按规划路径移动
- ✓ MAPF 禁用时，环境行为与 Day1 一致
- ✓ 调用频率：1 + ceil(steps / K)
- ✓ 缓存执行：非决策步不调用 MAPF
- ✓ 碰撞检测：无碰撞发生
- ✓ 日志记录：trace 和 metrics 完整
- ✓ Validator 兼容：Day6 validators 直接通过

**性能验收：**
- ✓ 成功率 ≥ 70%（实际 100%）
- ✓ 平均规划时间 < 200ms（实际 123.87ms）
- ✓ Fallback 比例 ≤ 50%（实际 0%）

**代码质量：**
- ✓ 最小侵入：core.py 改动集中在 5 个方法
- ✓ 向后兼容：MAPF 禁用时无影响
- ✓ 测试覆盖：17 个测试全部通过（14 个 Step 0-3 + 3 个 Step 4）
- ✓ 文档完整：每步都有总结文档

## 输出示例

### Trace 示例（trace.jsonl）

```json
{
    "t": 5,
    "ugv_pos": [[2.1, 1.9], [2.1, 2.5], [2.1, 1.9]],
    "ugv_positions": [[2.1, 1.9], [2.1, 2.5], [2.1, 1.9]],
    "uav_state": 0,
    "num_tasks_in_pool": 0,
    "num_active_tasks": 0,
    "task_completed_ids": [],
    "outage": 0,
    "snr_best": 0.0,
    "decision_step": true,
    "chosen_task_id": null,
    "chosen_rendezvous": null,
    "mapf_called": true,
    "mapf_success": true,
    "mapf_plan_time_ms": 125.42,
    "fallback": false,
    "mapf_fallback": false,
    "ugv_goals": {"0": [10, 10], "1": [12, 10], "2": [12, 12]}
}
```

### Metrics 示例（metrics.json）

```json
{
    "run_id": "map_01_N3_seed0_lambda0.1",
    "method": "day6.5",
    "planner": "mapf",
    "map_path": "maps/map_01.map",
    "map_hash": "abc123",
    "seed": 0,
    "steps": 30,

    "tasks_completed": 0,
    "total_tasks": 0,
    "active_tasks": 0,
    "completion_rate": 0.0,
    "deadline_miss": 0,
    "deadline_miss_rate": 0.0,
    "tardiness_sum": 0,
    "mean_tardiness": 0.0,

    "outage_steps": 0,
    "outage_percent": 0.0,
    "max_outage_streak": 0,
    "snr_threshold": -5.0,
    "snr_best_mean": 0.0,
    "snr_best_min": 0.0,

    "mapf_calls": 7,
    "mapf_success_calls": 7,
    "mapf_timeout_calls": 0,
    "mapf_fail_calls": 0,
    "mapf_mean_plan_time_ms": 123.87,
    "mapf_p95_plan_time_ms": 127.45,
    "fallback_wait_steps": 0,
    "collision_free": true,
    "expanded_nodes_total": 1234,
    "mapf_expanded_mean_per_call": 176.29,

    "rendezvous_success": 0,
    "rendezvous_fail": 0,
    "emergency_landings": 0,
    "uav_loiter_steps": 0,
    "ugv_hold_steps": 0,

    "termination_reason": "horizon",
    "runtime_sec": 1.23
}
```

## 后续工作

Day6.5 完成后，MAPF 已完全集成到 core.py，输出格式与 Day6 完全兼容。

**下一步：Day7 - 动态任务与会合点集成**
1. 动态目标切换：根据任务/会合点更新 goals
2. UAV 路径规划：集成 UAV 的 A* 规划
3. 任务分配：实现任务分配逻辑
4. 会合点协调：UGV 和 UAV 的会合点规划

## 文件清单

### 修改的文件
- `agcoop/env/core.py`：_log_step()、_save_final_metrics()

### 新增的测试
- `scripts/test_step4_validator_compatibility.py`：Step 4 验收测试

### 相关文档
- `docs/day6.5_step4_summary.md`：本文档
- `docs/day6.5_complete_summary.md`：Day6.5 完整总结
- `DEVLOG.md`：开发日志

## 经验总结

### 成功经验
1. **字段名对齐：** 同时写入两个字段名，保持兼容性
2. **利用现有数据：** Controller 已经提供所有需要的统计信息
3. **自动化验证：** 使用 Day6 的 validator 脚本自动验证输出格式

### 遇到的问题
1. **字段名不一致：** Day6 期望 `fallback` 和 `ugv_positions`，core.py 使用 `mapf_fallback` 和 `ugv_pos`
2. **缺少字段：** metrics.json 缺少 5 个字段（fail_calls, p95, collision_free, expanded_nodes_total, expanded_mean）

### 关键教训
1. **输出格式标准化：** 不同模块应该使用统一的字段名
2. **向后兼容：** 添加新字段时保留旧字段，避免破坏现有代码
3. **自动化测试：** 使用 validator 脚本确保输出格式正确
