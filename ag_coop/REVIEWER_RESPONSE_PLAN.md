# 审稿人意见应对方案 (Reviewer Response Plan)

## 📋 核心问题总结

根据您提供的审稿人反馈，当前研究存在三个主要弱点：

### 1. ❌ Baseline 太弱 - 全部是启发式规则
**问题**: 四个 Baseline（Static-Center, Tethered-Greedy, Dynamic-Heur., Random-Walk）全部是传统规则策略，缺乏学习类算法对比。

**审稿人视角**: "既然用深度强化学习（PPO），为什么不和其他学习类算法（DQN、MADDPG，或基础版 PPO）对比？"

### 2. ❌ 仿真环境过于理想化 - 2D 网格
**问题**: 2D 网格 + 离散 16 方向动作空间，缺乏三维连续动力学。

**审稿人视角**: "2D Grid 训练的策略能否应对真实三维空间的连续动力学限制？"

### 3. ❌ 缺乏规模扩展性测试
**问题**: 只验证了跨地图鲁棒性，未验证任务负载和智能体数量变化时的稳定性。

---

## ✅ 现有资源盘点

### 已实现的训练脚本
- ✅ `train_vanilla_ppo.py` - Vanilla PPO baseline（无改进）
- ✅ `train_dqn_baseline.py` - DQN baseline（值函数方法）
- ✅ `train_upgraded_ppo.py` - PPO V4（您的改进版本）

### 已实现的评估脚本
- ✅ `evaluate_scalability.py` - 可扩展性测试（20/40/80 tasks）
- ✅ `evaluate_baselines.py` - Baseline 对比评估
- ✅ `evaluate_multi_maps.py` - 跨地图泛化测试

### 已实现的 Baseline 策略
- ✅ `StaticCenterPolicy` - 静态中心部署
- ✅ `TetheredGreedyPolicy` - 系留贪心策略
- ✅ `DynamicHeuristicPolicy` - 动态启发式策略
- ✅ `PureRandomPolicy` - 纯随机策略

---

## 🎯 改进方案（针对审稿人意见）

### 方案 1: 增加学习类 Baseline ✅ (已完成)

#### 1.1 Vanilla PPO Baseline
**目的**: 证明您的 V4 改进（动态熵衰减、多模态网络、进取型奖励）的有效性

**实现状态**: ✅ 已完成
- 文件: `train_vanilla_ppo.py`
- 特征:
  - 固定熵系数: 0.01（无动态调整）
  - 标准学习率: 0.0003 → 0（无保底机制）
  - 标准网络: [64, 64]（无扩展容量）
  - 标准奖励函数（无进取型调整）

**训练命令**:
```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/train_vanilla_ppo.py
```

**预期训练时间**: 2-3 小时（1.2M steps, 8 envs）

#### 1.2 DQN Baseline
**目的**: 证明在当前动作空间下 Actor-Critic 架构的优越性

**实现状态**: ✅ 已完成
- 文件: `train_dqn_baseline.py`
- 特征:
  - 算法: Deep Q-Network（值函数方法）
  - 探索策略: Epsilon-greedy (1.0 → 0.05)
  - 经验回放: 100k buffer
  - 目标网络: 每 10k 步更新

**训练命令**:
```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/train_dqn_baseline.py
```

**预期训练时间**: 2-3 小时（1.2M steps, 8 envs）

---

### 方案 2: 系统负载可扩展性测试 ✅ (已完成)

**目的**: 证明算法在不同任务负载下的稳定性和可扩展性

**实现状态**: ✅ 已完成
- 文件: `evaluate_scalability.py`
- 测试维度:
  1. **低负载** (20 tasks): 验证基础性能
  2. **中负载** (40 tasks): 标准工况
  3. **高负载** (80 tasks): 极限压力测试

**对比对象**:
- PPO V4（您的改进模型）
- Vanilla PPO
- DQN
- Dynamic-Heuristic（最强 baseline）

**评估命令**:
```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/evaluate_scalability.py
```

**输出**: JSON 格式结果 + 对比表格

---

### 方案 3: 2D 环境的学术辩护

