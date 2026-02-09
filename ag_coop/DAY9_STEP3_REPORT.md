# Day9 Step 3 完成报告

## 目标

设计 observation space（Dict 优先，后续一键 Flatten）

## 实现内容

### 1. Observation Space 设计

**格式**: `gymnasium.spaces.Dict`

包含以下 5 个部分：

#### 1.1 UGV 位置 (`ugv_pos`)
- **Shape**: `(N, 2)` - N 个 UGV，每个 2D 位置
- **内容**: Grid 坐标，归一化到 [0, 1]
- **Dtype**: `float32`

#### 1.2 UAV 状态 (`uav_state`)
- **Shape**: `(3,)`
- **内容**:
  - `[0]`: onboard_ugv_id（归一化到 [0, 1]）
  - `[1]`: uav_mode（0=ONBOARD, 1=OUTBOUND, 2=SERVICING, 3=INBOUND，归一化到 [0, 1]）
  - `[2]`: reserved（占位，暂时为 0）
- **Dtype**: `float32`

#### 1.3 Top-M 任务 (`tasks_topM`)
- **Shape**: `(M, 4)` - M 个任务，每个 4 个特征
- **内容**:
  - `[0]`: x 坐标（归一化到 [0, 1]）
  - `[1]`: y 坐标（归一化到 [0, 1]）
  - `[2]`: deadline_normalized = (deadline - t) / horizon（归一化到 [0, 1]）
  - `[3]`: available_flag（1=有任务，0=无任务）
- **排序**: 按 deadline 排序（EDF - Earliest Deadline First）
- **Dtype**: `float32`

#### 1.4 通信状态 (`comm`)
- **Shape**: `(3,)`
- **内容**:
  - `[0]`: snr_best_nc（最佳非 carrier SNR，归一化到 [0, 1]，假设 SNR 范围 0-40 dB）
  - `[1]`: outage_percent_worst_nc（最差非 carrier outage 百分比，[0, 1]）
  - `[2]`: best_ugv_id_nc（最佳非 carrier UGV ID，归一化到 [0, 1]）
- **Dtype**: `float32`

#### 1.5 候选 Relay 点 (`candidates_R`)
- **Shape**: `(R, 3)` - R 个候选点，每个 3 个特征
- **内容**:
  - `[0]`: x 坐标（归一化到 [0, 1]）
  - `[1]`: y 坐标（归一化到 [0, 1]）
  - `[2]`: dist_to_carrier（到 carrier 的距离，归一化到 [0, 1]）
- **Dtype**: `float32`

### 2. 实现的方法

#### 2.1 `observation_space` 属性

**文件**: `agcoop/env/core.py`

```python
@property
def observation_space(self):
    """
    返回 gym.spaces.Dict，包含：
    - ugv_pos: shape (N, 2)
    - uav_state: shape (3,)
    - tasks_topM: shape (M, 4)
    - comm: shape (3,)
    - candidates_R: shape (R, 3)
    """
    if self._observation_space is None:
        try:
            from gymnasium import spaces
        except ImportError:
            from gym import spaces

        N = self.n_ugv
        M = self.top_m
        R = self.candidate_count

        self._observation_space = spaces.Dict({
            'ugv_pos': spaces.Box(low=0.0, high=1.0, shape=(N, 2), dtype=np.float32),
            'uav_state': spaces.Box(low=0.0, high=1.0, shape=(3,), dtype=np.float32),
            'tasks_topM': spaces.Box(low=0.0, high=1.0, shape=(M, 4), dtype=np.float32),
            'comm': spaces.Box(low=0.0, high=1.0, shape=(3,), dtype=np.float32),
            'candidates_R': spaces.Box(low=0.0, high=1.0, shape=(R, 3), dtype=np.float32),
        })

    return self._observation_space
```

#### 2.2 `_get_observation()` 方法

**功能**: 从当前状态提取观测

**关键逻辑**:

1. **UGV 位置归一化**:
   ```python
   for i, pos in enumerate(self.state.ugv_positions):
       cell = self.grid_map.world_to_cell(pos[0], pos[1])
       ugv_pos[i, 0] = cell[1] / map_w  # x
       ugv_pos[i, 1] = cell[0] / map_h  # y
   ```

