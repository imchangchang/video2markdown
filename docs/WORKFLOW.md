# Video2Markdown 处理流程详解

## 整体架构流程

```mermaid
flowchart TD
    Input[输入视频]
    %% 关键阶段
    S1[Stage 1: 视频分析]
    S2A[Stage 2a: 音频提取]
    S2B[Stage 2b: 语音转录]
    S2C[Stage 2c: AI文稿优化]
    S3[Stage 3: 关键帧提取]
    S4[Stage 4: 智能图片筛选]
    S5[Stage 5: AI 图像分析]
    S6[Stage 6: 图文融合生成]
    
    %% 中间成果
    M1[视频文稿 M1</br>AI优化后的结构化文稿</br>可直接阅读替代视频]
    M2[关键配图 M2</br>筛选后的关键帧图片]
    M3[配图说明 M3</br>AI对每张图片的文字描述]
    RawTranscript[原始转录</br>SRT字幕文件</br>保留做参考]

    Input --> S1
    S1 --> S2A
    S2A --> S2B
    S2B --> RawTranscript
    S2B --> S2C
    S2C --> |生成可直接阅读的文稿|M1
    
    M1 --> |从文稿提取关键时间点|S3
    S1 --> |从视频提取场景变化|S3
    S3 --> S4
    S4 --> |保留有价值的配图|M2
    M2 --> S5
    S5 --> |生成每张图的说明|M3

    M1 --> S6
    M2 --> S6
    M3 --> S6

    S6 --> S7[Stage 7: Markdown 渲染]
    S7 --> Output[输出文件]

    subgraph Stage2Detail [Stage 2: 音频提取与文稿生成]
        S2A_D["提取WAV音频"] --> S2B_D["Whisper语音转录"]
        S2B_D --> S2C_D["AI优化：去口语化、分段、加标题"]
        S2C_D --> M1
        S2B_D -.-> RawTranscript
    end

    subgraph Stage4 [Stage 4: 智能图片筛选]
        S4_Title["多层筛选策略"]

        S4A_Detail["第一层<br>时间戳去重"] 
            --> S4B["第二层<br>文字检测"] --> S4C["第三层<br>转录上下文"]
        S4B_Detail["• 边缘检测<br>• 文字密度] -.-> S4B
        S4C_Detail["• 检查M1文稿<br>• 是否提及视觉内容] -.-> S4C

        S4_Result["判定结果:<br> 保留: PPT/板书/图表/重要演示<br> 跳过: 过渡画面/风景/纯人物"]
        S4C --> S4_Result
    end

    subgraph Stage5 [Stage 5: AI 图像分析]
        S5_Input["输入: M2关键配图"]
        S5A["提取原始帧</br>无压缩"] --> S5B["Kimi Vision分析"] --> S5C["生成描述"]
        S5A_Detail["• 从视频原图提取<br>• 高质量JPG] -.-> S5A
        S5B_Detail["• 结合M1文稿上下文<br>• 理解图片与内容关系] -.-> S5B
        S5C_Detail["• 画面内容描述<br>• 关键元素提取<br>• 与文稿关联] -.-> S5C
        S5_Time["耗时: 10~15]
        S5_Input --> S5A
    end

    subgraph Stage6 [Stage 6: 图文融合生成]
        S6_Input["输入: M1 + M2 + M3"]
        S6A["分析M1文稿结构"] --> S6B["在合适位置插入配图"]
        S6C["为每章匹配M2/M3"] --> S6D["生成最终结构"]
        S6_Input --> S6A
        S6A --> S6B
        S6B --> S6C
        S6C --> S6D
    end

    subgraph OutputFiles [输出文件]
        OF1["• {title}/{title}.md - 最终图文文档"]
        OF2["• {title}/{title}_word.md - AI优化文稿M1</br>(可直接阅读替代视频)"]
        OF3["• {title}/{title}.srt - 原始转录字幕</br>(参考用)"]
        OF4["• {title}/images/ - 关键配图M2 + 说明M3"]
    end

```

## 核心概念：M1/M2/M3 中间产物

### M1: 视频文稿（AI优化后）

**定义**: 经过 AI 优化的结构化文稿，可直接阅读替代视频

**特点**:
- ❌ 不是口语化转录
- ✅ 是经过 AI 优化的正式文稿
- ✅ 有段落结构、小标题
- ✅ 去除重复、语气词、口头禅
- ✅ 专业术语准确

**生成流程**:
```
原始音频 → Whisper转录(口语化) → AI优化 → M1(可读文稿)
```

**输出文件**:
- `{title}_word.md` - AI优化后的文稿
- 可以直接阅读，无需看视频

### M2: 关键配图

**定义**: 经过智能筛选后需要保留的关键帧图片

**筛选标准**:
1. 时间戳去重（避免连续重复帧）
2. 文字检测（保留有 PPT/板书/代码的画面）
3. 上下文检查（M1文稿提及的视觉内容）

**输出**:
- `{title}_frames/frame_*.jpg` - 原始质量截图

### M3: 配图说明

**定义**: AI 对每张 M2 图片的文字描述

**内容**:
- 画面主要内容
- 提取的文字（如有）
- 与 M1 文稿的关联

**输出**:
- `{title}_frames/frame_*.txt` - 每张图的说明

## 详细处理时间分析

### 典型视频处理时间 (5-8 分钟)

