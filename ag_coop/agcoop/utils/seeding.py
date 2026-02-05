"""随机种子工具，用于实验可复现性。"""
import random
import numpy as np


def seed_everything(seed: int) -> None:
    """
    为所有随机数生成器设置种子。

    Args:
        seed: 随机种子值
    """
    random.seed(seed)
    np.random.seed(seed)

    # 预留 torch 接口（Day1 暂不使用）
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except ImportError:
        pass  # torch 未安装，跳过
