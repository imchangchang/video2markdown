"""Unit tests for prompt loader module.

Tests use small static fixtures and dynamic data.
No large files or external resources needed.
"""

import json
from pathlib import Path

import pytest

from video2markdown.prompts import Prompt, PromptLoader, get_loader


class TestPrompt:
    """Tests for Prompt dataclass."""
    
    def test_prompt_render_basic(self):
        """Test basic prompt rendering."""
        prompt = Prompt(
            name="test-prompt",
            content="Hello {name}!",
            metadata={}
        )
        
        messages = prompt.render(name="World")
        
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "Hello World!"
    
    def test_prompt_get_api_params(self):
        """Test extracting API parameters from metadata."""
        prompt = Prompt(
            name="test-prompt",
            content="Test",
            metadata={"parameters": {"temperature": 0.5, "max_tokens": 100}}
        )
        
        params = prompt.get_api_params()
        
        assert params["temperature"] == 0.5
        assert params["max_tokens"] == 100
    
    def test_prompt_render_messages_with_user_content(self):
        """Test rendering complete messages."""
        prompt = Prompt(
            name="test-prompt",
            content="System: {context}",
            metadata={"user_template": "User: {question}"}
        )
        
        messages = prompt.render_messages(
            context="test context",
            user_content="direct user message"
        )
        
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "System: test context"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "direct user message"


class TestPromptLoader:
    """Tests for PromptLoader class."""
    
    def test_load_existing_prompt(self, tmp_path):
        """Test loading an existing prompt file."""
        # Create a test prompt file
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        prompt_file = prompts_dir / "test.md"
        prompt_file.write_text("""---
name: test-prompt
version: "1.0.0"
---
Test prompt content.
""")
        
        loader = PromptLoader(prompts_dir)
        prompt = loader.load("test")
        
        assert prompt.name == "test-prompt"
        assert prompt.content == "Test prompt content."
        assert prompt.metadata["version"] == "1.0.0"
    
    def test_load_with_model_version(self, tmp_path):
        """Test model-specific prompt selection."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        # Create generic version
        (prompts_dir / "generation.md").write_text("""---
name: generation
---
Generic content.
""")
        
        # Create model-specific version
        (prompts_dir / "generation.kimi-k2.5.md").write_text("""---
name: generation-kimi
---
Kimi optimized content.
""")
        
        loader = PromptLoader(prompts_dir)
        
        # Should load model-specific version
        prompt = loader.load("generation", model="kimi-k2.5")
        assert prompt.name == "generation-kimi"
        
        # Should fallback to generic
        prompt = loader.load("generation", model="other-model")
        assert prompt.name == "generation"
    
    def test_load_nonexistent_prompt(self, tmp_path):
        """Test loading a non-existent prompt raises error."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        loader = PromptLoader(prompts_dir)
        
        with pytest.raises(FileNotFoundError):
            loader.load("nonexistent")
    
    def test_parse_without_frontmatter(self, tmp_path):
        """Test parsing prompt without YAML frontmatter."""
        prompts_dir = tmp_path / "prompts"
        prompts_dir.mkdir()
        
        prompt_file = prompts_dir / "simple.md"
        prompt_file.write_text("Simple content without frontmatter.")
        
        loader = PromptLoader(prompts_dir)
        prompt = loader.load("simple")
        
        assert prompt.name == "simple"
        assert prompt.content == "Simple content without frontmatter."


class TestGetLoader:
    """Tests for get_loader convenience function."""
    
    def test_get_loader_returns_loader(self):
        """Test get_loader returns a PromptLoader instance."""
        # This requires prompts/ directory to exist
        try:
            loader = get_loader()
            assert isinstance(loader, PromptLoader)
        except FileNotFoundError:
            pytest.skip("prompts/ directory not found")
    
    def test_get_loader_caches_instance(self):
        """Test get_loader caches the loader instance."""
        try:
            loader1 = get_loader()
            loader2 = get_loader()
            assert loader1 is loader2
        except FileNotFoundError:
            pytest.skip("prompts/ directory not found")


class TestPromptIntegration:
    """Integration tests using actual project prompts."""
    
    def test_load_document_generation_prompt(self):
        """Test loading the actual document generation prompt."""
        try:
            loader = get_loader()
            prompt = loader.load("document_generation", model="kimi-k2.5")
            
            assert prompt.name == "document-generation"
            assert "视频" in prompt.content or "文档" in prompt.content
            assert "version" in prompt.metadata
            assert "temperature" in prompt.get_api_params()
        except FileNotFoundError:
            pytest.skip("document_generation.md not found")
    
    def test_load_image_analysis_prompt(self):
        """Test loading the actual image analysis prompt."""
        try:
            loader = get_loader()
            prompt = loader.load("image_analysis")
            
            assert prompt.name == "image-analysis"
            assert "图片" in prompt.content or "分析" in prompt.content
        except FileNotFoundError:
            pytest.skip("image_analysis.md not found")
