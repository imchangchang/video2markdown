"""Tests for configuration module."""

import os
from pathlib import Path

import pytest
from pydantic import ValidationError

from video2markdown.config import Settings


class TestSettings:
    """Test settings configuration."""
    
    def test_default_values(self, monkeypatch):
        """Test default configuration values."""
        monkeypatch.setenv("VIDEO2MD_API_KEY", "test-key")
        
        # 禁用 .env 文件加载以隔离测试
        settings = Settings(_env_file=None)
        
        assert settings.api_key == "test-key"
        assert settings.base_url == "https://api.moonshot.cn/v1"
        assert settings.model == "kimi-k2.5"
        assert settings.scene_threshold == 0.3
        assert settings.keyframe_interval == 30.0
    
    def test_custom_values(self, monkeypatch):
        """Test custom configuration values."""
        monkeypatch.setenv("VIDEO2MD_API_KEY", "custom-key")
        monkeypatch.setenv("VIDEO2MD_SCENE_THRESHOLD", "0.5")
        monkeypatch.setenv("VIDEO2MD_KEYFRAME_INTERVAL", "60")
        
        # 禁用 .env 文件加载以隔离测试
        settings = Settings(_env_file=None)
        
        assert settings.api_key == "custom-key"
        assert settings.scene_threshold == 0.5
        assert settings.keyframe_interval == 60.0
    
    def test_missing_api_key(self, monkeypatch):
        """Test that missing API key raises error."""
        monkeypatch.delenv("VIDEO2MD_API_KEY", raising=False)
        monkeypatch.delenv("KIMI_API_KEY", raising=False)
        
        # Create settings without reading .env file
        with pytest.raises(ValidationError):
            Settings(_env_file=None)
    
    def test_client_kwargs(self, monkeypatch):
        """Test client kwargs generation."""
        monkeypatch.setenv("VIDEO2MD_API_KEY", "test-key")
        
        # 禁用 .env 文件加载以隔离测试
        settings = Settings(_env_file=None)
        kwargs = settings.get_client_kwargs()
        
        assert kwargs["api_key"] == "test-key"
        assert kwargs["base_url"] == "https://api.moonshot.cn/v1"
        assert "timeout" in kwargs
        assert kwargs["timeout"] == 120.0
        assert "max_retries" in kwargs
        assert kwargs["max_retries"] == 2
