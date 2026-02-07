# Day 6.5 调试工作流程

## 概述

如果 Day6.5 任一验收没过，按照本文档快速生成调试材料，帮助快速定位问题是：
- **Controller bug**（路径执行逻辑）
- **Core 集成 bug**（MAPF 调用失败）
- **日志/口径 bug**（指标计算错误）

---

## 快速使用

### 方法 1：使用自动化脚本（推荐）

```bash
# 生成完整调试报告
python scripts/generate_debug_report.py --run outputs/test_step5_exp_b

# 如果知道具体出错的行号
python scripts/generate_debug_report.py --run outputs/test_step5_exp_b --error-line 25
```

脚本会自动输出以下 4 个关键材料：
1. ✅ **config_resolved.yaml**（确认 K/H/budget/seed/n_agents）
2. ✅ **metrics.json**（关键指标）
3. ✅ **trace.jsonl 截取**（第一次出错前后 30 行，尤其是决策步附近）
4. ✅ **check_collisions.py 输出**（若报冲突，附冲突类型 vertex/edge swap）

### 方法 2：手动收集材料

如果需要手动收集，按以下顺序：

```bash
# 1. 查看配置
cat outputs/<run>/config_resolved.yaml

# 2. 查看指标
cat outputs/<run>/metrics.json

# 3. 查看 trace（截取关键部分）
head -n 30 outputs/<run>/trace.jsonl  # 开头 30 行
tail -n 30 outputs/<run>/trace.jsonl  # 结尾 30 行

# 4. 运行冲突检测
python scripts/check_collisions.py --trace outputs/<run>/trace.jsonl
```

---

## 需要回传的 4 个材料详解

### 1. config_resolved.yaml

**作用**：确认测试参数是否正确

**关键字段**：
```yaml
robots:
  n_ugv: 3          # UGV 数量（K）
  n_uav: 1          # UAV 数量

mapf:
  H: 40             # MAPF 规划时域
  time_budget_ms: 0 # MAPF 时间预算（0 表示无限制）

episode:
  horizon_steps: 50 # 仿真总步数
  seed: 0           # 随机种子
```

**检查点**：
- ✅ `n_ugv` 是否符合测试用例要求
- ✅ `H` 是否设置正确（通常 40）
- ✅ `time_budget_ms` 是否合理（0 或 5-50ms）
- ✅ `seed` 是否正确（用于复现问题）

---

### 2. metrics.json

**作用**：快速判断问题类型

**关键指标**：
```json
{
  "collision_free": true,        // ❌ false → controller bug
  "mapf_calls": 11,              // MAPF 总调用次数
  "mapf_success_calls": 0,       // MAPF 成功次数
  "mapf_timeout_calls": 11,      // ❌ 全超时 → time_budget 太小
  "mapf_fail_calls": 0,          // ❌ >0 → core 集成 bug
  "completion_rate": 0.0,        // 任务完成率
  "termination_reason": "horizon" // 终止原因
}
```

**问题诊断表**：

| 指标 | 异常值 | 可能原因 |
|------|--------|----------|
| `collision_free` | `false` | **Controller bug**：路径执行逻辑错误 |
| `mapf_fail_calls` | `> 0` | **Core 集成 bug**：MAPF 调用失败 |
| `mapf_timeout_calls` | `== mapf_calls` | `time_budget_ms` 太小或 MAPF 性能问题 |
| `completion_rate` | `0.0` | 任务分配或路径规划逻辑问题 |
| `expanded_nodes_total` | `0` | MAPF 未正常运行 |

---

### 3. trace.jsonl 截取

**作用**：查看具体执行过程，定位第一次出错的时刻

**格式说明**：
```
[  4] t=  5 🔵 UGV:[[2.1, 0.9], [2.1, 2.5], [2.3, 1.3]] UAV:[]
       └─ MAPF: timeout (time=0.01ms, expanded=0)
```

- `[4]`：trace 文件行号
- `t=5`：仿真时间步
- `🔵`：决策步标记（decision_step=true）
- `UGV/UAV`：机器人位置
- `MAPF`：MAPF 调用结果（仅决策步显示）

**关键信息**：
- **决策步附近**：查看 MAPF 调用状态（success/timeout/fail）
- **位置变化**：检查机器人是否按计划移动
- **冲突时刻**：如果有碰撞，定位发生的时间步

**示例分析**：

```
[  4] t=  5 🔵 UGV:[[2, 1], [2, 2], [2, 3]] UAV:[]
       └─ MAPF: timeout (time=0.01ms, expanded=0)
[  5] t=  6    UGV:[[2, 1], [2, 2], [2, 3]] UAV:[]  ← 位置未变化
[  6] t=  7    UGV:[[2, 1], [2, 2], [2, 3]] UAV:[]  ← 持续等待
```

**诊断**：MAPF 超时 → UGV 使用 fallback（原地等待）

---

### 4. check_collisions.py 输出

**作用**：验证是否有碰撞（vertex/edge collision）

**正常输出**：
```
✓ 碰撞检测通过：无冲突
验收结果: ok=true
```

