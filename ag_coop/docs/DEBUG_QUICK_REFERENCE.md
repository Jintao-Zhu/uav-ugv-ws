# Day 6.5 调试速查卡

## 🚀 快速开始

```bash
# 方法 1: 快速诊断（30秒）
./scripts/quick_debug.sh outputs/<run>

# 方法 2: 完整报告（包含 trace 截取）
python scripts/generate_debug_report.py --run outputs/<run>

# 方法 3: 仅检查冲突
python scripts/check_collisions.py --trace outputs/<run>/trace.jsonl
```

---

## 📋 需要回传的 4 个材料

当验收失败时，提供以下材料即可快速定位问题：

### ✅ 1. config_resolved.yaml
```bash
cat outputs/<run>/config_resolved.yaml
```
**关键字段**: `n_ugv`, `n_uav`, `H`, `time_budget_ms`, `seed`

### ✅ 2. metrics.json
```bash
cat outputs/<run>/metrics.json
```
**关键指标**: `collision_free`, `mapf_*_calls`, `completion_rate`

### ✅ 3. trace.jsonl 截取（前后 30 行）
```bash
# 如果知道出错行号（如第 25 行）
sed -n '1,55p' outputs/<run>/trace.jsonl  # 第 1-55 行

# 或查看决策步附近
grep -n '"decision_step": true' outputs/<run>/trace.jsonl | head -3
```

### ✅ 4. check_collisions.py 输出
```bash
python scripts/check_collisions.py --trace outputs/<run>/trace.jsonl
```
**输出**: 冲突类型（vertex/edge swap）或无冲突

---

## 🔍 问题诊断速查表

| 指标 | 异常值 | 问题类型 | 检查重点 |
|------|--------|----------|----------|
| `collision_free` | `false` | **Controller bug** | trace 冲突时刻 + `controller.py` |
| `mapf_fail_calls` | `> 0` | **Core 集成 bug** | `mapf_interface.py` 调用逻辑 |
| `mapf_timeout_calls` | `== mapf_calls` | **配置/性能问题** | `time_budget_ms` + MAPF 性能 |
| `completion_rate` | `0.0` | **逻辑问题** | 任务分配 + rendezvous 选择 |
| 指标正常 | 但验收失败 | **日志/口径 bug** | `logger.py` 指标统计 |

---

## 🛠️ 常见问题快速修复

### ❌ collision_free = false

```bash
# 1. 获取冲突详情
python scripts/check_collisions.py --trace outputs/<run>/trace.jsonl

# 输出示例: Vertex collision at t=15: agent 0 and 1 at (5, 5)

# 2. 查看冲突时刻的 trace
sed -n '13,17p' outputs/<run>/trace.jsonl  # t=15 前后

# 3. 检查最近的决策步
grep '"decision_step": true' outputs/<run>/trace.jsonl | grep -B2 -A2 '"t": 15'
```

**可能原因**:
- MAPF 规划的路径有冲突 → 检查 MAPF 算法
- Controller 执行路径出错 → 检查 `controller.py`
- Fallback 逻辑冲突 → 检查 fallback 策略

---

### ⚠️ 所有 MAPF 调用都超时

```bash
# 1. 检查配置
grep "time_budget_ms" outputs/<run>/config_resolved.yaml

# 2. 查看实际运行时间
grep "mapf_plan_time_ms" outputs/<run>/trace.jsonl | head -5

# 3. 查看扩展节点数
grep "expanded" outputs/<run>/trace.jsonl | head -5
```

**可能原因**:
- `time_budget_ms` 太小 → 增加到 50ms
- MAPF 性能问题 → 检查地图复杂度
- MAPF 未正常运行 → 检查 `mapf_interface.py`

---

### ⚠️ completion_rate = 0

```bash
# 1. 查看任务分配
grep "chosen_task_id" outputs/<run>/trace.jsonl | grep -v "null"

# 2. 查看 UAV 状态
grep "uav_state" outputs/<run>/trace.jsonl | head -20

# 3. 查看 rendezvous 选择
grep "chosen_rendezvous" outputs/<run>/trace.jsonl | grep -v "null"
```

**可能原因**:
- UAV 未选择任务 → 检查任务分配逻辑
- UAV 未到达 rendezvous → 检查路径规划
- 服务时间不足 → 检查 `service_time` 配置

---

## 📊 trace.jsonl 关键字段

```json
{
  "t": 5,                    // 时间步
  "decision_step": true,     // 🔵 决策步标记
  "mapf_called": true,       // 是否调用 MAPF
  "mapf_success": false,     // MAPF 是否成功
  "mapf_plan_time_ms": 0.01, // MAPF 运行时间
  "fallback": true,          // 是否使用 fallback
  "ugv_positions": [[2,1]],  // UGV 位置
  "chosen_task_id": 1,       // 选中的任务
  "outage": 0                // 通信中断
}
```

**决策步标记**: `🔵` 表示该时刻调用了 MAPF

---

## 🎯 调试流程（3 步）

### Step 1: 快速诊断
```bash
./scripts/quick_debug.sh outputs/<run>
```
→ 30秒内看到关键指标和诊断建议

### Step 2: 定位问题
根据诊断建议，查看对应的代码模块：
- Controller bug → `src/controller.py`
- Core 集成 bug → `src/mapf_interface.py`
- 日志/口径 bug → `src/logger.py`

### Step 3: 生成完整报告
```bash
python scripts/generate_debug_report.py --run outputs/<run>
```
→ 包含 config + metrics + trace 截取 + collision 检测

---

## 📁 文件位置

```
ag_coop/
├── scripts/
│   ├── quick_debug.sh              # 快速诊断脚本
│   ├── generate_debug_report.py    # 完整报告生成器
│   └── check_collisions.py         # 冲突检测脚本
├── docs/
│   └── DAY6_DEBUG_WORKFLOW.md      # 详细调试文档
└── outputs/<run>/
    ├── config_resolved.yaml        # 完整配置
    ├── metrics.json                # 运行指标
    └── trace.jsonl                 # 执行轨迹
```

---

## 💡 提示

- ✅ **优先使用** `quick_debug.sh`，快速看到问题
- ✅ **需要详细分析** 时使用 `generate_debug_report.py`
- ✅ **仅检查冲突** 时使用 `check_collisions.py`
- ✅ **trace 很大** 时，只截取关键部分（决策步附近）

---

## 🔗 相关文档

- 详细调试流程: `docs/DAY6_DEBUG_WORKFLOW.md`
- 验收标准: `DEVLOG.md` → Day 6.5
- 冲突检测说明: `scripts/check_collisions.py` 头部注释

---

**版本**: v1.0 | **更新**: 2024-02-07
