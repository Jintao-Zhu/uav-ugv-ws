# Day6.5-7 核心回归验收报告

## 🎯 测试目的

证明 core.py 集成后仍满足 Day6 的"真值标准"

---

## ✅ 测试配置

```yaml
seed: 0
n_ugv: 3
steps: 500
K: 5
H: 40
budget_ms: 300
```

**输出目录**: `outputs/day6_5_core_seed0/`

---

## 📊 验收结果

### 1.1 长 Episode 运行（500 steps）

#### 验收标准（6 项全部通过）

| # | 验收标准 | 期望值 | 实际值 | 结果 |
|---|----------|--------|--------|------|
| 1 | collision_free | true | true | ✅ |
| 2 | mapf_calls | 100 | 100 | ✅ |
| 3 | mapf_success_calls | == mapf_calls | 100/100 (100%) | ✅ |
| 4 | fallback_wait_steps | 0 | 0 | ✅ |
| 5 | mapf_p95_plan_time_ms | < 300ms | 145.39ms | ✅ |
| 6 | trace 决策步逻辑 | 正确 | 正确 | ✅ |

#### 详细验证

**验收标准 6：trace.jsonl 决策步逻辑**
- ✅ 决策步时间戳正确: t=1, 6, 11, 16, 21, ..., 496
- ✅ 决策步总数: 100
- ✅ 所有决策步: `decision_step=true` && `mapf_called=true`
- ✅ 所有非决策步: `mapf_called=false` (缓存执行)

---

### 1.2 离线校验脚本

#### Step 7: 冲突校验 ✅

```bash
python scripts/check_collisions.py --trace outputs/day6_5_core_seed0/trace.jsonl
```

**结果**: ✅ `ok=true` (无冲突)
- 无 Vertex collision
- 无 Edge swap collision

---

#### Step 8: 输出验证 ✅

```bash
python scripts/validate_day6_outputs.py --dir outputs/day6_5_core_seed0
```

**结果**: ✅ 验收通过

**验证项**:
- ✅ metrics.json 验证通过
  - mapf_calls: 100
  - mapf_success_calls: 100
  - mapf_timeout_calls: 0
  - mapf_fail_calls: 0
  - mapf_mean_plan_time_ms: 126.0
  - mapf_p95_plan_time_ms: 145.39
  - fallback_wait_steps: 0
  - 调用次数一致: 100 == 100
  - P95 >= Mean: 145.39 >= 126.00

- ✅ trace.jsonl 验证通过
  - Trace 行数: 500
  - 决策步数: 100
  - 所有决策步字段完整
  - 所有 mapf_plan_time_ms 都是正数

---

## 🎉 验收结论

### ✅ Day6.5-7 核心回归测试全部通过！

**证明**：core.py 集成后仍满足 Day6 的"真值标准"

**关键成就**：
- ✅ 迁移没有破坏 Day6 的正确性工具链
- ✅ 所有验收脚本都通过
- ✅ 可以无痛进入下一阶段

---

## 📈 MAPF 性能摘要

| 指标 | 值 |
|------|-----|
| 调用次数 | 100 |
| 成功率 | 100% (100/100) |
| 平均规划时间 | 126.00ms |
| P95 规划时间 | 145.39ms |
| 时间预算 | 300ms |
| 预算利用率 | 48.5% (145.39/300) |

---

## 🔍 系统行为验证

| 行为 | 验证结果 |
|------|----------|
| 无碰撞 | ✅ collision_free=true |
| 无 fallback | ✅ fallback_wait_steps=0 |
| 决策步正确 | ✅ 100 次，间隔 K=5 |
| 缓存执行正确 | ✅ 非决策步未调用 MAPF |

---

## 📝 关键经验

1. **决策步逻辑修复**：从 `t % K == 0` 改为 `(t-1) % K == 0`，使决策步从 t=1 开始
2. **调用次数公式**：`floor((steps-1)/K) + 1` 正确计算决策步数量
3. **验收脚本完整性**：Day6 的验收脚本完全兼容 core.py 集成后的输出
4. **性能表现**：P95 规划时间 145.39ms，远低于 300ms 预算，系统性能良好

---

## 🚀 下一步

Day6.5-7 验收通过后，可以进入：
- **Day6.5-8**：压力测试（更多 agent、更长 horizon）
- **Day7**：系统闭环 + Baseline 对比

---

**测试时间**: 2024-02-08
**测试人员**: AG_COOP Team
**验收状态**: ✅ 通过
