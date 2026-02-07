"""
Rendezvous 规划器

功能：
- 生成候选会合点集合
- 评分并选择最优会合点
- 计算会合时间
"""

import random
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass


@dataclass
class RendezvousPlan:
    """
    会合计划

    属性：
        rendezvous_cell: 会合点位置 (i, j)
        t_meet: 预期会合时刻
        window: 会合时间窗（±window 步）
        score: 会合点评分
        eta_uav: UAV 到达时间（估计）
        eta_ugv: UGV 到达时间（估计）
        snr_pred: 预测 SNR
        depart_delay: UGV 延迟出发时间（步数）
        eta_uav_est: UAV ETA 估计值（用于日志）
        eta_ugv_est: UGV ETA 估计值（用于日志）
    """
    rendezvous_cell: Tuple[int, int]
    t_meet: int
    window: int
    score: float
    eta_uav: int
    eta_ugv: int
    snr_pred: float
    depart_delay: int = 0  # 新增：UGV 延迟出发时间
    eta_uav_est: int = 0   # 新增：用于日志
    eta_ugv_est: int = 0   # 新增：用于日志


class RendezvousPlanner:
    """
    Rendezvous 规划器

    功能：
    - 生成候选会合点集合（路口点优先 + 随机补齐）
    - 评分并选择最优会合点
    - 计算会合时间
    """

    def __init__(
        self,
        grid_map,
        comm_model,
        candidate_count: int = 12,
        score_alpha_snr: float = 1.0,
        score_beta_eta: float = 0.3,
        meet_window: int = 3,
        seed: Optional[int] = None,
        sync_depart_enabled: bool = False,
        sync_depart_buffer: int = 2,
        sync_depart_max_delay: int = 30,
        sync_depart_min_gap: int = 1,
        uav_service_time: int = 2,
        uav_neighbor_mode: int = 8,
        ugv_neighbor_mode: int = 4
    ):
        """
        初始化 Rendezvous 规划器

        Args:
            grid_map: GridMap 对象
            comm_model: CommModel 对象
            candidate_count: 候选会合点数量
            score_alpha_snr: SNR 权重
            score_beta_eta: ETA 差异权重
            meet_window: 会合时间窗（±window 步）
            seed: 随机种子
            sync_depart_enabled: 是否启用同步出发
            sync_depart_buffer: 同步出发缓冲步数
            sync_depart_max_delay: 最大延迟出发时间
            sync_depart_min_gap: 最小触发间隔
            uav_service_time: UAV 服务时间
            uav_neighbor_mode: UAV 邻接模式
            ugv_neighbor_mode: UGV 邻接模式
        """
        self.grid_map = grid_map
        self.comm_model = comm_model
        self.candidate_count = candidate_count
        self.score_alpha_snr = score_alpha_snr
        self.score_beta_eta = score_beta_eta
        self.meet_window = meet_window
        self.seed = seed

        # 同步出发参数
        self.sync_depart_enabled = sync_depart_enabled
        self.sync_depart_buffer = sync_depart_buffer
        self.sync_depart_max_delay = sync_depart_max_delay
        self.sync_depart_min_gap = sync_depart_min_gap

        # UAV/UGV 参数
        self.uav_service_time = uav_service_time
        self.uav_neighbor_mode = uav_neighbor_mode
        self.ugv_neighbor_mode = ugv_neighbor_mode

        # 生成候选会合点集合
        self.candidates = self._generate_candidates()

        # 创建 ETA 估计器
        from .eta import ETAEstimator
        self.eta_estimator = ETAEstimator(
            grid_map=grid_map,
            uav_neighbor_mode=uav_neighbor_mode,
            ugv_neighbor_mode=ugv_neighbor_mode
        )

    def _generate_candidates(self) -> List[Tuple[int, int]]:
        """
        生成候选会合点集合

        策略：
        1. 路口点（4 邻接度 >= 3）优先
        2. 不足则从 free_cells 随机补齐
        3. 固定 seed，保证可复现

        Returns:
            候选会合点列表
        """
        candidates = []

        # 1. 找路口点（4 邻接度 >= 3）
        junction_cells = []
        for cell in self.grid_map.free_cells:
            degree = self._get_degree_4(cell)
            if degree >= 3:
                junction_cells.append(cell)

        # 优先添加路口点
        candidates.extend(junction_cells[:self.candidate_count])

        # 2. 不足则从 free_cells 随机补齐
        if len(candidates) < self.candidate_count:
            remaining = self.candidate_count - len(candidates)
            rng = random.Random(self.seed)

            # 排除已选的路口点
            available = [c for c in self.grid_map.free_cells if c not in candidates]
            sampled = rng.sample(available, min(remaining, len(available)))
            candidates.extend(sampled)

        return candidates

    def _get_degree_4(self, cell: Tuple[int, int]) -> int:
        """
        计算 4 邻接度（有多少个自由邻居）

        Args:
            cell: 格子位置 (i, j)

        Returns:
            邻接度（0-4）
        """
        i, j = cell
        degree = 0

        # 4 邻接：上下左右
        for di, dj in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ni, nj = i + di, j + dj
            if self._is_free(ni, nj):
                degree += 1

        return degree

    def _is_free(self, i: int, j: int) -> bool:
        """检查格子是否自由"""
        if not (0 <= i < self.grid_map.height and 0 <= j < self.grid_map.width):
            return False
        return self.grid_map.grid[i, j] == 0

    def plan(
        self,
        t_now: int,
        task_cell: Tuple[int, int],
        ugv_carrier_pos: Tuple[int, int],
        uav_pos: Tuple[int, int]
    ) -> Optional[RendezvousPlan]:
        """
        规划会合点

        Args:
            t_now: 当前时刻
            task_cell: 任务位置
            ugv_carrier_pos: 载机（UGV）位置
            uav_pos: UAV 当前位置（用于精确 ETA 估计）

        Returns:
            会合计划或 None（如果没有合适的会合点）
        """
        if not self.candidates:
            return None

        # 评分所有候选点
        scored_candidates = []

        for r in self.candidates:
            # 使用 ETA 估计器计算精确 ETA
            eta_uav_est = self.eta_estimator.estimate_uav_eta(
                uav_cell=uav_pos,
                task_cell=task_cell,
                rendezvous_cell=r,
                service_time=self.uav_service_time
            )
            eta_ugv_est = self.eta_estimator.estimate_ugv_eta(
                ugv_cell=ugv_carrier_pos,
                rendezvous_cell=r
            )

            # 计算预测 SNR（简化：假设 UAV 和 UGV 都在 r）
            snr_pred = self.comm_model.compute_snr(uav_cell=r, ugv_cell=r)

            # 计算评分
            score = self._compute_score(snr_pred, eta_uav_est, eta_ugv_est)

            scored_candidates.append({
                'cell': r,
                'score': score,
                'eta_uav_est': eta_uav_est,
                'eta_ugv_est': eta_ugv_est,
                'snr_pred': snr_pred
            })

        # 选择最高分
        best = max(scored_candidates, key=lambda x: x['score'])

        # 计算延迟出发量（同步出发机制）
        depart_delay = self._compute_depart_delay(
            eta_uav=best['eta_uav_est'],
            eta_ugv=best['eta_ugv_est']
        )

        # 计算会合时间（考虑延迟出发）
        t_meet = t_now + max(best['eta_uav_est'], best['eta_ugv_est'] + depart_delay)

        # 构造会合计划
        plan = RendezvousPlan(
            rendezvous_cell=best['cell'],
            t_meet=t_meet,
            window=self.meet_window,
            score=best['score'],
            eta_uav=best['eta_uav_est'],
            eta_ugv=best['eta_ugv_est'],
            snr_pred=best['snr_pred'],
            depart_delay=depart_delay,
            eta_uav_est=best['eta_uav_est'],
            eta_ugv_est=best['eta_ugv_est']
        )

        return plan

    def _compute_depart_delay(self, eta_uav: int, eta_ugv: int) -> int:
        """
        计算 UGV 延迟出发时间

        策略：
        - 若 eta_uav > eta_ugv + buffer + min_gap，则延迟 UGV 出发
        - 延迟量 = min(max_delay, eta_uav - eta_ugv - buffer)

        Args:
            eta_uav: UAV 到达时间估计
            eta_ugv: UGV 到达时间估计

        Returns:
            depart_delay: UGV 延迟出发时间（步数）
        """
        if not self.sync_depart_enabled:
            return 0

        gap = eta_uav - eta_ugv

        # 触发条件：gap > min_trigger_gap + buffer
        if gap > self.sync_depart_min_gap + self.sync_depart_buffer:
            # 延迟量 = min(max_delay, gap - buffer)
            depart_delay = min(self.sync_depart_max_delay, gap - self.sync_depart_buffer)
            return depart_delay
        else:
            return 0

    def _compute_score(self, snr_pred: float, eta_uav: int, eta_ugv: int) -> float:
        """
        计算会合点评分

        公式：score = alpha * snr_pred - beta * |eta_ugv - eta_uav|

        Args:
            snr_pred: 预测 SNR（dB）
            eta_uav: UAV 到达时间
            eta_ugv: UGV 到达时间

        Returns:
            评分
        """
        eta_diff = abs(eta_ugv - eta_uav)
        score = self.score_alpha_snr * snr_pred - self.score_beta_eta * eta_diff
        return score

    def _dist8(self, cell1: Tuple[int, int], cell2: Tuple[int, int]) -> int:
        """
        计算 8 邻接距离（Chebyshev 距离）

        Args:
            cell1: 起点 (i, j)
            cell2: 终点 (i, j)

        Returns:
            距离（步数）
        """
        i1, j1 = cell1
        i2, j2 = cell2
        return max(abs(i1 - i2), abs(j1 - j2))

    def _dist4(self, cell1: Tuple[int, int], cell2: Tuple[int, int]) -> int:
        """
        计算 4 邻接距离（Manhattan 距离）

        Args:
            cell1: 起点 (i, j)
            cell2: 终点 (i, j)

        Returns:
            距离（步数）
        """
        i1, j1 = cell1
        i2, j2 = cell2
        return abs(i1 - i2) + abs(j1 - j2)

    def get_candidates(self) -> List[Tuple[int, int]]:
        """获取候选会合点列表"""
        return self.candidates.copy()

    def get_candidate_count(self) -> int:
        """获取候选会合点数量"""
        return len(self.candidates)
