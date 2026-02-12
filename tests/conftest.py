"""Pytest configuration and shared fixtures.

Test Data Management:
- tests/fixtures/: Small static test data (<1MB, version controlled)
- testdata/samples/: Small sample data for integration tests
- testdata/videos/: Large test videos (manual placement, not in git)
- test_outputs/: Test outputs (gitignored, safe to delete anytime)

Usage:
    # Use tmp_path for temporary files (auto-cleaned)
    def test_something(tmp_path):
        output_file = tmp_path / "output.md"
        ...

    # Use debug_output_dir for persistent debug outputs
    def test_with_debug(debug_output_dir):
        output_file = debug_output_dir / "debug_result.md"
        ...
"""

import json
import shutil
from pathlib import Path

import pytest

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent
TESTDATA_DIR = PROJECT_ROOT / "testdata"
TEST_OUTPUTS_DIR = PROJECT_ROOT / "test_outputs"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_transcript_segments():
    """Sample transcript segments for unit tests.
    
    Returns:
        List of transcript segment dicts
    """
    return [
        {"start": 0.0, "end": 5.2, "text": "大家好，今天我们来讨论视频转文档的技术方案。"},
        {"start": 5.2, "end": 12.8, "text": "首先，我们需要进行语音识别，将音频转换为文字。"},
        {"start": 12.8, "end": 20.5, "text": "然后，使用AI对文字进行理解和结构化整理。"},
        {"start": 20.5, "end": 30.0, "text": "最后，结合视频画面生成完整的Markdown文档。"},
    ]


@pytest.fixture
def sample_video_metadata():
    """Sample video metadata for testing.
    
    Returns:
        Dict with video metadata
    """
    return {
        "title": "Test Video",
        "duration": 30.0,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
    }


@pytest.fixture
def debug_output_dir(request) -> Path:
    """Provide a debug output directory for persistent test outputs.
    
    Unlike tmp_path which is auto-cleaned, files here are preserved
    for manual inspection after test runs.
    
    Directory structure:
        test_outputs/results/<test_name>/<timestamp>/
    
    Usage:
        def test_something(debug_output_dir):
            output_file = debug_output_dir / "result.md"
            # ... write to output_file
            # File will be kept for inspection
    
    Returns:
        Path to debug output directory
    """
    # Create directory based on test name
    test_name = request.node.name
    output_dir = TEST_OUTPUTS_DIR / "results" / test_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return output_dir


@pytest.fixture
def testdata_videos_dir() -> Path:
    """Get the testdata/videos directory.
    
    Returns:
        Path to testdata/videos
        
    Raises:
        pytest.skip: If directory doesn't exist or is empty
    """
    videos_dir = TESTDATA_DIR / "videos"
    
    if not videos_dir.exists():
        pytest.skip(f"Test video directory not found: {videos_dir}")
    
    # Check for video files (not just .gitkeep)
    video_files = [
        f for f in videos_dir.iterdir() 
        if f.is_file() and f.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"}
    ]
    
    if not video_files:
        pytest.skip(f"No test videos found in: {videos_dir}")
    
    return videos_dir


@pytest.fixture
def get_test_video(testdata_videos_dir) -> Path:
    """Get the first available test video.
    
    Returns:
        Path to a test video file
    """
    video_files = [
        f for f in testdata_videos_dir.iterdir() 
        if f.is_file() and f.suffix.lower() in {".mp4", ".avi", ".mov", ".mkv"}
    ]
    
    if not video_files:
        pytest.skip("No test videos available")
    
    return video_files[0]


@pytest.fixture(scope="session", autouse=True)
def clean_old_temp_outputs():
    """Clean up old temporary test outputs at session start.
    
    Keeps the last few runs for comparison, removes older ones.
    """
    temp_dir = TEST_OUTPUTS_DIR / "temp"
    
    if temp_dir.exists():
        # Remove all files in temp directory
        for item in temp_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    
    yield
    
    # Cleanup could also happen here after all tests


# ============================================================================
# Fixtures for loading static test data
# ============================================================================

def load_json_fixture(filename: str) -> dict:
    """Load a JSON fixture from tests/fixtures/.
    
    Args:
        filename: Name of the JSON file
        
    Returns:
        Parsed JSON data
        
    Raises:
        FileNotFoundError: If fixture doesn't exist
    """
    fixture_path = FIXTURES_DIR / filename
    
    if not fixture_path.exists():
        raise FileNotFoundError(f"Fixture not found: {fixture_path}")
    
    with open(fixture_path, "r", encoding="utf-8") as f:
        return json.load(f)


# Example: Create a fixture that loads specific test data
@pytest.fixture
def sample_document_structure():
    """Sample document structure for testing document generation.
    
    Returns:
        Dict representing document structure
    """
    return {
        "title": "Test Document",
        "chapters": [
            {
                "id": 1,
                "title": "第一章：介绍",
                "start_time": "00:00:00",
                "end_time": "00:05:00",
                "summary": "本章介绍了项目背景和基本思路。",
                "key_points": ["背景介绍", "技术选型", "实现方案"],
                "cleaned_transcript": "欢迎来到本项目。今天我们要讨论的是...",
                "needs_visual": True,
                "visual_timestamp": 125.5,
                "visual_reason": "展示架构图",
            },
            {
                "id": 2,
                "title": "第二章：实现",
                "start_time": "00:05:00",
                "end_time": "00:12:30",
                "summary": "详细讲解了实现过程中的关键技术点。",
                "key_points": ["语音识别", "AI处理", "文档生成"],
                "cleaned_transcript": "实现阶段我们使用了 Whisper 进行语音识别...",
                "needs_visual": False,
                "visual_timestamp": None,
                "visual_reason": None,
            },
        ]
    }