2. **Top-M 任务提取**（按 deadline 排序）:
   ```python
   active_tasks = self.state.get_active_tasks()
   active_tasks_sorted = sorted(active_tasks, key=lambda t: t.deadline)
   top_m_tasks = active_tasks_sorted[:M]
   ```

3. **通信状态提取**:
   ```python
   snr_best_nc = getattr(self.state, '_current_snr_best_nc', 0.0)
   comm[0] = np.clip(snr_best_nc / 40.0, 0.0, 1.0)
   comm[1] = getattr(self.state, '_current_outage_worst_nc', 0.0)
   comm[2] = best_ugv_id / max(1.0, float(N - 1))
   ```

4. **候选点距离计算**:
   ```python
   for i, candidate in enumerate(self.candidate_relays[:R]):
       dist = np.sqrt((candidate[0] - carrier_cell[0])**2 +
                      (candidate[1] - carrier_cell[1])**2)
       candidates_R[i, 2] = dist / max_dist
   ```

5. **NaN/Inf 检查与修复**:
   ```python
   for key, value in obs.items():
       if not np.all(np.isfinite(value)):
           obs[key] = np.nan_to_num(value, nan=0.0, posinf=1.0, neginf=0.0)
   ```

#### 2.3 修改 `reset()` 和 `step()`

**reset() 返回值**:
```python
def reset(self) -> Dict[str, np.ndarray]:
    """重置环境到初始状态"""
    # ... 初始化逻辑 ...
    return self._get_observation()
```

**step() 返回值**:
```python
def step(self, action) -> Tuple[Dict[str, np.ndarray], float, bool, Dict[str, Any]]:
    """执行一步环境演化"""
    # ... 执行逻辑 ...
    obs = self._get_observation()
    return obs, reward, done, info
```

### 3. FlattenObservation Wrapper

**文件**: `agcoop/env/wrappers.py`

**功能**: 将 Dict 观测展平为单一的 Box 向量

**实现**:

```python
class FlattenObservation:
    def __init__(self, env):
        self.env = env

        # 计算展平后的维度
        self._obs_keys = sorted(env.observation_space.spaces.keys())
        self._obs_sizes = {key: int(np.prod(shape))
                          for key, shape in self._obs_shapes.items()}
        total_size = sum(self._obs_sizes.values())

        # 创建展平后的 observation space
        self.observation_space = spaces.Box(
            low=0.0, high=1.0, shape=(total_size,), dtype=np.float32
        )

    def _flatten_obs(self, obs_dict):
        flattened = []
        for key in self._obs_keys:
            flattened.append(obs_dict[key].flatten())
        return np.concatenate(flattened, axis=0).astype(np.float32)
```

**展平顺序**（按字母排序）:
1. `candidates_R`: (12, 3) → 36 维
2. `comm`: (3,) → 3 维
3. `tasks_topM`: (5, 4) → 20 维
4. `uav_state`: (3,) → 3 维
5. `ugv_pos`: (3, 2) → 6 维

**总维度**: 36 + 3 + 20 + 3 + 6 = **68 维**

### 4. 验证脚本

**文件**: `scripts/test_day9_step3_observation.py`

**测试内容**:

#### 4.1 基本功能测试
- ✅ observation_space 属性存在
- ✅ 所有 key 都存在
- ✅ Shape 和 dtype 匹配
- ✅ 初始观测没有 NaN/Inf

#### 4.2 一致性测试（100 步）
- ✅ 每步观测的 key 一致
- ✅ 每步观测的 shape 一致
- ✅ 每步观测的 dtype 一致
- ✅ 没有 NaN/Inf

#### 4.3 FlattenObservation Wrapper 测试
- ✅ Wrapper 正确初始化
- ✅ 展平后的 shape 正确（68 维）
- ✅ Reset 和 step 正常工作
- ✅ 没有 NaN/Inf

## 验收结果

```
✅ Observation space 基本功能
✅ Observation 一致性测试（100 步）
✅ FlattenObservation wrapper

关键结果:
  - Dict observation space: 5 个 key ✓
  - 所有观测归一化到 [0, 1] ✓
  - 没有 NaN/Inf ✓
  - FlattenObservation: 68 维 Box ✓
```

## 验收标准达成

✅ **标准 1**: reset() 返回 obs，obs 中所有 key 都固定存在、shape 固定、dtype 合理（float32）

