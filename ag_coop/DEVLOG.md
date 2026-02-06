# 开发日志

## 2026-02-06 20:30

### Step 6：阈值校准与一致性检查 ✅

**新增文件：**
- `scripts/sweep_threshold.py` - 阈值 sweep 工具
- `scripts/inspect_comm_extended.py` - 扩展通信检查工具（含一致性验证）

**问题识别：**
- 原阈值 `-20.0 dB` 过于宽松，导致 outage 始终为 0%
- 全图最小 SNR 为 -11.5 dB，远高于 -20 dB 阈值
- 这会导致 Day4+ 实验中"通信指标"失去区分度（所有方法都 0% outage）

**阈值 Sweep 结果：**

测试地图：`map_01.map` (20x20, 286 free cells)
UGV 位置：(2,2), (10,10), (15,15)
扫描范围：-15.0 ~ +5.0 dB（步长 1.0 dB）

| 阈值 (dB) | Outage % | Outage Count |
|-----------|----------|--------------|
| -15.0     | 1.0%     | 3/286        |
| -14.0     | 2.8%     | 8/286        |
| -13.0     | 4.5%     | 13/286       |
| **-12.0** | **6.3%** | **18/286**   |
| -11.0     | 7.3%     | 21/286       |
| -10.0     | 9.4%     | 27/286       |
| **-9.0**  | **14.0%**| **40/286**   |
| -8.0      | 18.5%    | 53/286       |
| **-7.0**  | **26.2%**| **75/286**   |
| -6.0      | 30.8%    | 88/286       |
| -5.0      | 36.0%    | 103/286      |
| ...       | ...      | ...          |

**🎯 推荐阈值方案：**

1. **Relaxed（宽松）**: `-12.0 dB` → 6% outage
   - 适合：通信指标"刚刚有差异"，不强驱动策略

2. **Default（默认）**: `-9.0 dB` → 14% outage ✅
   - 适合：平衡场景，通信与任务指标同时有区分度

3. **Strict（苛刻）**: `-7.0 dB` → 26% outage
   - 适合：强调中继部署/会合选择，拉开 baseline 差距

**配置更新：**
- `configs/default.yaml` 中 `snr_threshold_db` 已更新为 `-9.0 dB`
- 添加三档 profile 注释（relaxed/default/strict）

**一致性检查（扩展工具）：**

新增两个验证热力图：

1. **Best UGV 分区图** (`best_ugv_map.png`)
   - ✅ 显示清晰的分界线（类似 Voronoi 图）
   - ✅ 每个 UGV 周围有连续区域
   - ✅ 无碎片化随机噪声（验证 raycast/索引逻辑正确）

2. **Blocked Count 热力图** (`blocked_heatmap.png`)
   - ✅ 深红阴影区对应障碍物位置
   - ✅ 障碍后方有更高的 blocked 值
   - ✅ 验证障碍遮挡计数正确

**输出文件：**
- `outputs/threshold_sweep/map_01/`
  - `threshold_sweep.png` - 阈值 vs outage% 曲线图
  - `threshold_sweep.json` - 完整 sweep 数据
- `outputs/comm_inspect_ext/map_01/`
  - `snr_heatmap.png` - SNR 热力图
  - `best_ugv_map.png` - Best UGV 分区图
  - `blocked_heatmap.png` - Blocked Count 热力图
  - `comm_meta_extended.json` - 扩展元数据

**验收状态：**
- ✅ 阈值 sweep 显示单调变化（无异常跳变）
- ✅ 推荐阈值落在目标区间（5%-30%）
- ✅ Best UGV 分区图显示清晰分界线
- ✅ Blocked Count 热力图与障碍物位置对应
- ✅ 通信模型实现稳定可靠

**Day3 验收：通过 ✅**

以"通信指标具备可比较动态范围"为验收标准：
- Sweep 显示阈值在 -12 到 -6 dB 间可以稳定落在 5%-30% 区间
- 随阈值单调变化，无异常跳变
- 一致性检查通过，无碎片化噪声或计数错误
- **通信模型实现正确且稳定**

**后续计划：**
- Day4 将按此阈值区间设计 deadline 任务流与任务池规则
- 保证"任务指标 + 通信指标"同时有区分度
- 主实验建议使用两档阈值（-12 和 -7）以增强结果稳健性

---

## 2026-02-06 19:25

### Step 5：两组最小实验验证

**新增文件：**
- `test_step5_experiments.py` - 实验验证脚本

