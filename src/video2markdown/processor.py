"""AI-powered document processor for Video2Markdown.

This implements the refined workflow:
1. Video analysis
2. Audio transcription (original language)
3. AI document generation (single call: structure + translate + clean)
4. Smart image extraction (conditional)
5. Markdown assembly
"""

import json
import shutil
from pathlib import Path
from typing import Optional

import click

from video2markdown.asr import ASRProcessor, save_transcript_to_srt
from video2markdown.config import settings
from video2markdown.document import DocumentGenerator
from video2markdown.video import detect_scene_changes, extract_best_frame, get_video_info


@click.command(name="process-ai")
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
    help="Language hint for transcription (zh, en, auto)",
)
@click.option(
    "--scene-threshold",
    type=float,
    default=0.3,
    help="Scene change detection threshold (0.0-1.0, lower = more scenes)",
)
@click.option(
    "--keep-frames",
    is_flag=True,
    help="Keep extracted frames after processing",
)
def process_ai(
    video_path: Path,
    output: Optional[Path],
    title: Optional[str],
    language: str,
    scene_threshold: float,
    keep_frames: bool,
):
    """Process video using AI-powered document generation."""
    
    # Setup paths
    if output is None:
        output = settings.output_dir / f"{video_path.stem}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    
    frames_dir = output.parent / f"{output.stem}_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    temp_dir = settings.temp_dir
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    doc_title = title or video_path.stem
    
    click.echo(f"Processing: {video_path.name}")
    click.echo(f"Output: {output}")
    click.echo()
    
    # Stage 1: Video Analysis
    click.echo("[1/4] Analyzing video...")
    video_info = get_video_info(video_path)
    click.echo(f"  Duration: {video_info['duration']:.1f}s")
    click.echo(f"  Resolution: {video_info['width']}x{video_info['height']}")
    
    # Detect scene changes for smart image extraction
    click.echo("  Detecting scene changes...")
    scene_changes = detect_scene_changes(video_path, threshold=scene_threshold)
    click.echo(f"  Found {len(scene_changes)} scene changes")
    
    # Stage 2: Audio Transcription
    click.echo()
    click.echo("[2/4] Transcribing audio...")
    asr = ASRProcessor()
    segments = asr.process_video(video_path, language=language)
    
    # Save SRT
    srt_path = output.with_suffix(".srt")
    save_transcript_to_srt(segments, srt_path)
    click.echo(f"  Generated {len(segments)} transcript segments")
    
    # Stage 3: AI Document Generation
    click.echo()
    click.echo("[3/4] Generating document with AI...")
    
    # Convert segments to dict format
    segment_dicts = [
        {"start": s.start, "end": s.end, "text": s.text}
        for s in segments
    ]
    
    generator = DocumentGenerator()
    doc_structure = generator.generate_document_structure(
        segments=segment_dicts,
        title=doc_title,
        duration=video_info["duration"],
        scene_changes=scene_changes,
        language=language,
    )
    
    click.echo(f"  Generated {len(doc_structure.chapters)} chapters")
    for ch in doc_structure.chapters:
        visual_mark = "📷" if ch.needs_visual else ""
        click.echo(f"    - {ch.title} {visual_mark}")
    
    # Stage 4: Smart Image Extraction
    click.echo()
    click.echo("[4/4] Extracting images...")
    
    frame_mappings = {}  # chapter_id -> frame_filename
    visual_chapters = [ch for ch in doc_structure.chapters if ch.needs_visual]
    
    if visual_chapters:
        click.echo(f"  Extracting {len(visual_chapters)} images based on AI recommendations...")
        
        for chapter in visual_chapters:
            if chapter.visual_timestamp:
                timestamp = chapter.visual_timestamp
                frame_file = f"frame_ch{chapter.id}_{timestamp:.1f}s.jpg"
                frame_path = frames_dir / frame_file
                
                try:
                    actual_path, actual_ts = extract_best_frame(video_path, timestamp, frame_path)
                    frame_mappings[chapter.id] = frame_file
                    click.echo(f"    ✓ Chapter {chapter.id}: {actual_ts:.1f}s (searched around {timestamp:.1f}s)")
                except Exception as e:
                    click.echo(f"    ✗ Chapter {chapter.id}: failed ({e})")
    else:
        click.echo("  No images needed based on content analysis")
    
    # Render Markdown
    click.echo()
    click.echo("Rendering Markdown...")
    markdown = generator.render_markdown(
        doc_structure,
        frames_dir=Path(output.stem + "_frames"),
        frame_mappings=frame_mappings,
    )
    
    # Save output
    with open(output, "w", encoding="utf-8") as f:
        f.write(markdown)
    
    # Cleanup
    if not keep_frames and not frame_mappings:
        shutil.rmtree(frames_dir, ignore_errors=True)
    
    click.echo()
    click.echo("✅ Complete!")
    click.echo(f"  Document: {output}")
    click.echo(f"  Subtitle: {srt_path}")
    if frame_mappings:
        click.echo(f"  Frames: {frames_dir}")


# Add to CLI group
def register_ai_command(cli):
    """Register AI processor command to CLI group."""
    cli.add_command(process_ai)
