# 快速开始指南 - 应对审稿人意见

## 🎯 目标

完成以下三个关键改进以应对审稿人意见：
1. ✅ 增加学习类 Baseline（Vanilla PPO + DQN）
2. ✅ 运行可扩展性测试（20/40/80 tasks）
3. ✅ 生成论文级图表和表格

---

## ⚡ 最快方式：一键运行

```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop

# 运行完整流程（训练 + 评估 + 绘图）
python scripts/run_full_pipeline.py --mode all
```

**预计总耗时**: 6-8 小时（取决于您的 RTX 4060）

**输出**:
- ✅ Vanilla PPO 模型
- ✅ DQN 模型
- ✅ 可扩展性测试结果（JSON）
- ✅ 论文级图表（PDF）
- ✅ LaTeX 表格

---

## 📋 分步执行（推荐）

如果您想更好地控制流程，可以分步执行：

### 步骤 1: 训练 Vanilla PPO（2-3 小时）

```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/train_vanilla_ppo.py
```

**监控训练**（打开新终端）:
```bash
tensorboard --logdir outputs/vanilla_ppo_baseline_map02/tb_logs
```

然后在浏览器打开: http://localhost:6006

**检查点**:
- [ ] 训练完成（1.2M steps）
- [ ] 模型保存在 `outputs/vanilla_ppo_baseline_map02/best_model/`
- [ ] TensorBoard 显示学习曲线

---

### 步骤 2: 训练 DQN（2-3 小时）

```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/train_dqn_baseline.py
```

**监控训练**（打开新终端）:
```bash
tensorboard --logdir outputs/dqn_baseline_map02/tb_logs
```

**检查点**:
- [ ] 训练完成（1.2M steps）
- [ ] 模型保存在 `outputs/dqn_baseline_map02/best_model/`
- [ ] TensorBoard 显示学习曲线

---

### 步骤 3: 运行可扩展性测试（2-3 小时）

```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/evaluate_scalability.py
```

**输出**:
- `outputs/scalability_tests/scalability_test_YYYYMMDD_HHMMSS.json`

**检查点**:
- [ ] 测试完成（3 种负载 × 4 种策略 × 10 episodes）
- [ ] JSON 文件包含所有结果
- [ ] 控制台显示对比表格

---

### 步骤 4: 生成论文图表（< 1 分钟）

```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/plot_scalability_results.py
```

**输出**:
- `outputs/scalability_tests/plots/scalability_comparison.pdf`
- `outputs/scalability_tests/plots/scalability_heatmap.pdf`
- `outputs/scalability_tests/plots/performance_degradation.pdf`
- `outputs/scalability_tests/plots/scalability_table.tex`

**检查点**:
- [ ] 4 个文件生成成功
- [ ] PDF 图表清晰可读
- [ ] LaTeX 表格格式正确

---

## 🔧 高级选项

### 并行训练（节省时间）

如果您的 GPU 内存足够（RTX 4060 8GB 应该可以），可以同时训练两个模型：

```bash
# 终端 1: Vanilla PPO
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/train_vanilla_ppo.py

# 终端 2: DQN（同时运行）
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/train_dqn_baseline.py
```

**注意**: 并行训练会让每个任务稍慢，但总时间会减少。

---

### 仅运行评估（如果模型已训练）

```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/run_full_pipeline.py --mode eval_only
```

---

### 强制重新训练

```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/run_full_pipeline.py --mode all --force-train
```

---

## 📊 预期结果

### 训练曲线

**Vanilla PPO**:
- 初期奖励: -50 ~ -20
- 收敛奖励: 15 ~ 25
- 任务完成: 35 ~ 42

**DQN**:
- 初期奖励: -80 ~ -40
- 收敛奖励: 10 ~ 20
- 任务完成: 30 ~ 38

**PPO V4（您的模型）**:
- 初期奖励: -30 ~ -10
- 收敛奖励: 30 ~ 40
- 任务完成: 45 ~ 52

