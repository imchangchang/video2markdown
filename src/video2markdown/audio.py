"""Audio extraction and processing module."""

import subprocess
from pathlib import Path
from typing import Optional

from video2markdown.config import settings


def extract_audio(
    video_path: Path,
    output_path: Optional[Path] = None,
    sample_rate: int = 16000,
) -> Path:
    """Extract audio from video file.
    
    Args:
        video_path: Path to input video
        output_path: Path for output audio (optional)
        sample_rate: Target sample rate for ASR
        
    Returns:
        Path to extracted audio file
    """
    if output_path is None:
        output_path = settings.temp_dir / f"{video_path.stem}.wav"
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg",
        "-y",  # Overwrite output
        "-i", str(video_path),
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # PCM 16-bit little endian
        "-ac", "1",  # Mono
        "-ar", str(sample_rate),  # Target sample rate
        str(output_path),
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration using ffprobe.
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Duration in seconds
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path),
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def split_audio(
    audio_path: Path,
    segment_duration: int = 600,
    overlap: int = 5,
) -> list[Path]:
    """Split audio into segments for processing.
    
    Args:
        audio_path: Path to audio file
        segment_duration: Duration of each segment in seconds
        overlap: Overlap between segments in seconds
        
    Returns:
        List of segment file paths
    """
    duration = get_audio_duration(audio_path)
    segments = []
    
    start = 0
    segment_idx = 0
    
    while start < duration:
        end = min(start + segment_duration, duration)
        
        segment_path = settings.temp_dir / f"{audio_path.stem}_seg{segment_idx:04d}.wav"
        
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(audio_path),
            "-ss", str(start),
            "-t", str(end - start),
            "-c", "copy",
            str(segment_path),
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        segments.append(segment_path)
        
        start += segment_duration - overlap
        segment_idx += 1
    
    return segments
