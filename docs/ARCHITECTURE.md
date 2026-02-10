# Video2Markdown 架构设计

## 1. 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Video2Markdown                          │
├─────────────────────────────────────────────────────────────────┤
│  CLI Layer (cli.py)                                             │
│  ├── 命令行参数解析                                              │
│  ├── 处理流程编排                                                │
│  └── 进度显示和错误处理                                          │
├─────────────────────────────────────────────────────────────────┤
│  Core Processing Layer                                          │
│  ├─────────────┬─────────────┬─────────────┬──────────────────┐ │
│  │  Video      │  Audio      │  ASR        │  Vision          │ │
│  │  (video.py) │  (audio.py) │  (asr.py)   │  (vision.py)     │ │
│  ├─────────────┼─────────────┼─────────────┼──────────────────┤ │
│  │ • 视频信息   │ • 音频提取   │ • Whisper   │ • 关键帧提取      │ │
│  │ • 关键帧    │ • 格式转换   │ • 繁简转换   │ • 图片筛选        │ │
│  │   提取      │             │ • 分段处理   │ • AI 图像分析     │ │
│  └─────────────┴─────────────┴─────────────┴──────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│  Document Layer (document.py)                                   │
│  ├── 章节划分                                                    │
│  ├── 内容摘要生成                                                │
│  └── Markdown 渲染                                               │
├─────────────────────────────────────────────────────────────────┤
│  Config Layer (config.py)                                       │
│  ├── 环境变量管理                                                │
│  └── 配置验证                                                    │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 处理流程

```
输入视频
    │
    ▼
┌─────────────┐
│ 1. 视频分析  │──► 获取时长、分辨率、FPS
└─────────────┘
    │
    ▼
┌─────────────┐
│ 2. 音频提取  │──► 提取为 WAV 格式
└─────────────┘
    │
    ▼
┌─────────────┐
│ 3. 语音识别  │──► Whisper 转录 ──► OpenCC 繁简转换
└─────────────┘
    │
    ▼
┌─────────────┐
│ 4. 关键帧   │──► 场景检测 + 均匀采样
│    提取     │
└─────────────┘
    │
    ▼
┌─────────────┐     ┌─────────────────────────────┐
│ 5. 图片筛选  │────►│ • 颜色分析（PPT/白板检测）    │
│             │     │ • 文字检测（边缘密度）        │
│             │     │ • 转录上下文分析             │
└─────────────┘     └─────────────────────────────┘
    │
    ▼ (筛选后)
┌─────────────┐
│ 6. AI 图像   │──► Kimi Vision API 分析
│    分析     │
└─────────────┘
    │
    ▼
┌─────────────┐
│ 7. AI 文档   │──► 章节划分 + 摘要生成
│    生成     │
└─────────────┘
    │
    ▼
输出 Markdown
```

## 3. 模块详细设计

### 3.1 CLI (cli.py)

```python
class VideoProcessor:
    def process(self, video_path, output_path, options)
        # 1. 分析视频
        # 2. 转录音频
        # 3. 提取关键帧
        # 4. 分析图片
        # 5. 生成文档
```

### 3.2 ASR (asr.py)

```python
@dataclass
class TranscriptSegment:
    start_time: float    # 开始时间（秒）
    end_time: float      # 结束时间（秒）
    text: str           # 文本内容（简体中文）

class WhisperTranscriber:
    def transcribe(audio_path) -> list[TranscriptSegment]
    def to_simplified_chinese(text) -> str  # OpenCC 转换
```

### 3.3 Vision (vision.py)

```python
class ImageAnalyzer:
    def extract_keyframes(video_path, interval) -> list[Keyframe]
    
    def should_analyze_image(image_path, transcript) -> tuple[bool, str]
        # 1. 检查是否是 PPT/白板（颜色分析）
        # 2. 检查文字密度（边缘检测）
        # 3. 检查转录上下文
        
    def analyze_with_ai(image_path, context) -> str
        # 调用 Kimi Vision API
```

### 3.4 Document (document.py)

```python
class DocumentGenerator:
    def generate(transcript, images) -> str
        chapters = self.create_chapters(transcript)
        return self.render_markdown(chapters, images)
    
    def create_chapters(transcript) -> list[Chapter]
        # 使用 Kimi 分析内容，划分章节
        
    def render_markdown(chapters, images) -> str
        # 渲染为 Markdown 格式
```

## 4. 数据流

### 4.1 转录数据

```
Whisper JSON Output
    │
    ▼
TranscriptSegment[]
    ├── start_time: float
    ├── end_time: float
    └── text: str (简体中文)
```

### 4.2 关键帧数据

```
Keyframe
    ├── frame_path: Path
    ├── timestamp: float
    ├── image_type: str  # ppt, whiteboard, speaker, etc.
    └── description: str  # AI 生成描述
```

### 4.3 章节数据

```
Chapter
    ├── title: str
    ├── start_time: float
    ├── end_time: float
    ├── summary: str      # AI 生成摘要
    ├── transcript: str   # 原始转录
    └── images: list[Keyframe]  # 相关图片
```

## 5. 关键设计决策

### 5.1 Text-First 设计

- **核心原则**：文字内容是主体，图片是辅助
- **实现方式**：
  - 优先使用 Whisper 转录的完整内容
  - AI 章节划分基于文字内容
  - 图片仅用于补充文字无法表达的信息

### 5.2 智能图片筛选

**目的**：减少不必要的 API 调用，降低成本和时间

**策略**：

| 筛选层级 | 方法 | 节省率 |
|---------|------|-------|
| 第一层 | 颜色分析（检测 PPT/白板） | 30% |
| 第二层 | 文字密度检测（OpenCV） | 20% |
| 第三层 | 转录上下文分析 | 20% |

### 5.3 模型选择

| 用途 | 模型 | 理由 |
|-----|------|------|
| 语音识别 | whisper.cpp (local) | 免费、离线、保护隐私 |
| 文本生成 | kimi-k2.5 | 中文理解能力强、上下文长 |
| 图像理解 | kimi-k2.5 | 支持视觉、性价比高 |

### 5.4 错误处理策略

- **可恢复错误**：跳过当前步骤，继续处理（如单张图片分析失败）
- **关键错误**：终止处理，返回错误信息（如视频文件不存在）
- **降级策略**：如果 AI 服务不可用，仍输出基础转录和关键帧

## 6. 扩展性设计

### 6.1 添加新的 ASR 提供商

```python
# asr.py
class BaseTranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path) -> list[TranscriptSegment]:
        pass

class WhisperTranscriber(BaseTranscriber): ...
class OpenAITranscriber(BaseTranscriber): ...
class AzureTranscriber(BaseTranscriber): ...  # 新增
```

### 6.2 添加新的输出格式

```python
# document.py
class BaseRenderer(ABC):
    @abstractmethod
    def render(self, chapters) -> str:
        pass

class MarkdownRenderer(BaseRenderer): ...
class PDFRenderer(BaseRenderer): ...  # 新增
class WordRenderer(BaseRenderer): ...  # 新增
```

## 7. 配置体系

```
配置优先级（高到低）：

1. 命令行参数
   └── video2md process --keyframe-interval 60
   
2. 环境变量
   └── export KIMI_KEYFRAME_INTERVAL=60
   
3. .env 文件
   └── KIMI_KEYFRAME_INTERVAL=60
   
4. 默认值
   └── 代码中定义的默认值
```
