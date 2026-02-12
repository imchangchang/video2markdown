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
from video2markdown.stage5_analyze_images import _load_prompt_with_meta


def generate_document(
    transcript: VideoTranscript,
    keyframes: KeyFrames,
    descriptions: ImageDescriptions,
    title: Optional[str] = None,
) -> Document:
    """AI 图文融合生成.
    
    将 M1 (AI优化文稿)、M2 (关键配图)、M3 (配图说明) 融合为最终文档结构.
    
    Args:
        transcript: 视频文稿 (M1，已优化)
        keyframes: 关键配图 (M2)
        descriptions: 配图说明 (M3)
        title: 文档标题
        
    Returns:
        Document 文档结构
    """
    print(f"[Stage 6] AI 图文融合生成")
    
    client = OpenAI(**settings.get_client_kwargs())
    doc_title = title or transcript.title
    
    # 准备输入数据
    input_data = _prepare_input(transcript, keyframes, descriptions)
    
    print(f"  调用 AI 融合 M1 + M2 + M3...")
    
    # 加载 prompt 模板
    prompt_path = settings.prompts_dir / "document_merge.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_path}")
    
    system_msg, user_template, api_params = _load_prompt_with_meta(prompt_path)
    
    # 填充模板变量（使用安全替换，避免 JSON 中的 { 被当作格式标记）
    user_content = user_template
    user_content = user_content.replace("{title}", input_data["title"])
    user_content = user_content.replace("{m1_text}", input_data["m1_text"])
    user_content = user_content.replace("{images}", json.dumps(input_data["images"], ensure_ascii=False))
    
    # 调用 AI - 任务是在 M1 的合适位置插入配图
    response = client.chat.completions.create(
        model=settings.model,
        messages=[
            {
                "role": "system", 
                "content": system_msg
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        **api_params,
    )
    
    # 显示 Token 用量和价格
    _print_usage_info(response)
    
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


def _print_usage_info(response) -> None:
    """打印 API 用量和价格信息，并更新全局统计."""
    if not hasattr(response, 'usage') or response.usage is None:
        return
    
    usage = response.usage
    prompt_tokens = getattr(usage, 'prompt_tokens', 0)
    completion_tokens = getattr(usage, 'completion_tokens', 0)
    total_tokens = getattr(usage, 'total_tokens', 0)
    
    if total_tokens == 0:
        return
    
    # 更新全局统计
    from video2markdown.stats import get_stats
    get_stats().add(prompt_tokens, completion_tokens)
    
    # Kimi K2.5 价格 (2025-02)
    # 输入: ¥4.8 / 百万 tokens (约 $0.60)
    # 输出: ¥20 / 百万 tokens (约 $2.50)
    INPUT_PRICE_PER_1M = 4.8  # 人民币
    OUTPUT_PRICE_PER_1M = 20.0  # 人民币
    
    input_cost = (prompt_tokens / 1_000_000) * INPUT_PRICE_PER_1M
    output_cost = (completion_tokens / 1_000_000) * OUTPUT_PRICE_PER_1M
    total_cost = input_cost + output_cost
    
    print(f"  📊 Token 用量:")
    print(f"     输入: {prompt_tokens:,} tokens")
    print(f"     输出: {completion_tokens:,} tokens")
    print(f"     总计: {total_tokens:,} tokens")
    print(f"  💰 预估费用: ¥{total_cost:.4f} (输入¥{input_cost:.4f} + 输出¥{output_cost:.4f})")


def _prepare_input(
    transcript: VideoTranscript,
    keyframes: KeyFrames,
    descriptions: ImageDescriptions,
) -> dict:
    """准备 AI 输入数据."""
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
        "m1_text": transcript.optimized_text,  # 使用 AI 优化后的文稿
        "images": images_data,
    }


def _parse_response(content: str) -> dict:
    """解析 AI 响应，增强错误处理."""
    import re
    
    original_content = content.strip()
    
    # 处理 markdown 代码块
    if "```json" in content:
        start = content.find("```json") + 7
        end = content.find("```", start)
        if end == -1:
            end = len(content)
        content = content[start:end].strip()
    elif "```" in content:
        start = content.find("```") + 3
        end = content.find("```", start)
        if end == -1:
            end = len(content)
        content = content[start:end].strip()
    
    # 尝试解析 JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"  ⚠️  JSON 解析失败: {e}")
        print(f"  尝试修复...")
        
        # 尝试提取 JSON 对象（查找最外层的花括号内容）
        try:
            # 查找第一个 { 和最后一个 }
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_content = content[start_idx:end_idx+1]
                return json.loads(json_content)
        except Exception:
            pass
        
        # 如果仍然失败，返回一个基本的结构
        print(f"  ⚠️  无法解析 AI 响应，使用默认结构")
        # 保存原始响应用于调试
        debug_path = Path("test_outputs/temp/stage6_debug_response.txt")
        debug_path.parent.mkdir(parents=True, exist_ok=True)
        debug_path.write_text(original_content, encoding="utf-8")
        print(f"  原始响应已保存到: {debug_path}")
        
        return {
            "title": "解析失败 - 使用默认结构",
            "chapters": []
        }


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