**策略**: 在论文中增加一节 "Simulation Environment Justification"

**论证要点**:

1. **研究聚焦于调度决策，非飞行控制**
   - 本研究的核心贡献是 **任务分配与通信调度**，而非无人机飞行控制
   - 2D 网格足以验证调度策略的有效性

2. **计算效率与可重复性**
   - 2D 环境允许快速迭代和大规模实验
   - 便于其他研究者复现结果

3. **现有文献支持**
   - 引用其他使用 2D 环境进行调度研究的顶会论文
   - 例如: ICRA/IROS 中的 MAPF 研究大多使用 2D 网格

4. **未来工作方向**
   - 在 Discussion 中承认这是局限性
   - 提出未来将扩展到 3D 连续空间（如 Gazebo/AirSim）

**建议添加的段落**:
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

## 📊 实验执行计划

### 阶段 1: 训练学习类 Baseline（预计 6-8 小时）

#### 任务 1.1: 训练 Vanilla PPO
```bash
# 终端 1
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/train_vanilla_ppo.py

# 监控训练（终端 2）
tensorboard --logdir outputs/vanilla_ppo_baseline_map02/tb_logs
```

**检查点**:
- [ ] 训练完成（1.2M steps）
- [ ] 模型保存在 `outputs/vanilla_ppo_baseline_map02/best_model/`
- [ ] TensorBoard 曲线正常

#### 任务 1.2: 训练 DQN
```bash
# 终端 1
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/train_dqn_baseline.py

# 监控训练（终端 2）
tensorboard --logdir outputs/dqn_baseline_map02/tb_logs
```

**检查点**:
- [ ] 训练完成（1.2M steps）
- [ ] 模型保存在 `outputs/dqn_baseline_map02/best_model/`
- [ ] TensorBoard 曲线正常

---

### 阶段 2: 可扩展性评估（预计 2-3 小时）

#### 任务 2.1: 运行可扩展性测试
```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop
python scripts/evaluate_scalability.py
```

**输出文件**:
- `outputs/scalability_tests/scalability_test_YYYYMMDD_HHMMSS.json`

**预期结果**:
- PPO V4 在所有负载下优于 Vanilla PPO 和 DQN
- 高负载下性能差距更明显（证明改进的有效性）

#### 任务 2.2: 生成对比图表
使用 Python 脚本生成论文级图表：
```python
# 将在下一步提供绘图脚本
python scripts/plot_scalability_results.py
```

---

### 阶段 3: 论文修改（预计 1-2 天）

#### 修改 1: 更新 Baseline 对比表格
**位置**: Related Work / Experimental Setup

**新增内容**:
| Method | Type | Description |
|--------|------|-------------|
| Static-Center | Heuristic | UAV 固定在地图中心 |
| Tethered-Greedy | Heuristic | UAV 系留在 UGV 上 |
| Dynamic-Heuristic | Heuristic | 动态启发式调度 |
| Random-Walk | Heuristic | 随机游走策略 |
| **Vanilla PPO** | **Learning** | **标准 PPO（无改进）** |
| **DQN** | **Learning** | **Deep Q-Network** |
| **PPO V4 (Ours)** | **Learning** | **改进的 PPO** |

#### 修改 2: 新增可扩展性实验章节
**位置**: Experiments

**新增小节**: "5.X Scalability Analysis"

**内容结构**:
1. 实验设置（低/中/高负载）
2. 结果对比表格
3. 性能曲线图
4. 分析讨论

#### 修改 3: 更新 Ablation Study
**位置**: Experiments

**新增对比**:
- PPO V4 vs Vanilla PPO（证明改进有效）
- PPO V4 vs DQN（证明 Actor-Critic 优越性）

---

## 🔧 快速启动指南

### 如果您现在就要开始训练：

#### 选项 A: 串行训练（安全但慢）
```bash
# 1. 训练 Vanilla PPO（2-3 小时）
python scripts/train_vanilla_ppo.py

# 2. 训练 DQN（2-3 小时）
python scripts/train_dqn_baseline.py

# 3. 运行可扩展性测试（2-3 小时）
python scripts/evaluate_scalability.py
```

