"""
UGV Carrier（载机）

实现载机 UGV 的状态机和移动逻辑
"""

from enum import Enum
from typing import Tuple, List, Optional
from dataclasses import dataclass


class UGVState(Enum):
    """UGV 状态枚举"""
    IDLE = "idle"                          # 空闲
    WAIT_BEFORE_DEPART = "wait_depart"     # 延迟出发前等待
    MOVING_TO_RENDEZVOUS = "moving"        # 移动到会合点
    HOLDING = "holding"                    # 在会合点等待
    MEETING = "meeting"                    # 会合中


@dataclass
class UGVCarrier:
    """
    UGV Carrier（载机）

    属性：
        ugv_id: UGV ID
        cell: 当前位置 (i, j)
        neighbor_mode: 邻接模式（默认 4）
        hold_steps: 会合点等待时间（步数）
    """

    ugv_id: int
    cell: Tuple[int, int]
    neighbor_mode: int = 4
    hold_steps: int = 5

    def __post_init__(self):
        """初始化后处理"""
        # 状态相关
        self.state = UGVState.IDLE

        # 路径相关
        self.path: Optional[List[Tuple[int, int]]] = None
        self.path_index: int = 0

        # 会合相关
        self.rendezvous_cell: Optional[Tuple[int, int]] = None
        self.hold_counter: int = 0

        # 延迟出发相关
        self.depart_delay_remaining: int = 0

    def set_idle(self):
        """设置为 IDLE 状态"""
        self.state = UGVState.IDLE
        self.path = None
        self.path_index = 0
        self.rendezvous_cell = None
        self.hold_counter = 0
        self.depart_delay_remaining = 0

    def set_wait_before_depart(self, rendezvous_cell: Tuple[int, int], path: List[Tuple[int, int]], depart_delay: int):
        """
        设置为 WAIT_BEFORE_DEPART 状态（延迟出发前等待）

        Args:
            rendezvous_cell: 会合点位置
            path: 路径列表 [(i, j), ...]
            depart_delay: 延迟出发时间（步数）
        """
        self.state = UGVState.WAIT_BEFORE_DEPART
        self.rendezvous_cell = rendezvous_cell
        self.path = path
        self.path_index = 0
        self.hold_counter = 0
        self.depart_delay_remaining = depart_delay

    def set_moving_to_rendezvous(self, rendezvous_cell: Tuple[int, int], path: List[Tuple[int, int]]):
        """
        设置为 MOVING_TO_RENDEZVOUS 状态

        Args:
            rendezvous_cell: 会合点位置
            path: 路径列表 [(i, j), ...]
        """
        self.state = UGVState.MOVING_TO_RENDEZVOUS
        self.rendezvous_cell = rendezvous_cell
        self.path = path
        self.path_index = 0
        self.hold_counter = 0
        self.depart_delay_remaining = 0

    def set_holding(self):
        """设置为 HOLDING 状态（在会合点等待）"""
        self.state = UGVState.HOLDING
        self.hold_counter = 0

    def set_meeting(self):
        """设置为 MEETING 状态（会合中）"""
        self.state = UGVState.MEETING

    def step(self, t: int) -> bool:
        """
        执行一步

        Args:
            t: 当前时刻

        Returns:
            是否需要外部处理（状态转换）
        """
        if self.state == UGVState.IDLE:
            # 空闲，不移动
            return False

        elif self.state == UGVState.WAIT_BEFORE_DEPART:
            # 延迟出发前等待
            self.depart_delay_remaining -= 1
            if self.depart_delay_remaining <= 0:
                # 延迟结束，自动切换到 MOVING 状态
                self.state = UGVState.MOVING_TO_RENDEZVOUS
                # 不返回 True，继续执行移动逻辑
                # 注意：这里不立即移动，下一步才开始移动
            return False

        elif self.state == UGVState.MOVING_TO_RENDEZVOUS:
            # 移动到会合点
            if self._is_at_rendezvous():
                # 到达会合点，准备等待
                return True  # 需要外部调用 set_holding
            else:
                # 继续移动
                self._move_along_path()
                return False

        elif self.state == UGVState.HOLDING:
            # 在会合点等待
            self.hold_counter += 1
            if self.hold_counter >= self.hold_steps:
                # 等待时间到，准备会合
                return True  # 需要外部检查 UAV 是否到达
            return False

        elif self.state == UGVState.MEETING:
            # 会合中，不移动
            return False

        return False

    def _is_at_rendezvous(self) -> bool:
        """检查是否到达会合点"""
        if self.rendezvous_cell is None:
            return False
        return self.cell == self.rendezvous_cell

    def _move_along_path(self):
        """沿路径移动一步"""
        if self.path is None or len(self.path) == 0:
            return

        # 检查是否已到达终点
        if self.path_index >= len(self.path) - 1:
            return

        # 移动到下一个位置
        self.path_index += 1
        self.cell = self.path[self.path_index]

    def get_state(self) -> UGVState:
        """获取当前状态"""
        return self.state

    def get_position(self) -> Tuple[int, int]:
        """获取当前位置"""
        return self.cell

    def get_rendezvous_cell(self) -> Optional[Tuple[int, int]]:
        """获取会合点位置"""
        return self.rendezvous_cell

    def get_hold_counter(self) -> int:
        """获取等待计数器"""
        return self.hold_counter

    def has_path(self) -> bool:
        """是否有路径"""
        return self.path is not None and len(self.path) > 0

    def __repr__(self):
        return f"UGV({self.ugv_id}) at {self.cell} [{self.state.value}]"