**异常输出示例**：

#### Vertex Collision（顶点冲突）
```
✗ 碰撞检测失败
  错误: Vertex collision at t=15: agent 0 and 1 at (5, 5)
验收结果: ok=false
```
→ 两个 agent 在同一时刻占据同一位置

#### Edge Collision（边冲突/交换冲突）
```
✗ 碰撞检测失败
  错误: Edge collision at t=20: agent 0 and 1 swap positions ((3, 4) <-> (4, 4))
验收结果: ok=false
```
→ 两个 agent 交换位置（A→B 同时 B→A）

**如果检测到冲突**：
1. 记录冲突类型（vertex/edge）
2. 记录冲突时刻（t=?）
3. 记录涉及的 agent ID
4. 在 trace.jsonl 中查看该时刻前后的执行情况

---

## 问题定位决策树

```
验收失败
    │
    ├─ collision_free = false
    │   └─ 【Controller bug】检查路径执行逻辑
    │       - 查看 trace 中冲突时刻的位置变化
    │       - 检查 controller.py 的 step() 方法
    │       - 验证 MAPF 路径是否正确执行
    │
    ├─ mapf_fail_calls > 0
    │   └─ 【Core 集成 bug】检查 MAPF 调用
    │       - 查看 trace 中 MAPF 失败的决策步
    │       - 检查 mapf_interface.py 的调用逻辑
    │       - 验证输入参数是否正确
    │
    ├─ mapf_timeout_calls = mapf_calls（全超时）
    │   └─ 【配置问题】检查 time_budget_ms
    │       - 如果 budget=0，检查 MAPF 性能
    │       - 如果 budget>0，尝试增加预算
    │
    ├─ completion_rate = 0（无任务完成）
    │   └─ 【逻辑问题】检查任务分配
    │       - 查看 trace 中任务分配情况
    │       - 检查 rendezvous 选择逻辑
    │       - 验证 UAV 是否正常移动
    │
    └─ 指标正常但验收失败
        └─ 【日志/口径 bug】检查指标计算
            - 对比 trace 和 metrics 的一致性
            - 检查 logger.py 的指标统计逻辑
```

---

## 常见问题排查

### Q1: 所有 MAPF 调用都超时

**症状**：
```json
"mapf_calls": 11,
"mapf_timeout_calls": 11,
"mapf_success_calls": 0
```

**可能原因**：
1. `time_budget_ms = 0` 但 MAPF 实际运行时间过长
2. `time_budget_ms` 设置过小（如 1ms）
3. MAPF 算法陷入死循环或性能问题

**排查步骤**：
```bash
# 1. 检查配置
grep "time_budget_ms" outputs/<run>/config_resolved.yaml

# 2. 查看实际运行时间
grep "mapf_plan_time_ms" outputs/<run>/trace.jsonl | head -5

# 3. 尝试增加预算
# 修改配置文件，设置 time_budget_ms: 50
```

---

### Q2: collision_free = false

**症状**：
```json
"collision_free": false
```

**排查步骤**：

```bash
# 1. 运行冲突检测，获取具体冲突信息
python scripts/check_collisions.py --trace outputs/<run>/trace.jsonl

# 输出示例：
# ✗ Vertex collision at t=15: agent 0 and 1 at (5, 5)

# 2. 查看冲突时刻的 trace
sed -n '13,17p' outputs/<run>/trace.jsonl  # t=15 前后

# 3. 检查 MAPF 规划结果
# 查看 t=15 之前最近的决策步（t=10 或 t=15）
grep '"decision_step": true' outputs/<run>/trace.jsonl | grep -B2 -A2 '"t": 15'
```

**常见原因**：
- MAPF 规划的路径本身有冲突（MAPF bug）
- Controller 执行路径时出错（controller bug）
- Fallback 逻辑导致冲突（多个 agent 同时 fallback 到同一位置）

---

### Q3: completion_rate = 0（无任务完成）

**症状**：
```json
"completion_rate": 0.0,
"total_tasks": 3,
"tasks_completed": 0
```

**排查步骤**：

```bash
# 1. 查看任务分配情况
grep "chosen_task_id" outputs/<run>/trace.jsonl | grep -v "null"

# 2. 查看 UAV 状态变化
grep "uav_state" outputs/<run>/trace.jsonl | head -20

# 3. 查看 rendezvous 选择
grep "chosen_rendezvous" outputs/<run>/trace.jsonl | grep -v "null"
```

**可能原因**：
- UAV 未选择任务（任务分配逻辑问题）
- UAV 未到达 rendezvous 点（路径规划问题）
- 服务时间不足（service_time 配置问题）

---

## 示例：完整调试流程

### 场景：验收失败，需要定位问题

**步骤 1：生成调试报告**

```bash
python scripts/generate_debug_report.py --run outputs/test_step5_exp_b
```

**步骤 2：分析输出**

