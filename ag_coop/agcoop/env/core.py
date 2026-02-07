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
            except Exception as e:
                print(f"警告：无法加载地图 {self.map_path}: {e}")
                print("将使用简单随机通信模型")
                self.grid_map = None

        # 初始化状态
        self.state = SystemState()
        self.state.t = 0

        # 初始化 UGV 位置
        # 如果启用 MAPF 且有地图，从地图中采样不同的空闲位置
        if self.mapf_enabled and self.grid_map is not None:
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
                # 空闲位置不足，回退到原点
                print(f"警告：空闲位置不足 ({len(free_cells)} < {self.n_ugv})，使用原点")
                self.state.ugv_positions = [(0.0, 0.0) for _ in range(self.n_ugv)]
        else:
            # Day1: 所有 UGV 从原点开始
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

        # 初始化 MAPF controller（Day6.5）
        if self.mapf_enabled and self.grid_map is not None:
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

            # 初始化 UGV starts 和 goals
            # 将 float 位置转换为 int cell 坐标
            starts = {}
            for i, pos in enumerate(self.state.ugv_positions):
                cell = self.grid_map.world_to_cell(pos[0], pos[1])
                starts[i] = cell

            # 暂时使用固定巡逻点作为 goals（后续可以改为动态任务/会合点）
            # 简单策略：每个 UGV 的目标是地图中心附近的随机点
            goals = {}
            center_x = self.grid_map.width // 2
            center_y = self.grid_map.height // 2
            for i in range(self.n_ugv):
                # 在中心附近随机偏移
                offset_x = self.rng.randint(-5, 6)
                offset_y = self.rng.randint(-5, 6)
                goal_x = max(0, min(self.grid_map.width - 1, center_x + offset_x))
                goal_y = max(0, min(self.grid_map.height - 1, center_y + offset_y))

                # 确保目标是空闲格子
                if self.grid_map.is_free(goal_x, goal_y):
                    goals[i] = (goal_x, goal_y)
                else:
                    # 如果不是空闲格子，使用起点作为目标（原地不动）
                    goals[i] = starts[i]

            # 重置 controller
            self.ugv_controller.reset(starts, goals)

            # 执行初始规划（t=0）
            initial_plan_info = self.ugv_controller.maybe_replan(0, starts)

            print(f"MAPF Controller 初始化: K={self.mapf_K}, H={self.mapf_H}, budget={self.mapf_budget_ms}ms")
            if initial_plan_info.called:
                if initial_plan_info.success:
                    print(f"  初始规划成功 ({initial_plan_info.plan_time_ms:.2f} ms)")
                else:
                    print(f"  初始规划失败: {initial_plan_info.termination_reason}")
        else:
            self.ugv_controller = None
            self.mapf_wrapper = None

        # 初始化日志记录器
        if self.enable_logging and self.output_dir:
            from agcoop.utils.logger import TraceLogger, MetricsLogger
            from agcoop.utils.io import save_resolved_config, compute_file_hash

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

        # 时间步进
        self.state.t += 1

        # UGV 动作生成（Day6.5: 使用 MAPF controller）
        mapf_plan_info = None
        mapf_step_info = None

        if self.ugv_controller is not None:
            # 获取当前 UGV 位置（cell 坐标）
            current_positions = {}
            for i, pos in enumerate(self.state.ugv_positions):
                cell = self.grid_map.world_to_cell(pos[0], pos[1])
                current_positions[i] = cell

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
        生成新任务（Day1 简单版本）

        按 arrival_rate 概率生成任务，位置随机，deadline 随机。
        """
        if self.rng.random() < self.arrival_rate:
            # 随机位置
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
        简单的任务完成规则（Day1 测试用）

        规则：如果任务位置在 (0,0) 附近（距离 < 5.0），则立即完成。
        这只是为了测试指标链路，Day2+ 会实现真实的任务完成逻辑。
        """
        completion_radius = 5.0

        for task in self.state.get_active_tasks():
            # 计算任务到 (0,0) 的距离
            dist = np.sqrt(task.position[0]**2 + task.position[1]**2)

            if dist < completion_radius:
                # 完成任务
                self.state.complete_task(task.task_id, self.state.t)

    def _update_outage(self) -> Tuple[float, bool]:
        """
        更新 outage 指标（使用真实通信模型）

        Returns:
            (snr_best, outage) 元组
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
        ugv_cells = []
        for ugv_pos in self.state.ugv_positions:
            ugv_cell = self.grid_map.world_to_cell(ugv_pos[0], ugv_pos[1])
            ugv_cells.append(ugv_cell)

        # 计算最佳 SNR
        snr_best, best_ugv_id, outage = compute_best_snr(
            uav_cell, ugv_cells, self.grid_map, self.comm_config
        )

        # 更新累计指标
        if outage:
            self.state.outage_steps += 1

        self.state.snr_sum += snr_best
        self.state.snr_min = min(self.state.snr_min, snr_best)

        return snr_best, outage

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
        # 标准 Receding Horizon: t=1 立即规划，然后每 K 步重新规划
        # 即 t=1, 1+K, 1+2K, 1+3K, ... = 1, 6, 11, 16, ... (K=5)
        decision_step = ((self.state.t - 1) % self.decision_period == 0)

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

        # 构建步骤数据（包含预留字段）
        step_data = {
            't': self.state.t,
            'ugv_pos': self.state.ugv_positions,
            'ugv_positions': self.state.ugv_positions,  # Day6 collision checker 期望的字段名
            'uav_state': self.state.uav_onboard_ugv_id,
            'num_tasks_in_pool': len(self.state.task_pool),
            'num_active_tasks': len(self.state.get_active_tasks()),
            'task_completed_ids': [],  # Day1 占位
            'outage': outage_this_step,
            'snr_best': round(snr_best, 2),  # 真实 SNR 值
            'decision_step': decision_step,
            'chosen_task_id': None,  # Day1 占位
            'chosen_rendezvous': None,  # Day1 占位
            'mapf_called': mapf_called,
            'mapf_success': mapf_success,
            'mapf_plan_time_ms': mapf_plan_time_ms,
            'fallback': mapf_fallback,  # Day6 validator 期望的字段名
            'mapf_fallback': mapf_fallback,  # 保留向后兼容
            'ugv_goals': ugv_goals,  # Day6 validator 期望的字段
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

        # 生成 run_id（如果未指定）
        if self.run_id is None:
            map_name = Path(self.map_path).stem if self.map_path != 'none' else 'nomap'
            self.run_id = f"{map_name}_N{self.n_ugv}_seed{self.seed}_lambda{self.arrival_rate}"

        # 获取 MAPF 统计（Day6.5）
        mapf_stats = {}
        if self.ugv_controller is not None:
            mapf_stats = self.ugv_controller.get_stats()

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

        # 关闭 trace logger
        if self.trace_logger:
            self.trace_logger.close()

    def close(self) -> None:
        """关闭环境并清理资源"""
        if self.trace_logger and self.trace_logger.is_open:
            self.trace_logger.close()

