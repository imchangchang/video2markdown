#!/bin/bash

# 批量处理 videos/ 目录下的所有视频

VIDEOS_DIR="testbench/input"
OUTPUT_DIR="testbench/output"

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

# 查找视频
videos=()
for ext in mp4 avi mov mkv; do
    for f in "$VIDEOS_DIR"/*.$ext; do
        [ -f "$f" ] && videos+=("$f")
    done
done

if [ ${#videos[@]} -eq 0 ]; then
    echo "⚠️ 未找到视频文件"
    exit 0
fi

echo "找到 ${#videos[@]} 个视频"
echo ""

# 处理每个视频
for video in "${videos[@]}"; do
    filename=$(basename "$video")
    name="${filename%.*}"
    echo "处理: $filename"
    
    video2md process "$video" \
        -o "$OUTPUT_DIR/$name.md" \
        --title "$name" \
        --language zh \
        --keyframe-interval 30
    
    echo ""
done

echo "=== 处理完成 ==="
ls -lh "$OUTPUT_DIR"/*.md 2>/dev/null