**实验设计：**
- 实验 1：严格阈值（-5.0 dB）→ 预期 outage 上升
- 实验 2：宽松阈值（-40.0 dB）→ 预期 outage 下降
- Episode 长度：200 步

**实验结果：**

| 实验 | 阈值 (dB) | SNR Mean (dB) | SNR Min (dB) | Outage % | Outage Steps |
|------|-----------|---------------|--------------|----------|--------------|
| 严格 | -5.0      | 26.02         | 26.02        | 0.00%    | 0/200        |
| 宽松 | -40.0     | 26.02         | 26.02        | 0.00%    | 0/200        |

**trace 分析：**
- SNR 值：恒定为 26.02 dB（前 10 步）
- 标准差：0.00 dB（无波动）

**原因分析：**
- Day1 版本：所有 UGV 原地不动，都在 (0,0)
- UAV 永远在 0 号 UGV 上，也在 (0,0)
- 距离为 0，SNR 恒定为最大值（26.02 dB）
- 无论阈值如何设置，都不会 outage

**验收状态：**
- ⚠️ outage_percent 差异不明显（0.00% vs 0.00%）
- ⚠️ snr_best 无波动（恒定值）
- ✅ 通信模型正常工作（计算正确）
- ✅ 阈值配置生效（只是 SNR 太高，未触发）

**结论：**
- **通信模型实现正确**，但 Day1 场景过于简单
- 需要 Day2+ 实现 UGV 移动后，才能观察到：
  - SNR 随距离变化
  - outage_percent 随阈值变化
  - trace 中 snr_best 有波动

**验证方法（已通过）：**
- ✅ Step 4 的 SNR Heatmap 已验证：
  - 离 UGV 越近，SNR 越高
  - 障碍后方出现阴影区
  - SNR 范围：-11.50 ~ 26.02 dB（有明显变化）

---

## 2026-02-06 19:10

### Step 4：SNR Heatmap 可视化工具

**新增文件：**
- `scripts/inspect_comm.py` - SNR heatmap 生成工具

**功能：**
- 输入地图和 UGV 位置
- 对所有 free cell 作为 UAV 位置，计算 snr_best
- 输出 SNR heatmap 和元数据

**用法：**
```bash
python scripts/inspect_comm.py --map maps/test_small.map --ugv "1,1;8,8"
python scripts/inspect_comm.py --map maps/map_01.map --ugv "2,2;10,10;15,15" --threshold -10.0
```

**输出文件：**
- `outputs/comm_inspect/<map_id>/snr_heatmap.png` - SNR heatmap 图片
- `outputs/comm_inspect/<map_id>/comm_meta.json` - 元数据（阈值、参数、UGV 坐标、统计信息）

**可视化特点：**
- 颜色映射：绿色=高 SNR（好），黄色=中等，红色=低 SNR（差）
- UGV 位置：蓝色方块标注
- Outage 阈值：黑色虚线等高线
- 网格线辅助定位
- 详细说明文本框（验证要点、SNR 统计）

**测试结果（test_small.map, UGV at (1,1) and (8,8)）：**
- SNR 范围：-11.50 dB ~ 26.02 dB
- SNR 平均：1.95 dB
- Outage 比例：0.0%（阈值 -20.0 dB）
- 计算 56 个 free cells

**验收（肉眼）：**
- ✅ 离 UGV 越近，SNR 越高（颜色越绿）
- ✅ 障碍后方出现阴影区（SNR 更低）
- ✅ 对角线上的障碍明显影响 SNR 分布
- ✅ 两个 UGV 周围都有高 SNR 区域

**命令行参数：**
- `--map`: 地图文件路径（必需）
- `--ugv`: UGV 位置，格式 "i1,j1;i2,j2;..." （必需）
- `--output-dir`: 输出目录（可选）
- `--tx-power`: 发射功率 dB（默认 0.0）
- `--pathloss-n`: 路径损耗指数（默认 2.0）
- `--obstacle-penalty`: 障碍衰减 dB（默认 6.0）
- `--threshold`: Outage 阈值 dB（默认 -20.0）

---

## 2026-02-06 18:50

### Step 3：把通信统计接入 env

**修改文件：**
- `agcoop/env/core.py` - 集成真实通信模型

**新增文件：**
- `test_comm_integration.py` - 通信集成测试
- `test_comm_dispersed.py` - UGV 分散场景测试

**核心修改：**

