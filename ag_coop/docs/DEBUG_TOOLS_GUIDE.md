# Day 6 调试工具包 - 使用指南

## 📦 工具包内容

### 脚本工具（3 个）

1. **quick_debug.sh** - 快速诊断（推荐首选）
2. **generate_debug_report.py** - 完整报告生成器
3. **check_collisions.py** - 冲突检测脚本

### 文档（2 个）

1. **DAY6_DEBUG_WORKFLOW.md** - 详细调试流程（5000+ 字）
2. **DEBUG_QUICK_REFERENCE.md** - 速查卡（1 页纸）

---

## 🚀 快速开始（3 种方式）

### 方式 1：快速诊断（30秒）⭐ 推荐

```bash
./scripts/quick_debug.sh outputs/<run>
```

**适用场景**：
- ✅ 验收刚失败，想快速看到问题
- ✅ 需要立即判断问题类型
- ✅ 时间紧迫，需要快速决策

**输出内容**：
- 文件检查（3 个文件是否存在）
- 关键配置（6 个参数）
- 关键指标（7 个指标）
- 冲突检测结果
- 自动诊断建议

**示例输出**：
```
📊 关键指标:
  collision_free: True
  mapf_timeout_calls: 11 (100%)
  completion_rate: 0.00%

💡 诊断建议:
  ⚠️  所有 MAPF 调用都超时 → 检查 time_budget_ms 设置
```

---

### 方式 2：完整报告（需要详细分析）

```bash
python scripts/generate_debug_report.py --run outputs/<run>

# 如果知道出错的行号
python scripts/generate_debug_report.py --run outputs/<run> --error-line 25
```

**适用场景**：
- ✅ 需要回传完整材料给开发者
- ✅ 需要查看 trace 详细内容
- ✅ 需要深入分析问题

**输出内容**：
1. config_resolved.yaml 完整内容 + 关键参数摘要
2. metrics.json 完整内容 + 关键指标摘要
3. trace.jsonl 智能截取（决策步附近或指定行附近）
4. check_collisions.py 自动运行结果
5. 基于指标的自动诊断建议

**trace 截取示例**：
```
[  4] t=  5 🔵 UGV:[[2.1, 0.9], [2.1, 2.5], [2.3, 1.3]] UAV:[]
       └─ MAPF: timeout (time=0.01ms, expanded=0)
[  5] t=  6    UGV:[[2.1, 0.9], [2.1, 2.5], [2.3, 1.3]] UAV:[]
```

---

### 方式 3：仅检查冲突

```bash
python scripts/check_collisions.py --trace outputs/<run>/trace.jsonl
```

**适用场景**：
- ✅ 只需要验证是否有碰撞
- ✅ 需要确认冲突类型（vertex/edge）
- ✅ 快速验证修复效果

**输出示例**：

正常情况：
```
✓ 碰撞检测通过：无冲突
验收结果: ok=true
```

发现冲突：
```
✗ 碰撞检测失败
  错误: Vertex collision at t=15: agent 0 and 1 at (5, 5)
验收结果: ok=false
```

---

## 📋 需要回传的 4 个材料

当验收失败时，运行以下命令获取材料：

```bash
# 一键生成所有材料
python scripts/generate_debug_report.py --run outputs/<run>
```

或手动收集：

```bash
# 1. 配置文件
cat outputs/<run>/config_resolved.yaml

# 2. 指标文件
cat outputs/<run>/metrics.json

# 3. trace 截取（前 30 行 + 后 30 行）
head -n 30 outputs/<run>/trace.jsonl
tail -n 30 outputs/<run>/trace.jsonl

# 4. 冲突检测
python scripts/check_collisions.py --trace outputs/<run>/trace.jsonl
```

---

## 🔍 问题诊断速查

### 根据指标快速判断问题类型

