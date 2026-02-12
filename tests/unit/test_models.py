"""Unit tests for data models.

测试 M1/M2/M3 数据模型的基本功能。
"""

import json
from pathlib import Path

import pytest

from video2markdown.models import (
    TranscriptSegment,
    VideoTranscript,  # M1
    KeyFrame,
    KeyFrames,        # M2
    ImageDescription,
    ImageDescriptions, # M3
    Chapter,
    Document,
)


class TestTranscriptSegment:
    """测试转录片段."""
    
    def test_to_srt_time(self):
        """测试 SRT 时间格式转换."""
        seg = TranscriptSegment(start=0, end=5.5, text="Hello")
        
        assert seg.to_srt_time(0) == "00:00:00,000"
        assert seg.to_srt_time(5.5) == "00:00:05,500"
        assert seg.to_srt_time(3661.123) == "01:01:01,123"
    
    def test_to_srt_entry(self):
        """测试 SRT 条目生成."""
        seg = TranscriptSegment(start=0, end=5.5, text="Hello world")
        entry = seg.to_srt_entry(1)
        
        assert "1" in entry
        assert "00:00:00,000 --> 00:00:05,500" in entry
        assert "Hello world" in entry


class TestVideoTranscript:
    """测试 M1: 视频文字稿."""
    
    def test_to_srt(self):
        """测试 SRT 格式输出."""
        transcript = VideoTranscript(
            video_path=Path("test.mp4"),
            title="Test",
            language="zh",
            segments=[
                TranscriptSegment(start=0, end=5, text="第一行"),
                TranscriptSegment(start=5, end=10, text="第二行"),
            ],
            optimized_text="",
        )
        
        srt = transcript.to_srt()
        
        assert "1" in srt
        assert "00:00:00,000 --> 00:00:05,000" in srt
        assert "第一行" in srt
        assert "第二行" in srt
    
    def test_to_word_document(self):
        """测试文字稿生成."""
        transcript = VideoTranscript(
            video_path=Path("test.mp4"),
            title="测试视频",
            language="zh",
            segments=[
                TranscriptSegment(start=0, end=5, text="这是第一句"),
                TranscriptSegment(start=5, end=10, text="这是第二句"),
            ],
            optimized_text="",
        )
        
        doc = transcript.to_word_document()
        
        assert "# 测试视频" in doc
        assert "[00:00] 这是第一句" in doc
        assert "[00:05] 这是第二句" in doc
    
    def test_get_text_around(self):
        """测试获取时间点周围文本."""
        transcript = VideoTranscript(
            video_path=Path("test.mp4"),
            title="Test",
            language="zh",
            segments=[
                TranscriptSegment(start=0, end=5, text="第一段"),
                TranscriptSegment(start=5, end=10, text="第二段"),
                TranscriptSegment(start=20, end=25, text="第三段"),
            ],
            optimized_text="",
        )
        
        # 时间点 7s 附近应该包含第二段
        text = transcript.get_text_around(7.0, window=3.0)
        assert "第二段" in text
        assert "第三段" not in text


class TestKeyFrames:
    """测试 M2: 关键帧."""
    
    def test_get_timestamps(self):
        """测试获取时间戳列表."""
        kf = KeyFrames(
            video_path=Path("test.mp4"),
            frames=[
                KeyFrame(timestamp=10.0, source="scene_change", reason="场景变化"),
                KeyFrame(timestamp=30.0, source="interval", reason="30s间隔"),
                KeyFrame(timestamp=60.0, source="transcript", reason="转录提示"),
            ]
        )
        
        timestamps = kf.get_timestamps()
        assert timestamps == [10.0, 30.0, 60.0]


class TestImageDescriptions:
    """测试 M3: 图片描述."""
    
    def test_get_by_timestamp(self):
        """测试通过时间戳查找描述."""
        descs = ImageDescriptions([
            ImageDescription(
                timestamp=10.0,
                image_path=Path("frame1.jpg"),
                description="描述1",
                key_elements=["A", "B"],
                related_transcript="相关文本1",
            ),
            ImageDescription(
                timestamp=30.0,
                image_path=Path("frame2.jpg"),
                description="描述2",
                key_elements=["C", "D"],
                related_transcript="相关文本2",
            ),
        ])
        
        found = descs.get_by_timestamp(30.0)
        assert found is not None
        assert found.description == "描述2"
        
        # 容错查找（时间差在容差范围内）
        found_approx = descs.get_by_timestamp(10.5, tolerance=1.0)
        assert found_approx is not None
        assert found_approx.timestamp == 10.0
        
        # 找不到
        not_found = descs.get_by_timestamp(100.0)
        assert not_found is None


class TestDocument:
    """测试最终文档."""
    
    def test_get_chapter_with_visual(self):
        """测试查找包含配图的章节."""
        doc = Document(
            title="测试文档",
            chapters=[
                Chapter(
                    id=1,
                    title="第一章",
                    start_time="00:00:00",
                    end_time="00:05:00",
                    summary="摘要1",
                    key_points=["要点1"],
                    cleaned_transcript="原文1",
                    visual_timestamp=30.0,
                    visual_reason="展示图表",
                ),
                Chapter(
                    id=2,
                    title="第二章",
                    start_time="00:05:00",
                    end_time="00:10:00",
                    summary="摘要2",
                    key_points=["要点2"],
                    cleaned_transcript="原文2",
                    visual_timestamp=None,
                    visual_reason=None,
                ),
            ]
        )
        
        # 查找包含 30s 配图的章节
        ch = doc.get_chapter_with_visual(30.0)
        assert ch is not None
        assert ch.title == "第一章"
        
        # 查找不存在的
        not_found = doc.get_chapter_with_visual(100.0)
        assert not_found is None
