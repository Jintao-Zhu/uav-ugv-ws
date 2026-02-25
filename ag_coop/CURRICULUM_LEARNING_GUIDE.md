# Curriculum Learning Implementation Guide

## 概述

本实现基于课程学习（Curriculum Learning）和分布对齐（Distribution Alignment）原则，旨在解决Day24中数据增强导致的负迁移问题。

## 核心改进

### 1. 分布对齐
- **问题**：Day24的数据增强（随机化arrival_rate和deadline）导致训练分布与测试分布不一致
- **解决**：固定所有任务参数
  - `arrival_rate = 0.1`（固定）
  - `deadline_min = 25, deadline_max = 60`（固定标准范围）

### 2. 课程学习策略

三阶段渐进式训练，从简单到复杂：

#### Stage 1: 基础协同与认知（300k steps）
- **地图**: Map_03（开放地图，几乎无遮挡）
- **目标**: 学习基础的UAV-UGV协同和任务分配
- **参数**:
  - Learning rate: 0.0005
  - Entropy coefficient: 0.02（高探索率）
- **预期**: 建立正向奖励映射，无需担心复杂路径规划

#### Stage 2: 障碍物适应与规避（300k steps）
- **地图**: Map_01（中等遮挡）
- **目标**: 学习绕路和应对通信中断
- **参数**:
  - Learning rate: 0.0003（降低）
  - Entropy coefficient: 0.01（降低探索）
- **预期**: 在已有协同能力基础上微调移动策略

#### Stage 3: 极端高压微调（400k steps）
- **地图**: Map_02（高遮挡，目标测试地图）
- **目标**: 学习在极端通信阻断下的权衡策略
- **参数**:
  - Learning rate: 0.0001（进一步降低）
  - Entropy coefficient: 0.005（侧重利用已有知识）
- **预期**: 最终策略打磨，学会何时舍弃任务以保持通信

## 文件说明

### 训练脚本
- **[curriculum_train_ppo.py](scripts/curriculum_train_ppo.py)**: 主训练脚本
  - 实现三阶段课程学习
  - 自动保存每个阶段的模型
  - 连续的TensorBoard日志（`reset_num_timesteps=False`）

### 配置文件
- **[curriculum_learning.yaml](configs/curriculum_learning.yaml)**: 课程学习配置
  - 固定任务参数（分布对齐）
  - 训练超参数设置

### 评估脚本
- **[evaluate_curriculum.py](scripts/evaluate_curriculum.py)**: 测试集评估
  - 使用seeds 20000-20009（10个episodes）
  - 计算完成任务数、方差、奖励等指标

## 使用方法

### 1. 启动训练

```bash
cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop

# 使用默认配置
python scripts/curriculum_train_ppo.py --config configs/curriculum_learning.yaml

# 自定义参数
python scripts/curriculum_train_ppo.py \
    --config configs/curriculum_learning.yaml \
    --n_envs 8 \
    --seed 42 \
    --device cuda
```

### 2. 监控训练进度

```bash
# 启动TensorBoard
tensorboard --logdir outputs/curriculum_ppo/run_<timestamp>/tb

# 关键指标：
# - rollout/ep_rew_mean: Episode平均奖励
# - train/entropy_loss: 探索程度
# - train/learning_rate: 学习率变化
```

**重要观察点**：
- **300k步**（Stage 1→2切换）：奖励会骤降（正常现象）
- **600k步**（Stage 2→3切换）：奖励再次骤降（正常现象）
- **恢复速度**：如果课程学习有效，奖励应快速回升

### 3. 评估最终模型

```bash
# 在Map_02上评估（测试集seeds 20000-20009）
python scripts/evaluate_curriculum.py \
    --model outputs/curriculum_ppo/run_<timestamp>/models/ppo_curriculum_final.zip \
    --config configs/curriculum_learning.yaml \
    --map maps/map_02.map \
    --test_seeds 20000-20009
```

### 4. 评估各阶段模型（可选）

