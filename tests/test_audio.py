"""Tests for audio processing module."""

import subprocess
import tempfile
from pathlib import Path

import pytest

from video2markdown.audio import extract_audio, get_audio_duration, split_audio


class TestExtractAudio:
    """Test audio extraction."""
    
    def test_extract_audio_from_video(self):
        """Test extracting audio from video."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test.mp4"
            
            # Create test video with audio
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
                "-f", "lavfi", "-i", "color=c=black:s=320x240:d=2",
                "-shortest",
                "-pix_fmt", "yuv420p",
                str(video_path),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pytest.skip("FFmpeg not available")
            
            output_path = Path(tmpdir) / "output.wav"
            result = extract_audio(video_path, output_path)
            
            assert result.exists()
            assert result.suffix == ".wav"


class TestGetAudioDuration:
    """Test audio duration retrieval."""
    
    def test_get_duration(self):
        """Test getting audio duration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "test.wav"
            
            # Create test audio
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "sine=frequency=1000:duration=3",
                str(audio_path),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pytest.skip("FFmpeg not available")
            
            duration = get_audio_duration(audio_path)
            
            assert abs(duration - 3.0) < 0.5


class TestSplitAudio:
    """Test audio splitting."""
    
    def test_split_long_audio(self):
        """Test splitting long audio."""
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = Path(tmpdir) / "test.wav"
            
            # Create 12-second test audio
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "sine=frequency=1000:duration=12",
                str(audio_path),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pytest.skip("FFmpeg not available")
            
            segments = split_audio(audio_path, segment_duration=5, overlap=1)
            
            # Should create at least 2 segments for 12-second audio with 5-second chunks
            assert len(segments) >= 2
            
            for seg in segments:
                assert seg.exists()
