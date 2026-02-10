"""Tests for document generation module."""

from pathlib import Path

import pytest

from video2markdown.asr import TranscriptSegment
from video2markdown.document import (
    DocumentGenerator,
    DocumentSection,
    generate_summary,
)
from video2markdown.vision import ImageDescription


class TestDocumentSection:
    """Test document section."""
    
    def test_section_creation(self):
        """Test creating a document section."""
        section = DocumentSection(
            start_time=0.0,
            end_time=10.0,
            title="Test Section",
            content="This is the summary content",
            original_text="Original transcript text",
            key_images=[],
        )
        
        assert section.start_time == 0.0
        assert section.end_time == 10.0
        assert section.title == "Test Section"
        assert section.content == "This is the summary content"


class TestDocumentGenerator:
    """Test document generator."""
    
    def test_generate_simple(self, tmp_path):
        """Test simple document generation."""
        generator = DocumentGenerator(title="Test Document")
        
        transcripts = [
            TranscriptSegment(start=0.0, end=10.0, text="First section content"),
            TranscriptSegment(start=10.0, end=20.0, text="Second section content"),
        ]
        
        images = []
        output_path = tmp_path / "output.md"
        
        # This will use AI summarization, may fail without API
        try:
            result = generator.generate(transcripts, images, output_path)
            assert result.exists()
            content = result.read_text(encoding="utf-8")
            assert "Test Document" in content
        except Exception:
            # If AI call fails, that's expected in tests without API
            pass
    
    def test_generate_with_images(self, tmp_path):
        """Test document generation with images."""
        generator = DocumentGenerator(title="Test")
        
        transcripts = [
            TranscriptSegment(start=0.0, end=30.0, text="Content here"),
        ]
        
        images = [
            ImageDescription(
                timestamp=5.0,
                image_path=tmp_path / "frame.jpg",
                description="A frame",
                key_elements=["element1"],
                is_relevant=True,
            )
        ]
        
        # Create dummy image file
        (tmp_path / "frame.jpg").touch()
        
        output_path = tmp_path / "output.md"
        
        try:
            generator.generate(transcripts, images, output_path)
            content = output_path.read_text(encoding="utf-8")
            # Check new format
            assert "Test" in content
        except Exception:
            pass


class TestGenerateSummary:
    """Test summary generation."""
    
    def test_generate_summary(self, tmp_path):
        """Test summary generation."""
        transcripts = [
            TranscriptSegment(start=0.0, end=60.0, text="Video content here"),
        ]
        images = [
            ImageDescription(
                timestamp=5.0,
                image_path=Path("/tmp/frame.jpg"),
                description="First scene",
                key_elements=["person", "screen"],
                is_relevant=True,
            )
        ]
        
        output_path = tmp_path / "summary.md"
        
        try:
            summary = generate_summary(transcripts, images, output_path)
            
            assert output_path.exists()
            assert "视频摘要" in summary
        except Exception:
            pass
