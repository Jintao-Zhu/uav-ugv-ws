# 调试脚本使用说明

本目录包含 Day 6 调试工具包的所有脚本。

## 📦 脚本清单

### 1. quick_debug.sh ⭐ 推荐首选
**功能**：快速诊断（30秒内看到问题）

**用法**：
```bash
./scripts/quick_debug.sh outputs/<run>
```

**输出**：
- 文件检查（config/metrics/trace 是否存在）
- 关键配置（n_ugv, H, budget, seed）
- 关键指标（collision_free, mapf_calls, completion_rate）
- 冲突检测结果
- 自动诊断建议

**适用场景**：验收刚失败，需要快速判断问题类型

---

### 2. generate_debug_report.py
**功能**：生成完整调试报告（包含所有 4 个材料）

**用法**：
```bash
# 自动定位决策步附近
python scripts/generate_debug_report.py --run outputs/<run>

# 指定出错行号
python scripts/generate_debug_report.py --run outputs/<run> --error-line 25
```

**输出**：
1. config_resolved.yaml 完整内容 + 关键参数摘要
2. metrics.json 完整内容 + 关键指标摘要
3. trace.jsonl 智能截取（决策步附近或指定行附近）
4. check_collisions.py 自动运行结果
5. 基于指标的自动诊断建议

**适用场景**：需要回传完整材料给开发者，或需要深入分析

---

### 3. check_collisions.py
**功能**：离线验证 trace 中是否有碰撞

**用法**：
```bash
python scripts/check_collisions.py --trace outputs/<run>/trace.jsonl
```

**检测类型**：
- Vertex collision（两个 agent 同时占据同一位置）
- Edge collision（两个 agent 交换位置）

**返回值**：
- Exit code 0：无冲突
- Exit code 1：检测到冲突

**适用场景**：仅需验证是否有碰撞，或修复后快速验证

---

## 🚀 快速开始

### 场景 1：验收失败，不知道问题在哪

```bash
# Step 1: 快速诊断
./scripts/quick_debug.sh outputs/<run>

# Step 2: 根据诊断建议查看对应代码
# 例如：Controller bug → 查看 src/controller.py

# Step 3: 如果需要更多信息
python scripts/generate_debug_report.py --run outputs/<run>
```

---

### 场景 2：需要回传材料

```bash
# 一键生成完整报告
python scripts/generate_debug_report.py --run outputs/<run> > debug_report.txt

# 发送 debug_report.txt
```

---

### 场景 3：修复后验证

```bash
# 快速检查
./scripts/quick_debug.sh outputs/<new_run>

# 详细验证
python scripts/check_collisions.py --trace outputs/<new_run>/trace.jsonl
```

---

## 🔍 问题诊断速查

| 指标 | 异常值 | 问题类型 |
|------|--------|----------|
| `collision_free` | `false` | **Controller bug** |
| `mapf_fail_calls` | `> 0` | **Core 集成 bug** |
| `mapf_timeout_calls` | `== mapf_calls` | **配置/性能问题** |
| `completion_rate` | `0.0` | **逻辑问题** |
| 指标正常 | 但验收失败 | **日志/口径 bug** |

---

## 📚 详细文档

- **详细调试流程**：`docs/DAY6_DEBUG_WORKFLOW.md`（5000+ 字）
- **速查卡**：`docs/DEBUG_QUICK_REFERENCE.md`（1 页纸）
- **使用指南**：`docs/DEBUG_TOOLS_GUIDE.md`（4000+ 字）
- **完成总结**：`docs/DAY6_STEP6_SUMMARY.md`

---

## 💡 使用技巧

### 批量检查多个运行
```bash
for run in outputs/*/; do
    echo "=== $run ==="
    ./scripts/quick_debug.sh "$run" | grep "💡 诊断建议:" -A 5
done
```

### 对比两次运行
```bash
./scripts/quick_debug.sh outputs/run1 > report1.txt
./scripts/quick_debug.sh outputs/run2 > report2.txt
diff report1.txt report2.txt
```

### 查找所有决策步
```bash
grep -n '"decision_step": true' outputs/<run>/trace.jsonl
```

---

## 🔧 故障排除

### Q: quick_debug.sh 报错 "permission denied"
```bash
chmod +x scripts/quick_debug.sh
```

### Q: 找不到 Python 模块
```bash
# 确保在项目根目录运行
cd /path/to/ag_coop
python scripts/generate_debug_report.py --run outputs/<run>
```

---

## 📞 支持

遇到问题？查阅：
1. `docs/DAY6_DEBUG_WORKFLOW.md` 的常见问题部分
2. `docs/DEBUG_QUICK_REFERENCE.md` 的快速修复
3. 联系开发团队

---

**版本**: v1.0
**最后更新**: 2024-02-08
**维护者**: AG_COOP Team
