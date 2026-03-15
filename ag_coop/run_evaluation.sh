#!/bin/bash
# 可扩展性评估 - 直接运行脚本
# 使用方法: bash run_evaluation.sh

cd /home/anders/anders/ART_MAPF/uav-ugv-ws/ag_coop

echo "========================================================================"
echo "🚀 开始可扩展性评估"
echo "========================================================================"
echo ""
echo "检查模型文件..."

# 检查模型是否存在
if [ -f "outputs/ppo_v4_golden_ratio_map02/best_model/best_model.zip" ]; then
    echo "✓ PPO V4 模型存在"
else
    echo "✗ PPO V4 模型不存在"
fi

if [ -f "outputs/vanilla_ppo_baseline_map02/best_model/best_model.zip" ]; then
    echo "✓ Vanilla PPO 模型存在"
else
    echo "✗ Vanilla PPO 模型不存在"
fi

echo ""
echo "========================================================================"
echo "运行可扩展性测试..."
echo "========================================================================"
echo ""

# 运行评估（假设在 RL 环境中）
python scripts/evaluate_scalability.py

echo ""
echo "========================================================================"
echo "生成论文图表..."
echo "========================================================================"
echo ""

# 生成图表
python scripts/plot_scalability_results.py

echo ""
echo "========================================================================"
echo "✅ 完成！"
echo "========================================================================"
echo ""
echo "结果文件位置:"
echo "  - outputs/scalability_tests/scalability_test_*.json"
echo "  - outputs/scalability_tests/plots/*.pdf"
echo ""