#### 选项 B: 并行训练（快但占用资源）
```bash
# 终端 1: Vanilla PPO
CUDA_VISIBLE_DEVICES=0 python scripts/train_vanilla_ppo.py

# 终端 2: DQN
CUDA_VISIBLE_DEVICES=0 python scripts/train_dqn_baseline.py
```

**注意**: 您的 RTX 4060 可以同时运行两个训练任务，但会稍慢。

---

## 📈 预期成果

### 论文中可以新增的 Claims:

1. **学习类 Baseline 对比**:
   > "Our PPO V4 outperforms vanilla PPO by X% in task completion rate
   > and Y% in total reward, demonstrating the effectiveness of our
   > proposed improvements (dynamic entropy decay, expanded network
   > capacity, and progressive reward shaping)."

2. **算法架构优越性**:
   > "Compared to value-based methods (DQN), our actor-critic approach
   > (PPO V4) achieves Z% higher performance, validating the superiority
   > of policy gradient methods for this high-dimensional action space."

3. **可扩展性验证**:
   > "Under high task load (80 tasks), PPO V4 maintains W% of its
   > performance while vanilla PPO degrades by V%, demonstrating
   > superior scalability and robustness."

---

## ⚠️ 注意事项

### 训练前检查：
- [ ] 确认 GPU 可用: `nvidia-smi`
- [ ] 确认环境激活: `conda activate agcoop` (或您的环境名)
- [ ] 确认磁盘空间: 每个模型约 500MB，检查点约 2GB

### 训练中监控：
- [ ] 定期查看 TensorBoard
- [ ] 检查 GPU 利用率（应在 80-95%）
- [ ] 检查内存使用（不应超过 90%）

### 训练后验证：
- [ ] 检查模型文件是否存在
- [ ] 运行快速评估确认模型可用
- [ ] 备份训练好的模型

---

## 📞 需要帮助？

如果遇到问题，请提供：
1. 错误信息截图
2. 训练日志最后 50 行
3. `nvidia-smi` 输出
4. 当前执行的命令

---

## 🎓 学术写作建议

### 如何回应审稿人：

**审稿人意见 1**: "Baselines are too weak, all heuristic-based."

**回应模板**:
> We thank the reviewer for this valuable feedback. In the revised
> manuscript, we have added two learning-based baselines: (1) Vanilla
> PPO without our proposed improvements, and (2) DQN as a representative
> value-based method. Our experimental results (Table X, Figure Y) show
> that PPO V4 outperforms both learning-based baselines by significant
> margins, validating the effectiveness of our proposed improvements.

**审稿人意见 2**: "2D grid is too idealized."

**回应模板**:
> We acknowledge the reviewer's concern. Our 2D grid environment is
> designed to focus on the combinatorial optimization aspects of
> multi-agent task allocation and communication scheduling, which is
> the core contribution of this work. This abstraction is consistent
> with prior work in MAPF and multi-agent coordination [citations].
> We have added a discussion of this limitation in Section X and
> outlined plans for 3D continuous environment extension in future work.

**审稿人意见 3**: "Missing scalability tests."

**回应模板**:
> We have added comprehensive scalability experiments (Section X)
> evaluating our approach under varying task loads (20, 40, 80 tasks).
> Results demonstrate that PPO V4 maintains robust performance across
> all load conditions, with particularly strong advantages under high
> load scenarios (Table X, Figure Y).

---

## ✅ 完成检查清单

### 实验部分：
- [ ] Vanilla PPO 训练完成
- [ ] DQN 训练完成
- [ ] 可扩展性测试完成
- [ ] 结果图表生成完成

### 论文修改：
- [ ] Baseline 对比表格更新
- [ ] 可扩展性实验章节新增
- [ ] Ablation Study 更新
- [ ] 2D 环境辩护段落添加
- [ ] 审稿人回复信撰写

### 最终检查：
- [ ] 所有实验数据已备份
- [ ] 论文修改已完成
- [ ] 审稿人回复信已撰写
- [ ] 补充材料已准备

---

**祝您顺利通过审稿！如有任何问题，随时联系。**
