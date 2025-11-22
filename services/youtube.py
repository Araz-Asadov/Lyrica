"""
YouTube Search and Download Module
Production-ready implementation using youtube-search-python and yt-dlp

Features:
- Fast and reliable YouTube search using youtube-search-python
- High-quality audio download using yt-dlp
- Full async support with proper error handling
- Windows-compatible file paths
- Comprehensive logging
- No warnings or deprecated code
"""

import asyncio
import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

import yt_dlp
from youtubesearchpython import VideosSearch

logger = logging.getLogger(__name__)

# Thread pool executor for blocking operations (yt-dlp is not fully async)
_executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix="youtube_")


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================

class YouTubeError(Exception):
    """Base exception for YouTube operations"""
    pass


class NotFoundError(YouTubeError):
    """Raised when no search results are found"""
    pass


class DownloadError(YouTubeError):
    """Raised when download fails"""
    pass


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class YTResult:
    """
    YouTube search and download result
    
    Attributes:
        youtube_id: Video ID
        title: Video title (cleaned)
        artist: Extracted artist name
        duration: Video duration in seconds
        file_path: Path to downloaded audio file
        thumbnail: Thumbnail URL
    """
    youtube_id: str
    title: str
    artist: str
    duration: int
    file_path: str
    thumbnail: str


@dataclass
class SearchResult:
    """
    YouTube search result (before download)
    
    Attributes:
        video_id: Video ID
        title: Video title
        thumbnails: Dict with thumbnail URLs (default, medium, high)
        duration: Duration string (e.g., "3:45")
        views: View count string
        published_time: Published time string
    """
    video_id: str
    title: str
    thumbnails: Dict[str, str]
    duration: Optional[str] = None
    views: Optional[str] = None
    published_time: Optional[str] = None


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def extract_artist_from_title(title: str) -> tuple[str, str]:
    """
    Extract artist and song title from combined string
    
    Handles patterns like:
    - "Artist - Song"
    - "Artist: Song"
    - "Artist | Song"
    - "Artist - Song (Official Video)"
    
    Args:
        title: Combined title string
        
    Returns:
        Tuple of (artist, clean_title)
        If artist cannot be extracted, returns ("Unknown", title)
    """
    if not title or not isinstance(title, str):
        return "Unknown", title
    
    # Common patterns: "Artist - Song", "Artist: Song", "Artist | Song"
    patterns = [
        r"^(.+?)\s*[-–—]\s*(.+?)(?:\s*\([^)]*\))?\s*$",  # "Artist - Song (Official Video)"
        r"^(.+?)\s*:\s*(.+?)(?:\s*\([^)]*\))?\s*$",       # "Artist: Song (Official Video)"
        r"^(.+?)\s*\|\s*(.+?)(?:\s*\([^)]*\))?\s*$",      # "Artist | Song (Official Video)"
    ]
    
    for pattern in patterns:
        match = re.match(pattern, title.strip(), re.IGNORECASE)
        if match:
            artist = match.group(1).strip()
            song = match.group(2).strip()
            
            # Remove common suffixes
            artist = re.sub(r'\s*\([^)]*\)\s*$', '', artist)
            song = re.sub(r'\s*\([^)]*\)\s*$', '', song)
            
            # Validate: artist should be reasonable length and not empty
            if artist and song and len(artist) < 100 and len(song) > 0:
                return artist, song
    
    return "Unknown", title


def parse_duration(duration_str: Optional[str]) -> int:
    """
    Parse duration string to seconds
    
    Handles formats like:
    - "3:45" -> 225
    - "1:23:45" -> 5025
    - "PT3M45S" -> 225 (ISO 8601)
    
    Args:
        duration_str: Duration string
        
    Returns:
        Duration in seconds, 0 if parsing fails
    """
    if not duration_str:
        return 0
    
    try:
        # ISO 8601 format: PT3M45S or PT1H23M45S
        if duration_str.startswith("PT"):
            duration_str = duration_str[2:]  # Remove "PT" prefix
            hours = 0
            minutes = 0
            seconds = 0
            
            # Parse hours
            if "H" in duration_str:
                hour_part = duration_str.split("H")[0]
                hours = int(hour_part)
                duration_str = duration_str.split("H", 1)[1]
            
            # Parse minutes
            if "M" in duration_str:
                minute_part = duration_str.split("M")[0]
                minutes = int(minute_part)
                duration_str = duration_str.split("M", 1)[1]
            
            # Parse seconds
            if "S" in duration_str:
                second_part = duration_str.split("S")[0]
                seconds = int(second_part)
            
            return hours * 3600 + minutes * 60 + seconds
        
        # Simple format: "3:45" or "1:23:45"
        parts = duration_str.split(":")
        if len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # HH:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except Exception as e:
        logger.warning(f"Failed to parse duration '{duration_str}': {e}")
    
    return 0


