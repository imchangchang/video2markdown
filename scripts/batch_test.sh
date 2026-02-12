#!/bin/bash
# Batch Test Script for Video2Markdown
# 批量测试所有视频，生成对比报告

set -e

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
    # 使用虚拟环境直接运行
    UV_CMD="./.venv/bin/python -m"
else
    echo -e "${RED}错误: 未找到 uv 命令${NC}"
    echo "请安装 uv: https://github.com/astral-sh/uv"
    echo "或使用: curl -LsSf https://astral.sh/uv/install.sh | sh"
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

| 序号 | 视频名称 | 时长 | 稳定区间 | 候选帧 | 通过帧 | 状态 | 耗时 |
|-----|---------|------|---------|-------|-------|------|------|
EOF

# 获取所有视频文件
total=0
success=0
failed=0

for video in "$VIDEO_DIR"/*.mp4; do
    [ -f "$video" ] || continue
    ((total++))
done

echo -e "发现 ${YELLOW}$total${NC} 个视频文件"
echo ""

# 处理每个视频
idx=0
for video_path in "$VIDEO_DIR"/*.mp4; do
    [ -f "$video_path" ] || continue
    
    ((idx++))
    video_name=$(basename "$video_path")
    video_stem="${video_name%.*}"
    video_output="$OUTPUT_DIR/$video_stem"
    
    echo -e "${BLUE}[$idx/$total]${NC} 处理: ${YELLOW}$video_name${NC}"
    
    # 创建视频专属输出目录
    mkdir -p "$video_output"
    
    # 记录开始时间
    start_time=$(date +%s)
    
    # 运行处理（带超时保护）
    set +e
    timeout 600 $UV_CMD run python -m video2markdown process "$video_path" -o "$video_output" -l zh > "$video_output/processing.log" 2>&1
    exit_code=$?
    set -e
    
    # 计算耗时
    end_time=$(date +%s)
    elapsed=$((end_time - start_time))
    elapsed_fmt="$((elapsed / 60))m $((elapsed % 60))s"
    
    # 分析结果
    if [ $exit_code -eq 0 ]; then
        status="${GREEN}✓ 成功${NC}"
        ((success++))
        status_md="✅ 成功"
    elif [ $exit_code -eq 124 ]; then
        status="${RED}✗ 超时${NC}"
        ((failed++))
        status_md="⏱️ 超时"
    else
        status="${RED}✗ 失败${NC}"
        ((failed++))
        status_md="❌ 失败"
    fi
    
    # 提取关键指标
    if [ -f "$video_output"/*_stage1.json ]; then
        duration=$(grep '"duration"' "$video_output"/*_stage1.json | head -1 | sed 's/.*: \([0-9.]*\).*/\1/')
        stable_count=$(grep -c 'stable_interval' "$video_output"/*_stage3.json 2>/dev/null || echo "0")
        frame_count=$(grep -c '"timestamp"' "$video_output"/*_stage3.json 2>/dev/null || echo "0")
        passed_count=$(grep -c 'KEEP' "$video_output/processing.log" 2>/dev/null || echo "0")
    else
        duration="N/A"
        stable_count="N/A"
        frame_count="N/A"
        passed_count="N/A"
    fi
    
    # 显示结果
    echo -e "  状态: $status"
    echo -e "  耗时: $elapsed_fmt"
    echo ""
    
    # 添加到摘要
    echo "| $idx | $video_name | ${duration:-N/A}s | $stable_count | $frame_count | $passed_count | $status_md | $elapsed_fmt |" >> "$SUMMARY_FILE"
    
    # 保存到日志
    echo "[$idx/$total] $video_name - $status_md - $elapsed_fmt" >> "$LOG_FILE"
done

# 生成总结
cat >> "$SUMMARY_FILE" << EOF

## 统计

- **总视频数**: $total
- **成功**: $success
- **失败**: $failed
- **成功率**: $(( success * 100 / total ))%

## 详细日志

查看各视频的详细处理日志：
\`\`\`
$OUTPUT_DIR/<视频名>/processing.log
\`\`\`

## 生成文件

每个视频目录包含：
- `<视频名>.md` - 最终 Markdown 文档
- `<视频名>_word.md` - AI 优化文稿
- `<视频名>.srt` - 字幕文件
- `<视频名>_frames/` - 关键帧图片
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
