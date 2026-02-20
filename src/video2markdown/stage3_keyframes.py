"""Stage 3: 关键帧提取.

输入: 视频文件 + VideoInfo
输出: 候选关键帧时间点列表 (只在稳定区间内)

策略:
1. 从 VideoInfo 获取稳定区间
2. 在每个稳定区间内按固定间隔采样
3. 结合场景变化点（取不稳定区间中间作为补充）
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
    """提取候选关键帧时间点（只在稳定区间内）.
    
    策略:
    1. 从稳定区间提取采样点
    2. 添加场景变化点作为补充
    3. 合并并去重
    
    Args:
        video_path: 视频文件路径
        video_info: 视频信息 (包含 stable_intervals)
        interval_sec: 固定间隔 (秒)
        
    Returns:
        KeyFrames (候选帧列表，全部位于稳定区间)
    """
    print(f"[Stage 3] 提取候选关键帧: {video_path.name}")
    
    # 纯音频场景：直接返回空列表
    if video_info.video_codec == "audio_only":
        print(f"  ⏭️  纯音频文件，跳过关键帧提取")
        return KeyFrames(video_path=video_path, frames=[])
    
    frames = []
    
    # 1. 从稳定区间采样
    stable_count = 0
    for start, end in video_info.stable_intervals:
        current = start
        while current < end:
            frames.append(KeyFrame(
                timestamp=current,
                source="stable_interval",
                reason=f"稳定区间采样 @ {current:.1f}s"
            ))
            stable_count += 1
            current += interval_sec
    
    # 2. 从场景变化点添加（如果不在稳定区间内）
    scene_count = 0
    for ts in video_info.scene_changes:
        # 检查是否已经在列表中（接近）
        too_close = any(abs(f.timestamp - ts) < interval_sec / 2 for f in frames)
        if not too_close:
            # 找到最近的稳定区间，微调时间戳到区间内
            adjusted_ts = _adjust_to_stable(ts, video_info.stable_intervals)
            if adjusted_ts is not None:
                frames.append(KeyFrame(
                    timestamp=adjusted_ts,
                    source="scene_change",
                    reason=f"场景变化点 @ {ts:.1f}s → 稳定区间 {adjusted_ts:.1f}s"
                ))
                scene_count += 1
    
    # 3. 排序
    frames.sort(key=lambda f: f.timestamp)
    
    print(f"  ✓ 提取 {len(frames)} 个候选关键帧")
    print(f"    - 稳定区间采样: {stable_count}")
    print(f"    - 场景变化点: {scene_count}")
    print(f"  ✓ 覆盖 {len(video_info.stable_intervals)} 个稳定区间")
    
    return KeyFrames(video_path=video_path, frames=frames)


def _adjust_to_stable(
    timestamp: float,
    stable_intervals: list[tuple[float, float]],
    max_adjust: float = 1.0
) -> Optional[float]:
    """将时间戳调整到最近的稳定区间内.
    
    如果 timestamp 已经在稳定区间内，返回原值
    否则找到最近的稳定区间边界，向内偏移
    
    Args:
        timestamp: 原始时间戳
        stable_intervals: 稳定区间列表
        max_adjust: 最大调整距离
        
    Returns:
        调整后时间戳，或 None 如果无法调整
    """
    # 检查是否已在稳定区间内
    for start, end in stable_intervals:
        if start <= timestamp <= end:
            return timestamp
    
    # 找到最近的稳定区间
    best_ts = None
    best_dist = float('inf')
    
    for start, end in stable_intervals:
        if timestamp < start:
            dist = start - timestamp
            if dist < best_dist and dist <= max_adjust:
                best_dist = dist
                best_ts = start + 0.1  # 稍微进入区间
        elif timestamp > end:
            dist = timestamp - end
            if dist < best_dist and dist <= max_adjust:
                best_dist = dist
                best_ts = end - 0.1  # 稍微在区间内
    
    return best_ts


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
        print(f"  [{f.timestamp:7.2f}s] {f.source:15s} - {f.reason}")
