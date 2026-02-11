# Video2Markdown 处理流程详解

## 整体架构流程

```mermaid
flowchart TD
    Input[输入视频] --> S1[Stage 1: 视频分析]
    S1 --> S2[Stage 2: 音频提取与转录]
    S2 --> S3[Stage 3: 关键帧提取]
    S3 --> S4[Stage 4: 智能图片筛选]
    S4 --> S5[Stage 5: AI 图像分析]
    S5 --> S6[Stage 6: AI 文档生成]
    S6 --> S7[Stage 7: Markdown 渲染]
    S7 --> Output[输出文件]

    subgraph Stage1 [Stage 1: 视频分析]
        S1_Detail["• 读取视频元数据 (FFmpeg)  - 时长、分辨率、帧率、编码格式• 评估处理参数  - 关键帧采样间隔  - 预估处理时间"]
    end

    subgraph Stage2 [Stage 2: 音频提取与转录]
        S2A["提取音频<br>(WAV)"] --> S2B["Whisper<br>转录"] --> S2C["繁简转换<br>(OpenCC)"]
        S2A_Detail["• FFmpeg<br>• 16kHz<br>• 单声道"] -.-> S2A
        S2B_Detail["• 本地模型<br>• 时间戳<br>• 分段文本"] -.-> S2B
        S2C_Detail["• 繁体中文<br>• 转简体中文<br>• 保持一致性"] -.-> S2C
        S2_Output["输出: TranscriptSegment[]<br>- start_time: float (秒)<br>- end_time: float (秒)<br>- text: str (简体中文)"]
        S2C --> S2_Output
    end

    subgraph Stage3 [Stage 3: 关键帧提取]
        S3A["场景检测<br>(OpenCV)"] --> S3C["合并筛选<br>去重排序"]
        S3B["均匀采样<br>(按间隔)"] --> S3C
        S3A_Detail["• 帧差分析<br>• 检测转场<br>• 标记场景"] -.-> S3A
        S3B_Detail["• 固定间隔<br>• 兜底策略<br>• 确保覆盖"] -.-> S3B
        S3C_Detail["• 时间排序<br>• 质量筛选<br>• 限制数量"] -.-> S3C
    end

    subgraph Stage4 [Stage 4: 智能图片筛选]
        S4_Title["多层筛选策略 (减少 50-70% API 调用)"]
        S4A["第一层<br>颜色分析"] --> S4B["第二层<br>文字检测"] --> S4C["第三层<br>转录上下文"]
        S4A_Detail["• 检测白色背景<br>• PPT/白板判定<br>跳过率: 30%"] -.-> S4A
        S4B_Detail["• 边缘检测<br>• 文字密度<br>跳过率: 20%"] -.-> S4B
        S4C_Detail["• 检查对应时段<br>  转录内容<br>• 是否提及视觉内容<br>跳过率: 20%"] -.-> S4C
        S4_Result["判定结果:<br>✅ 分析: 检测到PPT/板书类图片<br>⏭️ 跳过: 无显著文字内容"]
        S4C --> S4_Result
    end

    subgraph Stage5 [Stage 5: AI 图像分析]
        S5_Input["输入: 筛选后的关键帧 (通常 5-15 张)"]
        S5A["图片编码<br>(Base64)"] --> S5B["Kimi API<br>调用"] --> S5C["内容描述"]
        S5A_Detail["• JPG格式<br>• 质量85%<br>• 尺寸限制"] -.-> S5A
        S5B_Detail["• 压缩优化<br>• 中文提示<br>• 重试机制"] -.-> S5B
        S5C_Detail["• 画面内容<br>• 文字提取<br>• 与上下文关联"] -.-> S5C
        S5_Time["耗时: 约 10-15 秒/张"]
        S5_Input --> S5A
    end

    subgraph Stage6 [Stage 6: AI 文档生成]
        S6_Input["输入: 转录文本 + 图片分析结果"]
        S6A[1. 内容理解] --> S6B[2. 章节划分] --> S6C[3. 摘要生成] --> S6D[4. 图片关联]
        S6A_Detail["• 分析转录文本主题<br>• 识别内容结构和逻辑"] -.-> S6A
        S6B_Detail["• 自动识别主题转换点<br>• 生成 3-6 个章节<br>• 确定每章时间范围"] -.-> S6B
        S6C_Detail["• 每章生成中文摘要<br>• 提取核心观点和关键信息"] -.-> S6C
        S6D_Detail["• 将图片匹配到对应章节<br>• 根据内容选择最相关的图片"] -.-> S6D
        S6_Time["耗时: 约 20-40 秒"]
        S6_Input --> S6A
    end

    subgraph Stage7 [Stage 7: Markdown 渲染]
        S7_Output["输出结构:<br><br>视频标题<br><br>目录<br>1. 章节1<br>2. 章节2<br>...<br><br>1. 章节标题<br>时间: [00:00:00 - 00:05:00]<br><br>AI生成的内容摘要...<br><br>相关画面:<br>时间戳图片<br>AI图片描述<br><br>原始转录文字(可折叠)<br>转录内容..."]
    end

    subgraph OutputFiles [输出文件]
        OF1["• {title}.md - 主文档"]
        OF2["• {title}_summary.md - 视频摘要"]
        OF3["• {title}.srt - 字幕文件"]
        OF4["• {title}_frames/ - 关键帧图片目录"]
    end

    S1 --> Stage1
    Stage2 --> S3
    Stage3 --> S4
    Stage4 --> S5
    Stage5 --> S6
    Stage6 --> S7
    Stage7 --> OutputFiles
```

