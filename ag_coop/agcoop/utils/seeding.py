"""Seeding utilities for reproducibility."""
import random
import numpy as np


def seed_everything(seed: int) -> None:
    """
    Set random seeds for all random number generators.

    Args:
        seed: Random seed value
    """
    random.seed(seed)
    np.random.seed(seed)

    # Reserved for torch (Day1 not used yet)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed(seed)
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
            torch.backends.cudnn.benchmark = False
    except ImportError:
        pass  # torch not installed, skip
