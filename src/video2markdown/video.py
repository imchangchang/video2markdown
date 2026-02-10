"""Video processing and keyframe extraction module."""

import json
import subprocess
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from tqdm import tqdm

from video2markdown.config import settings


def get_video_info(video_path: Path) -> dict:
    """Get video metadata using ffprobe.
    
    Args:
        video_path: Path to video file
        
    Returns:
        Dictionary with video info (fps, duration, width, height)
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path),
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    
    stream = data.get("streams", [{}])[0]
    format_info = data.get("format", {})
    
    # Parse frame rate fraction
    fps_str = stream.get("r_frame_rate", "30/1")
    num, den = map(int, fps_str.split("/"))
    fps = num / den if den != 0 else 30.0
    
    duration = float(stream.get("duration") or format_info.get("duration", 0))
    
    return {
        "fps": fps,
        "duration": duration,
        "width": stream.get("width", 0),
        "height": stream.get("height", 0),
        "total_frames": int(fps * duration) if duration > 0 else 0,
    }


def detect_scene_changes(
    video_path: Path,
    threshold: Optional[float] = None,
) -> list[float]:
    """Detect scene change timestamps using FFmpeg scene filter.
    
    Args:
        video_path: Path to video file
        threshold: Scene change threshold (0.0-1.0)
        
    Returns:
        List of timestamps where scenes change
    """
    if threshold is None:
        threshold = settings.scene_threshold
    
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", f"select='gte(scene,{threshold})',showinfo",
        "-f", "null",
        "-",
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    timestamps = []
    for line in result.stderr.split("\n"):
        if "pts_time:" in line:
            try:
                # Extract pts_time value
                parts = line.split("pts_time:")
                if len(parts) > 1:
                    time_str = parts[1].split()[0]
                    timestamps.append(float(time_str))
            except (ValueError, IndexError):
                continue
    
    return timestamps


def extract_frame(video_path: Path, timestamp: float, output_path: Path) -> Path:
    """Extract a single frame at given timestamp.
    
    Args:
        video_path: Path to video file
        timestamp: Time in seconds
        output_path: Output image path
        
    Returns:
        Path to extracted frame
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", str(settings.frame_quality),
        str(output_path),
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    return output_path


def is_black_frame(image_path: Path, threshold: float = 0.95) -> bool:
    """Check if image is mostly black (transition/scene change).
    
    Args:
        image_path: Path to image
        threshold: Ratio of dark pixels to consider as black frame
        
    Returns:
        True if image is mostly black
    """
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return True
    
    # Calculate mean brightness
    mean_brightness = np.mean(img)
    
    # If mean brightness is very low, it's likely a black frame
    if mean_brightness < 10:
        return True
    
    # Count very dark pixels (0-20)
    dark_pixels = np.sum(img < 20)
    total_pixels = img.size
    dark_ratio = dark_pixels / total_pixels
    
    return dark_ratio > threshold


def score_frame_quality(image_path: Path) -> float:
    """Score frame quality (higher is better).
    
    Combines:
    - Sharpness (Laplacian variance)
    - Brightness (avoid too dark or too bright)
    - Content (avoid uniform colors)
    
    Args:
        image_path: Path to image
        
    Returns:
        Quality score (0-100)
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return 0.0
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Sharpness
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    sharpness_score = min(laplacian_var / 500, 50)  # Max 50 points
    
    # Brightness (ideal: 50-200)
    mean_brightness = np.mean(gray)
    if mean_brightness < 30 or mean_brightness > 225:
        brightness_score = 0
    else:
        brightness_score = 25
    
    # Content variety (standard deviation)
    std_dev = np.std(gray)
    content_score = min(std_dev / 2, 25)  # Max 25 points
    
    return sharpness_score + brightness_score + content_score


def extract_best_frame(
    video_path: Path,
    target_timestamp: float,
    output_path: Path,
    search_window: float = 2.0,
    step: float = 0.5,
) -> tuple[Path, float]:
    """Extract best frame around target timestamp.
    
    Searches in a window around the target timestamp to find
    the clearest, non-black frame.
    
    Args:
        video_path: Path to video file
        target_timestamp: Target time in seconds
        output_path: Output image path
        search_window: Time window to search (seconds on each side)
        step: Time step between candidate frames
        
    Returns:
        Tuple of (output_path, actual_timestamp)
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Generate candidate timestamps
    candidates = []
    current = max(0, target_timestamp - search_window)
    end = target_timestamp + search_window
    
    while current <= end:
        candidates.append(current)
        current += step
    
    # Evaluate each candidate
    best_frame = None
    best_score = -1
    best_timestamp = target_timestamp
    
    temp_dir = settings.temp_dir / "frame_selection"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    for i, ts in enumerate(candidates):
        temp_path = temp_dir / f"candidate_{i}_{ts:.2f}.jpg"
        
        try:
            extract_frame(video_path, ts, temp_path)
            
            # Skip black frames
            if is_black_frame(temp_path):
                continue
            
            # Score quality
            score = score_frame_quality(temp_path)
            
            if score > best_score:
                best_score = score
                best_frame = temp_path
                best_timestamp = ts
                
        except Exception:
            continue
    
    # Copy best frame to output
    if best_frame and best_frame.exists():
        import shutil
        shutil.copy(best_frame, output_path)
        # Cleanup temp files
        for f in temp_dir.glob("candidate_*.jpg"):
            f.unlink(missing_ok=True)
        return output_path, best_timestamp
    else:
        # Fallback: extract at exact timestamp
        extract_frame(video_path, target_timestamp, output_path)
        return output_path, target_timestamp


