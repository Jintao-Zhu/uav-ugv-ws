#!/usr/bin/env python3
"""
全新Baseline策略集合 - 适配UAV独立飞行系统

包含4个精心设计的baseline策略：
1. Tethered-Greedy: 绑定式贪心（消融实验基准）
2. Static-Center: 静态中心部署（经典通信基站）
3. Dynamic-Heuristic: 启发式动态跟随（最强人类规则）
4. Pure-Random: 纯随机（系统混沌下限）
"""

import numpy as np
import math
from typing import Tuple, Optional


class BaselinePolicy:
    """Baseline策略基类"""

    def __init__(self, env):
        self.env = env
        self.policy_name = "BasePolicy"

    def predict(self, obs, deterministic=True):
        """
        模仿SB3模型的predict接口
        :param obs: 观察空间字典
        :param deterministic: 是否确定性输出（兼容接口）
        :return: (action, state)
        """
        raise NotImplementedError

    def _get_distance(self, pos1, pos2):
        """计算欧几里得距离"""
        return math.hypot(pos1[0] - pos2[0], pos1[1] - pos2[1])


class TetheredGreedyPolicy(BaselinePolicy):
    """
    Baseline 1: Tethered-Greedy (绑定式贪心策略)

    学术目的：消融实验基准，证明UAV独立飞行的必要性
    逻辑：强制UAV永远停靠在UGV_0上，剥夺飞行权利
    """

    def __init__(self, env):
        super().__init__(env)
        self.policy_name = "Tethered-Greedy"

    def predict(self, obs, deterministic=True):
        # 使用简单的轮询策略选择任务（1-5循环）
        # 避免task_choice=0导致底层Greedy接管
        if not hasattr(self, '_task_counter'):
            self._task_counter = 0
        task_choice = (self._task_counter % 5) + 1  # 1-5循环
        self._task_counter += 1

        relay_target = 0

        # 解析UAV状态
        uav_state = obs['uav_state']
        mode = uav_state[0]  # 归一化后的mode (0.0=ONBOARD, 0.5=FLYING, 1.0=HOVERING)
        onboard_id = int(round(uav_state[4] * 2.0))  # 还原UGV ID (假设3台车)

        # 强制逻辑：如果不在UGV_0上，立刻飞回去
        if mode > 0.01 or onboard_id != 0:  # 不在ONBOARD模式或不在UGV_0上
            uav_action = 13  # 降落到UGV_0
        else:
            uav_action = 0  # 保持不动

        action = np.array([task_choice, relay_target, uav_action])
        return action, None


class StaticCenterPolicy(BaselinePolicy):
    """
    Baseline 2: Static-Center (静态中心部署)

    学术目的：对比经典通信基站策略，证明动态伴飞的优势
    逻辑：UAV飞往地图中心悬停，仅在低电量时返回充电
    """

    def __init__(self, env):
        super().__init__(env)
        self.policy_name = "Static-Center"

        # 计算地图中心坐标
        map_w = self.env.grid_map.width
        map_h = self.env.grid_map.height
        center_x = map_w / 2.0
        center_y = map_h / 2.0

        # 找到距离中心最近的中继点
        min_dist = float('inf')
        self.center_relay_idx = 1  # 默认第1个中继点

        for i, relay_pos in enumerate(self.env.candidate_relays):
            dist = self._get_distance((center_x, center_y), relay_pos)
            if dist < min_dist:
                min_dist = dist
                self.center_relay_idx = i + 1  # 动作空间1-12

    def predict(self, obs, deterministic=True):
        # 使用简单的轮询策略选择任务（1-5循环）
        if not hasattr(self, '_task_counter'):
            self._task_counter = 0
        task_choice = (self._task_counter % 5) + 1  # 1-5循环
        self._task_counter += 1

        relay_target = 0

        # 解析UAV状态
        uav_state = obs['uav_state']
        battery = uav_state[3]

        # 策略逻辑：电量充足去中心，电量不足保持现状（环境会强制返航）
        if battery > 0.9:  # 电量充足
            uav_action = self.center_relay_idx
        else:
            uav_action = 0  # 保持现状

        action = np.array([task_choice, relay_target, uav_action])
        return action, None


class DynamicHeuristicPolicy(BaselinePolicy):
    """
    Baseline 3: Dynamic-Heuristic (启发式动态跟随)

    学术目的：最强人类规则，挑战RL的假想敌
    逻辑：实时计算UGV质心，飞往最近中继点；低电量时主动寻找最近UGV充电
    """

    def __init__(self, env, battery_threshold=0.25):
        super().__init__(env)
        self.policy_name = "Dynamic-Heuristic"
        self.battery_threshold = battery_threshold
        self.candidate_relays = self.env.candidate_relays
        self.n_ugvs = self.env.n_ugv

    def predict(self, obs, deterministic=True):
        # 使用简单的轮询策略选择任务（1-5循环）
        if not hasattr(self, '_task_counter'):
            self._task_counter = 0
        task_choice = (self._task_counter % 5) + 1  # 1-5循环
        self._task_counter += 1

        relay_target = 0
        uav_action = 0

        # 解析UAV状态
        uav_state = obs['uav_state']
        current_mode = int(round(uav_state[0] * 2.0))  # 0=ONBOARD, 1=FLYING, 2=HOVERING

        # 还原UAV真实位置
        map_w = self.env.grid_map.width
        map_h = self.env.grid_map.height
        uav_pos = np.array([
            uav_state[1] * map_w,  # X坐标
            uav_state[2] * map_h   # Y坐标
        ])
        battery_level = uav_state[3]

        # 解析UGV位置
        ugv_positions = obs['ugv_pos'].reshape(self.n_ugvs, 2)

        # 核心逻辑分支
        if battery_level < self.battery_threshold and current_mode != 0:
            # 【电量告急】：寻找最近的UGV降落充电
            min_dist = float('inf')
            best_ugv_id = 0

            for i in range(self.n_ugvs):
                dist = self._get_distance(uav_pos, ugv_positions[i])
                if dist < min_dist:
                    min_dist = dist
                    best_ugv_id = i

            uav_action = 13 + best_ugv_id  # 13, 14, 15

        elif battery_level >= self.battery_threshold:
            # 【电量健康】：计算UGV质心，飞往最近中继点
            centroid_x = np.mean(ugv_positions[:, 0])
            centroid_y = np.mean(ugv_positions[:, 1])
            centroid = np.array([centroid_x, centroid_y])

            min_dist = float('inf')
            best_relay_idx = 1  # 默认第1个中继点

            for i, relay_pos in enumerate(self.candidate_relays):
                dist = self._get_distance(centroid, relay_pos)
                if dist < min_dist:
                    min_dist = dist
                    best_relay_idx = i + 1  # 1-12

            uav_action = best_relay_idx

        action = np.array([task_choice, relay_target, uav_action])
        return action, None


class PureRandomPolicy(BaselinePolicy):
    """
    Baseline 4: Pure-Random (纯随机)

    学术目的：系统混沌下限，检验容错性和稳定性
    逻辑：在整个3D动作空间内均匀采样
    """

    def __init__(self, env):
        super().__init__(env)
        self.policy_name = "Pure-Random"
        self.action_space = env.action_space

    def predict(self, obs, deterministic=True):
        # 直接从动作空间采样
        action = self.action_space.sample()
        return action, None