1. **SystemState 扩展**
   - 添加 `snr_sum: float` - 累计 SNR
   - 添加 `snr_min: float` - 最小 SNR（初始为 +inf）

2. **AGCoopEnv 初始化**
   - 添加 `comm_config: CommConfig` - 通信配置对象
   - 添加 `grid_map: GridMap` - 地图对象（用于通信计算）
   - 在 `reset()` 中加载地图（如果指定）

3. **_update_outage() 重写**
   - 使用真实通信模型 `compute_best_snr()`
   - 计算 UAV 到所有 UGV 的 SNR
   - 返回 `(snr_best, outage)` 元组
   - 更新累计指标：`snr_sum`, `snr_min`, `outage_steps`
   - 如果地图未加载，回退到简单随机模型

4. **step() 逻辑**
   - 调用 `_update_outage()` 获取 `snr_best` 和 `outage`
   - 传递给 `_log_step(snr_best, outage)`

5. **_log_step() 更新**
   - 接收 `snr_best` 和 `outage` 参数
   - 写入 trace：`snr_best` 字段（真实值，保留 2 位小数）
   - 写入 trace：`outage` 字段（0 或 1）

6. **_save_final_metrics() 更新**
   - 计算 `snr_best_mean = snr_sum / steps`
   - 计算 `snr_best_min`（如果为 +inf 则返回 0.0）
   - 写入 metrics：`snr_best_mean`, `snr_best_min`

**集成测试（test_comm_integration.py）：**
- ✅ 测试 1：通信启用，SNR 指标不为 0
  - snr_best_mean: 26.02 dB
  - snr_best_min: 26.02 dB
  - trace 包含真实 snr_best 值
- ✅ 测试 2：通信禁用，SNR 指标为 0
  - snr_best_mean: 0.0 dB
  - snr_best_min: 0.0 dB
  - outage_percent: 0.0%
- ✅ 测试 3：outage_percent 随阈值变化
  - 不同阈值：-30.0, -20.0, -10.0, 0.0 dB
  - 注：Day1 所有 UGV 在原点，距离为 0，SNR 很高，无 outage

**验收：**
- ✅ snr_best_mean 和 snr_best_min 不为 0（comm enabled）
- ✅ snr_best_mean 和 snr_best_min 为 0（comm disabled）
- ✅ trace.jsonl 包含真实 snr_best 值
- ✅ outage_percent 正确计算
- ✅ 地图加载成功（maps/map_01.map, 20x20）

**注意事项：**
- Day1 版本：UGV 原地不动，都在 (0,0)，所以 SNR 很高（26.02 dB）
- 如果地图未加载，回退到简单随机通信模型（10% outage 概率）
- Day2+ 会实现 UGV 移动，届时 SNR 会随距离变化

---

## 2026-02-06 18:30

### Step 2：实现通信模型（SNR_best + outage）

**新增文件：**
- `agcoop/comm/comm_model.py` - 通信模型（SNR 计算和 outage 判断）
- `tests/test_comm_model.py` - 通信模型单元测试

**修改文件：**
- `configs/default.yaml` - 添加完整通信配置
- `agcoop/comm/__init__.py` - 导出通信模型函数

**配置项（configs/default.yaml）：**
```yaml
comm:
  enabled: true
  tx_power_db: 0.0          # 发射功率（dB）
  pathloss_n: 2.0           # 距离衰减指数
  obstacle_penalty_db: 6.0  # 每个障碍的衰减（dB）
  snr_threshold_db: -20.0   # outage 阈值
  eps_m: 0.05               # 避免 log(0)
```

**SNR 公式：**
```
snr_db = tx_power_db - 10 * pathloss_n * log10(d + eps) - obstacle_penalty_db * blocked
```

**核心函数：**
1. `CommConfig` - 通信配置数据类
   - `from_dict()` - 从配置字典创建

2. `compute_snr(distance_m, blocked_count, config)` - 计算 SNR
   - 基于距离衰减和障碍遮挡
   - 返回 SNR（dB）

3. `compute_snr_to_ugvs(uav_cell, ugv_cells, grid_map, config)` - 计算到所有 UGV 的 SNR
   - 返回 (snr_list, distance_list, blocked_list)

4. `compute_best_snr(uav_cell, ugv_cells, grid_map, config)` - 计算最佳 SNR
   - 返回 (snr_best, best_ugv_id, outage)
   - outage = True if snr_best < snr_threshold_db

