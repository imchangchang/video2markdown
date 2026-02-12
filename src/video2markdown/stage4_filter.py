"""Stage 4: 智能图片筛选.

输入: 视频文件 + 候选关键帧 + VideoTranscript (M1)
输出: KeyFrames (M2) - 筛选后的关键帧

筛选策略 (四层):
    1. 时间戳分析去重
    2. 动画稳定检测 (新增)
    3. 文字检测 (OpenCV)
    4. 转录上下文检查
"""

from pathlib import Path
from typing import Optional

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
    
    四层筛选:
    1. 时间戳去重 (合并过近的帧)
    2. 动画稳定检测 (检测并修正动画过渡帧)
    3. 文字检测 (OpenCV 边缘检测)
    4. 转录上下文检查 (检查对应时段是否提及视觉内容)
    
    Args:
        video_path: 视频文件路径
        candidates: 候选关键帧
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
        
        # 第二层: 动画稳定检测
        # 检测该时间点是否处于动画中，如果是，调整到稳定帧
        # 默认只向后搜索（捕捉动画完成后的状态）
            # 第二层: 动画稳定检测
        # 检测该时间点是否处于动画中，如果是，调整到稳定帧
        # 默认只向后搜索（捕捉动画完成后的状态）
        # 放宽 max_shift 到 5s 以捕捉长动画后的完整帧
        stable_ts, stability_info = _find_stable_frame(
            video_path, frame.timestamp, 
            prefer_direction="backward",
            window_sec=5.0,  # 搜索窗口 5s
            max_shift=5.0    # 支持 52s→57s 的长动画
        )
        if stable_ts != frame.timestamp:
            print(f"adjusted {frame.timestamp:.1f}s → {stable_ts:.1f}s ", end="")
            frame.timestamp = stable_ts
            frame.reason = f"{frame.reason} | {stability_info}"
        
        # 第三层: 文字检测
        has_text, text_ratio = _detect_text_content(video_path, frame.timestamp)
        if not has_text and text_ratio < 0.02:
            print(f"SKIP (无显著文字, 密度={text_ratio:.3f})")
            continue
        
        # 第四层: 转录上下文检查
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


def _find_stable_frame(
    video_path: Path,
    timestamp: float,
    window_sec: float = 3.0,  # 增大窗口从1s到3s，适应长动画
    step_sec: float = 0.2,    # 增大步长减少计算量
    max_shift: float = 2.5,   # 最大允许偏移2.5s（支持52s→55s这种情况）
    stability_threshold: float = 8.0,  # 稳定性阈值，低于此值视为稳定
    prefer_direction: str = "backward",  # "backward"(向后) 或 "auto"(自动)
) -> tuple[float, str]:
    """查找稳定帧，避开动画过渡.
    
    策略:
    1. 在目标时间戳前后 window_sec 范围内采样
    2. 计算相邻帧的差异度
    3. 选择差异度最低的稳定帧
    
    Args:
        video_path: 视频文件路径
        timestamp: 目标时间戳
        window_sec: 搜索窗口 (秒)
        step_sec: 采样步长 (秒)
        max_shift: 最大允许时间偏移 (秒)
        stability_threshold: 稳定性阈值，低于此值视为稳定帧
        prefer_direction: 搜索方向 "backward"(只向后) 或 "auto"(前后都搜)
        
    Returns:
        (stable_timestamp, info_string)
    """
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return timestamp, "无法打开视频"
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    # 生成采样时间点
    samples = []
    if prefer_direction == "backward":
        # 只向后搜索（更晚的时间点）
        current = timestamp
        end = min(duration, timestamp + window_sec)
    else:
        # 前后都搜索
        current = max(0, timestamp - window_sec)
        end = min(duration, timestamp + window_sec)
    
    while current <= end:
        samples.append(current)
        current += step_sec
    
    if len(samples) < 2:
        cap.release()
        return timestamp, "采样点不足"
    
    # 计算每帧的稳定性得分
    # 稳定性 = 与前后帧的平均差异度倒数
    stability_scores = []
    
    for i, ts in enumerate(samples):
        # 读取当前帧
        frame = _read_frame_at(cap, ts, fps)
        if frame is None:
            stability_scores.append((ts, float('inf')))
            continue
        
        # 计算与前后帧的差异
        diffs = []
        
        # 与前一个采样点比较
        if i > 0:
            prev_frame = _read_frame_at(cap, samples[i-1], fps)
            if prev_frame is not None:
                diff = _frame_difference(frame, prev_frame)
                diffs.append(diff)
        
        # 与后一个采样点比较
        if i < len(samples) - 1:
            next_frame = _read_frame_at(cap, samples[i+1], fps)
            if next_frame is not None:
                diff = _frame_difference(frame, next_frame)
                diffs.append(diff)
        
        # 稳定性得分 = 平均差异 (越低越稳定)
        avg_diff = sum(diffs) / len(diffs) if diffs else float('inf')
        stability_scores.append((ts, avg_diff))
    
    cap.release()
    
    # 找到最稳定的帧
    # 但要在目标时间戳的合理范围内，不能完全偏离
    best_ts = timestamp
    best_score = float('inf')
    
    # 首先检查原始时间点的稳定性
    original_score = None
    for ts, score in stability_scores:
        if abs(ts - timestamp) < 0.05:  # 接近原始时间点
            original_score = score
            break
    
    # 在窗口内寻找最稳定的帧
    # 优先选择稍晚的时间点（动画通常向前播放，后面更完整）
    for ts, score in stability_scores:
        # 不能太远离原始时间点
        if abs(ts - timestamp) > max_shift:
            continue
        
        # 向后偏移的帧给予轻微偏好（权重：时间差 * 0.5）
        time_bias = (ts - timestamp) * 0.5
        adjusted_score = score - time_bias  # 越往后，得分越低（越优选）
        
        if adjusted_score < best_score:
            best_score = adjusted_score
            best_ts = ts
    
    # 判断是否处于动画中
    if original_score is not None and best_score < original_score * 0.7:
        # 找到了明显更稳定的帧
        if abs(best_ts - timestamp) > 0.1:
            return best_ts, f"动画稳定化({timestamp:.1f}→{best_ts:.1f})"
    
    # 如果原始帧已经很稳定，或者所有帧都不稳定，保持原样
    if original_score is not None and original_score < stability_threshold:
        return timestamp, "已稳定"
    elif best_score < stability_threshold:
        shift = best_ts - timestamp
        if abs(shift) > 0.5:
            return best_ts, f"动画稳定化(+{shift:+.1f}s)"
        else:
            return best_ts, f"微调({shift:+.1f}s)"
    else:
        # 所有帧都不稳定，选择相对最稳定的
        if best_score < original_score * 0.6 if original_score else float('inf'):
            return best_ts, f"相对最稳({best_ts:.1f})"
        return timestamp, "持续动画中"