```
关键指标摘要:
  collision_free: True          ✅ 无碰撞
  mapf_calls: 11
  mapf_success_calls: 0         ❌ 全部失败
  mapf_timeout_calls: 11        ❌ 全部超时
  mapf_fail_calls: 0
  completion_rate: 0.0          ⚠️  无任务完成
```

**步骤 3：诊断**

根据指标：
- ✅ `collision_free = true` → 不是 controller bug
- ❌ `mapf_timeout_calls = 11` → MAPF 超时问题
- ⚠️  `completion_rate = 0` → 可能是超时导致

**步骤 4：查看配置**

```yaml
mapf:
  time_budget_ms: 0  # ← 无限制，但仍然超时
```

**步骤 5：查看 trace**

```
[  4] t=  5 🔵 UGV:[[2.1, 0.9], [2.1, 2.5], [2.3, 1.3]] UAV:[]
       └─ MAPF: timeout (time=0.01ms, expanded=0)
```

**步骤 6：结论**

- MAPF 调用立即返回超时（0.01ms）
- `expanded=0` 说明 MAPF 未执行搜索
- **问题定位**：Core 集成 bug，MAPF 接口调用失败

**步骤 7：修复方向**

检查 `mapf_interface.py`：
- MAPF 输入参数是否正确
- MAPF 返回值是否正确解析
- 超时判断逻辑是否有误

---

## 工具脚本说明

### generate_debug_report.py

**功能**：一键生成完整调试报告

**用法**：
```bash
python scripts/generate_debug_report.py --run <output_dir> [--error-line <line_num>]
```

**参数**：
- `--run`：必需，输出目录路径（如 `outputs/test_step5_exp_b`）
- `--error-line`：可选，trace 中出错的行号（用于精确定位）

**输出**：
1. 配置摘要（关键参数）
2. 指标摘要（关键指标）
3. Trace 截取（决策步附近或指定行附近）
4. 冲突检测结果
5. 调试建议（基于指标自动生成）

---

### check_collisions.py

**功能**：离线验证 trace 中是否有碰撞

**用法**：
```bash
python scripts/check_collisions.py --trace <trace.jsonl>
```

**检测类型**：
- **Vertex collision**：两个 agent 同时占据同一位置
- **Edge collision**：两个 agent 交换位置

**返回值**：
- Exit code 0：无冲突
- Exit code 1：检测到冲突

---

## 快速参考

### 一键命令

```bash
# 生成调试报告
python scripts/generate_debug_report.py --run outputs/<run>

# 检查冲突
python scripts/check_collisions.py --trace outputs/<run>/trace.jsonl

# 查看配置
cat outputs/<run>/config_resolved.yaml | grep -E "n_ugv|n_uav|H:|time_budget_ms|seed"

# 查看关键指标
cat outputs/<run>/metrics.json | grep -E "collision_free|mapf_.*_calls|completion_rate"
```

### 关键文件位置

```
outputs/<run>/
├── config_resolved.yaml   # 完整配置
├── metrics.json           # 运行指标
└── trace.jsonl            # 执行轨迹
```

### 问题类型速查

| 症状 | 问题类型 | 检查重点 |
|------|----------|----------|
| `collision_free=false` | Controller bug | trace 冲突时刻 + controller.py |
| `mapf_fail_calls>0` | Core 集成 bug | mapf_interface.py 调用逻辑 |
| `mapf_timeout_calls=mapf_calls` | 配置/性能问题 | time_budget_ms + MAPF 性能 |
| `completion_rate=0` | 逻辑问题 | 任务分配 + rendezvous 选择 |
| 指标正常但验收失败 | 日志/口径 bug | logger.py 指标统计 |

---

## 总结

当 Day6.5 验收失败时，按以下流程快速定位：

1. **运行调试脚本**：`python scripts/generate_debug_report.py --run outputs/<run>`
2. **查看 4 个材料**：config + metrics + trace + collision
3. **使用决策树**：根据指标判断问题类型
4. **定位具体代码**：controller / core / logger
5. **修复并验证**：重新运行验收

**关键原则**：
- ✅ 先看 metrics，快速判断问题类型
- ✅ 再看 trace，定位具体时刻
- ✅ 最后看代码，修复 bug

---

## 附录：trace.jsonl 字段说明

```json
{
  "t": 5,                          // 时间步
  "ugv_positions": [[2, 1], ...],  // UGV 位置
  "uav_positions": [[5, 5]],       // UAV 位置
  "decision_step": true,           // 是否为决策步
  "mapf_called": true,             // 是否调用 MAPF
  "mapf_success": false,           // MAPF 是否成功
  "mapf_plan_time_ms": 0.01,       // MAPF 运行时间
  "fallback": true,                // 是否使用 fallback
  "num_active_tasks": 2,           // 活跃任务数
  "chosen_task_id": 1,             // 选中的任务 ID
  "chosen_rendezvous": [8, 8],     // 选中的 rendezvous 点
  "outage": 0,                     // 是否通信中断
  "snr_best": 26.02                // 最佳 SNR
}
```

---

**文档版本**：v1.0
**最后更新**：2024-02-07
**维护者**：AG_COOP Team
