#!/usr/bin/env python3
"""
重新保存 PPO V4 模型以兼容当前 numpy 版本
"""

import sys
from pathlib import Path
import numpy as np

# 添加兼容性
if not hasattr(np, '_core'):
    import numpy.core as core
    np._core = core
    np._core.numeric = core.numeric

from stable_baselines3 import PPO

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("尝试加载 PPO V4 模型...")

model_path = project_root / "outputs" / "ppo_v4_golden_ratio_map02" / "best_model" / "best_model.zip"
output_path = project_root / "outputs" / "ppo_v4_golden_ratio_map02" / "best_model" / "best_model_fixed.zip"

try:
    model = PPO.load(str(model_path))
    print("✓ 模型加载成功")

    # 重新保存
    model.save(str(output_path))
    print(f"✓ 模型已重新保存: {output_path}")

except Exception as e:
    print(f"✗ 失败: {e}")
    import traceback
    traceback.print_exc()
