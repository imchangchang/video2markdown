# 开发环境迁移指南

本文档帮助你在新电脑上快速恢复 Video2Markdown 开发环境。

## 快速开始（推荐）

```bash
# 1. 克隆仓库
git clone <repository-url>
cd video_process

# 2. 初始化子模块（whisper.cpp）
git submodule update --init --recursive

# 3. 运行初始化脚本
./setup.sh

# 4. 配置 API Key
cp .env.example .env
vim .env  # 填入你的 Kimi API Key

# 5. 验证安装
source .venv/bin/activate
video2md --help
```

## 手动安装步骤

如果自动脚本遇到问题，可以按以下步骤手动安装：

### 1. 系统依赖

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install ffmpeg cmake

# macOS
brew install ffmpeg cmake
```

### 2. Python 环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. 编译 Whisper

```bash
cd whisper.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4
cd ..
cp whisper.cpp/build/bin/whisper-cli ./whisper-cpp
```

### 4. 下载语音模型

```bash
mkdir -p whisper.cpp/models
cd whisper.cpp/models
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small-q8_0.bin
cd ../..
```

### 5. 配置环境

```bash
cp .env.example .env
# 编辑 .env，填入 KIMI_API_KEY
```

## 文件说明

迁移时需要保留/注意的文件：

| 文件/目录 | 说明 | 迁移方式 |
|---------|------|---------|
| `.env` | API Key 和配置（**敏感**） | 手动复制，不要提交到 git |
| `whisper.cpp/models/*.bin` | 语音模型（大文件） | 重新下载或复制 |
| `testbench/input/` | 输入视频 | 按需复制 |
| `testbench/output/` | 生成文档 | 可选保留 |

## 常见问题

### 1. whisper.cpp 子模块为空

```bash
git submodule update --init --recursive
```

### 2. 模型文件下载慢

使用镜像源或手动下载后复制到 `whisper.cpp/models/` 目录。

### 3. FFmpeg 未安装

```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

### 4. Python 版本要求

需要 Python 3.10+：

```bash
python3 --version  # 检查版本
```

## 验证安装

运行测试确保环境正常：

```bash
# 运行单元测试
pytest tests/ -v

# 测试转录功能（需要模型文件）
video2md process testbench/input/test.mp4 --dry-run
```

## 开发工作流

```bash
# 激活环境
source .venv/bin/activate

# 代码格式化
black src/ tests/
ruff check src/ tests/

# 运行测试
pytest tests/ -v

# 处理视频
video2md process testbench/input/video.mp4

# 批量处理
./run_batch.sh
```

## 环境变量速查

关键配置项：

```bash
KIMI_API_KEY=your-api-key          # 必需：Kimi API Key
KIMI_MODEL=kimi-k2.5               # 文本生成模型
KIMI_VISION_MODEL=kimi-k2.5        # 视觉分析模型
KIMI_ASR_PROVIDER=local            # ASR 提供商：local 或 openai
KIMI_WHISPER_LANGUAGE=zh           # 语音语言
KIMI_KEYFRAME_INTERVAL=30          # 关键帧间隔（秒）
```
