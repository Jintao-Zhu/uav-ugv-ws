"""
通信模块

包含：
- raycast.py - 格栅射线追踪（Bresenham 算法）
- comm_model.py - 通信模型（SNR 计算和 outage 判断）
- model_wrapper.py - CommModel 包装类
"""

from .raycast import (
    bresenham_cells,
    count_blocked_cells,
    has_line_of_sight,
    compute_los_distance,
)

from .comm_model import (
    CommConfig,
    compute_snr,
    compute_snr_to_ugvs,
    compute_best_snr,
    compute_comm_metrics,
)

from .model_wrapper import CommModel

__all__ = [
    # raycast
    'bresenham_cells',
    'count_blocked_cells',
    'has_line_of_sight',
    'compute_los_distance',
    # comm_model
    'CommConfig',
    'compute_snr',
    'compute_snr_to_ugvs',
    'compute_best_snr',
    'compute_comm_metrics',
    # model_wrapper
    'CommModel',
]
