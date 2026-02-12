#!/bin/bash
# Batch Test Script for Video2Markdown
# 批量测试所有视频，基于视频时长动态计算超时

set -o pipefail

# 当前运行的子进程PID
CURRENT_PID=""

# 信号处理：捕获 Ctrl+C，终止所有子进程
cleanup() {
    echo ""
    echo -e "${RED}收到中断信号，正在清理...${NC}"
    # 终止当前运行的子进程（如果有）
    if [ -n "$CURRENT_PID" ] && kill -0 "$CURRENT_PID" 2>/dev/null; then
        kill -TERM "$CURRENT_PID" 2>/dev/null
        wait "$CURRENT_PID" 2>/dev/null
    fi
    exit 130
}
trap cleanup INT TERM

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 查找 uv 命令
if command -v uv &> /dev/null; then
    UV_CMD="uv"
elif [ -f "./.venv/bin/python" ]; then
    UV_CMD="./.venv/bin/python -m"
else
    echo -e "${RED}错误: 未找到 uv 命令${NC}"
    echo "请安装 uv: https://github.com/astral-sh/uv"
    exit 1
fi

# 配置
VIDEO_DIR="testdata/videos"
OUTPUT_DIR="test_outputs/results/batch_test_$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$OUTPUT_DIR/batch_test.log"
SUMMARY_FILE="$OUTPUT_DIR/summary.md"

