"""Image understanding module with intelligent filtering."""

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from openai import OpenAI
from tqdm import tqdm

from video2markdown.config import settings
from video2markdown.video import resize_for_api


@dataclass
class ImageDescription:
    """Description of an image."""
    timestamp: float
    image_path: Path
    description: str
    key_elements: list[str]
    is_relevant: bool = True
    analysis_reason: str = ""  # 说明为什么分析这张图
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "image_path": str(self.image_path),
            "description": self.description,
            "key_elements": self.key_elements,
            "is_relevant": self.is_relevant,
            "analysis_reason": self.analysis_reason,
        }


def detect_text_in_image(image_path: Path) -> tuple[bool, float]:
    """
    检测图片中是否包含大量文字（如PPT、板书）
    
    Returns:
        (has_significant_text, text_ratio)
    """
    img = cv2.imread(str(image_path))
    if img is None:
        return False, 0.0
    
    # 转为灰度
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 使用边缘检测来识别文字区域
    edges = cv2.Canny(gray, 50, 150)
    
    # 计算文字区域比例
    text_pixels = np.sum(edges > 0)
    total_pixels = edges.shape[0] * edges.shape[1]
    text_ratio = text_pixels / total_pixels
    
    # 如果文字区域占比在 5%-50% 之间，认为是有意义的文字内容（PPT、板书等）
    # 太低可能是风景图，太高可能是纯文字截图
    has_significant_text = 0.05 < text_ratio < 0.50
    
    return has_significant_text, text_ratio


def is_likely_ppt_or_whiteboard(image_path: Path) -> bool:
    """判断图片是否可能是PPT、板书或演示文稿"""
    img = cv2.imread(str(image_path))
    if img is None:
        return False
    
    # 计算图片的主要颜色分布
    # PPT/板书通常有简洁的背景（白、黑、纯色）
    pixels = img.reshape(-1, 3)
    
    # 计算背景色占比（白色或接近白色）
    white_mask = np.all(pixels > 240, axis=1)
    white_ratio = np.sum(white_mask) / len(pixels)
    
    # 计算黑色背景占比
    dark_mask = np.all(pixels < 30, axis=1)
    dark_ratio = np.sum(dark_mask) / len(pixels)
    
    # 纯色背景占比超过40%，可能是PPT
    if white_ratio > 0.40 or dark_ratio > 0.40:
        return True
    
    # 检测是否有大量文字
    has_text, _ = detect_text_in_image(image_path)
    return has_text


def analyze_transcript_need_for_image(transcript_text: str) -> tuple[bool, str]:
    """
    分析文字稿是否需要图片辅助理解
    
    Returns:
        (needs_image, reason)
    """
    if not transcript_text or len(transcript_text.strip()) < 10:
        return True, "文字稿过短，需要图片补充"
    
    # 如果文字稿已经很详细（字数较多），可能不需要图片
    if len(transcript_text) > 200:
        # 检查是否包含具体的视觉描述词
        visual_indicators = [
            "如图所示", "如图", "看这个", "展示", "屏幕", "页面",
            "这边", "这里", "这个", "界面", "图表", "数据"
        ]
        
        has_visual_ref = any(indicator in transcript_text for indicator in visual_indicators)
        
        if not has_visual_ref:
            return False, "文字稿已详细且无明显视觉引用"
    
    # 检查文字稿是否包含抽象概念，可能需要图片辅助
    abstract_concepts = [
        "架构", "流程", "结构", "框架", "模型", "系统",
        "原理", "机制", "算法", "设计", "方案"
    ]
    
    has_abstract = any(concept in transcript_text for concept in abstract_concepts)
    
    if has_abstract:
        return True, "包含抽象概念，图片可能有助于理解"
    
    return True, "默认需要图片辅助"


