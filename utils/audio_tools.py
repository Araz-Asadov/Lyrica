"""
Audio processing utilities for music recognition
"""
import os
import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def extract_audio_from_video(
    video_path: str,
    output_path: Optional[str] = None,
    duration: Optional[int] = None,
    start_time: int = 0
) -> Optional[str]:
    """
    Extract audio from video file using FFmpeg.
    
    Args:
        video_path: Path to video file
        output_path: Output audio file path (optional)
        duration: Extract only first N seconds (optional)
        start_time: Start time in seconds (default: 0)
    
    Returns:
        Path to extracted audio file or None on error
    """
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: {video_path}")
        return None
    
    if output_path is None:
        output_path = os.path.join(
            tempfile.gettempdir(),
            f"audio_{os.path.basename(video_path)}.wav"
        )
    
    # FFmpeg command for audio extraction
    # Format: 16-bit PCM WAV, mono, 44.1 kHz (optimal for recognition)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # 16-bit PCM
        "-ar", "44100",  # 44.1 kHz sample rate
        "-ac", "1",  # Mono
    ]
    
    if start_time > 0:
        cmd.extend(["-ss", str(start_time)])
    
    if duration:
        cmd.extend(["-t", str(duration)])
    
    cmd.append(output_path)
    
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg error: {e}")
        return None
    except FileNotFoundError:
        logger.error("FFmpeg not found")
        return None


def convert_audio_format(
    input_path: str,
    output_path: Optional[str] = None,
    format: str = "wav",
    sample_rate: int = 44100,
    channels: int = 1
) -> Optional[str]:
    """
    Convert audio file to specified format.
    
    Args:
        input_path: Input audio file
        output_path: Output file path (optional)
        format: Output format (wav, mp3, etc.)
        sample_rate: Sample rate in Hz
        channels: Number of channels (1=mono, 2=stereo)
    
    Returns:
        Path to converted file or None on error
    """
    if not os.path.exists(input_path):
        logger.error(f"Input file not found: {input_path}")
        return None
    
    if output_path is None:
        base = os.path.splitext(input_path)[0]
        output_path = f"{base}.{format}"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-ar", str(sample_rate),
        "-ac", str(channels),
    ]
    
    if format == "wav":
        cmd.extend(["-acodec", "pcm_s16le"])
    elif format == "mp3":
        cmd.extend(["-acodec", "libmp3lame", "-q:a", "4"])
    
    cmd.append(output_path)
    
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg conversion error: {e}")
        return None
    except FileNotFoundError:
        logger.error("FFmpeg not found")
        return None


def extract_audio_segment(
    audio_path: str,
    start_time: int = 0,
    duration: int = 30,
    output_path: Optional[str] = None
) -> Optional[str]:
    """
    Extract a segment from audio file (useful for recognition).
    
    Args:
        audio_path: Input audio file
        start_time: Start time in seconds
        duration: Duration in seconds
        output_path: Output file path (optional)
    
    Returns:
        Path to extracted segment or None on error
    """
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return None
    
    if output_path is None:
        base = os.path.splitext(audio_path)[0]
        output_path = f"{base}_segment_{start_time}_{duration}.wav"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", audio_path,
        "-ss", str(start_time),
        "-t", str(duration),
        "-acodec", "copy",
        output_path
    ]
    
    try:
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"FFmpeg segment extraction error: {e}")
        return None
    except FileNotFoundError:
        logger.error("FFmpeg not found")
        return None


def get_audio_duration(audio_path: str) -> Optional[int]:
    """
    Get audio file duration in seconds using ffprobe.
    
    Args:
        audio_path: Path to audio file
    
    Returns:
        Duration in seconds (rounded to int) or None on error
    """
    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return None
    
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        audio_path
    ]
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        duration_str = result.stdout.strip()
        if duration_str:
            duration_float = float(duration_str)
            return int(round(duration_float))
        return None
    except subprocess.CalledProcessError as e:
        logger.warning(f"ffprobe error for {audio_path}: {e}")
        return None
    except (ValueError, FileNotFoundError) as e:
        logger.warning(f"Error getting duration for {audio_path}: {e}")
        return None