| 阶段 | 耗时 | 占比 | 说明 |
|-----|------|-----|------|
| Stage 1: 视频分析 | < 1s | < 1% | FFmpeg 读取元数据 |
| Stage 2a: 音频提取 | 2-3s | 2% | FFmpeg 提取 WAV |
| Stage 2b: 语音转录 | 60-90s | 25% | Whisper 本地处理 |
| Stage 2c: AI文稿优化 | 20-30s | 10% | Kimi API，优化为可读文稿 |
| Stage 3: 关键帧提取 | 2-3s | 2% | OpenCV 处理 |
| Stage 4: 智能筛选 | 1-2s | < 1% | 本地 OpenCV，无 API 调用 |
| Stage 5: 图片分析 | 80-120s | 40% | Kimi Vision API，10-15s/张 |
| Stage 6: 图文融合 | 20-30s | 10% | Kimi API，整合 M1+M2+M3 |
| Stage 7: Markdown渲染 | < 1s | < 1% | 本地处理 |
| **总计** | **~4-6 分钟** | **100%** | |

### 长视频处理时间 (20-30 分钟)

| 阶段 | 预估耗时 | 说明 |
|-----|---------|------|
| 语音转录 | 4-6 分钟 | 与时长成正比 |
| AI文稿优化 | 30-60s | 文稿量增加 |
| 图片分析 | 3-5 分钟 | 帧数增加 |
| 图文融合 | 30-60s | 复杂度增加 |
| **总计** | **~15-20 分钟** | |

## 性能优化建议

### 1. 减少 API 调用时间

```bash
# 增大关键帧间隔，减少图片数量
video2md process video.mp4 --keyframe-interval 60  # 默认 30
```

### 2. 使用更快的 Whisper 模型

```bash
# .env 配置
KIMI_WHISPER_MODEL=base  # 更快但准确度略低
```

### 3. 跳过图片分析（仅生成文稿）

```bash
# 如果只需要 M1 文稿，不需要配图
video2md stage2 video.mp4  # 只生成 M1
```

## 错误处理流程

```mermaid
flowchart TD
    Error[处理过程中错误]
    
    subgraph Errors [错误类型与处理]
        E1[视频读取失败] --> E1_Res["提示: 无法读取视频文件，请检查格式"]
        E2[音频提取失败] --> E2_Res["提示: 音频提取失败，尝试备用方法"]
        E3[ASR 转录失败] --> E3_Res["回退到占位符: [音频转录失败...]"]
        E4[单张图片分析失败] --> E4_Res["跳过该图片，继续处理其他"]
        E5[AI 文稿优化失败] --> E5_Res["使用原始转录作为 M1"]
        E6[AI 文档生成失败] --> E6_Res["使用基础模板生成文档"]
    end
    
    Error --> E1
    Error --> E2
    Error --> E3
    Error --> E4
    Error --> E5
    Error --> E6
```

## 数据流转换

```mermaid
flowchart TD
    Video[视频文件] -->|FFmpeg| Audio[音频 WAV]
    Audio -->|Whisper| Transcript1[原始转录 口语化]
    Transcript1 -->|OpenCC| Transcript2[简体转录]
    Transcript2 -->|AI优化| M1[视频文稿 M1<br>结构化可读]
    
    M1 --> DocGen[文档生成]
    
    Video -->|场景检测| Scenes[场景变化点]
    Video -->|固定间隔| Intervals[固定间隔点]
    Scenes --> KeyFrames[候选关键帧]
    Intervals --> KeyFrames
    KeyFrames --> Filter[智能筛选]
    M1 --> Filter
    Filter --> M2[关键配图 M2]
    
    M2 --> AI[AI图像分析]
    M1 --> AI
    AI --> M3[配图说明 M3]
    
    M1 --> Merge[图文融合]
    M2 --> Merge
    M3 --> Merge
    Merge --> Final[最终文档]
```

## 文件输出规范

输出目录结构：

```
test_outputs/results/
└── {filename}/                          # 以视频标题命名的文件夹
    ├── {filename}.md                    # 最终图文文档
    ├── {filename}_word.md               # M1: AI优化文稿（核心产物）
    ├── {filename}.srt                   # 原始转录字幕（参考）
    └── {filename}_frames/               # M2 + M3
        ├── frame_0001_15.5s.jpg         # 关键配图
        ├── frame_0001_15.5s.txt         # M3: 配图说明
        ├── frame_0002_45.2s.jpg
        └── ...
```

### 各文件用途

| 文件 | 用途 | 是否必须 |
|-----|------|---------|
| `{filename}_word.md` | **M1: AI优化文稿**，可直接阅读替代视频 | ✅ 核心产物 |
| `{filename}.md` | 最终图文文档，包含配图 | ✅ 完整产物 |
| `{filename}.srt` | 原始转录字幕，用于核对 | 参考 |
| `{filename}_frames/` | M2 配图 + M3 说明 | 有配图时 |

## 配置参数影响

| 参数 | 影响 | 默认值 | 建议 |
|-----|------|-------|------|
| `--keyframe-interval` | 图片数量 | 30s | 短视频 20s，长视频 60s |
| `--language` | 转录语言 | zh | 根据视频语音设置 |
| `KIMI_WHISPER_MODEL` | 转录速度/准确度 | medium | tiny(快) / medium(准) |
| `KIMI_MODEL` | AI优化质量 | kimi-k2.5 | 通常无需修改 |

---

*最后更新: 2024-02-12 - 更新 M1 定义为 AI 优化后的可读文稿*
