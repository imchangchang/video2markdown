"""Stage 3: 关键帧提取.

输入: 视频文件 + VideoInfo
输出: 候选关键帧时间点列表 (未筛选)

注意: 这里只提取候选帧，实际筛选在 Stage 4
"""

from pathlib import Path
from typing import Optional

import cv2

from video2markdown.models import VideoInfo, KeyFrame, KeyFrames


def extract_candidate_frames(
    video_path: Path,
    video_info: VideoInfo,
    interval_sec: float = 30.0,
) -> KeyFrames:
    """提取候选关键帧时间点.
    
    策略:
    1. 基于场景变化时间点
    2. 基于固定间隔 (补充场景变化之间的帧)
    3. 合并并去重
    
    Args:
        video_path: 视频文件路径
        video_info: 视频信息 (包含 scene_changes)
        interval_sec: 固定间隔 (秒)
        
    Returns:
        KeyFrames (候选帧列表)
    """
    print(f"[Stage 3] 提取候选关键帧: {video_path.name}")
    
    frames = []
    
    # 1. 从场景变化添加
    for ts in video_info.scene_changes:
        frames.append(KeyFrame(
            timestamp=ts,
            source="scene_change",
            reason="场景变化"
        ))
    
    # 2. 按固定间隔添加
    current = 0.0
    while current < video_info.duration:
        # 检查是否与已有帧太近
        too_close = any(abs(f.timestamp - current) < interval_sec / 2 for f in frames)
        if not too_close:
            frames.append(KeyFrame(
                timestamp=current,
                source="interval",
                reason=f"{interval_sec}s 间隔"
            ))
        current += interval_sec
    
    # 3. 排序
    frames.sort(key=lambda f: f.timestamp)
    
    print(f"  ✓ 提取 {len(frames)} 个候选关键帧")
    print(f"    - 场景变化: {len([f for f in frames if f.source == 'scene_change'])}")
    print(f"    - 固定间隔: {len([f for f in frames if f.source == 'interval'])}")
    
    return KeyFrames(video_path=video_path, frames=frames)


def extract_frame_at_timestamp(
    video_path: Path,
    timestamp: float,
    output_path: Path,
    quality: int = 95,
) -> Path:
    """从视频提取指定时间点的帧 (原始质量，无压缩).
    
    Args:
        video_path: 视频文件路径
        timestamp: 时间点 (秒)
        output_path: 输出图片路径
        quality: JPEG 质量 (默认 95%，接近无损)
        
    Returns:
        输出图片路径
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")
    
    # 定位到指定时间
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = int(timestamp * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    
    # 读取帧
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise RuntimeError(f"无法在 {timestamp}s 读取帧")
    
    # 保存 (高质量)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_path), frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    
    return output_path


# CLI 入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python -m video2markdown.stage3_keyframes <视频文件>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    # 需要先运行 Stage 1
    from video2markdown.stage1_analyze import analyze_video
    video_info = analyze_video(video_path)
    
    # 运行 Stage 3
    keyframes = extract_candidate_frames(video_path, video_info)
    
    print(f"\n候选关键帧时间点:")
    for f in keyframes.frames:
        print(f"  [{f.timestamp:7.2f}s] {f.source:12s} - {f.reason}")
