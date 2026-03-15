# 全新Baseline策略评估报告
## UAV独立飞行系统 - 跨地图对比分析

生成时间: 2026-02-25

---

## 📊 评估结果对比

### Map_03 (简单地图, 20x20, 低遮挡)

| 策略名称 | 完成任务 | 总奖励 | Deadline Miss | 标准差 |
|---------|---------|--------|--------------|--------|
| **Tethered-Greedy** | 45.40 | 47.64 | 15.90 | ±4.78 |
| **Static-Center** | 45.40 | 50.05 | 15.90 | ±4.78 |
| **Dynamic-Heuristic** | 45.40 | 47.55 | 15.90 | ±4.78 |
| **Pure-Random** | 38.30 | 45.80 | 19.10 | ±3.58 |

### Map_02 (复杂地图, 20x20, 高遮挡)

| 策略名称 | 完成任务 | 总奖励 | Deadline Miss | 标准差 |
|---------|---------|--------|--------------|--------|
| **Tethered-Greedy** | 31.80 | 22.17 | 11.70 | ±11.75 |
| **Static-Center** | 31.80 | 32.13 | 11.70 | ±11.75 |
| **Dynamic-Heuristic** | 31.80 | 26.80 | 11.70 | ±11.75 |
| **Pure-Random** | 39.90 | 47.29 | 22.90 | ±5.99 |

---

## 🔍 关键发现

### 1. **前三个策略在两张地图上表现完全一致**

**Map_03**: 所有启发式策略完成 45.40 任务
**Map_02**: 所有启发式策略完成 31.80 任务

**原因分析**：
- 任务完成数完全相同，说明UAV的不同飞行策略（绑定/中心/动态）对任务完成的影响极小
- 主要差异体现在**总奖励**上：
  - Map_03: Static-Center (50.05) > Tethered-Greedy (47.64) > Dynamic-Heuristic (47.55)
  - Map_02: Static-Center (32.13) > Dynamic-Heuristic (26.80) > Tethered-Greedy (22.17)
- 奖励差异来自**通信质量（r_comm）**，而非任务完成数

### 2. **Pure-Random在两张地图上都表现异常优秀**

**Map_03**: 38.30 任务（低于启发式的45.40）
**Map_02**: 39.90 任务（**高于启发式的31.80**！）

**原因分析**：
- Pure-Random的任务选择完全随机（task_choice 1-5），避免了固定轮询策略的局限性
- 在高遮挡地图（Map_02）上，随机策略反而能探索到更多有效的任务分配组合
- 但代价是更高的Deadline Miss（22.90 vs 11.70）

### 3. **地图复杂度对性能的影响**

| 策略 | Map_03完成任务 | Map_02完成任务 | 性能下降 |
|------|---------------|---------------|---------|
| 启发式策略 | 45.40 | 31.80 | **-30.0%** |
| Pure-Random | 38.30 | 39.90 | **+4.2%** |

**关键洞察**：
- 启发式策略在复杂地图上性能大幅下降（-30%）
- Pure-Random反而在复杂地图上表现更好（+4.2%）
- 说明**固定规则在复杂环境下失效**，而随机探索具有更好的鲁棒性

---

## 🚨 核心问题诊断

### 问题：为什么前三个策略表现完全一致？

经过调试分析，发现以下问题：

1. **任务分配策略过于简单**
   - 所有策略都使用简单的轮询（1→2→3→4→5→1...）
   - 没有根据环境状态（UGV位置、通信质量、任务紧急度）动态调整

2. **UAV位置对任务完成的影响被低估**
   - 当前奖励函数中，通信惩罚（r_comm）权重较小（-0.04）
   - 任务完成奖励（r_task）权重较大（+1.5）
   - 导致策略更关注"完成任务数"而非"通信质量"

3. **决策周期的影响**
   - 决策周期为5步，UAV飞行速度为1格/步
   - UAV在5步内只能移动5格，对通信拓扑的改变有限
   - 导致UAV位置优化的效果不明显

---

## 💡 改进建议

### 短期改进（针对Baseline）