| 指标 | 异常值 | 问题类型 | 下一步 |
|------|--------|----------|--------|
| `collision_free` | `false` | **Controller bug** | 查看 trace 冲突时刻 |
| `mapf_fail_calls` | `> 0` | **Core 集成 bug** | 检查 mapf_interface.py |
| `mapf_timeout_calls` | `== mapf_calls` | **配置/性能问题** | 检查 time_budget_ms |
| `completion_rate` | `0.0` | **逻辑问题** | 检查任务分配逻辑 |
| 指标正常 | 但验收失败 | **日志/口径 bug** | 检查 logger.py |

### 常见问题快速修复

#### ❌ collision_free = false

```bash
# 1. 获取冲突详情
python scripts/check_collisions.py --trace outputs/<run>/trace.jsonl

# 2. 查看冲突时刻（假设 t=15）
sed -n '13,17p' outputs/<run>/trace.jsonl

# 3. 检查决策步
grep '"decision_step": true' outputs/<run>/trace.jsonl | grep -B2 -A2 '"t": 15'
```

#### ⚠️ 所有 MAPF 调用都超时

```bash
# 1. 检查配置
grep "time_budget_ms" outputs/<run>/config_resolved.yaml

# 2. 查看实际运行时间
grep "mapf_plan_time_ms" outputs/<run>/trace.jsonl | head -5

# 3. 增加预算（修改配置文件）
# time_budget_ms: 50
```

#### ⚠️ completion_rate = 0

```bash
# 1. 查看任务分配
grep "chosen_task_id" outputs/<run>/trace.jsonl | grep -v "null"

# 2. 查看 UAV 状态
grep "uav_state" outputs/<run>/trace.jsonl | head -20
```

---

## 📚 详细文档

### DAY6_DEBUG_WORKFLOW.md（详细版）

**内容**：
- 快速使用指南
- 4 个材料详解（每个材料的作用、关键字段、检查点）
- 问题定位决策树（完整的诊断流程）
- 常见问题排查（Q&A 格式）
- 完整调试流程示例（从失败到修复）
- trace.jsonl 字段说明（所有字段含义）

**适用场景**：
- 第一次使用调试工具
- 需要深入理解调试流程
- 遇到复杂问题需要系统性排查

**阅读时间**：15-20 分钟

---

### DEBUG_QUICK_REFERENCE.md（速查版）

**内容**：
- 快速开始命令（3 种方式）
- 问题诊断速查表（5 种问题类型）
- 常见问题快速修复（3 个常见问题）
- trace 关键字段（10 个字段）
- 3 步调试流程（快速定位）

**适用场景**：
- 已经熟悉调试流程
- 需要快速查找命令
- 时间紧迫需要速查

**阅读时间**：2-3 分钟

---

## 🎯 推荐工作流程

### 场景 1：验收刚失败，不知道问题在哪

```bash
# Step 1: 快速诊断（30秒）
./scripts/quick_debug.sh outputs/<run>

# Step 2: 根据诊断建议，查看对应代码
# 例如：Controller bug → 查看 src/controller.py

# Step 3: 如果需要更多信息，生成完整报告
python scripts/generate_debug_report.py --run outputs/<run>
```

---

### 场景 2：需要回传材料给开发者

```bash
# 一键生成完整报告（包含所有 4 个材料）
python scripts/generate_debug_report.py --run outputs/<run> > debug_report.txt

# 发送 debug_report.txt 给开发者
```

---

### 场景 3：修复后验证

```bash
# 重新运行测试
python scripts/run_experiment.py --config configs/test.yaml

# 快速检查是否修复
./scripts/quick_debug.sh outputs/<new_run>

# 如果 collision_free=true，再详细验证
python scripts/check_collisions.py --trace outputs/<new_run>/trace.jsonl
```

---

## 💡 使用技巧

### 技巧 1：快速对比两次运行

```bash
# 运行 1（失败）
./scripts/quick_debug.sh outputs/run1 > report1.txt

# 运行 2（修复后）
./scripts/quick_debug.sh outputs/run2 > report2.txt

# 对比差异
diff report1.txt report2.txt
```

---

### 技巧 2：批量检查多个运行

