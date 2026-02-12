"""Stage 5: AI 图像分析.

输入: 视频文件 + KeyFrames (M2) + VideoTranscript (M1)
输出: ImageDescriptions (M3)

流程:
    1. 根据 M2 的时间点提取原始帧 (无压缩)
    2. 使用 Kimi Vision API 分析每张图片
    3. 结合 M1 的文字稿上下文
    4. 生成图片描述
"""

import base64
from pathlib import Path
from typing import Optional

import cv2
from openai import OpenAI

from video2markdown.config import settings
from video2markdown.models import ImageDescription, ImageDescriptions, KeyFrames, VideoTranscript


def analyze_images(
    video_path: Path,
    keyframes: KeyFrames,
    transcript: VideoTranscript,
    output_dir: Path,
    max_size: int = 1024,
) -> ImageDescriptions:
    """AI 分析关键帧图片.
    
    Args:
        video_path: 视频文件路径
        keyframes: 筛选后的关键帧 (M2)
        transcript: 视频文字稿 (M1)
        output_dir: 输出目录 (保存原始帧)
        max_size: 发送给 API 的最大图片尺寸
        
    Returns:
        ImageDescriptions (M3)
    """
    print(f"[Stage 5] AI 图像分析: {len(keyframes.frames)} 张图片")
    
    client = OpenAI(**settings.get_client_kwargs())
    descriptions = []
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    for i, frame in enumerate(keyframes.frames, 1):
        print(f"  分析图片 {i}/{len(keyframes.frames)} @ {frame.timestamp:.1f}s...")
        
        # 1. 提取原始帧 (高质量)
        frame_path = output_dir / f"frame_{i:04d}_{frame.timestamp:.1f}s.jpg"
        _extract_original_frame(video_path, frame.timestamp, frame_path)
        
        # 2. 准备 API 调用 (压缩版本)
        api_image = _prepare_for_api(frame_path, max_size)
        
        # 3. 获取相关文字稿
        context = transcript.get_text_around(frame.timestamp, window=10.0)
        
        # 4. 调用 AI 分析
        desc = _analyze_single_image(
            client, api_image, frame.timestamp, frame_path, context
        )
        
        descriptions.append(desc)
        print(f"    ✓ {desc.description[:60]}...")
    
    print(f"  ✓ 完成 {len(descriptions)} 张图片分析")
    return ImageDescriptions(descriptions=descriptions)


def _extract_original_frame(
    video_path: Path,
    timestamp: float,
    output_path: Path,
    quality: int = 95,
) -> Path:
    """提取原始视频帧 (无压缩，高质量)."""
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_idx = int(timestamp * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise RuntimeError(f"无法读取 {timestamp}s 的帧")
    
    # 保存高质量原图
    cv2.imwrite(str(output_path), frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return output_path


def _prepare_for_api(image_path: Path, max_size: int) -> Path:
    """准备图片用于 API 调用 (压缩但保持清晰)."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise RuntimeError(f"无法读取图片: {image_path}")
    
    h, w = img.shape[:2]
    
    # 等比例缩放
    if max(h, w) > max_size:
        scale = max_size / max(h, w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    
    # 保存临时文件
    temp_path = image_path.parent / f"{image_path.stem}_api.jpg"
    cv2.imwrite(str(temp_path), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    
    return temp_path


def _load_prompt_with_meta(template_path: Path):
    """加载 prompt 模板，返回 (system_msg, user_template, api_params)."""
    import yaml
    
    content = template_path.read_text(encoding="utf-8")
    
    # 解析 YAML frontmatter
    _, frontmatter, body = content.split("---", 2)
    metadata = yaml.safe_load(frontmatter)
    
    system_msg = metadata.get("system", "你是一位专业的视频内容分析师。")
    api_params = metadata.get("parameters", {})
    user_template = body.strip()
    
    return system_msg, user_template, api_params


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
    
    # 从配置获取价格
    input_cost = (prompt_tokens / 1_000_000) * settings.price_input_per_1m
    output_cost = (completion_tokens / 1_000_000) * settings.price_output_per_1m
    total_cost = input_cost + output_cost
    
    print(f"      📊 Token 用量: {prompt_tokens:,} 输入 / {completion_tokens:,} 输出")
    print(f"      💰 预估费用: ¥{total_cost:.4f}")


def _analyze_single_image(
    client: OpenAI,
    image_path: Path,
    timestamp: float,
    original_path: Path,
    context: str,
) -> ImageDescription:
    """使用 Kimi Vision API 分析单张图片."""
    
    # 读取并编码图片
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    
    # 加载 prompt 模板
    prompt_path = settings.prompts_dir / "image_analysis.md"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_path}")
    
    system_msg, user_template, api_params = _load_prompt_with_meta(prompt_path)
    user_content = user_template.format(context=context[:500])
    
    # 调用 API
    response = client.chat.completions.create(
        model=settings.vision_model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": [
                {"type": "text", "text": user_content},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data}"
                }}
            ]}
        ],
        **api_params,
    )
    
    content = response.choices[0].message.content
    
    # 打印 Token 用量
    _print_usage_info(response)
    
    # 解析响应 (简单处理)
    description = content.strip()
    key_elements = _extract_key_elements(content)
    
    # 清理临时 API 图片
    image_path.unlink(missing_ok=True)
    
    return ImageDescription(
        timestamp=timestamp,
        image_path=original_path,  # 指向原始高质量图片
        description=description,
        key_elements=key_elements,
        related_transcript=context,
    )


def _extract_key_elements(text: str) -> list[str]:
    """从描述中提取关键元素."""
    # 简单提取：寻找关键词或列表项
    elements = []
    
    # 检查是否有列表格式
    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        # 提取以 - 或数字开头的列表项
        if line.startswith("-") or line.startswith("•"):
            elements.append(line[1:].strip())
    
    return elements[:5]  # 最多 5 个


# CLI 入口
if __name__ == "__main__":
    import sys
    from video2markdown.stage1_analyze import analyze_video
    from video2markdown.stage2_transcribe import transcribe_video
    from video2markdown.stage3_keyframes import extract_candidate_frames
    from video2markdown.stage4_filter import filter_keyframes
    
    if len(sys.argv) < 3:
        print("用法: python -m video2markdown.stage5_analyze_images <视频文件> <模型路径>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    model_path = Path(sys.argv[2])
    
    # 运行前置阶段
    video_info = analyze_video(video_path)
    transcript = transcribe_video(video_path, video_info, model_path)
    candidates = extract_candidate_frames(video_path, video_info)
    keyframes = filter_keyframes(video_path, candidates, transcript)
    
    # 运行 Stage 5
    output_dir = Path("testbench/output") / f"{video_path.stem}_frames"
    descriptions = analyze_images(video_path, keyframes, transcript, output_dir)
    
    print(f"\n图片分析结果 (M3):")
    for desc in descriptions.descriptions:
        print(f"\n  [{desc.timestamp:.1f}s] {desc.image_path.name}")
        print(f"  描述: {desc.description[:100]}...")
        print(f"  元素: {desc.key_elements}")