### 可扩展性测试

**预期性能排序**:
1. PPO V4（最好）
2. Vanilla PPO
3. Dynamic-Heuristic
4. DQN

**预期趋势**:
- 低负载（20 tasks）: 所有方法性能接近
- 中负载（40 tasks）: PPO V4 开始领先
- 高负载（80 tasks）: PPO V4 优势明显

---

## ⚠️ 常见问题

### Q1: 训练时 GPU 利用率低（< 50%）

**原因**: 环境模拟成为瓶颈

**解决**:
- 这是正常的，RL 训练通常 CPU 密集
- 可以增加并行环境数（修改 `N_ENVS`）

### Q2: 训练中断了怎么办？

**解决**:
- 模型会自动保存为 `interrupted_model.zip`
- 可以从检查点恢复（每 50k 步保存一次）

### Q3: 评估时提示模型不存在

**解决**:
```bash
# 检查模型文件
ls -lh outputs/vanilla_ppo_baseline_map02/best_model/
ls -lh outputs/dqn_baseline_map02/best_model/
ls -lh outputs/upgraded_ppo_map02/best_model/
```

如果缺失，需要先训练对应模型。

### Q4: 绘图时报错 "No module named matplotlib"

**解决**:
```bash
pip install matplotlib seaborn
```

---

## 📝 论文修改清单

完成实验后，您需要修改论文的以下部分：

### 1. Baseline 对比表格（Related Work / Experimental Setup）

在现有 4 个启发式 baseline 基础上，添加：
- ✅ Vanilla PPO（学习类）
- ✅ DQN（学习类）

### 2. 新增实验章节（Experiments）

**标题**: "5.X Scalability Analysis"

**内容**:
- 实验设置（低/中/高负载）
- 结果对比表格（使用生成的 LaTeX 表格）
- 性能曲线图（使用生成的 PDF 图表）
- 分析讨论

### 3. 更新 Ablation Study

**新增对比**:
- PPO V4 vs Vanilla PPO → 证明改进有效
- PPO V4 vs DQN → 证明 Actor-Critic 优越性

### 4. 添加环境辩护段落（Simulation Environment）

**建议位置**: Experimental Setup

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

### 回应意见 1: "Baselines are too weak"

> We thank the reviewer for this valuable feedback. In the revised
> manuscript, we have added two learning-based baselines: (1) Vanilla
> PPO without our proposed improvements, and (2) DQN as a representative
> value-based method. Our experimental results (Table X, Figure Y) show
> that PPO V4 outperforms both learning-based baselines by significant
> margins (X% improvement in task completion, Y% improvement in reward),
> validating the effectiveness of our proposed improvements.

### 回应意见 2: "2D grid is too idealized"

> We acknowledge the reviewer's concern. Our 2D grid environment is
> designed to focus on the combinatorial optimization aspects of
> multi-agent task allocation and communication scheduling, which is
> the core contribution of this work. This abstraction is consistent
> with prior work in MAPF and multi-agent coordination [citations].
> We have added a discussion of this limitation in Section X and
> outlined plans for 3D continuous environment extension in future work.

### 回应意见 3: "Missing scalability tests"

> We have added comprehensive scalability experiments (Section X)
> evaluating our approach under varying task loads (20, 40, 80 tasks).
> Results demonstrate that PPO V4 maintains robust performance across
> all load conditions, with particularly strong advantages under high
> load scenarios (Table X, Figure Y). Specifically, under high load
> (80 tasks), PPO V4 maintains X% of its low-load performance while
> Vanilla PPO degrades by Y%, demonstrating superior scalability.

---

## ✅ 最终检查清单

### 实验部分
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

## 🆘 需要帮助？

如果遇到问题，请提供：
1. 错误信息截图
2. 训练日志最后 50 行
3. `nvidia-smi` 输出
4. 当前执行的命令

---

**祝您顺利通过审稿！** 🎉
