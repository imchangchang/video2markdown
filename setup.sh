#!/bin/bash

# Video2Markdown 环境初始化脚本

set -e

echo "=== Video2Markdown 初始化 ==="
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未安装 Python3"
    exit 1
fi

python3 --version
echo ""

# 检查 FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  警告: 未安装 FFmpeg"
    echo "   请运行: sudo apt-get install ffmpeg"
    exit 1
fi

echo "✓ FFmpeg 已安装"
echo ""

# 创建虚拟环境
echo "创建虚拟环境..."
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -e . -q

# 检查 .env
if [ ! -f ".env" ]; then
    echo "创建 .env 配置文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，填入你的 Kimi API Key"
fi

# 检查 whisper.cpp
if [ ! -f "whisper-cpp" ]; then
    echo "编译 whisper.cpp..."
    if [ -d "whisper.cpp" ]; then
        cd whisper.cpp
        cmake -B build -DCMAKE_BUILD_TYPE=Release 2>/dev/null || echo "cmake 可能未安装"
        cmake --build build -j4 2>/dev/null || echo "编译失败，请检查依赖"
        cd ..
        if [ -f "whisper.cpp/build/bin/whisper-cli" ]; then
            cp whisper.cpp/build/bin/whisper-cli ./whisper-cpp
            echo "✓ whisper.cpp 编译完成"
        fi
    else
        echo "⚠️  whisper.cpp 目录不存在，请手动下载编译"
    fi
else
    echo "✓ whisper-cpp 已存在"
fi

echo ""
echo "=== 初始化完成 ==="
echo ""
echo "使用方法:"
echo "  1. 激活环境: source .venv/bin/activate"
echo "  2. 编辑配置: vim .env"
echo "  3. 处理视频: video2md process videos/example.mp4"
echo ""