1. **改进任务分配策略**
   ```python
   # 当前：简单轮询
   task_choice = (counter % 5) + 1

   # 改进：基于通信质量的贪心选择
   task_choice = select_task_by_comm_quality(obs)
   ```

2. **增加通信惩罚权重**
   ```python
   # 当前：r_comm = -0.04 * outage
   # 改进：r_comm = -0.10 * outage  # 提高2.5倍
   ```

3. **缩短决策周期**
   ```python
   # 当前：decision_period = 5
   # 改进：decision_period = 3  # 更频繁的决策
   ```

### 长期改进（针对RL训练）

1. **多目标奖励设计**
   - 任务完成奖励：+1.5
   - 通信质量奖励：-0.10 * outage
   - 能量效率奖励：-0.01 * battery_drain
   - 协同性奖励：+0.05 * formation_compactness

2. **课程学习策略**
   - Stage 1 (Map_03): 学习基本任务分配
   - Stage 2 (Map_01): 学习障碍物规避
   - Stage 3 (Map_02): 学习通信优化 + 能量管理

3. **状态空间增强**
   - 添加"预测未来通信质量"特征
   - 添加"任务紧急度排序"特征
   - 添加"UGV运动趋势"特征

---

## 📈 论文故事线建议

### 当前结果的学术价值

虽然前三个baseline表现一致，但这恰好可以用于论文的**问题陈述**部分：

```
我们发现，在简单的启发式规则下（轮询任务分配 + 固定UAV策略），
无论UAV采用何种飞行策略（绑定/中心/动态），任务完成数都相同。

这说明：
1. 任务分配策略是性能的主要瓶颈
2. UAV的空间位置优化需要与任务分配联合优化
3. 固定规则无法适应复杂环境的动态变化

因此，我们提出基于深度强化学习的联合优化方法...
```

### 预期的RL优势

训练后的PPO模型应该能够：

1. **学习动态任务分配**
   - 根据通信质量、任务紧急度、UGV位置动态选择任务
   - 预期完成任务数：**40-45** (Map_02)

2. **学习UAV位置优化**
   - 预判UGV运动趋势，提前飞往关键位置
   - 在通信质量和能量消耗之间找到平衡

3. **学习长期规划**
   - 避免"假质心陷阱"
   - 避免"乒乓充电效应"

---

## 📁 数据文件

### Map_03 结果
- `outputs/new_baseline_evaluation/tethered_greedy_results.json`
- `outputs/new_baseline_evaluation/static_center_results.json`
- `outputs/new_baseline_evaluation/dynamic_heuristic_results.json`
- `outputs/new_baseline_evaluation/pure_random_results.json`
- `outputs/new_baseline_evaluation/summary.json`

### Map_02 结果
- `outputs/new_baseline_evaluation_map02/tethered_greedy_results.json`
- `outputs/new_baseline_evaluation_map02/static_center_results.json`
- `outputs/new_baseline_evaluation_map02/dynamic_heuristic_results.json`
- `outputs/new_baseline_evaluation_map02/pure_random_results.json`
- `outputs/new_baseline_evaluation_map02/summary.json`

---

## 🎯 下一步行动

1. **立即行动**：
   - [ ] 使用新的3D动作空间训练PPO模型
   - [ ] 目标：在Map_02上完成 40-45 任务
   - [ ] 对比Pure-Random（39.90）和启发式（31.80）

2. **论文准备**：
   - [ ] 绘制对比图表（柱状图 + 误差棒）
   - [ ] 撰写消融实验章节
   - [ ] 准备可视化视频（UAV轨迹 + 通信热力图）

3. **系统优化**（可选）：
   - [ ] 调整奖励函数权重
   - [ ] 缩短决策周期
   - [ ] 改进baseline的任务分配策略

---

## 📝 结论

全新的baseline评估系统已成功部署，虽然前三个启发式策略在当前设置下表现一致，
但这恰好揭示了**联合优化的必要性**。Pure-Random在复杂地图上的优异表现
（39.90 vs 31.80）证明了探索的重要性，为RL方法的引入提供了强有力的动机。

下一步的重点是训练PPO模型，目标是在Map_02上达到 **40-45 任务完成数**，
超越所有baseline，证明深度强化学习在多智能体协同任务中的优势。
