# UAV-UGV 协同系统操作指南

本文档提供完整的系统操作说明，包括环境配置、训练、评估、可视化等所有操作。

---

## 📋 目录

1. [快速开始](#快速开始)
2. [环境配置](#环境配置)
3. [系统运行](#系统运行)
4. [RL 训练](#rl-训练)
5. [策略评估](#策略评估)
6. [可视化](#可视化)
7. [实验复现](#实验复现)
8. [常用工具](#常用工具)

---

## 快速开始

### 最小运行示例

```bash
# 1. 进入工作目录
cd ag_coop

# 2. 运行单个 episode（使用默认配置）
python scripts/run_one_episode.py --seed 0

# 3. 查看输出
ls outputs/
```

### 核心文件结构

```
ag_coop/
├── agcoop/                    # 核心代码
│   ├── env/                   # 环境实现
│   │   ├── core.py           # 主环境类
│   │   └── wrappers.py       # Gym 包装器
│   ├── rl/                    # RL 相关
│   │   └── callbacks.py      # 训练回调
│   ├── robots/                # 机器人控制器
│   ├── tasks/                 # 任务管理
│   ├── comm/                  # 通信模型
│   └── mapf/                  # MAPF 规划
├── configs/                   # 配置文件
│   ├── default.yaml          # 默认配置
│   └── day10_ppo_train.yaml  # PPO 训练配置
├── scripts/                   # 可执行脚本
├── maps/                      # 地图文件
└── outputs/                   # 输出目录
```

---

## 环境配置

### 依赖安装

```bash
# Python 环境（推荐 Python 3.10）
pip install numpy scipy pyyaml
pip install stable-baselines3 gymnasium
pip install matplotlib seaborn pandas

# MAPF 求解器（CBS）
# 确保 libMultiRobotPlanning.so 在系统路径中
```

### 配置文件说明

主配置文件：`configs/default.yaml`

```yaml
episode:
  horizon_steps: 500          # Episode 长度
  decision_period: 5          # 决策周期 K
  map_path: "maps/map_01.map" # 地图路径
  seed: 0                     # 随机种子

robots:
  n_ugv: 3                    # UGV 数量
  n_uav: 1                    # UAV 数量

tasks:
  arrival_rate: 0.1           # 任务到达率
  deadline_min: 25            # 最小 deadline
  deadline_max: 60            # 最大 deadline

comm:
  enabled: true               # 启用通信模型
  obstacle_penalty_db: 6.0    # 遮挡惩罚

mapf:
  enabled: false              # 是否启用 MAPF
  time_budget_ms: 300         # MAPF 时间预算
```

---

## 系统运行

### 1. 运行单个 Episode

```bash
# 基础运行
python scripts/run_one_episode.py --seed 0

# 指定配置文件
python scripts/run_one_episode.py \
    --config configs/default.yaml \
    --seed 42

# 指定输出目录
python scripts/run_one_episode.py \
    --seed 0 \
    --out_dir outputs/test_run
```

**输出文件**：
- `metrics.json` - 性能指标
- `trace.jsonl` - 完整轨迹（可选）
- `config_resolved.yaml` - 解析后的配置

### 2. 运行 Baseline 对比

```bash
# Day8 通信 baseline 对比（Greedy vs Coverage）
python scripts/run_day8_comm_baselines.py

# 输出：outputs/day8_comm_baselines/
#   - greedy_results.json
#   - coverage_results.json
#   - comparison.json
```

### 3. 批量实验（Sweep）

```bash
# 任务负载扫描
python scripts/sweep_task_load.py \
    --map maps/map_01.map \
    --loads 0.05 0.1 0.15 0.2 \
    --seeds 5 \
    --out_dir outputs/load_sweep

# 通信阈值扫描
python scripts/sweep_threshold.py \
    --thresholds -12 -9 -6 -3 \
    --seeds 5
```

---

## RL 训练

### 1. PPO 训练（Day10 配置）

```bash
# 使用 Day10 配置训练
python scripts/day10_train_ppo.py \
    --config configs/day10_ppo_train.yaml \
    --out_dir outputs/day10_ppo

# 自定义训练参数
python scripts/day10_train_ppo.py \
    --config configs/day10_ppo_train.yaml \
    --total_timesteps 1000000 \
    --n_envs 8 \
    --learning_rate 0.0003 \
    --out_dir outputs/ppo_1m
```

**训练配置关键参数**：
```yaml
training:
  total_timesteps: 100000     # 总训练步数
  n_envs: 4                   # 并行环境数
  batch_size: 256             # Batch size
  n_steps: 64                 # 每环境步数 (batch_size / n_envs)
  learning_rate: 0.0003       # 学习率
  eval_freq: 2500             # 评估频率
  eval_episodes: 5            # 评估 episode 数
```

**训练输出**：
```
outputs/day10_ppo/
├── checkpoints/              # 模型检查点
│   ├── best_model.zip       # 最佳模型
│   └── rl_model_50000_steps.zip
├── eval_logs/                # 评估日志
│   ├── eval_0.json
│   └── eval_2500.json
├── tb/                       # TensorBoard 日志
├── config_resolved.yaml      # 训练配置
└── training_summary.json     # 训练总结
```

### 2. 监控训练进度

```bash
# 启动 TensorBoard
tensorboard --logdir outputs/day10_ppo/tb --port 6006

# 浏览器访问
# http://localhost:6006
```

**关键指标**：
- `rollout/ep_rew_mean` - 平均 episode 奖励
- `train/loss` - 训练损失
- `eval/mean_reward` - 评估平均奖励
- `eval/tasks_completed` - 完成任务数
- `eval/deadline_miss` - Deadline miss 数

### 3. 恢复训练

```bash
# 从检查点恢复
python scripts/day10_train_ppo.py \
    --config configs/day10_ppo_train.yaml \
    --resume outputs/day10_ppo/checkpoints/rl_model_50000_steps.zip \
    --total_timesteps 200000
```

---

## 策略评估

### 1. 评估训练好的 PPO 策略

```bash
# 使用 Day10 对比脚本
python scripts/day10_step5_compare_policies.py \
    --model outputs/day10_ppo/checkpoints/best_model.zip \
    --config configs/day10_ppo_train.yaml \
    --seeds 10000 10001 10002 10003 10004 \
    --out_dir outputs/ppo_eval

# 输出：
#   - ppo_policy_results.json
#   - random_policy_results.json
#   - comparison_results.json
```

### 2. 多策略对比

```bash
# Day8 最终对比（10 seeds）
python scripts/day8_10seed_compare.py \
    --map maps/map_01.map \
    --seeds 10 \
    --out_dir outputs/day8_10seed

# 输出对比表格和统计
```

### 3. 评估指标说明

**核心指标**：
- `total_reward` - 总奖励
- `tasks_completed` - 完成任务数
- `deadline_miss` - Deadline miss 数
- `deadline_miss_rate` - Miss 率 (%)
- `outage_steps` - 通信中断步数
- `outage_percent` - 中断百分比 (%)

**Reward 分量**：
- `reward_task` - 任务完成奖励 (+1.0 per task)
- `reward_time` - 时间惩罚 (-0.01 per step)
- `reward_comm` - 通信惩罚 (-0.05 per outage step)
- `reward_deadline` - Deadline 惩罚 (-0.1 per miss)
- `reward_mapf` - MAPF 超时惩罚 (-0.2 per timeout)

---

## 可视化

### 1. 轨迹可视化

```bash
# 可视化单个 episode
python scripts/visualize.py \
    --trace outputs/test_run/trace.jsonl \
    --map maps/map_01.map \
    --out_dir outputs/viz

# 生成动画（需要 ffmpeg）
python scripts/visualize.py \
    --trace outputs/test_run/trace.jsonl \
    --map maps/map_01.map \
    --animate \
    --fps 10 \
    --out outputs/animation.mp4
```

**可视化内容**：
- UGV/UAV 轨迹
- 任务位置和状态
- 通信连接（SNR 热力图）
- 候选中继点
- 时间轴

### 2. 性能曲线绘制

```bash
# 绘制 tradeoff 曲线
python scripts/plot_tradeoff_curves.py \
    --results outputs/load_sweep/results.csv \
    --out_dir outputs/figures

# 生成图表：
#   - throughput_vs_load.png
#   - miss_rate_vs_load.png
#   - outage_vs_load.png
```

### 3. 通信分析

```bash
# 检查通信质量
python scripts/inspect_comm.py \
    --trace outputs/test_run/trace.jsonl \
    --map maps/map_01.map

# 扩展通信分析
python scripts/inspect_comm_extended.py \
    --trace outputs/test_run/trace.jsonl \
    --out_dir outputs/comm_analysis
```

---

## 实验复现

### Day10 PPO 训练完整复现

```bash
# Step 1: 训练 PPO（100k 步，~2 分钟）
python scripts/day10_train_ppo.py \
    --config configs/day10_ppo_train.yaml \
    --out_dir outputs/day10_ppo_reproduce

# Step 2: 评估策略（5 个固定种子）
python scripts/day10_step5_compare_policies.py \
    --model outputs/day10_ppo_reproduce/checkpoints/best_model.zip \
    --config configs/day10_ppo_train.yaml \
    --seeds 10000 10001 10002 10003 10004 \
    --out_dir outputs/day10_eval_reproduce

# Step 3: 验证结果
python scripts/verify_day10_delivery.py \
    --eval_dir outputs/day10_eval_reproduce

# 预期结果：
# - PPO mean reward: ~22.24 (±3.99)
# - Random mean reward: ~10.62 (±5.35)
# - Improvement: +109.42%
```

### 验证交付包

```bash
# 验证 Day10 交付包完整性
python scripts/verify_day10_delivery.py \
    --package outputs/day10_ppo_summary

# 检查项：
# ✅ 配置文件存在且一致
# ✅ 模型文件存在
# ✅ 评估结果完整
# ✅ Metrics 非零且合理
# ✅ 文档完整
```

---

## 常用工具

### 1. 配置检查

```bash
# 打印解析后的配置
python scripts/print_config.py \
    --config configs/day10_ppo_train.yaml

# 检查配置一致性
python scripts/test_catalog_consistency.py
```

### 2. 地图工具

```bash
# 检查地图信息
python scripts/inspect_map.py \
    --map maps/map_01.map

# 输出：
#   - 地图尺寸
#   - 障碍物数量
#   - 自由格子数
#   - 连通性

# 生成候选中继点
python scripts/gen_candidates.py \
    --map maps/map_01.map \
    --count 12 \
    --out candidates.json
```

### 3. 碰撞检测

```bash
# 检查轨迹碰撞
python scripts/check_collisions.py \
    --trace outputs/test_run/trace.jsonl

# 调试碰撞
python scripts/debug_collision.py \
    --trace outputs/test_run/trace.jsonl \
    --timestep 150
```

### 4. 输出验证

```bash
# 验证输出完整性
python scripts/validate_output_integrity.py \
    --out_dir outputs/test_run

# 验证 Day6 输出格式
python scripts/validate_day6_outputs.py \
    --out_dir outputs/day6_test
```

---

## 常见问题

### Q1: 训练时 reward 不收敛？

**检查项**：
1. 学习率是否合适（推荐 3e-4）
2. Batch size 和 n_steps 是否匹配（batch_size = n_steps × n_envs）
3. Reward 权重是否合理（task: 1.0, comm: 0.05, deadline: 0.1）
4. 环境是否稳定（检查 NaN/Inf）

```bash
# 检查训练日志
grep "NaN\|Inf" outputs/day10_ppo/training.log

# 降低学习率重试
python scripts/day10_train_ppo.py \
    --learning_rate 0.0001
```

### Q2: MAPF 频繁超时？

**解决方案**：
1. 增加时间预算：`time_budget_ms: 500`
2. 减少 horizon：`H: 40`
3. 暂时禁用 MAPF：`mapf.enabled: false`

### Q3: 通信 outage 过高？

**调整参数**：
```yaml
comm:
  obstacle_penalty_db: 6.0    # 降低遮挡惩罚（原 10.0）
  snr_threshold_db: -9.0      # 降低 SNR 阈值（原 -6.0）
```

### Q4: 如何加速训练？

```bash
# 增加并行环境
python scripts/day10_train_ppo.py \
    --n_envs 8  # 原 4

# 减少评估频率
python scripts/day10_train_ppo.py \
    --eval_freq 5000  # 原 2500

# 使用更小的地图
# 修改 configs/day10_ppo_train.yaml:
#   map_path: "maps/test_small.map"
```

---

## 性能基准

### 硬件配置

- CPU: Intel i7 或同等性能
- RAM: 16 GB
- GPU: 不需要（CPU 训练即可）

### 运行时间参考

| 任务 | 时间 | 说明 |
|------|------|------|
| 单 episode (500 步) | ~1-2 秒 | 不启用 MAPF |
| 单 episode (500 步) | ~3-5 秒 | 启用 MAPF |
| PPO 训练 (100k 步) | ~2 分钟 | 4 并行环境 |
| PPO 训练 (1M 步) | ~20 分钟 | 4 并行环境 |
| 评估 (5 episodes) | ~10 秒 | 固定种子 |

---

## 引用和文档

### 相关文档

- [DEVLOG.md](DEVLOG.md) - 完整开发日志
- [DAY10_SUMMARY.md](DAY10_SUMMARY.md) - Day10 总结
- [outputs/day10_ppo_summary/README.md](outputs/day10_ppo_summary/README.md) - 交付包说明

### 核心论文

- PPO: Schulman et al., "Proximal Policy Optimization Algorithms", 2017
- CBS (MAPF): Sharon et al., "Conflict-Based Search For Optimal Multi-Agent Path Finding", 2012

---

## 联系和支持

如有问题，请查看：
1. [DEVLOG.md](DEVLOG.md) - 详细实现记录
2. [outputs/day10_ppo_summary/summary.md](outputs/day10_ppo_summary/summary.md) - 实验结果
3. GitHub Issues（如果有）

---

---

# 三周实验规划（原文档）

下面给出一个**三周（21 天）内"必能完成"的实验规划**。核心原则是：**先把 Layer-1（Python 离散主实验）做成"跑就出曲线"的闭环**；RL 作为增益项，但即使 RL 训练效果一般，也通过 **"Heuristic + Imitation 兜底"** 保证实验一定产出。Gazebo（Layer-2）只做少量复现验证，严格限范围，避免工程爆炸。

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


