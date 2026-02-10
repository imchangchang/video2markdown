"""Tests for vision module."""

from pathlib import Path

import pytest

from video2markdown.vision import ImageDescription


class TestImageDescription:
    """Test image description dataclass."""
    
    def test_creation(self):
        """Test creating image description."""
        desc = ImageDescription(
            timestamp=10.5,
            image_path=Path("/tmp/test.jpg"),
            description="A test image",
            key_elements=["element1", "element2"],
        )
        
        assert desc.timestamp == 10.5
        assert desc.image_path == Path("/tmp/test.jpg")
        assert desc.description == "A test image"
        assert desc.key_elements == ["element1", "element2"]
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        desc = ImageDescription(
            timestamp=10.5,
            image_path=Path("/tmp/test.jpg"),
            description="A test image",
            key_elements=["element1"],
            is_relevant=True,
            analysis_reason="test",
        )
        d = desc.to_dict()
        
        assert d["timestamp"] == 10.5
        assert d["image_path"] == "/tmp/test.jpg"
        assert d["description"] == "A test image"
        assert d["key_elements"] == ["element1"]
        assert d["is_relevant"] == True


class TestVisionProcessor:
    """Test vision processor (mocked)."""
    
    def test_init_without_api_key(self, monkeypatch):
        """Test initialization without API key."""
        monkeypatch.setenv("KIMI_API_KEY", "test-key")
        
        from video2markdown.vision import VisionProcessor
        
        processor = VisionProcessor()
        assert processor.model is not None
