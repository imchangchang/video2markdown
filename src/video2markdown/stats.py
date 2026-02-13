"""全局统计信息模块.

用于收集和汇总各阶段的 API 用量和费用.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from video2markdown.config import settings


@dataclass
class APICallRecord:
    """单次 API 调用记录."""
    stage: str
    timestamp: str
    prompt_tokens: int
    completion_tokens: int
    model: str = ""
    
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class ProcessingSummary:
    """处理汇总信息."""
    video_name: str = ""
    video_duration: float = 0.0
    start_time: str = ""
    end_time: str = ""
    total_stages: int = 7
    completed_stages: int = 0
    
    @property
    def elapsed_seconds(self) -> float:
        if not self.start_time or not self.end_time:
            return 0.0
        try:
            start = datetime.fromisoformat(self.start_time)
            end = datetime.fromisoformat(self.end_time)
            return (end - start).total_seconds()
        except:
            return 0.0


class UsageStats:
    """API 用量统计."""
    
    def __init__(self):
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.api_calls: int = 0
        self.records: list[APICallRecord] = []
        self.summary: ProcessingSummary = ProcessingSummary()
    
    @property
    def input_price(self) -> float:
        """输入 token 单价 (¥/token)."""
        return settings.llm_price_input_per_1m / 1_000_000
    
    @property
    def output_price(self) -> float:
        """输出 token 单价 (¥/token)."""
        return settings.llm_price_output_per_1m / 1_000_000
    
    def add(self, prompt_tokens: int, completion_tokens: int, stage: str = "", model: str = "") -> None:
        """添加一次 API 调用的用量."""
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.api_calls += 1
        
        # 记录明细
        record = APICallRecord(
            stage=stage or f"call_{self.api_calls}",
            timestamp=datetime.now().isoformat(),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model=model or settings.model,
        )
        self.records.append(record)
    
    def add_from_response(self, response, stage: str = "") -> None:
        """从 API 响应中提取用量信息."""
        if not hasattr(response, 'usage') or response.usage is None:
            return
        
        usage = response.usage
        prompt = getattr(usage, 'prompt_tokens', 0)
        completion = getattr(usage, 'completion_tokens', 0)
        model = getattr(response, 'model', settings.model)
        self.add(prompt, completion, stage=stage, model=model)
    
    @property
    def total_tokens(self) -> int:
        """总 token 数."""
        return self.prompt_tokens + self.completion_tokens
    
    @property
    def input_cost(self) -> float:
        """输入费用 (¥)."""
        return self.prompt_tokens * self.input_price
    
    @property
    def output_cost(self) -> float:
        """输出费用 (¥)."""
        return self.completion_tokens * self.output_price
    
    @property
    def total_cost(self) -> float:
        """总费用 (¥)."""
        return self.input_cost + self.output_cost
    
    def summary_text(self) -> str:
        """格式化汇总信息（用于终端显示）."""
        lines = [
            "📊 AI API 用量汇总:",
            f"   API 调用: {self.api_calls} 次",
            f"   Token 用量: {self.prompt_tokens:,} 输入 / {self.completion_tokens:,} 输出 / {self.total_tokens:,} 总计",
            f"   预估费用: ¥{self.total_cost:.4f} (输入¥{self.input_cost:.4f} + 输出¥{self.output_cost:.4f})",
        ]
        return "\n".join(lines)
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 序列化）."""
        return {
            "summary": {
                "video_name": self.summary.video_name,
                "video_duration_seconds": self.summary.video_duration,
                "start_time": self.summary.start_time,
                "end_time": self.summary.end_time,
                "elapsed_seconds": self.summary.elapsed_seconds,
                "total_stages": self.summary.total_stages,
                "completed_stages": self.summary.completed_stages,
            },
            "pricing": {
                "input_price_per_1m": settings.llm_price_input_per_1m,
                "output_price_per_1m": settings.llm_price_output_per_1m,
                "currency": "CNY",
            },
            "total": {
                "api_calls": self.api_calls,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens,
                "input_cost": round(self.input_cost, 4),
                "output_cost": round(self.output_cost, 4),
                "total_cost": round(self.total_cost, 4),
            },
            "records": [
                {
                    "stage": r.stage,
                    "timestamp": r.timestamp,
                    "model": r.model,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "total_tokens": r.total_tokens,
                }
                for r in self.records
            ],
        }
    
    def save_json(self, path: Path) -> None:
        """保存为 JSON 文件."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
    
    def generate_summary_md(self) -> str:
        """生成 summary.md 内容."""
        lines = [
            f"# 处理汇总报告",
            "",
            f"**视频**: {self.summary.video_name}",
            f"**开始时间**: {self.summary.start_time}",
            f"**结束时间**: {self.summary.end_time}",
            f"**总耗时**: {self._format_duration(self.summary.elapsed_seconds)}",
            "",
            "## AI API 用量",
            "",
            f"- **API 调用**: {self.api_calls} 次",
            f"- **Token 用量**: {self.prompt_tokens:,} 输入 / {self.completion_tokens:,} 输出 / {self.total_tokens:,} 总计",
            f"- **预估费用**: ¥{self.total_cost:.4f}",
            "",
            "### 调用明细",
            "",
            "| 序号 | 阶段 | 模型 | 输入 | 输出 | 总计 |",
            "|-----|-----|------|-----|-----|-----|",
        ]
        
        for i, r in enumerate(self.records, 1):
            lines.append(f"| {i} | {r.stage} | {r.model} | {r.prompt_tokens:,} | {r.completion_tokens:,} | {r.total_tokens:,} |")
        
        lines.extend([
            "",
            "## 价格配置",
            "",
            f"- 输入: ¥{settings.llm_price_input_per_1m} / 百万 tokens",
            f"- 输出: ¥{settings.llm_price_output_per_1m} / 百万 tokens",
        ])
        
        return "\n".join(lines)
    
    def save_summary_md(self, path: Path) -> None:
        """保存 summary.md 文件."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.generate_summary_md(), encoding="utf-8")
    
    def _format_duration(self, seconds: float) -> str:
        """格式化时长."""
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            return f"{seconds/60:.1f}分钟"
        else:
            return f"{seconds/3600:.1f}小时"
    
    def reset(self) -> None:
        """重置统计."""
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.api_calls = 0
        self.records = []
        self.summary = ProcessingSummary()


# 全局统计实例
_global_stats: Optional[UsageStats] = None


def get_stats() -> UsageStats:
    """获取全局统计实例."""
    global _global_stats
    if _global_stats is None:
        _global_stats = UsageStats()
    return _global_stats


def reset_stats() -> None:
    """重置全局统计."""
    global _global_stats
    _global_stats = UsageStats()
