"""Stage 4: 智能图片筛选.

输入: 视频文件 + 候选关键帧 + VideoTranscript (M1)
输出: KeyFrames (M2) - 筛选后的关键帧

筛选策略 (三层):
    1. 时间戳分析去重
    2. 文字检测 (OpenCV)
    3. 转录上下文检查
    
注意: 动画稳定检测已在 Stage 1 完成，Stage 3 只从稳定区间采样
"""

from pathlib import Path

import cv2
import numpy as np

from video2markdown.models import KeyFrame, KeyFrames, VideoTranscript


def filter_keyframes(
    video_path: Path,
    candidates: KeyFrames,
    transcript: VideoTranscript,
    min_interval: float = 10.0,
) -> KeyFrames:
    """智能筛选关键帧.
    
    三层筛选:
    1. 时间戳去重 (合并过近的帧)
    2. 文字检测 (OpenCV 边缘检测)
    3. 转录上下文检查 (检查对应时段是否提及视觉内容)
    
    Args:
        video_path: 视频文件路径
        candidates: 候选关键帧（已确保在稳定区间）
        transcript: 视频文字稿 (M1)
        min_interval: 最小镇间隔 (秒)
        
    Returns:
        KeyFrames (M2) - 筛选后的关键帧
    """
    print(f"[Stage 4] 智能图片筛选: {len(candidates.frames)} 个候选帧")
    
    filtered = []
    
    for i, frame in enumerate(candidates.frames):
        print(f"  检查帧 {i+1}/{len(candidates.frames)} @ {frame.timestamp:.1f}s...", end=" ")
        
        # 第一层: 时间戳去重
        if _is_too_close(frame.timestamp, filtered, min_interval):
            print("SKIP (距离太近)")
            continue
        
        # 第二层: 文字检测
        has_text, text_ratio = _detect_text_content(video_path, frame.timestamp)
        if not has_text and text_ratio < 0.02:
            print(f"SKIP (无显著文字, 密度={text_ratio:.3f})")
            continue
        
        # 第三层: 转录上下文检查
        needs_visual, reason = _check_transcript_context(
            frame.timestamp, transcript
        )
        if not needs_visual:
            print(f"SKIP (文字稿已足够清晰: {reason})")
            continue
        
        # 通过筛选
        frame.reason = f"{frame.reason} | {reason} | 文字密度={text_ratio:.2f}"
        filtered.append(frame)
        print(f"KEEP ({reason})")
    
    print(f"  ✓ 筛选完成: {len(filtered)}/{len(candidates.frames)} 个帧通过")
    
    return KeyFrames(video_path=video_path, frames=filtered)


def _is_too_close(timestamp: float, selected_frames: list[KeyFrame], min_interval: float) -> bool:
    """检查是否与已选帧太近."""
    for f in selected_frames:
        if abs(f.timestamp - timestamp) < min_interval:
            return True
    return False


def _detect_text_content(video_path: Path, timestamp: float) -> tuple[bool, float]:
    """检测指定时间点的帧是否包含文字.
    
    Returns:
        (has_text, text_ratio)
    """
    # 提取单帧 (低质量，仅用于分析)
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = int(timestamp * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        return False, 0.0
    
    # 边缘检测识别文字区域
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    # 计算文字区域比例
    text_pixels = np.sum(edges > 0)
    total_pixels = edges.shape[0] * edges.shape[1]
    text_ratio = text_pixels / total_pixels
    
    # 判断是否有意义的内容 (5%-50% 是合理的范围)
    has_text = 0.05 < text_ratio < 0.50
    
    return has_text, text_ratio


def _check_transcript_context(
    timestamp: float,
    transcript: VideoTranscript,
    window: float = 8.0
) -> tuple[bool, str]:
    """检查转录文本是否表明需要配图.
    
    Returns:
        (needs_visual, reason)
    """
    # 获取时间窗口内的文本
    text = transcript.get_text_around(timestamp, window)
    
    if not text or len(text.strip()) < 10:
        return True, "文字稿过短，需要图片补充"
    
    # 检查视觉指示词
    visual_indicators = [
        "如图", "如图所示", "看这个", "展示", "屏幕", "页面",
        "这边", "这里", "这个", "界面", "图表", "数据",
        "PPT", "板书", "代码", "演示"
    ]
    
    has_visual_ref = any(word in text for word in visual_indicators)
    
    if has_visual_ref:
        return True, "检测到视觉引用"
    
    # 检查抽象概念
    abstract_concepts = [
        "架构", "流程", "结构", "框架", "模型", "系统",
        "原理", "机制", "算法", "设计", "方案"
    ]
    
    has_abstract = any(concept in text for concept in abstract_concepts)
    
    if has_abstract:
        return True, "包含抽象概念，图片有助于理解"
    
    # 如果文字已经很详细，可能不需要图片
    if len(text) > 200:
        return False, "文字稿已详细"
    
    return True, "默认需要配图辅助"


# CLI 入口
if __name__ == "__main__":
    import sys
    from video2markdown.stage1_analyze import analyze_video
    from video2markdown.stage2_transcribe import transcribe_video
    from video2markdown.stage3_keyframes import extract_candidate_frames
    
    if len(sys.argv) < 3:
        print("用法: python -m video2markdown.stage4_filter <视频文件> <模型路径>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    model_path = Path(sys.argv[2])
    
    # 运行前置阶段
    video_info = analyze_video(video_path)
    transcript = transcribe_video(video_path, video_info, model_path)
    candidates = extract_candidate_frames(video_path, video_info)
    
    # 运行 Stage 4
    filtered = filter_keyframes(video_path, candidates, transcript)
    
    print(f"\n筛选后的关键帧 (M2):")
    for f in filtered.frames:
        print(f"  [{f.timestamp:7.2f}s] {f.reason}")
