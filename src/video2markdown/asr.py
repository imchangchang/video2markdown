"""Automatic Speech Recognition module using Whisper API or local model."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import opencc
from openai import OpenAI
from tqdm import tqdm

from video2markdown.config import settings
from video2markdown.audio import extract_audio, split_audio


# 简繁转换器（繁体转简体）
_t2s_converter = None

def get_t2s_converter():
    """获取繁体转简体转换器（延迟初始化）"""
    global _t2s_converter
    if _t2s_converter is None:
        _t2s_converter = opencc.OpenCC('t2s')  # 繁体转简体
    return _t2s_converter


def convert_to_simplified(text: str) -> str:
    """将繁体中文转换为简体中文"""
    if not text:
        return text
    try:
        converter = get_t2s_converter()
        return converter.convert(text)
    except Exception:
        # 转换失败时返回原文
        return text


@dataclass
class TranscriptSegment:
    """A segment of transcribed speech."""
    start: float
    end: float
    text: str
    
    def to_dict(self) -> dict:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
        }


class WhisperProcessor:
    """Speech-to-text processor using OpenAI Whisper API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """Initialize Whisper processor.
        
        Args:
            api_key: OpenAI API key (defaults to settings.whisper_api_key or settings.api_key)
            base_url: API base URL (defaults to settings.whisper_base_url)
            model: Whisper model name (defaults to settings.whisper_model)
        """
        # Use whisper-specific key or fall back to main API key
        key = api_key or settings.whisper_api_key or settings.api_key
        url = base_url or settings.whisper_base_url
        
        self.client = OpenAI(api_key=key, base_url=url)
        self.model = model or settings.whisper_model
    
    def transcribe_audio(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        response_format: str = "verbose_json",
    ) -> list[TranscriptSegment]:
        """Transcribe audio file using Whisper API.
        
        Args:
            audio_path: Path to audio file
            language: Language code (zh, en, etc.)
            response_format: Response format from Whisper API
            
        Returns:
            List of transcript segments
        """
        lang = language or settings.whisper_language
        
        # Check file size (Whisper API limit is 25MB)
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        
        if file_size_mb > 24:  # Slightly under 25MB limit
            print(f"  Audio file too large ({file_size_mb:.1f}MB), splitting...")
            return self._transcribe_large_audio(audio_path, lang)
        
        return self._transcribe_single(audio_path, lang, response_format, 0.0)
    
    def _transcribe_single(
        self,
        audio_path: Path,
        language: Optional[str],
        response_format: str,
        offset: float,
    ) -> list[TranscriptSegment]:
        """Transcribe a single audio file using Whisper API."""
        with open(audio_path, "rb") as audio_file:
            kwargs = {
                "model": self.model,
                "file": audio_file,
                "response_format": response_format,
            }
            
            if language:
                kwargs["language"] = language
            
            transcript = self.client.audio.transcriptions.create(**kwargs)
        
        # Parse response based on format
        if response_format == "verbose_json":
            return self._parse_verbose_json(transcript, offset)
        else:
            # Simple text format - treat as single segment
            text = transcript if isinstance(transcript, str) else transcript.text
            duration = self._get_audio_duration(audio_path)
            return [TranscriptSegment(
                start=offset,
                end=offset + duration,
                text=text,
            )]
    
    def _transcribe_large_audio(
        self,
        audio_path: Path,
        language: Optional[str],
    ) -> list[TranscriptSegment]:
        """Transcribe large audio by splitting into segments."""
        segments = split_audio(audio_path, segment_duration=300)  # 5 min chunks
        all_transcriptions = []
        
        offset = 0.0
        for seg_path in tqdm(segments, desc="Transcribing segments"):
            segs = self._transcribe_single(seg_path, language, "verbose_json", offset)
            all_transcriptions.extend(segs)
            
            # Update offset based on segment duration
            if segs:
                offset = segs[-1].end
        
        return all_transcriptions
    
    def _parse_verbose_json(self, transcript, offset: float) -> list[TranscriptSegment]:
        """Parse verbose_json response from Whisper API."""
        segments = []
        
        # Handle both object and dict response
        if hasattr(transcript, "segments"):
            raw_segments = transcript.segments
        elif isinstance(transcript, dict):
            raw_segments = transcript.get("segments", [])
        else:
            # Fallback: treat entire text as one segment
            text = transcript.text if hasattr(transcript, "text") else str(transcript)
            return [TranscriptSegment(start=offset, end=offset + 60, text=text)]
        
        for seg in raw_segments:
            if isinstance(seg, dict):
                segments.append(TranscriptSegment(
                    start=seg.get("start", 0) + offset,
                    end=seg.get("end", 0) + offset,
                    text=seg.get("text", "").strip(),
                ))
            else:
                segments.append(TranscriptSegment(
                    start=seg.start + offset if hasattr(seg, "start") else offset,
                    end=seg.end + offset if hasattr(seg, "end") else offset + 60,
                    text=seg.text.strip() if hasattr(seg, "text") else str(seg),
                ))
        
        return segments
    
    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    
    def process_video(
        self,
        video_path: Path,
        language: Optional[str] = None,
    ) -> list[TranscriptSegment]:
        """Process video file: extract audio and transcribe.
        
        Args:
            video_path: Path to video file
            language: Language for transcription
            
        Returns:
            List of transcript segments
        """
        print(f"Extracting audio from {video_path}...")
        audio_path = extract_audio(video_path)
        
        print("Transcribing audio with Whisper API...")
        return self.transcribe_audio(audio_path, language)


