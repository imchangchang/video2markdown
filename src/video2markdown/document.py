"""Document generation module with AI-powered summarization."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from openai import OpenAI

from video2markdown.asr import TranscriptSegment, format_timestamp
from video2markdown.config import settings
from video2markdown.vision import ImageDescription


@dataclass
class DocumentSection:
    """A section in the output document."""
    start_time: float
    end_time: float
    title: str
    content: str  # AI总结后的内容
    original_text: str  # 原始转录文本
    key_images: list[ImageDescription]  # 关键图片（只在需要时）


class DocumentGenerator:
    """Generate structured Markdown documents with AI summarization."""
    
    def __init__(
        self,
        title: str = "Video Analysis",
        model: Optional[str] = None,
    ):
        """Initialize document generator.
        
        Args:
            title: Document title
            model: LLM model for summarization
        """
        self.title = title
        self.model = model or settings.model
        self.client = OpenAI(**settings.get_client_kwargs())
    
    def generate(
        self,
        transcripts: list[TranscriptSegment],
        image_descriptions: list[ImageDescription],
        output_path: Path,
    ) -> Path:
        """Generate structured document with AI summarization.
        
        Args:
            transcripts: List of transcript segments
            image_descriptions: List of image descriptions
            output_path: Output file path
            
        Returns:
            Path to generated document
        """
        # Step 1: Use AI to analyze and summarize the transcript
        structured_content = self._summarize_transcript(transcripts)
        
        # Step 2: Align images with sections (only keep relevant ones)
        sections = self._create_sections(structured_content, transcripts, image_descriptions)
        
        # Step 3: Generate Markdown
        markdown = self._generate_markdown(sections)
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        
        return output_path
    
    def _summarize_transcript(
        self,
        transcripts: list[TranscriptSegment],
    ) -> list[dict]:
        """Use AI to summarize transcript into structured sections.
        
        Returns:
            List of sections with title, summary, and timestamps
        """
        # Prepare transcript text with timestamps
        transcript_text = ""
        for seg in transcripts:
            time_str = format_timestamp(seg.start)
            transcript_text += f"[{time_str}] {seg.text}\n"
        
        # Build prompt for AI summarization
        system_prompt = (
            "你是一位专业的内容编辑。请将以下视频转录文字稿整理成结构化的中文文档。\n\n"
            "要求：\n"
            "1. 分析文字稿的核心主题和结构\n"
            "2. 将内容分成3-8个逻辑段落（章节）\n"
            "3. 每个段落包含：\n"
            "   - 小标题（概括该部分核心内容）\n"
            "   - 详细总结（用中文流畅地重述核心观点）\n"
            "   - 关键时间戳（该段落对应的视频时间，格式[MM:SS]）\n"
            "4. 保持专业性和可读性\n"
            "5. 输出必须是简体中文\n\n"
            "输出格式（JSON）：\n"
            "[\n"
            "  {\n"
            '    "title": "章节标题",\n'
            '    "summary": "详细总结内容...",\n'
            '    "start_time": "00:00",\n'
            '    "end_time": "01:30",\n'
            '    "key_points": ["要点1", "要点2"]\n'
            "  },\n"
            "  ...\n"
            "]"
        )
        
        # Truncate if too long (keep last ~8000 tokens)
        max_chars = 24000
        if len(transcript_text) > max_chars:
            transcript_text = "..." + transcript_text[-max_chars:]
        
        # Call AI for summarization
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"视频标题：{self.title}\n\n转录文字稿：\n{transcript_text}"},
            ],
        }
        
        if "k2.5" not in self.model:
            kwargs["temperature"] = 0.3
        
        completion = self.client.chat.completions.create(**kwargs)
        content = completion.choices[0].message.content
        
        # Parse JSON response
        return self._parse_summary_json(content, transcripts)
    
    def _parse_summary_json(
        self,
        content: str,
        transcripts: list[TranscriptSegment],
    ) -> list[dict]:
        """Parse AI summary response into structured data."""
        import json
        import re
        
        try:
            # Extract JSON from response
            json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                # Try to find JSON array directly
                json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    data = []
            
            # Validate and normalize
            sections = []
            for item in data:
                section = {
                    "title": item.get("title", "未命名章节"),
                    "summary": item.get("summary", ""),
                    "start_time": item.get("start_time", "00:00"),
                    "end_time": item.get("end_time", "00:00"),
                    "key_points": item.get("key_points", []),
                }
                sections.append(section)
            
            return sections if sections else self._fallback_sections(transcripts)
            
        except (json.JSONDecodeError, Exception) as e:
            print(f"Warning: Failed to parse AI summary: {e}")
            return self._fallback_sections(transcripts)
    
    def _fallback_sections(
        self,
        transcripts: list[TranscriptSegment],
    ) -> list[dict]:
        """Fallback: create simple sections from transcripts."""
        sections = []
        chunk_size = max(1, len(transcripts) // 5)  # ~5 sections
        
        for i in range(0, len(transcripts), chunk_size):
            chunk = transcripts[i:i+chunk_size]
            if not chunk:
                continue
            
            start_time = format_timestamp(chunk[0].start)
            end_time = format_timestamp(chunk[-1].end)
            text = " ".join([seg.text for seg in chunk])
            
            # Extract first sentence as title
            title = text[:30] + "..." if len(text) > 30 else text
            
            sections.append({
                "title": title,
                "summary": text,
                "start_time": start_time,
                "end_time": end_time,
                "key_points": [],
            })
        
        return sections
    
    def _create_sections(
        self,
        structured_content: list[dict],
        transcripts: list[TranscriptSegment],
        image_descriptions: list[ImageDescription],
    ) -> list[DocumentSection]:
        """Create document sections from structured content."""
        sections = []
        
        for item in structured_content:
            # Parse timestamps
            start_sec = self._parse_time_to_seconds(item.get("start_time", "00:00"))
            end_sec = self._parse_time_to_seconds(item.get("end_time", "00:00"))
            
            # Find original text for this time range
            original_text = " ".join([
                seg.text for seg in transcripts
                if start_sec <= seg.start <= end_sec or start_sec <= seg.end <= end_sec
            ])
            
            # Find relevant images (only keep most relevant ones)
            key_images = [
                img for img in image_descriptions
                if start_sec <= img.timestamp <= end_sec and img.is_relevant
            ][:2]  # Max 2 images per section
            
            sections.append(DocumentSection(
                start_time=start_sec,
                end_time=end_sec,
                title=item.get("title", "未命名章节"),
                content=item.get("summary", ""),
                original_text=original_text,
                key_images=key_images,
            ))
        
        return sections
    
    def _parse_time_to_seconds(self, time_str: str) -> float:
        """Parse time string (MM:SS or HH:MM:SS) to seconds."""
        parts = time_str.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        return 0.0
    
    def _generate_markdown(self, sections: list[DocumentSection]) -> str:
        """Generate Markdown content from sections."""
        lines = []
        
        # Title
        lines.append(f"# {self.title}")
        lines.append("")
        lines.append("*AI整理的视频内容*")
        lines.append("")
        
        # Table of Contents
        if sections:
            lines.append("## 目录")
            lines.append("")
            for i, section in enumerate(sections, 1):
                lines.append(f"{i}. [{section.title}](#section-{i})")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # Sections
        for i, section in enumerate(sections, 1):
            lines.append(f"<a id='section-{i}'></a>")
            lines.append(f"## {i}. {section.title}")
            lines.append("")
            
            # Time reference
            start_fmt = format_timestamp(section.start_time)
            end_fmt = format_timestamp(section.end_time)
            lines.append(f"**时间：** [{start_fmt} - {end_fmt}]")
            lines.append("")
            
            # Main content (AI summary)
            lines.append(section.content)
            lines.append("")
            
            # Key points if available
            if hasattr(section, 'key_points') and section.key_points:
                lines.append("**要点：**")
                for point in section.key_points:
                    lines.append(f"- {point}")
                lines.append("")
            
            # Key images (only if relevant)
            if section.key_images:
                lines.append("**相关画面：**")
                lines.append("")
                for img in section.key_images:
                    rel_path = self._get_image_path(img.image_path)
                    lines.append(f"![{format_timestamp(img.timestamp)}]({rel_path})")
                    if img.description:
                        lines.append(f"*{img.description[:60]}...*")
                    lines.append("")
            
            # Collapsible original transcript
            if section.original_text:
                lines.append("<details>")
                lines.append("<summary>原始转录文字</summary>")
                lines.append("")
                lines.append(f"> {section.original_text}")
                lines.append("")
                lines.append("</details>")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def _get_image_path(self, image_path: Path) -> str:
        """Get image path for Markdown reference."""
        parent = image_path.parent
        if parent.name.endswith("_frames"):
            return f"{parent.name}/{image_path.name}"
        return str(image_path.name)


def generate_summary(
    transcripts: list[TranscriptSegment],
    image_descriptions: list[ImageDescription],
    output_path: Optional[Path] = None,
) -> str:
    """Generate a brief summary of the video content.
    
    Args:
        transcripts: List of transcript segments
        image_descriptions: List of image descriptions
        output_path: Optional path to save summary
        
    Returns:
        Summary text
    """
    full_text = " ".join([t.text for t in transcripts])
    
    # Use AI to generate summary
    client = OpenAI(**settings.get_client_kwargs())
    
    prompt = (
        "请用中文总结以下视频内容的要点：\n\n"
        f"{full_text[:3000]}\n\n"
        "要求：\n"
        "1. 列出3-5个核心要点\n"
        "2. 输出简体中文\n"
        "3. 简洁明了"
    )
    
    kwargs = {
        "model": settings.model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if "k2.5" not in settings.model:
        kwargs["temperature"] = 0.3
    
    completion = client.chat.completions.create(**kwargs)
    summary = completion.choices[0].message.content
    
    # Create summary document
    lines = [
        "# 视频摘要",
        "",
        f"**时长：** {format_timestamp(transcripts[-1].end if transcripts else 0)}",
        f"**关键画面：** {len([img for img in image_descriptions if img.is_relevant])} 张",
        "",
        "## 内容要点",
        "",
        summary,
        "",
    ]
    
    summary_text = "\n".join(lines)
    
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
    
    return summary_text
