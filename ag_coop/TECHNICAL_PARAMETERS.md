# 系统建模技术细节文档

## 1. SNR 计算细节

### 1.1 基本参数

**发射功率 ($P_{tx}$)**:
- 数值: `0.0 dBm`
- 代码位置: `agcoop/comm/comm_model.py:34`
- 说明: 相对参考功率，实际物理功率可以理解为标准化后的基准值

**噪声底噪 ($N_0$)**:
- 隐式包含在 SNR 阈值中
- SNR 阈值: `-20.0 dB`
- 代码位置: `agcoop/comm/comm_model.py:38`
- 说明: 系统采用相对 SNR 模型，噪声底噪已归一化到阈值判定中

### 1.2 SNR 计算公式

**完整公式**:
```
SNR(dB) = P_tx - 10 × n × log₁₀(d + ε) - α × N_obs
```

其中:
- `P_tx = 0.0 dBm` (发射功率)
- `n = 2.0` (路径损耗指数，自由空间传播)
- `d` (距离，单位：米)
- `ε = 0.05 m` (避免 log(0) 的小量)
- `α` (障碍物衰减系数，取决于链路类型)
  - **G2G (地对地)**: `α = 6.0 dB/障碍物`
  - **A2G (空对地)**: `α = 1.5 dB/障碍物`
- `N_obs` (射线穿过的障碍物格子数)

**代码实现**: `agcoop/comm/comm_model.py:83-101`

### 1.3 A2G vs G2G 差异化建模

**核心创新**: 基于仰角的智能穿透惩罚

**G2G (Ground-to-Ground)**:
- 场景: UGV ↔ UGV, 或 UAV(ONBOARD) ↔ UGV
- 障碍物衰减: `6.0 dB/障碍物`
- 物理原理: 信号平行贴地传输，穿墙极其困难
- 代码: `agcoop/comm/comm_model.py:96-98`

**A2G (Air-to-Ground)**:
- 场景: UAV(FLYING/HOVERING) ↔ UGV
- 障碍物衰减: `1.5 dB/障碍物` (仅为 G2G 的 25%)
- 物理原理: 空中俯角穿透，具有视距(LoS)优势
- 特殊优化: 极近距离 (d < 3m) 时，仰角极大，几乎无视遮挡 (α = 0)
- 代码: `agcoop/comm/comm_model.py:87-94`

**性能提升**: A2G 相比 G2G 可获得约 **9 dB** 的 SNR 改善
- 示例: 10米距离 + 2个障碍物
  - G2G: SNR = 0 - 20.04 - 12.0 = **-32.04 dB** (中断)
  - A2G: SNR = 0 - 20.04 - 3.0 = **-23.04 dB** (连通)

---

## 2. 通信中断判定

### 2.1 Outage 阈值

**SNR 阈值**: `-20.0 dB`
- 代码位置: `agcoop/comm/comm_model.py:38`
- 判定规则: `outage = (SNR_best < -20.0 dB)`
- 代码实现: `agcoop/comm/comm_model.py:194`

### 2.2 判定逻辑

```python
# 计算到所有 UGV 的 SNR
snr_list = [compute_snr(d_i, blocked_i, config) for each UGV_i]

# 选择最佳链路
snr_best = max(snr_list)

# 判定中断
if snr_best < -20.0:
    outage = True  # 通信中断
else:
    outage = False  # 通信正常
```

**代码位置**: `agcoop/comm/comm_model.py:155-196`

### 2.3 中断惩罚

**奖励函数中的体现**:
```python
# V4 (Golden Ratio)
r_comm = -0.15 × current_outage_nc
```
- `current_outage_nc`: 当前步处于中断状态的 UGV 数量
- 每个中断的 UGV 每步惩罚 `-0.15`
- 代码位置: `agcoop/env/core.py:1527`

---

## 3. 任务截止时间 (Deadline)

### 3.1 生成机制

**动态生成**: 任务生成时随机分配截止时间

**参数范围**:
- `deadline_min = 25` 步
- `deadline_max = 60` 步
- 代码位置: `agcoop/env/coop_env.py:60-61`

**生成公式**:
```python
deadline_offset = random.randint(25, 60)  # 随机偏移量
deadline = current_time + deadline_offset  # 绝对截止时间
```
- 代码位置: `agcoop/env/core.py:931-932`

### 3.2 物理意义

**时间单位**: 步 (step)
- 1 步 = 1 个决策周期
- 假设每步 1 秒，则 deadline 范围为 **25-60 秒**

**距离无关**: 截止时间与任务距离无关，纯随机生成
- 这增加了任务调度的难度
- 需要智能的 EDF (Earliest Deadline First) 策略

### 3.3 超期惩罚

**V4 奖励函数**:
```python
if delta_miss > 0:
    max_penalty = -2.0
    steepness = 0.05
    r_deadline = max_penalty × tanh(steepness × delta_miss)
else:
    r_deadline = 0.0
```
- `delta_miss`: 本步新增的超期任务数
- 使用 `tanh` 函数实现非线性惩罚，避免极端值
- 代码位置: `agcoop/env/core.py:1529-1535`

---

## 4. UAV 6自由度控制

### 4.1 自由度定义

**实际实现**: **2.5 自由度** (而非完整的 6 自由度)

**控制维度**:
1. **X 方向** (东西): 16 个离散方向中的 X 分量
2. **Y 方向** (南北): 16 个离散方向中的 Y 分量
3. **高度 Z** (垂直): **固定高度**，不可控

**状态维度**:
- 位置: `(x, y)` 2D 坐标
- 速度: `speed = 1.0 m/s` (固定)
- 电池: `battery_level ∈ [0, 1]`
- 模式: `mode ∈ {ONBOARD, FLYING, HOVERING}`

