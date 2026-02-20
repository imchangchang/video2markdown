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

# 加载 .env 文件中的价格配置（如果存在）
if [ -f ".env" ]; then
    # 读取价格配置，使用默认值
    PRICE_INPUT_PER_1M=$(grep "^LLM_PRICE_INPUT_PER_1M=" .env 2>/dev/null | cut -d= -f2 || echo "4.8")
    PRICE_OUTPUT_PER_1M=$(grep "^LLM_PRICE_OUTPUT_PER_1M=" .env 2>/dev/null | cut -d= -f2 || echo "20.0")
else
    # 使用默认价格
    PRICE_INPUT_PER_1M="4.8"
    PRICE_OUTPUT_PER_1M="20.0"
fi

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

# 获取媒体文件列表（支持视频和音频格式）
video_list=()
for ext in mp4 wav mp3 m4a mov avi mkv flv wma aac ogg flac; do
    for video in "$VIDEO_DIR"/*.$ext; do
        [ -f "$video" ] && video_list+=("$video")
    done
done

# 去重（避免同一文件匹配多个扩展名）
IFS=$'\n' sorted=($(sort -u <<<"${video_list[*]}"))
unset IFS
video_list=("${sorted[@]}")

total=${#video_list[@]}

if [ $total -eq 0 ]; then
    echo -e "${RED}错误: 未在 $VIDEO_DIR 找到媒体文件（支持: mp4, wav, mp3, m4a, mov, avi, mkv, flv, wma, aac, ogg, flac）${NC}"
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
EOF

# 使用 Python 生成 API 用量汇总（包括按阶段统计）
if command -v python3 &> /dev/null; then
    python3 << PYEOF
import json
from pathlib import Path
from collections import defaultdict

output_dir = Path("$OUTPUT_DIR")
price_input = float("$PRICE_INPUT_PER_1M")
price_output = float("$PRICE_OUTPUT_PER_1M")

# 阶段名称映射
stage_names = {
    'stage2_transcribe': 'Stage 2: 转录优化',
    'stage5_analyze_images': 'Stage 5: 图像分析', 
    'stage6_generate': 'Stage 6: 文档生成',
    'unknown': '未知阶段'
}

# 收集统计
video_stats = []
stage_stats = defaultdict(lambda: {'calls': 0, 'input': 0, 'output': 0})
total_api_calls = 0
total_input = 0
total_output = 0

for video_dir in sorted(output_dir.iterdir()):
    if video_dir.is_dir():
        tokens_file = video_dir / 'temp' / 'ai_tokens.json'
        if tokens_file.exists():
            try:
                data = json.load(open(tokens_file))
                total = data.get('total', {})
                
                api_calls = total.get('api_calls', 0)
                input_tok = total.get('prompt_tokens', 0)
                output_tok = total.get('completion_tokens', 0)
                total_tok = total.get('total_tokens', 0)
                cost = total.get('total_cost', 0)
                
                video_stats.append({
                    'name': video_dir.name,
                    'calls': api_calls,
                    'input': input_tok,
                    'output': output_tok,
                    'total': total_tok,
                    'cost': cost
                })
                
                total_api_calls += api_calls
                total_input += input_tok
                total_output += output_tok
                
                # 按阶段汇总
                for r in data.get('records', []):
                    stage = r.get('stage', 'unknown')
                    stage_stats[stage]['calls'] += 1
                    stage_stats[stage]['input'] += r.get('prompt_tokens', 0)
                    stage_stats[stage]['output'] += r.get('completion_tokens', 0)
                    
            except Exception as e:
                print(f"Warning: Failed to parse {tokens_file}: {e}")

# 写入汇总报告
with open("$SUMMARY_FILE", "a") as f:
    # 按视频汇总
    f.write("\n## AI API 用量汇总（按视频）\n\n")
    f.write("| 视频 | API调用 | Token用量(输入/输出/总计) | 费用 |\n")
    f.write("|-----|--------|------------------------|-----|\n")
    
    for v in video_stats:
        f.write(f"| {v['name']} | {v['calls']} | {v['input']:,} / {v['output']:,} / {v['total']:,} | ¥{v['cost']:.4f} |\n")
    
    total_cost = (total_input * price_input / 1_000_000) + (total_output * price_output / 1_000_000)
    f.write(f"| **总计** | **{total_api_calls}** | **{total_input:,} / {total_output:,} / {total_input+total_output:,}** | **¥{total_cost:.4f}** |\n")
    
    # 按阶段汇总
    f.write("\n## AI API 用量汇总（按阶段）\n\n")
    f.write("| 阶段 | API调用 | 输入Tokens | 输出Tokens | 总Tokens | 费用 |\n")
    f.write("|-----|--------|-----------|-----------|---------|-----|\n")
    
    for stage, stats in sorted(stage_stats.items()):
        name = stage_names.get(stage, stage)
        calls = stats['calls']
        inp = stats['input']
        out = stats['output']
        total_tok = inp + out
        cost = (inp * price_input / 1_000_000) + (out * price_output / 1_000_000)
        f.write(f"| {name} | {calls} | {inp:,} | {out:,} | {total_tok:,} | ¥{cost:.4f} |\n")
    
    if stage_stats:
        f.write(f"| **总计** | **{total_api_calls}** | **{total_input:,}** | **{total_output:,}** | **{total_input+total_output:,}** | **¥{total_cost:.4f}** |\n")
    
    f.write(f"\n> 价格标准（从 .env 读取）\n")
    f.write(f"> - 输入: ¥{price_input} / 百万 tokens\n")
    f.write(f"> - 输出: ¥{price_output} / 百万 tokens\n")

print(f"API usage summary generated")
PYEOF
else
    echo "Python3 not available, skipping API usage summary"
fi

# 添加生成文件说明
cat >> "$SUMMARY_FILE" << EOF

## 生成文件

每个视频目录包含：
- \`<视频名>.md\` - 最终 Markdown 文档
- \`images/\` - 关键配图（统一存放）
- \`temp/\` - 中间产物
  - \`<视频名>_word.md\` - AI 优化文稿 (M1)
  - \`<视频名>.srt\` - 字幕文件
  - \`ai_tokens.json\` - AI API 调用明细
  - \`summary.md\` - 处理汇总报告
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
