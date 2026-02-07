#!/bin/bash
# Day 6.5 快速调试脚本
# 用法: ./scripts/quick_debug.sh outputs/test_step5_exp_b

set -e

if [ $# -eq 0 ]; then
    echo "用法: $0 <output_dir>"
    echo "示例: $0 outputs/test_step5_exp_b"
    exit 1
fi

RUN_DIR=$1

if [ ! -d "$RUN_DIR" ]; then
    echo "❌ 目录不存在: $RUN_DIR"
    exit 1
fi

echo "════════════════════════════════════════════════════════════════════════════════"
echo "  Day 6.5 快速调试 - $RUN_DIR"
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""

# 1. 检查文件是否存在
echo "📁 检查文件..."
FILES=("config_resolved.yaml" "metrics.json" "trace.jsonl")
for file in "${FILES[@]}"; do
    if [ -f "$RUN_DIR/$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (缺失)"
    fi
done
echo ""

# 2. 关键配置
echo "⚙️  关键配置:"
if [ -f "$RUN_DIR/config_resolved.yaml" ]; then
    grep -E "n_ugv:|n_uav:|H:|time_budget_ms:|seed:|horizon_steps:" "$RUN_DIR/config_resolved.yaml" | sed 's/^/  /'
else
    echo "  (config_resolved.yaml 不存在)"
fi
echo ""

# 3. 关键指标
echo "📊 关键指标:"
if [ -f "$RUN_DIR/metrics.json" ]; then
    python3 -c "
import json
with open('$RUN_DIR/metrics.json') as f:
    m = json.load(f)

print(f\"  collision_free: {m.get('collision_free', 'N/A')}\")
print(f\"  mapf_calls: {m.get('mapf_calls', 0)}\")
print(f\"  mapf_success_calls: {m.get('mapf_success_calls', 0)}\")
print(f\"  mapf_timeout_calls: {m.get('mapf_timeout_calls', 0)}\")
print(f\"  mapf_fail_calls: {m.get('mapf_fail_calls', 0)}\")
print(f\"  completion_rate: {m.get('completion_rate', 0):.2%}\")
print(f\"  termination_reason: {m.get('termination_reason', 'N/A')}\")
"
else
    echo "  (metrics.json 不存在)"
fi
echo ""

# 4. 冲突检测
echo "🔍 冲突检测:"
if [ -f "$RUN_DIR/trace.jsonl" ]; then
    python scripts/check_collisions.py --trace "$RUN_DIR/trace.jsonl" 2>&1 | grep -E "✓|✗|错误:" | sed 's/^/  /'
else
    echo "  (trace.jsonl 不存在)"
fi
echo ""

# 5. 诊断建议
echo "💡 诊断建议:"
if [ -f "$RUN_DIR/metrics.json" ]; then
    python3 -c "
import json
with open('$RUN_DIR/metrics.json') as f:
    m = json.load(f)

suggestions = []

if not m.get('collision_free', True):
    suggestions.append('❌ collision_free=false → 检查 controller bug（路径执行逻辑）')

if m.get('mapf_fail_calls', 0) > 0:
    suggestions.append('❌ mapf_fail_calls > 0 → 检查 core 集成 bug（MAPF 调用失败）')

if m.get('mapf_timeout_calls', 0) == m.get('mapf_calls', 0) and m.get('mapf_calls', 0) > 0:
    suggestions.append('⚠️  所有 MAPF 调用都超时 → 检查 time_budget_ms 设置或 MAPF 性能')

if m.get('completion_rate', 0) == 0 and m.get('total_tasks', 0) > 0:
    suggestions.append('⚠️  completion_rate=0 → 检查任务分配或路径规划逻辑')

if not suggestions:
    suggestions.append('✓ 主要指标正常，可能是日志/口径 bug')

for s in suggestions:
    print(f'  {s}')
"
else
    echo "  (metrics.json 不存在)"
fi
echo ""

# 6. 下一步
echo "📋 下一步操作:"
echo "  1. 查看完整报告: python scripts/generate_debug_report.py --run $RUN_DIR"
echo "  2. 查看 trace 详情: less $RUN_DIR/trace.jsonl"
echo "  3. 查看完整配置: cat $RUN_DIR/config_resolved.yaml"
echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