def ensure_directory(path: str) -> None:
    """
    Ensure directory exists, create if it doesn't
    
    Args:
        path: Directory path
    """
    Path(path).mkdir(parents=True, exist_ok=True)


def clean_temp_files(base_path: str, keep_extension: str = ".mp3") -> None:
    """
    Remove temporary files created during download
    
    Args:
        base_path: Base path without extension
        keep_extension: Extension to keep (e.g., ".mp3")
    """
    temp_extensions = [".m4a", ".opus", ".webm", ".mp4"]
    
    for ext in temp_extensions:
        if ext == keep_extension:
            continue
        
        temp_file = base_path + ext
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logger.debug(f"Removed temp file: {temp_file}")
        except Exception as e:
            logger.warning(f"Failed to remove temp file {temp_file}: {e}")


# ============================================================
# YOUTUBE SEARCH
# ============================================================

async def search_youtube(query: str, limit: int = 1) -> Dict[str, Any]:
    """
    Search YouTube for videos using youtube-search-python
    
    This is the most reliable search method that doesn't break
    when YouTube updates its UI.
    
    Args:
        query: Search query string
        limit: Maximum number of results (default: 1 for best result)
        
    Returns:
        Dict containing:
        - video_id: YouTube video ID
        - title: Video title
        - thumbnails: Dict with thumbnail URLs
        - duration: Duration string
        - views: View count string
        - published_time: Published time string
        
    Raises:
        NotFoundError: If no results found
        YouTubeError: If search fails
    """
    if not query or not isinstance(query, str) or not query.strip():
        logger.error("Empty or invalid query provided")
        raise ValueError("Search query cannot be empty")
    
    query = query.strip()
    logger.info(f"Searching YouTube for: {query}")
    
    try:
        # Run search in thread pool (youtube-search-python is blocking)
        # Cannot use lambda in run_in_executor, need a proper function
        def _search_sync(q: str, lim: int):
            """Synchronous search wrapper"""
            return VideosSearch(q, limit=lim).result()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(_executor, _search_sync, query, limit)
        
        # Check if results exist
        if not result or "result" not in result or not result["result"]:
            logger.warning(f"No results found for query: {query}")
            raise NotFoundError(f"Mahnı tapılmadı: '{query}'")
        
        # Get first (most relevant) result
        video_data = result["result"][0]
        
        # Extract video information
        video_id = video_data.get("id", "")
        title = video_data.get("title", "")
        thumbnails = video_data.get("thumbnails", [{}])
        duration = video_data.get("duration", None)
        views = video_data.get("viewCount", {}).get("text", None)
        published_time = video_data.get("publishedTime", None)
        
        if not video_id:
            logger.error(f"Video ID not found in search result for: {query}")
            raise NotFoundError(f"Mahnı tapılmadı: '{query}'")
        
        # Build thumbnails dict
        thumbnails_dict = {}
        if thumbnails:
            # Get highest quality thumbnail
            if isinstance(thumbnails, list) and len(thumbnails) > 0:
                thumbnails_dict["high"] = thumbnails[0].get("url", "")
            elif isinstance(thumbnails, dict):
                thumbnails_dict = thumbnails
        
        # Fallback to default YouTube thumbnail if none found
        if not thumbnails_dict.get("high"):
            thumbnails_dict["high"] = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        thumbnails_dict["default"] = thumbnails_dict["high"]
        thumbnails_dict["medium"] = thumbnails_dict["high"]
        
        search_result = {
            "video_id": video_id,
            "title": title,
            "thumbnails": thumbnails_dict,
            "duration": duration,
            "views": views,
            "published_time": published_time,
        }
        
        logger.info(f"Found video: {title} (ID: {video_id})")
        return search_result
        
    except NotFoundError:
        raise
    except Exception as e:
        logger.error(f"Search error for query '{query}': {e}", exc_info=True)
        raise YouTubeError(f"Axtarış zamanı xəta baş verdi: {str(e)}")