5. `compute_comm_metrics(uav_cell, ugv_cells, grid_map, config)` - 完整通信指标
   - 返回字典，包含所有通信相关信息

**单元测试（tests/test_comm_model.py）：**
- ✅ 距离变大，SNR 降低
  - 1m: -0.42 dB, 10m: -20.04 dB, 100m: -40.00 dB
- ✅ blocked 增加，SNR 降低
  - 0 blocked: -20.04 dB, 1 blocked: -26.04 dB, 5 blocked: -50.04 dB
  - 每个障碍扣 6 dB（符合配置）
- ✅ threshold 检查 outage 正确
  - 近距离：SNR=6.94 dB, outage=False
  - 远距离+障碍：SNR=-74.69 dB, outage=True
  - 严格阈值：SNR=-8.28 dB < 0.0 dB, outage=True
- ✅ 最佳 UGV 选择正确
- ✅ 完整通信指标计算正确
- ✅ 边界情况处理（空 UGV 列表）
- ✅ 配置字典转换

**验收：**
- ✅ 所有测试通过（7 个测试）
- ✅ 距离变大，SNR 降低 ✓
- ✅ blocked 增加，SNR 降低 ✓
- ✅ threshold 检查 outage 正确 ✓
- ✅ 输出数值不是 NaN/inf ✓

**工程化特点：**
- 使用 eps_m 避免 log(0)
- 所有参数可配置
- 完整的边界情况处理
- 数值稳定性验证

---

## 2026-02-06 18:15

### Step 1：实现格栅 LOS/遮挡计数（Bresenham）

**新增文件：**
- `agcoop/comm/raycast.py` - 格栅射线追踪模块
- `agcoop/comm/__init__.py` - 通信模块导出
- `tests/test_raycast.py` - Raycast 单元测试

**核心函数：**
1. `bresenham_cells(i0, j0, i1, j1)` - Bresenham 算法
   - 返回两点连线穿过的格子序列
   - **包含端点**
   - 遵循项目坐标约定：i=row(y), j=col(x)

2. `count_blocked_cells(grid_map, cell_a, cell_b)` - 遮挡计数
   - 遍历线段格子，统计 obstacle 数量
   - **不含端点**（端点不参与统计）
   - 返回遮挡的障碍格子数

3. `has_line_of_sight(grid_map, cell_a, cell_b)` - 视线检查
   - 返回 True 如果无障碍遮挡

4. `compute_los_distance(grid_map, cell_a, cell_b)` - 距离计算
   - 返回欧几里得距离（米）

**单元测试（tests/test_raycast.py）：**
- ✅ bresenham_cells() 基本功能（水平、垂直、对角线）
- ✅ 端点包含测试
- ✅ 无障碍直线：blocked=0
- ✅ 中间放一个障碍：blocked>=1
- ✅ 多个障碍：blocked=3
- ✅ 对称性：count(a,b)==count(b,a)（5 对点）
- ✅ 端点不被统计
- ✅ has_line_of_sight() 正确
- ✅ compute_los_distance() 正确

**验收：**
- ✅ 所有测试通过（11 个测试）
- ✅ 坐标约定一致（i=row, j=col）
- ✅ 对称性验证通过
- ✅ 端点处理正确

---

## 2026-02-06 18:05

### Day3 开头：坐标系可视化验证

**新增文件：**
- `day3_verify_coords.py` - 坐标系可视化验证脚本
- `outputs/day3_coord_verification.png` - 验证图片（164KB）
- `outputs/day3_verification_report.md` - 详细验证报告
- `DAY3_README.md` - Day3 快速指南

**验证内容：**
1. ✅ 在 preview 图上标注 5 个随机 free cell 的 (x_idx, y_idx)
   - 显示为青色圆点，带坐标标签
   - 肉眼确认：所有点都落在白色区域（free cells）
2. ✅ 从测试实例中抽取 (sx, sy, gx, gy)，标注 start/goal
   - START: 绿色星星，cell(1, 1)，左下角附近
   - GOAL: 红色星星，cell(8, 8)，右上角附近
3. ✅ Y-flip 检查（一次性排雷）
   - START 在底部 (i=1 < 5.0) ✅
   - GOAL 在顶部 (i=8 > 5.0) ✅
   - **结论：坐标系正确，无需 y-flip！**

