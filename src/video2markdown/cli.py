"""Command-line interface for Video2Markdown."""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional

import click
from tqdm import tqdm

from video2markdown import version
from video2markdown.asr import ASRProcessor, merge_short_segments, save_transcript_to_srt
from video2markdown.config import settings
from video2markdown.document import DocumentGenerator, generate_summary
from video2markdown.video import (
    detect_scene_changes,
    extract_keyframes,
    get_video_info,
    sample_uniform_frames,
)
from video2markdown.cli_v3 import process_v3
from video2markdown.vision import VisionProcessor


def setup_temp_dir(video_path: Path) -> Path:
    """Setup temporary directory for processing."""
    temp_dir = settings.temp_dir / f"{video_path.stem}_processing"
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir


def cleanup_temp_dir(temp_dir: Path, keep_frames: bool = False) -> None:
    """Cleanup temporary directory."""
    if not keep_frames and temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


@click.command()
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(path_type=Path),
    default=None,
    help="Output Markdown file path",
)
@click.option(
    "--title",
    default=None,
    help="Document title (defaults to video filename)",
)
@click.option(
    "--language",
    default="zh",
    help="Language code for transcription (zh, en, etc.)",
)
@click.option(
    "--scene-threshold",
    type=float,
    default=None,
    help="Scene change detection threshold (0.0-1.0)",
)
@click.option(
    "--max-keyframes",
    type=int,
    default=None,
    help="Maximum number of keyframes to extract",
)
@click.option(
    "--keyframe-interval",
    type=float,
    default=30.0,
    help="Interval between keyframes in seconds (if no scene changes detected)",
)
@click.option(
    "--no-transcript",
    is_flag=True,
    help="Skip audio transcription",
)
@click.option(
    "--no-vision",
    is_flag=True,
    help="Skip image analysis",
)
@click.option(
    "--keep-frames",
    is_flag=True,
    help="Keep extracted frames after processing",
)
@click.option(
    "--skip-existing",
    is_flag=True,
    help="Skip processing if output already exists",
)
@click.option(
    "--api-key",
    envvar="KIMI_API_KEY",
    help="Kimi API key (or set KIMI_API_KEY env var)",
)
@click.option(
    "--base-url",
    default=None,
    help="Kimi API base URL",
)
@click.option(
    "--model",
    default=None,
    help="Model name for text generation",
)
@click.option(
    "--vision-model",
    default=None,
    help="Model name for vision tasks",
)
@click.option(
    "--asr-provider",
    default=None,
    help="ASR provider: local (default), openai",
)
@click.option(
    "--whisper-key",
    default=None,
    help="OpenAI API key for Whisper (only for openai provider)",
)
@click.option(
    "--local-model",
    default=None,
    help="Local Whisper model size: tiny, base, small, medium, large (only for local provider)",
)
def main(
    video_path: Path,
    output: Optional[Path],
    title: Optional[str],
    language: str,
    scene_threshold: Optional[float],
    max_keyframes: Optional[int],
    keyframe_interval: float,
    no_transcript: bool,
    no_vision: bool,
    keep_frames: bool,
    skip_existing: bool,
    api_key: Optional[str],
    base_url: Optional[str],
    model: Optional[str],
    vision_model: Optional[str],
    asr_provider: Optional[str],
    whisper_key: Optional[str],
    local_model: Optional[str],
):
    """Convert video to Markdown document with AI-powered analysis.
    
    VIDEO_PATH: Path to the video file to process
    """
    # Validate API key
    if not api_key and not settings.api_key:
        click.echo("Error: API key is required. Set KIMI_API_KEY environment variable or use --api-key", err=True)
        sys.exit(1)
    
    # Update settings
    if api_key:
        os.environ["KIMI_API_KEY"] = api_key
    if base_url:
        os.environ["KIMI_BASE_URL"] = base_url
    if model:
        os.environ["KIMI_MODEL"] = model
    if vision_model:
        os.environ["KIMI_VISION_MODEL"] = vision_model
    if asr_provider:
        os.environ["KIMI_ASR_PROVIDER"] = asr_provider
    if whisper_key:
        os.environ["WHISPER_API_KEY"] = whisper_key
    if local_model:
        os.environ["KIMI_WHISPER_LOCAL_MODEL"] = local_model
    if scene_threshold is not None:
        os.environ["KIMI_SCENE_THRESHOLD"] = str(scene_threshold)
    if max_keyframes is not None:
        os.environ["KIMI_MAX_KEYFRAMES"] = str(max_keyframes)
    
    # Determine output path - maintain same directory structure as input
    if output is None:
        # Get the relative path from current working directory or common parent
        try:
            # Try to get relative path from cwd
            rel_path = video_path.relative_to(Path.cwd())
        except ValueError:
            # If not under cwd, use the path as-is
            rel_path = video_path
        
        # Replace 'input' with 'output' in the path, or just use output_dir
        path_parts = list(rel_path.parts)
        if len(path_parts) > 1 and path_parts[0] == "testbench" and path_parts[1] == "input":
            # Replace testbench/input with testbench/output
            output = settings.output_dir / rel_path.relative_to("testbench/input").parent / f"{video_path.stem}.md"
        else:
            # Default behavior: just put in output_dir
            output = settings.output_dir / f"{video_path.stem}.md"
    
    # Check if output exists
    if skip_existing and output.exists():
        click.echo(f"Output already exists: {output}")
        return
    
    # Determine title
    if title is None:
        title = video_path.stem
    
    # Setup
    click.echo(f"Processing: {video_path}")
    click.echo(f"Output: {output}")
    
    temp_dir = setup_temp_dir(video_path)
    frames_dir = temp_dir / "frames"
    
    try:
        # Step 1: Get video info
        click.echo("\n[1/5] Analyzing video...")
        video_info = get_video_info(video_path)
        click.echo(f"  Duration: {video_info['duration']:.1f}s")
        click.echo(f"  Resolution: {video_info['width']}x{video_info['height']}")
        click.echo(f"  FPS: {video_info['fps']:.2f}")
        
        # Step 2: Transcription
        transcripts = []
        if not no_transcript:
            click.echo("\n[2/5] Transcribing audio...")
            try:
                asr = ASRProcessor()
                transcripts = asr.process_video(video_path, language=language)
                transcripts = merge_short_segments(transcripts)
                click.echo(f"  Generated {len(transcripts)} transcript segments")
                
                # Save SRT for reference
                srt_path = output.parent / f"{output.stem}.srt"
                save_transcript_to_srt(transcripts, srt_path)
                click.echo(f"  Saved transcript: {srt_path}")
            except Exception as e:
                click.echo(f"  Warning: Transcription failed: {e}", err=True)
        
        # Step 3: Keyframe extraction
        click.echo("\n[3/5] Extracting keyframes...")
        
        # Detect scene changes
        scene_times = detect_scene_changes(video_path)
        click.echo(f"  Detected {len(scene_times)} scene changes")
        
        # If no scenes detected, use uniform sampling
        if len(scene_times) < 5:
            click.echo(f"  Using uniform sampling (every {keyframe_interval}s)")
            video_duration = video_info['duration']
            scene_times = [i * keyframe_interval for i in range(int(video_duration / keyframe_interval))]
        
        # Limit keyframes
        max_kf = max_keyframes or settings.max_keyframes
        if len(scene_times) > max_kf:
            # Sample evenly
            step = len(scene_times) / max_kf
            scene_times = [scene_times[int(i * step)] for i in range(max_kf)]
        
        keyframes = extract_keyframes(video_path, scene_times, frames_dir)
        keyframes = [kf for kf in keyframes if not kf.get("is_blurry", False)]
        click.echo(f"  Extracted {len(keyframes)} usable keyframes")
        
        # Step 4: Image analysis
        image_descriptions = []
        if not no_vision and keyframes:
            click.echo("\n[4/5] Analyzing images with AI...")
            try:
                vision = VisionProcessor()
                image_descriptions = vision.describe_images_batch(keyframes, transcripts)
                click.echo(f"  Analyzed {len(image_descriptions)} images")
            except Exception as e:
                click.echo(f"  Warning: Image analysis failed: {e}", err=True)
        
        # Step 5: Generate document
        click.echo("\n[5/5] Generating Markdown document...")
        
        # Copy frames to output directory
        output_frames_dir = output.parent / f"{output.stem}_frames"
        if image_descriptions and not keep_frames:
            output_frames_dir.mkdir(parents=True, exist_ok=True)
            for desc in image_descriptions:
                dest = output_frames_dir / desc.image_path.name
                shutil.copy2(desc.image_path, dest)
                desc.image_path = dest
        
        # Generate main document
        generator = DocumentGenerator(title=title)
        generator.generate(transcripts, image_descriptions, output)
        
        # Generate summary
        summary_path = output.parent / f"{output.stem}_summary.md"
        generate_summary(transcripts, image_descriptions, summary_path)
        
        click.echo(f"\n✅ Complete!")
        click.echo(f"  Main document: {output}")
        click.echo(f"  Summary: {summary_path}")
        if image_descriptions:
            click.echo(f"  Frames: {output_frames_dir}")
        
    except KeyboardInterrupt:
        click.echo("\n\nInterrupted by user", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"\n❌ Error: {e}", err=True)
        raise click.ClickException(str(e))
    finally:
        cleanup_temp_dir(temp_dir, keep_frames)


