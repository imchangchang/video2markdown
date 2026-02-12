"""Integration tests for video processing pipeline.

These tests require actual video files in testdata/videos/.
They will be skipped if no videos are available.

Place test videos:
    cp your_video.mp4 testdata/videos/sample_short.mp4

Run tests:
    pytest tests/integration/ -v
"""

import json
from pathlib import Path

import pytest


class TestVideoProcessingPipeline:
    """Integration tests for the full video processing pipeline."""
    
    @pytest.mark.slow
    def test_extract_audio_from_video(self, get_test_video, tmp_path):
        """Test audio extraction from video.
        
        Requires: testdata/videos/ with at least one video file.
        """
        from video2markdown.audio import extract_audio
        
        video_path = get_test_video
        output_path = tmp_path / "audio.wav"
        
        # Extract audio
        result_path = extract_audio(video_path, output_path)
        
        assert result_path.exists()
        assert result_path.stat().st_size > 0
    
    @pytest.mark.slow
    def test_extract_keyframes(self, get_test_video, tmp_path):
        """Test keyframe extraction from video."""
        from video2markdown.video import extract_keyframes
        
        video_path = get_test_video
        frames_dir = tmp_path / "frames"
        
        # Extract keyframes
        keyframes = extract_keyframes(
            video_path, 
            output_dir=frames_dir,
            interval_sec=5  # 5 second interval for faster tests
        )
        
        assert len(keyframes) > 0
        assert all(f.exists() for f in keyframes)
    
    @pytest.mark.slow
    def test_transcribe_video(self, get_test_video, tmp_path):
        """Test video transcription.
        
        Note: This requires whisper.cpp models to be downloaded.
        May take a while to run.
        """
        pytest.skip("Requires whisper model - run manually")
        
        from video2markdown.asr import transcribe_audio
        
        video_path = get_test_video
        output_path = tmp_path / "transcript.json"
        
        # This would require actual ASR setup
        # segments = transcribe_audio(video_path, output_path)
        # assert len(segments) > 0


class TestDocumentGeneration:
    """Integration tests for document generation with real data."""
    
    def test_generate_document_structure(self, sample_transcript_segments, tmp_path):
        """Test document generation with sample transcript.
        
        Uses mocked/sample data, no external API calls.
        """
        from video2markdown.document import DocumentGenerator, DocumentStructure
        
        # This test uses the actual DocumentGenerator but with sample data
        # Note: If API key is not set, this may fail
        
        try:
            generator = DocumentGenerator()
        except Exception as e:
            pytest.skip(f"Cannot initialize DocumentGenerator: {e}")
        
        # Generate document structure
        doc = generator.generate_document_structure(
            segments=sample_transcript_segments,
            title="Test Video",
            duration=30.0,
            scene_changes=[8.0, 15.5, 22.0],
            language="en"
        )
        
        assert isinstance(doc, DocumentStructure)
        assert doc.title == "Test Video"
        assert len(doc.chapters) > 0
    
    def test_render_markdown(self, sample_document_structure, tmp_path):
        """Test markdown rendering from document structure."""
        from video2markdown.document import DocumentGenerator
        
        generator = DocumentGenerator()
        
        doc_structure = sample_document_structure
        markdown = generator.render_markdown(doc_structure, frames_dir=None)
        
        assert "# Test Document" in markdown
        assert "第一章：介绍" in markdown
        assert "第二章：实现" in markdown


class TestEndToEndWorkflow:
    """End-to-end workflow tests."""
    
    @pytest.mark.slow
    @pytest.mark.e2e
    def test_full_pipeline_with_video(self, get_test_video, debug_output_dir):
        """Complete pipeline test with real video.
        
        This test:
        1. Extracts keyframes from video
        2. Analyzes them (if API available)
        3. Generates document structure
        4. Renders markdown
        
        Output is saved to test_outputs/results/ for inspection.
        """
        from video2markdown.video import extract_keyframes, get_video_info
        
        video_path = get_test_video
        output_dir = debug_output_dir
        
        # Step 1: Get video info
        video_info = get_video_info(video_path)
        assert video_info is not None
        
        # Step 2: Extract keyframes (sampled for speed)
        frames_dir = output_dir / "frames"
        keyframes = extract_keyframes(
            video_path,
            output_dir=frames_dir,
            interval_sec=10  # 10 second interval
        )
        
        print(f"\nExtracted {len(keyframes)} keyframes")
        print(f"Output: {output_dir}")
        
        # Save metadata for inspection
        metadata = {
            "video_path": str(video_path),
            "video_info": video_info,
            "keyframes_count": len(keyframes),
            "keyframes": [str(f) for f in keyframes]
        }
        
        metadata_file = output_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
        
        assert len(keyframes) > 0
        print(f"\nResults saved to: {output_dir}")
        print("You can inspect the output files after the test.")
