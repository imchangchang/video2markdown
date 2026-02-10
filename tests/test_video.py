"""Tests for video processing module."""

import tempfile
from pathlib import Path

import pytest

from video2markdown.video import (
    get_video_info,
    is_blurry,
    resize_for_api,
)


class TestVideoInfo:
    """Test video info extraction."""
    
    def test_get_video_info_sample(self):
        """Test getting info from a sample video."""
        # Create a minimal test video
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test.mp4"
            
            # Create a 2-second test video using ffmpeg
            import subprocess
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "testsrc=duration=2:size=640x480:rate=30",
                "-f", "lavfi", "-i", "sine=frequency=1000:duration=2",
                "-pix_fmt", "yuv420p",
                str(video_path),
            ]
            try:
                subprocess.run(cmd, check=True, capture_output=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pytest.skip("FFmpeg not available")
            
            info = get_video_info(video_path)
            
            assert info["width"] == 640
            assert info["height"] == 480
            assert info["fps"] == 30.0
            assert abs(info["duration"] - 2.0) < 0.5


class TestImageProcessing:
    """Test image processing functions."""
    
    def test_is_blurry_with_sharp_image(self):
        """Test blur detection on sharp image."""
        import numpy as np
        import cv2
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a sharp test image
            img = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            img_path = Path(tmpdir) / "sharp.jpg"
            cv2.imwrite(str(img_path), img)
            
            result = is_blurry(img_path, threshold=50.0)
            # Random noise should not be blurry
            assert bool(result) is False
    
    def test_is_blurry_with_blurry_image(self):
        """Test blur detection on blurry image."""
        import numpy as np
        import cv2
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a blurry test image (uniform color)
            img = np.full((100, 100, 3), 128, dtype=np.uint8)
            img_path = Path(tmpdir) / "blurry.jpg"
            cv2.imwrite(str(img_path), img)
            
            result = is_blurry(img_path, threshold=50.0)
            assert bool(result) is True
    
    def test_resize_for_api(self, monkeypatch):
        """Test image resizing for API."""
        import numpy as np
        import cv2
        from video2markdown import config
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Mock temp_dir to use our temp directory
            monkeypatch.setattr(config.settings, "temp_dir", Path(tmpdir))
            
            # Create a large test image
            img = np.random.randint(0, 255, (2000, 2000, 3), dtype=np.uint8)
            img_path = Path(tmpdir) / "large.jpg"
            cv2.imwrite(str(img_path), img)
            
            result_path = resize_for_api(img_path, max_size=1024)
            
            # Check resized dimensions
            assert result_path.exists()
            resized = cv2.imread(str(result_path))
            assert max(resized.shape[:2]) <= 1024