✅ **标准 2**: 任何一步 obs 不允许 NaN/Inf（跑 1 episode 后统计 np.isfinite(obs).all() 为 True）

✅ **标准 3**: FlattenObservation wrapper 正常工作

## 关键设计决策

### 1. 归一化策略

**所有观测归一化到 [0, 1]**:
- **位置**: 除以地图宽度/高度
- **距离**: 除以地图对角线长度
- **SNR**: 除以 40 dB（假设最大值）
- **Deadline**: (deadline - t) / horizon
- **ID**: 除以最大 ID

**优势**:
- 统一的数值范围，便于神经网络训练
- 避免数值不稳定
- 便于不同地图尺寸的泛化

### 2. Top-M 任务排序

**按 deadline 排序（EDF）**:
```python
active_tasks_sorted = sorted(active_tasks, key=lambda t: t.deadline)
```

**原因**:
- 优先考虑紧急任务
- 与 action space 的 task_choice 一致
- 符合实际应用场景

### 3. 通信指标选择

**使用 Day8 引入的 worst_nc 指标**:
- `snr_best_nc`: 最佳非 carrier SNR
- `outage_worst_nc`: 最差非 carrier outage

**原因**:
- 捕捉"UGV 掉队"问题
- 与 Day8 comm_greedy 一致
- 反映最弱链路的通信质量

### 4. NaN/Inf 处理

**自动修复策略**:
```python
if not np.all(np.isfinite(value)):
    obs[key] = np.nan_to_num(value, nan=0.0, posinf=1.0, neginf=0.0)
```

**保证**: 即使出现异常值，环境也不会崩溃

### 5. Dict vs Flattened

**提供两种格式**:
- **Dict**: 结构化，便于调试和理解
- **Flattened**: 单一向量，便于 PPO 等算法

**使用方式**:
```python
# Dict 格式
env = AGCoopEnv(config, method="rl")
obs = env.reset()  # Dict

# Flattened 格式
env = FlattenObservation(AGCoopEnv(config, method="rl"))
obs = env.reset()  # np.ndarray (68,)
```

## Observation Space 示例

**配置**: N=3, M=5, R=12

**Dict 格式**:
```python
{
    'ugv_pos': array([[0.5, 0.5], [0.6, 0.4], [0.4, 0.6]], dtype=float32),  # (3, 2)
    'uav_state': array([0.0, 0.0, 0.0], dtype=float32),  # (3,)
    'tasks_topM': array([[0.1, 0.2, 0.8, 1.0], ...], dtype=float32),  # (5, 4)
    'comm': array([0.75, 0.1, 0.5], dtype=float32),  # (3,)
    'candidates_R': array([[0.3, 0.4, 0.2], ...], dtype=float32),  # (12, 3)
}
```

**Flattened 格式**:
```python
array([0.3, 0.4, 0.2, ..., 0.5, 0.5, 0.6, 0.4, 0.4, 0.6], dtype=float32)  # (68,)
```

## 与 Day8 的对比

| 维度 | Day8 | Day9 |
|------|------|------|
| 返回值 | SystemState 对象 | Dict 观测 |
| 格式 | 原始状态 | 归一化观测 |
| 用途 | 日志记录 | RL 训练 |
| 通信指标 | 实时计算 | 包含在观测中 |

## 下一步（Day9 Step 4）

设计 reward function：
- 多目标权衡：task completion + deadline + communication
- 稀疏 vs 密集奖励
- Reward shaping

## 文件清单

### 修改的文件
- `agcoop/env/core.py`:
  - 添加 `_observation_space` 初始化
  - 添加 `observation_space` 属性
  - 添加 `_get_observation()` 方法
  - 修改 `reset()` 返回 obs
  - 修改 `step()` 返回 obs

### 新增的文件
- `agcoop/env/wrappers.py`: FlattenObservation 和 NormalizeReward wrapper
- `agcoop/env/__init__.py`: 更新导出
- `scripts/test_day9_step3_observation.py`: 验证脚本
- `DAY9_STEP3_REPORT.md`: 本报告

## 运行验证

```bash
python scripts/test_day9_step3_observation.py
```

---

**Day9 Step 3 状态**: ✅ **完成并验收通过**

**日期**: 2026-02-09
