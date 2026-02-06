"""日志记录工具：逐步记录和最终指标输出。"""
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, TextIO


class TraceLogger:
    """
    逐步记录日志到 trace.jsonl 文件。

    每一步写一行 JSON，包含：
    - t: 时间步
    - ugv_pos: UGV 位置列表
    - uav_state: UAV 状态（当前在哪个 UGV 上）
    - num_tasks_in_pool: 任务池中的任务数
    - outage: 当前步是否 outage (0/1)
    - task_completed_this_step: 当前步完成的任务数
    """

    def __init__(self, output_path: str):
        """
        初始化 TraceLogger。

        Args:
            output_path: trace.jsonl 文件路径
        """
        self.output_path = Path(output_path)
        self.file_handle: Optional[TextIO] = None
        self.is_open = False

    def open(self) -> None:
        """打开日志文件准备写入。"""
        # 确保父目录存在
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 打开文件（写模式，会覆盖已存在的文件）
        self.file_handle = open(self.output_path, 'w')
        self.is_open = True

    def write_step(self, step_data: Dict[str, Any]) -> None:
        """
        写入一步的数据。

        Args:
            step_data: 包含当前步信息的字典
        """
        if not self.is_open or self.file_handle is None:
            raise RuntimeError("TraceLogger is not open. Call open() first.")

        # 写入 JSON 行
        json_line = json.dumps(step_data, ensure_ascii=False)
        self.file_handle.write(json_line + '\n')
        self.file_handle.flush()  # 立即刷新到磁盘

    def close(self) -> None:
        """关闭日志文件。"""
        if self.is_open and self.file_handle is not None:
            self.file_handle.close()
            self.is_open = False
            self.file_handle = None

    def __enter__(self):
        """支持 with 语句。"""
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持 with 语句。"""
        self.close()
        return False


class MetricsLogger:
    """
    最终指标记录器，用于保存 episode 结束时的汇总指标。

    输出到 metrics.json，包含：
    - seed: 随机种子
    - steps: 总步数
    - tasks_completed: 完成的任务数
    - outage_percent: outage 百分比
    - deadline_miss_rate: 超期率
    - mean_tardiness: 平均延迟
    - runtime_sec: 运行时间（秒）
    """

    def __init__(self, output_path: str):
        """
        初始化 MetricsLogger。

        Args:
            output_path: metrics.json 文件路径
        """
        self.output_path = Path(output_path)
        self.start_time: Optional[float] = None

    def start_timer(self) -> None:
        """开始计时。"""
        self.start_time = time.time()

    def save_metrics(self, metrics: Dict[str, Any]) -> None:
        """
        保存最终指标到 JSON 文件。

        Args:
            metrics: 指标字典
        """
        # 确保父目录存在
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # 添加运行时间和性能指标
        if self.start_time is not None:
            runtime_sec = time.time() - self.start_time
            metrics['runtime_sec'] = runtime_sec

            # 计算 sim_steps_per_sec（避免除零）
            steps = metrics.get('steps', 0)
            if runtime_sec > 0 and steps > 0:
                metrics['sim_steps_per_sec'] = round(steps / runtime_sec, 2)
            else:
                metrics['sim_steps_per_sec'] = 0.0

        # 写入 JSON 文件（格式化输出，便于阅读）
        with open(self.output_path, 'w') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

    def __enter__(self):
        """支持 with 语句。"""
        self.start_timer()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持 with 语句。"""
        return False
