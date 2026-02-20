"""Stage 1: 视频分析.

输入: 视频文件路径
输出: VideoInfo (包含元数据、场景变化和稳定/不稳定区间)

验证点:
    - 视频能否正常读取
    - 时长、分辨率是否正确
    - 场景变化时间点是否合理
    - 稳定/不稳定区间划分是否准确
"""

import subprocess
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np

from video2markdown.models import VideoInfo


def analyze_video(video_path: Path) -> VideoInfo:
    """分析视频文件，提取元数据和场景变化区间.
    
    Args:
        video_path: 视频文件路径
        
    Returns:
        VideoInfo 包含视频元数据、场景变化和稳定/不稳定区间
        
    Raises:
        FileNotFoundError: 视频文件不存在
        RuntimeError: 无法读取视频
    """
    if not video_path.exists():
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    
    print(f"[Stage 1] 分析视频: {video_path.name}")
    
    # 使用 ffprobe 获取视频元数据
    info, is_audio_only = _get_video_metadata(video_path)
    
    if is_audio_only:
        # 纯音频场景：跳过场景检测，整个音频作为一个稳定区间
        print(f"  检测到纯音频文件，跳过视频分析...")
        info.scene_changes = []
        info.stable_intervals = [(0, info.duration)] if info.duration > 0 else []
        info.unstable_intervals = []
        
        print(f"  ✓ 时长: {info.duration:.1f}s")
        print(f"  ✓ 纯音频模式：整个音频作为一个处理区间")
    else:
        # 检测场景变化和不稳定区间
        print(f"  检测场景变化和稳定区间...")
        scene_changes, stable_intervals, unstable_intervals = _analyze_video_stability(
            video_path, info.duration
        )
        
        info.scene_changes = scene_changes
        info.stable_intervals = stable_intervals
        info.unstable_intervals = unstable_intervals
        
        print(f"  ✓ 时长: {info.duration:.1f}s, 分辨率: {info.width}x{info.height}")
        print(f"  ✓ 检测到 {len(scene_changes)} 个场景变化点")
        print(f"  ✓ 稳定区间: {len(stable_intervals)} 段 (总 {_total_duration(stable_intervals):.1f}s)")
        print(f"  ✓ 不稳定区间: {len(unstable_intervals)} 段 (总 {_total_duration(unstable_intervals):.1f}s)")
    
    return info


def _get_video_metadata(video_path: Path) -> tuple[VideoInfo, bool]:
    """使用 ffprobe 获取视频/音频元数据."""
    # 首先获取格式信息（时长等）
    cmd_format = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path)
    ]
    
    result_format = subprocess.run(cmd_format, capture_output=True, text=True, check=True)
    import json
    data_format = json.loads(result_format.stdout)
    format_info = data_format.get("format", {})
    duration = float(format_info.get("duration", 0))
    
    # 尝试获取视频流信息
    cmd_video = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate",
        "-of", "json",
        str(video_path)
    ]
    
    result_video = subprocess.run(cmd_video, capture_output=True, text=True)
    
    # 默认值为纯音频场景
    width, height, fps = 0, 0, 0.0
    is_audio_only = True
    
    if result_video.returncode == 0:
        data_video = json.loads(result_video.stdout)
        streams = data_video.get("streams", [])
        if streams:  # 有视频流
            stream = streams[0]
            width = stream.get("width", 0)
            height = stream.get("height", 0)
            
            # 解析帧率
            fps_str = stream.get("r_frame_rate", "30/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = float(num) / float(den) if float(den) != 0 else 0.0
            else:
                fps = float(fps_str)
            
            is_audio_only = False
    
    return VideoInfo(
        path=video_path,
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        audio_codec="unknown",
        video_codec="unknown" if not is_audio_only else "audio_only",
        scene_changes=[],
        stable_intervals=[],
        unstable_intervals=[]
    ), is_audio_only


def _analyze_video_stability(
    video_path: Path,
    duration: float,
    stability_threshold: float = 8.0,
    min_stable_duration: float = 1.0
) -> Tuple[list[float], list[Tuple[float, float]], list[Tuple[float, float]]]:
    """分析视频稳定性，识别场景变化和稳定/不稳定区间.
    
    策略:
    1. 粗粒度采样，找出可能的变化点
    2. 对每个变化点用二分法精确化边界
    3. 标记稳定区间（适合截图）和不稳定区间（动画/过渡）
    
    Args:
        video_path: 视频路径
        duration: 视频时长
        stability_threshold: 稳定性阈值（帧差异低于此值为稳定）
        min_stable_duration: 最小镇定时长
        
    Returns:
        (scene_changes, stable_intervals, unstable_intervals)
    """
    from video2markdown.progress import HeartbeatMonitor
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # 第一步：粗粒度检测，找出变化点
    print(f"    第一步: 粗粒度检测...")
    rough_changes = _detect_rough_changes(cap, fps, total_frames)
    
    # 第二步：精确化每个变化点的边界
    print(f"    第二步: 精确化 {len(rough_changes)} 个变化点边界...")
    precise_intervals = []
    with HeartbeatMonitor("精确化边界", interval=5):
        for i, change_ts in enumerate(rough_changes):
            start, end = _precise_change_boundary(cap, fps, change_ts, stability_threshold)
            precise_intervals.append((start, end))
            if (i + 1) % 5 == 0 or i == len(rough_changes) - 1:
                print(f"      已处理 {i+1}/{len(rough_changes)} 个变化点")
    
    cap.release()
    
    # 第三步：构建稳定和不稳定区间
    print(f"    第三步: 构建稳定区间...")
    stable_intervals, unstable_intervals = _build_intervals(
        duration, precise_intervals, min_stable_duration
    )
    
    # 场景变化点取不稳定区间的中间位置
    scene_changes = [(start + end) / 2 for start, end in unstable_intervals]
    
    return scene_changes, stable_intervals, unstable_intervals


def _detect_rough_changes(cap: cv2.VideoCapture, fps: float, total_frames: int) -> list[float]:
    """粗粒度检测变化点（每秒采样）."""
    changes = []
    prev_frame = None
    prev_ts = 0.0
    
    for frame_idx in range(0, total_frames, int(fps)):  # 每秒一帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break
        
        timestamp = frame_idx / fps
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (320, 180))  # 缩小加速
        
        if prev_frame is not None:
            diff = _frame_diff_fast(prev_frame, gray)
            if diff > 15.0:  # 粗粒度阈值
                if timestamp - prev_ts >= 1.0:  # 至少间隔1秒
                    changes.append(timestamp)
                    prev_ts = timestamp
        
        prev_frame = gray
        
        if frame_idx % (int(fps) * 10) == 0:
            progress = (frame_idx / total_frames) * 100
            print(f"      进度: {progress:.1f}%", end="\r")
    
    print()  # 换行
    return changes


