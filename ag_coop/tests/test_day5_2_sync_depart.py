"""
Day5.2 同步出发机制验收实验

对照实验设计：
- Baseline: sync_depart.enabled = False
- Sync: sync_depart.enabled = True
- 5 个随机种子：0, 1, 2, 3, 4
- 固定其他参数（map, arrival_rate, deadline 等）

验收指标：
1. mean_ugv_wait_at_r 下降（目标：从 13.75 降到 < 5）
2. emergency_rate 下降（目标：从 61.5% 降到 < 30%）
3. late_meet_count 下降（目标：从高比例降到 < 20%）
"""

import sys
from pathlib import Path
import json
import yaml
import numpy as np
from scipy import stats

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from agcoop.map import auto_load_map
from agcoop.env import CoopEnv, EnvConfig


def load_config(config_path: str) -> dict:
    """加载配置文件"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def create_env_config(yaml_config: dict, seed: int, sync_enabled: bool) -> EnvConfig:
    """从 YAML 配置创建 EnvConfig"""
    return EnvConfig(
        # Episode 配置
        horizon_steps=yaml_config['episode']['horizon_steps'],
        decision_period=yaml_config['episode']['decision_period'],
        seed=seed,

        # UAV 配置
        uav_speed=yaml_config['uav']['speed_cells_per_step'],
        uav_neighbor_mode=yaml_config['uav']['neighbor_mode'],
        uav_service_time=yaml_config['uav']['service_time'],
        uav_meet_window=yaml_config['uav']['meet_window'],
        uav_max_loiter_steps=yaml_config['uav']['max_loiter_steps'],

        # UGV 配置
        ugv_speed=yaml_config['ugv']['speed_cells_per_step'],
        ugv_neighbor_mode=yaml_config['ugv']['neighbor_mode'],
        ugv_hold_steps=yaml_config['ugv']['hold_steps'],
        carrier_id=yaml_config['ugv']['carrier_id'],

        # Rendezvous 配置
        rendezvous_candidate_count=yaml_config['rendezvous']['candidate_count'],
        rendezvous_score_alpha_snr=yaml_config['rendezvous']['score_alpha_snr'],
        rendezvous_score_beta_eta=yaml_config['rendezvous']['score_beta_eta'],

        # 同步出发配置（关键变量）
        sync_depart_enabled=sync_enabled,
        sync_depart_buffer_steps=yaml_config['sync_depart']['buffer_steps'],
        sync_depart_max_delay=yaml_config['sync_depart']['max_depart_delay'],
        sync_depart_min_trigger_gap=yaml_config['sync_depart']['min_trigger_gap'],

        # 任务配置
        task_arrival_rate=yaml_config['tasks']['arrival_rate'],
        task_deadline_min=yaml_config['tasks']['deadline_min'],
        task_deadline_max=yaml_config['tasks']['deadline_max'],
        task_max_active=yaml_config['tasks']['max_active'],
        task_top_m=yaml_config['tasks']['top_m'],

        # 通信配置
        comm_tx_power_db=yaml_config['comm']['tx_power_db'],
        comm_pathloss_n=yaml_config['comm']['pathloss_n'],
        comm_obstacle_penalty_db=yaml_config['comm']['obstacle_penalty_db'],
        comm_snr_threshold_db=yaml_config['comm']['snr_threshold_db'],
    )


def run_experiment(map_path: str, config: EnvConfig, experiment_name: str) -> dict:
    """运行单次实验"""
    print(f"\n运行实验: {experiment_name} (seed={config.seed})")

    # 加载地图
    grid_map = auto_load_map(map_path)

    # 创建环境
    env = CoopEnv(grid_map, config)

    # 运行 episode
    metrics = env.run_episode()

    # 打印关键指标
    print(f"  完成任务: {metrics['total_completed']}")
    print(f"  emergency_rate: {metrics['emergency_rate']:.2%}")
    print(f"  mean_ugv_wait_at_r: {metrics['mean_ugv_wait_at_r']:.2f}")
    print(f"  mean_depart_delay: {metrics.get('mean_depart_delay', 0):.2f}")
    print(f"  late_meet_count: {metrics.get('late_meet_count', 0)}")

    return metrics


def run_baseline_vs_sync(seeds: list = [0, 1, 2, 3, 4]):
    """运行 Baseline vs Sync 对照实验"""
    print("=" * 80)
    print("Day5.2 同步出发机制验收实验")
    print("=" * 80)

    # 加载配置
    config_path = project_root / "configs" / "default.yaml"
    yaml_config = load_config(config_path)
    map_path = project_root / yaml_config['episode']['map_path']

    # 存储结果
    baseline_results = []
    sync_results = []

    # 运行 Baseline 实验（sync_depart.enabled = False）
    print("\n" + "=" * 80)
    print("Baseline 实验（sync_depart.enabled = False）")
    print("=" * 80)

    for seed in seeds:
        config = create_env_config(yaml_config, seed, sync_enabled=False)
        metrics = run_experiment(str(map_path), config, f"Baseline-seed{seed}")
        baseline_results.append(metrics)

    # 运行 Sync 实验（sync_depart.enabled = True）
    print("\n" + "=" * 80)
    print("Sync 实验（sync_depart.enabled = True）")
    print("=" * 80)

    for seed in seeds:
        config = create_env_config(yaml_config, seed, sync_enabled=True)
        metrics = run_experiment(str(map_path), config, f"Sync-seed{seed}")
        sync_results.append(metrics)

    # 计算统计量
    print("\n" + "=" * 80)
    print("统计结果对比")
    print("=" * 80)

    def compute_stats(results, name):
        """计算统计量"""
        n = len(results)

        # 关键指标
        emergency_rates = [r['emergency_rate'] for r in results]
        ugv_waits = [r['mean_ugv_wait_at_r'] for r in results]
        depart_delays = [r.get('mean_depart_delay', 0) for r in results]
        late_meets = [r.get('late_meet_count', 0) for r in results]
        total_attempts = [r['total_rendezvous_attempts'] for r in results]
        total_completed = [r['total_completed'] for r in results]

        print(f"\n{name}:")
        print(f"  emergency_rate: {sum(emergency_rates)/n:.2%} ± {max(emergency_rates)-min(emergency_rates):.2%}")
        print(f"  mean_ugv_wait_at_r: {sum(ugv_waits)/n:.2f} ± {max(ugv_waits)-min(ugv_waits):.2f}")
        print(f"  mean_depart_delay: {sum(depart_delays)/n:.2f} ± {max(depart_delays)-min(depart_delays):.2f}")
        print(f"  late_meet_count: {sum(late_meets)/n:.1f} ± {max(late_meets)-min(late_meets):.1f}")
        print(f"  late_meet_rate: {sum(late_meets)/sum(total_attempts):.2%}")
        print(f"  total_completed: {np.mean(total_completed):.2f} ± {np.std(total_completed, ddof=1):.2f}")

        return {
            'emergency_rate_mean': sum(emergency_rates) / n,
            'ugv_wait_mean': sum(ugv_waits) / n,
            'depart_delay_mean': sum(depart_delays) / n,
            'late_meet_count_mean': sum(late_meets) / n,
            'late_meet_rate': sum(late_meets) / sum(total_attempts),
            'total_completed_mean': np.mean(total_completed),
            'total_completed_std': np.std(total_completed, ddof=1),
            'total_completed_values': total_completed,
        }

    baseline_stats = compute_stats(baseline_results, "Baseline")
    sync_stats = compute_stats(sync_results, "Sync")

    # 计算改进幅度
    print("\n" + "=" * 80)
    print("改进幅度")
    print("=" * 80)

    def compute_improvement(baseline_val, sync_val, metric_name, lower_is_better=True):
        """计算改进幅度"""
        if baseline_val == 0:
            print(f"  {metric_name}: N/A (baseline=0)")
            return

        if lower_is_better:
            improvement = (baseline_val - sync_val) / baseline_val * 100
            symbol = "↓" if improvement > 0 else "↑"
        else:
            improvement = (sync_val - baseline_val) / baseline_val * 100
            symbol = "↑" if improvement > 0 else "↓"

        print(f"  {metric_name}: {symbol} {abs(improvement):.1f}%")

        # 验收标准
        if metric_name == "emergency_rate" and improvement > 30:
            print(f"    ✓ 达到目标（> 30% 下降）")
        elif metric_name == "mean_ugv_wait_at_r" and improvement > 50:
            print(f"    ✓ 达到目标（> 50% 下降）")
        elif metric_name == "late_meet_rate" and improvement > 50:
            print(f"    ✓ 达到目标（> 50% 下降）")

    compute_improvement(baseline_stats['emergency_rate_mean'], sync_stats['emergency_rate_mean'],
                       "emergency_rate", lower_is_better=True)
    compute_improvement(baseline_stats['ugv_wait_mean'], sync_stats['ugv_wait_mean'],
                       "mean_ugv_wait_at_r", lower_is_better=True)
    compute_improvement(baseline_stats['late_meet_rate'], sync_stats['late_meet_rate'],
                       "late_meet_rate", lower_is_better=True)

    # 统计显著性检验
    print("\n" + "=" * 80)
    print("统计显著性检验 (Paired Tests)")
    print("=" * 80)

    def perform_significance_test(baseline_vals, sync_vals, metric_name):
        """执行配对统计检验"""
        baseline_arr = np.array(baseline_vals)
        sync_arr = np.array(sync_vals)

        # Wilcoxon signed-rank test (非参数检验，适用于配对样本)
        statistic, p_value = stats.wilcoxon(baseline_arr, sync_arr, alternative='two-sided')

        # 计算效应量 (Cohen's d for paired samples)
        diff = baseline_arr - sync_arr
        d = np.mean(diff) / np.std(diff, ddof=1)

        print(f"\n{metric_name}:")
        print(f"  Baseline: {baseline_arr} (mean={np.mean(baseline_arr):.2f}, std={np.std(baseline_arr, ddof=1):.2f})")
        print(f"  Sync:     {sync_arr} (mean={np.mean(sync_arr):.2f}, std={np.std(sync_arr, ddof=1):.2f})")
        print(f"  Wilcoxon test: statistic={statistic:.2f}, p-value={p_value:.4f}")
        print(f"  Effect size (Cohen's d): {d:.3f}")

        # 解释显著性
        if p_value < 0.001:
            sig_level = "*** (p < 0.001, 极显著)"
        elif p_value < 0.01:
            sig_level = "** (p < 0.01, 非常显著)"
        elif p_value < 0.05:
            sig_level = "* (p < 0.05, 显著)"
        else:
            sig_level = "n.s. (p >= 0.05, 不显著)"

        print(f"  显著性: {sig_level}")

        # 解释效应量
        if abs(d) < 0.2:
            effect_interp = "小效应"
        elif abs(d) < 0.5:
            effect_interp = "中等效应"
        elif abs(d) < 0.8:
            effect_interp = "大效应"
        else:
            effect_interp = "极大效应"

        print(f"  效应量解释: {effect_interp}")

        return {
            'statistic': float(statistic),
            'p_value': float(p_value),
            'effect_size_d': float(d),
            'significant': bool(p_value < 0.05),
            'significance_level': sig_level,
            'effect_interpretation': effect_interp,
        }

    # 对 total_completed 进行检验
    completed_test = perform_significance_test(
        baseline_stats['total_completed_values'],
        sync_stats['total_completed_values'],
        "total_completed"
    )

    # 对 mean_ugv_wait_at_r 进行检验
    baseline_ugv_waits = [r['mean_ugv_wait_at_r'] for r in baseline_results]
    sync_ugv_waits = [r['mean_ugv_wait_at_r'] for r in sync_results]
    ugv_wait_test = perform_significance_test(
        baseline_ugv_waits,
        sync_ugv_waits,
        "mean_ugv_wait_at_r"
    )

    # 保存结果
    output_dir = project_root / "outputs" / "day5_2_sync_depart"
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {
        'baseline': baseline_results,
        'sync': sync_results,
        'baseline_stats': baseline_stats,
        'sync_stats': sync_stats,
        'seeds': seeds,
        'statistical_tests': {
            'total_completed': completed_test,
            'mean_ugv_wait_at_r': ugv_wait_test,
        }
    }

    with open(output_dir / "results.json", 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n✓ 结果已保存: {output_dir / 'results.json'}")

    return results


def main():
    """主函数"""
    try:
        results = run_baseline_vs_sync(seeds=[0, 1, 2, 3, 4])

        print("\n" + "=" * 80)
        print("Day5.2 验收实验完成")
        print("=" * 80)

        print("\n✓ 所有实验完成！")

    except Exception as e:
        print(f"\n✗ 实验失败: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