```bash
# 检查所有运行
for run in outputs/*/; do
    echo "=== $run ==="
    ./scripts/quick_debug.sh "$run" | grep "💡 诊断建议:" -A 5
done
```

---

### 技巧 3：提取特定时刻的 trace

```bash
# 提取 t=10 到 t=20 的 trace
sed -n '10,20p' outputs/<run>/trace.jsonl | python -m json.tool
```

---

### 技巧 4：查找所有决策步

```bash
# 查找所有决策步的行号
grep -n '"decision_step": true' outputs/<run>/trace.jsonl

# 查看第一个决策步的详细信息
grep '"decision_step": true' outputs/<run>/trace.jsonl | head -1 | python -m json.tool
```

---

## 🔧 故障排除

### Q: quick_debug.sh 报错 "permission denied"

```bash
# 添加执行权限
chmod +x scripts/quick_debug.sh
```

---

### Q: generate_debug_report.py 找不到模块

```bash
# 确保在项目根目录运行
cd /path/to/ag_coop
python scripts/generate_debug_report.py --run outputs/<run>
```

---

### Q: trace.jsonl 太大，无法查看

```bash
# 只查看前 100 行
head -n 100 outputs/<run>/trace.jsonl

# 只查看决策步
grep '"decision_step": true' outputs/<run>/trace.jsonl

# 使用 generate_debug_report.py 自动截取关键部分
python scripts/generate_debug_report.py --run outputs/<run>
```

---

## 📊 工具对比

| 工具 | 速度 | 详细程度 | 适用场景 |
|------|------|----------|----------|
| quick_debug.sh | ⚡ 快（30秒） | ⭐ 简要 | 快速诊断 |
| generate_debug_report.py | 🐢 慢（1-2分钟） | ⭐⭐⭐ 详细 | 深入分析 |
| check_collisions.py | ⚡ 快（10秒） | ⭐ 单一 | 验证冲突 |

**推荐组合**：
1. 先用 `quick_debug.sh` 快速看问题
2. 如果需要详细分析，再用 `generate_debug_report.py`
3. 修复后用 `check_collisions.py` 快速验证

---

## 📁 文件结构

```
ag_coop/
├── scripts/
│   ├── quick_debug.sh              # 快速诊断脚本
│   ├── generate_debug_report.py    # 完整报告生成器
│   └── check_collisions.py         # 冲突检测脚本
├── docs/
│   ├── DAY6_DEBUG_WORKFLOW.md      # 详细调试流程
│   ├── DEBUG_QUICK_REFERENCE.md    # 速查卡
│   └── DEBUG_TOOLS_GUIDE.md        # 本文档
└── outputs/<run>/
    ├── config_resolved.yaml        # 完整配置
    ├── metrics.json                # 运行指标
    └── trace.jsonl                 # 执行轨迹
```

---

## 🎓 学习路径

### 新手（第一次使用）

1. 阅读本文档（10 分钟）
2. 运行 `quick_debug.sh` 体验（5 分钟）
3. 阅读 `DEBUG_QUICK_REFERENCE.md`（5 分钟）
4. 遇到问题时查阅 `DAY6_DEBUG_WORKFLOW.md`

### 熟练（已使用过几次）

1. 直接使用 `quick_debug.sh` 诊断
2. 需要时查阅 `DEBUG_QUICK_REFERENCE.md`
3. 复杂问题查阅 `DAY6_DEBUG_WORKFLOW.md`

### 专家（经常使用）

1. 直接使用命令行工具
2. 自定义脚本组合使用
3. 贡献改进建议

---

## 🤝 贡献

如果发现工具有改进空间，欢迎：
- 提出新的诊断规则
- 添加新的常见问题
- 改进输出格式
- 优化性能

---

## 📞 支持

遇到问题？
1. 查阅 `DAY6_DEBUG_WORKFLOW.md` 的常见问题部分
2. 查看 `DEBUG_QUICK_REFERENCE.md` 的快速修复
3. 联系开发团队

---

**版本**: v1.0
**最后更新**: 2024-02-08
**维护者**: AG_COOP Team
