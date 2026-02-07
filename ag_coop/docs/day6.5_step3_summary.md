# Day6.5 Step 3: UGV Action Generation in step() - 完成总结

## 目标
将 MAPF controller 集成到 `step()` 方法中，实现 Receding Horizon 执行：
- 每 K 步调用 MAPF 规划
- 非决策步执行缓存路径
- 更新 UGV 位置
- 记录 MAPF 信息到 trace 和 metrics

## 实现内容

### 1. 修改 `step()` 方法 (core.py:338-441)

**UGV 动作生成逻辑：**
```python
if self.ugv_controller is not None:
    # 1. 获取当前 UGV 位置（cell 坐标）
    current_positions = {}
    for i, pos in enumerate(self.state.ugv_positions):
        cell = self.grid_map.world_to_cell(pos[0], pos[1])
        current_positions[i] = cell

    # 2. 尝试重规划（每 K 步）
    mapf_plan_info = self.ugv_controller.maybe_replan(
        self.state.t,
        current_positions
    )

    # 3. 执行一步（缓存路径或 fallback WAIT）
    mapf_step_info = self.ugv_controller.step(
        self.state.t,
        current_positions
    )

    # 4. 检查碰撞
    if not mapf_step_info.collision_free:
        raise RuntimeError(f"MAPF collision: {mapf_step_info.collision_error}")

    # 5. 更新 UGV 位置（从 cell 坐标转换回 world 坐标）
    new_ugv_positions = []
    for i in range(self.n_ugv):
        cell = mapf_step_info.positions[i]
        world_pos = self.grid_map.cell_to_world(cell[0], cell[1])
        new_ugv_positions.append(world_pos)

    self.state.ugv_positions = new_ugv_positions
else:
    # Day1: UGV 原地不动（fallback）
    pass
```

**关键点：**
- 坐标转换：world ↔ cell
- 每步都调用 `maybe_replan()` 和 `step()`，controller 内部判断是否真正规划
- 碰撞检测：如果检测到碰撞，抛出异常
- 回退行为：MAPF 禁用时，UGV 保持原地不动

### 2. 修改 `_log_step()` 方法 (core.py:570-634)

**接受 MAPF 信息参数：**
```python
def _log_step(self, snr_best: float = 0.0, outage: bool = False,
               mapf_plan_info=None, mapf_step_info=None) -> None:
```

**提取并记录 MAPF 信息：**
```python
# 提取 MAPF 信息
mapf_called = False
mapf_success = None
mapf_plan_time_ms = None
mapf_fallback = False

if mapf_plan_info is not None:
    mapf_called = mapf_plan_info.called
    mapf_success = mapf_plan_info.success
    mapf_plan_time_ms = mapf_plan_info.plan_time_ms

if mapf_step_info is not None:
    mapf_fallback = mapf_step_info.in_fallback

step_data = {
    't': self.state.t,
    'decision_step': decision_step,
    'mapf_called': mapf_called,
    'mapf_success': mapf_success,
    'mapf_plan_time_ms': mapf_plan_time_ms,
    'mapf_fallback': mapf_fallback,
    # ... 其他字段
}
```

### 3. 修改 `_save_final_metrics()` 方法 (core.py:636-724)

**从 controller 获取统计信息：**
```python
# 获取 MAPF 统计（Day6.5）
mapf_stats = {}
if self.ugv_controller is not None:
    mapf_stats = self.ugv_controller.get_stats()

# 构建指标字典
metrics = {
    # ... 其他字段

    # D. 规划与执行
    'mapf_calls': mapf_stats.get('mapf_calls', 0),
    'mapf_success_calls': mapf_stats.get('mapf_success_calls', 0),
    'mapf_timeout_calls': mapf_stats.get('mapf_timeout_calls', 0),
    'mapf_mean_plan_time_ms': round(mapf_stats.get('mapf_mean_plan_time_ms', 0.0), 2),
    'fallback_wait_steps': mapf_stats.get('fallback_wait_steps', 0),

    # ... 其他字段
}
```

### 4. 修改 `reset()` 方法 - 初始规划 (core.py:303-313)

**在 reset 时执行初始规划（t=0）：**
```python
# 重置 controller
self.ugv_controller.reset(starts, goals)

# 执行初始规划（t=0）
initial_plan_info = self.ugv_controller.maybe_replan(0, starts)

print(f"MAPF Controller 初始化: K={self.mapf_K}, H={self.mapf_H}, budget={self.mapf_budget_ms}ms")
if initial_plan_info.called:
    if initial_plan_info.success:
        print(f"  初始规划成功 ({initial_plan_info.plan_time_ms:.2f} ms)")
    else:
        print(f"  初始规划失败: {initial_plan_info.termination_reason}")
```

**原因：**
- 环境 reset 后 t=0
- 第一次 step() 会将 t 增加到 1
- 如果不在 reset 时规划，第一次 step 时 t=1，不满足 t % K == 0，不会规划
- 但此时没有缓存路径，controller 会报错

### 5. 修改 UGV 初始位置生成 (core.py:226-255)

