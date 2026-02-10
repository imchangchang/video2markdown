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
        monkeypatch.setenv("KIMI_API_KEY", "test-key")
        
        settings = Settings()
        
        assert settings.api_key == "test-key"
        assert settings.base_url == "https://api.moonshot.cn/v1"
        assert settings.model == "kimi-k2.5"
        assert settings.scene_threshold == 0.4
        assert settings.max_keyframes == 20
        assert settings.audio_sample_rate == 16000
    
    def test_custom_values(self, monkeypatch):
        """Test custom configuration values."""
        monkeypatch.setenv("KIMI_API_KEY", "custom-key")
        monkeypatch.setenv("KIMI_SCENE_THRESHOLD", "0.5")
        monkeypatch.setenv("KIMI_MAX_KEYFRAMES", "100")
        
        settings = Settings()
        
        assert settings.api_key == "custom-key"
        assert settings.scene_threshold == 0.5
        assert settings.max_keyframes == 100
    
    def test_missing_api_key(self, monkeypatch):
        """Test that missing API key raises error."""
        monkeypatch.delenv("KIMI_API_KEY", raising=False)
        
        # Create settings without reading .env file
        with pytest.raises(ValidationError):
            Settings(_env_file=None)
    
    def test_client_kwargs(self, monkeypatch):
        """Test client kwargs generation."""
        monkeypatch.setenv("KIMI_API_KEY", "test-key")
        
        settings = Settings()
        kwargs = settings.get_client_kwargs()
        
        assert kwargs["api_key"] == "test-key"
        assert kwargs["base_url"] == "https://api.moonshot.cn/v1"
        assert "timeout" in kwargs
