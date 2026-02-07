"""
UAV-UGV 协同环境

整合所有组件：
- TaskStream: 任务流生成
- TaskManager: 任务管理
- UAVExecutor: UAV 执行器
- UGVCarrier: UGV 载机
- RendezvousPlanner: 会合规划器
- AStarPlanner: 路径规划器
"""

import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from ..map import GridMap
from ..comm import CommModel
from ..tasks import TaskStream, TaskManager, TaskConfig
from ..uav import UAVExecutor, UAVState
from ..ugv import UGVCarrier, UGVState
from ..rendezvous import RendezvousPlanner
from ..planning import AStarPlanner


@dataclass
class EnvConfig:
    """环境配置"""
    # Episode 配置
    horizon_steps: int = 500
    decision_period: int = 5  # K
    seed: int = 0

    # UAV 配置
    uav_speed: int = 1
    uav_neighbor_mode: int = 8
    uav_service_time: int = 2
    uav_meet_window: int = 3
    uav_max_loiter_steps: int = 20

    # UGV 配置
    ugv_speed: int = 1
    ugv_neighbor_mode: int = 4
    ugv_hold_steps: int = 5
    carrier_id: int = 0

    # Rendezvous 配置
    rendezvous_candidate_count: int = 12
    rendezvous_score_alpha_snr: float = 1.0
    rendezvous_score_beta_eta: float = 0.3

    # 同步出发配置
    sync_depart_enabled: bool = True
    sync_depart_buffer_steps: int = 2
    sync_depart_max_delay: int = 30
    sync_depart_min_trigger_gap: int = 1

    # 任务配置
    task_arrival_rate: float = 0.1
    task_deadline_min: int = 25
    task_deadline_max: int = 60
    task_max_active: int = 20
    task_top_m: int = 5

    # 通信配置
    comm_tx_power_db: float = 0.0
    comm_pathloss_n: float = 2.0
    comm_obstacle_penalty_db: float = 6.0
    comm_snr_threshold_db: float = -9.0


