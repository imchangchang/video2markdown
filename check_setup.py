#!/usr/bin/env python3
"""Check project setup and configuration."""

import sys
from pathlib import Path

def check_path(name: str, path: Path, should_exist: bool = True) -> bool:
    """Check if a path exists."""
    exists = path.exists()
    status = "✓" if exists == should_exist else "✗"
    exist_str = "exists" if exists else "MISSING"
    
    if should_exist:
        print(f"  {status} {name}: {path} ({exist_str})")
    else:
        print(f"  {status} {name}: {path} (should not exist)")
    
    return exists == should_exist


def main():
    """Run all checks."""
    print("=" * 60)
    print("Video2Markdown Setup Check")
    print("=" * 60)
    
    # Project root
    project_root = Path.cwd()
    print(f"\n📁 Project root: {project_root}")
    
    all_ok = True
    
    # Check directories
    print("\n📂 Directories:")
    all_ok &= check_path("src/video2markdown", project_root / "src" / "video2markdown")
    all_ok &= check_path("prompts", project_root / "prompts")
    all_ok &= check_path("whisper.cpp", project_root / "whisper.cpp")
    all_ok &= check_path("testbench/input", project_root / "testbench" / "input")
    all_ok &= check_path("testbench/output", project_root / "testbench" / "output")
    
    # Check key files
    print("\n📄 Key files:")
    all_ok &= check_path(".env", project_root / ".env")
    all_ok &= check_path("whisper-cpp executable", project_root / "whisper-cpp")
    all_ok &= check_path("prompts/document_generation.md", project_root / "prompts" / "document_generation.md")
    
    # Check whisper models
    print("\n🎙️ Whisper models:")
    models_dir = project_root / "whisper.cpp" / "models"
    if models_dir.exists():
        models = list(models_dir.glob("*.bin"))
        if models:
            print(f"  ✓ Found {len(models)} model files:")
            for m in sorted(models)[:5]:  # Show first 5
                size_mb = m.stat().st_size / (1024 * 1024)
                print(f"    - {m.name} ({size_mb:.1f} MB)")
            if len(models) > 5:
                print(f"    ... and {len(models) - 5} more")
        else:
            print(f"  ✗ No .bin model files found in {models_dir}")
            all_ok = False
    else:
        print(f"  ✗ Models directory not found: {models_dir}")
        all_ok = False
    
    # Check Python imports
    print("\n🐍 Python environment:")
    try:
        sys.path.insert(0, str(project_root / "src"))
        from video2markdown.config import settings, PROJECT_ROOT
        print(f"  ✓ Config module imported")
        print(f"    - PROJECT_ROOT: {PROJECT_ROOT}")
        print(f"    - prompts_dir: {settings.prompts_dir}")
        print(f"    - temp_dir: {settings.temp_dir}")
        print(f"    - output_dir: {settings.output_dir}")
        
        # Check if paths are resolved correctly
        if settings.prompts_dir.exists():
            print(f"  ✓ prompts_dir exists")
        else:
            print(f"  ✗ prompts_dir does not exist: {settings.prompts_dir}")
            all_ok = False
            
        # Check whisper model resolution
        resolved_model = settings.resolve_whisper_model_path()
        if resolved_model:
            print(f"  ✓ Whisper model resolved: {resolved_model}")
        else:
            print(f"  ⚠ No whisper model found (will need to download or configure)")
            
    except Exception as e:
        print(f"  ✗ Failed to import config: {e}")
        all_ok = False
    
    # Summary
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ All checks passed! Ready to test.")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
