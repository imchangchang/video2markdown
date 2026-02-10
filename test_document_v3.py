#!/usr/bin/env python3
"""Test V3 document generation from existing SRT files."""

import re
from pathlib import Path

from video2markdown.document_v3 import DocumentGeneratorV3


def parse_srt(srt_path: Path) -> list[dict]:
    """Parse SRT file into segments."""
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    segments = []
    
    # Split by empty lines
    blocks = re.split(r'\n\s*\n', content.strip())
    
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            # Line 1: sequence number (skip)
            # Line 2: time range
            time_line = lines[1]
            text = ' '.join(lines[2:])
            
            # Parse time: 00:00:00,000 --> 00:00:02,640
            match = re.match(
                r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
                time_line
            )
            if match:
                h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, match.groups())
                start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
                end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
                
                segments.append({
                    "start": start,
                    "end": end,
                    "text": text.strip()
                })
    
    return segments


def test_document_generation(srt_file: str, title: str = None, duration: float = None):
    """Test document generation from SRT file."""
    srt_path = Path("testbench/output") / srt_file
    
    if not srt_path.exists():
        print(f"❌ File not found: {srt_path}")
        return
    
    print(f"\n{'='*60}")
    print(f"Testing: {srt_file}")
    print(f"{'='*60}\n")
    
    # Parse SRT
    print(f"📄 Parsing SRT file...")
    segments = parse_srt(srt_path)
    print(f"   Loaded {len(segments)} segments")
    
    # Estimate duration if not provided
    if duration is None and segments:
        duration = segments[-1]["end"]
    
    print(f"   Duration: {duration:.1f}s ({duration/60:.1f} min)")
    print(f"   Sample text: {segments[0]['text'][:50]}...")
    
    # Generate document
    print(f"\n🤖 Generating document with AI...")
    generator = DocumentGeneratorV3()
    
    try:
        doc = generator.generate_document_structure(
            segments=segments,
            title=title or srt_path.stem,
            duration=duration,
            scene_changes=[],  # No scene changes for test
            language="zh"
        )
        
        print(f"\n✅ Success! Generated {len(doc.chapters)} chapters:\n")
        
        for ch in doc.chapters:
            visual_icon = "📷" if ch.needs_visual else "  "
            print(f"  {visual_icon} {ch.id}. {ch.title}")
            print(f"      Time: {ch.start_time} - {ch.end_time}")
            print(f"      Summary: {ch.summary[:80]}...")
            if ch.needs_visual:
                print(f"      Visual: {ch.visual_timestamp}s ({ch.visual_reason})")
            print()
        
        # Render markdown
        output_path = Path("testbench/output") / f"{srt_path.stem}_docv3.md"
        markdown = generator.render_markdown(doc, frames_dir=None)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        print(f"💾 Markdown saved to: {output_path}")
        print(f"   File size: {len(markdown)} bytes")
        
        # Preview
        print(f"\n📋 Preview (first 1500 chars):\n")
        print(markdown[:1500])
        print("\n... [truncated] ...\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Run tests on available SRT files."""
    output_dir = Path("testbench/output")
    srt_files = sorted(output_dir.glob("*.srt"))
    
    # Filter out already processed v3 files
    test_files = [f for f in srt_files if not f.name.endswith("_v3.srt") and not f.name.endswith("_docv3.md")]
    
    print(f"Found {len(test_files)} SRT files to test:")
    for f in test_files:
        print(f"  - {f.name}")
    
    # Test first 2 files
    if len(test_files) >= 1:
        test_document_generation(
            test_files[0].name,
            title="为什么我不再折腾RAG了",
            duration=351.0
        )
    
    if len(test_files) >= 2:
        test_document_generation(
            test_files[1].name,
            title="嵌入式开发，AI能做到什么程度了",
            duration=504.0
        )


if __name__ == "__main__":
    main()
