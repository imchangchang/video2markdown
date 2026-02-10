"""Document generation module for Video2Markdown V3.

This module implements the V3 workflow:
1. AI generates structured document from transcript (single API call)
2. Smart image extraction based on chapter needs
3. Markdown assembly with collapsible sections
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from openai import OpenAI

from video2markdown.config import settings


@dataclass
class Chapter:
    """Represents a document chapter."""
    id: int
    title: str
    start_time: str  # HH:MM:SS format
    end_time: str
    summary: str
    key_points: list[str]
    cleaned_transcript: str
    needs_visual: bool = False
    visual_timestamp: Optional[float] = None
    visual_reason: Optional[str] = None


@dataclass
class DocumentStructure:
    """Structured document output from AI."""
    title: str
    chapters: list[Chapter] = field(default_factory=list)


class DocumentGeneratorV3:
    """V3 document generator using single AI call for text processing."""
    
    def __init__(self):
        """Initialize document generator."""
        self.client = OpenAI(**settings.get_client_kwargs())
        self._load_prompts()
    
    def _load_prompts(self):
        """Load prompt templates from files."""
        try:
            self.doc_prompt = settings.get_prompt(settings.prompt_document_generation)
        except FileNotFoundError as e:
            print(f"Warning: Could not load prompt file: {e}")
            print("Using fallback prompt...")
            self.doc_prompt = self._get_fallback_document_prompt()
    
    def _get_fallback_document_prompt(self) -> str:
        """Fallback prompt if file not found."""
        return """你是一个专业的视频内容编辑助手。请分析视频转录文本，生成结构化文档。

任务：
1. 将内容划分为3-6个章节
2. 每个章节包含：标题、时间范围、摘要、关键要点
3. 去除语气词，修正识别错误
4. 将所有内容转换为简体中文
5. 判断每个章节是否需要配图

输入格式：
{
  "title": "视频标题",
  "language": "zh/en",
  "duration": 600,
  "segments": [{"start": 0.0, "end": 5.0, "text": "转录文本"}],
  "scene_changes": [10.0, 30.0, 60.0]
}

