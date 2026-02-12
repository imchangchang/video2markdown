"""Configuration management.

按优先级读取配置:
1. 环境变量 (KIMI_*)
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
        env_prefix="KIMI_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # API 配置
    api_key: str = Field(..., description="Kimi API Key")
    base_url: str = Field(default="https://api.moonshot.cn/v1")
    model: str = Field(default="kimi-k2.5")
    vision_model: str = Field(default="kimi-k2.5")

    # Whisper 配置
    whisper_model: str = Field(default="base", description="Whisper 模型名称 (tiny/base/small/medium) 或完整路径")
    whisper_language: str = Field(default="zh")

    # 处理参数
    keyframe_interval: float = Field(default=30.0)
    scene_threshold: float = Field(default=0.3)
    
    # 路径
    output_dir: Path = Field(default=PROJECT_ROOT / "testbench" / "output")
    temp_dir: Path = Field(default=PROJECT_ROOT / "testbench" / "output" / "temp")

    def get_client_kwargs(self) -> dict:
        """获取 OpenAI 客户端参数."""
        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
        }

    def resolve_whisper_model(self) -> Optional[Path]:
        """解析 Whisper 模型路径.
        
        搜索顺序:
        1. 直接路径（如 models/ggml-medium-q8_0.bin）
        2. models/ggml-{model}.bin
        3. models/ggml-{model}-q8_0.bin（量化版本）
        4. whisper.cpp/models/ 下的相应文件
        """
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
