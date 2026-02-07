"""
UAV 执行器

实现 UAV 状态机和移动逻辑
"""

from enum import Enum
from typing import Tuple, Optional
from dataclasses import dataclass


class UAVState(Enum):
    """UAV 状态枚举"""
    ONBOARD = "onboard"           # 在载机上（carrier_id）
    OUTBOUND = "outbound"         # 飞向任务点（task_id）
    SERVICING = "servicing"       # 服务任务（task_id, remaining_service）
    INBOUND = "inbound"           # 飞向会合点（rendezvous_cell, t_meet, window）
    EMERGENCY = "emergency"       # 紧急状态（target_cell）


@dataclass
class UAVExecutor:
    """
    UAV 执行器

    属性：
        uav_id: UAV ID
        cell: 当前位置 (i, j)
        state: 当前状态
        neighbor_mode: 邻接模式（默认 8）
        service_time: 服务时间（步数）
    """

    uav_id: int
    cell: Tuple[int, int]
    neighbor_mode: int = 8
    service_time: int = 2

    def __post_init__(self):
        """初始化后处理"""
        # 状态相关
        self.state = UAVState.ONBOARD
        self.carrier_id: Optional[int] = 0  # 默认在 0 号载机上

        # 任务相关
        self.current_task_id: Optional[int] = None
        self.remaining_service: int = 0

        # 目标相关
        self.target_cell: Optional[Tuple[int, int]] = None

        # 会合相关
        self.rendezvous_cell: Optional[Tuple[int, int]] = None
        self.t_meet: Optional[int] = None
        self.meet_window: int = 3

    def set_onboard(self, carrier_id: int, carrier_cell: Tuple[int, int]):
        """
        设置为 ONBOARD 状态

        Args:
            carrier_id: 载机 ID
            carrier_cell: 载机位置
        """
        self.state = UAVState.ONBOARD
        self.carrier_id = carrier_id
        self.cell = carrier_cell
        self.target_cell = None
        self.current_task_id = None

    def set_outbound(self, task_id: int, task_cell: Tuple[int, int]):
        """
        设置为 OUTBOUND 状态（飞向任务点）

        Args:
            task_id: 任务 ID
            task_cell: 任务位置
        """
        self.state = UAVState.OUTBOUND
        self.current_task_id = task_id
        self.target_cell = task_cell
        self.carrier_id = None

    def set_servicing(self, task_id: int):
        """
        设置为 SERVICING 状态（服务任务）

        Args:
            task_id: 任务 ID
        """
        self.state = UAVState.SERVICING
        self.current_task_id = task_id
        self.remaining_service = self.service_time
        self.target_cell = None

    def set_inbound(self, rendezvous_cell: Tuple[int, int], t_meet: int, window: int = 3):
        """
        设置为 INBOUND 状态（飞向会合点）

        Args:
            rendezvous_cell: 会合点位置
            t_meet: 预期会合时刻
            window: 会合时间窗（±window 步）
        """
        self.state = UAVState.INBOUND
        self.rendezvous_cell = rendezvous_cell
        self.target_cell = rendezvous_cell
        self.t_meet = t_meet
        self.meet_window = window

    def set_emergency(self, target_cell: Tuple[int, int]):
        """
        设置为 EMERGENCY 状态（飞向安全降落点）

        Args:
            target_cell: 安全降落点
        """
        self.state = UAVState.EMERGENCY
        self.target_cell = target_cell
        self.current_task_id = None
        self.rendezvous_cell = None

    def step(self, t: int) -> bool:
        """
        执行一步

        Args:
            t: 当前时刻

        Returns:
            是否需要外部处理（状态转换）
        """
        if self.state == UAVState.ONBOARD:
            # 在载机上，不移动
            return False

        elif self.state == UAVState.OUTBOUND:
            # 飞向任务点
            if self._is_at_target():
                # 到达任务点，准备服务
                return True  # 需要外部调用 set_servicing
            else:
                # 继续移动
                self._move_towards_target()
                return False

        elif self.state == UAVState.SERVICING:
            # 服务任务
            self.remaining_service -= 1
            if self.remaining_service <= 0:
                # 服务完成
                return True  # 需要外部调用 set_inbound
            return False

        elif self.state == UAVState.INBOUND:
            # 飞向会合点
            if self._is_at_target():
                # 到达会合点，等待 UGV
                return True  # 需要外部检查会合
            else:
                # 继续移动
                self._move_towards_target()
                return False

        elif self.state == UAVState.EMERGENCY:
            # 飞向安全降落点
            if self._is_at_target():
                # 到达安全点
                return True  # 需要外部处理
            else:
                # 继续移动
                self._move_towards_target()
                return False

        return False

    def _is_at_target(self) -> bool:
        """检查是否到达目标"""
        if self.target_cell is None:
            return False
        return self.cell == self.target_cell

    def _move_towards_target(self):
        """
        向目标移动一步（贪心 8 邻接）

        规则：
        - 计算 dx = sign(target_x - current_x)
        - 计算 dy = sign(target_y - current_y)
        - 移动到 (current_i + dy, current_j + dx)
        """
        if self.target_cell is None:
            return

        current_i, current_j = self.cell
        target_i, target_j = self.target_cell

        # 计算方向
        di = self._sign(target_i - current_i)
        dj = self._sign(target_j - current_j)

        # 移动
        if di != 0 or dj != 0:
            self.cell = (current_i + di, current_j + dj)

    @staticmethod
    def _sign(x: int) -> int:
        """符号函数"""
        if x > 0:
            return 1
        elif x < 0:
            return -1
        else:
            return 0

    def get_state(self) -> UAVState:
        """获取当前状态"""
        return self.state

    def get_position(self) -> Tuple[int, int]:
        """获取当前位置"""
        return self.cell

    def get_task_id(self) -> Optional[int]:
        """获取当前任务 ID"""
        return self.current_task_id

    def __repr__(self):
        return f"UAV({self.uav_id}) at {self.cell} [{self.state.value}]"
