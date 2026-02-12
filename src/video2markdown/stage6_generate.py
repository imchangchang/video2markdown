"""Stage 6: AI 文档生成.

输入: M1 (VideoTranscript) + M2 (KeyFrames) + M3 (ImageDescriptions)
输出: Document (文档结构)

流程:
    1. 将 M1 的文字稿发送给 AI
    2. AI 生成章节结构
    3. 根据 M2/M3 将图片关联到章节
    4. 生成最终文档结构
"""

import json
from pathlib import Path
from typing import Optional

from openai import OpenAI

from video2markdown.config import settings
from video2markdown.models import (
    Chapter, Document, ImageDescriptions, KeyFrames, VideoTranscript
)


def generate_document(
    transcript: VideoTranscript,
    keyframes: KeyFrames,
    descriptions: ImageDescriptions,
    title: Optional[str] = None,
) -> Document:
    """AI 生成文档结构.
    
    Args:
        transcript: 视频文字稿 (M1)
        keyframes: 关键配图 (M2)
        descriptions: 配图说明 (M3)
        title: 文档标题
        
    Returns:
        Document 文档结构
    """
    print(f"[Stage 6] AI 文档生成")
    
    client = OpenAI(**settings.get_client_kwargs())
    doc_title = title or transcript.title
    
    # 准备输入数据
    input_data = _prepare_input(transcript, keyframes, descriptions)
    
    print(f"  调用 AI 生成文档结构...")
    
    # 调用 AI
    response = client.chat.completions.create(
        model=settings.model,
        messages=[
            {
                "role": "system", 
                "content": _get_document_prompt()
            },
            {
                "role": "user",
                "content": json.dumps(input_data, ensure_ascii=False)
            }
        ],
        temperature=1,
    )
    
    # 解析响应
    content = response.choices[0].message.content
    doc_data = _parse_response(content)
    
    # 创建 Document
    chapters = []
    for i, ch in enumerate(doc_data.get("chapters", []), 1):
        chapter = Chapter(
            id=i,
            title=ch.get("title", f"章节 {i}"),
            start_time=ch.get("start_time", "00:00:00"),
            end_time=ch.get("end_time", "00:00:00"),
            summary=ch.get("summary", ""),
            key_points=ch.get("key_points", []),
            cleaned_transcript=ch.get("cleaned_transcript", ""),
            visual_timestamp=ch.get("visual_timestamp"),
            visual_reason=ch.get("visual_reason"),
        )
        chapters.append(chapter)
    
    print(f"  ✓ 生成 {len(chapters)} 个章节")
    
    return Document(
        title=doc_data.get("title", doc_title),
        chapters=chapters,
    )


def _prepare_input(
    transcript: VideoTranscript,
    keyframes: KeyFrames,
    descriptions: ImageDescriptions,
) -> dict:
    """准备 AI 输入数据."""
    # 文字稿
    segments_data = []
    for seg in transcript.segments:
        segments_data.append({
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
        })
    
    # 配图信息
    images_data = []
    for desc in descriptions.descriptions:
        images_data.append({
            "timestamp": desc.timestamp,
            "description": desc.description,
            "key_elements": desc.key_elements,
        })
    
    return {
        "title": transcript.title,
        "language": transcript.language,
        "duration": transcript.segments[-1].end if transcript.segments else 0,
        "segments": segments_data,
        "images": images_data,
    }


def _get_document_prompt() -> str:
    """获取文档生成提示."""
    return """你是一位专业的视频内容编辑。请将视频转录文本转换为结构化的 Markdown 文档。

任务：
1. 将内容划分为 3-6 个章节
2. 每个章节包含：标题、时间范围、摘要、关键要点、清洗后的原文
3. 去除语气词，修正识别错误
4. 将所有内容转换为简体中文
5. 根据提供的图片描述，判断每个章节是否需要配图，选择合适的图片时间戳

输入格式：
{
  "title": "视频标题",
  "language": "zh",
  "duration": 600,
  "segments": [{"start": 0, "end": 5, "text": "..."}],
  "images": [{"timestamp": 30, "description": "...", "key_elements": [...]}]
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
      "summary": "AI 生成的摘要",
      "key_points": ["要点1", "要点2"],
      "cleaned_transcript": "清洗后的原文",
      "visual_timestamp": 125.5,
      "visual_reason": "展示架构图"
    }
  ]
}

注意事项：
1. 所有文本必须是简体中文
2. 只输出 JSON，不要有其他内容
3. 确保 JSON 格式正确
4. 时间戳格式为 HH:MM:SS"""


def _parse_response(content: str) -> dict:
    """解析 AI 响应."""
    content = content.strip()
    
    # 处理 markdown 代码块
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        content = content[start:end].strip()
    elif "```" in content:
        start = content.find("```") + 3
        end = content.find("```", start)
        content = content[start:end].strip()
    
    return json.loads(content)


# CLI 入口
if __name__ == "__main__":
    import sys
    from video2markdown.stage1_analyze import analyze_video
    from video2markdown.stage2_transcribe import transcribe_video
    from video2markdown.stage3_keyframes import extract_candidate_frames
    from video2markdown.stage4_filter import filter_keyframes
    from video2markdown.stage5_analyze_images import analyze_images
    
    if len(sys.argv) < 3:
        print("用法: python -m video2markdown.stage6_generate <视频文件> <模型路径>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    model_path = Path(sys.argv[2])
    
    # 运行前置阶段
    video_info = analyze_video(video_path)
    transcript = transcribe_video(video_path, video_info, model_path)
    candidates = extract_candidate_frames(video_path, video_info)
    keyframes = filter_keyframes(video_path, candidates, transcript)
    
    frames_dir = Path("testbench/output") / f"{video_path.stem}_frames"
    descriptions = analyze_images(video_path, keyframes, transcript, frames_dir)
    
    # 运行 Stage 6
    document = generate_document(transcript, keyframes, descriptions)
    
    print(f"\n文档结构:")
    print(f"  标题: {document.title}")
    for ch in document.chapters:
        visual = f" [配图@{ch.visual_timestamp:.0f}s]" if ch.visual_timestamp else ""
        print(f"  - {ch.title}{visual}")
