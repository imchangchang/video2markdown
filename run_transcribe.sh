#!/bin/bash

# 批量转录视频生成字幕（仅 Stage 1-2：视频分析 + 音频转录）

INPUT_DIR="testbench/input"
OUTPUT_DIR="testbench/output"
LANGUAGE=${1:-zh}

echo "=== 批量视频转录 ==="
echo "输入目录: $INPUT_DIR"
echo "输出目录: $OUTPUT_DIR"
echo "语言: $LANGUAGE"
echo ""

# 检查环境
if [ ! -d ".venv" ]; then
    echo "❌ 错误: 虚拟环境不存在"
    exit 1
fi

source .venv/bin/activate

# 查找所有视频
videos=()
while IFS= read -r -d '' f; do
    videos+=("$f")
done < <(find "$INPUT_DIR" -type f \( \
    -iname "*.mp4" -o \
    -iname "*.avi" -o \
    -iname "*.mov" -o \
    -iname "*.mkv" \
\) -print0 | sort -z)

if [ ${#videos[@]} -eq 0 ]; then
    echo "⚠️ 未找到视频文件"
    exit 0
fi

echo "找到 ${#videos[@]} 个视频"
echo ""

# 统计
success=0
failed=0
skipped=0

# 处理每个视频
for video in "${videos[@]}"; do
    filename=$(basename "$video")
    name="${filename%.*}"
    
    # 清理文件名中的特殊字符
    safe_name=$(echo "$name" | tr ' ' '_' | tr '/' '_' | tr -cd '[:alnum:]_-')
    output_srt="$OUTPUT_DIR/${safe_name}.srt"
    
    # 检查是否已处理过
    if [ -f "$output_srt" ]; then
        echo "⏭️  跳过（已存在）: $filename"
        ((skipped++))
        continue
    fi
    
    echo "▶️  处理 ($((success+failed+skipped+1))/${#videos[@]}): $filename"
    
    # 提取音频并转录
    temp_wav="$OUTPUT_DIR/temp/${safe_name}.wav"
    mkdir -p "$OUTPUT_DIR/temp"
    
    echo "  📹 提取音频..."
    ffmpeg -y -i "$video" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$temp_wav" 2>/dev/null
    
    if [ ! -f "$temp_wav" ]; then
        echo "  ❌ 音频提取失败"
        ((failed++))
        continue
    fi
    
    echo "  🎙️  转录中..."
    if ./whisper-cpp \
        -m whisper.cpp/models/ggml-small-q8_0.bin \
        -f "$temp_wav" \
        -osrt \
        -of "$OUTPUT_DIR/${safe_name}" \
        -l "$LANGUAGE" 2>&1 | tail -5; then
        
        echo "  ✅ 完成: ${safe_name}.srt"
        ((success++))
    else
        echo "  ❌ 转录失败"
        ((failed++))
    fi
    
    # 清理临时文件
    rm -f "$temp_wav"
    rm -f "$OUTPUT_DIR/temp/${safe_name}.wav.json"
    
    echo ""
done

echo "=== 处理统计 ==="
echo "✅ 成功: $success"
echo "⏭️  跳过: $skipped"
echo "❌ 失败: $failed"
echo ""
echo "字幕文件输出到: $OUTPUT_DIR/"
ls -lh "$OUTPUT_DIR"/*.srt 2>/dev/null | wc -l && echo "个 SRT 文件"
