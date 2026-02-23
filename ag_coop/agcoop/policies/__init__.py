"""
Baseline Policies for UAV-UGV Cooperation

提供确定性策略（Greedy, Coverage）用于对比实验
"""

from agcoop.policies.base_policy import BasePolicy
from agcoop.policies.greedy_policy import GreedyPolicy
from agcoop.policies.coverage_policy import CoveragePolicy

__all__ = [
    'BasePolicy',
    'GreedyPolicy',
    'CoveragePolicy',
]
