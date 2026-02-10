# Video2Markdown

将视频转换为结构化 Markdown 图文文档的 AI 工具。

## 功能特性

- 📝 **智能文字稿处理**：语音转文字，自动转换为简体中文，按主题分段整理
- 🎬 **智能图片筛选**：使用 OpenCV 预筛选，只分析有价值的画面（PPT、板书、图表）
- 🖼️ **AI 图像理解**：Kimi Vision API 辅助理解视觉内容，减少 50-70% 不必要调用
- 📄 **结构化 Markdown 输出**：AI 生成章节摘要，便于阅读和编辑
- ⏱️ **时间戳引用**：关键信息处标注视频时间点

## 核心设计

**Text-First 设计理念**：
1. **语音转录**：Whisper 将音频转为带时间戳的文字稿
2. **繁简转换**：OpenCC 自动将转录结果转为简体中文
3. **AI 总结**：Kimi 对文字稿进行理解、归纳、整理成结构化章节
4. **智能配图**：只在文字无法清晰表达时，才插入相关截图

**输出特点**：
- 纯中文文档（简体中文）
- 结构化的章节和内容总结
- 原始转录文字可折叠查看
- 图片作为辅助，仅在需要时出现
- 关键帧保存于 `{filename}_frames/` 子目录

## 快速开始

### 1. 安装依赖

```bash
# 系统依赖
sudo apt-get install ffmpeg cmake

# 一键初始化
./setup.sh
```

或手动安装：
```bash
# Python 环境
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 编译 Whisper
cd whisper.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4
cd ..
cp whisper.cpp/build/bin/whisper-cli ./whisper-cpp

# 下载模型
mkdir -p whisper.cpp/models
cd whisper.cpp/models
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small-q8_0.bin
cd ../..
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 Kimi API Key
```

### 3. 处理视频

```bash
# 单文件处理
video2md process testbench/input/example.mp4 -o testbench/output/doc.md

# 批量处理
./run_batch.sh
```

## 文件结构

```
video_process/
├── testbench/           # 测试平台（输入/输出工作目录）
│   ├── input/          # 输入视频（用户放置待处理视频）
│   └── output/         # 输出文档
│       ├── *.md        # 生成的 Markdown 文档
│       ├── *.srt       # 字幕文件
│       ├── *_frames/   # 关键帧图片目录
│       └── temp/       # 临时文件
├── whisper.cpp/        # Whisper 引擎
│   └── models/         # 语音模型（.bin 文件，gitignore）
├── src/video2markdown/ # 源代码
│   ├── asr.py          # 语音识别
│   ├── vision.py       # 图像分析与筛选
│   ├── document.py     # 文档生成
│   ├── cli.py          # 命令行接口
│   └── config.py       # 配置管理
├── tests/              # 单元测试
├── .env                # 配置文件（gitignore）
├── setup.sh            # 初始化脚本
├── run_batch.sh        # 批量处理脚本
└── README.md
```

## 配置说明

编辑 `.env` 文件：

```bash
# Kimi API（图像理解和文档生成）
KIMI_API_KEY=your-key
KIMI_MODEL=kimi-k2.5
KIMI_VISION_MODEL=kimi-k2.5

# Whisper（语音转文字）
KIMI_ASR_PROVIDER=local                    # local 或 openai
KIMI_WHISPER_LOCAL_MODEL=whisper.cpp/models/ggml-small-q8_0.bin
KIMI_WHISPER_LANGUAGE=zh

# 处理参数
KIMI_KEYFRAME_INTERVAL=30                  # 关键帧采样间隔（秒）
```

## 使用示例

```bash
# 基础用法
video2md process testbench/input/video.mp4

# 指定输出文件和标题
video2md process testbench/input/video.mp4 \
  -o testbench/output/doc.md \
  --title "视频标题"

# 高级选项
video2md process testbench/input/video.mp4 \
  -o testbench/output/doc.md \
  --title "视频标题" \
  --language zh \
  --keyframe-interval 30
```

### 命令行参数

| 参数 | 说明 | 默认值 |
|-----|------|-------|
| `video` | 输入视频文件路径 | 必需 |
| `-o, --output` | 输出 Markdown 文件路径 | 自动生成 |
| `--title` | 文档标题 | 视频文件名 |
| `--language` | 语音语言 | `zh` |
| `--keyframe-interval` | 关键帧采样间隔（秒） | `30` |

## 批量处理

使用 `run_batch.sh` 脚本批量处理 `testbench/input/` 目录下的所有视频：

```bash
# 处理所有视频
./run_batch.sh

# 脚本会处理以下格式的视频：
# - *.mp4, *.avi, *.mov, *.mkv
```

## 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定测试
pytest tests/test_asr.py -v
pytest tests/test_vision.py -v

# 代码格式化
black src/ tests/
ruff check src/ tests/
```

## 性能提示

1. **图片分析耗时**：AI 图片分析约 10-20 秒/张，智能筛选可减少 50-70% API 调用
2. **模型选择**：`ggml-small-q8_0.bin` 在准确率和速度间取得平衡
3. **关键帧间隔**：增大 `--keyframe-interval` 可减少处理帧数，加快处理速度

## 技术栈

- **Python 3.10+**
- **OpenAI API**（Kimi）- 文档生成和图像理解
- **Whisper.cpp** - 本地语音识别
- **FFmpeg** - 音视频处理
- **OpenCV** - 图像预筛选
- **OpenCC** - 繁体中文转简体中文

## 模型下载

Whisper 模型可从 [Hugging Face](https://huggingface.co/ggerganov/whisper.cpp) 下载：

| 模型 | 大小 | 速度 | 准确率 |
|-----|------|------|-------|
| `ggml-tiny-q8_0.bin` | 39 MB | 最快 | 一般 |
| `ggml-base-q8_0.bin` | 94 MB | 快 | 较好 |
| `ggml-small-q8_0.bin` | 244 MB | 中等 | 好 |
| `ggml-medium-q8_0.bin` | 669 MB | 慢 | 很好 |

推荐使用 `ggml-small-q8_0.bin` 作为平衡选择。

## 许可证

MIT License