## 详细处理时间分析

### 典型视频处理时间 (5-8 分钟)

| 阶段 | 耗时 | 占比 | 说明 |
|-----|------|-----|------|
| 视频分析 | < 1s | < 1% | FFmpeg 读取元数据 |
| 音频提取 | 2-3s | 2% | FFmpeg 提取 WAV |
| **语音转录** | **60-90s** | **35%** | Whisper 本地处理 |
| 关键帧提取 | 2-3s | 2% | OpenCV 处理 |
| **智能筛选** | **1-2s** | **< 1%** | 本地 OpenCV，无 API 调用 |
| **图片分析** | **80-120s** | **45%** | Kimi Vision API，10-15s/张 |
| **文档生成** | **30-40s** | **15%** | Kimi API |
| Markdown 渲染 | < 1s | < 1% | 本地处理 |
| **总计** | **~4-6 分钟** | **100%** | |

### 长视频处理时间 (20-30 分钟)

| 阶段 | 预估耗时 | 说明 |
|-----|---------|------|
| 语音转录 | 4-6 分钟 | 与时长成正比 |
| 图片分析 | 3-5 分钟 | 帧数增加 |
| 文档生成 | 40-60s | 文本量增加 |
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
KIMI_WHISPER_LOCAL_MODEL=whisper.cpp/models/ggml-base-q8_0.bin  # 更快但准确度略低
```

### 3. 批量处理优化

```bash
# 使用批量脚本，自动跳过已处理视频
./run_batch.sh
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
        E5[AI 文档生成失败] --> E5_Res["使用基础模板生成文档"]
    end
    
    Error --> E1
    Error --> E2
    Error --> E3
    Error --> E4
    Error --> E5
```

## 数据流转换

```mermaid
flowchart TD
    Video[视频文件] -->|FFmpeg| Audio[音频 WAV]
    Audio -->|Whisper| Transcript1[转录文本 (繁体)]
    Transcript1 -->|OpenCC| Transcript2[转录文本 (简体)]
    Transcript2 -->|转换| Segments[TranscriptSegment[]]
    
    Segments --> DocGen[文档生成]
    Transcript2 --> DocGen
    
    DocGen --> Chapter[章节划分]
    Chapter --> Summary[摘要生成]
    Summary --> Markdown[Markdown]
    Transcript2 --> Markdown
    
    Frames[关键帧图片] --> Filter[智能筛选]
    Filter --> AI[AI 分析]
    AI --> DocGen
```

## 文件输出规范

输出目录结构：

```
testbench/output/
├── {filename}.md              # 主 Markdown 文档
├── {filename}_summary.md      # 视频摘要 (要点列表)
├── {filename}.srt             # SRT 字幕文件
└── {filename}_frames/         # 关键帧目录
    ├── frame_0001_15.557.jpg
    ├── frame_0002_25.108.jpg
    └── ...
```

## 配置参数影响

| 参数 | 影响 | 默认值 | 建议 |
|-----|------|-------|------|
| `--keyframe-interval` | 图片数量 | 30s | 短视频 20s，长视频 60s |
| `--language` | 转录语言 | zh | 根据视频语音设置 |
| `KIMI_WHISPER_LOCAL_MODEL` | 转录速度/准确度 | small | tiny(快) / medium(准) |
| `KIMI_MODEL` | 文档生成质量 | kimi-k2.5 | 通常无需修改 |

---

*最后更新: 2024-02-10*