@click.group()
@click.version_option(version=version, prog_name="video2md")
def cli():
    """Video2Markdown - Convert videos to Markdown documents."""
    pass


@cli.command("info")
@click.argument("video_path", type=click.Path(exists=True, path_type=Path))
def info_cmd(video_path: Path):
    """Display video information."""
    video_info = get_video_info(video_path)
    
    click.echo(f"Video: {video_path}")
    click.echo(f"  Duration: {video_info['duration']:.2f} seconds")
    click.echo(f"  Resolution: {video_info['width']}x{video_info['height']}")
    click.echo(f"  FPS: {video_info['fps']:.2f}")
    click.echo(f"  Total frames: {video_info['total_frames']}")


cli.add_command(main, name="process")
cli.add_command(process_v3, name="process-v3")
cli.add_command(info_cmd, name="info")


def main_entry():
    """Main entry point - delegates to cli but supports direct video path."""
    import sys
    
    # If first arg is a file path (not a command), use process command
    if len(sys.argv) > 1 and not sys.argv[1].startswith("-"):
        arg = sys.argv[1]
        if arg not in ["process", "info", "--help", "-h", "--version"]:
            # Check if it's a file path
            path = Path(arg)
            if path.exists() and path.is_file():
                # Insert 'process' command
                sys.argv.insert(1, "process")
    
    cli()


if __name__ == "__main__":
    main_entry()