# 创建输出目录
mkdir -p "$OUTPUT_DIR"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Video2Markdown 批量测试${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "输出目录: $OUTPUT_DIR"
echo "开始时间: $(date)"
echo ""

# 初始化摘要文件
cat > "$SUMMARY_FILE" << EOF
# Video2Markdown 批量测试报告

**测试时间**: $(date)
**视频目录**: $VIDEO_DIR
**输出目录**: $OUTPUT_DIR

## 测试结果汇总

| 序号 | 视频名称 | 时长 | 预估时间 | 实际耗时 | 状态 |
|-----|---------|------|---------|---------|------|
EOF

# 获取所有视频文件
total=0
success=0
failed=0

# 检查视频目录
if [ ! -d "$VIDEO_DIR" ]; then
    echo -e "${RED}错误: 视频目录不存在: $VIDEO_DIR${NC}"
    exit 1
fi

# 获取视频列表
video_list=()
for video in "$VIDEO_DIR"/*.mp4; do
    [ -f "$video" ] && video_list+=("$video")
done

total=${#video_list[@]}

if [ $total -eq 0 ]; then
    echo -e "${RED}错误: 未在 $VIDEO_DIR 找到视频文件${NC}"
    exit 1
fi

echo -e "发现 ${YELLOW}$total${NC} 个视频文件"
echo ""

# 辅助函数：获取视频时长（秒）
get_duration() {
    local video="$1"
    local duration
    duration=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$video" 2>/dev/null | cut -d. -f1)
    echo "${duration:-0}"
}

# 辅助函数：预估处理时间（基于视频时长）
# 基于两轮测试数据优化（实际耗时约为视频时长的 1.5x ~ 3.0x）
# 新公式：基础60秒 + 视频时长×2 + 100%余量 = 视频时长×4 + 60
# 范围：5分钟 ~ 1小时
estimate_time() {
    local duration="$1"
    # 新公式：视频时长 × 4 + 60秒基础
    local estimate=$(( duration * 4 + 60 ))
    # 限制范围：最少300s(5m)，最多3600s(1h)
    if [ $estimate -lt 300 ]; then
        estimate=300
    elif [ $estimate -gt 3600 ]; then
        estimate=3600
    fi
    echo "$estimate"
}

# 辅助函数：格式化时长
format_duration() {
    local seconds="$1"
    if [ $seconds -lt 60 ]; then
        echo "${seconds}s"
    elif [ $seconds -lt 3600 ]; then
        echo "$((seconds / 60))m $((seconds % 60))s"
    else
        echo "$((seconds / 3600))h $((seconds % 3600 / 60))m"
    fi
}

# 处理每个视频
idx=0
for video_path in "${video_list[@]}"; do
    idx=$((idx + 1))
    video_name=$(basename "$video_path")
    video_stem="${video_name%.*}"
    video_output="$OUTPUT_DIR/$video_stem"
    
    # 获取视频时长
    duration=$(get_duration "$video_path")
    duration_fmt=$(format_duration "$duration")
    
    # 计算动态超时
    timeout_sec=$(estimate_time "$duration")
    timeout_fmt=$(format_duration "$timeout_sec")
    
    echo -e "${BLUE}[$idx/$total]${NC} 处理: ${YELLOW}$video_name${NC}"
    echo "  时长: $duration_fmt | 预估: $timeout_fmt | 超时限制: $timeout_fmt"
    
    # 创建视频专属输出目录
    mkdir -p "$video_output"
    
    # 记录开始时间
    start_time=$(date +%s)
    
    # 运行处理（使用动态计算的超时）
    # --foreground: 让信号直接传递到子进程，Ctrl+C 可以立即停止
    # --signal=TERM: 超时时发送 TERM 信号
    timeout --foreground --signal=TERM "$timeout_sec" $UV_CMD run python -m video2markdown process "$video_path" -o "$video_output" -l zh > "$video_output/processing.log" 2>&1 &
    CURRENT_PID=$!
    
    # 等待进程完成，同时响应 Ctrl+C
    wait $CURRENT_PID
    exit_code=$?
    CURRENT_PID=""
    
    # 计算耗时
    end_time=$(date +%s)
    elapsed=$((end_time - start_time))
    elapsed_fmt=$(format_duration "$elapsed")
    
    # 分析结果
    if [ $exit_code -eq 0 ]; then
        status="${GREEN}✓ 成功${NC}"
        success=$((success + 1))
        status_md="✅ 成功"
    elif [ $exit_code -eq 124 ]; then
        status="${RED}✗ 超时${NC}"
        failed=$((failed + 1))
        status_md="⏱️ 超时"
    else
        status="${RED}✗ 失败${NC}"
        failed=$((failed + 1))
        status_md="❌ 失败"
    fi
    
    # 显示结果
    echo -e "  状态: $status"
    echo -e "  实际耗时: $elapsed_fmt"
    echo ""
    
    # 添加到摘要
    echo "| $idx | $video_name | $duration_fmt | $timeout_fmt | $elapsed_fmt | $status_md |" >> "$SUMMARY_FILE"
    
    # 保存到日志
    echo "[$idx/$total] $video_name - $status_md - 时长:$duration_fmt 预估:$timeout_fmt 实际:$elapsed_fmt" >> "$LOG_FILE"
done

# 生成总结
cat >> "$SUMMARY_FILE" << EOF

## 统计

- **总视频数**: $total
- **成功**: $success
- **失败**: $failed
- **成功率**: $(( success * 100 / total ))%

## 超时机制说明

本次测试使用**动态超时机制**（基于两轮实测数据优化）：
- 基础时间：60秒
- 视频时长系数：×4（实测平均为 1.5x ~ 3.0x）
- 范围：最少5分钟，最多1小时

公式：超时 = max(300, min(3600, 视频秒数×4 + 60))

优化依据：
- 第一轮测试（无缓存）：实际耗时/视频时长 = 1.4x ~ 3.0x
- 第二轮测试（有缓存）：实际耗时/视频时长 = 1.1x ~ 2.8x

## 详细日志

查看各视频的详细处理日志：
\`\`\`
$OUTPUT_DIR/<视频名>/processing.log
\`\`\`

## AI API 用量汇总

| 视频 | API调用 | Token用量(输入/输出/总计) | 费用 |
|-----|--------|------------------------|-----|
EOF

# 初始化汇总变量
total_api_calls=0
total_input_tokens=0
total_output_tokens=0

# 从每个视频的 processing.log 中提取统计信息
for video_path in "${video_list[@]}"; do
    video_name=$(basename "$video_path")
    video_stem="${video_name%.*}"
    log_file="$OUTPUT_DIR/$video_stem/processing.log"
    
    if [ -f "$log_file" ] && grep -q "📊 AI API 用量汇总" "$log_file" 2>/dev/null; then
        # 从汇总行提取数据
        summary_line=$(grep "📊 AI API 用量汇总" -A3 "$log_file" 2>/dev/null | grep "Token 用量")
        api_calls=$(grep "API 调用" "$log_file" 2>/dev/null | tail -1 | grep -oP '\d+' | head -1)
        
        # 提取输入/输出/总计 token
        input_tok=$(echo "$summary_line" | grep -oP '\d+(?=\s*输入)' | sed 's/,//g' | head -1)
        output_tok=$(echo "$summary_line" | grep -oP '\d+(?=\s*输出)' | sed 's/,//g' | head -1)
        total_tok=$(echo "$summary_line" | grep -oP '\d+(?=\s*总计)' | sed 's/,//g' | head -1)
        
        # 提取费用
        cost_line=$(grep "预估费用" "$log_file" 2>/dev/null | tail -1)
        cost=$(echo "$cost_line" | grep -oP '(?<=¥)[0-9.]+' | head -1)
        
        # 累加到总计
        [ -n "$api_calls" ] && total_api_calls=$((total_api_calls + api_calls))
        [ -n "$input_tok" ] && total_input_tokens=$((total_input_tokens + input_tok))
        [ -n "$output_tok" ] && total_output_tokens=$((total_output_tokens + output_tok))
        
        # 格式化显示
        [ -z "$api_calls" ] && api_calls="0"
        [ -z "$input_tok" ] && input_tok="0"
        [ -z "$output_tok" ] && output_tok="0"
        [ -z "$total_tok" ] && total_tok="0"
        [ -z "$cost" ] && cost="N/A"
        
        echo "| $video_stem | $api_calls | $input_tok / $output_tok / $total_tok | ¥$cost |" >> "$SUMMARY_FILE"
    else
        echo "| $video_stem | - | - | - |" >> "$SUMMARY_FILE"
    fi
done

# 计算总费用
total_tokens=$((total_input_tokens + total_output_tokens))
if command -v python3 &> /dev/null; then
    total_cost=$(python3 -c "print(f'{( $total_input_tokens * 4.8 / 1000000 + $total_output_tokens * 20 / 1000000 ):.4f}')")
else
    total_cost="N/A"
fi

echo "| **总计** | **$total_api_calls** | **$total_input_tokens / $total_output_tokens / $total_tokens** | **¥$total_cost** |" >> "$SUMMARY_FILE"

cat >> "$SUMMARY_FILE" << EOF

> 价格标准：Kimi K2.5 (2025-02)
> - 输入: ¥4.8 / 百万 tokens
> - 输出: ¥20 / 百万 tokens

## 生成文件

每个视频目录包含：
- \`<视频名>.md\` - 最终 Markdown 文档
- \`<视频名>_word.md\` - AI 优化文稿
- \`<视频名>.srt\` - 字幕文件
- \`images/\` - 关键配图（统一存放）
- \`temp/\` - 中间产物
EOF

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  批量测试完成${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "总视频数: ${YELLOW}$total${NC}"
echo -e "成功: ${GREEN}$success${NC}"
echo -e "失败: ${RED}$failed${NC}"
echo ""
echo "输出目录: $OUTPUT_DIR"
echo "摘要报告: $SUMMARY_FILE"
echo "详细日志: $LOG_FILE"
echo ""
echo "结束时间: $(date)"
