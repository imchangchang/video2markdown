"""Configuration management.

按优先级读取配置:
1. 环境变量 (VIDEO2MD_*)
2. .env 文件
3. 默认值
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_project_root() -> Path:
    """获取项目根目录."""
    # 从环境变量
    if root := os.environ.get("VIDEO2MD_ROOT"):
        return Path(root)
    
    # 从当前工作目录向上查找
    current = Path.cwd()
    for path in [current, *current.parents]:
        if (path / ".env").exists() or (path / "prompts").exists():
            return path
    
    # 从本文件位置推导
    this_file = Path(__file__).resolve()
    return this_file.parent.parent.parent


PROJECT_ROOT = get_project_root()


class Settings(BaseSettings):
    """应用配置."""

    model_config = SettingsConfigDict(
        env_prefix="VIDEO2MD_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # API 配置
    api_key: str = Field(..., description="LLM API Key")
    base_url: str = Field(default="https://api.moonshot.cn/v1")
    model: str = Field(default="kimi-k2.5")
    vision_model: str = Field(default="kimi-k2.5")
    
    # 输出语言配置
    output_language: str = Field(default="zh", description="输出语言: zh, en, ja, ko 等")

    # Whisper 配置
    asr_provider: str = Field(default="local", description="ASR 提供商: local 或 openai")
    whisper_model: str = Field(default="base", description="Whisper 模型名称 (tiny/base/small/medium) 或完整路径")
    whisper_local_model: str = Field(default="", description="本地 Whisper 模型路径")

    # 并发配置
    api_max_concurrency: int = Field(default=5, description="LLM API 最大并发数")
    image_max_concurrency: int = Field(default=3, description="图片分析并发数")
    
    # 处理参数
    keyframe_interval: float = Field(default=30.0)
    scene_threshold: float = Field(default=0.3)
    
    # 路径
    output_dir: Path = Field(default=PROJECT_ROOT / "test_outputs" / "results")
    temp_dir: Path = Field(default=PROJECT_ROOT / "test_outputs" / "temp")
    prompts_dir: Path = Field(default=PROJECT_ROOT / "prompts")

    # LLM API 定价（单位：元/百万 tokens）
    llm_price_input_per_1m: float = Field(default=4.8, description="输入 token 价格（元/百万）")
    llm_price_output_per_1m: float = Field(default=20.0, description="输出 token 价格（元/百万）")
    
    # 向后兼容：支持旧的 KIMI_ 前缀配置
    def model_post_init(self, __context):
        """向后兼容处理."""
        import os
        # 如果新配置为空，尝试读取旧配置
        if not self.api_key or self.api_key == "your-api-key":
            if old_key := os.environ.get("KIMI_API_KEY"):
                self.api_key = old_key
        if self.model == "kimi-k2.5":
            if old_model := os.environ.get("KIMI_MODEL"):
                self.model = old_model

    def get_client_kwargs(self) -> dict:
        """获取 OpenAI 客户端参数."""
        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
        }

    def resolve_whisper_cli(self) -> Optional[Path]:
        """查找 whisper-cli 可执行文件."""
        candidates = [
            # 项目内置版本（优先）- 使用 wrapper 脚本处理动态库
            PROJECT_ROOT / "tools" / "whisper-cpp" / "whisper-cli-wrapper",
            # 项目内置版本 - 直接二进制（需手动设置 LD_LIBRARY_PATH）
            PROJECT_ROOT / "tools" / "whisper-cpp" / "whisper-cli",
            # 向后兼容：CMake 构建版本
            PROJECT_ROOT / "whisper.cpp" / "build" / "bin" / "whisper-cli",
            # 项目根目录
            PROJECT_ROOT / "whisper-cli",
            PROJECT_ROOT / "whisper-cpp",
            # 系统路径
            Path("/usr/local/bin/whisper-cli"),
            Path("/usr/bin/whisper-cli"),
        ]
        
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate.resolve()
        
        return None

    def resolve_whisper_model_path(self) -> Optional[Path]:
        """解析 Whisper 模型路径.
        
        搜索顺序:
        1. whisper_local_model（如果配置了完整路径）
        2. whisper_model 配置（base/small/medium 等）
        3. models/ggml-{model}.bin
        4. models/ggml-{model}-q8_0.bin（量化版本）
        """
        # 优先使用 whisper_local_model（如果配置了）
        if self.whisper_local_model:
            path = Path(self.whisper_local_model)
            if path.exists() and path.is_file():
                return path.resolve()
            # 尝试在项目根目录下查找
            full_path = PROJECT_ROOT / self.whisper_local_model
            if full_path.exists() and full_path.is_file():
                return full_path.resolve()
        
        model = self.whisper_model
        
        # 如果是完整路径且存在
        path = Path(model)
        if path.exists() and path.is_file():
            return path.resolve()
        
        # 尝试常见位置（多种命名格式）
        candidates = [
            # 直接路径
            PROJECT_ROOT / model,
            # models/ 目录（项目根目录）
            PROJECT_ROOT / "models" / model,
            PROJECT_ROOT / "models" / f"ggml-{model}.bin",
            PROJECT_ROOT / "models" / f"ggml-{model}-q8_0.bin",  # 量化版本
            # whisper.cpp/models/ 目录
            PROJECT_ROOT / "whisper.cpp" / "models" / model,
            PROJECT_ROOT / "whisper.cpp" / "models" / f"ggml-{model}.bin",
            PROJECT_ROOT / "whisper.cpp" / "models" / f"ggml-{model}-q8_0.bin",
            PROJECT_ROOT / "whisper.cpp" / "models" / f"for-tests-ggml-{model}.bin",
        ]
        
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate.resolve()
        
        return None


settings = Settings()