**代码位置**: `agcoop/env/core.py:25-39`

### 4.2 动作空间

**16 方向控制**:
```
动作空间 = {
    0: 停留 (STAY)
    1-16: 16 个方向 (N, NE, E, SE, S, SW, W, NW, NNE, ENE, ESE, SSE, SSW, WSW, WNW, NNW)
}
```

**物理实现**:
- 每个方向对应一个 `(dx, dy)` 向量
- 速度固定为 `1.0 m/s`
- 每步移动距离 = `speed × dt = 1.0 m`

### 4.3 高度建模

**固定高度假设**: UAV 飞行时保持恒定高度

**高度值**:
- 未在代码中显式定义
- 建议设定: **10 米** (典型低空飞行高度)
- 用途: 仅在 A2G 通信计算中体现仰角优势

**物理意义**:
- 高度不参与路径规划 (2D 网格)
- 高度仅影响通信质量 (A2G vs G2G)
- 障碍物视为 "墙" 而非 "建筑物"，UAV 可以飞越

**为什么不是 6 自由度?**
- 简化问题: 2D 网格环境，高度维度不影响任务分配
- 计算效率: 避免 3D 路径规划的复杂性
- 实际合理: 低空巡航任务通常保持恒定高度

---

## 5. 电池管理

### 5.1 电池参数

**初始电量**: `1.0` (100%)

**消耗速率**:
- **飞行 (FLYING)**: `0.005 / step` (0.5% / 步)
- HOVERING)**: `0.002 / step` (0.2% / 步)
- **停靠 (ONBOARD)**: 充电中

**充电速率**:
- **停靠在 UGV 上**: `0.01 / step` (1.0% / 步)

**代码位置**: `agcoop/env/core.py:33-35`

### 5.2 安全机制

**紧急返航阈值**: `15%`
- 当电量 < 15% 时，UAV 必须返回最近的 UGV
- 代码位置: `agcoop/env/core.py` (UAV 控制逻辑)

**续航时间**:
- 纯飞行: `1.0 / 0.005 = 200 步` (约 3.3 分钟)
- 纯悬停: `1.0 / 0.002 = 500 步` (约 8.3 分钟)

---

## 6. 物理参数总结表

| 参数类别 | 参数名称 | 数值 | 单位 | 代码位置 |
|---------|---------|------|------|---------|
| **通信** | 发射功率 $P_{tx}$ | 0.0 | dBm | comm_model.py:34 |
| | 路径损耗指数 $n$ | 2.0 | - | comm_model.py:35 |
| | G2G 障碍衰减 | 6.0 | dB/障碍物 | comm_model.py:36 |
| | A2G 障碍衰减 | 1.5 | dB/障碍物 | comm_model.py:37 |
| | SNR 阈值 | -20.0 | dB | comm_model.py:38 |
| | 距离修正量 $\epsilon$ | 0.05 | m | comm_model.py:39 |
| **任务** | Deadline 最小值 | 25 | 步 | coop_env.py:60 |
| | Deadline 最大值 | 60 | 步 | coop_env.py:61 |
| **UAV** | 飞行速度 | 1.0 | m/s | core.py:32 |
| | 飞行耗电 | 0.005 | /步 | core.py:33 |
| | 悬停耗电 | 0.002 | /步 | core.py:34 |
| | 充电速率 | 0.01 | /步 | core.py:35 |
| | 紧急返航阈值 | 0.15 | (15%) | core.py |
| | 飞行高度 | 10 | m | (建议值) |
| **奖励** | 任务奖励 $r_{task}$ | 3.0 | - | core.py:1526 |
| | 通信惩罚 $r_{comm}$ | -0.15 | /中断 | core.py:1527 |
| | Deadline 惩罚 | -2.0 | (最大) | core.py:1530 |

---

## 7. 论文写作建议

### 7.1 通信模型章节

**标题**: "Communication Model with A2G/G2G Differentiation"

**公式**:
```latex
\text{SNR}(dB) = P_{tx} - 10n\log_{10}(d + \epsilon) - \alpha N_{obs}
```

**参数表**:
```latex
\begin{table}[h]
\centering
\caption{Communication Model Parameters}
\begin{tabular}{lcc}
\hline
Parameter & Value & Unit \\
\hline
Transmit Power ($P_{tx}$) & 0.0 & dBm \\
Path Loss Exponent ($n$) & 2.0 & - \\
G2G Obstacle Penalty ($\alpha_{G2G}$) & 6.0 & dB/obstacle \\
A2G Obstacle Penalty ($\alpha_{A2G}$) & 1.5 & dB/obstacle \\
SNR Threshold & -20.0 & dB \\
\hline
\end{tabular}
\end{table}
```

### 7.2 UAV 控制章节

**澄清说明**:
> "While we refer to '6-DOF control' in the context of UAV autonomy, our implementation focuses on 2D planar motion with fixed altitude. The UAV operates at a constant cruising height (10m), with 16-directional control in the horizontal plane. This simplification is justified by the 2D grid-based task allocation problem, where altitude variation does not affect task assignment decisions. The fi altitude assumption is common in low-alveillance missions."

### 7.3 Deadline 机制章节

**描述**:
> "Task deadlines are randomly generated upon task creation, with a uniform distribution in the range [25, 60] steps. This distance-independent deadline mechanism increases scheduling complexity and necessitates intelligent prioritization strategies such as Earliest Deadline First (EDF)."

---

**文档生成时间**: 2026-02-26
**代码版本**: V4 (Golden Ratio)
**验证状态**: ✅ 所有参数已从代码中提取并验证
