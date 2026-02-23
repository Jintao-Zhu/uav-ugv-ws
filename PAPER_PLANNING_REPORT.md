# UAV-UGV协同系统论文规划报告

**日期**: 2026-02-23
**目标**: CCF C级会议论文
**项目**: UAV-UGV Cooperative Task Execution with Communication-Aware Planning

---

## 一、项目现状分析

### 1.1 已完成的核心成果

#### ✅ Layer-1: 离散仿真系统（Python）
- **完整的协同框架**: UAV-UGV异构多机器人协同任务执行
- **MAPF规划**: Prioritized Planning算法，支持3-6台UGV的无碰撞路径规划
- **通信模型**: 基于Raycast的遮挡感知通信模型（SNR计算、outage检测）
- **任务管理**: 在线任务流生成、deadline约束、任务分配与执行
- **Rendezvous机制**: UAV-UGV会合点规划与时间窗协调
- **RL训练**: PPO策略训练，100k步训练达到+66.97%性能提升

#### ✅ Layer-2: Gazebo物理仿真（ROS 2）
- **联合仿真环境**: PX4 SITL (UAV) + TurtleBot3 (UGV) + Gazebo Harmonic
- **CoopBridge节点**: 连接ag_coop决策层与Gazebo执行层
- **PI控制器**: 精确的UGV轨迹跟踪（误差<0.1m）
- **多机独立控制**: 3台UGV独立话题控制，无干扰

#### ✅ 实验数据
- **PPO训练结果**:
  - Mean reward: 22.24 (PPO) vs 13.32 (Random), +66.97%
  - Task reward: +16.94%
  - Comm penalty: +10.27% (减少通信中断)
  - Deadline penalty: +54.17%
- **63个评估指标**: reward、任务、通信、MAPF等全方位追踪
- **固定种子可复现**: 5个评估种子（10000-10004）

### 1.2 技术亮点

1. **异构协同**: UAV作为移动中继，UGV执行地面任务
2. **通信感知**: 显式建模遮挡、距离衰减，优化中继点选择
3. **Deadline约束**: 实时任务流，截止时间管理
4. **RL优化**: PPO学习任务分配+中继点选择的联合策略
5. **双层验证**: 离散仿真（快速统计）+ 物理仿真（真实性验证）

### 1.3 当前不足

1. **实验规模有限**:
   - 仅1张地图（map_01, 20×20）
   - 仅1个任务负载（λ=6.0）
   - 训练步数较少（100k步）

2. **Baseline对比不足**:
   - 仅有Random baseline
   - 缺少Greedy、Coverage等确定性策略对比

3. **Gazebo验证不完整**:
   - 地图不匹配问题（default world vs map_01）
   - UAV控制未集成
   - 缺少大规模统计实验

4. **泛化性未验证**:
   - 未测试多地图
   - 未测试不同UGV数量
   - 未测试不同任务负载

---

## 二、论文定位与创新点

### 2.1 研究问题（Problem Statement）

**核心问题**: 在通信受限环境下，如何协调UAV和多台UGV完成带deadline约束的在线任务流？

**挑战**:
1. **异构协同**: UAV和UGV能力差异大（速度、视野、载荷）
2. **通信约束**: 地面遮挡导致UGV-基站通信中断，需UAV中继
3. **实时决策**: 任务在线到达，需实时分配+路径规划
4. **多目标优化**: 任务吞吐量、deadline满足率、通信质量的权衡

### 2.2 创新点（Contributions）

#### 🌟 创新点1: 通信感知的异构协同框架
- **What**: 显式建模遮挡对通信的影响，将中继点选择纳入决策
- **Why**: 现有MAPF工作忽略通信约束，现有UAV中继工作假设UGV静止
- **How**: Raycast遮挡检测 + SNR计算 + 候选中继点集合

#### 🌟 创新点2: RL驱动的联合优化
- **What**: 用PPO学习任务分配+中继点选择的联合策略
- **Why**: 传统方法分离优化（先分配任务，再选中继），次优
- **How**: 统一observation空间（任务+通信+MAPF状态），端到端学习

