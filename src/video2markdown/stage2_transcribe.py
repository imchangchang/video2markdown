"""Stage 2: 音频提取与文字稿转化.

输入: 视频文件路径 + VideoInfo
输出: VideoTranscript (M1)

验证点:
    - SRT 文件是否正确生成
    - 文字稿是否可读
    - AI 优化后的文字稿质量
"""

import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import opencc

from video2markdown.models import TranscriptSegment, VideoInfo, VideoTranscript


def extract_audio(video_path: Path, output_path: Path) -> Path:
    """从视频提取音频.
    
    Args:
        video_path: 视频文件路径
        output_path: 输出音频路径
        
    Returns:
        音频文件路径
    """
    print(f"  提取音频...")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn",  # 无视频
        "-acodec", "pcm_s16le",  # 16-bit PCM
        "-ar", "16000",  # 16kHz (Whisper 推荐)
        "-ac", "1",  # 单声道
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    
    print(f"  ✓ 音频已提取: {output_path}")
    return output_path


def transcribe_with_whisper(
    audio_path: Path,
    model_path: Path,
    language: str = "zh"
) -> list[TranscriptSegment]:
    """使用 whisper.cpp 转录音频.
    
    Args:
        audio_path: 音频文件路径
        model_path: 模型文件路径
        language: 语言代码
        
    Returns:
        转录片段列表
    """
    print(f"  转录音频 (使用 {model_path.name})...")
    
    # 确定输出路径 (whisper.cpp 会自动添加 .json)
    output_json = audio_path.with_suffix(".wav.json")
    
    # 查找 whisper-cpp 可执行文件
    whisper_cpp = _find_whisper_cpp()
    
    cmd = [
        str(whisper_cpp),
        "-m", str(model_path),
        "-f", str(audio_path),
        "-oj",  # 输出 JSON
        "-of", str(audio_path.with_suffix("")),  # 输出前缀
        "-l", language,
    ]
    
    print(f"    运行: {' '.join(cmd[:6])}...")
    subprocess.run(cmd, check=True, capture_output=True)
    
    # 解析输出
    if not output_json.exists():
        # 尝试替代路径
        alt_json = Path(str(audio_path) + ".json")
        if alt_json.exists():
            output_json = alt_json
        else:
            raise FileNotFoundError(f"转录输出文件不存在: {output_json}")
    
    import json
    with open(output_json, "r") as f:
        data = json.load(f)
    
    # 清理临时文件
    output_json.unlink(missing_ok=True)
    
    # 解析为 TranscriptSegment
    segments = []
    for seg in data.get("transcription", []):
        segments.append(TranscriptSegment(
            start=seg.get("offsets", {}).get("from", 0) / 1000.0,
            end=seg.get("offsets", {}).get("to", 0) / 1000.0,
            text=seg.get("text", "").strip(),
        ))
    
    print(f"  ✓ 转录完成: {len(segments)} 个片段")
    return segments


def convert_to_simplified(text: str) -> str:
    """繁体中文转简体中文."""
    converter = opencc.OpenCC('t2s')
    return converter.convert(text)


def transcribe_video(
    video_path: Path,
    video_info: VideoInfo,
    model_path: Path,
    language: str = "zh",
    temp_dir: Optional[Path] = None,
) -> VideoTranscript:
    """Stage 2 主函数: 转录视频生成文字稿.
    
    Args:
        video_path: 视频文件路径
        video_info: 视频信息 (来自 Stage 1)
        model_path: Whisper 模型路径
        language: 语言代码
        temp_dir: 临时目录
        
    Returns:
        VideoTranscript (M1)
    """
    print(f"[Stage 2] 音频提取与转录: {video_path.name}")
    
    # 创建临时音频文件
    if temp_dir is None:
        temp_dir = Path(tempfile.gettempdir()) / "video2markdown"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    audio_path = temp_dir / f"{video_path.stem}.wav"
    
    try:
        # 提取音频
        extract_audio(video_path, audio_path)
        
        # 转录
        segments = transcribe_with_whisper(audio_path, model_path, language)
        
        # 繁简转换
        if language in ("zh", "auto"):
            print(f"  繁简转换...")
            for seg in segments:
                seg.text = convert_to_simplified(seg.text)
        
        # 创建 VideoTranscript (M1)
        transcript = VideoTranscript(
            video_path=video_path,
            title=video_path.stem,
            language=language,
            segments=segments,
            optimized_text="",  # Stage 6 会填充
        )
        
        print(f"  ✓ M1 生成完成: {len(segments)} 个片段")
        return transcript
        
    finally:
        # 清理临时音频
        audio_path.unlink(missing_ok=True)


def _find_whisper_cpp() -> Path:
    """查找 whisper-cpp 可执行文件."""
    candidates = [
        Path("whisper-cpp"),
        Path(__file__).parent.parent.parent / "whisper-cpp",
        Path("/usr/local/bin/whisper-cpp"),
    ]
    
    for path in candidates:
        if path.exists() and path.is_file():
            return path.absolute()
    
    # 尝试 which
    result = subprocess.run(["which", "whisper-cpp"], capture_output=True, text=True)
    if result.returncode == 0:
        return Path(result.stdout.strip())
    
    raise FileNotFoundError("whisper-cpp 可执行文件未找到")


# CLI 入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python -m video2markdown.stage2_transcribe <视频文件> <模型路径>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    model_path = Path(sys.argv[2])
    
    # 先运行 Stage 1 获取 VideoInfo
    from video2markdown.stage1_analyze import analyze_video
    video_info = analyze_video(video_path)
    
    # 运行 Stage 2
    transcript = transcribe_video(video_path, video_info, model_path)
    
    # 保存 M1
    output_dir = Path("testbench/output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存 SRT
    srt_path = output_dir / f"{video_path.stem}.srt"
    srt_path.write_text(transcript.to_srt(), encoding="utf-8")
    print(f"\n  SRT 已保存: {srt_path}")
    
    # 保存文字稿
    word_path = output_dir / f"{video_path.stem}_word.md"
    word_path.write_text(transcript.to_word_document(), encoding="utf-8")
    print(f"  文字稿已保存: {word_path}")
