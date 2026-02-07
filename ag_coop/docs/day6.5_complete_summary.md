# Day6.5: MAPF 集成到 core.py - 完整总结

## 概述

Day6.5 的目标是将 Day6 验证的 MAPF 功能集成到 `core.py` 环境中，实现生产级的 UGV 路径规划。采用**最小侵入、渐进式集成**的策略，分 4 个步骤完成。

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        AGCoopEnv (core.py)                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  reset()                                              │  │
│  │    - 初始化 UGVMAPFWrapper                            │  │
│  │    - 初始化 UGVRecedingHorizonMAPFController          │  │
│  │    - 执行初始规划 (t=0)                               │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  step()                                               │  │
│  │    - 调用 controller.maybe_replan(t, positions)       │  │
│  │    - 调用 controller.step(t, positions)               │  │
│  │    - 更新 UGV 位置                                     │  │
│  │    - 记录 MAPF 信息到 trace                           │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  _save_final_metrics()                                │  │
│  │    - 从 controller 获取统计信息                        │  │
│  │    - 保存到 metrics.json                              │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │  UGVRecedingHorizonMAPFController     │
        │  ┌─────────────────────────────────┐  │
        │  │  maybe_replan(t, starts)        │  │
        │  │    - 判断是否决策步 (t % K == 0)│  │
        │  │    - 调用 wrapper.plan()        │  │
        │  │    - 缓存路径或触发 fallback    │  │
        │  └─────────────────────────────────┘  │
        │  ┌─────────────────────────────────┐  │
        │  │  step(t, current_positions)     │  │
        │  │    - 从缓存读取下一步动作       │  │
        │  │    - 或执行 fallback WAIT       │  │
        │  │    - 碰撞检测                   │  │
        │  └─────────────────────────────────┘  │
        └───────────────────────────────────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  UGVMAPFWrapper       │
                │  ┌─────────────────┐  │
                │  │  plan()         │  │
                │  │    - 调用 MAPF  │  │
                │  │    - 返回结果   │  │
                │  └─────────────────┘  │
                └───────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  MAPFPlanner  │
                    │  (Space-Time  │
                    │   A* + CBS)   │
                    └───────────────┘
```

## 四个步骤详解

### Step 0: UGV MAPF Wrapper（接口封装）

**目标：** 创建简洁的 MAPF 接口，隔离底层实现细节

**实现：**
- 文件：`agcoop/mapf/ugv_wrapper.py`
- 类：`UGVMAPFWrapper`
- 接口：`plan(starts, goals, H, budget_ms) -> UGVMAPFResult`

**关键设计：**
```python
class UGVMAPFResult:
    success: bool
    paths: Optional[Dict[int, List[Tuple[int, int]]]]
    plan_time_ms: float
    expanded_nodes: int
    termination_reason: str

class UGVMAPFWrapper:
    def plan(self, starts, goals, H, budget_ms):
        # 调用 MAPFPlanner
        # 返回简化的结果
```

**验收：** ✓ 4 个测试通过（基本功能、超时、多次调用、向后兼容）

---

### Step 1: Controller 逻辑提取（可复用组件）

**目标：** 将 Day6 的控制逻辑提取为可复用的 Controller 类

**实现：**
- 文件：`agcoop/controllers/ugv_mapf_controller.py`
- 类：`UGVRecedingHorizonMAPFController`

**5 个核心机制：**
1. **每 K 步规划：** `maybe_replan()` 判断 `t % K == 0`
2. **缓存执行：** 非决策步从 `path_cache` 读取动作
3. **失败 WAIT：** MAPF 失败时触发 `fallback_wait_remaining = K`
4. **在线碰撞检查：** `step()` 检测 vertex/edge collision
5. **动态目标切换：** `set_goals()` 支持运行时更新目标

**关键方法：**
```python
def reset(starts, goals):
    # 重置状态和统计

def maybe_replan(t, starts, goals=None) -> PlanInfo:
    # 判断是否需要规划
    # 调用 wrapper.plan()
    # 缓存路径或触发 fallback

def step(t, current_positions) -> StepInfo:
    # 从缓存读取下一步
    # 或执行 fallback WAIT
    # 碰撞检测

def get_stats() -> Dict:
    # 返回统计信息
```

**验收：** ✓ 3 个测试通过（基本功能、fallback、目标切换）+ 一致性验证

---

### Step 2: 最小侵入集成（初始化）

**目标：** 在 `core.py` 中挂载 controller，不改变现有行为

**实现：**
- 在 `__init__()` 中读取 MAPF 配置
- 在 `reset()` 中初始化 wrapper 和 controller
- 设置初始 starts 和 goals

**关键代码：**
```python
# __init__
self.mapf_enabled = config.get('mapf', {}).get('enabled', False)
self.ugv_controller = None
self.mapf_wrapper = None

# reset()
if self.mapf_enabled and self.grid_map is not None:
    self.mapf_wrapper = UGVMAPFWrapper(...)
    self.ugv_controller = UGVRecedingHorizonMAPFController(...)

    starts = {i: grid_map.world_to_cell(...) for ...}
    goals = {...}  # 地图中心附近的巡逻点

    self.ugv_controller.reset(starts, goals)
