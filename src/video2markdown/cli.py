"""命令行接口 - 支持分步执行和完整流程."""

import sys
from pathlib import Path

import click

from video2markdown.config import settings
from video2markdown.stats import get_stats, reset_stats


@click.group()
@click.version_option(version="2.0.0")
def cli():
    """Video2Markdown - 视频转结构化 Markdown 文档."""
    pass


@cli.command()
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), help="输出目录")
def stage1(video_path: Path, output: Path):
    """Stage 1: 视频分析."""
    from video2markdown.stage1_analyze import analyze_video
    
    info = analyze_video(video_path)
    
    # 保存结果
    output_dir = output or settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    import json
    result = {
        "path": str(info.path),
        "duration": info.duration,
        "resolution": f"{info.width}x{info.height}",
        "fps": info.fps,
        "scene_changes": info.scene_changes,
    }
    
    output_file = output_dir / f"{video_path.stem}_stage1.json"
    output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    
    click.echo(f"\n结果已保存: {output_file}")


@cli.command()
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path), help="输出目录")
@click.option("-l", "--language", default="zh", help="语言代码")
def stage2(video_path: Path, output: Path, language: str):
    """Stage 2: 音频提取与转录 (生成 M1)."""
    from video2markdown.stage1_analyze import analyze_video
    from video2markdown.stage2_transcribe import transcribe_video
    
    # 检查模型
    model_path = settings.resolve_whisper_model_path()
    if not model_path:
        click.echo("错误: 找不到 Whisper 模型", err=True)
        click.echo(f"请检查 KIMI_WHISPER_MODEL 配置或放置模型到 whisper.cpp/models/", err=True)
        sys.exit(1)
    
    # 运行
    video_info = analyze_video(video_path)
    transcript = transcribe_video(video_path, video_info, model_path)
    
    # 保存 M1
    output_dir = output or settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    srt_path = output_dir / f"{video_path.stem}.srt"
    srt_path.write_text(transcript.to_srt(), encoding="utf-8")
    
    word_path = output_dir / f"{video_path.stem}_word.md"
    word_path.write_text(transcript.to_word_document(), encoding="utf-8")
    
    click.echo(f"\nM1 已生成:")
    click.echo(f"  SRT: {srt_path}")
    click.echo(f"  文字稿: {word_path}")


@cli.command()
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path))
def stage3(video_path: Path, output: Path):
    """Stage 3: 关键帧提取."""
    from video2markdown.stage1_analyze import analyze_video
    from video2markdown.stage3_keyframes import extract_candidate_frames
    
    video_info = analyze_video(video_path)
    keyframes = extract_candidate_frames(video_path, video_info)
    
    # 保存
    output_dir = output or settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    import json
    result = {
        "video": str(video_path),
        "keyframes": [
            {"timestamp": f.timestamp, "source": f.source, "reason": f.reason}
            for f in keyframes.frames
        ]
    }
    
    output_file = output_dir / f"{video_path.stem}_stage3.json"
    output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    
    click.echo(f"\n候选帧已保存: {output_file}")


@cli.command()
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path))
@click.option("-l", "--language", default="zh")
def stage4(video_path: Path, output: Path, language: str):
    """Stage 4: 智能图片筛选 (生成 M2)."""
    from video2markdown.stage1_analyze import analyze_video
    from video2markdown.stage2_transcribe import transcribe_video
    from video2markdown.stage3_keyframes import extract_candidate_frames
    from video2markdown.stage4_filter import filter_keyframes
    
    model_path = settings.resolve_whisper_model_path()
    if not model_path:
        click.echo("错误: 找不到 Whisper 模型", err=True)
        sys.exit(1)
    
    video_info = analyze_video(video_path)
    transcript = transcribe_video(video_path, video_info, model_path)
    candidates = extract_candidate_frames(video_path, video_info)
    keyframes = filter_keyframes(video_path, candidates, transcript)
    
    # 保存 M2
    output_dir = output or settings.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    
    import json
    result = {
        "video": str(video_path),
        "filtered_frames": [
            {"timestamp": f.timestamp, "source": f.source, "reason": f.reason}
            for f in keyframes.frames
        ]
    }
    
    output_file = output_dir / f"{video_path.stem}_stage4.json"
    output_file.write_text(json.dumps(result, indent=2), encoding="utf-8")
    
    click.echo(f"\nM2 (筛选后的关键帧) 已保存: {output_file}")


@cli.command()
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path))
@click.option("-l", "--language", default="zh")
def stage5(video_path: Path, output: Path, language: str):
    """Stage 5: AI 图像分析 (生成 M3)."""
    from video2markdown.stage1_analyze import analyze_video
    from video2markdown.stage2_transcribe import transcribe_video
    from video2markdown.stage3_keyframes import extract_candidate_frames
    from video2markdown.stage4_filter import filter_keyframes
    from video2markdown.stage5_analyze_images import analyze_images
    
    model_path = settings.resolve_whisper_model_path()
    if not model_path:
        click.echo("错误: 找不到 Whisper 模型", err=True)
        sys.exit(1)
    
    video_info = analyze_video(video_path)
    transcript = transcribe_video(video_path, video_info, model_path)
    candidates = extract_candidate_frames(video_path, video_info)
    keyframes = filter_keyframes(video_path, candidates, transcript)
    
    frames_dir = (output or settings.output_dir) / f"{video_path.stem}_frames"
    descriptions = analyze_images(video_path, keyframes, transcript, frames_dir)
    
    click.echo(f"\nM3 (图片分析) 已完成")
    click.echo(f"  配图保存: {frames_dir}")
    for desc in descriptions.descriptions:
        click.echo(f"    [{desc.timestamp:.1f}s] {desc.description[:50]}...")


