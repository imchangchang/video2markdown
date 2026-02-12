#!/bin/bash
# Batch Test Script for Video2Markdown
# 批量测试所有视频，基于视频时长动态计算超时

set -o pipefail

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
# 预估模型：基础60秒 + 每分钟视频240秒（4倍）+ 50%余量
estimate_time() {
    local duration="$1"
    local minutes=$((duration / 60))
    # 基础60s + 每分钟240s，然后×1.5余量，最少600s(10m)，最多7200s(2h)
    local estimate=$(( (60 + minutes * 240) * 15 / 10 ))
    if [ $estimate -lt 600 ]; then
        estimate=600
    elif [ $estimate -gt 7200 ]; then
        estimate=7200
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
    timeout "$timeout_sec" $UV_CMD run python -m video2markdown process "$video_path" -o "$video_output" -l zh > "$video_output/processing.log" 2>&1
    exit_code=$?
    
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

本次测试使用**动态超时机制**：
- 基础时间：60秒
- 系数：每分钟视频增加240秒（4倍）
- 余量：×1.5
- 范围：最少10分钟，最多2小时

公式：超时 = max(600, min(7200, (60 + 分钟×240) × 1.5))

## 详细日志

查看各视频的详细处理日志：
\`\`\`
$OUTPUT_DIR/<视频名>/processing.log
\`\`\`

## 生成文件

每个视频目录包含：
- \`<视频名>.md\` - 最终 Markdown 文档
- \`<视频名>_word.md\` - AI 优化文稿
- \`<视频名>.srt\` - 字幕文件
- \`<视频名>_frames/\` - 关键帧图片
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