```bash
# 评估Stage 1模型
python scripts/evaluate_curriculum.py \
    --model outputs/curriculum_ppo/run_<timestamp>/models/ppo_curriculum_stage1.zip \
    --map maps/map_03.map \
    --test_seeds 20000-20009

# 评估Stage 2模型
python scripts/evaluate_curriculum.py \
    --model outputs/curriculum_ppo/run_<timestamp>/models/ppo_curriculum_stage2.zip \
    --map maps/map_01.map \
    --test_seeds 20000-20009

# 评估Stage 3模型（最终模型）
python scripts/evaluate_curriculum.py \
    --model outputs/curriculum_ppo/run_<timestamp>/models/ppo_curriculum_stage3.zip \
    --map maps/map_02.map \
    --test_seeds 20000-20009
```

## 预期结果

### 成功标准
- **平均完成任务数**: 35-40（在Map_02上，seeds 20000-20009）
- **标准差**: < 5（方差大幅缩小，模型稳定性提升）
- **对比Day24**: 应显著优于Day24的结果

### TensorBoard曲线特征
1. **Stage 1（0-300k）**: 奖励稳定上升
2. **Stage 2（300k-600k）**: 初期骤降后快速恢复
3. **Stage 3（600k-1000k）**: 初期骤降后逐步收敛

## 输出文件结构

```
outputs/curriculum_ppo/run_<timestamp>/
├── config.yaml                          # 配置文件
├── curriculum_plan.json                 # 课程学习计划
├── training_summary.json                # 训练摘要
├── models/
│   ├── ppo_curriculum_stage1.zip       # Stage 1模型
│   ├── ppo_curriculum_stage2.zip       # Stage 2模型
│   ├── ppo_curriculum_stage3.zip       # Stage 3模型
│   └── ppo_curriculum_final.zip        # 最终模型
├── stage1_info.json                     # Stage 1信息
├── stage2_info.json                     # Stage 2信息
├── stage3_info.json                     # Stage 3信息
├── stage1_checkpoints/                  # Stage 1检查点
├── stage2_checkpoints/                  # Stage 2检查点
├── stage3_checkpoints/                  # Stage 3检查点
├── stage1_eval_logs/                    # Stage 1评估日志
├── stage2_eval_logs/                    # Stage 2评估日志
├── stage3_eval_logs/                    # Stage 3评估日志
└── tb/                                  # TensorBoard日志
    ├── stage1_*/
    ├── stage2_*/
    └── stage3_*/
```

## 理论依据

### 为什么课程学习有效？

1. **避免负迁移**: 直接在高难度地图训练容易学到次优策略（过度保守）
2. **渐进式学习**: 人类学习的自然方式，从简单到复杂
3. **知识迁移**: 在简单地图学到的协同策略可迁移到复杂地图
4. **探索效率**: 简单环境中更容易探索到有效策略

### 为什么分布对齐重要？

1. **MDP一致性**: 训练和测试的马尔可夫决策过程必须一致
2. **避免过拟合**: 数据增强可能导致模型学习到错误的泛化方向
3. **可复现性**: 固定参数确保实验可复现

## 故障排查

### 问题1: 奖励在Stage切换后不恢复
- **可能原因**: 学习率过低或探索率过低
- **解决方案**: 适当提高当前Stage的learning_rate或ent_coef

### 问题2: 最终性能不如预期
- **可能原因**: Stage 3训练步数不足
- **解决方案**: 增加Stage 3的timesteps（如500k或600k）

### 问题3: 方差仍然很大
- **可能原因**: 网络容量不足或训练不充分
- **解决方案**: 增加网络层数或增加总训练步数

## 下一步优化方向

1. **自适应课程**: 根据性能自动调整Stage切换时机
2. **多地图混合**: 在Stage 3混合多张高难度地图
3. **奖励塑形**: 进一步优化奖励函数权重
4. **网络架构**: 尝试更深的网络或注意力机制

## 参考文献

- Bengio et al. (2009). "Curriculum Learning"
- Narvekar et al. (2020). "Curriculum Learning for Reinforcement Learning Domains: A Framework and Survey"
