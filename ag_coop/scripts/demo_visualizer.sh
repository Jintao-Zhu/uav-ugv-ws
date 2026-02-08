#!/bin/bash
# Visualizer 快速演示脚本

echo "=========================================="
echo "AGCoop Visualizer 演示"
echo "=========================================="
echo ""

# 1. 生成测试数据
echo "[1/3] 生成测试数据..."
python scripts/run_day7_baselines.py --method greedy --seed 42 --out demo_vis_seed42
echo ""

# 2. 测试数据加载
echo "[2/3] 测试数据加载..."
python scripts/test_visualizer.py
echo ""

# 3. 启动可视化器
echo "[3/3] 启动可视化器..."
echo ""
echo "快捷键提示："
echo "  Space: 暂停/继续"
echo "  ↑/↓: 加速/减速"
echo "  →/←: 单步前进/后退（暂停时）"
echo "  R: 重启"
echo "  G: 显示/隐藏网格线"
echo "  T: 显示/隐藏任务"
echo "  O: 显示/隐藏目标"
echo "  ESC/Q: 退出"
echo ""
echo "按 Enter 启动可视化器..."
read

python scripts/visualize.py --run outputs/demo_vis_seed42 --cell-px 35

echo ""
echo "演示完成！"
