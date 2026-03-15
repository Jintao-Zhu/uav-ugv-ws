#!/bin/bash
# 一键训练所有模型

echo "=========================================="
echo "🚀 开始训练所有模型"
echo "=========================================="

# 1. 训练 Vanilla PPO (约3小时)
echo ""
echo "1/2 训练 Vanilla PPO Baseline..."
python scripts/train_vanilla_ppo.py

# 2. 训练 DQN (约3小时)
echo ""
echo "2/2 训练 DQN Baseline..."
python scripts/train_dqn_baseline.py

echo ""
echo "=========================================="
echo "✅ 所有模型训练完成"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 运行综合对比: python scripts/compare_all_methods.py"
echo "2. 运行可扩展性测试: python scripts/evaluate_scalability.py"