#### 🌟 创新点3: 双层验证框架
- **What**: 离散仿真（大规模统计）+ 物理仿真（真实性验证）
- **Why**: 纯离散仿真缺乏真实性，纯物理仿真效率低
- **How**: Layer-1快速迭代策略，Layer-2验证关键场景

### 2.3 论文类型与投稿方向

**推荐类型**: **Application Paper**（应用型论文）

**理由**:
- 你的系统是**工程集成**（MAPF + 通信模型 + RL + ROS2），不是纯算法创新
- 核心价值在于**问题建模**和**系统实现**，而非理论突破
- CCF C会议更看重**实用性**和**完整性**

**推荐会议** (CCF C级):
1. **IROS** (International Conference on Intelligent Robots and Systems)
   - 截稿: 通常3月
   - 特点: 接受系统集成类工作，重视实验验证

2. **ICRA** (International Conference on Robotics and Automation)
   - 截稿: 通常9月
   - 特点: 机器人顶会，竞争激烈但认可度高

3. **DARS** (Distributed Autonomous Robotic Systems)
   - 截稿: 不定期
   - 特点: 专注多机器人协同，小众但对口

4. **AAMAS** (Autonomous Agents and Multiagent Systems)
   - 截稿: 通常11月
   - 特点: 多智能体方向，接受RL应用

---

## 三、论文故事线（Narrative）

### 3.1 动机（Motivation）

**场景**: 灾后搜救、仓库物流、农业巡检等需要多机器人协同的场景

**问题**:
- UGV执行地面任务，但通信受建筑/地形遮挡
- UAV可作为移动中继，但需协调位置
- 任务有deadline，需实时决策

**现有方法的不足**:
- MAPF工作: 忽略通信约束
- UAV中继工作: 假设UGV静止或轨迹已知
- 任务分配工作: 不考虑通信质量

**我们的方法**: 联合优化任务分配、路径规划、中继点选择

### 3.2 方法（Approach）

#### 系统架构
```
┌─────────────────────────────────────┐
│  Decision Layer (RL Policy)         │
│  - Task assignment (Top-M → 1)     │
│  - Relay target selection (R → 1)  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  Planning Layer (MAPF)              │
│  - Prioritized Planning             │
│  - Collision-free paths             │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  Execution Layer (Controllers)      │
│  - UGV: PI controller               │
│  - UAV: Offboard controller         │
└─────────────────────────────────────┘
```

#### 关键技术
1. **通信模型**: Raycast + 距离衰减 → SNR → outage判定
2. **Observation**: 任务状态 + UGV/UAV位置 + 通信质量 + MAPF状态
3. **Action**: 离散动作（任务选择 + 中继点选择）
4. **Reward**: 多目标加权（任务+1.0, 通信-0.05, deadline-0.1, 时间-0.01）
5. **训练**: PPO + 并行环境 + 在线评估

### 3.3 实验（Experiments）

#### 实验设置
- **地图**: 20×20格子，包含内部障碍物
- **机器人**: 3 UGV + 1 UAV
- **任务**: 在线到达，λ=6.0，deadline 25-60步
- **评估**: 5个固定种子，63个指标

#### 对比方法
1. **Random**: 随机选择任务和中继点
2. **Greedy**: 选择最近任务，最近中继点
3. **Coverage**: 启发式覆盖策略（最大化通信覆盖）
4. **PPO**: 我们的RL策略

#### 主要结果
- **PPO vs Random**: +66.97% reward
- **任务完成**: +16.94%
- **通信质量**: +10.27% (减少中断)
- **Deadline满足**: +54.17%
- **稳定性**: 方差-41.92%

#### Gazebo验证
- 3个代表场景（瓶颈/遮挡/开阔）
- 每场景20次重复
- 趋势一致性验证

### 3.4 讨论（Discussion）

**PPO学到了什么？**
1. 优先选择slack大的任务（避免deadline miss）
2. 选择覆盖多个UGV的中继点（减少通信中断）
3. 平衡任务完成速度和通信质量

**局限性**:
1. 训练地图单一，泛化性待验证
2. 训练步数有限，策略可能未完全收敛
3. 仅测试3 UGV场景，扩展性待验证

---

## 四、补充实验计划（3周）

### Week 1: 补充Baseline + 多场景实验

