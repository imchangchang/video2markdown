#!/bin/bash

# 批量处理 videos/ 目录下的所有视频（支持子目录递归）

VIDEOS_DIR="testbench/input"
OUTPUT_DIR="testbench/output"

# 默认处理前 N 个视频（0 表示全部）
LIMIT=${1:-0}

echo "=== 批量处理视频 ==="
echo ""

# 检查目录
if [ ! -d "$VIDEOS_DIR" ]; then
    echo "❌ 错误: 视频目录不存在: $VIDEOS_DIR"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# 激活环境
source .venv/bin/activate 2>/dev/null || {
    echo "❌ 请先运行: source .venv/bin/activate"
    exit 1
}

# 查找视频（递归子目录）
videos=()
while IFS= read -r -d '' f; do
    videos+=("$f")
done < <(find "$VIDEOS_DIR" -type f \( \
    -iname "*.mp4" -o \
    -iname "*.avi" -o \
    -iname "*.mov" -o \
    -iname "*.mkv" -o \
    -iname "*.flv" -o \
    -iname "*.wmv" \
\) -print0 | sort -z)

if [ ${#videos[@]} -eq 0 ]; then
    echo "⚠️ 未找到视频文件"
    exit 0
fi

echo "找到 ${#videos[@]} 个视频"

# 如果设置了限制，只处理前 N 个
if [ "$LIMIT" -gt 0 ] && [ "$LIMIT" -lt "${#videos[@]}" ]; then
    echo "本次处理前 $LIMIT 个视频（使用 ./run_batch.sh 0 处理全部）"
    videos=("${videos[@]:0:$LIMIT}")
fi

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
    safe_name=$(echo "$name" | tr ' ' '_' | tr -cd '[:alnum:]_-')
    output_file="$OUTPUT_DIR/${safe_name}.md"
    
    # 检查是否已处理过
    if [ -f "$output_file" ]; then
        echo "⏭️  跳过（已存在）: $filename"
        ((skipped++))
        continue
    fi
    
    echo "▶️  处理 ($((success+failed+skipped+1))/${#videos[@]}): $filename"
    
    if video2md process "$video" \
        -o "$output_file" \
        --title "$name" \
        --language zh \
        --keyframe-interval 30; then
        echo "✅ 完成: $filename"
        ((success++))
    else
        echo "❌ 失败: $filename"
        ((failed++))
    fi
    
    echo ""
done

echo "=== 处理统计 ==="
echo "✅ 成功: $success"
echo "⏭️  跳过: $skipped"
echo "❌ 失败: $failed"
echo ""
echo "输出文件:"
ls -lh "$OUTPUT_DIR"/*.md 2>/dev/null | tail -10
