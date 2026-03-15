# 审稿人意见应对方案 - 执行总结

## 📅 创建时间
2026-03-14

## 🎯 任务目标

应对审稿人提出的三个核心问题：
1. ❌ Baseline 太弱（全部是启发式规则）
2. ❌ 仿真环境过于理想化（2D 网格）
3. ❌ 缺乏规模扩展性测试

---

## ✅ 已完成的工作

### 1. 代码资源盘点

经过检查，您的项目已经具备以下资源：

#### 训练脚本（已存在）
- ✅ `scripts/train_vanilla_ppo.py` - Vanilla PPO baseline
- ✅ `scripts/train_dqn_baseline.py` - DQN baseline
- ✅ `scripts/train_upgraded_ppo.py` - PPO V4（您的改进版本）

#### 评估脚本（已存在）
- ✅ `scripts/evaluate_scalability.py` - 可扩展性测试（20/40/80 tasks）
- ✅ `scripts/evaluate_baselines.py` - Baseline 对比
- ✅ `scripts/evaluate_multi_maps.py` - 跨地图泛化

#### Baseline 策略（已实现）
- ✅ `StaticCenterPolicy` - 静态中心部署
- ✅ `TetheredGreedyPolicy` - 系留贪心
- ✅ `DynamicHeuristicPolicy` - 动态启发式
- ✅ `PureRandomPolicy` - 纯随机

### 2. 新增文档和工具

#### 文档
- ✅ `REVIEWER_RESPONSE_PLAN.md` - 详细的应对方案（14 页）
- ✅ `QUICK_START.md` - 快速开始指南

#### 新增脚本
- ✅ `scripts/plot_scalability_results.py` - 生成论文级图表
  - 对比柱状图（PDF）
  - 性能热力图（PDF）
  - 性能退化曲线（PDF）
  - LaTeX 表格

- ✅ `scripts/run_full_pipeline.py` - 一键式训练与评估流程
  - 自动训练 Vanilla PPO
  - 自动训练 DQN
  - 自动运行可扩展性测试
  - 自动生成图表
  - 生成执行日志

---

## 🚀 下一步行动

### 立即可执行的命令

#### 选项 A: 一键运行（推荐）
```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/run_full_pipeline.py --mode all
```

**预计耗时**: 6-8 小时
**输出**: 所有模型 + 测试结果 + 论文图表

#### 选项 B: 分步执行（更可控）

**步骤 1**: 训练 Vanilla PPO（2-3 小时）
```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/train_vanilla_ppo.py
```

**步骤 2**: 训练 DQN（2-3 小时）
```bash
python scripts/train_dqn_baseline.py
```

**步骤 3**: 运行可扩展性测试（2-3 小时）
```bash
python scripts/evaluate_scalability.py
```

**步骤 4**: 生成图表（< 1 分钟）
```bash
python scripts/plot_scalability_results.py
```

#### 选项 C: 仅评估（如果模型已训练）
```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/run_full_pipeline.py --mode eval_only
```

---

## 📊 预期输出

### 训练模型
- `outputs/vanilla_ppo_baseline_map02/best_model/best_model.zip`
- `outputs/dqn_baseline_map02/best_model/best_model.zip`

### 测试结果
- `outputs/scalability_tests/scalability_test_YYYYMMDD_HHMMSS.json`

### 论文图表
- `outputs/scalability_tests/plots/scalability_comparison.pdf`
- `outputs/scalability_tests/plots/scalability_heatmap.pdf`
- `outputs/scalability_tests/plots/performance_degradation.pdf`
- `outputs/scalability_tests/plots/scalability_table.tex`

---

## 📝 论文修改要点

### 1. 更新 Baseline 对比表格

在 Related Work 或 Experimental Setup 中，将现有的 4 个启发式 baseline 扩展为：

| Method | Type | Description |
|--------|------|-------------|
| Static-Center | Heuristic | UAV 固定在地图中心 |
| Tethered-Greedy | Heuristic | UAV 系留在 UGV 上 |
| Dynamic-Heuristic | Heuristic | 动态启发式调度 |
| Random-Walk | Heuristic | 随机游走策略 |
| **Vanilla PPO** | **Learning** | **标准 PPO（无改进）** |
| **DQN** | **Learning** | **Deep Q-Network** |
| **PPO V4 (Ours)** | **Learning** | **改进的 PPO** |

### 2. 新增实验章节

**标题**: "5.X Scalability Analysis"

**内容结构**:
1. 实验设置（低/中/高负载：20/40/80 tasks）
2. 结果对比表格（插入生成的 LaTeX 表格）
3. 性能曲线图（插入生成的 PDF 图表）
4. 分析讨论

### 3. 更新 Ablation Study

新增对比：
- **PPO V4 vs Vanilla PPO**: 证明您的改进（动态熵衰减、扩展网络、进取型奖励）的有效性
- **PPO V4 vs DQN**: 证明 Actor-Critic 架构在当前动作空间下的优越性

### 4. 添加 2D 环境辩护段落

**建议位置**: Experimental Setup 或 Simulation Environment

**内容**:
```
While our simulation uses a 2D grid environment, this design choice is
justified by our research focus on task allocation and communication
scheduling rather than low-level flight control. The 2D abstraction
allows us to efficiently explore the combinatorial optimization space
of multi-agent coordination while maintaining computational tractability
for extensive ablation studies. This approach is consistent with prior
work in multi-agent path finding (MAPF) and task allocation [citations].
Future work will extend our approach to 3D continuous environments with
realistic flight dynamics.
```

---

## 📧 审稿人回复模板

### 意见 1: "Baselines are too weak, all heuristic-based"