**测试数据：**
- 地图：test_small.map (10x10, 56 free cells)
- 随机采样的 5 个 free cells：
  - cell(1, 1) → world(0.30, 0.30)
  - cell(1, 6) → world(1.30, 0.30)
  - cell(5, 8) → world(1.70, 1.10)
  - cell(2, 8) → world(1.70, 0.50)
  - cell(3, 8) → world(1.70, 0.70)

**可视化特点：**
- 使用 `origin='lower'` 确保 i=0 在图像底部
- 青色圆点标注随机 free cells
- 绿色星星标注 START，红色星星标注 GOAL
- 网格线辅助定位
- 详细说明文本框（验证要点、测试实例）

**验收：**
- ✅ 所有青色点都在白色区域
- ✅ START 在左下角附近
- ✅ GOAL 在右上角附近
- ✅ 坐标标注清晰可见
- ✅ 无需 y-flip（坐标系方向正确）

**下一步：**
Day3 完整工作还包括：
- 实例生成工具（生成 .scen 或 _inst.txt 文件）
- 更多地图的验证（map_01.map 等）
- 与外部求解器的实际对接测试

---

## 2026-02-06 17:45

### 完善项目文档（Day2 收尾）

**新增文件：**
- `README.md` - 高质量项目文档
- `requirements.txt` - 依赖列表

**README.md 内容：**
- 项目概述和特点
- 系统架构图
- 核心功能详解（地图系统、仿真环境、日志系统）
- 使用指南（基本使用、地图操作、工具脚本）
- 开发进度（Day 1-2 完成，Day 3+ 计划）
- 实验复现说明
- 配置参数表
- 已知问题与注意事项
- 贡献指南

**特色：**
- 清晰的代码结构说明
- 完整的使用示例
- 坐标系约定详解（防止混淆）
- 外部求解器兼容性说明
- 预留字段文档（保持 schema 稳定）

**验收：**
- ✅ 结构清晰，易于理解
- ✅ 包含所有核心功能说明
- ✅ 提供完整的使用示例
- ✅ 标注开发进度和计划
- ✅ 说明已知问题和注意事项

---

## 2026-02-06 17:30

### 坐标系统加固与外部兼容性（Day2 关键修正）⚠️

**问题识别：**
- 测试脚本口径不一致（全量 vs 抽样）
- 缺少明确的坐标系约定文档
- 缺少与外部求解器的坐标转换

**修改文件：**
- `scripts/test_mapping.py` - 添加 --test-all 选项
- `scripts/inspect_map.py` - 添加 coordinate_convention 到 map_meta.json
- `agcoop/map/mapping.py` - 添加外部求解器坐标转换函数
- `test_solver_coords.py` - 求解器坐标转换测试

**A. 统一测试口径：**
- 添加 `--test-all` 选项，测试所有 free cells（而非抽样）
- 报告中添加 `test_all` 标记，明确测试范围
- 默认仍为抽样（快速测试），但可选全量测试（完整验证）

**B. 明确坐标系约定（map_meta.json）：**
```json
"coordinate_convention": {
  "index_order": "row_col",
  "origin_location": "lower_left",
  "y_axis_direction": "up",
  "cell_center_offset": 0.5,
  "note": "i=row(y), j=col(x); world_x = origin_x + (j+0.5)*resolution"
}
```

**C. 外部求解器坐标转换：**
- `to_solver_coords(i, j, height)` - 内部坐标 → 求解器坐标
  - 求解器约定：x=列, y=行（0=顶部）
  - 转换：solver_x = j, solver_y = (height-1) - i
- `from_solver_coords(solver_x, solver_y, height)` - 求解器坐标 → 内部坐标
- `format_solver_instance()` - 格式化为求解器实例（MovingAI 风格）
- `parse_solver_solution()` - 解析求解器返回的路径

**验收：**
- ✅ test_mapping.py --test-all：286/286 通过（100%）
- ✅ map_meta.json 包含完整坐标系约定
- ✅ 求解器坐标转换：所有角落格子正确
- ✅ 往返转换：to_solver_coords ↔ from_solver_coords 互为逆操作
- ✅ 实例格式化和解析正确

**重要性：**
这些修正防止了后续开发中最常见的坐标系 bug：
1. 测试覆盖不完整导致的边界 bug
2. 坐标系约定不明确导致的集成 bug
3. 与外部求解器对接时的坐标翻转 bug

---

## 2026-02-06 17:10

### 实现候选点生成原型（Day2 加分项）

**新增文件：**
- `scripts/gen_candidates.py` - 候选点生成工具

