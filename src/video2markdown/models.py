"""数据模型定义 - 中间产物和阶段数据.

中间产物:
    M1: VideoTranscript - 视频文稿 (Stage 2 输出)
    M2: KeyFrames - 关键配图 (Stage 4 输出)
    M3: ImageDescriptions - 配图说明 (Stage 5 输出)
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from datetime import datetime


@dataclass
class VideoInfo:
    """Stage 1: 视频分析输出."""
    path: Path
    duration: float          # 秒
    width: int
    height: int
    fps: float
    audio_codec: str
    video_codec: str
    scene_changes: list[float] = field(default_factory=list)  # 场景变化时间点


@dataclass
class TranscriptSegment:
    """转录文本片段."""
    start: float             # 开始时间 (秒)
    end: float               # 结束时间 (秒)
    text: str                # 文本内容
    
    def to_srt_time(self, seconds: float) -> str:
        """转换为 SRT 时间格式 HH:MM:SS,mmm."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def to_srt_entry(self, index: int) -> str:
        """生成 SRT 条目."""
        return f"{index}\n{self.to_srt_time(self.start)} --> {self.to_srt_time(self.end)}\n{self.text}\n"


@dataclass  
class VideoTranscript:
    """M1: 视频文稿 (Stage 2 输出).
    
    包含:
    - 原始转录文本 (带时间戳)
    - AI 优化后的文字稿 (更适合阅读的形式)
    """
    video_path: Path
    title: str
    language: str          # 语言代码
    segments: list[TranscriptSegment]  # 原始转录片段
    optimized_text: str     # AI 优化后的文字稿 (可选)
    
    def to_srt(self) -> str:
        """生成 SRT 格式字幕."""
        return "\n".join(
            seg.to_srt_entry(i + 1) 
            for i, seg in enumerate(self.segments)
        )
    
    def to_word_document(self) -> str:
        """生成纯文字稿 (无配图，仅带时间戳和文字)."""
        lines = [f"# {self.title}", "", f"视频文稿 | 语言: {self.language}", ""]
        
        for seg in self.segments:
            time_str = f"[{int(seg.start//60):02d}:{int(seg.start%60):02d}]"
            lines.append(f"{time_str} {seg.text}")
        
        return "\n".join(lines)
    
    def get_text_around(self, timestamp: float, window: float = 10.0) -> str:
        """获取指定时间点前后的文本."""
        relevant = []
        for seg in self.segments:
            if seg.start <= timestamp + window and seg.end >= timestamp - window:
                relevant.append(seg.text)
        return " ".join(relevant)


@dataclass
class KeyFrame:
    """关键帧信息."""
    timestamp: float         # 时间点 (秒)
    source: str              # 来源: "scene_change" | "transcript_hint" | "interval"
    reason: str              # 选择原因


@dataclass
class KeyFrames:
    """M2: 关键配图 (Stage 4 输出).
    
    经过智能筛选后的关键时间点列表.
    实际图片在 Stage 5 按需提取.
    """
    video_path: Path
    frames: list[KeyFrame]   # 筛选后的关键帧列表
    
    def get_timestamps(self) -> list[float]:
        """获取所有时间点."""
        return [f.timestamp for f in self.frames]


@dataclass
class ImageDescription:
    """单张图片的分析结果."""
    timestamp: float         # 图片时间点
    image_path: Path         # 图片文件路径 (原始视频截图，无压缩)
    description: str         # AI 描述
    key_elements: list[str]  # 关键元素
    related_transcript: str  # 相关的文字稿内容


@dataclass
class ImageDescriptions:
    """M3: 配图说明 (Stage 5 输出)."""
    descriptions: list[ImageDescription]
    
    def get_by_timestamp(self, timestamp: float, tolerance: float = 1.0) -> Optional[ImageDescription]:
        """根据时间戳查找描述."""
        for desc in self.descriptions:
            if abs(desc.timestamp - timestamp) <= tolerance:
                return desc
        return None


@dataclass
class Chapter:
    """文档章节."""
    id: int
    title: str
    start_time: float        # 开始时间 (秒)
    end_time: float          # 结束时间 (秒)
    summary: str             # 摘要
    key_points: list[str]    # 关键要点
    cleaned_transcript: str  # 清洗后的原文
    
    # 配图关联
    visual_timestamp: Optional[float] = None  # 关联的图片时间点
    visual_reason: Optional[str] = None       # 配图原因


@dataclass
class Document:
    """最终文档结构."""
    title: str
    chapters: list[Chapter]
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_chapter_with_visual(self, timestamp: float, tolerance: float = 1.0) -> Optional[Chapter]:
        """查找包含指定时间点配图的章节."""
        for ch in self.chapters:
            if ch.visual_timestamp and abs(ch.visual_timestamp - timestamp) <= tolerance:
                return ch
        return None
