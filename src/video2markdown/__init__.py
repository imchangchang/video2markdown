"""Video2Markdown - Convert videos to Markdown documents with AI-powered understanding."""

__version__ = "0.1.0"
version = __version__  # Alias for easier import
__all__ = ["DocumentGenerator", "VideoProcessor", "version"]

# Lazy imports to avoid dependency issues
def __getattr__(name):
    if name == "DocumentGenerator":
        from video2markdown.document import DocumentGenerator
        return DocumentGenerator
    if name == "VideoProcessor":
        from video2markdown.video import VideoProcessor
        return VideoProcessor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