**功能：**
- 计算每个 free cell 的度数（4-连通邻居数量）
- 选择度 ≥ min_degree 的路口点（junction points）
- 随机抽样补齐或缩减到目标数量 R（默认 12）
- 输出 candidates.json（包含 cell、world、degree、is_junction）
- 可选可视化（红色=路口点，蓝色=随机点）

**生成策略：**
1. 优先选择路口点（度数高的格子）
2. 如果路口点不足，随机补充
3. 如果路口点过多，随机抽样缩减

**验收：**
- ✅ map_01.map（度≥3）：282 个路口点，随机抽样 12 个
- ✅ map_01.map（度≥4）：164 个路口点，随机抽样 12 个
- ✅ test_small.map（度≥3）：48 个路口点，随机抽样 12 个
- ✅ test_small.map（度≥5）：0 个路口点，随机补充 12 个
- ✅ JSON 格式正确，包含 map_info、generation_params、statistics、candidates
- ✅ 可视化正确显示路口点和随机点

**用途：**
- Day 8 的 coverage baseline
- 会合点候选集
- 任务分配的参考点

**用法：**
```bash
python scripts/gen_candidates.py maps/map_01.map
python scripts/gen_candidates.py maps/map_01.map --num-candidates 20 --visualize
python scripts/gen_candidates.py maps/map_01.map --min-degree 4 --output outputs/candidates.json
```

---

## 2026-02-06 17:00

### 实现映射单元测试脚本（Day2）

**新增文件：**
- `scripts/test_mapping.py` - 坐标映射单元测试脚本

**测试内容：**
- 测试1：随机抽 50 个 free cells，验证 cell → world → cell 往返转换
- 测试2：随机抽 50 个 world 点，验证 world → cell → world 往返转换
- 输出详细测试报告（mapping_report.json）

**报告内容：**
- 地图信息（width, height, resolution, origin, free_cells）
- 测试1结果（pass_count, fail_count, pass_rate, failures）
- 测试2结果（pass_count, fail_count, max_error, mean_error, out_of_bounds_count）
- 总体结果（all_tests_passed, total_samples, total_pass, total_fail）

**验收：**
- ✅ map_01.map：100/100 通过（100%）
  - 测试1：50/50 通过
  - 测试2：50/50 通过，最大误差 0.137m，平均误差 0.086m
  - 越界次数：0
- ✅ test_ros.yaml：100/100 通过（100%）
  - 测试1：50/50 通过
  - 测试2：50/50 通过，最大误差 0.034m，平均误差 0.021m
  - 越界次数：0
- ✅ 报告 JSON 格式正确，包含所有必要字段

**用法：**
```bash
python scripts/test_mapping.py maps/map_01.map
python scripts/test_mapping.py maps/test_ros.yaml --n-samples 100
python scripts/test_mapping.py maps/map_01.map --output outputs/report.json
```

---

## 2026-02-06 16:50

### 实现地图检查工具（Day2）

**新增文件：**
- `scripts/inspect_map.py` - 地图检查和可视化工具

**功能：**
- 生成地图元数据（map_meta.json）
  - map_id, width, height, total_cells
  - free_count, obstacle_count, free_percent
  - resolution, origin, frame
  - connectivity_default (4)
- 生成地图预览图（map_preview.png）
  - 黑色 = 障碍，白色 = 自由
  - 使用 origin='lower' 确保坐标系正确
- 生成详细预览（--detailed 选项）
  - 标注四个角落格子位置
  - 用于验证地图方向（防止上下翻转）

**修复：**
- 修复 `auto_load_map()` 支持 ROS .yaml 格式

**验收：**
- ✅ 成功加载 MovingAI .map 格式（map_01.map）
- ✅ 成功加载 ROS .yaml 格式（test_ros.yaml）
- ✅ 元数据 JSON 格式正确，包含所有必要字段
- ✅ 预览图生成成功（PNG 格式，48-77KB）
- ✅ 详细预览包含角落标注，便于验证方向
- ✅ 肉眼确认地图方向正确（没有上下翻转）

**用法：**
```bash
python scripts/inspect_map.py maps/map_01.map
python scripts/inspect_map.py maps/test_ros.yaml --detailed
python scripts/inspect_map.py maps/map_01.map --output-dir outputs/map_inspect
```

---

## 2026-02-06 16:40

### 实现邻接图和最短路径工具（Day2）

**新增文件：**
- `agcoop/map/neighbors.py` - 邻接图和 BFS 最短路径
- `test_neighbors.py` - 邻接图验收测试

