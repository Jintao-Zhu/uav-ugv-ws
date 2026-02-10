"""
Day10 Step 2: Custom Callbacks for Training

提供自定义回调，用于在线评估和详细 metrics 记录
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import VecEnv


class DetailedEvalCallback(BaseCallback):
    """
    详细评估回调

    在训练过程中定期评估策略，记录详细的 metrics
    """

    def __init__(
        self,
        eval_env: VecEnv,
        eval_freq: int = 10000,
        n_eval_episodes: int = 5,
        eval_seeds: Optional[List[int]] = None,
        log_path: str = "eval_logs",
        verbose: int = 1,
    ):
        """
        初始化评估回调

        Args:
            eval_env: 评估环境
            eval_freq: 评估频率（训练步数）
            n_eval_episodes: 每次评估的 episode 数量
            eval_seeds: 评估使用的固定种子列表
            log_path: 日志保存路径
            verbose: 日志详细程度
        """
        super().__init__(verbose)

        self.eval_env = eval_env
        self.eval_freq = eval_freq
        self.n_eval_episodes = n_eval_episodes
        self.log_path = Path(log_path)
        self.log_path.mkdir(parents=True, exist_ok=True)

        # 固定评估种子
        if eval_seeds is None:
            self.eval_seeds = list(range(10000, 10000 + n_eval_episodes))
        else:
            self.eval_seeds = eval_seeds

        # 确保种子数量与 episode 数量匹配
        if len(self.eval_seeds) < n_eval_episodes:
            # 扩展种子列表
            base_seed = self.eval_seeds[-1] + 1
            self.eval_seeds.extend(range(base_seed, base_seed + n_eval_episodes - len(self.eval_seeds)))

        # 评估历史
        self.eval_history = []

        # 上次评估的步数
        self.last_eval_step = 0

    def _on_step(self) -> bool:
        """
        每步调用

        Returns:
            是否继续训练
        """
        # 检查是否需要评估
        if self.num_timesteps - self.last_eval_step >= self.eval_freq:
            self._evaluate()
            self.last_eval_step = self.num_timesteps

        return True

    def _evaluate(self):
        """执行评估"""
        if self.verbose > 0:
            print()
            print("=" * 70)
            print(f"Evaluation at step {self.num_timesteps}")
            print("=" * 70)

        # 收集所有 episode 的 metrics
        episode_metrics_list = []

        for i in range(self.n_eval_episodes):
            seed = self.eval_seeds[i]

            if self.verbose > 0:
                print(f"  Episode {i+1}/{self.n_eval_episodes} (seed={seed})...")

            # 运行一个 episode
            metrics = self._run_episode(seed)
            episode_metrics_list.append(metrics)

            if self.verbose > 0:
                print(f"    Reward: {metrics['total_reward']:.4f}, "
                      f"Tasks: {metrics['tasks_completed']}, "
                      f"Miss rate: {metrics['deadline_miss_rate']:.2f}%")
                # 打印 reward 分量
                print(f"      Components: task={metrics['reward_task']:.2f}, "
                      f"time={metrics['reward_time']:.2f}, "
                      f"comm={metrics['reward_comm']:.2f}, "
                      f"deadline={metrics['reward_deadline']:.2f}, "
                      f"mapf={metrics['reward_mapf']:.2f}")

        # 计算统计量
        eval_stats = self._compute_stats(episode_metrics_list)
        eval_stats['timestep'] = self.num_timesteps
        eval_stats['n_episodes'] = self.n_eval_episodes
        eval_stats['seeds'] = self.eval_seeds[:self.n_eval_episodes]

        # 保存评估结果
        self._save_eval_results(eval_stats, episode_metrics_list)

        # 记录到 TensorBoard
        self._log_to_tensorboard(eval_stats)

        # 添加到历史
        self.eval_history.append(eval_stats)

        if self.verbose > 0:
            print()
            print("Evaluation Summary:")
            print(f"  Mean reward: {eval_stats['eval/mean_reward']:.4f} ± {eval_stats['eval/std_reward']:.4f}")
            print(f"  Reward components (mean):")
            print(f"    - Task: {eval_stats.get('eval/reward_task_mean', 0.0):.4f}")
            print(f"    - Time: {eval_stats.get('eval/reward_time_mean', 0.0):.4f}")
            print(f"    - Comm: {eval_stats.get('eval/reward_comm_mean', 0.0):.4f}")
            print(f"    - Deadline: {eval_stats.get('eval/reward_deadline_mean', 0.0):.4f}")
            print(f"    - MAPF: {eval_stats.get('eval/reward_mapf_mean', 0.0):.4f}")
            print(f"  Mean tasks completed: {eval_stats['eval/tasks_completed_mean']:.2f} ± {eval_stats['eval/tasks_completed_std']:.2f}")
            print(f"  Mean deadline miss rate: {eval_stats['eval/deadline_miss_rate_mean']:.2f}% ± {eval_stats['eval/deadline_miss_rate_std']:.2f}%")
            print(f"  Mean outage percent (worst_nc): {eval_stats['eval/outage_percent_worst_nc_mean']:.2f}% ± {eval_stats['eval/outage_percent_worst_nc_std']:.2f}%")
            print("=" * 70)
            print()

    def _run_episode(self, seed: int) -> Dict[str, Any]:
        """
        运行一个评估 episode

        Args:
            seed: 随机种子

        Returns:
            episode metrics
        """
        # 重置环境
        obs = self.eval_env.reset()
        if hasattr(self.eval_env, 'seed'):
            self.eval_env.seed(seed)

        # 运行 episode
        done = False
        total_reward = 0.0
        episode_length = 0

        # 累积 reward 分量
        reward_components_sum = {
            'r_task': 0.0,
            'r_time': 0.0,
            'r_comm': 0.0,
            'r_deadline': 0.0,
            'r_mapf': 0.0,
        }

        while not done:
            # 使用确定性策略
            action, _ = self.model.predict(obs, deterministic=True)
            obs, reward, done, info = self.eval_env.step(action)

            total_reward += reward[0]
            episode_length += 1

            # 累积 reward 分量（从 info 中获取）
            step_info = info[0] if isinstance(info, list) else info
            if 'reward_components' in step_info:
                rc = step_info['reward_components']
                for key in reward_components_sum.keys():
                    if key in rc:
                        reward_components_sum[key] += rc[key]

            # 检查是否结束
            if done[0]:
                break

        # 获取最终 metrics（从 info 中）
        # 注意：VecEnv 的 info 是一个列表
        final_info = info[0] if isinstance(info, list) else info

        # 构建 metrics
        metrics = {
            'seed': seed,
            'steps': episode_length,
            'total_reward': float(total_reward),
            'mean_reward': float(total_reward / episode_length) if episode_length > 0 else 0.0,
        }

        # 添加 reward 分量
        metrics['reward_task'] = float(reward_components_sum['r_task'])
        metrics['reward_time'] = float(reward_components_sum['r_time'])
        metrics['reward_comm'] = float(reward_components_sum['r_comm'])
        metrics['reward_deadline'] = float(reward_components_sum['r_deadline'])
        metrics['reward_mapf'] = float(reward_components_sum['r_mapf'])

        # 添加任务 metrics（直接从 final_info 中读取）
        metrics['tasks_completed'] = int(final_info.get('tasks_completed', 0))
        metrics['deadline_miss'] = int(final_info.get('deadline_miss', 0))
        metrics['outage_steps'] = int(final_info.get('outage_steps', 0))
        metrics['tardiness_sum'] = float(final_info.get('tardiness_sum', 0.0))

        # 计算派生 metrics
        if metrics['tasks_completed'] + metrics['deadline_miss'] > 0:
            metrics['deadline_miss_rate'] = 100.0 * metrics['deadline_miss'] / (metrics['tasks_completed'] + metrics['deadline_miss'])
        else:
            metrics['deadline_miss_rate'] = 0.0

        if metrics['deadline_miss'] > 0:
            metrics['mean_tardiness'] = metrics['tardiness_sum'] / metrics['deadline_miss']
        else:
            metrics['mean_tardiness'] = 0.0

        if metrics['tasks_completed'] + metrics['deadline_miss'] > 0:
            metrics['completion_rate'] = 100.0 * metrics['tasks_completed'] / (metrics['tasks_completed'] + metrics['deadline_miss'])
        else:
            metrics['completion_rate'] = 0.0

        # 通信 metrics
        if episode_length > 0:
            metrics['outage_percent_worst_nc'] = 100.0 * metrics['outage_steps'] / episode_length
        else:
            metrics['outage_percent_worst_nc'] = 0.0

        metrics['snr_best_nc_mean'] = 0.0  # 需要从环境累积
        metrics['snr_best_nc_min'] = 0.0   # 需要从环境累积

        # MAPF metrics（暂时设为 0，需要从环境累积）
        metrics['mapf_calls'] = 0
        metrics['mapf_success'] = 0
        metrics['mapf_timeout'] = 0
        metrics['mapf_success_rate'] = 0.0

        return metrics

    def _compute_stats(self, episode_metrics_list: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        计算统计量

        Args:
            episode_metrics_list: episode metrics 列表

        Returns:
            统计量字典
        """
        stats = {}

        # 需要统计的字段
        fields = [
            'total_reward',
            'mean_reward',
            'reward_task',
            'reward_time',
            'reward_comm',
            'reward_deadline',
            'reward_mapf',
            'tasks_completed',
            'deadline_miss',
            'deadline_miss_rate',
            'mean_tardiness',
            'completion_rate',
            'outage_steps',
            'outage_percent_worst_nc',
            'snr_best_nc_mean',
            'snr_best_nc_min',
            'mapf_calls',
            'mapf_success',
            'mapf_timeout',
            'mapf_success_rate',
        ]

        for field in fields:
            values = [m[field] for m in episode_metrics_list if field in m]
            if values:
                # 计算均值和标准差
                mean_val = np.mean(values)
                std_val = np.std(values)
                min_val = np.min(values)
                max_val = np.max(values)

                # 使用 eval/ 前缀
                if field == 'total_reward':
                    stats['eval/mean_reward'] = float(mean_val)
                    stats['eval/std_reward'] = float(std_val)
                    stats['eval/min_reward'] = float(min_val)
                    stats['eval/max_reward'] = float(max_val)
                else:
                    stats[f'eval/{field}_mean'] = float(mean_val)
                    stats[f'eval/{field}_std'] = float(std_val)
                    stats[f'eval/{field}_min'] = float(min_val)
                    stats[f'eval/{field}_max'] = float(max_val)

        return stats

    def _save_eval_results(self, eval_stats: Dict[str, Any], episode_metrics_list: List[Dict[str, Any]]):
        """
        保存评估结果

        Args:
            eval_stats: 评估统计量
            episode_metrics_list: episode metrics 列表
        """
        # 保存统计量
        stats_path = self.log_path / f'eval_stats_{self.num_timesteps:08d}.json'
        with open(stats_path, 'w') as f:
            json.dump(eval_stats, f, indent=2)

        # 保存详细 metrics
        details_path = self.log_path / f'eval_details_{self.num_timesteps:08d}.json'
        with open(details_path, 'w') as f:
            json.dump(episode_metrics_list, f, indent=2)

        # 更新汇总文件
        summary_path = self.log_path / 'eval_summary.json'
        with open(summary_path, 'w') as f:
            json.dump(self.eval_history + [eval_stats], f, indent=2)

    def _log_to_tensorboard(self, eval_stats: Dict[str, float]):
        """
        记录到 TensorBoard

        Args:
            eval_stats: 评估统计量
        """
        # 记录所有 eval/ 开头的指标
        try:
            if self.logger is not None:
                for key, value in eval_stats.items():
                    if key.startswith('eval/') and isinstance(value, (int, float)):
                        self.logger.record(key, value)
        except (AttributeError, Exception):
            # Logger 未初始化或不可用，跳过 TensorBoard 记录
            pass
