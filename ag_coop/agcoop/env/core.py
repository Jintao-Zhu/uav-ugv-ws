"""
AGCoop 环境核心：最小数据模型 (Day1)

定义系统状态、step 逻辑和基础指标。
Day1 版本：UGV 原地不动，UAV 永远在 0 号车上，任务生成简单随机。
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path
import numpy as np


@dataclass
class Task:
    """任务数据结构"""
    task_id: int
    position: Tuple[float, float]  # (x, y)
    arrival_time: int
    deadline: int
    completed: bool = False
    completion_time: Optional[int] = None

    def is_overdue(self, current_time: int) -> bool:
        """检查任务是否超期"""
        return current_time > self.deadline

    def get_tardiness(self, current_time: int) -> int:
        """计算延迟时间（如果已完成）"""
        if self.completed and self.completion_time is not None:
            return max(0, self.completion_time - self.deadline)
        return 0


@dataclass
class SystemState:
    """系统状态（Day1 最简版本）"""
    t: int = 0  # 当前时间步
    ugv_positions: List[Tuple[float, float]] = field(default_factory=list)  # [(x,y)] * n_ugv
    uav_onboard_ugv_id: int = 0  # UAV 永远在 0 号车上（Day1）
    task_pool: List[Task] = field(default_factory=list)  # 任务池

    # 指标累计
    tasks_completed: int = 0
    outage_steps: int = 0
    deadline_miss: int = 0
    tardiness_sum: int = 0

    # 通信指标累计
    snr_sum: float = 0.0
    snr_min: float = float('inf')

    # 内部计数器
    _next_task_id: int = 0

    def add_task(self, position: Tuple[float, float], arrival_time: int, deadline: int) -> Task:
        """添加新任务到任务池"""
        task = Task(
            task_id=self._next_task_id,
            position=position,
            arrival_time=arrival_time,
            deadline=deadline
        )
        self.task_pool.append(task)
        self._next_task_id += 1
        return task

    def complete_task(self, task_id: int, completion_time: int) -> bool:
        """完成任务并更新指标"""
        for task in self.task_pool:
            if task.task_id == task_id and not task.completed:
                task.completed = True
                task.completion_time = completion_time
                self.tasks_completed += 1

                # 检查是否超期
                if completion_time > task.deadline:
                    self.deadline_miss += 1
                    self.tardiness_sum += (completion_time - task.deadline)

                return True
        return False

    def get_active_tasks(self) -> List[Task]:
        """获取未完成的任务"""
        return [task for task in self.task_pool if not task.completed]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于日志记录）"""
        return {
            't': self.t,
            'ugv_positions': self.ugv_positions,
            'uav_onboard_ugv_id': self.uav_onboard_ugv_id,
            'n_active_tasks': len(self.get_active_tasks()),
            'tasks_completed': self.tasks_completed,
            'outage_steps': self.outage_steps,
            'deadline_miss': self.deadline_miss,
            'tardiness_sum': self.tardiness_sum,
        }


