"""Stage 2: 音频提取与文稿生成.

包含三个子阶段:
    2a: 音频提取
    2b: 语音转录 (原始口语化文本)
    2c: AI文稿优化 (生成可直接阅读的 M1)

输入: 视频文件路径 + VideoInfo
输出: VideoTranscript (M1) + SRT (原始转录，参考用)
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import opencc
from openai import OpenAI

from video2markdown.config import settings
from video2markdown.models import TranscriptSegment, VideoInfo, VideoTranscript


def extract_audio(video_path: Path, output_path: Path) -> Path:
    """Stage 2a: 从视频提取音频."""
    print(f"  [2a] 提取音频...")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"  ✓ 音频已提取: {output_path}")
    return output_path


def transcribe_audio(
    audio_path: Path,
    model_path: Path,
    language: str = "zh"
) -> list[TranscriptSegment]:
    """Stage 2b: 使用 whisper.cpp 转录音频."""
    print(f"  [2b] 语音转录 (使用 {model_path.name})...")
    
    whisper_cli = _find_whisper_cli()
    output_dir = audio_path.parent
    output_name = audio_path.stem
    output_json = output_dir / f"{output_name}.json"
    
    cmd = [
        str(whisper_cli),
        "-m", str(model_path),
        "-f", str(audio_path),
        "-oj",
        "-of", str(output_dir / output_name),
        "-l", language,
    ]
    
    print(f"    运行: whisper-cli -m {model_path.name} ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"  错误: {result.stderr}")
        raise RuntimeError(f"whisper-cli 失败: {result.returncode}")
    
    # 查找输出文件
    if not output_json.exists():
        candidates = [
            audio_path.with_suffix(".json"),
            Path(str(audio_path) + ".json"),
            output_dir / f"{output_name}.wav.json",
        ]
        for candidate in candidates:
            if candidate.exists():
                output_json = candidate
                break
        else:
            raise FileNotFoundError(f"转录输出不存在: {candidates}")
    
    # 解析
    with open(output_json, "r") as f:
        data = json.load(f)
    
    output_json.unlink(missing_ok=True)
    
    segments = []
    for seg in data.get("transcription", []):
        segments.append(TranscriptSegment(
            start=seg.get("offsets", {}).get("from", 0) / 1000.0,
            end=seg.get("offsets", {}).get("to", 0) / 1000.0,
            text=seg.get("text", "").strip(),
        ))
    
    print(f"  ✓ 转录完成: {len(segments)} 个片段")
    return segments


def optimize_transcript(
    segments: list[TranscriptSegment],
    title: str,
    language: str = "zh",
) -> str:
    """Stage 2c: AI 优化转录为可读文稿 (生成 M1).
    
    将口语化的转录文本转换为结构化的可读文稿:
    - 去除语气词、口头禅
    - 分段落、加小标题
    - 修正专业术语
    - 去除重复内容
    """
    print(f"  [2c] AI 文稿优化...")
    
    # 合并转录文本
    raw_text = "\n".join(f"[{int(seg.start//60):02d}:{int(seg.start%60):02d}] {seg.text}" 
                         for seg in segments)
    
    client = OpenAI(**settings.get_client_kwargs())
    
    prompt = f"""请将以下视频转录文本转换为结构化的可读文稿。

原始文本是语音转录，包含口语化表达。请将其优化为正式的阅读文稿：

要求：
1. 去除语气词（嗯、啊、那个、这个、就是说等）
2. 去除重复内容
3. 修正明显的语音识别错误
4. 按逻辑分段，添加小标题（使用 ## 格式）
5. 保留关键时间戳 [MM:SS] 在段落开头
6. 确保专业术语准确
7. 输出纯 Markdown 格式，不要其他解释

标题: {title}

原始转录：
{raw_text[:8000]}  # 限制长度避免超出 token 限制

