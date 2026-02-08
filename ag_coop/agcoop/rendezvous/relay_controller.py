"""
Relay Controller

管理 relay UGV 的决策逻辑：
- 检测 outage 风险
- 选择最佳 relay 目标
- 在风险低时切换回任务执行模式
"""

from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass


@dataclass
class RelayConfig:
    """Relay 配置"""
    enabled: bool = True  # 是否启用 relay 模式
    relay_ugv_id: int = 0  # 指定哪个 UGV 作为 relay（默认 0 号）
    risk_margin: float = 5.0  # SNR 风险边界 (dB)
    beta: float = 0.1  # 距离惩罚权重
    gamma: float = 5.0  # 拥挤度惩罚权重

    @classmethod
    def from_dict(cls, config_dict: dict) -> 'RelayConfig':
        """从配置字典创建"""
        return cls(
            enabled=config_dict.get('enabled', True),
            relay_ugv_id=config_dict.get('relay_ugv_id', 0),
            risk_margin=config_dict.get('risk_margin', 5.0),
            beta=config_dict.get('beta', 0.1),
            gamma=config_dict.get('gamma', 5.0),
        )


class RelayController:
    """
    Relay Controller

    负责管理 relay UGV 的决策：
    - 检测 outage 风险
    - 选择最佳 relay 目标
    - 在风险低时切换回任务执行模式
    """

    def __init__(
        self,
        relay_config: RelayConfig,
        candidate_relays: List[Tuple[int, int]],
        grid_map,
        comm_config
    ):
        """
        初始化 Relay Controller

        Args:
            relay_config: Relay 配置
            candidate_relays: 候选中继点列表 [(i, j), ...]
            grid_map: GridMap 对象
            comm_config: 通信配置
        """
        self.relay_config = relay_config
        self.candidate_relays = candidate_relays
        self.grid_map = grid_map
        self.comm_config = comm_config

        # 当前状态
        self.relay_mode = False  # 是否处于 relay 模式
        self.relay_target = None  # 当前 relay 目标 (i, j)

    def decide_relay_action(
        self,
        snr_best: float,
        uav_cell: Tuple[int, int],
        ugv_cells: Dict[int, Tuple[int, int]]
    ) -> Tuple[bool, Optional[Tuple[int, int]], float]:
        """
        决定 relay UGV 的行动

        Args:
            snr_best: 当前最佳 SNR (dB)
            uav_cell: UAV 当前位置 (i, j)
            ugv_cells: 所有 UGV 的位置 {ugv_id: (i, j), ...}

        Returns:
            (relay_mode, relay_target, score)
            - relay_mode: 是否应该进入 relay 模式
            - relay_target: relay 目标位置 (i, j)，如果不是 relay 模式则为 None
            - score: relay 目标的分数
        """
        from agcoop.rendezvous.coverage_score import check_outage_risk, select_best_relay_target

        # 检查 outage 风险
        has_risk = check_outage_risk(
            snr_best,
            self.comm_config.snr_threshold_db,
            self.relay_config.risk_margin
        )

        if not has_risk:
            # 没有风险，不需要 relay
            self.relay_mode = False
            self.relay_target = None
            return False, None, 0.0

        # 有风险，选择最佳 relay 目标
        relay_ugv_id = self.relay_config.relay_ugv_id
        relay_ugv_cell = ugv_cells.get(relay_ugv_id)

        if relay_ugv_cell is None:
            # relay UGV 不存在
            return False, None, 0.0

        # 获取其他 UGV 的位置
        other_ugv_cells = [
            cell for ugv_id, cell in ugv_cells.items()
            if ugv_id != relay_ugv_id
        ]

        # 选择最佳 relay 目标
        best_target, best_score = select_best_relay_target(
            self.candidate_relays,
            uav_cell,
            relay_ugv_cell,
            other_ugv_cells,
            self.grid_map,
            self.comm_config,
            self.relay_config.beta,
            self.relay_config.gamma
        )

        if best_target is None:
            # 没有可达的候选点
            self.relay_mode = False
            self.relay_target = None
            return False, None, 0.0

        # 进入 relay 模式
        self.relay_mode = True
        self.relay_target = best_target

        return True, best_target, best_score

    def get_relay_goal(self, ugv_id: int) -> Optional[Tuple[int, int]]:
        """
        获取指定 UGV 的 relay 目标

        Args:
            ugv_id: UGV ID

        Returns:
            relay 目标 (i, j)，如果不是 relay UGV 或不在 relay 模式则为 None
        """
        if ugv_id != self.relay_config.relay_ugv_id:
            return None

        if not self.relay_mode:
            return None

        return self.relay_target

    def is_relay_ugv(self, ugv_id: int) -> bool:
        """
        检查指定 UGV 是否是 relay UGV

        Args:
            ugv_id: UGV ID

        Returns:
            True 如果是 relay UGV，False 否则
        """
        return ugv_id == self.relay_config.relay_ugv_id

    def get_status(self) -> Dict:
        """
        获取当前状态（用于日志）

        Returns:
            状态字典
        """
        return {
            'relay_mode': self.relay_mode,
            'relay_target_cell': list(self.relay_target) if self.relay_target else None,
            'relay_ugv_id': self.relay_config.relay_ugv_id,
        }