class AGCoopEnv:
    """
    AGCoop 环境主类（Day1 最简版本）

    Day1 特性：
    - UGV 原地不动
    - UAV 永远在 0 号车上
    - 任务随机生成（可选）
    - 简单的任务完成规则（测试指标链路）
    """

    def __init__(self, config: Dict[str, Any], output_dir: Optional[str] = None, enable_logging: bool = False,
                 run_id: Optional[str] = None, method: str = "static", planner: str = "none"):
        """
        初始化环境

        Args:
            config: 配置字典，包含 episode, robots, tasks 等配置
            output_dir: 输出目录（用于日志记录），如果为 None 则不记录日志
            enable_logging: 是否启用日志记录
            run_id: 运行 ID（用于唯一标识一次运行）
            method: 方法名称（static/greedy/coverage/ppo/il 等）
            planner: 规划器名称（PIBT/HCA/none 等）
        """
        self.config = config

        # 提取配置参数
        self.horizon_steps = config['episode']['horizon_steps']
        self.seed = config['episode']['seed']
        self.n_ugv = config['robots']['n_ugv']
        self.n_uav = config['robots']['n_uav']

        # 任务配置
        self.tasks_enabled = config['tasks']['enabled']
        self.arrival_rate = config['tasks']['arrival_rate']
        self.deadline_min = config['tasks']['deadline_min']
        self.deadline_max = config['tasks']['deadline_max']

        # 通信配置
        self.comm_enabled = config['comm']['enabled']
        self.snr_threshold = config['comm'].get('snr_threshold_db', -20.0)

        # 初始化通信模型
        if self.comm_enabled:
            from agcoop.comm import CommConfig
            self.comm_config = CommConfig.from_dict(config['comm'])
        else:
            self.comm_config = None

        # Relay 配置（Day8 Step 3）
        self.relay_enabled = config.get('relay', {}).get('enabled', False)
        if self.relay_enabled:
            from agcoop.rendezvous.relay_controller import RelayConfig
            self.relay_config = RelayConfig.from_dict(config.get('relay', {}))
        else:
            self.relay_config = None

        # Relay controller（延迟初始化，在 reset 时创建）
        self.relay_controller = None

        # Communication-Aware Greedy 配置（Day8 Step 6.3/6.6）
        self.comm_lambda = config.get('comm_greedy', {}).get('lambda', 0.0)
        self.comm_radius = config.get('comm_greedy', {}).get('radius', 8.0)
        self.comm_margin = config.get('comm_greedy', {}).get('margin', 3.0)  # Day8 Step 6.6: gating margin

        # MAPF 配置（Day6.5）
        self.mapf_enabled = config.get('mapf', {}).get('enabled', False)
        if self.mapf_enabled:
            self.mapf_K = config['episode'].get('decision_period', 5)  # 使用 decision_period 作为 K
            self.mapf_H = config['mapf'].get('H', 10)
            self.mapf_budget_ms = config['mapf'].get('time_budget_ms', 1000)
            self.mapf_connectivity = config['mapf'].get('connectivity', 4)
        else:
            self.mapf_K = None
            self.mapf_H = None
            self.mapf_budget_ms = None
            self.mapf_connectivity = None

        # MAPF controller（延迟初始化，在 reset 时创建）
        self.ugv_controller = None
        self.mapf_wrapper = None

        # 地图配置
        self.map_path = config['episode'].get('map_path', 'none')
        self.map_hash = None  # 延迟计算（在 reset 时）
        self.grid_map = None  # 地图对象（如果加载）

        # 决策周期
        self.decision_period = config['episode'].get('decision_period', 5)

        # 实验标识
        self.run_id = run_id
        self.method = method
        self.planner = planner

        # 初始化随机数生成器
        self.rng = np.random.RandomState(self.seed)

        # 状态
        self.state: Optional[SystemState] = None

        # Day1: 简单的地图边界（假设 100x100）
        self.map_width = 100.0
        self.map_height = 100.0

        # 日志记录
        self.enable_logging = enable_logging
        self.output_dir = output_dir
        self.trace_logger = None
        self.metrics_logger = None

        # 用于跟踪每步完成的任务数和 outage
        self._prev_tasks_completed = 0
        self._prev_outage_steps = 0

        # 用于跟踪 outage 连续性
        self._current_outage_streak = 0
        self._max_outage_streak = 0

    def reset(self) -> SystemState:
        """
        重置环境到初始状态

        Returns:
            初始系统状态
        """
        # 重置随机数生成器（保证可复现）
        self.rng = np.random.RandomState(self.seed)

        # 加载地图（如果指定）
        if self.map_path != 'none' and self.grid_map is None:
            try:
                from agcoop.map import auto_load_map
                self.grid_map = auto_load_map(self.map_path)
                print(f"地图加载成功: {self.map_path} ({self.grid_map.width}x{self.grid_map.height})")
                # 更新地图边界为实际网格范围
                self.map_width = self.grid_map.width * self.grid_map.resolution
                self.map_height = self.grid_map.height * self.grid_map.resolution
            except Exception as e:
                print(f"警告：无法加载地图 {self.map_path}: {e}")
                print("将使用简单随机通信模型")
                self.grid_map = None

        # 生成候选中继点（Day8 Step 2）
        self.candidate_relays = []
        if self.grid_map is not None:
            from agcoop.rendezvous.candidate_generator import generate_candidate_relays
            candidate_count = self.config.get('rendezvous', {}).get('candidate_count', 12)
            self.candidate_relays = generate_candidate_relays(
                self.grid_map,
                R=candidate_count,
                rng=self.rng
            )
            print(f"候选中继点生成: {len(self.candidate_relays)} 个")

        # 初始化 Relay Controller（Day8 Step 3）
        if self.relay_enabled and self.grid_map is not None and self.candidate_relays:
            from agcoop.rendezvous.relay_controller import RelayController
            self.relay_controller = RelayController(
                self.relay_config,
                self.candidate_relays,
                self.grid_map,
                self.comm_config
            )
            print(f"Relay Controller 初始化: relay_ugv_id={self.relay_config.relay_ugv_id}")
        else:
            self.relay_controller = None

        # 初始化状态
        self.state = SystemState()
        self.state.t = 0

        # 初始化 UGV 位置
        # 当有地图时（不论 method），从地图中采样不同的空闲位置
        if self.grid_map is not None:
            # 采样不同的空闲起始位置
            free_cells = []
            for x in range(self.grid_map.width):
                for y in range(self.grid_map.height):
                    if self.grid_map.is_free(x, y):
                        free_cells.append((x, y))

            if len(free_cells) >= self.n_ugv:
                # 随机采样 n_ugv 个不同的空闲位置
                sampled_cells = self.rng.choice(len(free_cells), size=self.n_ugv, replace=False)
                self.state.ugv_positions = []
                for idx in sampled_cells:
                    cell = free_cells[idx]
                    world_pos = self.grid_map.cell_to_world(cell[0], cell[1])
                    self.state.ugv_positions.append(world_pos)
            else:
                print(f"警告：空闲位置不足 ({len(free_cells)} < {self.n_ugv})，使用原点")
                self.state.ugv_positions = [(0.0, 0.0) for _ in range(self.n_ugv)]
        else:
            # 无地图: 所有 UGV 从原点开始
            self.state.ugv_positions = [(0.0, 0.0) for _ in range(self.n_ugv)]

        # 初始化 UAV（永远在 0 号车上）
        self.state.uav_onboard_ugv_id = 0

        # 清空任务池
        self.state.task_pool = []

        # 重置指标
        self.state.tasks_completed = 0
        self.state.outage_steps = 0
        self.state.deadline_miss = 0
        self.state.tardiness_sum = 0
        self.state._next_task_id = 0

        # 重置通信指标
        self.state.snr_sum = 0.0
        self.state.snr_min = float('inf')

        # 重置日志跟踪变量
        self._prev_tasks_completed = 0
        self._prev_outage_steps = 0
        self._current_outage_streak = 0
        self._max_outage_streak = 0

        # 初始化 step motion 跟踪（用于 mean_step_motion）
        self._step_motions = []

        # 初始化 controller（基于 method）
        # 记录初始信息（用于 init.json）
        self._init_starts = None
        self._init_goals = None

        # 获取 UGV cell 坐标（所有方法共用）
        starts = {}
        if self.grid_map is not None:
            for i, pos in enumerate(self.state.ugv_positions):
                cell = self.grid_map.world_to_cell(pos[0], pos[1])
                starts[i] = cell

        if self.method == "greedy" and self.grid_map is not None:
            from agcoop.controllers import UGVGreedyController

            K = self.decision_period
            self.ugv_controller = UGVGreedyController(
                K=K,
                grid_map=self.grid_map,
                connectivity=4
            )

            # 初始目标 = 起点（greedy 在 step 时根据任务动态更新目标）
            goals = {i: starts[i] for i in starts}
            self._init_starts = dict(starts)
            self._init_goals = dict(goals)
            self.ugv_controller.reset(starts, goals)

            print(f"Greedy Controller 初始化: K={K}")

        elif self.method == "coverage" and self.grid_map is not None:
            from agcoop.controllers import UGVCoverageController

            K = self.decision_period
            self.ugv_controller = UGVCoverageController(
                K=K,
                grid_map=self.grid_map,
                connectivity=4,
                relay_controller=self.relay_controller  # Pass relay controller
            )

            # 初始目标 = 起点（coverage 在 step 时根据任务和 relay 动态更新目标）
            goals = {i: starts[i] for i in starts}
            self._init_starts = dict(starts)
            self._init_goals = dict(goals)
            self.ugv_controller.reset(starts, goals)

            print(f"Coverage Controller 初始化: K={K}, relay_enabled={self.relay_enabled}")

        elif self.method == "comm_greedy" and self.grid_map is not None:
            # Day8 Step 6.3: Communication-Aware Greedy Controller
            # 使用与 greedy 相同的 controller，只是目标选择函数不同
            from agcoop.controllers import UGVGreedyController

            K = self.decision_period
            self.ugv_controller = UGVGreedyController(
                K=K,
                grid_map=self.grid_map,
                connectivity=4
            )

            # 初始目标 = 起点（comm_greedy 在 step 时根据任务和通信动态更新目标）
            goals = {i: starts[i] for i in starts}
            self._init_starts = dict(starts)
            self._init_goals = dict(goals)
            self.ugv_controller.reset(starts, goals)

            print(f"Comm-Greedy Controller 初始化: K={K}, λ={self.comm_lambda}, D0={self.comm_radius}")

        elif self.mapf_enabled and self.grid_map is not None:
            from agcoop.mapf import UGVMAPFWrapper
            from agcoop.controllers import UGVRecedingHorizonMAPFController

            # 创建 wrapper
            self.mapf_wrapper = UGVMAPFWrapper(
                grid_map=self.grid_map,
                connectivity=self.mapf_connectivity,
                time_budget_ms=self.mapf_budget_ms
            )

            # 创建 controller
            self.ugv_controller = UGVRecedingHorizonMAPFController(
                K=self.mapf_K,
                H=self.mapf_H,
                budget_ms=self.mapf_budget_ms,
                wrapper=self.mapf_wrapper,
                enable_collision_check=True
            )

            # 生成巡逻目标
            goals = {}
            center_x = self.grid_map.width // 2
            center_y = self.grid_map.height // 2
            for i in range(self.n_ugv):
                offset_x = self.rng.randint(-5, 6)
                offset_y = self.rng.randint(-5, 6)
                goal_x = max(0, min(self.grid_map.width - 1, center_x + offset_x))
                goal_y = max(0, min(self.grid_map.height - 1, center_y + offset_y))

                if self.grid_map.is_free(goal_x, goal_y):
                    goals[i] = (goal_x, goal_y)
                else:
                    goals[i] = starts[i]

            self._init_starts = dict(starts)
            self._init_goals = dict(goals)
            self.ugv_controller.reset(starts, goals)

            print(f"MAPF Controller 初始化: K={self.mapf_K}, H={self.mapf_H}, budget={self.mapf_budget_ms}ms")
        else:
            # static: 无 controller，UGV 不动
            self.ugv_controller = None
            self.mapf_wrapper = None
            if self.grid_map is not None:
                self._init_starts = dict(starts)
                self._init_goals = {i: starts[i] for i in starts}

        # 初始化日志记录器
        if self.enable_logging and self.output_dir:
            from agcoop.utils.logger import TraceLogger, MetricsLogger
            from agcoop.utils.io import save_resolved_config, compute_file_hash
            import json as _json

            # 计算地图哈希（如果地图存在）
            if self.map_hash is None and self.map_path != 'none':
                self.map_hash = compute_file_hash(self.map_path)
            elif self.map_hash is None:
                self.map_hash = "none"

            # 创建输出目录
            output_path = Path(self.output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # 初始化 trace logger
            self.trace_logger = TraceLogger(str(output_path / "trace.jsonl"))
            self.trace_logger.open()

            # 初始化 metrics logger
            self.metrics_logger = MetricsLogger(str(output_path / "metrics.json"))
            self.metrics_logger.start_timer()

            # 保存配置
            save_resolved_config(self.config, self.output_dir)

            # 保存 init.json
            init_info = {
                'map': self.map_path,
                'n_agents': self.n_ugv,
                'seed': self.seed,
                'ugv_positions': self.state.ugv_positions,
            }
            if self._init_starts is not None:
                init_info['starts'] = {str(k): list(v) for k, v in self._init_starts.items()}
                init_info['goals'] = {str(k): list(v) for k, v in self._init_goals.items()}
            # Day8 Step 2: 添加候选中继点
            if self.candidate_relays:
                init_info['candidate_relays'] = [list(cell) for cell in self.candidate_relays]
            with open(output_path / "init.json", 'w') as f:
                _json.dump(init_info, f, indent=2)

        # Day8 Step 6.1: 生成任务目录（固化任务流）
        self.task_catalog = None
        if self.tasks_enabled and self.enable_logging and self.output_dir:
            from agcoop.tasks import generate_and_save_catalog

            # Day8 Step 6.5: 获取双热点配置
            dual_hotspot_config = self.config.get('dual_hotspot', None)

            # 生成任务目录
            self.task_catalog = generate_and_save_catalog(
                output_dir=Path(self.output_dir),
                horizon_steps=self.horizon_steps,
                arrival_rate=self.arrival_rate,
                deadline_min=self.deadline_min,
                deadline_max=self.deadline_max,
                grid_map=self.grid_map,
                seed=self.seed,
                dual_hotspot_config=dual_hotspot_config
            )

            print(f"任务目录生成: {len(self.task_catalog)} 个任务, hash={self.task_catalog.compute_hash()}")

        return self.state

    def step(self, action: Optional[Any] = None) -> Tuple[SystemState, Dict[str, Any], bool, Dict[str, Any]]:
        """
        执行一步环境演化

        Args:
            action: 动作（Day1 不使用，占位）

        Returns:
            (state, reward, done, info) 元组
            - state: 新的系统状态
            - reward: 奖励（Day1 占位，返回 0）
            - done: 是否结束
            - info: 额外信息字典
        """
        if self.state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")

        # 记录步前 UGV 位置（用于计算 mean_step_motion）
        prev_ugv_positions = list(self.state.ugv_positions)

        # UGV 动作生成（Day6.5: 使用 MAPF controller）
        mapf_plan_info = None
        mapf_step_info = None

        if self.ugv_controller is not None:
            # 获取当前 UGV 位置（cell 坐标）
            current_positions = {}
            for i, pos in enumerate(self.state.ugv_positions):
                cell = self.grid_map.world_to_cell(pos[0], pos[1])
                current_positions[i] = cell

            # Greedy/Coverage/Comm-Greedy: 在决策步更新目标
            if self.method in ["greedy", "coverage", "comm_greedy"] and (self.state.t % self.decision_period == 0):
                if self.method == "comm_greedy":
                    # Day8 Step 6.3: 使用通信感知的目标选择
                    goals = self._compute_comm_greedy_goals(current_positions)
                else:
                    # Greedy 或 Coverage（带 relay）
                    goals = self._compute_greedy_goals(current_positions)
                self.ugv_controller.set_goals(goals)

            # 尝试重规划（每 K 步）
            mapf_plan_info = self.ugv_controller.maybe_replan(
                self.state.t,
                current_positions
            )

            # 执行一步（缓存路径或 fallback WAIT）
            mapf_step_info = self.ugv_controller.step(
                self.state.t,
                current_positions
            )

            # 检查碰撞
            if not mapf_step_info.collision_free:
                raise RuntimeError(f"MAPF collision: {mapf_step_info.collision_error}")

            # 更新 UGV 位置（从 cell 坐标转换回 world 坐标）
            new_ugv_positions = []
            for i in range(self.n_ugv):
                cell = mapf_step_info.positions[i]
                world_pos = self.grid_map.cell_to_world(cell[0], cell[1])
                new_ugv_positions.append(world_pos)

            self.state.ugv_positions = new_ugv_positions
        else:
            # Day1: UGV 原地不动（不更新位置）
            # self.state.ugv_positions 保持不变
            pass

        # Day1: UAV 原地不动（永远在 0 号车上）
        # self.state.uav_onboard_ugv_id 保持为 0

        # 任务生成（可选）
        if self.tasks_enabled:
            self._generate_tasks()

        # 任务完成（Day1 简单规则：如果任务在 (0,0) 附近则立即完成）
        self._complete_tasks_simple()

        # 计算通信指标（使用真实通信模型）
        snr_best, outage = self._update_outage()

        # 记录日志（如果启用）
        if self.enable_logging and self.trace_logger:
            self._log_step(snr_best, outage, mapf_plan_info, mapf_step_info)

        # 计算 step motion（移动的 agent 数量）
        if self.ugv_controller is not None:
            moved = sum(1 for old, new in zip(prev_ugv_positions, self.state.ugv_positions) if old != new)
            self._step_motions.append(moved)

        # 时间步进（在处理和日志记录之后）
        self.state.t += 1

        # 检查是否结束
        done = self.state.t >= self.horizon_steps

        # 如果结束，保存最终指标
        if done and self.enable_logging and self.metrics_logger:
            self._save_final_metrics()

        # 构建返回信息
        reward = 0.0  # Day1 占位
        info = {
            'timestep': self.state.t,
            'tasks_completed': self.state.tasks_completed,
            'outage_steps': self.state.outage_steps,
            'deadline_miss': self.state.deadline_miss,
            'tardiness_sum': self.state.tardiness_sum,
            'active_tasks': len(self.state.get_active_tasks()),
        }

        # 添加 MAPF 信息（如果有）
        if mapf_plan_info is not None:
            info['mapf_called'] = mapf_plan_info.called
            info['mapf_success'] = mapf_plan_info.success
            info['mapf_plan_time_ms'] = mapf_plan_info.plan_time_ms

        return self.state, reward, done, info

    def _generate_tasks(self) -> None:
        """
        生成新任务

        Day8 Step 6.1: 如果有任务目录，从目录中释放任务；否则按原逻辑随机生成。
        """
        # Day8 Step 6.1: 优先使用任务目录
        if self.task_catalog is not None:
            # 从目录中获取当前时间步应该释放的任务
            tasks_to_release = self.task_catalog.get_tasks_at_time(self.state.t)
            for task_data in tasks_to_release:
                position = tuple(task_data['position'])
                release_t = task_data['release_t']
                deadline_t = task_data['deadline_t']
                # 添加任务（使用 catalog 中的 deadline）
                self.state.add_task(position, release_t, deadline_t)
            return

        # 原逻辑：随机生成任务
        if self.rng.random() < self.arrival_rate:
            if self.grid_map is not None:
                # 在地图空闲格子中随机选一个作为任务位置
                free_cells = []
                for r in range(self.grid_map.height):
                    for c in range(self.grid_map.width):
                        if self.grid_map.is_free(r, c):
                            free_cells.append((r, c))
                if free_cells:
                    cell = free_cells[self.rng.randint(0, len(free_cells))]
                    position = self.grid_map.cell_to_world(cell[0], cell[1])
                else:
                    position = (0.0, 0.0)
            else:
                x = self.rng.uniform(0, self.map_width)
                y = self.rng.uniform(0, self.map_height)
                position = (x, y)

            # 随机 deadline
            deadline_offset = self.rng.randint(self.deadline_min, self.deadline_max + 1)
            deadline = self.state.t + deadline_offset

            # 添加任务
            self.state.add_task(position, self.state.t, deadline)

    def _complete_tasks_simple(self) -> None:
        """
        任务完成规则：如果任务位置在某个 UGV 附近，则完成。

        Day7 版本：检查任务与所有 UGV 的距离（而非 Day1 的固定原点）。
        """
        completion_radius = 0.3  # 约 1.5 个 cell（0.2m/cell）

        for task in self.state.get_active_tasks():
            for ugv_pos in self.state.ugv_positions:
                dx = task.position[0] - ugv_pos[0]
                dy = task.position[1] - ugv_pos[1]
                dist = np.sqrt(dx * dx + dy * dy)
                if dist < completion_radius:
                    self.state.complete_task(task.task_id, self.state.t)
                    break

    def _compute_greedy_goals(
        self,
        current_positions: dict
    ) -> dict:
        """
        Greedy 目标选择：每个 UGV 选最近的未分配活跃任务。

        Day8 Step 3: 如果启用 relay 模式，relay UGV 可能会被分配到 relay 目标。

        Args:
            current_positions: {agent_id: (i, j)} cell 坐标

        Returns:
            {agent_id: (i, j)} 目标 cell 坐标
        """
        # Day8 Step 3: 检查是否需要 relay 模式
        relay_goal = None
        if self.relay_controller is not None:
            # 获取当前 SNR
            # Day8 Step 6.2 FIX: 使用 SNR_nc（排除 carrier）而非 SNR_all
            self._update_outage()
            snr_best_nc = self.state._current_snr_best_nc

            # 获取 UAV 位置
            uav_ugv_id = self.state.uav_onboard_ugv_id
            uav_world_pos = self.state.ugv_positions[uav_ugv_id]
            uav_cell = self.grid_map.world_to_cell(uav_world_pos[0], uav_world_pos[1])

            # 决定 relay 行动（使用 SNR_nc）
            relay_mode, relay_target, relay_score = self.relay_controller.decide_relay_action(
                snr_best_nc,
                uav_cell,
                current_positions
            )

            if relay_mode and relay_target is not None:
                # 进入 relay 模式，为 relay UGV 分配 relay 目标
                relay_ugv_id = self.relay_config.relay_ugv_id
                relay_goal = {relay_ugv_id: relay_target}

        # 为所有 UGV 分配目标
        active_tasks = self.state.get_active_tasks()
        goals = {}
        assigned_tasks = set()

        for i in range(self.n_ugv):
            # Day8 Step 3: 如果是 relay UGV 且有 relay 目标，使用 relay 目标
            if relay_goal is not None and i in relay_goal:
                goals[i] = relay_goal[i]
                continue

            # 否则，使用 Greedy 逻辑选择最近任务
            pos = current_positions[i]
            best_task = None
            best_dist = float('inf')

            for task in active_tasks:
                if task.task_id in assigned_tasks:
                    continue
                # 将任务 world 坐标转换为 cell 坐标
                task_cell = self.grid_map.world_to_cell(task.position[0], task.position[1])
                # 确保 cell 在地图内且可通行
                ti, tj = task_cell
                if not (0 <= ti < self.grid_map.height and 0 <= tj < self.grid_map.width):
                    continue
                if not self.grid_map.is_free(ti, tj):
                    continue
                # 曼哈顿距离
                dist = abs(pos[0] - ti) + abs(pos[1] - tj)
                if dist < best_dist:
                    best_dist = dist
                    best_task = task

            if best_task is not None:
                task_cell = self.grid_map.world_to_cell(
                    best_task.position[0], best_task.position[1])
                goals[i] = task_cell
                assigned_tasks.add(best_task.task_id)
            else:
                # 没有可用任务，保持当前位置
                goals[i] = pos

        return goals

    def _compute_comm_greedy_goals(
        self,
        current_positions: dict
    ) -> dict:
        """
        Communication-Aware Greedy v2 目标选择（Day8 Step 6.6）

        核心思想：维持编队紧凑性，而非靠近 carrier

        打分公式：score = -d_task + λ * compactness_gain
        - d_task: UGV 到任务的距离
        - compactness_gain: 选择该任务后编队紧凑性的改善
        - λ: 通信权重（只在通信差时启用 gating）

        Args:
            current_positions: {agent_id: (i, j)} cell 坐标

        Returns:
            {agent_id: (i, j)} 目标 cell 坐标
        """
        # 获取通信参数
        comm_lambda = getattr(self, 'comm_lambda', 0.0)
        comm_margin = getattr(self, 'comm_margin', 3.0)  # gating margin (dB)

        # Day8 Step 6.6: Gating - 只在通信差时启用通信惩罚
        snr_worst_nc = getattr(self.state, '_current_snr_worst_nc', 0.0)
        snr_threshold = self.comm_config.snr_threshold_db if self.comm_config else -12.0

        # 如果 worst_nc 高于阈值 + margin，不启用通信惩罚
        if snr_worst_nc >= (snr_threshold + comm_margin):
            effective_lambda = 0.0
        else:
            effective_lambda = comm_lambda

        # 计算当前编队紧凑性（平均两两距离）
        current_compactness = self._compute_compactness(current_positions)

        # 为所有 UGV 分配目标
        active_tasks = self.state.get_active_tasks()
        goals = {}
        assigned_tasks = set()

        for i in range(self.n_ugv):
            pos = current_positions[i]
            best_task = None
            best_score = -float('inf')

            for task in active_tasks:
                if task.task_id in assigned_tasks:
                    continue

                # 将任务 world 坐标转换为 cell 坐标
                task_cell = self.grid_map.world_to_cell(task.position[0], task.position[1])
                ti, tj = task_cell

                # 确保 cell 在地图内且可通行
                if not (0 <= ti < self.grid_map.height and 0 <= tj < self.grid_map.width):
                    continue
                if not self.grid_map.is_free(ti, tj):
                    continue

                # 1. 任务距离项
                d_task = abs(pos[0] - ti) + abs(pos[1] - tj)
                term_task = -d_task

                # 2. 编队紧凑性项（只在 effective_lambda > 0 时计算）
                term_comm = 0.0
                if effective_lambda > 0:
                    # 模拟：如果 UGV i 移动到 task_cell，编队紧凑性如何变化
                    new_positions = dict(current_positions)
                    new_positions[i] = task_cell
                    new_compactness = self._compute_compactness(new_positions)

                    # compactness_gain: 紧凑性改善（负值表示变得更分散）
                    # 我们希望紧凑性增加（距离减小），所以 gain = current - new
                    compactness_gain = current_compactness - new_compactness
                    term_comm = compactness_gain

                # 3. 综合打分
                score = term_task + effective_lambda * term_comm

                if score > best_score:
                    best_score = score
                    best_task = task

            if best_task is not None:
                task_cell = self.grid_map.world_to_cell(
                    best_task.position[0], best_task.position[1])
                goals[i] = task_cell
                assigned_tasks.add(best_task.task_id)
            else:
                # 没有可用任务，保持当前位置
                goals[i] = pos

        return goals

    def _compute_compactness(self, positions: dict) -> float:
        """
        计算编队紧凑性（平均两两距离）

        Args:
            positions: {agent_id: (i, j)} cell 坐标

        Returns:
            平均两两距离（越小越紧凑）
        """
        if len(positions) <= 1:
            return 0.0

        total_dist = 0.0
        count = 0

        pos_list = list(positions.values())
        for i in range(len(pos_list)):
            for j in range(i + 1, len(pos_list)):
                dist = abs(pos_list[i][0] - pos_list[j][0]) + abs(pos_list[i][1] - pos_list[j][1])
                total_dist += dist
                count += 1

        return total_dist / count if count > 0 else 0.0

    def _update_outage(self) -> Tuple[float, bool]:
        """
        更新 outage 指标（使用真实通信模型）

        Day8 Step 5: 实现双轨 SNR 计算
        - all: 包含 carrier（legacy，保持向后兼容）
        - nc (non-carrier): 排除 carrier（主指标，用于评估 coverage 效果）

        Returns:
            (snr_best_all, outage_all) 元组（保持向后兼容）
        """
        if not self.comm_enabled or self.comm_config is None:
            # 通信未启用，返回默认值
            return 0.0, False

        # 需要地图来计算通信
        # Day1: 如果没有加载地图，使用简单随机模型
        if not hasattr(self, 'grid_map') or self.grid_map is None:
            # 简单随机 outage（10% 概率）
            outage = (self.rng.random() < 0.1)
            if outage:
                self.state.outage_steps += 1
            return 0.0, outage

        # 使用真实通信模型
        from agcoop.comm import compute_best_snr

        # 获取 UAV 位置（在 UGV 上）
        uav_ugv_id = self.state.uav_onboard_ugv_id
        uav_world_pos = self.state.ugv_positions[uav_ugv_id]

        # 转换为 cell 坐标
        uav_cell = self.grid_map.world_to_cell(uav_world_pos[0], uav_world_pos[1])

        # 获取所有 UGV 的 cell 坐标
        ugv_cells_all = []
        for ugv_pos in self.state.ugv_positions:
            ugv_cell = self.grid_map.world_to_cell(ugv_pos[0], ugv_pos[1])
            ugv_cells_all.append(ugv_cell)

        # 计算最佳 SNR (all - 包含 carrier)
        snr_best_all, best_ugv_id_all, outage_all = compute_best_snr(
            uav_cell, ugv_cells_all, self.grid_map, self.comm_config
        )

        # Day8 Step 5: 计算 non-carrier SNR
        # 排除 carrier，只计算 UAV 到其他 UGV 的 SNR
        ugv_cells_nc = []
        ugv_ids_nc = []
        for i, ugv_pos in enumerate(self.state.ugv_positions):
            if i == uav_ugv_id:
                continue  # 跳过 carrier
            ugv_cell = self.grid_map.world_to_cell(ugv_pos[0], ugv_pos[1])
            ugv_cells_nc.append(ugv_cell)
            ugv_ids_nc.append(i)

        if ugv_cells_nc:
            # 有其他 UGV，计算 non-carrier SNR
            snr_best_nc, best_idx_nc, outage_nc = compute_best_snr(
                uav_cell, ugv_cells_nc, self.grid_map, self.comm_config
            )
            # 映射回原始 UGV ID
            best_ugv_id_nc = ugv_ids_nc[best_idx_nc]

            # Day8 Step 6.4: 计算 worst SNR（编队连通性指标）
            # 计算 UAV 到每个非 carrier UGV 的 SNR
            from agcoop.comm import compute_snr, raycast
            snr_list_nc = []
            for ugv_cell in ugv_cells_nc:
                # 计算距离
                uav_world = self.grid_map.cell_to_world(uav_cell[0], uav_cell[1])
                ugv_world = self.grid_map.cell_to_world(ugv_cell[0], ugv_cell[1])
                dx = ugv_world[0] - uav_world[0]
                dy = ugv_world[1] - uav_world[1]
                distance_m = (dx**2 + dy**2)**0.5

                # 计算遮挡
                blocked_count = raycast.count_blocked_cells(self.grid_map, uav_cell, ugv_cell)

                # 计算 SNR
                snr = compute_snr(distance_m, blocked_count, self.comm_config)
                snr_list_nc.append(snr)

            # 最差链路 SNR
            snr_worst_nc = min(snr_list_nc)
            outage_worst_nc = snr_worst_nc < self.comm_config.snr_threshold_db
        else:
            # 只有 carrier，没有其他 UGV
            snr_best_nc = -float('inf')
            best_ugv_id_nc = -1
            outage_nc = True
            snr_worst_nc = -float('inf')
            outage_worst_nc = True

        # 更新累计指标 (all)
        if outage_all:
            self.state.outage_steps += 1

        self.state.snr_sum += snr_best_all
        self.state.snr_min = min(self.state.snr_min, snr_best_all)

        # Day8 Step 5: 更新 non-carrier 累计指标
        if not hasattr(self.state, 'outage_steps_nc'):
            self.state.outage_steps_nc = 0
            self.state.snr_sum_nc = 0.0
            self.state.snr_min_nc = float('inf')

        if outage_nc:
            self.state.outage_steps_nc += 1

        self.state.snr_sum_nc += snr_best_nc
        self.state.snr_min_nc = min(self.state.snr_min_nc, snr_best_nc)

        # Day8 Step 6.4: 更新 worst_nc 累计指标（编队连通性）
        if not hasattr(self.state, 'outage_steps_worst_nc'):
            self.state.outage_steps_worst_nc = 0
            self.state.snr_sum_worst_nc = 0.0
            self.state.snr_min_worst_nc = float('inf')

        if outage_worst_nc:
            self.state.outage_steps_worst_nc += 1

        self.state.snr_sum_worst_nc += snr_worst_nc
        self.state.snr_min_worst_nc = min(self.state.snr_min_worst_nc, snr_worst_nc)

        # 存储当前步的 nc 和 worst_nc 指标（用于 trace）
        self.state._current_snr_best_nc = snr_best_nc
        self.state._current_outage_nc = outage_nc
        self.state._current_best_ugv_id_nc = best_ugv_id_nc
        self.state._current_snr_worst_nc = snr_worst_nc
        self.state._current_outage_worst_nc = outage_worst_nc

        return snr_best_all, outage_all

    def get_metrics(self) -> Dict[str, Any]:
        """
        获取当前累计指标

        Returns:
            指标字典
        """
        if self.state is None:
            return {}

        return {
            'tasks_completed': self.state.tasks_completed,
            'outage_steps': self.state.outage_steps,
            'deadline_miss': self.state.deadline_miss,
            'tardiness_sum': self.state.tardiness_sum,
            'total_tasks': len(self.state.task_pool),
            'active_tasks': len(self.state.get_active_tasks()),
        }

    def render(self) -> str:
        """
        简单的文本渲染（Day1 版本）

        Returns:
            状态的文本表示
        """
        if self.state is None:
            return "Environment not initialized."

        lines = [
            f"=== AGCoop Environment (t={self.state.t}/{self.horizon_steps}) ===",
            f"UGV Positions: {self.state.ugv_positions}",
            f"UAV on UGV: {self.state.uav_onboard_ugv_id}",
            f"Active Tasks: {len(self.state.get_active_tasks())}",
            f"Metrics:",
            f"  - Tasks Completed: {self.state.tasks_completed}",
            f"  - Deadline Miss: {self.state.deadline_miss}",
            f"  - Tardiness Sum: {self.state.tardiness_sum}",
            f"  - Outage Steps: {self.state.outage_steps}",
        ]

        return "\n".join(lines)

    def _log_step(self, snr_best: float = 0.0, outage: bool = False,
                   mapf_plan_info=None, mapf_step_info=None) -> None:
        """记录当前步的日志到 trace.jsonl

        Args:
            snr_best: 当前步的最佳 SNR（dB）
            outage: 当前步是否发生 outage
            mapf_plan_info: MAPF 规划信息（PlanInfo）
            mapf_step_info: MAPF 执行信息（StepInfo）
        """
        if self.state is None or self.trace_logger is None:
            return

        # 计算当前步完成的任务数
        tasks_completed_this_step = self.state.tasks_completed - self._prev_tasks_completed
        self._prev_tasks_completed = self.state.tasks_completed

        # 计算当前步是否发生 outage
        outage_this_step = 1 if outage else 0

        # 跟踪 outage 连续性
        if outage_this_step:
            self._current_outage_streak += 1
            self._max_outage_streak = max(self._max_outage_streak, self._current_outage_streak)
        else:
            self._current_outage_streak = 0

        # 判断是否为决策步
        # 标准 Receding Horizon: t=0 立即规划，然后每 K 步重新规划
        # 即 t=0, K, 2K, 3K, ... = 0, 5, 10, 15, ... (K=5)
        decision_step = (self.state.t % self.decision_period == 0)

        # 提取 MAPF 信息
        mapf_called = False
        mapf_success = None
        mapf_plan_time_ms = None
        mapf_fallback = False
        ugv_goals = None

        if mapf_plan_info is not None:
            mapf_called = mapf_plan_info.called
            mapf_success = mapf_plan_info.success
            mapf_plan_time_ms = mapf_plan_info.plan_time_ms

        if mapf_step_info is not None:
            mapf_fallback = mapf_step_info.in_fallback

        # 获取 UGV goals（如果 controller 存在）
        if self.ugv_controller is not None and self.ugv_controller.current_goals is not None:
            ugv_goals = self.ugv_controller.current_goals

        # Day8 Step 3: 获取 relay 信息
        relay_mode = False
        relay_target_cell = None
        relay_ugv_id = None
        if self.relay_controller is not None:
            relay_status = self.relay_controller.get_status()
            relay_mode = relay_status['relay_mode']
            relay_target_cell = relay_status['relay_target_cell']
            relay_ugv_id = relay_status['relay_ugv_id']

        # Day8 Step 5: 获取 non-carrier SNR 指标
        snr_best_nc = getattr(self.state, '_current_snr_best_nc', 0.0)
        outage_nc = getattr(self.state, '_current_outage_nc', False)
        best_ugv_id_nc = getattr(self.state, '_current_best_ugv_id_nc', -1)
        outage_nc_this_step = 1 if outage_nc else 0

        # Day8 Step 6.4: 获取 worst_nc SNR 指标（编队连通性）
        snr_worst_nc = getattr(self.state, '_current_snr_worst_nc', 0.0)
        outage_worst_nc = getattr(self.state, '_current_outage_worst_nc', False)
        outage_worst_nc_this_step = 1 if outage_worst_nc else 0

        # 构建步骤数据（包含预留字段）
        step_data = {
            't': self.state.t,
            'ugv_pos': self.state.ugv_positions,
            'ugv_positions': self.state.ugv_positions,  # Day6 collision checker 期望的字段名
            'uav_state': self.state.uav_onboard_ugv_id,
            'uav_onboard_ugv_id': self.state.uav_onboard_ugv_id,  # Day8 Step 5: 明确 carrier ID
            'num_tasks_in_pool': len(self.state.task_pool),
            'num_active_tasks': len(self.state.get_active_tasks()),
            'task_completed_ids': [],  # Day1 占位
            # Day8 Step 5: 双轨 SNR 指标
            'outage': outage_this_step,  # legacy (all)
            'snr_best': round(snr_best, 2),  # legacy (all)
            'outage_all': outage_this_step,  # 明确标注 all
            'snr_best_all': round(snr_best, 2),  # 明确标注 all
            'outage_nc': outage_nc_this_step,  # non-carrier (主指标)
            'snr_best_nc': round(snr_best_nc, 2),  # non-carrier (主指标)
            'best_ugv_id_nc': best_ugv_id_nc,  # non-carrier 最佳 UGV ID
            # Day8 Step 6.4: worst_nc 指标（编队连通性）
            'outage_worst_nc': outage_worst_nc_this_step,
            'snr_worst_nc': round(snr_worst_nc, 2),
            'decision_step': decision_step,
            'chosen_task_id': None,  # Day1 占位
            'chosen_rendezvous': None,  # Day1 占位
            'mapf_called': mapf_called,
            'mapf_success': mapf_success,
            'mapf_plan_time_ms': mapf_plan_time_ms,
            'fallback': mapf_fallback,  # Day6 validator 期望的字段名
            'mapf_fallback': mapf_fallback,  # 保留向后兼容
            'ugv_goals': ugv_goals,  # Day6 validator 期望的字段
            # Day8 Step 3: Relay 信息
            'relay_mode': relay_mode,
            'relay_target_cell': relay_target_cell,
            'relay_ugv_id': relay_ugv_id,
        }

        # 写入日志
        self.trace_logger.write_step(step_data)

    def _save_final_metrics(self) -> None:
        """保存最终指标到 metrics.json"""
        if self.state is None or self.metrics_logger is None:
            return

        # 计算基础指标
        steps = self.state.t
        tasks_completed = self.state.tasks_completed
        total_tasks = len(self.state.task_pool)
        active_tasks = len(self.state.get_active_tasks())
        outage_steps = self.state.outage_steps
        deadline_miss = self.state.deadline_miss
        tardiness_sum = self.state.tardiness_sum

        # 计算百分比和平均值
        outage_percent = (outage_steps / steps * 100) if steps > 0 else 0.0
        completion_rate = (tasks_completed / total_tasks * 100) if total_tasks > 0 else 0.0
        deadline_miss_rate = (deadline_miss / tasks_completed * 100) if tasks_completed > 0 else 0.0
        mean_tardiness = (tardiness_sum / deadline_miss) if deadline_miss > 0 else 0.0

        # 计算 SNR 统计
        snr_best_mean = (self.state.snr_sum / steps) if steps > 0 else 0.0
        snr_best_min = self.state.snr_min if self.state.snr_min != float('inf') else 0.0

        # Day8 Step 5: 计算 non-carrier SNR 统计
        outage_steps_nc = getattr(self.state, 'outage_steps_nc', 0)
        snr_sum_nc = getattr(self.state, 'snr_sum_nc', 0.0)
        snr_min_nc = getattr(self.state, 'snr_min_nc', float('inf'))

        outage_percent_nc = (outage_steps_nc / steps * 100) if steps > 0 else 0.0
        snr_best_mean_nc = (snr_sum_nc / steps) if steps > 0 else 0.0
        snr_best_min_nc = snr_min_nc if snr_min_nc != float('inf') else -float('inf')

        # Day8 Step 6.4: 计算 worst_nc SNR 统计（编队连通性）
        outage_steps_worst_nc = getattr(self.state, 'outage_steps_worst_nc', 0)
        snr_sum_worst_nc = getattr(self.state, 'snr_sum_worst_nc', 0.0)
        snr_min_worst_nc = getattr(self.state, 'snr_min_worst_nc', float('inf'))

        outage_percent_worst_nc = (outage_steps_worst_nc / steps * 100) if steps > 0 else 0.0
        snr_worst_mean_nc = (snr_sum_worst_nc / steps) if steps > 0 else 0.0
        snr_worst_min_nc = snr_min_worst_nc if snr_min_worst_nc != float('inf') else -float('inf')

        # 生成 run_id（如果未指定）
        if self.run_id is None:
            map_name = Path(self.map_path).stem if self.map_path != 'none' else 'nomap'
            self.run_id = f"{map_name}_N{self.n_ugv}_seed{self.seed}_lambda{self.arrival_rate}"

        # 获取 MAPF 统计（Day6.5）
        mapf_stats = {}
        if self.ugv_controller is not None:
            mapf_stats = self.ugv_controller.get_stats()

        # 计算 mean_step_motion
        mean_step_motion = (
            sum(self._step_motions) / len(self._step_motions)
            if self._step_motions else 0.0
        )

        # 构建指标字典
        metrics = {
            # A. 复现与实验管理
            'run_id': self.run_id,
            'method': self.method,
            'planner': self.planner,
            'map_path': self.map_path,
            'map_hash': self.map_hash if self.map_hash else "none",
            'seed': self.seed,
            'steps': steps,
            'K': self.mapf_K if self.mapf_K else self.decision_period,
            'H': self.mapf_H if self.mapf_H else 0,
            'budget_ms': self.mapf_budget_ms if self.mapf_budget_ms is not None else 0,
            'n_agents': self.n_ugv,

            # B. 任务质量
            'tasks_completed': tasks_completed,
            'total_tasks': total_tasks,
            'active_tasks': active_tasks,
            'completion_rate': round(completion_rate, 2),
            'deadline_miss': deadline_miss,
            'deadline_miss_rate': round(deadline_miss_rate, 2),
            'tardiness_sum': tardiness_sum,
            'mean_tardiness': round(mean_tardiness, 2),

            # C. 通信指标
            'outage_steps': outage_steps,
            'outage_percent': round(outage_percent, 2),
            'max_outage_streak': self._max_outage_streak,
            'snr_threshold': self.snr_threshold,
            'snr_best_mean': round(snr_best_mean, 2),
            'snr_best_min': round(snr_best_min, 2),
            # Day8 Step 5: 明确标注 all 指标
            'outage_steps_all': outage_steps,
            'outage_percent_all': round(outage_percent, 2),
            'snr_best_all_mean': round(snr_best_mean, 2),
            'snr_best_all_min': round(snr_best_min, 2),
            # Day8 Step 5: non-carrier 指标（主指标）
            'outage_steps_nc': outage_steps_nc,
            'outage_percent_nc': round(outage_percent_nc, 2),
            'snr_best_nc_mean': round(snr_best_mean_nc, 2),
            'snr_best_nc_min': round(snr_best_min_nc, 2),
            # Day8 Step 6.4: worst_nc 指标（编队连通性）
            'outage_steps_worst_nc': outage_steps_worst_nc,
            'outage_percent_worst_nc': round(outage_percent_worst_nc, 2),
            'snr_worst_nc_mean': round(snr_worst_mean_nc, 2),
            'snr_worst_nc_min': round(snr_worst_min_nc, 2),

            # D. 规划与执行
            'mapf_calls': mapf_stats.get('mapf_calls', 0),
            'mapf_success_calls': mapf_stats.get('mapf_success_calls', 0),
            'mapf_timeout_calls': mapf_stats.get('mapf_timeout_calls', 0),
            'mapf_fail_calls': mapf_stats.get('mapf_fail_calls', 0),
            'mapf_mean_plan_time_ms': round(mapf_stats.get('mapf_mean_plan_time_ms', 0.0), 2),
            'mapf_p95_plan_time_ms': round(mapf_stats.get('mapf_p95_plan_time_ms', 0.0), 2),
            'fallback_wait_steps': mapf_stats.get('fallback_wait_steps', 0),
            'collision_free': True,  # Day6.5: 如果有碰撞会抛异常，所以到这里一定是 True
            'expanded_nodes_total': mapf_stats.get('expanded_nodes_total', 0),
            'mapf_expanded_mean_per_call': round(mapf_stats.get('mapf_expanded_mean_per_call', 0.0), 2),
            'mean_step_motion': round(mean_step_motion, 4),

            # D2. 会合/回收
            'rendezvous_success': 0,
            'rendezvous_fail': 0,
            'emergency_landings': 0,
            'uav_loiter_steps': 0,
            'ugv_hold_steps': 0,

            # E. 性能与稳定性（runtime_sec 由 MetricsLogger 自动添加）
            'termination_reason': 'horizon',
        }

        # 保存指标
        self.metrics_logger.save_metrics(metrics)

        # 保存任务信息（用于 visualizer）
        self._save_tasks_json()

        # 关闭 trace logger
        if self.trace_logger:
            self.trace_logger.close()

    def _save_tasks_json(self) -> None:
        """保存任务信息到 tasks.json（用于 visualizer）"""
        if self.state is None or not self.enable_logging or not self.output_dir:
            return

        output_path = Path(self.output_dir)

        # 获取地图尺寸
        grid_width = self.grid_map.width if self.grid_map else 20
        grid_height = self.grid_map.height if self.grid_map else 20

        # 构建任务列表
        tasks_data = []
        for task in self.state.task_pool:
            # 将世界坐标转换为 grid 坐标
            if self.grid_map:
                cell = self.grid_map.world_to_cell(task.position[0], task.position[1])
            else:
                # 如果没有地图，假设简单的坐标映射
                cell = [int(task.position[1] * 5), int(task.position[0] * 5)]

            task_dict = {
                'id': task.task_id,
                'cell': cell,
                'release_t': task.arrival_time,
                'deadline_t': task.deadline,
                'completed_t': task.completion_time,
                'status': 'completed' if task.completed else (
                    'missed' if task.is_overdue(self.state.t) else 'active'
                )
            }
            tasks_data.append(task_dict)

        # 构建完整的 tasks.json 结构
        tasks_json = {
            'schema_version': 1,
            'grid': {
                'width': grid_width,
                'height': grid_height
            },
            'tasks': tasks_data
        }

        # 保存到文件
        import json as _json
        with open(output_path / "tasks.json", 'w') as f:
            _json.dump(tasks_json, f, indent=2)

    def close(self) -> None:
        """关闭环境并清理资源"""
        if self.trace_logger and self.trace_logger.is_open:
            self.trace_logger.close()

