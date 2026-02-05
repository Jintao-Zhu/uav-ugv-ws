下面给出一个**三周（21 天）内“必能完成”的实验规划**。核心原则是：**先把 Layer-1（Python 离散主实验）做成“跑就出曲线”的闭环**；RL 作为增益项，但即使 RL 训练效果一般，也通过 **“Heuristic + Imitation 兜底”** 保证实验一定产出。Gazebo（Layer-2）只做少量复现验证，严格限范围，避免工程爆炸。

---

# 总体交付物（21 天结束时必须具备）

## Layer-1（主实验，必须大规模统计）

* `results_layer1.csv`：覆盖 **≥20 张地图 × 3 档任务负载 × 4 种方法** 的统计结果
* 主指标曲线：

  * throughput（完成任务数/单位时间）
  * miss rate / mean tardiness / p95 tardiness（deadline 指标）
  * outage%（通信软指标）
  * MAPF 规划耗时/超时率、回退次数
* 代表性轨迹与日志：每类方法至少 3 个 episode 可复现（固定 seed）

## Layer-2（Gazebo 验证，范围受控）

* 3 个代表场景（瓶颈/遮挡强/开阔对照），每场景 **≥20 次**重复
* `results_layer2.csv` + 1 张“Layer-1 vs Layer-2 趋势一致性”对照表
* 1 段可展示的视频/截图序列（不是必须大规模）

---

# 全程默认配置（保证稳定、可跑、易调参）

* UAV：1 台
* UGV：训练阶段 N=3 或 4；评测阶段扩到 N=6（如果算力允许再到 8）
* 决策周期：`K = 5`
* MAPF horizon：`H = 60`
* MAPF time budget：`0.3s ~ 0.5s / replanning`（保守稳定）
* 候选会合/中继点数量：`R = 12`（固定离散候选，降低 RL 难度）
* 任务池 Top-M：`M = 5`（动作维度可控）
* 载机移动 + 会合：采用 **rendezvous 机制**（UAV 回收目标是“会合点 + 时间窗”，不是追车降落）
* 通信：软指标（outage 进入 reward/评测，不做硬约束）

---

# 风险兜底策略（保证“必完成”）

你最担心的是 RL 训练不稳定、或 MAPF 与会合耦合导致 episode 崩。这里直接给硬兜底：

1. **MAPF 失败/超时**：全体 UGV `WAIT K` 步（安全回退，episode 不会中断）
2. **会合失败**：UAV 去最近安全降落点集合 `S`（预选开阔格子），落地等待；UGV 后续去回收（记录 emergency 次数）
3. **RL 训练兜底**：

   * Day 12 前若 PPO 没明显收益，立刻转 **Imitation Learning（模仿 Heuristic Coverage）**，保证“学习策略”一定有可用版本
   * 最终论文实验仍可报告：RL vs Heuristic（或 IL vs Heuristic）

---

# 三周详细日程（每天明确产物与验收）

## Week 1：把系统跑通（闭环优先）

### Day 1：工程骨架与可复现配置

* 建目录与配置：`configs/default.yaml`（K/H/R/M/N/λ/seed 等）
* 固定随机源：Python `random`/`numpy`/环境 seed 全部统一
* **验收产物**：`run_one_episode.py --seed 0` 能跑到结束并输出基础 metrics（哪怕很差）

### Day 2：地图与离散化（Layer-1）

* 读入你的 grid map 格式（直接复用你现有地图/解析逻辑）
* 定义坐标系与 cell↔world 映射（Layer-2 会用到）
* **验收产物**：任意地图可输出 `free_cells`、邻接、路点中心坐标

### Day 3：通信模型（软指标）实现

* `comm_model.py`：raycast（Bresenham）统计遮挡格数 + 距离衰减 → SNR
* 定义 `outage(t)` 与 `outage%`
* **验收产物**：给定一段 UAV/UGV 轨迹，能稳定输出 `SNR_best(t)` 曲线与 outage%