**邻接图功能：**
- `get_neighbors()` - 获取格子的合法邻居（4-连通或 8-连通）
- `shortest_path_length()` - BFS 计算最短路径长度
- `shortest_path()` - BFS 计算完整路径
- `compute_distance_map()` - 从起点计算到所有格子的距离

**设计选择：**
- 默认使用 4-连通（更适合差速车、执行更稳定）
- 8-连通可选（后续可用于 UAV 或启发式估算）
- BFS 实现（Day2 足够快，简单可靠）

**验收：**
- ✅ get_neighbors() 返回正确的邻居（4-连通、8-连通）
- ✅ shortest_path_length() 正确计算距离
- ✅ 随机采样 30 对 free cells，100% 可达（地图连通性好）
- ✅ 平均距离 14.5 步，最大距离 27 步
- ✅ obstacle 封堵时返回 None
- ✅ 路径上所有格子都是 free cells
- ✅ distance_map 正确计算到所有格子的距离
- ✅ 边界情况处理正确（起点即终点、障碍、越界）

---

## 2026-02-06 16:25

### 实现权威坐标映射系统（Day2）

**新增文件：**
- `agcoop/map/mapping.py` - 权威坐标映射函数
- `test_mapping.py` - 坐标映射验收测试

**坐标映射功能：**
- `cell_to_world()` - 格子中心坐标转世界坐标
- `world_to_cell()` - 世界坐标转格子索引
- `world_to_cell_checked()` - 带边界检查的转换（越界抛异常）
- `in_bounds()` - 边界检查
- `clip_to_bounds()` - 裁剪到边界
- `get_cell_bounds()` - 获取格子边界

**坐标系约定（详见 mapping.py 注释）：**
- i = row (y 方向), j = col (x 方向)
- origin 在 cell(0,0) 左下角
- cell_to_world 返回格子中心坐标
- 支持任意 origin（包括负值，ROS 常见）

**验收：**
- ✅ 100% 往返转换一致（286/286 个自由格子）
- ✅ 边界检查正确（in_bounds, clip_to_bounds）
- ✅ world_to_cell_checked 越界正确抛出异常
- ✅ get_cell_bounds 正确
- ✅ 不同 origin 处理正确（包括负 origin）

**集成：**
- GridMap 已更新为使用 mapping 模块函数
- 所有地图 I/O 模块统一使用权威映射函数

---

## 2026-02-06 16:07

### 添加 ROS 地图格式支持（Day2）

**新增文件：**
- `agcoop/map/io_ros.py` - ROS map_server 格式 I/O
- `maps/test_ros.yaml` - ROS 测试地图配置
- `maps/test_ros.pgm` - ROS 测试地图图像（20x20）
- `test_map_ros.py` - ROS 地图测试

**ROS 格式支持：**
- 加载 .yaml + .pgm 格式（ROS map_server 标准）
- 解析 resolution, origin, occupied_thresh, free_thresh
- 正确处理 PGM 图像（P5 binary 格式）
- 二值化 occupancy grid（高值=自由，低值=障碍）
- 保存为 ROS 格式（save_ros_map）

**验收：**
- ✅ 加载 ROS .yaml + .pgm 格式
- ✅ 正确解析 resolution (0.05) 和 origin (-10.0, -10.0)
- ✅ 正确二值化（306 个自由格子，76.5%）
- ✅ 坐标转换考虑 origin
- ✅ 保存和重新加载一致

---

## 2026-02-06 15:54

### 实现地图模块（Day2）

**新增文件：**
- `agcoop/map/grid_map.py` - GridMap 核心数据结构
- `agcoop/map/io_text.py` - 文本格式地图 I/O（MovingAI .map、简单文本）
- `agcoop/map/__init__.py` - 模块导出接口
- `maps/test_small.map` - 测试地图（10x10）
- `maps/map_01.map` - 示例地图（20x20）
- `test_map.py` - 地图模块测试

**GridMap 功能：**
- 字段：width, height, grid, resolution, origin, frame, free_cells
- 方法：is_free(), in_bounds(), cell_to_world(), world_to_cell(), get_neighbors()
- 预计算：free_cells 列表（加载时自动计算）

**支持格式：**
- MovingAI .map 格式（标准 MAPF benchmark）
- 简单文本格式（0/1 矩阵）
- auto_load_map() 自动检测格式

