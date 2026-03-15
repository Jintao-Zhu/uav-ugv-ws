#!/usr/bin/env python3
"""
升级版Baseline策略 - 智能任务分配

核心升级：
1. EDF (Earliest Deadline First) 任务分配
2. 保留原有的UAV飞行策略差异
3. 彻底击败Pure-Random的"瞎猫碰死耗子"
"""

import numpy as np
import math
from typing import Tuple, Optional


class SmartBaselinePolicy:
    """智能Baseline策略基类"""

    def __init__(self, env):
        self.env = env
        self.policy_name = "SmartBasePolicy"

    def _get_distance(self, pos1, pos2):
        """计算欧几里得距离"""
        return math.hypot(pos1[0] - pos2[0], pos1[1] - pos2[1])

    def _smart_task_choice(self, obs):
        """
        智能任务选择策略

        关键发现：环境内部已经按deadline对任务排序（EDF）！
        - task_choice=1: 选择最紧急的任务（环境已排序）
        - task_choice=2-5: 选择第2-5紧急的任务
        - task_choice=0: carrier UGV保持原地（会导致性能暴跌）

        策略：永远选择最紧急的任务（task_choice=1）
        """
        # 检查是否有可用任务
        tasks = obs['tasks_topM']
        has_available_task = False

        for task in tasks:
            if task[3] > 0.5:  # available flag
                has_available_task = True
                break

        # 如果有可用任务，选择第一个（环境已按deadline排序）
        if has_available_task:
            return 1  # 永远选择最紧急的任务
        else:
            # 没有可用任务，使用轮询策略避免carrier停滞
            if not hasattr(self, '_task_counter'):
                self._task_counter = 0
            task_choice = (self._task_counter % 5) + 1
            self._task_counter += 1
            return task_choice

    def predict(self, obs, deterministic=True):
        """策略决策接口"""
        raise NotImplementedError


class TetheredSmartPolicy(SmartBaselinePolicy):
    """
    策略1: Tethered-Smart (绑定车顶 + 智能任务分配)

    学术定位：消融实验基准，证明UAV必须解绑
    逻辑：智能任务分配 + UAV强制停靠在UGV_0
    """

    def __init__(self, env):
        super().__init__(env)
        self.policy_name = "Tethered-Smart"

    def predict(self, obs, deterministic=True):
        # 智能任务分配
        task_choice = self._smart_task_choice(obs)
        relay_target = 0

        # 解析UAV状态
        uav_state = obs['uav_state']
        mode = uav_state[0]  # 归一化后的mode
        onboard_id = int(round(uav_state[4] * 2.0))

        # 强制逻辑：如果不在UGV_0上，立刻飞回去
        if mode > 0.01 or onboard_id != 0:
            uav_action = 13  # 降落到UGV_0
        else:
            uav_action = 0  # 保持不动

        action = np.array([task_choice, relay_target, uav_action])
        return action, None


class StaticCenterSmartPolicy(SmartBaselinePolicy):
    """
    策略2: Static-Center-Smart (静态中心部署 + 智能任务分配)

    学术定位：经典通信基站策略
    逻辑：智能任务分配 + UAV飞往地图中心悬停
    """

    def __init__(self, env):
        super().__init__(env)
        self.policy_name = "Static-Center-Smart"

        # 计算地图中心坐标
        map_w = self.env.grid_map.width
        map_h = self.env.grid_map.height
        center_x = map_w / 2.0
        center_y = map_h / 2.0

        # 找到距离中心最近的中继点
        min_dist = float('inf')
        self.center_relay_idx = 1

        for i, relay_pos in enumerate(self.env.candidate_relays):
            dist = self._get_distance((center_x, center_y), relay_pos)
            if dist < min_dist:
                min_dist = dist
                self.center_relay_idx = i + 1

    def predict(self, obs, deterministic=True):
        # 智能任务分配
        task_choice = self._smart_task_choice(obs)
        relay_target = 0

        # 解析UAV状态
        uav_state = obs['uav_state']
        battery = uav_state[3]

        # 策略逻辑：电量充足去中心，电量不足保持现状
        if battery > 0.9:
            uav_action = self.center_relay_idx
        else:
            uav_action = 0

        action = np.array([task_choice, relay_target, uav_action])
        return action, None


class DynamicHeuristicSmartPolicy(SmartBaselinePolicy):
    """
    策略3: Dynamic-Heuristic-Smart (质心动态跟随 + 智能任务分配)

    学术定位：最强人类规则，挑战RL的假想敌
    逻辑：智能任务分配 + UAV动态跟随UGV质心 + 智能充电
    """

    def __init__(self, env, battery_threshold=0.25):
        super().__init__(env)
        self.policy_name = "Dynamic-Heuristic-Smart"
        self.battery_threshold = battery_threshold
        self.candidate_relays = self.env.candidate_relays
        self.n_ugvs = self.env.n_ugv

    def predict(self, obs, deterministic=True):
        # 智能任务分配
        task_choice = self._smart_task_choice(obs)
        relay_target = 0
        uav_action = 0

        # 解析UAV状态
        uav_state = obs['uav_state']
        current_mode = int(round(uav_state[0] * 2.0))

        # 还原UAV真实位置
        map_w = self.env.grid_map.width
        map_h = self.env.grid_map.height
        uav_pos = np.array([
            uav_state[1] * map_w,
            uav_state[2] * map_h
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

            uav_action = 13 + best_ugv_id

        elif battery_level >= self.battery_threshold:
            # 【电量健康】：计算UGV质心，飞往最近中继点
            centroid_x = np.mean(ugv_positions[:, 0])
            centroid_y = np.mean(ugv_positions[:, 1])
            centroid = np.array([centroid_x, centroid_y])

            min_dist = float('inf')
            best_relay_idx = 1

            for i, relay_pos in enumerate(self.candidate_relays):
                dist = self._get_distance(centroid, relay_pos)
                if dist < min_dist:
                    min_dist = dist
                    best_relay_idx = i + 1

            uav_action = best_relay_idx

        action = np.array([task_choice, relay_target, uav_action])
        return action, None


class PureRandomPolicy(SmartBaselinePolicy):
    """
    策略4: Pure-Random (纯随机)

    学术定位：系统混沌下限
    逻辑：完全随机采样
    """

    def __init__(self, env):
        super().__init__(env)
        self.policy_name = "Pure-Random"
        self.action_space = env.action_space

    def predict(self, obs, deterministic=True):
        action = self.action_space.sample()
        return action, None