**MAPF 启用时，采样不同的空闲起始位置：**
```python
# 初始化 UGV 位置
# 如果启用 MAPF 且有地图，从地图中采样不同的空闲位置
if self.mapf_enabled and self.grid_map is not None:
    # 采样不同的空闲起始位置
    free_cells = []
    for x in range(self.grid_map.width):
        for y in range(self.grid_map.height):
            if self.grid_map.is_free(x, y):
                free_cells.append((x, y))

    if len(free_cells) >= self.n_ugv:
        # 随机采样 n_ugv 个不同的空闲位置
        sampled_cells = self.rng.choice(len(free_cells), size=self.n_ugv, replace=False)
        self.state.ugv_positions = []
        for idx in sampled_cells:
            cell = free_cells[idx]
            world_pos = self.grid_map.cell_to_world(cell[0], cell[1])
            self.state.ugv_positions.append(world_pos)
    else:
        # 空闲位置不足，回退到原点
        print(f"警告：空闲位置不足 ({len(free_cells)} < {self.n_ugv})，使用原点")
        self.state.ugv_positions = [(0.0, 0.0) for _ in range(self.n_ugv)]
else:
    # Day1: 所有 UGV 从原点开始
    self.state.ugv_positions = [(0.0, 0.0) for _ in range(self.n_ugv)]
```

**原因：**
- 原来所有 UGV 都从 (0, 0) 开始，导致多个 agent 在同一位置
- MAPF 无法为同一位置的多个 agent 规划路径（no_path）
- 碰撞检测会报错（vertex collision）

## 验收测试

### 测试脚本：`scripts/test_step3_receding_horizon.py`

**Test 1: Receding Horizon 执行**
- ✓ MAPF 调用频率：11 次（1 次初始 + 10 次后续）
- ✓ 决策步调用 MAPF：10 次（t=5, 10, 15, 20, 25, 30, 35, 40, 45, 50）
- ✓ 非决策步执行缓存：40 次（不调用 MAPF）
- ✓ UGV 位置有更新
- ✓ Trace 记录 MAPF 信息
- ✓ Metrics 保存 MAPF 统计

**Test 2: MAPF 禁用（回归保护）**
- ✓ Controller 不存在
- ✓ 环境正常运行 20 步
- ✓ Metrics 中 mapf_calls = 0

**Test 3: UGV 移动行为**
- ✓ UGV 有移动（10/30 步）
- ✓ Fallback 比例 0%
- ✓ 所有 MAPF 调用成功

### 测试结果

```
================================================================================
验收结果
================================================================================
✓ Test 1: Receding Horizon 执行（调用频率、缓存执行）
✓ Test 2: MAPF 禁用（回归保护）
✓ Test 3: UGV 移动行为

✓ Day6.5 Step 3 验收通过
```

## 关键技术细节

### 1. 调用频率计算
- 初始规划：t=0（在 reset 中）
- 后续规划：t=5, 10, 15, ..., 50（每 K=5 步）
- 总调用次数：1 + ceil(steps / K) = 1 + 10 = 11

### 2. 坐标转换
- World 坐标：float，环境使用
- Cell 坐标：int，MAPF 使用
- 转换方法：`grid_map.world_to_cell()` 和 `grid_map.cell_to_world()`

### 3. 时间步语义
- `self.state.t`：当前时间步
- Reset 后：t=0
- 第一次 step()：t 增加到 1
- 因此需要在 reset 时执行 t=0 的规划

### 4. Trace 字段名
- 实际字段：`ugv_pos`（不是 `ugv_positions`）
- Logger 属性：`output_path`（不是 `file_path`）

## 输出示例

### Trace 示例（trace.jsonl）
```json
{
    "t": 5,
    "ugv_pos": [[2.1, 1.3], [2.1, 2.5], [1.9, 1.3]],
    "decision_step": true,
    "mapf_called": true,
    "mapf_success": true,
    "mapf_plan_time_ms": 135.42,
    "mapf_fallback": false,
    ...
}
```

### Metrics 示例（metrics.json）
```json
{
    "mapf_calls": 11,
    "mapf_success_calls": 11,
    "mapf_timeout_calls": 0,
    "mapf_mean_plan_time_ms": 132.32,
    "fallback_wait_steps": 0,
    ...
}
```

## 后续工作

Day6.5 Step 3 完成后，MAPF 已完全集成到 core.py：
- ✓ Step 0: UGV MAPF Wrapper（接口封装）
- ✓ Step 1: Controller 逻辑提取（可复用组件）
- ✓ Step 2: 最小侵入集成（初始化）
- ✓ Step 3: UGV 动作生成（Receding Horizon 执行）

**下一步可能的方向：**
1. 动态目标切换：根据任务/会合点动态更新 goals
2. 性能优化：调整 K、H、budget 参数
3. 失败处理：改进 fallback 策略
4. 多场景测试：不同地图、不同 agent 数量
5. 与 Day7+ 集成：UAV 路径规划、任务分配等

## 文件清单

**修改的文件：**
- `agcoop/env/core.py`：step()、_log_step()、_save_final_metrics()、reset()

**新增的测试：**
- `scripts/test_step3_receding_horizon.py`：Step 3 验收测试

**相关文档：**
- `docs/day6.5_step3_summary.md`：本文档
