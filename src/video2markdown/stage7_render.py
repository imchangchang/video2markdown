"""Stage 7: Markdown 渲染.

输入: Document + ImageDescriptions (M3)
输出: Markdown 文件

输出结构:
    {title}/
    ├── {title}.md           # 最终文档
    ├── {title}_word.md      # 视频文字稿
    ├── {title}.srt          # 字幕文件
    └── images/              # 关键配图
        ├── frame_0001_15.5s.jpg
        ├── frame_0001_15.5s.txt  # 配图说明
        └── ...
"""

import shutil
from pathlib import Path
from typing import Optional

from video2markdown.models import Document, ImageDescriptions, VideoTranscript


def render_markdown(
    document: Document,
    transcript: VideoTranscript,
    descriptions: ImageDescriptions,
    output_dir: Path,
) -> Path:
    """渲染 Markdown 文档.
    
    Args:
        document: 文档结构
        transcript: 视频文字稿 (M1)
        descriptions: 配图说明 (M3)
        output_dir: 输出目录
        
    Returns:
        主文档路径
    """
    print(f"[Stage 7] Markdown 渲染")
    
    # 创建输出目录结构
    doc_dir = output_dir / document.title
    doc_dir.mkdir(parents=True, exist_ok=True)
    
    # 使用统一的 images/ 目录存放配图，避免特殊字符路径问题
    frames_dir = doc_dir / "images"
    frames_dir.mkdir(exist_ok=True)
    
    # 1. 渲染主文档
    main_doc = _render_main_document(document, descriptions)
    main_path = doc_dir / f"{document.title}.md"
    main_path.write_text(main_doc, encoding="utf-8")
    print(f"  ✓ 主文档: {main_path}")
    
    # 2. 保存文字稿
    word_path = doc_dir / f"{document.title}_word.md"
    word_path.write_text(transcript.to_word_document(), encoding="utf-8")
    print(f"  ✓ 文字稿: {word_path}")
    
    # 3. 保存字幕
    srt_path = doc_dir / f"{document.title}.srt"
    srt_path.write_text(transcript.to_srt(), encoding="utf-8")
    print(f"  ✓ 字幕: {srt_path}")
    
    # 4. 复制配图和说明
    _copy_frames_with_descriptions(descriptions, frames_dir)
    
    return main_path


def _render_main_document(
    document: Document,
    descriptions: ImageDescriptions,
) -> str:
    """渲染主 Markdown 文档."""
    lines = []
    
    # 标题
    lines.append(f"# {document.title}")
    lines.append("")
    lines.append("*AI 整理的视频内容*")
    lines.append("")
    
    # 目录
    lines.append("## 目录")
    for ch in document.chapters:
        anchor = f"chapter-{ch.id}"
        lines.append(f"{ch.id}. [{ch.title}](#{anchor})")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    # 章节内容
    for ch in document.chapters:
        anchor = f"chapter-{ch.id}"
        lines.append(f"<a id='{anchor}'></a>")
        lines.append(f"## {ch.id}. {ch.title}")
        lines.append("")
        lines.append(f"**时间:** [{ch.start_time} - {ch.end_time}]")
        lines.append("")
        
        # 摘要
        lines.append("### 内容摘要")
        lines.append(ch.summary)
        lines.append("")
        
        # 关键要点
        if ch.key_points:
            lines.append("### 关键要点")
            for point in ch.key_points:
                lines.append(f"- {point}")
            lines.append("")
        
        # 配图 (如果有)
        if ch.visual_timestamp:
            desc = descriptions.get_by_timestamp(ch.visual_timestamp)
            if desc:
                frame_file = desc.image_path.name
                lines.append("### 相关画面")
                # 使用相对路径 images/ 目录，避免特殊字符和空格问题
                lines.append(f"![{ch.visual_timestamp}s](images/{frame_file})")
                lines.append("")
                lines.append("**画面内容:**")
                lines.append(f"> {desc.description}")
                lines.append("")
                if desc.key_elements:
                    lines.append(f"**关键元素:** {', '.join(desc.key_elements)}")
                    lines.append("")
        
        # 原文
        if ch.cleaned_transcript:
            lines.append("### 原文记录")
            lines.append("<details>")
            lines.append("<summary>📄 查看原始转录</summary>")
            lines.append("")
            lines.append(ch.cleaned_transcript)
            lines.append("</details>")
            lines.append("")
        
        lines.append("---")
        lines.append("")
    
    return "\n".join(lines)


def _copy_frames_with_descriptions(
    descriptions: ImageDescriptions,
    frames_dir: Path,
) -> None:
    """复制配图和说明文件."""
    for desc in descriptions.descriptions:
        if not desc.image_path.exists():
            continue
        
        # 复制图片
        dest_image = frames_dir / desc.image_path.name
        shutil.copy2(desc.image_path, dest_image)
        
        # 保存说明
        desc_file = frames_dir / f"{desc.image_path.stem}.txt"
        desc_content = f"时间戳: {desc.timestamp}s\n\n"
        desc_content += f"描述: {desc.description}\n\n"
        desc_content += f"关键元素: {', '.join(desc.key_elements)}\n\n"
        desc_content += f"相关文字稿:\n{desc.related_transcript[:500]}..."
        desc_file.write_text(desc_content, encoding="utf-8")
    
    print(f"  ✓ 配图: {frames_dir} ({len(descriptions.descriptions)} 张)")


# CLI 入口
if __name__ == "__main__":
    import sys
    from video2markdown.stage1_analyze import analyze_video
    from video2markdown.stage2_transcribe import transcribe_video
    from video2markdown.stage3_keyframes import extract_candidate_frames
    from video2markdown.stage4_filter import filter_keyframes
    from video2markdown.stage5_analyze_images import analyze_images
    from video2markdown.stage6_generate import generate_document
    
    if len(sys.argv) < 3:
        print("用法: python -m video2markdown.stage7_render <视频文件> <模型路径>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    model_path = Path(sys.argv[2])
    
    # 运行完整流程
    video_info = analyze_video(video_path)
    transcript = transcribe_video(video_path, video_info, model_path)
    candidates = extract_candidate_frames(video_path, video_info)
    keyframes = filter_keyframes(video_path, candidates, transcript)
    
    frames_dir = Path("testbench/output") / f"{video_path.stem}_frames"
    descriptions = analyze_images(video_path, keyframes, transcript, frames_dir)
    document = generate_document(transcript, keyframes, descriptions)
    
    # 运行 Stage 7
    output_dir = Path("testbench/output")
    result_path = render_markdown(document, transcript, descriptions, output_dir)
    
    print(f"\n✅ 完整输出已保存到: {result_path.parent}")