输出格式（JSON）：
{
  "title": "文档标题",
  "chapters": [
    {
      "id": 1,
      "title": "章节标题",
      "start_time": "00:00:00",
      "end_time": "00:05:00",
      "summary": "摘要",
      "key_points": ["要点1"],
      "cleaned_transcript": "清洗后的原文",
      "needs_visual": true,
      "visual_timestamp": 30.0,
      "visual_reason": "说明原因"
    }
  ]
}"""
    
    def generate_document_structure(
        self,
        segments: list[dict],
        title: str,
        duration: float,
        scene_changes: list[float],
        language: str = "zh",
    ) -> DocumentStructure:
        """Generate structured document from transcript segments.
        
        This is the core V3 function that makes a single AI call to:
        1. Structure content into chapters
        2. Clean and translate text to Simplified Chinese
        3. Remove filler words and repetitions
        4. Determine visual needs for each chapter
        
        Args:
            segments: List of transcript segments with start, end, text
            title: Video title
            duration: Video duration in seconds
            scene_changes: List of scene change timestamps
            language: Detected language code
            
        Returns:
            Structured document with chapters
        """
        # Prepare input
        input_data = {
            "title": title,
            "language": language,
            "duration": duration,
            "segments": segments,
            "scene_changes": scene_changes,
        }
        
        # Call AI
        try:
            response = self.client.chat.completions.create(
                model=settings.model,
                messages=[
                    {"role": "system", "content": self.doc_prompt},
                    {"role": "user", "content": json.dumps(input_data, ensure_ascii=False)},
                ],
                # Note: kimi-k2.5 only supports temperature=1
                temperature=1,
            )
            
            # Parse JSON response
            content = response.choices[0].message.content
            # Extract JSON from response (handle markdown code blocks)
            json_str = self._extract_json(content)
            data = json.loads(json_str)
            
            # Convert to DocumentStructure
            return self._parse_document_structure(data)
            
        except json.JSONDecodeError as e:
            print(f"Error parsing AI response: {e}")
            print(f"Response content: {content[:500]}")
            raise
        except Exception as e:
            print(f"Error generating document: {e}")
            raise
    
    def _extract_json(self, content: str) -> str:
        """Extract JSON from AI response, handling markdown code blocks."""
        content = content.strip()
        
        # Handle markdown code blocks
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            return content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            return content[start:end].strip()
        
        return content
    
    def _parse_document_structure(self, data: dict) -> DocumentStructure:
        """Parse JSON data into DocumentStructure."""
        chapters = []
        for ch_data in data.get("chapters", []):
            chapter = Chapter(
                id=ch_data.get("id", 0),
                title=ch_data.get("title", ""),
                start_time=ch_data.get("start_time", "00:00:00"),
                end_time=ch_data.get("end_time", "00:00:00"),
                summary=ch_data.get("summary", ""),
                key_points=ch_data.get("key_points", []),
                cleaned_transcript=ch_data.get("cleaned_transcript", ""),
                needs_visual=ch_data.get("needs_visual", False),
                visual_timestamp=ch_data.get("visual_timestamp"),
                visual_reason=ch_data.get("visual_reason"),
            )
            chapters.append(chapter)
        
        return DocumentStructure(
            title=data.get("title", "Untitled"),
            chapters=chapters,
        )
    
    def render_markdown(
        self,
        doc_structure: DocumentStructure,
        frames_dir: Optional[Path] = None,
        frame_mappings: Optional[dict] = None,
    ) -> str:
        """Render DocumentStructure to Markdown.
        
        Args:
            doc_structure: Structured document content
            frames_dir: Directory containing frame images (relative path)
            frame_mappings: Dict mapping chapter_id to frame filename
            
        Returns:
            Markdown formatted string
        """
        lines = []
        
        # Title
        lines.append(f"# {doc_structure.title}")
        lines.append("")
        lines.append("*AI整理的视频内容*")
        lines.append("")
        
        # Table of Contents
        lines.append("## 目录")
        for chapter in doc_structure.chapters:
            anchor = f"section-{chapter.id}"
            lines.append(f"{chapter.id}. [{chapter.title}](#{anchor})")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # Chapters
        for chapter in doc_structure.chapters:
            anchor = f"section-{chapter.id}"
            lines.append(f"<a id='{anchor}'></a>")
            lines.append(f"## {chapter.id}. {chapter.title}")
            lines.append("")
            lines.append(f"**时间:** [{chapter.start_time} - {chapter.end_time}]")
            lines.append("")
            
            # Summary
            lines.append("### 内容摘要")
            lines.append(chapter.summary)
            lines.append("")
            
            # Key Points
            if chapter.key_points:
                lines.append("### 关键要点")
                for point in chapter.key_points:
                    lines.append(f"- {point}")
                lines.append("")
            
            # Visual (if has frame)
            if chapter.needs_visual and frame_mappings and chapter.id in frame_mappings:
                lines.append("### 相关画面")
                frame_file = frame_mappings[chapter.id]
                if frames_dir:
                    frame_path = frames_dir / frame_file
                else:
                    frame_path = frame_file
                lines.append(f"![{chapter.visual_timestamp or ''}]({frame_path})")
                # Image analysis will be added later in collapsible section
                lines.append("<details>")
                lines.append("<summary>🖼️ 画面内容</summary>")
                lines.append("")
                lines.append("*图片分析内容将在此处显示*")
                lines.append("</details>")
                lines.append("")
            
            # Cleaned Transcript (collapsible)
            if chapter.cleaned_transcript:
                lines.append("### 原文记录")
                lines.append("<details>")
                lines.append("<summary>📄 查看原始转录</summary>")
                lines.append("")
                lines.append(chapter.cleaned_transcript)
                lines.append("</details>")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)


# Convenience function
def generate_document_v3(
    segments: list[dict],
    title: str,
    duration: float,
    scene_changes: list[float],
    language: str = "zh",
    frames_dir: Optional[Path] = None,
) -> tuple[str, DocumentStructure]:
    """Convenience function to generate document using V3 workflow.
    
    Args:
        segments: Transcript segments
        title: Video title
        duration: Video duration
        scene_changes: Scene change timestamps
        language: Language code
        frames_dir: Directory for frame images
        
    Returns:
        Tuple of (markdown_content, document_structure)
    """
    generator = DocumentGeneratorV3()
    doc_structure = generator.generate_document_structure(
        segments=segments,
        title=title,
        duration=duration,
        scene_changes=scene_changes,
        language=language,
    )
    markdown = generator.render_markdown(doc_structure, frames_dir)
    return markdown, doc_structure