#### Day 1-2: 实现Greedy和Coverage baseline
- **Greedy**:
  - 任务选择: EDF (Earliest Deadline First)
  - 中继点: 最近可达点
- **Coverage**:
  - 任务选择: EDF
  - 中继点: 最大化SNR覆盖的候选点

#### Day 3-4: 多地图实验
- **目标**: 验证泛化性
- **地图**:
  - map_01 (20×20, 中等遮挡) - 已有
  - map_02 (20×20, 高遮挡) - 需生成
  - map_03 (20×20, 低遮挡/开阔) - 需生成
- **实验**: 每地图 × 3方法 × 5 seeds

#### Day 5-7: 多负载实验
- **目标**: 测试不同任务压力
- **负载**: λ ∈ {3.0, 6.0, 9.0} (低/中/高)
- **实验**: 3负载 × 3地图 × 3方法 × 5 seeds
- **产出**: Throughput vs Load曲线

### Week 2: 扩展实验 + Gazebo验证

#### Day 8-10: 多UGV扩展
- **目标**: 测试可扩展性
- **配置**: N ∈ {3, 5, 6} UGVs
- **实验**: 3配置 × 1地图 × 3方法 × 5 seeds

#### Day 11-12: 消融实验
- **目标**: 验证各模块贡献
- **变体**:
  1. No Communication (不考虑通信)
  2. Static Relay (固定中继点)
  3. No MAPF (贪心路径)
  4. Full System (完整系统)

#### Day 13-14: Gazebo验证
- **目标**: 修复地图匹配问题，完成物理验证
- **步骤**:
  1. 修复map_01.sdf与map_01.map的匹配
  2. 集成UAV offboard控制
  3. 运行3个代表场景 × 20次重复
  4. 对比Layer-1和Layer-2趋势

### Week 3: 论文撰写

#### Day 15-17: 初稿撰写
- Introduction + Related Work
- Method + System Design
- Experiments + Results

#### Day 18-19: 图表制作
- 系统架构图
- 实验结果曲线（6-8张）
- Gazebo截图/视频

#### Day 20-21: 修改润色
- 逻辑检查
- 语言润色
- 格式调整

---

## 五、论文结构建议

### Title (标题)
**推荐**: "Communication-Aware Cooperative Task Execution for Heterogeneous UAV-UGV Teams with Reinforcement Learning"

**备选**:
- "Learning to Coordinate: RL-based Task Assignment and Relay Planning for UAV-UGV Teams"
- "Joint Task Assignment and Communication Relay Planning for Multi-Robot Systems"

### Abstract (摘要, ~200词)
1. **问题**: 通信受限环境下的UAV-UGV协同任务执行
2. **挑战**: 异构能力、遮挡通信、实时决策、多目标优化
3. **方法**: RL驱动的联合优化框架（任务分配+中继点选择）
4. **结果**: PPO策略比随机策略提升66.97%，比启发式策略提升X%
5. **验证**: 离散仿真 + Gazebo物理仿真

### 1. Introduction (~2页)
- **1.1 Motivation**: 应用场景 + 问题重要性
- **1.2 Challenges**: 4个核心挑战
- **1.3 Contributions**: 3个创新点
- **1.4 Organization**: 论文结构

### 2. Related Work (~1.5页)
- **2.1 Multi-Robot Task Allocation**: 传统MRTA方法
- **2.2 Multi-Agent Path Finding**: MAPF算法（CBS, Prioritized Planning）
- **2.3 UAV as Communication Relay**: UAV中继相关工作
- **2.4 RL for Multi-Robot Coordination**: RL在多机器人中的应用
- **2.5 Gap**: 现有工作的不足 → 引出我们的工作

### 3. Problem Formulation (~1页)
- **3.1 System Model**: UAV/UGV能力、通信模型、任务模型
- **3.2 Objective**: 多目标优化公式
- **3.3 Constraints**: Deadline、碰撞避免、通信质量

### 4. Approach (~3页)
- **4.1 System Architecture**: 三层架构（决策/规划/执行）
- **4.2 Communication Model**: Raycast + SNR计算
- **4.3 RL Formulation**:
  - Observation space
  - Action space
  - Reward function
- **4.4 MAPF Integration**: Prioritized Planning
- **4.5 Training**: PPO + 并行环境

