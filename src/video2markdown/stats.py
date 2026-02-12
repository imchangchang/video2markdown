"""全局统计信息模块.

用于收集和汇总各阶段的 API 用量和费用.
"""

from typing import Optional

from video2markdown.config import settings


class UsageStats:
    """API 用量统计."""
    
    def __init__(self):
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.api_calls: int = 0
    
    @property
    def input_price(self) -> float:
        """输入 token 单价 (¥/token)."""
        return settings.price_input_per_1m / 1_000_000
    
    @property
    def output_price(self) -> float:
        """输出 token 单价 (¥/token)."""
        return settings.price_output_per_1m / 1_000_000
    
    def add(self, prompt_tokens: int, completion_tokens: int) -> None:
        """添加一次 API 调用的用量."""
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.api_calls += 1
    
    def add_from_response(self, response) -> None:
        """从 API 响应中提取用量信息."""
        if not hasattr(response, 'usage') or response.usage is None:
            return
        
        usage = response.usage
        prompt = getattr(usage, 'prompt_tokens', 0)
        completion = getattr(usage, 'completion_tokens', 0)
        self.add(prompt, completion)
    
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
    
    def summary(self) -> str:
        """格式化汇总信息."""
        lines = [
            "📊 AI API 用量汇总:",
            f"   API 调用: {self.api_calls} 次",
            f"   Token 用量: {self.prompt_tokens:,} 输入 / {self.completion_tokens:,} 输出 / {self.total_tokens:,} 总计",
            f"   预估费用: ¥{self.total_cost:.4f} (输入¥{self.input_cost:.4f} + 输出¥{self.output_cost:.4f})",
        ]
        return "\n".join(lines)
    
    def reset(self) -> None:
        """重置统计."""
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.api_calls = 0


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