# ============================================================
# AUDIO DOWNLOAD
# ============================================================

def _download_audio_sync(video_id: str, output_path: str) -> str:
    """
    Synchronous audio download using yt-dlp
    
    This function runs in a thread pool to avoid blocking the event loop.
    
    Args:
        video_id: YouTube video ID
        output_path: Desired output file path (will be adjusted based on format)
        
    Returns:
        Final file path to downloaded audio
        
    Raises:
        DownloadError: If download fails
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir:
        ensure_directory(output_dir)
    
    # Check if file already exists (cache)
    base_path = os.path.splitext(output_path)[0]
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        if file_size > 0:
            logger.info(f"Using cached file: {output_path} ({file_size} bytes)")
            return output_path
    
    # yt-dlp options optimized for audio quality and speed
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=opus]/bestaudio/best",
        "outtmpl": base_path + ".%(ext)s",
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        
        # Speed optimizations
        "noplaylist": True,
        "nocheckcertificate": True,
        "fragment_retries": 3,
        "retries": 3,
        "file_access_retries": 1,
        "concurrent_fragments": 4,
        
        # Skip unnecessary metadata
        "writesubtitles": False,
        "writeautomaticsub": False,
        "writethumbnail": False,
        "writeinfojson": False,
        "writedescription": False,
        "writecomments": False,
        
        # Audio post-processing
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",  # Higher quality for production
            }
        ],
        
        # FFmpeg options for faster conversion
        "postprocessor_args": {
            "ffmpeg": ["-threads", "4"]
        },
    }
    
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    logger.info(f"Downloading audio from: {video_url}")
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        
        # Find the actual output file (yt-dlp may change extension)
        actual_path = None
        for ext in [".mp3", ".m4a", ".opus", ".webm"]:
            candidate = base_path + ext
            if os.path.exists(candidate):
                actual_path = candidate
                break
        
        if not actual_path:
            raise DownloadError(f"Downloaded file not found. Expected: {output_path}")
        
        # Check file size
        file_size = os.path.getsize(actual_path)
        if file_size == 0:
            raise DownloadError(f"Downloaded file is empty: {actual_path}")
        
        # Convert to MP3 if needed
        if not actual_path.endswith(".mp3"):
            logger.info(f"Converting {actual_path} to MP3...")
            try:
                # Use FFmpeg to convert
                subprocess.run(
                    [
                        "ffmpeg",
                        "-y",  # Overwrite output file
                        "-i", actual_path,
                        "-acodec", "libmp3lame",
                        "-ab", "192k",  # Higher bitrate
                        "-threads", "4",
                        output_path
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=180
                )
                
                # Verify converted file exists and is not empty
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    # Remove original file
                    try:
                        os.remove(actual_path)
                    except Exception as e:
                        logger.warning(f"Failed to remove original file {actual_path}: {e}")
                    
                    actual_path = output_path
                    logger.info(f"Converted to MP3: {output_path}")
                else:
                    raise DownloadError("MP3 conversion failed: output file missing or empty")
                    
            except subprocess.TimeoutExpired:
                raise DownloadError("MP3 conversion timeout (file too large)")
            except subprocess.CalledProcessError as e:
                raise DownloadError(f"FFmpeg conversion failed: {e}")
            except FileNotFoundError:
                raise DownloadError("FFmpeg not found. Please install FFmpeg.")
        
        # Clean up any temporary files
        clean_temp_files(base_path, ".mp3")
        
        logger.info(f"Downloaded audio: {actual_path} ({os.path.getsize(actual_path)} bytes)")
        return actual_path
        
    except DownloadError:
        raise
    except Exception as e:
        logger.error(f"Download error for video {video_id}: {e}", exc_info=True)
        raise DownloadError(f"Audio yüklənərkən xəta: {str(e)}")


async def download_audio(video_id: str, output_path: Optional[str] = None) -> str:
    """
    Download audio from YouTube video using yt-dlp
    
    Downloads best quality audio and converts to MP3.
    
    Args:
        video_id: YouTube video ID
        output_path: Optional output file path. If not provided, uses default directory.
        
    Returns:
        Path to downloaded audio file (MP3)
        
    Raises:
        DownloadError: If download fails
        ValueError: If video_id is invalid
    """
    if not video_id or not isinstance(video_id, str):
        raise ValueError("Invalid video ID provided")
    
    video_id = video_id.strip()
    
    # Set default output path if not provided
    if not output_path:
        default_dir = os.path.join("data", "downloads")
        ensure_directory(default_dir)
        output_path = os.path.join(default_dir, f"{video_id}.mp3")
    
    # Normalize path for Windows compatibility
    output_path = os.path.normpath(output_path)
    
    # Run download in thread pool (yt-dlp is blocking)
    loop = asyncio.get_event_loop()
    try:
        file_path = await loop.run_in_executor(
            _executor,
            _download_audio_sync,
            video_id,
            output_path
        )
        return file_path
    except Exception as e:
        if isinstance(e, DownloadError):
            raise
        logger.error(f"Download error for {video_id}: {e}", exc_info=True)
        raise DownloadError(f"Audio yüklənə bilmədi: {str(e)}")


# ============================================================
# MAIN FUNCTION: SEARCH + DOWNLOAD
# ============================================================

async def get_audio(query: str, output_dir: Optional[str] = None) -> str:
    """
    Search YouTube and download audio in one step
    
    This is the main convenience function that combines search and download.
    
    Args:
        query: Search query string
        output_dir: Optional output directory. If not provided, uses default.
        
    Returns:
        Path to downloaded audio file (MP3)
        
    Raises:
        NotFoundError: If no search results found
        DownloadError: If download fails
        YouTubeError: For other errors
    """
    logger.info(f"get_audio called with query: {query}")
    
    # Search for video
    search_result = await search_youtube(query, limit=1)
    video_id = search_result["video_id"]
    
    # Set output path
    if output_dir:
        ensure_directory(output_dir)
        output_path = os.path.join(output_dir, f"{video_id}.mp3")
    else:
        default_dir = os.path.join("data", "downloads")
        ensure_directory(default_dir)
        output_path = os.path.join(default_dir, f"{video_id}.mp3")
    
    # Download audio
    file_path = await download_audio(video_id, output_path)
    
    return file_path


# ============================================================
# LEGACY COMPATIBILITY: search_and_download
# ============================================================

async def search_and_download(query: str) -> YTResult:
    """
    Search YouTube and download audio (legacy compatibility function)
    
    This function maintains backward compatibility with existing handlers.
    Returns YTResult dataclass used by the bot.
    
    Args:
        query: Search query string
        
    Returns:
        YTResult with all video information
        
    Raises:
        NotFoundError: If no search results found
        DownloadError: If download fails
        YouTubeError: For other errors
    """
    logger.info(f"search_and_download called with query: {query}")
    
    # Search for video
    search_result = await search_youtube(query, limit=1)
    video_id = search_result["video_id"]
    title = search_result["title"]
    thumbnails = search_result["thumbnails"]
    duration_str = search_result.get("duration")
    
    # Extract artist from title
    artist, clean_title = extract_artist_from_title(title)
    
    # Parse duration
    duration = parse_duration(duration_str)
    
    # Download audio
    default_dir = os.path.join("data", "downloads")
    ensure_directory(default_dir)
    output_path = os.path.join(default_dir, f"{video_id}.mp3")
    
    file_path = await download_audio(video_id, output_path)
    
    # Get thumbnail URL
    thumbnail = thumbnails.get("high", thumbnails.get("default", f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"))
    
    return YTResult(
        youtube_id=video_id,
        title=clean_title if clean_title else title,
        artist=artist if artist else "Unknown",
        duration=duration,
        file_path=file_path,
        thumbnail=thumbnail
    )