### 5. Implementation (~1页)
- **5.1 Layer-1**: Python离散仿真
- **5.2 Layer-2**: ROS 2 + Gazebo + PX4
- **5.3 CoopBridge**: 决策层与执行层的桥接

### 6. Experiments (~3页)
- **6.1 Experimental Setup**:
  - 地图、机器人配置、任务参数
  - Baseline方法
  - 评估指标
- **6.2 Main Results**:
  - PPO vs Baselines (表格+曲线)
  - 多地图泛化
  - 多负载实验
- **6.3 Ablation Study**: 各模块贡献
- **6.4 Scalability**: 多UGV扩展
- **6.5 Gazebo Validation**: 物理仿真验证

### 7. Discussion (~1页)
- **7.1 What Did PPO Learn?**: 策略分析
- **7.2 Limitations**: 当前不足
- **7.3 Future Work**: 扩展方向

### 8. Conclusion (~0.5页)
- 总结贡献
- 强调实用价值

---

## 六、关键图表规划

### 必需图表（6-8张）

1. **系统架构图**: 三层架构 + 数据流
2. **通信模型示意图**: Raycast遮挡检测 + SNR计算
3. **主实验结果对比**: PPO vs Baselines (柱状图)
4. **训练曲线**: Reward vs Training Steps
5. **多负载实验**: Throughput/Miss Rate vs Task Load (折线图)
6. **消融实验**: 各模块贡献 (柱状图)
7. **Gazebo截图**: 实际运行场景
8. **轨迹可视化**: 典型episode的UGV/UAV轨迹

### 可选图表（2-3张）

9. **多地图泛化**: 不同地图上的性能对比
10. **可扩展性**: 性能 vs UGV数量
11. **Reward分量变化**: 训练过程中各分量的演化

---

## 七、论文写作要点

### 7.1 突出实用价值

**强调**:
- 真实场景需求（灾后搜救、仓库物流）
- 系统完整性（从决策到执行的闭环）
- 双层验证（离散+物理仿真）

**避免**:
- 过度强调理论创新（你的工作是应用型）
- 夸大性能提升（+66.97%是相对Random，需要更强的baseline）

### 7.2 诚实面对局限

**承认**:
- 训练地图单一（但补充多地图实验）
- 训练步数有限（但趋势明确）
- 仅测试小规模场景（3-6 UGV）

**强调**:
- 框架可扩展（支持更多UGV/UAV）
- 方法通用（可迁移到其他场景）
- 开源计划（代码+数据公开）

### 7.3 对比相关工作

**关键差异**:
1. vs MAPF工作: 我们考虑通信约束
2. vs UAV中继工作: 我们的UGV是移动的
3. vs 任务分配工作: 我们联合优化（不是分离）
4. vs 纯RL工作: 我们有物理仿真验证

### 7.4 写作风格

**语言**:
- 简洁、直接、避免冗余
- 多用主动语态（"We propose..." 而非 "It is proposed..."）
- 避免过度修饰（"significantly" 需有统计支撑）

**逻辑**:
- 每段一个中心思想
- 段落间有过渡
- 图表与正文紧密配合

---

## 八、时间线与里程碑

### Week 1: 补充实验（Day 1-7）
- **Day 1-2**: Greedy + Coverage baseline ✅
- **Day 3-4**: 多地图实验（3张地图）✅
- **Day 5-7**: 多负载实验（3档负载）✅
- **产出**: `results_layer1_extended.csv`

### Week 2: 扩展实验 + Gazebo（Day 8-14）
- **Day 8-10**: 多UGV扩展（3/5/6 UGV）✅
- **Day 11-12**: 消融实验（4个变体）✅
- **Day 13-14**: Gazebo验证（3场景×20次）✅
- **产出**: `results_layer2.csv` + 视频

### Week 3: 论文撰写（Day 15-21）
- **Day 15-17**: 初稿（8节）✅
- **Day 18-19**: 图表制作（8张）✅
- **Day 20-21**: 修改润色 ✅
- **产出**: 完整论文初稿

---

## 九、成功标准

