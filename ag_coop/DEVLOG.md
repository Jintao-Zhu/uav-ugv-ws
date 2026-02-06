# 开发日志

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