class CoopEnv:
    """
    UAV-UGV 协同环境

    功能：
    - 任务流生成和管理
    - UAV 飞行和任务执行
    - UGV 移动和会合
    - 会合规划和协调
    - Emergency 处理
    """

    def __init__(self, grid_map: GridMap, config: EnvConfig):
        """
        初始化环境

        Args:
            grid_map: 地图对象
            config: 环境配置
        """
        self.grid_map = grid_map
        self.config = config

        # 设置随机种子
        random.seed(config.seed)

        # 创建通信模型
        self.comm_model = CommModel(
            grid_map=grid_map,
            tx_power_db=config.comm_tx_power_db,
            pathloss_n=config.comm_pathloss_n,
            obstacle_penalty_db=config.comm_obstacle_penalty_db,
            snr_threshold_db=config.comm_snr_threshold_db
        )

        # 创建任务系统
        task_config = TaskConfig(
            enabled=True,
            arrival_rate=config.task_arrival_rate,
            deadline_min=config.task_deadline_min,
            deadline_max=config.task_deadline_max,
            max_active=config.task_max_active,
            top_m=config.task_top_m,
            service_time=config.uav_service_time
        )
        self.task_stream = TaskStream(task_config, grid_map.free_cells, seed=config.seed)
        self.task_manager = TaskManager(
            max_active=config.task_max_active,
            top_m=config.task_top_m,
            seed=config.seed
        )

        # 创建 UAV
        start_cell = grid_map.free_cells[0]
        self.uav = UAVExecutor(
            uav_id=0,
            cell=start_cell,
            neighbor_mode=config.uav_neighbor_mode,
            service_time=config.uav_service_time
        )
        self.uav.set_onboard(carrier_id=config.carrier_id, carrier_cell=start_cell)

        # 创建 UGV Carrier
        self.carrier = UGVCarrier(
            ugv_id=config.carrier_id,
            cell=start_cell,
            neighbor_mode=config.ugv_neighbor_mode,
            hold_steps=config.ugv_hold_steps
        )

        # 创建会合规划器
        self.rendezvous_planner = RendezvousPlanner(
            grid_map=grid_map,
            comm_model=self.comm_model,
            candidate_count=config.rendezvous_candidate_count,
            score_alpha_snr=config.rendezvous_score_alpha_snr,
            score_beta_eta=config.rendezvous_score_beta_eta,
            meet_window=config.uav_meet_window,
            seed=config.seed,
            # 同步出发参数
            sync_depart_enabled=config.sync_depart_enabled,
            sync_depart_buffer=config.sync_depart_buffer_steps,
            sync_depart_max_delay=config.sync_depart_max_delay,
            sync_depart_min_gap=config.sync_depart_min_trigger_gap,
            uav_service_time=config.uav_service_time,
            uav_neighbor_mode=config.uav_neighbor_mode,
            ugv_neighbor_mode=config.ugv_neighbor_mode
        )

        # 创建路径规划器
        self.path_planner = AStarPlanner(grid_map)

        # 安全降落点（从候选会合点中选择）
        self.safe_landing_sites = self.rendezvous_planner.get_candidates()

        # 当前会合计划
        self.current_rendezvous = None

        # 统计信息
        self.t = 0

        # 会合统计（细化）
        self.clean_rendezvous_count = 0  # 不触发 emergency 的干净会合
        self.emergency_recovery_count = 0  # 触发 emergency 后成功回收
        self.emergency_landing_count = 0  # emergency 触发次数
        self.meet_delays = []  # 记录会合延迟（所有成功会合）

        # 等待统计（细化）
        self.uav_wait_times = []  # UAV 在会合点等待时间
        self.ugv_wait_times = []  # UGV 在会合点等待时间
        self.current_uav_wait = 0  # 当前 UAV 等待计数
        self.current_ugv_wait = 0  # 当前 UGV 等待计数

        # 同步出发统计
        self.depart_delays = []  # 记录每次的延迟出发量
        self.rendezvous_attempt_count = 0  # 会合尝试次数（每次生成 plan +1）

        # 到达时间戳记录（事件驱动，更精确）
        self.t_uav_arrive_r = None  # UAV 首次到达会合点的时刻
        self.t_ugv_arrive_r = None  # UGV 首次到达会合点的时刻
        self.t_board = None  # 成功上车的时刻

        # 到达时间统计（用于计算 arrival_gap）
        self.arrival_pairs = []  # [(t_uav, t_ugv), ...] 配对的到达时间
        self.arrival_uav_only_count = 0  # 只有 UAV 到达的次数
        self.arrival_ugv_only_count = 0  # 只有 UGV 到达的次数

        # 晚会合统计（拆分为两个明确指标）
        self.ugv_late_arrival_count = 0  # UGV 比 UAV 晚到会合点的次数
        self.late_board_count = 0  # 上车时间超出 planned_window 的次数

        # Trace 记录
        self.trace = []

    def reset(self):
        """重置环境"""
        self.t = 0
        self.task_stream = TaskStream(
            TaskConfig(
                enabled=True,
                arrival_rate=self.config.task_arrival_rate,
                deadline_min=self.config.task_deadline_min,
                deadline_max=self.config.task_deadline_max,
                max_active=self.config.task_max_active,
                top_m=self.config.task_top_m,
                service_time=self.config.uav_service_time
            ),
            self.grid_map.free_cells,
            seed=self.config.seed
        )
        self.task_manager.reset()

        start_cell = self.grid_map.free_cells[0]
        self.uav.set_onboard(carrier_id=self.config.carrier_id, carrier_cell=start_cell)
        self.carrier.set_idle()
        self.carrier.cell = start_cell

        self.current_rendezvous = None

        # 会合统计（细化）
        self.clean_rendezvous_count = 0
        self.emergency_recovery_count = 0
        self.emergency_landing_count = 0
        self.meet_delays = []

        # 等待统计（细化）
        self.uav_wait_times = []
        self.ugv_wait_times = []
        self.current_uav_wait = 0
        self.current_ugv_wait = 0

        # 同步出发统计
        self.depart_delays = []
        self.rendezvous_attempt_count = 0

        # 到达时间戳记录（事件驱动，更精确）
        self.t_uav_arrive_r = None
        self.t_ugv_arrive_r = None
        self.t_board = None

        # 到达时间统计
        self.arrival_pairs = []
        self.arrival_uav_only_count = 0
        self.arrival_ugv_only_count = 0

        # 晚会合统计
        self.ugv_late_arrival_count = 0
        self.late_board_count = 0

        self.trace = []

    def step(self):
        """执行一步"""
        # 1. 生成新任务
        new_tasks = self.task_stream.generate_tasks(self.t, self.task_manager.num_active)
        for task in new_tasks:
            self.task_manager.add_task(task)

        # 2. 过期任务
        self.task_manager.expire_overdue_tasks(self.t)

        # 3. 决策时刻：分配任务
        if self.t % self.config.decision_period == 0:
            self._make_decision()

        # 4. UAV 执行
        self._uav_step()

        # 5. UGV 执行
        self._ugv_step()

        # 6. 检查会合
        self._check_rendezvous()

        # 7. 检查 Emergency
        self._check_emergency()

        # 8. 记录 trace
        self._record_trace()

        self.t += 1

    def _make_decision(self):
        """决策时刻：分配任务"""
        # 只有 UAV 在 ONBOARD 状态才能分配新任务
        if self.uav.get_state() != UAVState.ONBOARD:
            return

        # 获取 Top-M 任务（EDF 策略）
        top_tasks = self.task_manager.get_top_m(self.t, policy="earliest_deadline")

        if not top_tasks:
            return

        # 选择第一个任务（EDF）
        task = top_tasks[0]

        # 标记任务为已分配
        self.task_manager.mark_assigned(task.id, self.t)

        # UAV 飞向任务点
        self.uav.set_outbound(task_id=task.id, task_cell=task.cell)

        # 规划会合点（包含同步出发计算）
        rendezvous_plan = self.rendezvous_planner.plan(
            t_now=self.t,
            task_cell=task.cell,
            ugv_carrier_pos=self.carrier.get_position(),
            uav_pos=self.uav.get_position()
        )

        if rendezvous_plan:
            self.current_rendezvous = rendezvous_plan

            # 记录会合尝试次数
            self.rendezvous_attempt_count += 1

            # 记录延迟出发量
            if rendezvous_plan.depart_delay > 0:
                self.depart_delays.append(rendezvous_plan.depart_delay)

            # UGV 移动到会合点
            path, success = self.path_planner.plan(
                start=self.carrier.get_position(),
                goal=rendezvous_plan.rendezvous_cell,
                neighbor_mode=self.config.ugv_neighbor_mode
            )

            if success and path:
                # 检查是否需要延迟出发
                if rendezvous_plan.depart_delay > 0:
                    # UGV 先等待，然后再移动
                    self.carrier.set_wait_before_depart(
                        rendezvous_cell=rendezvous_plan.rendezvous_cell,
                        path=path,
                        depart_delay=rendezvous_plan.depart_delay
                    )
                else:
                    # 立即出发
                    self.carrier.set_moving_to_rendezvous(
                        rendezvous_cell=rendezvous_plan.rendezvous_cell,
                        path=path
                    )

        # 记录事件
        self.current_event = "assign_task"

    def _uav_step(self):
        """UAV 执行一步"""
        state = self.uav.get_state()

        if state == UAVState.ONBOARD:
            # 在载机上，跟随载机移动
            self.uav.cell = self.carrier.get_position()

        elif state == UAVState.OUTBOUND:
            # 飞向任务点
            need_action = self.uav.step(self.t)
            if need_action:
                # 到达任务点，开始服务
                self.uav.set_servicing(task_id=self.uav.current_task_id)

        elif state == UAVState.SERVICING:
            # 服务任务
            need_action = self.uav.step(self.t)
            if need_action:
                # 服务完成，检查任务是否已过期
                task = self.task_manager.get_task(self.uav.current_task_id)
                if task and task.status != "expired":
                    # 任务未过期，标记完成
                    self.task_manager.mark_completed(self.uav.current_task_id, self.t)

                    # 记录事件
                    self.current_event = "task_done"

                    # 飞向会合点
                    if self.current_rendezvous:
                        self.uav.set_inbound(
                            rendezvous_cell=self.current_rendezvous.rendezvous_cell,
                            t_meet=self.current_rendezvous.t_meet,
                            window=self.current_rendezvous.window
                        )
                else:
                    # 任务已过期，直接返回
                    self.uav.set_onboard(
                        carrier_id=self.config.carrier_id,
                        carrier_cell=self.carrier.get_position()
                    )

        elif state == UAVState.INBOUND:
            # 飞向会合点
            need_action = self.uav.step(self.t)
            if need_action:
                # 到达会合点，等待 UGV（在 _check_rendezvous 中处理）
                pass

            # 记录 UAV 首次到达会合点的时间（事件驱动）
            if self.uav._is_at_target() and self.t_uav_arrive_r is None:
                if self.current_rendezvous and self.uav.get_position() == self.current_rendezvous.rendezvous_cell:
                    self.t_uav_arrive_r = self.t

            # 统计 UAV 等待时间（到达会合点后）
            if self.uav._is_at_target():
                self.current_uav_wait += 1

        elif state == UAVState.EMERGENCY:
            # Emergency 状态，飞向安全降落点
            need_action = self.uav.step(self.t)
            if need_action:
                # 到达安全降落点，等待 UGV（在 _check_rendezvous 中处理）
                pass

    def _ugv_step(self):
        """UGV 执行一步"""
        state = self.carrier.get_state()

        if state == UGVState.IDLE:
            # 空闲，不移动
            pass

        elif state == UGVState.WAIT_BEFORE_DEPART:
            # 延迟出发等待中（UGV 会自动切换到 MOVING 状态）
            self.carrier.step(self.t)

        elif state == UGVState.MOVING_TO_RENDEZVOUS:
            # 移动到会合点
            need_action = self.carrier.step(self.t)

            # 记录 UGV 首次到达会合点的时间（事件驱动）
            if self.t_ugv_arrive_r is None:
                if self.current_rendezvous and self.carrier.get_position() == self.current_rendezvous.rendezvous_cell:
                    self.t_ugv_arrive_r = self.t

            if need_action:
                # 到达会合点，开始等待
                self.carrier.set_holding()

        elif state == UGVState.HOLDING:
            # 在会合点等待
            need_action = self.carrier.step(self.t)
            # 累计等待步数
            self.current_ugv_wait += 1
            if need_action:
                # 等待时间到（在 _check_rendezvous 中处理会合）
                pass

        elif state == UGVState.MEETING:
            # 会合中，不移动
            pass

    def _check_rendezvous(self):
        """检查会合"""
        # 只有 UAV 在 INBOUND 或 EMERGENCY 状态才检查会合
        uav_state = self.uav.get_state()
        if uav_state not in [UAVState.INBOUND, UAVState.EMERGENCY]:
            return

        # 检查 UAV 和 UGV 是否都在会合点
        uav_pos = self.uav.get_position()
        ugv_pos = self.carrier.get_position()

        if uav_pos != ugv_pos:
            # 未在同一位置
            return

        # 在同一位置，检查时间窗
        if self.current_rendezvous:
            t_meet = self.current_rendezvous.t_meet
            window = self.current_rendezvous.window

            if abs(self.t - t_meet) <= window:
                # 会合成功
                self._handle_rendezvous_success()
            else:
                # 超出时间窗，但已在同一位置，也算成功（宽松处理）
                self._handle_rendezvous_success()
        else:
            # Emergency 情况，直接回收
            self._handle_rendezvous_success()

    def _handle_rendezvous_success(self):
        """处理会合成功"""
        # 记录上车时刻
        self.t_board = self.t

        # 记录会合延迟（基于上车时刻）
        if self.current_rendezvous:
            meet_delay = abs(self.t_board - self.current_rendezvous.t_meet)
            self.meet_delays.append(meet_delay)

        # 计算并记录等待时间（基于到达时间戳）
        if self.t_uav_arrive_r is not None:
            uav_wait = self.t_board - self.t_uav_arrive_r
            if uav_wait > 0:
                self.uav_wait_times.append(uav_wait)

        if self.t_ugv_arrive_r is not None:
            ugv_wait = self.t_board - self.t_ugv_arrive_r
            if ugv_wait > 0:
                self.ugv_wait_times.append(ugv_wait)

        # 记录到达时间对（用于计算 arrival_gap）
        if self.t_uav_arrive_r is not None and self.t_ugv_arrive_r is not None:
            self.arrival_pairs.append((self.t_uav_arrive_r, self.t_ugv_arrive_r))

            # 记录 UGV 晚到次数（UGV 比 UAV 晚到会合点）
            if self.t_ugv_arrive_r > self.t_uav_arrive_r:
                self.ugv_late_arrival_count += 1

        elif self.t_uav_arrive_r is not None:
            self.arrival_uav_only_count += 1
        elif self.t_ugv_arrive_r is not None:
            self.arrival_ugv_only_count += 1

        # 记录晚上车次数（上车时间超出 planned_window）
        if self.current_rendezvous:
            meet_delay = abs(self.t_board - self.current_rendezvous.t_meet)
            if meet_delay > self.current_rendezvous.window:
                self.late_board_count += 1

        # 区分干净会合 vs emergency 回收
        if self.uav.get_state() == UAVState.EMERGENCY:
            # Emergency 回收
            self.emergency_recovery_count += 1
        else:
            # 干净会合（未触发 emergency）
            self.clean_rendezvous_count += 1
            self.current_event = "meet_success"

        # 重置时间戳和等待计数
        self.current_uav_wait = 0
        self.current_ugv_wait = 0
        self.t_uav_arrive_r = None
        self.t_ugv_arrive_r = None
        self.t_board = None

        # UAV 回到载机
        self.uav.set_onboard(
            carrier_id=self.config.carrier_id,
            carrier_cell=self.carrier.get_position()
        )

        # UGV 回到 IDLE
        self.carrier.set_idle()

        # 清除会合计划
        self.current_rendezvous = None

    def _check_emergency(self):
        """检查 Emergency 条件"""
        # 只有 UAV 在 INBOUND 状态才检查 Emergency
        if self.uav.get_state() != UAVState.INBOUND:
            return

        # 检查 UAV 等待超时
        if self.current_uav_wait > self.config.uav_max_loiter_steps:
            self._trigger_emergency()
            return

        # 检查时间窗超时
        if self.current_rendezvous:
            t_meet = self.current_rendezvous.t_meet
            window = self.current_rendezvous.window
            slack = 5

            if self.t > t_meet + window + slack:
                self._trigger_emergency()

    def _trigger_emergency(self):
        """触发 Emergency"""
        self.emergency_landing_count += 1

        # 重置等待计数和到达时间戳（emergency 触发时）
        self.current_uav_wait = 0
        self.current_ugv_wait = 0
        self.t_uav_arrive_r = None
        self.t_ugv_arrive_r = None
        self.t_board = None

        # 选择最近的安全降落点
        uav_pos = self.uav.get_position()
        safe_site = min(
            self.safe_landing_sites,
            key=lambda s: max(abs(s[0] - uav_pos[0]), abs(s[1] - uav_pos[1]))
        )

        # UAV 飞向安全降落点
        self.uav.set_emergency(target_cell=safe_site)

        # UGV 移动到安全降落点
        path, success = self.path_planner.plan(
            start=self.carrier.get_position(),
            goal=safe_site,
            neighbor_mode=self.config.ugv_neighbor_mode
        )

        if success and path:
            self.carrier.set_moving_to_rendezvous(
                rendezvous_cell=safe_site,
                path=path
            )

        # 记录事件
        self.current_event = "emergency_land"

    def _record_trace(self):
        """记录 trace"""
        # 获取当前状态
        trace_entry = {
            't': self.t,
            'uav_state': self.uav.get_state().value,
            'uav_cell': self.uav.get_position(),
            'carrier_cell': self.carrier.get_position(),
            'carrier_state': self.carrier.get_state().value,
            'current_task_id': self.uav.current_task_id,
            'num_active_tasks': self.task_manager.num_active,
            'num_completed_tasks': self.task_manager.num_done,
            'num_expired_tasks': self.task_manager.num_expired,
        }

        # 会合信息
        if self.current_rendezvous:
            trace_entry['rendezvous_cell'] = self.current_rendezvous.rendezvous_cell
            trace_entry['t_meet'] = self.current_rendezvous.t_meet
            trace_entry['meet_window'] = self.current_rendezvous.window
            trace_entry['depart_delay'] = self.current_rendezvous.depart_delay
            trace_entry['eta_uav_est'] = self.current_rendezvous.eta_uav_est
            trace_entry['eta_ugv_est'] = self.current_rendezvous.eta_ugv_est
        else:
            trace_entry['rendezvous_cell'] = None
            trace_entry['t_meet'] = None
            trace_entry['meet_window'] = None
            trace_entry['depart_delay'] = None
            trace_entry['eta_uav_est'] = None
            trace_entry['eta_ugv_est'] = None

        # 事件（如果有）
        trace_entry['event'] = getattr(self, 'current_event', None)

        # 清除事件标志
        self.current_event = None

        self.trace.append(trace_entry)

    def get_metrics(self) -> Dict:
        """获取统计指标"""
        task_stats = self.task_manager.get_stats()
        stream_stats = self.task_stream.get_stats()

        # 计算任务守恒
        total_generated = stream_stats['total_generated']
        total_dropped = stream_stats['total_dropped']
        total_completed = task_stats['total_completed']
        total_expired = task_stats['total_expired']
        total_pending_end = self.task_manager.num_active  # episode 结束时仍在系统中的任务

        # 计算 airborne 步数（UAV 不在载机上的步数）
        airborne_steps = sum(1 for entry in self.trace if entry.get('uav_state') != 'onboard')

        # 计算会合成功率（干净会合）
        total_rendezvous_attempts = self.clean_rendezvous_count + self.emergency_landing_count
        clean_rendezvous_rate = self.clean_rendezvous_count / max(1, total_rendezvous_attempts)

        metrics = {
            # 任务统计（守恒）
            'total_generated': total_generated,
            'total_dropped': total_dropped,
            'total_completed': total_completed,
            'total_expired': total_expired,
            'total_pending_end': total_pending_end,  # 新增
            'completion_rate': task_stats['completion_rate'],
            'miss_rate': task_stats['expiration_rate'],
            'mean_tardiness': task_stats['avg_tardiness'],

            # 完成时间分布
            'mean_completion_time': task_stats.get('mean_completion_time', 0.0),
            'p95_completion_time': task_stats.get('p95_completion_time', 0.0),

            # Slack 分析
            'mean_slack_at_assignment': task_stats.get('mean_slack_at_assignment', 0.0),
            'mean_slack_at_completion': task_stats.get('mean_slack_at_completion', 0.0),

            # 会合统计（细化）
            'clean_rendezvous': self.clean_rendezvous_count,  # 不触发 emergency 的干净会合
            'emergency_recovery': self.emergency_recovery_count,  # emergency 后成功回收
            'emergency_landings': self.emergency_landing_count,  # emergency 触发次数
            'total_rendezvous_attempts': total_rendezvous_attempts,  # 总会合尝试次数
            'clean_rendezvous_rate': clean_rendezvous_rate,  # 干净会合率
            'emergency_rate': self.emergency_landing_count / max(1, total_rendezvous_attempts),  # emergency 率

            # 会合延迟统计（软目标语义）
            'mean_meet_delay': sum(self.meet_delays) / len(self.meet_delays) if self.meet_delays else 0.0,
            'max_meet_delay': max(self.meet_delays) if self.meet_delays else 0.0,
            'p95_meet_delay': sorted(self.meet_delays)[int(len(self.meet_delays) * 0.95)] if len(self.meet_delays) > 0 else 0.0,
            'planned_window': self.config.uav_meet_window,  # 改名：明确这是计划窗口，非硬约束

            # 等待统计（细化）
            'mean_uav_wait_at_r': sum(self.uav_wait_times) / len(self.uav_wait_times) if self.uav_wait_times else 0.0,
            'mean_ugv_wait_at_r': sum(self.ugv_wait_times) / len(self.ugv_wait_times) if self.ugv_wait_times else 0.0,
            'max_uav_wait_at_r': max(self.uav_wait_times) if self.uav_wait_times else 0,
            'max_ugv_wait_at_r': max(self.ugv_wait_times) if self.ugv_wait_times else 0,
            'total_uav_wait_steps': sum(self.uav_wait_times),
            'total_ugv_wait_steps': sum(self.ugv_wait_times),

            # 同步出发统计（新增）
            'mean_depart_delay': sum(self.depart_delays) / len(self.depart_delays) if self.depart_delays else 0.0,
            'max_depart_delay': max(self.depart_delays) if self.depart_delays else 0,
            'total_delayed_departs': len(self.depart_delays),  # 触发延迟出发的次数
            'depart_delay_trigger_rate': len(self.depart_delays) / max(1, self.rendezvous_attempt_count),  # 延迟出发触发率

            # 到达时间差统计（修复空样本问题，明确定义）
            'rendezvous_attempt_count': self.rendezvous_attempt_count,  # 会合尝试次数（每次生成 plan +1）
            'arrival_pair_count': len(self.arrival_pairs),  # 有效到达对数量（成功会合样本）
            'arrival_pair_rate': len(self.arrival_pairs) / max(1, self.rendezvous_attempt_count),  # 到达对比例
            'arrival_uav_only_count': self.arrival_uav_only_count,  # 只有 UAV 到达
            'arrival_ugv_only_count': self.arrival_ugv_only_count,  # 只有 UGV 到达
            'mean_arrival_gap': self._compute_mean_arrival_gap(),  # UAV 和 UGV 到达时间差的均值

            # 晚会合统计（拆分为两个明确指标）
            'ugv_late_arrival_count': self.ugv_late_arrival_count,  # UGV 比 UAV 晚到会合点的次数
            'ugv_late_arrival_rate': self.ugv_late_arrival_count / max(1, len(self.arrival_pairs)),  # UGV 晚到率
            'late_board_count': self.late_board_count,  # 上车时间超出 planned_window 的次数
            'late_board_rate': self.late_board_count / max(1, total_rendezvous_attempts),  # 晚上车率

            # 通信统计口径
            'airborne_steps': airborne_steps,  # 明确 UAV 离开载机的步数
            'total_steps': len(self.trace),
        }

        return metrics

    def _compute_mean_arrival_gap(self) -> float:
        """
        计算 UAV 和 UGV 到达会合点的时间差均值

        正值：UGV 晚到（t_ugv > t_uav）
        负值：UGV 早到（t_ugv < t_uav）
        """
        if len(self.arrival_pairs) == 0:
            return 0.0

        gaps = [t_ugv - t_uav for t_uav, t_ugv in self.arrival_pairs]
        return sum(gaps) / len(gaps)

    def run_episode(self) -> Dict:
        """运行完整 episode"""
        self.reset()

        for _ in range(self.config.horizon_steps):
            self.step()

        return self.get_metrics()

    def get_trace(self) -> List[Dict]:
        """获取 trace 记录"""
        return self.trace

    def save_trace(self, filepath: str):
        """保存 trace 到文件"""
        import json
        with open(filepath, 'w') as f:
            json.dump(self.trace, f, indent=2, ensure_ascii=False)