def _read_frame_at(cap: cv2.VideoCapture, timestamp: float, fps: float) -> Optional[np.ndarray]:
    """在指定时间戳读取帧 (缩小尺寸用于快速比较)."""
    frame_idx = int(timestamp * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    
    if not ret:
        return None
    
    # 缩小尺寸加快比较速度
    small = cv2.resize(frame, (320, 180))
    return small


def _frame_difference(frame1: np.ndarray, frame2: np.ndarray) -> float:
    """计算两帧的差异度.
    
    使用多指标综合评估:
    1. 像素级差异 (MSE)
    2. 结构相似性 (简化版)
    3. 边缘变化
    
    Returns:
        差异得分 (0-100, 越低表示越相似)
    """
    # 转灰度
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)
    
    # 1. 均方误差 (MSE)
    mse = np.mean((gray1.astype(float) - gray2.astype(float)) ** 2)
    
    # 2. 边缘差异 (检测文字/图形变化)
    edges1 = cv2.Canny(gray1, 50, 150)
    edges2 = cv2.Canny(gray2, 50, 150)
    edge_diff = np.mean(cv2.absdiff(edges1, edges2))
    
    # 3. 直方图差异 (颜色分布变化)
    hist1 = cv2.calcHist([gray1], [0], None, [32], [0, 256])
    hist2 = cv2.calcHist([gray2], [0], None, [32], [0, 256])
    hist_diff = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CHISQR)
    
    # 综合得分 (归一化到 0-100)
    # 权重: MSE 40%, 边缘 40%, 直方图 20%
    score = (mse / 255 * 0.4 + edge_diff / 255 * 0.4 + min(hist_diff / 1000, 1) * 100 * 0.2)
    
    return min(score, 100)


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
    from video2markdown.stage2_transcribe import transc_video
    from video2markdown.stage3_keyframes import extract_candidate_frames
    
    if len(sys.argv) < 3:
        print("用法: python -m video2markdown.stage4_filter <视频文件> <模型路径>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    model_path = Path(sys.argv[2])
    
    # 运行前置阶段
    video_info = analyze_video(video_path)
    transcript = transc_video(video_path, video_info, model_path)
    candidates = extract_candidate_frames(video_path, video_info)
    
    # 运行 Stage 4
    filtered = filter_keyframes(video_path, candidates, transcript)
    
    print(f"\n筛选后的关键帧 (M2):")
    for f in filtered.frames:
        print(f"  [{f.timestamp:7.2f}s] {f.reason}")
