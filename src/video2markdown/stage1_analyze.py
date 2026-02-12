"""Stage 1: 视频分析.

输入: 视频文件路径
输出: VideoInfo (包含元数据和场景变化时间点)

验证点:
    - 视频能否正常读取
    - 时长、分辨率是否正确
    - 场景变化时间点是否合理
"""

import subprocess
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from video2markdown.models import VideoInfo


def analyze_video(video_path: Path) -> VideoInfo:
    """分析视频文件，提取元数据和场景变化.
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        VideoInfo 包含视频元数据和场景变化时间点
        
    Raises:
        FileNotFoundError: 视频文件不存在
        RuntimeError: 无法读取视频
    """
    if not video_path.exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    print(f"[Stage 1] 分析视频: {video_path.name}")
    
    # 使用 ffprobe 获取视频元数据
    info = _get_video_metadata(video_path)
    
    # 检测场景变化
    print(f"  检测场景变化...")
    scene_changes = _detect_scene_changes(video_path)
    info.scene_changes = scene_changes
    
    print(f"  ✓ 时长: {info.duration:.1f}s, 分辨率: {info.width}x{info.height}")
    print(f"  ✓ 检测到 {len(scene_changes)} 个场景变化点")
    
    return info


def _get_video_metadata(video_path: Path) -> VideoInfo:
    """使用 ffprobe 获取视频元数据."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    import json
    data = json.loads(result.stdout)
    
    # 解析视频流信息
    stream = data.get("streams", [{}])[0]
    format_info = data.get("format", {})
    
    # 解析帧率 (如 "30/1" -> 30.0)
    fps_str = stream.get("r_frame_rate", "30/1")
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den)
    else:
        fps = float(fps_str)
    
    return VideoInfo(
        path=video_path,
        duration=float(format_info.get("duration", 0)),
        width=stream.get("width", 0),
        height=stream.get("height", 0),
        fps=fps,
        audio_codec="unknown",  # 可在需要时添加
        video_codec="unknown",
        scene_changes=[]
    )


def _detect_scene_changes(
    video_path: Path,
    threshold: float = 30.0,
    min_scene_duration: float = 1.0
) -> list[float]:
    """检测视频场景变化时间点.
    
    Args:
        video_path: 视频路径
        threshold: 场景变化阈值 (帧间差异阈值)
        min_scene_duration: 最小镇景时长 (秒)
        
    Returns:
        场景变化时间点列表 (秒)
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    scene_changes = []
    prev_frame = None
    prev_timestamp = 0.0
    frame_idx = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # 每秒检测一帧 (降低计算量)
        if frame_idx % int(fps) != 0:
            frame_idx += 1
            continue
        
        timestamp = frame_idx / fps
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        if prev_frame is not None:
            # 计算帧间差异
            diff = cv2.absdiff(prev_frame, gray)
            mean_diff = np.mean(diff)
            
            # 检测场景变化
            if mean_diff > threshold:
                if timestamp - prev_timestamp >= min_scene_duration:
                    scene_changes.append(timestamp)
                    prev_timestamp = timestamp
        
        prev_frame = gray
        frame_idx += 1
        
        # 每 10 秒打印进度
        if frame_idx % (int(fps) * 10) == 0:
            progress = (frame_idx / total_frames) * 100
            print(f"    场景检测进度: {progress:.1f}%", end="\r")
    
    cap.release()
    print()  # 换行
    
    return scene_changes


# CLI 入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python -m video2markdown.stage1_analyze <视频文件>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    info = analyze_video(video_path)
    
    print(f"\n分析结果:")
    print(f"  文件: {info.path}")
    print(f"  时长: {info.duration:.2f}s")
    print(f"  分辨率: {info.width}x{info.height}")
    print(f"  帧率: {info.fps:.2f}")
    print(f"  场景变化: {len(info.scene_changes)} 个")
    for ts in info.scene_changes[:10]:  # 只显示前 10 个
        print(f"    - {ts:.2f}s")