def is_blurry(image_path: Path, threshold: Optional[float] = None) -> bool:
    """Check if image is blurry using Laplacian variance.
    
    Args:
        image_path: Path to image
        threshold: Blur threshold (lower values are blurrier)
        
    Returns:
        True if image is blurry
    """
    if threshold is None:
        threshold = settings.blur_threshold
    
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return True
    
    laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
    return laplacian_var < threshold


def resize_for_api(image_path: Path, max_size: Optional[int] = None) -> Path:
    """Resize image for API upload while maintaining aspect ratio.
    
    Args:
        image_path: Original image path
        max_size: Maximum dimension size
        
    Returns:
        Path to resized image (may be same as input)
    """
    if max_size is None:
        max_size = settings.max_image_size
    
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Cannot read image: {image_path}")
    
    height, width = img.shape[:2]
    
    # Check if resizing is needed
    if max(height, width) <= max_size:
        return image_path
    
    # Calculate new dimensions
    if height > width:
        new_height = max_size
        new_width = int(width * max_size / height)
    else:
        new_width = max_size
        new_height = int(height * max_size / width)
    
    resized = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    # Save to temp location
    output_path = settings.temp_dir / f"{image_path.stem}_resized.jpg"
    cv2.imwrite(str(output_path), resized, [cv2.IMWRITE_JPEG_QUALITY, 90])
    
    return output_path


def extract_keyframes(
    video_path: Path,
    timestamps: list[float],
    output_dir: Path,
    filter_blurry: bool = True,
) -> list[dict]:
    """Extract keyframes at given timestamps.
    
    Args:
        video_path: Path to video file
        timestamps: List of timestamps to extract
        output_dir: Directory for output images
        filter_blurry: Whether to filter out blurry frames
        
    Returns:
        List of dicts with frame info (timestamp, path, is_blurry)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    keyframes = []
    
    for i, ts in enumerate(tqdm(timestamps, desc="Extracting keyframes")):
        output_path = output_dir / f"frame_{i:04d}_{ts:.3f}.jpg"
        
        try:
            extract_frame(video_path, ts, output_path)
            
            blurry = False
            if filter_blurry:
                blurry = is_blurry(output_path)
            
            keyframes.append({
                "timestamp": ts,
                "path": output_path,
                "is_blurry": blurry,
                "index": i,
            })
        except subprocess.CalledProcessError as e:
            print(f"Warning: Failed to extract frame at {ts}: {e}")
            continue
    
    return keyframes


def sample_uniform_frames(
    video_path: Path,
    interval_seconds: float = 5.0,
    output_dir: Optional[Path] = None,
) -> list[dict]:
    """Sample frames at uniform intervals.
    
    Args:
        video_path: Path to video file
        interval_seconds: Interval between frames
        output_dir: Directory for output images
        
    Returns:
        List of frame info dicts
    """
    info = get_video_info(video_path)
    duration = info["duration"]
    
    timestamps = []
    current = 0.0
    while current < duration:
        timestamps.append(current)
        current += interval_seconds
    
    if output_dir is None:
        output_dir = settings.temp_dir / f"{video_path.stem}_frames"
    
    return extract_keyframes(video_path, timestamps, output_dir)
