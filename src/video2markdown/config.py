"""Configuration management for Video2Markdown."""

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_prefix="KIMI_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # API Configuration
    api_key: str = Field(..., description="Kimi API key")
    base_url: str = Field(
        default="https://api.moonshot.cn/v1",
        description="Kimi API base URL",
    )
    model: str = Field(
        default="kimi-k2.5",
        description="Default model for text generation",
    )
    vision_model: str = Field(
        default="kimi-k2.5",
        description="Model for vision tasks",
    )

    # Video Processing
    scene_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Scene change detection threshold (higher = fewer scenes)",
    )
    min_scene_duration: float = Field(
        default=1.0,
        ge=0.0,
        description="Minimum scene duration in seconds",
    )
    max_keyframes: int = Field(
        default=20,
        ge=1,
        le=200,
        description="Maximum number of keyframes to extract",
    )
    frame_quality: int = Field(
        default=85,
        ge=1,
        le=100,
        description="JPEG quality for extracted frames",
    )

    # Audio Processing
    audio_sample_rate: int = Field(
        default=16000,
        description="Audio sample rate for ASR",
    )
    audio_format: str = Field(
        default="wav",
        description="Audio format for extraction",
    )
    
    # Whisper ASR Configuration
    asr_provider: str = Field(
        default="local",
        description="ASR provider: local, openai, or kimi",
    )
    whisper_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for Whisper (defaults to KIMI_API_KEY)",
    )
    whisper_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Whisper API base URL",
    )
    whisper_model: str = Field(
        default="whisper-1",
        description="Whisper API model name",
    )
    whisper_local_model: str = Field(
        default="base",
        description="Local Whisper model size: tiny, base, small, medium, large",
    )
    whisper_language: Optional[str] = Field(
        default="zh",
        description="Language code for Whisper transcription",
    )

    # Image Processing
    max_image_size: int = Field(
        default=1024,
        ge=256,
        le=2048,
        description="Max dimension for images sent to API",
    )
    blur_threshold: float = Field(
        default=100.0,
        ge=0.0,
        description="Blur detection threshold (lower is blurrier)",
    )

    # Output
    temp_dir: Path = Field(
        default=Path("./testbench/output/temp"),
        description="Temporary directory for processing",
    )
    output_dir: Path = Field(
        default=Path("./testbench/output"),
        description="Default output directory",
    )

    # Concurrency
    max_workers: int = Field(
        default=4,
        ge=1,
        le=10,
        description="Maximum concurrent workers for API calls",
    )
    request_timeout: int = Field(
        default=120,
        ge=10,
        description="API request timeout in seconds",
    )

    def get_client_kwargs(self) -> dict:
        """Get kwargs for OpenAI client initialization."""
        return {
            "api_key": self.api_key,
            "base_url": self.base_url,
            "timeout": self.request_timeout,
        }


# Global settings instance
settings = Settings()