class LocalWhisperProcessor:
    """Local Whisper processor using faster-whisper or whisper.cpp."""
    
    def __init__(self, model_path: Optional[str] = None, model_size: str = "base"):
        """Initialize local Whisper processor.
        
        Args:
            model_path: Path to local model file or directory
            model_size: Model size for downloading (tiny, base, small, medium, large-v1, large-v2, large-v3)
        """
        self.model_path = model_path
        self.model_size = model_size
        self.model = None
        self._processor_type = None
        
        # Determine processor type based on model path
        if model_path:
            path = Path(model_path)
            if path.is_file() and path.suffix == ".bin":
                # GGML format (whisper.cpp)
                self._processor_type = "whisper_cpp"
            elif path.is_dir() or (path.is_file() and path.suffix in [".pt", ".pth"]):
                # PyTorch format (openai-whisper) or directory
                self._processor_type = "faster_whisper"
            else:
                # Try faster-whisper by default
                self._processor_type = "faster_whisper"
        else:
            self._processor_type = "faster_whisper"
    
    def _load_model(self):
        """Load the appropriate Whisper model."""
        if self._processor_type == "whisper_cpp":
            self._load_whisper_cpp()
        else:
            # Check if whisper-cpp CLI is available
            try:
                exe_path = self._find_whisper_cpp()
                print(f"Using whisper.cpp CLI: {exe_path}")
                self._processor_type = "whisper_cpp"
                self.model = "whisper_cpp_cli"
            except FileNotFoundError:
                self._load_faster_whisper()
    
    def _load_whisper_cpp(self):
        """Load whisper.cpp model."""
        try:
            # Try to use whisper-cpp-python if available
            from whisper_cpp_python import Whisper
            
            print(f"Loading whisper.cpp model: {self.model_path}...")
            self.model = Whisper(self.model_path)
            print(f"✓ Model loaded successfully")
        except ImportError:
            # Fall back to subprocess
            print(f"Using whisper.cpp CLI: {self.model_path}")
            self.model = "whisper_cpp_cli"
    
    def _load_faster_whisper(self):
        """Load faster-whisper model."""
        try:
            from faster_whisper import WhisperModel
            
            model_path = self.model_path or self.model_size
            print(f"Loading faster-whisper model: {model_path}...")
            
            # Use CPU with int8 quantization for faster inference
            self.model = WhisperModel(
                model_path,
                device="cpu",
                compute_type="int8",
                download_root=str(settings.temp_dir / "whisper_models"),
            )
            print(f"✓ Model loaded successfully")
        except ImportError:
            raise ImportError(
                "faster-whisper not installed. "
                "Run: pip install faster-whisper"
            )
    
    def transcribe_audio(
        self,
        audio_path: Path,
        language: Optional[str] = None,
    ) -> list[TranscriptSegment]:
        """Transcribe audio file using local Whisper model.
        
        Args:
            audio_path: Path to audio file
            language: Language code (zh, en, etc.)
            
        Returns:
            List of transcript segments
        """
        if self.model is None:
            self._load_model()
        
        lang = language or settings.whisper_language
        
        if self._processor_type == "whisper_cpp" and self.model == "whisper_cpp_cli":
            return self._transcribe_with_whisper_cpp_cli(audio_path, lang)
        elif self._processor_type == "whisper_cpp":
            return self._transcribe_with_whisper_cpp_python(audio_path, lang)
        else:
            return self._transcribe_with_faster_whisper(audio_path, lang)
    
    def _transcribe_with_faster_whisper(self, audio_path: Path, language: Optional[str]) -> list[TranscriptSegment]:
        """Transcribe using faster-whisper."""
        print(f"Transcribing with faster-whisper...")
        
        segments, info = self.model.transcribe(
            str(audio_path),
            language=language,
            task="transcribe",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )
        
        print(f"  Detected language: {info.language} (probability: {info.language_probability:.2f})")
        
        # Convert to TranscriptSegment
        transcript_segments = []
        for segment in tqdm(segments, desc="Processing segments"):
            transcript_segments.append(TranscriptSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text.strip(),
            ))
        
        return transcript_segments
    
    def _transcribe_with_whisper_cpp_python(self, audio_path: Path, language: Optional[str]) -> list[TranscriptSegment]:
        """Transcribe using whisper-cpp-python."""
        print(f"Transcribing with whisper.cpp...")
        
        result = self.model.transcribe(str(audio_path), language=language)
        
        transcript_segments = []
        for segment in result:
            transcript_segments.append(TranscriptSegment(
                start=segment.t0 / 100.0,  # Convert from centiseconds to seconds
                end=segment.t1 / 100.0,
                text=segment.text.strip(),
            ))
        
        return transcript_segments
    
    def _transcribe_with_whisper_cpp_cli(self, audio_path: Path, language: Optional[str]) -> list[TranscriptSegment]:
        """Transcribe using whisper.cpp CLI."""
        import json
        
        print(f"Transcribing with whisper.cpp CLI...")
        
        # Determine output path (whisper.cpp adds .json extension)
        output_json = audio_path.parent / f"{audio_path.stem}.wav.json"
        
        # Get model path (use default if not set)
        model_path = self.model_path or settings.whisper_local_model
        if not model_path or not Path(model_path).exists():
            raise FileNotFoundError(f"Whisper model not found: {model_path}. Please download a model from https://huggingface.co/ggerganov/whisper.cpp")
        
        try:
            # Find whisper-cpp executable
            whisper_cpp_exe = self._find_whisper_cpp()
            
            # Run whisper.cpp
            cmd = [
                str(whisper_cpp_exe),
                "-m", str(model_path),
                "-f", str(audio_path),
                "-oj",  # Output JSON
                "-of", str(audio_path),  # Output prefix (whisper.cpp adds extension)
            ]
            
            if language:
                cmd.extend(["-l", language])
            
            print(f"Running: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Parse output
            if not output_json.exists():
                # Try alternative path
                alt_output = Path(str(audio_path) + ".json")
                if alt_output.exists():
                    output_json = alt_output
                else:
                    raise FileNotFoundError(f"Output file not found: {output_json}")
            
            with open(output_json, "r") as f:
                data = json.load(f)
            
            transcript_segments = []
            for segment in data.get("transcription", []):
                transcript_segments.append(TranscriptSegment(
                    start=segment.get("offsets", {}).get("from", 0) / 1000.0,
                    end=segment.get("offsets", {}).get("to", 0) / 1000.0,
                    text=segment.get("text", "").strip(),
                ))
            
            return transcript_segments
        finally:
            # Cleanup output file
            output_json.unlink(missing_ok=True)
    
    def _find_whisper_cpp(self) -> Path:
        """Find whisper-cpp executable."""
        # Check common locations
        possible_paths = [
            Path("whisper-cpp"),  # Current directory
            Path(__file__).parent.parent.parent / "whisper-cpp",  # Project root
            Path("/usr/local/bin/whisper-cpp"),
            Path("/usr/bin/whisper-cpp"),
        ]
        
        for path in possible_paths:
            if path.exists() and path.is_file():
                return path.absolute()
        
        # Try which command
        try:
            result = subprocess.run(["which", "whisper-cpp"], capture_output=True, text=True, check=True)
            return Path(result.stdout.strip())
        except subprocess.CalledProcessError:
            pass
        
        raise FileNotFoundError(
            "whisper-cpp executable not found. "
            "Please install whisper.cpp from https://github.com/ggml-org/whisper.cpp"
        )
    
    def process_video(
        self,
        video_path: Path,
        language: Optional[str] = None,
    ) -> list[TranscriptSegment]:
        """Process video file: extract audio and transcribe.
        
        Args:
            video_path: Path to video file
            language: Language for transcription
            
        Returns:
            List of transcript segments
        """
        print(f"Extracting audio from {video_path}...")
        audio_path = extract_audio(video_path)
        
        print("Transcribing with local Whisper...")
        return self.transcribe_audio(audio_path, language)


class ASRProcessor:
    """ASR processor that routes to appropriate provider."""
    
    def __init__(self, provider: Optional[str] = None, local_model: Optional[str] = None):
        """Initialize ASR processor.
        
        Args:
            provider: ASR provider ('local', 'openai', 'kimi')
            local_model: Local model path or size
        """
        self.provider = provider or settings.asr_provider
        self.local_model = local_model or settings.whisper_local_model
        self._processor = None
    
    def _get_processor(self):
        """Get or create the appropriate processor."""
        if self._processor is None:
            if self.provider == "local":
                # Check if local_model is a path or a size
                model_path = None
                model_size = "base"
                
                if self.local_model:
                    if Path(self.local_model).exists():
                        model_path = self.local_model
                        print(f"Using local model at: {model_path}")
                    else:
                        model_size = self.local_model
                        print(f"Using local Whisper model size: {model_size}")
                
                self._processor = LocalWhisperProcessor(
                    model_path=model_path,
                    model_size=model_size,
                )
            elif self.provider == "openai":
                print(f"Using OpenAI Whisper API")
                self._processor = WhisperProcessor()
            else:
                raise ValueError(f"Unknown ASR provider: {self.provider}")
        return self._processor
    
    def process_video(
        self,
        video_path: Path,
        language: Optional[str] = "zh",
    ) -> list[TranscriptSegment]:
        """Process video file based on configured provider.
        
        Args:
            video_path: Path to video file
            language: Language for transcription
            
        Returns:
            List of transcript segments
        """
        try:
            processor = self._get_processor()
            return processor.process_video(video_path, language)
        except Exception as e:
            print(f"  Warning: ASR failed: {e}")
            print("  Falling back to placeholder transcription.")
            return self._fallback_transcription()
    
    def _fallback_transcription(self) -> list[TranscriptSegment]:
        """Generate fallback transcription when ASR is unavailable."""
        return [TranscriptSegment(
            start=0.0,
            end=60.0,
            text="[音频转录失败。请检查 ASR 配置或模型是否正确加载。]",
        )]


def format_timestamp(seconds: float) -> str:
    """Format seconds to HH:MM:SS.mmm."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def save_transcript_to_srt(
    segments: list[TranscriptSegment],
    output_path: Path,
) -> None:
    """Save transcript to SRT format.
    
    Args:
        segments: List of transcript segments
        output_path: Output SRT file path
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n")
            f.write(f"{format_timestamp(seg.start)} --> {format_timestamp(seg.end)}\n")
            f.write(f"{seg.text}\n\n")


def merge_short_segments(
    segments: list[TranscriptSegment],
    min_duration: float = 5.0,
    max_duration: float = 30.0,
) -> list[TranscriptSegment]:
    """Merge short segments and split long ones for better readability.
    
    Args:
        segments: Input segments
        min_duration: Minimum segment duration
        max_duration: Maximum segment duration
        
    Returns:
        Merged segments
    """
    if not segments:
        return []
    
    merged = []
    current = segments[0]
    
    for seg in segments[1:]:
        duration = seg.end - current.start
        
        if duration < min_duration:
            # Merge with current
            current = TranscriptSegment(
                start=current.start,
                end=seg.end,
                text=current.text + " " + seg.text,
            )
        else:
            # Save current and start new
            if duration > max_duration:
                # Split long segment
                mid = (current.start + current.end) / 2
                merged.append(TranscriptSegment(
                    start=current.start,
                    end=mid,
                    text=current.text[:len(current.text)//2],
                ))
                merged.append(TranscriptSegment(
                    start=mid,
                    end=current.end,
                    text=current.text[len(current.text)//2:],
                ))
            else:
                merged.append(current)
            current = seg
    
    merged.append(current)
    return merged