### 9.1 实验完整性
- ✅ 至少3个baseline（Random, Greedy, Coverage）
- ✅ 至少3张地图
- ✅ 至少3档任务负载
- ✅ 至少5个评估种子
- ✅ Gazebo物理验证

### 9.2 性能提升
- ✅ PPO vs Random: ≥50% (已达到66.97%)
- ⚠️ PPO vs Greedy: ≥20% (待验证)
- ⚠️ PPO vs Coverage: ≥10% (待验证)

### 9.3 论文质量
- ✅ 问题定义清晰
- ✅ 方法描述完整
- ✅ 实验设计合理
- ✅ 结果分析深入
- ✅ 图表专业美观

---

## 十、风险与应对

### 风险1: PPO性能不如Coverage
**概率**: 中等
**影响**: 高（削弱RL的价值）
**应对**:
1. 增加训练步数（100k → 1M）
2. 调整reward权重（增加comm权重）
3. 改变叙事: "RL接近启发式，但更通用"

### 风险2: Gazebo验证失败
**概率**: 中等
**影响**: 中（削弱真实性）
**应对**:
1. 简化验证范围（3场景 → 1场景）
2. 只做趋势验证（不要求绝对值匹配）
3. 强调Layer-1的统计价值

### 风险3: 时间不足
**概率**: 高
**影响**: 高（无法完成所有实验）
**应对**:
1. 优先级排序: 主实验 > 消融 > 扩展
2. 并行执行: 实验跑着，同时写论文
3. 降低标准: 3地图 → 2地图，5 seeds → 3 seeds

---

## 十一、总结与建议

### 你的优势
1. ✅ **系统完整**: 从决策到执行的全栈实现
2. ✅ **双层验证**: 离散+物理仿真
3. ✅ **问题新颖**: 通信感知的异构协同
4. ✅ **代码质量高**: 可复现、可扩展

### 你的劣势
1. ⚠️ **实验规模小**: 1地图、1负载、100k步
2. ⚠️ **Baseline弱**: 仅Random，缺少强baseline
3. ⚠️ **理论深度不足**: 偏工程，缺少理论分析

### 我的建议

#### 短期（3周内）
1. **优先补充Baseline**: Greedy和Coverage是必须的
2. **多地图实验**: 至少2-3张地图验证泛化性
3. **修复Gazebo**: 地图匹配问题必须解决
4. **并行写作**: 不要等实验全部完成再写

#### 中期（投稿前）
1. **增加训练步数**: 100k → 500k或1M
2. **多负载实验**: 验证不同任务压力下的性能
3. **消融实验**: 证明各模块的必要性
4. **语言润色**: 找英语好的同学帮忙

#### 论文定位
- **不要**: 定位为"算法创新"论文（你的RL算法是标准PPO）
- **应该**: 定位为"系统集成+应用"论文（强调问题建模和工程实现）
- **强调**: 实用价值、完整性、可复现性

#### 投稿策略
1. **首选**: IROS（接受系统类工作，认可度高）
2. **备选**: DARS（小众但对口）或AAMAS（RL方向）
3. **保底**: 国内会议（如ROBIO、CCC）

---

## 十二、行动清单

### 立即开始（本周）
- [ ] 实现Greedy baseline
- [ ] 实现Coverage baseline
- [ ] 生成2张新地图（高遮挡、低遮挡）
- [ ] 修复Gazebo地图匹配问题

### Week 1
- [ ] 运行多地图实验（3地图 × 3方法 × 5 seeds）
- [ ] 运行多负载实验（3负载 × 3方法 × 5 seeds）
- [ ] 开始写Introduction和Related Work

### Week 2
- [ ] 运行消融实验（4变体 × 5 seeds）
- [ ] 完成Gazebo验证（3场景 × 20次）
- [ ] 写完Method和Experiments章节

### Week 3
- [ ] 制作所有图表（8张）
- [ ] 完成初稿
- [ ] 修改润色
- [ ] 准备投稿材料

---

**最后的话**: 你的项目基础很扎实，代码质量高，问题定义清晰。只要补充足够的对比实验，完全有机会发表CCF C级会议。关键是**不要贪多**，聚焦核心贡献，把故事讲清楚。加油！

---

**报告完成日期**: 2026-02-23
**作者**: Claude Opus 4.6