### Day 4：deadline 任务流与任务池

* `tasks.py`：在线任务生成（release, x, y, deadline）
* 定义完成时刻：**先用“到达任务点即完成”**（更稳，后续可扩展）
* **验收产物**：固定 seed 生成可复现任务流；能统计 miss/tardiness

### Day 5：UAV 执行器（sortie + 能量 + 会合）

* UAV 状态机：ONBOARD → OUTBOUND → SERVICING → INBOUND(rendezvous)
* 能量模型（简单线性消耗）+ loiter（等待耗能）
* **验收产物**：单 UAV 在移动 rendezvous 目标下能回收；会合失败能触发 emergency

### Day 6：UGV MAPF wrapper 接入（离散层）

* 写 `ugv_mapf_wrapper.py`：输入 starts/goals/time_budget → 输出 paths/plan_time/success
* 执行策略：receding horizon，失败则 WAIT K
* **验收产物**：N=3 在一张地图上可无碰撞运行 500 步

### Day 7：系统闭环 v1（无 RL）+ 两个 baseline

* Baseline A：Static Relay（UGV 不动）
* Baseline B：Greedy（按距离选会合点/中继点）
* 输出统一 `episode_log.jsonl` 与 `metrics.json`
* **验收产物**：两种 baseline 在同一场景跑完并输出不同指标（哪怕差异小）

---

## Week 2：补齐强 baseline + RL/IL 训练管线 + 小规模统计

### Day 8：Heuristic Coverage baseline（你的“强确定性策略”）

* 候选点集合 `R`：路口/高分叉 + 任务热点周边（固定生成）
* 打分函数：最大化预测 `SNR_best` + 加入拥堵惩罚（如局部占用/等待计数）
* **验收产物**：在遮挡强地图上 outage% 明显优于 Greedy（通常很稳）

### Day 9：Gym 环境封装（RL API 固化）

* `reset()`/`step(action)`，action = (task_choice, relay_targets)
* obs 含：UGV/UAV 状态、Top-M 任务、通信摘要、候选点摘要
* **验收产物**：random policy 能跑完 episode（无崩溃、无 NaN）

### Day 10：PPO 训练跑通（小规模）

* 训练设置：N=3、1–3 张训练地图、低负载 λ_low
* reward：完成任务 +1；每步时间罚；outage 罚；tardiness 罚；MAPF 超时罚
* **验收产物**：reward 曲线有上升趋势；policy 能完成任务

### Day 11：Curriculum（负载/遮挡逐步增强）

* 从 λ_low → λ_mid，逐步增遮挡惩罚参数 B 或提高 θ
* **验收产物**：policy 不崩；outage% 相对 Greedy 有改善迹象

### Day 12：学习策略兜底分叉（必须做，保证完成）

> 这是“确保一定完成”的关键关口。

* 若 PPO 已优于 Greedy/接近 Heuristic：继续 PPO
* 若 PPO 不稳定/收益弱：立刻做 **Imitation Learning**

  * 用 Heuristic Coverage 生成 (obs, action) 数据集（≥50k steps）
  * 训练一个小 MLP 分类器输出离散动作（或分开预测 task 与 relay）
* **验收产物**：得到一个“学习策略”模型（PPO 或 IL），可稳定跑完 episode

### Day 13：小规模 sweep（先出第一批可用曲线）

* 地图：3–5 张代表地图
* 负载：λ_low/λ_mid/λ_high
* 方法：Static/Greedy/Coverage/Learned
* **验收产物**：`results_layer1_small.csv` + 初版 3 张图（throughput、outage%、miss rate）

### Day 14：会合与移动载机的鲁棒性检查

* 加扰动（确定性、可复现）：

  * 指定时刻让 carrier UGV 强制 wait 3 步
  * 临时封闭一段走廊（在 grid 上加动态障碍）
* **验收产物**： learned/coverage/greedy 在扰动下趋势差异清晰（哪怕 learned 不赢，也能写“鲁棒性”）

