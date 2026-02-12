# Video2Markdown

将视频转换为结构化 Markdown 图文文档的 AI 工具。

## 功能特性

- 📝 **智能文字稿处理**：语音转文字，自动转换为简体中文，按主题分段整理
- 🎬 **智能图片筛选**：使用 OpenCV 预筛选，只分析有价值的画面（PPT、板书、图表）
- 🖼️ **AI 图像理解**：Kimi Vision API 辅助理解视觉内容，减少 50-70% 不必要调用
- 📄 **结构化 Markdown 输出**：AI 生成章节摘要，便于阅读和编辑
- ⏱️ **时间戳引用**：关键信息处标注视频时间点
- 💾 **智能缓存**：Stage 2 转录结果自动缓存，重复运行更快速

## 核心设计

**Text-First 设计理念**：
1. **语音转录**：Whisper 将音频转为带时间戳的文字稿
2. **繁简转换**：OpenCC 自动将转录结果转为简体中文
3. **AI 总结**：Kimi 对文字稿进行理解、归纳、整理成结构化章节
4. **智能配图**：只在文字无法清晰表达时，才插入相关截图

**7-Stage 处理流程**：
```
视频 → Stage1(视频分析) → Stage2(音频转录+AI优化/M1) → Stage3(关键帧提取)
  → Stage4(智能筛选/M2) → Stage5(AI图像分析/M3) → Stage6(图文融合) → Stage7(Markdown渲染)
```

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
sudo apt-get install ffmpeg

# 一键初始化（安装 Python 依赖，无需编译 Whisper）
./setup.sh
```

### 2. 下载 Whisper 模型

```bash
mkdir -p models
cd models
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-medium-q8_0.bin
cd ..
```

或使用脚本：
```bash
./models/download-ggml-model.sh medium-q8_0
```

### 3. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 Kimi API Key
```

### 4. 处理视频

```bash
# 完整流程（所有 7 个 Stage）
uv run python -m video2markdown process testdata/videos/example.mp4

# 分阶段处理
uv run python -m video2markdown stage1 testdata/videos/example.mp4  # 视频分析
uv run python -m video2markdown stage2 testdata/videos/example.mp4  # 音频转录 (M1)
uv run python -m video2markdown stage3 testdata/videos/example.mp4  # 关键帧提取
uv run python -m video2markdown stage4 testdata/videos/example.mp4  # 智能筛选 (M2)
uv run python -m video2markdown stage5 testdata/videos/example.mp4  # AI图像分析 (M3)
uv run python -m video2markdown stage6 testdata/videos/example.mp4  # 图文融合

# 批量处理
./run_batch.sh
```

## 文件结构

```
video2markdown/
├── testdata/videos/         # 测试视频目录
├── models/                  # Whisper 模型目录 (gitignore)
├── test_outputs/            # 测试输出目录
│   ├── results/            # 生成的文档
│   └── temp/               # 临时文件和缓存
├── tools/whisper-cpp/       # 预编译 Whisper 二进制
│   ├── whisper-cli         # 主程序
│   ├── whisper-cli-wrapper # 包装脚本（处理动态库路径）
│   └── lib/                # 动态库
├── src/video2markdown/      # 源代码
│   ├── stage1_analyze.py   # Stage 1: 视频分析
│   ├── stage2_transcribe.py# Stage 2: 音频转录 (M1)
│   ├── stage3_keyframes.py # Stage 3: 关键帧提取
│   ├── stage4_filter.py    # Stage 4: 智能筛选 (M2)
│   ├── stage5_analyze_images.py # Stage 5: AI图像分析 (M3)
│   ├── stage6_generate.py  # Stage 6: 图文融合
│   ├── stage7_render.py    # Stage 7: Markdown渲染
│   ├── cli.py              # 命令行接口
│   ├── config.py           # 配置管理
│   └── models.py           # 数据模型
├── prompts/                 # AI Prompt 模板
│   ├── transcript_optimization.md  # Stage 2c: 文稿优化
│   ├── image_analysis.md           # Stage 5: 图像分析
│   └── document_merge.md           # Stage 6: 图文融合
├── docs/                    # 文档
│   ├── WORKFLOW.md         # 详细处理流程
│   └── whisper-cpp-setup.md # Whisper 平台适配指南
├── tests/                   # 单元测试
├── .env                     # 配置文件 (gitignore)
├── setup.sh                 # 初始化脚本
├── run_batch.sh             # 批量处理脚本
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
KIMI_WHISPER_MODEL=medium-q8_0             # tiny/base/small/medium

# 处理参数
KIMI_KEYFRAME_INTERVAL=30                  # 关键帧采样间隔（秒）
```

## 输出文件

处理完成后，输出目录结构：

```
test_outputs/results/
└── {filename}/                          # 以视频标题命名的文件夹
    ├── {filename}.md                    # 最终图文文档
    ├── {filename}_word.md               # M1: AI优化文稿（可直接阅读替代视频）
    ├── {filename}.srt                   # 原始转录字幕（参考）
    └── {filename}_frames/               # M2 配图 + M3 说明
        ├── frame_0001_15.5s.jpg
        ├── frame_0001_15.5s.txt
        └── ...
```

## 性能提示

1. **缓存机制**：Stage 2b (Whisper 转录) 会自动缓存，重复运行跳过转录，直接进行 AI 优化
2. **图片分析耗时**：AI 图片分析约 10-20 秒/张，智能筛选可减少 50-70% API 调用
3. **模型选择**：`ggml-medium-q8_0.bin` 准确率最高；`ggml-small-q8_0.bin` 速度与准确率平衡

## 技术栈

- **Python 3.13+**
- **OpenAI API**（Kimi）- 文档生成和图像理解
- **Whisper.cpp** - 本地语音识别（内置预编译二进制）
- **FFmpeg** - 音视频处理
- **OpenCV** - 图像预筛选和场景检测
- **OpenCC** - 繁体中文转简体中文

## 模型下载

Whisper 模型可从 [Hugging Face](https://huggingface.co/ggerganov/whisper.cpp) 下载：

| 模型 | 大小 | 速度 | 准确率 |
|-----|------|------|-------|
| `ggml-tiny-q8_0.bin` | 39 MB | 最快 | 一般 |
| `ggml-base-q8_0.bin` | 94 MB | 快 | 较好 |
| `ggml-small-q8_0.bin` | 244 MB | 中等 | 好 |
| `ggml-medium-q8_0.bin` | 786 MB | 慢 | 很好 |

推荐使用 `ggml-small-q8_0.bin` 或 `ggml-medium-q8_0.bin`。

## 详细文档

- [WORKFLOW.md](docs/WORKFLOW.md) - 详细处理流程和 M1/M2/M3 定义
- [whisper-cpp-setup.md](docs/whisper-cpp-setup.md) - Whisper 跨平台适配指南
- [testbench/STAGE_TEST_CHECKLIST.md](testbench/STAGE_TEST_CHECKLIST.md) - 7-Stage 测试清单

## 许可证

MIT License
