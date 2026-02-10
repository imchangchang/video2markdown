"""Tests for ASR module."""

from pathlib import Path

import pytest

from video2markdown.asr import (
    TranscriptSegment,
    format_timestamp,
    merge_short_segments,
    save_transcript_to_srt,
)


class TestTranscriptSegment:
    """Test transcript segment dataclass."""
    
    def test_creation(self):
        """Test creating a transcript segment."""
        seg = TranscriptSegment(start=0.0, end=5.0, text="Hello world")
        
        assert seg.start == 0.0
        assert seg.end == 5.0
        assert seg.text == "Hello world"
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        seg = TranscriptSegment(start=0.0, end=5.0, text="Hello")
        d = seg.to_dict()
        
        assert d == {"start": 0.0, "end": 5.0, "text": "Hello"}


class TestFormatTimestamp:
    """Test timestamp formatting."""
    
    def test_zero(self):
        """Test formatting zero."""
        assert format_timestamp(0.0) == "00:00:00.000"
    
    def test_seconds_only(self):
        """Test formatting seconds."""
        assert format_timestamp(45.5) == "00:00:45.500"
    
    def test_minutes(self):
        """Test formatting minutes."""
        assert format_timestamp(125.0) == "00:02:05.000"
    
    def test_hours(self):
        """Test formatting hours."""
        assert format_timestamp(3661.5) == "01:01:01.500"


class TestMergeSegments:
    """Test segment merging."""
    
    def test_empty_list(self):
        """Test merging empty list."""
        result = merge_short_segments([], min_duration=5.0)
        assert result == []
    
    def test_single_segment(self):
        """Test merging single segment."""
        segs = [TranscriptSegment(start=0.0, end=3.0, text="Hello")]
        result = merge_short_segments(segs, min_duration=5.0)
        
        assert len(result) == 1
        assert result[0].text == "Hello"
    
    def test_merge_short_segments(self):
        """Test merging short consecutive segments."""
        segs = [
            TranscriptSegment(start=0.0, end=2.0, text="Hello"),
            TranscriptSegment(start=2.0, end=4.0, text="world"),
        ]
        result = merge_short_segments(segs, min_duration=5.0)
        
        assert len(result) == 1
        assert result[0].start == 0.0
        assert result[0].end == 4.0
        assert "Hello" in result[0].text
        assert "world" in result[0].text
    
    def test_keep_long_segments(self):
        """Test that long enough segments are kept separate."""
        segs = [
            TranscriptSegment(start=0.0, end=10.0, text="First long segment"),
            TranscriptSegment(start=10.0, end=20.0, text="Second long segment"),
        ]
        result = merge_short_segments(segs, min_duration=5.0, max_duration=30.0)
        
        assert len(result) == 2


class TestSaveSRT:
    """Test SRT file saving."""
    
    def test_save_srt(self, tmp_path):
        """Test saving to SRT format."""
        segs = [
            TranscriptSegment(start=0.0, end=5.0, text="First line"),
            TranscriptSegment(start=5.0, end=10.0, text="Second line"),
        ]
        output_path = tmp_path / "test.srt"
        
        save_transcript_to_srt(segs, output_path)
        
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        
        assert "1" in content
        assert "First line" in content
        assert "00:00:00.000 --> 00:00:05.000" in content
        assert "2" in content
        assert "Second line" in content
