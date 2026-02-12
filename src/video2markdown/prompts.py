"""Prompt management with YAML Frontmatter support.

This module implements the Prompt Loader pattern from ai-api-integration skill,
providing file-based prompt management with version control.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any

import yaml


@dataclass
class Prompt:
    """A loaded prompt with metadata and content."""
    
    name: str
    content: str
    metadata: dict[str, Any]
    
    def render(self, **kwargs) -> list[dict]:
        """Render as OpenAI messages format.
        
        Args:
            **kwargs: Template variables to substitute
            
        Returns:
            List of message dicts with role and content
        """
        content = self.content.format(**kwargs)
        return [{"role": "system", "content": content}]
    
    def get_api_params(self) -> dict:
        """Get API parameters from metadata.
        
        Returns:
            Dict of API parameters like temperature, max_tokens
        """
        return self.metadata.get("parameters", {})
    
    def get_user_template(self) -> Optional[str]:
        """Get user message template if defined in metadata.
        
        Returns:
            User message template string or None
        """
        return self.metadata.get("user_template")
    
    def render_messages(self, user_content: Optional[str] = None, **kwargs) -> list[dict]:
        """Render complete messages including system and user.
        
        Args:
            user_content: Direct user message content
            **kwargs: Template variables for both system and user templates
            
        Returns:
            List of message dicts for OpenAI API
        """
        messages = []
        
        # System message
        if self.content:
            system_content = self.content.format(**kwargs)
            messages.append({"role": "system", "content": system_content})
        
        # User message
        user_template = self.get_user_template()
        if user_content:
            messages.append({"role": "user", "content": user_content})
        elif user_template:
            user_content = user_template.format(**kwargs)
            messages.append({"role": "user", "content": user_content})
        
        return messages


class PromptLoader:
    """Load and manage prompt files with YAML Frontmatter.
    
    Supports model-specific prompt versions and template rendering.
    
    Example:
        loader = PromptLoader("prompts")
        
        # Load with automatic model version selection
        prompt = loader.load("document/generation", model="kimi-k2.5")
        
        # Render with template variables
        messages = prompt.render_messages(
            title="My Video",
            duration=600,
            user_content=json.dumps(data)
        )
    """
    
    def __init__(self, prompts_dir: str | Path):
        """Initialize the prompt loader.
        
        Args:
            prompts_dir: Directory containing prompt files
        """
        self.prompts_dir = Path(prompts_dir)
        if not self.prompts_dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self.prompts_dir}")
    
    def load(self, path: str, model: Optional[str] = None) -> Prompt:
        """Load a prompt file with model-specific version selection.
        
        Version selection priority:
        1. {path}.{model}.md - exact match (e.g., generation.kimi-k2.5.md)
        2. {path}.{prefix}.md - prefix match (e.g., generation.kimi.md)
        3. {path}.md - default version
        
        Args:
            path: Relative path without extension (e.g., "document/generation")
            model: Model name for version selection (e.g., "kimi-k2.5")
            
        Returns:
            Loaded Prompt object
            
        Raises:
            FileNotFoundError: If no suitable prompt file found
        """
        path = path.replace(".", "/")  # Allow dot notation
        base_path = self.prompts_dir / path
        
        # Try versioned files in priority order
        candidates = []
        if model:
            candidates.append(f"{base_path}.{model}.md")
            # Try prefix match (e.g., "kimi-k2.5" -> "kimi")
            if "-" in model:
                prefix = model.split("-")[0]
                candidates.append(f"{base_path}.{prefix}.md")
        candidates.append(f"{base_path}.md")
        
        # Find first existing file
        for candidate in candidates:
            candidate_path = Path(candidate)
            if candidate_path.exists():
                return self._parse_file(candidate_path)
        
        # Try directory/index pattern
        for candidate in candidates:
            candidate_path = Path(candidate.replace(".md", "/index.md"))
            if candidate_path.exists():
                return self._parse_file(candidate_path)
        
        raise FileNotFoundError(
            f"Prompt not found: {path}\n"
            f"Tried: {', '.join(candidates)}"
        )
    
    def _parse_file(self, file_path: Path) -> Prompt:
        """Parse a prompt file with YAML Frontmatter.
        
        Args:
            file_path: Path to .md file
            
        Returns:
            Parsed Prompt object
        """
        content = file_path.read_text(encoding="utf-8")
        
        # Parse YAML Frontmatter
        frontmatter_match = re.match(
            r'^---\s*\n(.*?)\n---\s*\n?(.*)$',
            content,
            re.DOTALL
        )
        
        if frontmatter_match:
            yaml_content = frontmatter_match.group(1)
            body_content = frontmatter_match.group(2).strip()
            metadata = yaml.safe_load(yaml_content) or {}
        else:
            # No frontmatter, treat entire content as body
            metadata = {}
            body_content = content.strip()
        
        # Extract name from metadata or filename
        name = metadata.get("name", file_path.stem.split(".")[0])
        
        return Prompt(
            name=name,
            content=body_content,
            metadata=metadata
        )
    
    def list_prompts(self) -> list[Path]:
        """List all available prompt files.
        
        Returns:
            List of prompt file paths (relative to prompts_dir)
        """
        prompts = []
        for file_path in self.prompts_dir.rglob("*.md"):
            if file_path.name == "README.md":
                continue
            prompts.append(file_path.relative_to(self.prompts_dir))
        return sorted(prompts)
    
    def get_info(self, path: str, model: Optional[str] = None) -> dict:
        """Get metadata info about a prompt without loading full content.
        
        Args:
            path: Prompt path
            model: Model name for version selection
            
        Returns:
            Dict with name, version, description, etc.
        """
        prompt = self.load(path, model)
        return {
            "name": prompt.name,
            "version": prompt.metadata.get("version", "unknown"),
            "description": prompt.metadata.get("description", ""),
            "models": prompt.metadata.get("models", []),
            "variables": prompt.metadata.get("variables", []),
            "parameters": prompt.get_api_params(),
        }


# Convenience functions for backward compatibility
def load_prompt(prompt_path: str | Path, model: Optional[str] = None) -> str:
    """Load a prompt file content (legacy compatibility).
    
    Args:
        prompt_path: Path to prompt file
        model: Model name (for version selection)
        
    Returns:
        Raw prompt content (without frontmatter)
    """
    path = Path(prompt_path)
    
    # If just a filename, look in prompts dir
    if len(path.parts) == 1:
        path = Path("prompts") / path
    
    loader = PromptLoader(path.parent)
    prompt = loader.load(path.stem, model)
    return prompt.content


# Global loader instance (initialized lazily)
_loader: Optional[PromptLoader] = None


def get_loader() -> PromptLoader:
    """Get or create global prompt loader.
    
    Returns:
        Global PromptLoader instance
    """
    global _loader
    if _loader is None:
        _loader = PromptLoader("prompts")
    return _loader