---

## Week 3：全量统计 + Gazebo 小规模验证 + 完整实验包

### Day 15：全量评测脚本与并行化

* `run_sweep.py`：自动遍历 maps×λ×methods×seeds
* 每个配置重复 seeds=10（保守可缩到 5，先保证完成）
* **验收产物**：一键产出 `results_layer1.csv`（至少先跑 10 张地图）

### Day 16：跑满 Layer-1 全量实验（优先完成统计）

* 目标：≥20 张地图、3 档负载、4 方法、≥5 seeds
* **验收产物**：`results_layer1.csv` 完整落盘；失败配置可自动重试/记录原因

### Day 17：Layer-1 主图与消融（必须）

* 消融：K∈{3,5,8}、MAPF 预算∈{0.2s,0.5s}（只做 1–2 个维度，别扩太大）
* **验收产物**：`figures_layer1/`：至少 6 张图（throughput/outage/miss/tardiness/plan_time/timeout）

### Day 18：选 Gazebo 代表场景并“对齐”数据

* 从 Layer-1 选 3 个场景：瓶颈/遮挡强/开阔
* 固化：对应 grid、候选点 R、任务流 seed、方法配置
* **验收产物**：`gazebo_cases/`（每个 case 有 yaml 配置 + 任务流文件）

### Day 19：Gazebo 最小闭环（只做执行与指标采集）

* 仅做：UGV waypoint follower + pose 读取 + outage 计算
* MAPF 仍在 grid 上算，输出 waypoint 给 Gazebo 执行
* UAV：先用简化 position controller（或直接按离散航点更新位置，不引入飞控）
* **验收产物**：1 个 case 跑通 5 次，得到 `results_layer2_case1.csv`

### Day 20：Gazebo 3 个 case 全部跑完（每 case ≥20 次）

* 方法至少做 2 个：Greedy vs Coverage 或 Greedy vs Learned（看 learned 是否稳）
* **验收产物**：`results_layer2.csv` + 关键截图/短视频

### Day 21：最终实验包整理（复现实验“必成功”）

* `reproduce.md`：

  * Layer-1：一键跑小规模 / 一键跑全量 / 一键出图
  * Layer-2：每个 case 一键运行与采集
* 输出最终压缩包结构（代码 + 配置 + 数据 + 图）
* **验收产物**：从空目录按 `reproduce.md` 能复现主要结果（至少 small 版）

---

# 关键实现细节（避免 Day 5–6 被卡住）

## 1) “UGV 允许移动 + UAV 回收”一定用 rendezvous，不做追车降落

* 每个 sortie 生成一个 `rendezvous_cell` 与 `t_meet`（可选离散档位：早/中/晚）
* carrier UGV 的近期目标强制包含 `rendezvous_cell`
* UAV 若提前到：loiter；UGV 若提前到：wait；错过则 emergency
  这样耦合可控、实现量小、不会把系统拖死。

## 2) deadline 必须体现在决策与指标

* 每个任务计算 slack：`deadline - (t + estimated_completion)`
* baselines 至少在 task 选择里用 EDF（Earliest Deadline First）或 slack 最小优先
  这保证 deadline 不是“挂名”。

---

# 你将得到的最小可用对比（即使 RL 表现一般也稳）

* Static vs Greedy：一定有差异（吞吐/延迟）
* Greedy vs Coverage：通常一定在 outage% 上有差异
* Coverage vs Learned：若 PPO 不好，IL 至少能接近 Coverage（保证“学习策略”可用）
* MAPF vs No-MAPF（可选）：瓶颈场景下拥堵/延迟差异通常非常明显

---

如果你希望我把 Day 1–Day 3 的**接口定义写到“可以直接编码”**（例如 `action/obs` 张量维度、`results.csv` 字段、任务与会合的 YAML/JSON 格式），我可以在下一条消息直接给出一份“实验协议与数据格式规范”（不涉及论文写作）。