class VisionProcessor:
    """Image understanding processor with intelligent filtering."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.client = OpenAI(**(api_key and {"api_key": api_key} or settings.get_client_kwargs()))
        self.model = settings.vision_model
        self.api_call_count = 0
    
    def should_analyze_image(
        self,
        image_path: Path,
        transcript_context: Optional[str],
    ) -> tuple[bool, str]:
        """
        智能判断是否需要对该图片调用API分析
        
        Returns:
            (should_analyze, reason)
        """
        # 1. 首先检查图片是否是PPT/板书类型
        is_ppt = is_likely_ppt_or_whiteboard(image_path)
        
        if is_ppt:
            return True, "检测到PPT/板书类图片，值得分析"
        
        # 2. 检查文字稿是否需要图片辅助
        if transcript_context:
            needs_image, reason = analyze_transcript_need_for_image(transcript_context)
            if not needs_image:
                return False, f"文字稿已足够清晰，跳过: {reason}"
        
        # 3. 检查图片内容是否丰富
        has_text, text_ratio = detect_text_in_image(image_path)
        
        if not has_text and text_ratio < 0.02:
            # 图片几乎没有文字，可能是风景、人物等无关画面
            return False, "图片无显著文字内容，可能是过渡画面"
        
        return True, "图片可能有价值，需要API分析确认"
    
    def describe_image(
        self,
        image_path: Path,
        context: Optional[str] = None,
    ) -> Optional[ImageDescription]:
        """Generate description for a single image, with smart filtering."""
        
        # 智能判断是否值得调用API
        should_analyze, reason = self.should_analyze_image(image_path, context)
        
        if not should_analyze:
            print(f"  [跳过] {image_path.name}: {reason}")
            return None
        
        print(f"  [分析] {image_path.name}: {reason}")
        
        # 调用API分析
        processed_path = resize_for_api(image_path)
        
        with open(processed_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        mime_type = "image/png" if processed_path.suffix.lower() == ".png" else "image/jpeg"
        
        # 构建提示 - 强调简体中文输出
        system_prompt = (
            "你是一位专业的视频内容分析师。请分析这张视频截图，并用简体中文（非繁体）简要描述。\n\n"
            "重要提示：\n"
            "1. 输出必须是简体中文，不要使用繁体中文\n"
            "2. 如果这是PPT、板书、代码或文档截图，请提取关键文字内容\n"
            "3. 如果是无关画面（风景、黑屏、过渡动画），请在description中写[无关]\n"
            "4. 描述要简洁，突出重点\n\n"
            "输出格式（JSON）：\n"
            "{\n"
            '  "description": "简体中文描述，如无关请写[无关]",\n'
            '  "key_elements": ["关键元素1", "关键元素2"]\n'
            "}"
        )
        
        user_text = "请用简体中文分析这张视频截图："
        if context:
            user_text = f"视频上下文：{context[:300]}\n\n请用简体中文分析这张截图与上述内容的关联："
        
        # Call API
        self.api_call_count += 1
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": [
                    {"type": "text", "text": user_text},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_data}"}}
                ]}
            ],
        }
        
        # kimi-k2.5 only supports temperature=1
        if "k2.5" not in self.model:
            kwargs["temperature"] = 0.3
        
        completion = self.client.chat.completions.create(**kwargs)
        content = completion.choices[0].message.content
        
        return self._parse_description(content, 0.0, image_path, reason)
    
    def describe_images_batch(
        self,
        keyframes: list[dict],
        transcripts: Optional[list] = None,
    ) -> list[ImageDescription]:
        """Describe multiple images with intelligent filtering."""
        descriptions = []
        skipped_count = 0
        
        for frame in tqdm(keyframes, desc="分析图片"):
            if frame.get("is_blurry"):
                skipped_count += 1
                continue
            
            # 获取文字稿上下文
            context = None
            if transcripts:
                context = self._find_transcript_context(frame["timestamp"], transcripts)
            
            try:
                desc = self.describe_image(frame["path"], context)
                if desc:
                    desc.timestamp = frame["timestamp"]
                    if desc.is_relevant:
                        descriptions.append(desc)
                    else:
                        skipped_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                print(f"  [错误] 分析失败 {frame['timestamp']}: {e}")
                skipped_count += 1
        
        print(f"\n图片分析统计：")
        print(f"  - API调用: {self.api_call_count} 次")
        print(f"  - 成功: {len(descriptions)} 张")
        print(f"  - 跳过: {skipped_count} 张")
        
        return descriptions
    
    def _find_transcript_context(
        self,
        timestamp: float,
        transcripts: list,
        window: float = 8.0,
    ) -> Optional[str]:
        """Find transcript text around a timestamp."""
        relevant = []
        for seg in transcripts:
            if (seg.start <= timestamp + window and seg.end >= timestamp - window):
                relevant.append(seg.text)
        
        # 去重
        unique_texts = []
        for text in relevant:
            if not unique_texts or text != unique_texts[-1]:
                unique_texts.append(text)
        
        return " ".join(unique_texts)[:600] if unique_texts else None
    
    def _parse_description(
        self,
        content: str,
        timestamp: float,
        image_path: Path,
        analysis_reason: str = "",
    ) -> ImageDescription:
        """Parse API response into ImageDescription."""
        import json
        import re
        
        description = content.strip()
        key_elements = []
        is_relevant = True
        
        # Try to extract JSON
        try:
            json_match = re.search(r'```(?:json)?\s*(\{.*?)\s*```', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(1))
            else:
                json_match = re.search(r'\{[\s\S]*?"description"[\s\S]*?\}', content)
                if json_match:
                    data = json.loads(json_match.group(0))
                else:
                    data = {}
            
            description = data.get("description", content)
            key_elements = data.get("key_elements", [])
        except (json.JSONDecodeError, AttributeError):
            pass
        
        # 检查是否标记为无关
        irrelevant_keywords = ["[无关]", "不相关", "黑屏", "过渡画面", "纯装饰", "无实质内容"]
        if any(kw in description for kw in irrelevant_keywords):
            is_relevant = False
        
        return ImageDescription(
            timestamp=timestamp,
            image_path=image_path,
            description=description,
            key_elements=key_elements if isinstance(key_elements, list) else [key_elements],
            is_relevant=is_relevant,
            analysis_reason=analysis_reason,
        )