def _precise_change_boundary(
    cap: cv2.VideoCapture,
    fps: float,
    rough_ts: float,
    threshold: float,
    search_window: float = 2.0
) -> Tuple[float, float]:
    """用二分法精确化场景变化的边界.
    
    返回:
        (unstable_start, unstable_end) 不稳定区间的开始和结束时间
    """
    # 搜索范围
    search_start = max(0, rough_ts - search_window)
    search_end = rough_ts + search_window
    
    # 采样更多帧进行精确分析
    samples = []
    ts = search_start
    while ts <= search_end:
        frame = _read_frame_at(cap, ts, fps)
        if frame is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (160, 90))  # 更小尺寸快速比较
            samples.append((ts, gray))
        ts += 0.1  # 100ms 步长
    
    if len(samples) < 3:
        return (rough_ts - 0.5, rough_ts + 0.5)
    
    # 计算每帧的稳定性（与相邻帧的差异）
    stability = []
    for i, (ts, frame) in enumerate(samples):
        if i == 0 or i == len(samples) - 1:
            stability.append((ts, float('inf')))
            continue
        
        diff_prev = _frame_diff_fast(samples[i-1][1], frame)
        diff_next = _frame_diff_fast(frame, samples[i+1][1])
        avg_diff = (diff_prev + diff_next) / 2
        stability.append((ts, avg_diff))
    
    # 找到不稳定区间的起点和终点
    # 不稳定 = 差异度高于阈值
    unstable_points = [(ts, diff) for ts, diff in stability if diff > threshold]
    
    if not unstable_points:
        # 没有发现明显不稳定，返回粗略估计
        return (rough_ts - 0.3, rough_ts + 0.3)
    
    # 不稳定区间的边界
    unstable_start = min(ts for ts, _ in unstable_points)
    unstable_end = max(ts for ts, _ in unstable_points)
    
    # 扩展一点边界，确保捕获完整过渡
    unstable_start = max(search_start, unstable_start - 0.2)
    unstable_end = min(search_end, unstable_end + 0.2)
    
    return (unstable_start, unstable_end)


def _build_intervals(
    duration: float,
    unstable_intervals: list[Tuple[float, float]],
    min_stable_duration: float
) -> Tuple[list[Tuple[float, float]], list[Tuple[float, float]]]:
    """构建稳定和不稳定区间列表.
    
    合并重叠的不稳定区间，剩下的就是稳定区间。
    """
    if not unstable_intervals:
        # 整个视频都是稳定的
        return ([(0, duration)], [])
    
    # 排序并合并重叠的不稳定区间
    unstable_intervals.sort(key=lambda x: x[0])
    merged_unstable = [list(unstable_intervals[0])]
    
    for start, end in unstable_intervals[1:]:
        if start <= merged_unstable[-1][1]:  # 重叠或相邻
            merged_unstable[-1][1] = max(merged_unstable[-1][1], end)
        else:
            merged_unstable.append([start, end])
    
    # 构建稳定区间（不稳定区间之间的空隙）
    stable_intervals = []
    prev_end = 0.0
    
    for start, end in merged_unstable:
        if start > prev_end and start - prev_end >= min_stable_duration:
            stable_intervals.append((prev_end, start))
        prev_end = max(prev_end, end)
    
    # 添加最后一个稳定区间
    if prev_end < duration and duration - prev_end >= min_stable_duration:
        stable_intervals.append((prev_end, duration))
    
    return (stable_intervals, [(s, e) for s, e in merged_unstable])


def _read_frame_at(cap: cv2.VideoCapture, timestamp: float, fps: float) -> Optional[np.ndarray]:
    """在指定时间戳读取帧."""
    frame_idx = int(timestamp * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    return frame if ret else None


def _frame_diff_fast(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """快速计算两帧差异（用于粗粒度检测）."""
    diff = cv2.absdiff(frame1, frame2)
    return np.mean(diff)


def _total_duration(intervals: list[Tuple[float, float]]) -> float:
    """计算区间总时长."""
    return sum(end - start for start, end in intervals)


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
    print(f"\n  场景变化点:")
    for ts in info.scene_changes[:10]:
        print(f"    - {ts:.2f}s")
    print(f"\n  稳定区间 (适合截图):")
    for start, end in info.stable_intervals[:10]:
        print(f"    - {start:.2f}s ~ {end:.2f}s (持续 {end-start:.1f}s)")
    print(f"\n  不稳定区间 (动画/过渡):")
    for start, end in info.unstable_intervals[:10]:
        print(f"    - {start:.2f}s ~ {end:.2f}s (持续 {end-start:.1f}s)")