```

**验收：** ✓ 3 个测试通过（禁用回归、启用初始化、无地图）

---

### Step 3: UGV 动作生成（Receding Horizon 执行）

**目标：** 在 `step()` 中调用 controller，实现 UGV 移动

**实现：**
1. **step() 中调用 controller**
2. **_log_step() 记录 MAPF 信息**
3. **_save_final_metrics() 保存统计**
4. **reset() 中执行初始规划**
5. **采样不同的起始位置**

**关键代码：**
```python
# step()
if self.ugv_controller is not None:
    # 1. 获取当前位置（cell 坐标）
    current_positions = {i: grid_map.world_to_cell(...) for ...}

    # 2. 尝试重规划
    mapf_plan_info = self.ugv_controller.maybe_replan(t, current_positions)

    # 3. 执行一步
    mapf_step_info = self.ugv_controller.step(t, current_positions)

    # 4. 检查碰撞
    if not mapf_step_info.collision_free:
        raise RuntimeError(...)

    # 5. 更新位置（world 坐标）
    new_ugv_positions = [grid_map.cell_to_world(...) for ...]
    self.state.ugv_positions = new_ugv_positions
```

**验收：** ✓ 3 个测试通过（Receding Horizon、禁用回归、移动行为）

---

## 关键技术决策

### 1. 接口设计：Wrapper 模式
- **问题：** MAPFPlanner 接口复杂，返回值多
- **方案：** 创建 UGVMAPFWrapper 封装，提供简洁接口
- **优点：** core.py 不依赖 MAPF 实现细节，易于替换

### 2. 控制逻辑：Controller 模式
- **问题：** Day6 的控制逻辑散落在测试脚本中
- **方案：** 提取为 UGVRecedingHorizonMAPFController 类
- **优点：** 可复用、可测试、易维护

### 3. 集成策略：渐进式、最小侵入
- **问题：** 一次性集成风险高，难以调试
- **方案：** 分 4 步，每步独立验收
- **优点：** 每步可回滚，问题定位清晰

### 4. 初始规划：reset() 时执行
- **问题：** 第一次 step() 时 t=1，不满足 t % K == 0，无缓存路径
- **方案：** 在 reset() 中调用 `maybe_replan(0, starts)`
- **优点：** 确保第一步就有路径可执行

### 5. 起始位置：采样不同空闲格子
- **问题：** 所有 UGV 从 (0, 0) 开始，导致碰撞和 no_path
- **方案：** MAPF 启用时，从地图中随机采样不同空闲位置
- **优点：** 避免初始碰撞，提高规划成功率

### 6. 坐标转换：world ↔ cell
- **问题：** 环境使用 float world 坐标，MAPF 使用 int cell 坐标
- **方案：** 在 step() 中转换：world_to_cell() 和 cell_to_world()
- **优点：** 保持接口一致性

---

## 测试覆盖

### Step 0 测试（ugv_wrapper）
- ✓ 基本功能：成功规划
- ✓ 超时处理：budget=0ms
- ✓ 多次调用：连续规划
- ✓ 向后兼容：与 Day6 一致

### Step 1 测试（ugv_controller）
- ✓ 基本功能：K 步规划、缓存执行
- ✓ Fallback 机制：失败 WAIT
- ✓ 动态目标切换：set_goals()
- ✓ 一致性验证：与 Day6 输出一致

### Step 2 测试（core_mapf_integration）
- ✓ MAPF 禁用：回归保护
- ✓ MAPF 启用：controller 初始化
- ✓ 无地图：controller 不初始化

### Step 3 测试（step3_receding_horizon）
- ✓ Receding Horizon 执行：调用频率、缓存执行
- ✓ MAPF 禁用：回归保护
- ✓ UGV 移动行为：位置更新

**总计：** 14 个测试，全部通过 ✓

---

## 性能指标

### 测试场景：map_01 (20x20), 3 agents, 50 steps, K=5, H=40

**MAPF 调用：**
- 调用次数：11 次（1 次初始 + 10 次后续）
- 成功率：100% (11/11)
- 平均规划时间：132.32 ms
- P95 规划时间：< 150 ms

**UGV 移动：**
- 移动步数：10/30 (33%)
- Fallback 比例：0%
- 碰撞检测：✓ 通过

**日志记录：**
- Trace：50 行，包含 MAPF 信息
- Metrics：完整统计信息

---

## 配置示例

### default.yaml
```yaml
episode:
  horizon_steps: 500
  decision_period: 5   # K
  map_path: "maps/map_01.map"
  seed: 0

mapf:
  enabled: false       # 启用/禁用 MAPF
  H: 10                # 规划视野
  time_budget_ms: 1000 # 时间预算
  connectivity: 4      # 4 或 8 邻接
  priority: "carrier_first"
```

### 启用 MAPF
```python
config['mapf']['enabled'] = True
config['mapf']['H'] = 40
config['mapf']['time_budget_ms'] = 300

