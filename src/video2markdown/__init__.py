"""Video2Markdown - 视频转结构化 Markdown 文档工具.

处理流程 (7 个阶段):
    Stage 1: 视频分析
    Stage 2: 音频提取与文字稿转化 -> M1 (视频文稿)
    Stage 3: 关键帧提取
    Stage 4: 智能图片筛选 -> M2 (关键配图)
    Stage 5: AI 图像分析 -> M3 (配图说明)
    Stage 6: AI 文档生成
    Stage 7: Markdown 渲染

中间产物:
    M1: VideoTranscript - 带时间戳的视频文字稿 (AI 优化后)
    M2: KeyFrames - 关键配图集合
    M3: ImageDescriptions - 配图的文字说明
"""

__version__ = "2.0.0"

from video2markdown.models import (
    VideoInfo,
    TranscriptSegment,
    VideoTranscript,  # M1
    KeyFrame,
    KeyFrames,        # M2
    ImageDescription,
    ImageDescriptions, # M3
    Chapter,
    Document,
)

__all__ = [
    "VideoInfo",
    "TranscriptSegment",
    "VideoTranscript",
    "KeyFrame",
    "KeyFrames",
    "ImageDescription",
    "ImageDescriptions",
    "Chapter",
    "Document",
]