请输出优化后的文稿："""

    response = client.chat.completions.create(
        model=settings.model,
        messages=[
            {"role": "system", "content": "你是一位专业的文稿编辑，擅长将口语化转录转换为正式阅读文稿。"},
            {"role": "user", "content": prompt}
        ],
        temperature=1,  # kimi-k2.5 only supports temperature=1
    )
    
    optimized = response.choices[0].message.content.strip()
    
    # 清理可能的代码块标记
    if optimized.startswith("```markdown"):
        optimized = optimized[11:].strip()
    if optimized.startswith("```"):
        optimized = optimized[3:].strip()
    if optimized.endswith("```"):
        optimized = optimized[:-3].strip()
    
    print(f"  ✓ 文稿优化完成")
    return optimized


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
    """Stage 2 主函数: 完整的音频提取、转录、优化流程.
    
    Returns:
        VideoTranscript (M1) - AI优化后的可读文稿
    """
    print(f"[Stage 2] 音频提取与文稿生成: {video_path.name}")
    
    # 创建临时目录
    if temp_dir is None:
        temp_dir = Path(tempfile.gettempdir()) / "video2markdown"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    audio_path = temp_dir / f"{video_path.stem}.wav"
    
    try:
        # 2a: 提取音频
        extract_audio(video_path, audio_path)
        
        # 2b: 语音转录
        segments = transcribe_audio(audio_path, model_path, language)
        
        # 繁简转换
        if language in ("zh", "auto"):
            for seg in segments:
                seg.text = convert_to_simplified(seg.text)
        
        # 2c: AI 文稿优化 (生成 M1)
        optimized_text = optimize_transcript(segments, video_path.stem, language)
        
        # 创建 VideoTranscript (M1)
        transcript = VideoTranscript(
            video_path=video_path,
            title=video_path.stem,
            language=language,
            segments=segments,
            optimized_text=optimized_text,
        )
        
        print(f"  ✓ M1 (视频文稿) 生成完成")
        print(f"    - 原始转录: {len(segments)} 个片段")
        print(f"    - 优化文稿: {len(optimized_text)} 字符")
        
        return transcript
        
    finally:
        audio_path.unlink(missing_ok=True)


def _find_whisper_cli() -> Path:
    """查找 whisper-cli 可执行文件."""
    cli_path = settings.resolve_whisper_cli()
    if cli_path:
        return cli_path
    
    candidates = [
        Path(__file__).parent.parent.parent / "whisper.cpp" / "build" / "bin" / "whisper-cli",
        Path("whisper-cli"),
        Path("/usr/local/bin/whisper-cli"),
    ]
    
    for path in candidates:
        if path.exists() and path.is_file():
            return path.absolute()
    
    for cmd in ["whisper-cli", "whisper-cpp"]:
        result = subprocess.run(["which", cmd], capture_output=True, text=True)
        if result.returncode == 0:
            return Path(result.stdout.strip())
    
    raise FileNotFoundError("whisper-cli not found. Build: cd whisper.cpp && cmake -B build && cmake --build build")


# CLI 入口
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("用法: python -m video2markdown.stage2_transcribe <视频文件> <模型路径>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    model_path = Path(sys.argv[2])
    
    from video2markdown.stage1_analyze import analyze_video
    video_info = analyze_video(video_path)
    
    transcript = transcribe_video(video_path, video_info, model_path)
    
    # 保存输出
    output_dir = settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存 SRT (原始转录，参考用)
    srt_path = output_dir / f"{video_path.stem}.srt"
    srt_path.write_text(transcript.to_srt(), encoding="utf-8")
    print(f"\n  SRT (原始转录): {srt_path}")
    
    # 保存 M1 (AI优化后的文稿，核心产物)
    m1_path = output_dir / f"{video_path.stem}_word.md"
    m1_content = f"# {transcript.title}\n\n"
    m1_content += f"*AI优化后的视频文稿，可直接阅读替代视频*\n\n"
    m1_content += "---\n\n"
    m1_content += transcript.optimized_text
    m1_path.write_text(m1_content, encoding="utf-8")
    print(f"  M1 (视频文稿): {m1_path}")