env = AGCoopEnv(config, output_dir='outputs/run1', enable_logging=True)
```

---

## 输出示例

### Trace (trace.jsonl)
```json
{
    "t": 5,
    "ugv_pos": [[2.1, 1.3], [2.1, 2.5], [1.9, 1.3]],
    "decision_step": true,
    "mapf_called": true,
    "mapf_success": true,
    "mapf_plan_time_ms": 135.42,
    "mapf_fallback": false,
    ...
}
```

### Metrics (metrics.json)
```json
{
    "mapf_calls": 11,
    "mapf_success_calls": 11,
    "mapf_timeout_calls": 0,
    "mapf_mean_plan_time_ms": 132.32,
    "fallback_wait_steps": 0,
    ...
}
```

---

## 文件清单

### 新增文件
- `agcoop/mapf/ugv_wrapper.py` - UGV MAPF Wrapper
- `agcoop/controllers/ugv_mapf_controller.py` - Receding Horizon Controller
- `agcoop/controllers/__init__.py` - Controllers 模块

### 修改文件
- `agcoop/env/core.py` - 集成 MAPF controller
- `agcoop/mapf/__init__.py` - 导出 UGVMAPFWrapper

### 测试文件
- `scripts/test_ugv_wrapper.py` - Step 0 测试
- `scripts/test_ugv_controller.py` - Step 1 测试
- `scripts/test_controller_consistency.py` - Step 1 一致性验证
- `scripts/test_core_mapf_integration.py` - Step 2 测试
- `scripts/test_step3_receding_horizon.py` - Step 3 测试

### 文档
- `docs/day6.5_step0_summary.md` - Step 0 总结
- `docs/day6.5_step1_summary.md` - Step 1 总结
- `docs/day6.5_step2_summary.md` - Step 2 总结
- `docs/day6.5_step3_summary.md` - Step 3 总结
- `docs/day6.5_complete_summary.md` - 本文档

---

## 后续工作

### 短期（Day7）
1. **动态目标切换：** 根据任务/会合点更新 goals
2. **UAV 路径规划：** 集成 UAV 的 A* 规划
3. **任务分配：** 实现任务分配逻辑

### 中期优化
1. **参数调优：** K、H、budget 的最优配置
2. **Fallback 改进：** 更智能的失败处理策略
3. **性能优化：** 减少规划时间，提高成功率

### 长期扩展
1. **多场景测试：** 不同地图、不同 agent 数量
2. **在线重规划：** 动态障碍物、agent 故障
3. **学习增强：** 使用 RL/IL 改进规划策略

---

## 经验总结

### 成功经验
1. **渐进式集成：** 分步验收，降低风险
2. **接口隔离：** Wrapper 和 Controller 模式，解耦清晰
3. **测试驱动：** 每步都有完整测试，问题早发现
4. **文档同步：** 每步都有总结文档，便于回顾

### 遇到的问题
1. **初始规划时机：** 需要在 reset() 时执行，而非第一次 step()
2. **起始位置冲突：** 多个 agent 同一位置导致 no_path
3. **坐标转换：** world 和 cell 坐标需要仔细转换
4. **字段名不一致：** trace 中是 `ugv_pos` 不是 `ugv_positions`

### 关键教训
1. **时间步语义：** 理解 t 的增长时机很重要
2. **状态初始化：** 确保初始状态合法（无碰撞）
3. **接口一致性：** 统一命名规范，避免混淆
4. **测试覆盖：** 边界情况（禁用、无地图、失败）都要测试

---

## 验收标准

### 功能验收
- ✓ MAPF 启用时，UGV 按规划路径移动
- ✓ MAPF 禁用时，环境行为与 Day1 一致
- ✓ 调用频率：1 + ceil(steps / K)
- ✓ 缓存执行：非决策步不调用 MAPF
- ✓ 碰撞检测：无碰撞发生
- ✓ 日志记录：trace 和 metrics 完整

### 性能验收
- ✓ 成功率 ≥ 70%（实际 100%）
- ✓ 平均规划时间 < 200ms（实际 132ms）
- ✓ Fallback 比例 ≤ 50%（实际 0%）

### 代码质量
- ✓ 最小侵入：core.py 改动集中在 4 个方法
- ✓ 向后兼容：MAPF 禁用时无影响
- ✓ 测试覆盖：14 个测试全部通过
- ✓ 文档完整：每步都有总结文档

---

## 结论

Day6.5 成功将 MAPF 集成到 core.py，实现了生产级的 UGV 路径规划功能。通过渐进式、最小侵入的策略，确保了集成的稳定性和可维护性。所有测试通过，性能指标优秀，为后续的 Day7+ 工作奠定了坚实基础。

**Day6.5 完成标志：**
- ✓ Step 0: UGV MAPF Wrapper
- ✓ Step 1: Controller 逻辑提取
- ✓ Step 2: 最小侵入集成
- ✓ Step 3: UGV 动作生成

**下一步：Day7 - 动态任务与会合点集成**