**回复**:
> We thank the reviewer for this valuable feedback. In the revised
> manuscript, we have added two learning-based baselines: (1) Vanilla
> PPO without our proposed improvements, and (2) DQN as a representative
> value-based method. Our experimental results (Table X, Figure Y) show
> that PPO V4 outperforms both learning-based baselines by significant
> margins, validating the effectiveness of our proposed improvements.
> Specifically, compared to Vanilla PPO, our method achieves X% higher
> task completion rate and Y% higher total reward. Compared to DQN,
> our Actor-Critic approach demonstrates Z% better performance,
> validating the superiority of policy gradient methods for this
> high-dimensional action space.

### 意见 2: "2D grid is too idealized"

**回复**:
> We acknowledge the reviewer's concern. Our 2D grid environment is
> designed to focus on the combinatorial optimization aspects of
> multi-agent task allocation and communication scheduling, which is
> the core contribution of this work. This abstraction is consistent
> with prior work in MAPF and multi-agent coordination [citations].
> We have added a discussion of this limitation in Section X and
> outlined plans for 3D continuous environment extension in future work.
> The 2D abstraction allows us to efficiently explore the optimization
> space while maintaining computational tractability for extensive
> ablation studies.

### 意见 3: "Missing scalability tests"

**回复**:
> We have added comprehensive scalability experiments (Section X)
> evaluating our approach under varying task loads (20, 40, 80 tasks).
> Results demonstrate that PPO V4 maintains robust performance across
> all load conditions, with particularly strong advantages under high
> load scenarios (Table X, Figure Y). Specifically, under high load
> (80 tasks), PPO V4 maintains X% of its low-load performance while
> Vanilla PPO degrades by Y%, demonstrating superior scalability and
> robustness.

---

## 🔍 关键文件位置

### 文档
- 详细方案: `REVIEWER_RESPONSE_PLAN.md`
- 快速指南: `QUICK_START.md`
- 本总结: `SUMMARY.md`

### 训练脚本
- Vanilla PPO: `scripts/train_vanilla_ppo.py`
- DQN: `scripts/train_dqn_baseline.py`
- PPO V4: `scripts/train_upgraded_ppo.py`

### 评估脚本
- 可扩展性测试: `scripts/evaluate_scalability.py`
- 绘图工具: `scripts/plot_scalability_results.py`
- 完整流程: `scripts/run_full_pipeline.py`

### 配置文件
- 训练配置: `configs/curriculum_learning.yaml`

---

## ⚠️ 注意事项

### 训练前检查
- [ ] GPU 可用: `nvidia-smi`
- [ ] 环境激活: 确认 Python 环境正确
- [ ] 磁盘空间: 至少 10GB 可用空间

### 训练中监控
- [ ] TensorBoard: `tensorboard --logdir outputs/*/tb_logs`
- [ ] GPU 利用率: 应在 80-95%
- [ ] 内存使用: 不应超过 90%

### 训练后验证
- [ ] 模型文件存在
- [ ] 快速评估确认模型可用
- [ ] 备份训练好的模型

---

## 📈 预期性能指标

### Vanilla PPO
- 收敛奖励: 15 ~ 25
- 任务完成: 35 ~ 42
- 训练时间: 2-3 小时

### DQN
- 收敛奖励: 10 ~ 20
- 任务完成: 30 ~ 38
- 训练时间: 2-3 小时

### PPO V4（您的模型）
- 收敛奖励: 30 ~ 40
- 任务完成: 45 ~ 52
- 应该显著优于 Vanilla PPO 和 DQN

### 可扩展性测试
- 低负载（20 tasks）: 所有方法性能接近
- 中负载（40 tasks）: PPO V4 开始领先
- 高负载（80 tasks）: PPO V4 优势明显

---

## ✅ 完成检查清单

### 实验执行
- [ ] Vanilla PPO 训练完成
- [ ] DQN 训练完成
- [ ] 可扩展性测试完成
- [ ] 所有图表生成完成
- [ ] 结果已备份

### 论文修改
- [ ] Baseline 对比表格更新
- [ ] 可扩展性实验章节新增
- [ ] Ablation Study 更新
- [ ] 2D 环境辩护段落添加
- [ ] 所有图表插入论文

### 审稿回复
- [ ] 回复信撰写完成
- [ ] 所有修改点标注清楚
- [ ] 补充材料准备完成

---

## 🎓 学术贡献总结

完成上述工作后，您的论文将具备以下优势：

1. **更强的 Baseline 对比**
   - 不仅与启发式方法对比
   - 还与学习类方法（Vanilla PPO、DQN）对比
   - 证明您的改进是有效的

2. **全面的可扩展性验证**
   - 低/中/高负载下的性能对比
   - 证明算法的鲁棒性和实用性

3. **清晰的消融实验**
   - PPO V4 vs Vanilla PPO → 证明改进有效
   - PPO vs DQN → 证明架构选择合理

4. **合理的环境辩护**
   - 明确研究聚焦点（调度而非控制）
   - 引用相关工作支持
   - 承认局限性并提出未来方向

---

## 🆘 需要帮助？

如果遇到问题，请检查：
1. 错误信息和日志
2. GPU 状态（`nvidia-smi`）
3. 磁盘空间（`df -h`）
4. Python 环境（`which python`, `pip list`）

---

## 🎉 结语

您的项目已经具备了应对审稿人意见的所有必要工具和脚本。现在只需要：

1. **运行实验**（6-8 小时）
2. **修改论文**（1-2 天）
3. **撰写回复信**（半天）

**祝您顺利通过审稿！**

---

**文档版本**: v1.0
**创建日期**: 2026-03-14
**作者**: Claude Opus 4.6