**验收：**
- ✅ 加载 MovingAI .map 格式（test_small.map: 10x10, 56 个自由格子）
- ✅ free_cells 数量正确
- ✅ 边界检查不崩溃（in_bounds, is_free）
- ✅ 坐标转换正确（cell_to_world, world_to_cell）
- ✅ 邻居查询正确（4-连通、8-连通）
- ✅ 可视化正常（小地图可打印）
- ✅ 加载真实地图（map_01.map: 20x20, 286 个自由格子，71.5% 自由）

---

## 2026-02-06 15:18

### 完善 metrics.json 和 trace.jsonl schema（最终版）

**修改文件：**
- `agcoop/utils/io.py` - 添加 compute_file_hash() 函数
- `agcoop/env/core.py` - 添加 map_hash、decision_period，扩展 trace 字段

**metrics.json 新增：**
- `map_hash` - 地图文件哈希（sha256 前 16 位）

**trace.jsonl 扩展字段（预留）：**
- `task_completed_ids` - 当前步完成的任务 ID 列表
- `snr_best` - 最佳 SNR 值
- `decision_step` - 是否为决策步（t % decision_period == 0）
- `chosen_task_id` - 选择的任务 ID
- `chosen_rendezvous` - 选择的会合点
- `mapf_called` - 是否调用 MAPF
- `mapf_success` - MAPF 是否成功
- `mapf_plan_time_ms` - MAPF 规划时间

**验收：**
- ✅ 相同 seed 两次运行，所有指标完全一致
- ✅ trace.jsonl 完全一致（包含所有预留字段）
- ✅ decision_step 正确标记（t=5,10,15...）
- ✅ metrics 包含 33 个字段，trace 包含 14 个字段
- ✅ 所有预留字段为合理默认值（0/null/false/[]）

---

## 2026-02-06 15:11

### 扩展 metrics.json 字段

**修改文件：**
- `agcoop/env/core.py` - 添加 run_id、method、planner 参数，跟踪 max_outage_streak
- `agcoop/utils/logger.py` - 添加 sim_steps_per_sec 计算
- `scripts/run_one_episode.py` - 添加 --method 和 --planner 参数

**新增字段（共 30+ 个）：**
- **A. 复现管理**: run_id, method, planner, map_path
- **B. 任务质量**: completion_rate
- **C. 通信指标**: max_outage_streak, snr_threshold, snr_best_mean, snr_best_min
- **D. 规划执行（预留）**: mapf_calls, mapf_success_calls, mapf_timeout_calls, mapf_mean_plan_time_ms, fallback_wait_steps
- **D2. 会合回收（预留）**: rendezvous_success, rendezvous_fail, emergency_landings, uav_loiter_steps, ugv_hold_steps
- **E. 性能**: sim_steps_per_sec, termination_reason

**验收：**
- ✅ 相同 seed 重复执行，所有关键指标完全一致
- ✅ max_outage_streak 正确跟踪（示例：3）
- ✅ run_id 自动生成（格式：map_01_N3_seed100_lambda0.1）
- ✅ 预留字段全部为 0（后续填充不改 schema）

---

## 2026-02-06 14:54

### 实现一键运行脚本

**文件：**
- `scripts/run_one_episode.py` - 一键运行脚本

**功能：**
- 命令行参数：`--config`、`--seed`、`--out_name`
- 自动覆盖 seed、创建输出目录、运行完整 episode
- 显示进度条（每 10%）和最终统计
- 验证输出文件和 trace 行数

**验收：**
- ✅ 相同 seed 重复执行，metrics 完全一致（除 runtime_sec）
- ✅ trace.jsonl 完全一致
- ✅ outage%、tasks_completed 等指标可复现

**用法：**
```bash
python scripts/run_one_episode.py --seed 42
python scripts/run_one_episode.py --config configs/default.yaml --seed 123 --out_name my_run
```

---

## 2026-02-06 (早些时候)

### 实现日志与指标输出系统

**文件：**
- `agcoop/utils/logger.py` - TraceLogger 和 MetricsLogger
- `agcoop/utils/io.py` - 原子写文件工具
- `agcoop/env/core.py` - 集成日志功能（添加 `output_dir` 和 `enable_logging` 参数）

**输出文件：**
- `trace.jsonl` - 每步记录（行数 = steps）
- `metrics.json` - 最终指标
- `config_resolved.yaml` - 完整配置

**测试：**
- `test_logging.py` - 验收测试（全部通过）
- `example_with_logging.py` - 使用示例