@cli.command()
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path))
@click.option("-l", "--language", default="zh")
def stage6(video_path: Path, output: Path, language: str):
    """Stage 6: AI 文档生成."""
    from video2markdown.stage1_analyze import analyze_video
    from video2markdown.stage2_transcribe import transcribe_video
    from video2markdown.stage3_keyframes import extract_candidate_frames
    from video2markdown.stage4_filter import filter_keyframes
    from video2markdown.stage5_analyze_images import analyze_images
    from video2markdown.stage6_generate import generate_document
    
    model_path = settings.resolve_whisper_model_path()
    if not model_path:
        click.echo("错误: 找不到 Whisper 模型", err=True)
        sys.exit(1)
    
    video_info = analyze_video(video_path)
    transcript = transcribe_video(video_path, video_info, model_path)
    candidates = extract_candidate_frames(video_path, video_info)
    keyframes = filter_keyframes(video_path, candidates, transcript)
    
    frames_dir = (output or settings.output_dir) / f"{video_path.stem}_frames"
    descriptions = analyze_images(video_path, keyframes, transcript, frames_dir)
    
    document = generate_document(transcript, keyframes, descriptions)
    
    click.echo(f"\n文档结构已生成:")
    click.echo(f"  标题: {document.title}")
    for ch in document.chapters:
        click.echo(f"  - {ch.title}")


@cli.command()
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option("-o", "--output", type=click.Path(path_type=Path))
@click.option("-l", "--language", default="zh")
def process(video_path: Path, output: Path, language: str):
    """完整流程: 执行所有 7 个阶段."""
    import time
    from datetime import datetime
    
    from video2markdown.stage1_analyze import analyze_video
    from video2markdown.stage2_transcribe import transcribe_video
    from video2markdown.stage3_keyframes import extract_candidate_frames
    from video2markdown.stage4_filter import filter_keyframes
    from video2markdown.stage5_analyze_images import analyze_images
    from video2markdown.stage6_generate import generate_document
    from video2markdown.stage7_render import render_markdown
    from video2markdown.stats import get_stats, reset_stats
    
    # 重置统计并设置初始信息
    reset_stats()
    stats = get_stats()
    stats.summary.video_name = video_path.name
    stats.summary.start_time = datetime.now().isoformat()
    
    output_dir = output or settings.output_dir
    temp_dir = output_dir / "temp"
    
    click.echo(f"处理视频: {video_path.name}")
    click.echo(f"输出目录: {output_dir}")
    click.echo()
    
    # 检查模型
    model_path = settings.resolve_whisper_model_path()
    if not model_path:
        click.echo("错误: 找不到 Whisper 模型", err=True)
        sys.exit(1)
    click.echo(f"使用 Whisper 模型: {model_path.name}")
    click.echo()
    
    # Stage 1
    click.echo("=" * 50)
    stats.summary.start_stage("stage1_analyze")
    video_info = analyze_video(video_path)
    stats.summary.video_duration = video_info.duration
    stats.summary.end_stage("stage1_analyze")
    stats.summary.completed_stages = 1
    click.echo()
    
    # Stage 2
    click.echo("=" * 50)
    stats.summary.start_stage("stage2_transcribe")
    transcript = transcribe_video(video_path, video_info, model_path)
    stats.summary.end_stage("stage2_transcribe")
    stats.summary.completed_stages = 2
    click.echo()
    
    # Stage 3
    click.echo("=" * 50)
    stats.summary.start_stage("stage3_keyframes")
    candidates = extract_candidate_frames(video_path, video_info)
    stats.summary.end_stage("stage3_keyframes")
    stats.summary.completed_stages = 3
    click.echo()
    
    # Stage 4
    click.echo("=" * 50)
    stats.summary.start_stage("stage4_filter")
    keyframes = filter_keyframes(video_path, candidates, transcript)
    stats.summary.end_stage("stage4_filter")
    stats.summary.completed_stages = 4
    click.echo()
    
    # Stage 5
    click.echo("=" * 50)
    stats.summary.start_stage("stage5_analyze_images")
    frames_dir = temp_dir / "images"
    descriptions = analyze_images(video_path, keyframes, transcript, frames_dir)
    stats.summary.end_stage("stage5_analyze_images")
    stats.summary.completed_stages = 5
    click.echo()
    
    # Stage 6
    click.echo("=" * 50)
    stats.summary.start_stage("stage6_generate")
    document = generate_document(transcript, keyframes, descriptions)
    stats.summary.end_stage("stage6_generate")
    stats.summary.completed_stages = 6
    click.echo()
    
    # Stage 7
    click.echo("=" * 50)
    stats.summary.start_stage("stage7_render")
    result_path = render_markdown(document, transcript, descriptions, output_dir, temp_dir)
    stats.summary.end_stage("stage7_render")
    stats.summary.completed_stages = 7
    
    # 设置结束时间
    stats.summary.end_time = datetime.now().isoformat()
    
    # 生成 ai_tokens.json 和 summary.md
    click.echo()
    click.echo("=" * 50)
    click.echo("生成汇总文件...")
    
    # 保存 ai_tokens.json
    ai_tokens_path = temp_dir / "ai_tokens.json"
    stats.save_json(ai_tokens_path)
    click.echo(f"  ✓ API 用量明细: {ai_tokens_path}")
    
    # 保存 summary.md
    summary_path = temp_dir / "summary.md"
    stats.save_summary_md(summary_path)
    click.echo(f"  ✓ 处理汇总报告: {summary_path}")
    
    # 打印统计摘要
    click.echo()
    click.echo(stats.summary_text())
    
    click.echo()
    click.echo("✅ 处理完成!")
    click.echo(f"输出: {result_path.parent}")


if __name__ == "__main__":
    cli()
