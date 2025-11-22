"""
Social Media Link Extraction Service
Handles TikTok, Instagram Reels, and YouTube links
"""
import yt_dlp
import re
import os
import logging
from typing import Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SocialMediaResult:
    platform: str  # "tiktok", "instagram", "youtube"
    video_id: str
    title: str
    audio_path: str
    thumbnail: Optional[str] = None


def is_tiktok_link(url: str) -> bool:
    """Check if URL is a TikTok link"""
    if not url or not isinstance(url, str):
        return False
    url_lower = url.lower().strip()
    patterns = [
        r'tiktok\.com',
        r'vm\.tiktok\.com',
        r'vt\.tiktok\.com',
        r'tiktok\.com/@',
        r'tiktok\.com/t/',
    ]
    return any(re.search(pattern, url_lower) for pattern in patterns)


def is_instagram_link(url: str) -> bool:
    """Check if URL is an Instagram link (Reels or regular post)"""
    if not url or not isinstance(url, str):
        return False
    url_lower = url.lower().strip()
    patterns = [
        r'instagram\.com/(p|reel|tv)/',
        r'instagr\.am/(p|reel|tv)/',
        r'instagram\.com/p/',
        r'instagram\.com/reel/',
        r'instagram\.com/tv/',
        r'www\.instagram\.com/(p|reel|tv)/',
    ]
    return any(re.search(pattern, url_lower) for pattern in patterns)


def is_youtube_link(url: str) -> bool:
    """Check if URL is a YouTube link"""
    patterns = [
        r'youtube\.com/watch',
        r'youtu\.be/',
        r'youtube\.com/shorts/',
    ]
    return any(re.search(pattern, url.lower()) for pattern in patterns)


def extract_audio_from_url(url: str, output_dir: str = "./data/downloads") -> Optional[SocialMediaResult]:
    """
    Extract audio from TikTok, Instagram, or YouTube link
    Returns SocialMediaResult with audio file path
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Determine platform
    if is_tiktok_link(url):
        platform = "tiktok"
    elif is_instagram_link(url):
        platform = "instagram"
    elif is_youtube_link(url):
        platform = "youtube"
    else:
        return None
    
    # Extract video ID for filename
    video_id = extract_video_id(url, platform)
    if not video_id:
        video_id = "unknown"
    
    output_path = os.path.join(output_dir, f"{platform}_{video_id}.mp3")
    
    # Check if file already exists (cache)
    if os.path.exists(output_path):
        # Get title from existing file or use default
        return SocialMediaResult(
            platform=platform,
            video_id=video_id,
            title="Cached Audio",
            audio_path=output_path,
            thumbnail=None
        )
    
    # Use yt-dlp to download audio (works with TikTok, Instagram, YouTube)
    # Optimized for speed
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=opus]/bestaudio/best",
        "outtmpl": output_path.replace(".mp3", ".%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        # Speed optimizations
        "noplaylist": True,
        "nocheckcertificate": True,
        "fragment_retries": 3,
        "retries": 3,
        "concurrent_fragments": 4,
        "writesubtitles": False,
        "writeautomaticsub": False,
        "writethumbnail": False,
        "writeinfojson": False,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",  # Lower quality for speed
            }
        ],
        "postprocessor_args": {
            "ffmpeg": ["-threads", "4", "-preset", "fast"]
        },
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Get title
            title = info.get("title", "Unknown")
            
            # Get thumbnail
            thumbnail = info.get("thumbnail") or info.get("thumbnails", [{}])[0].get("url") if info.get("thumbnails") else None
            
            # Find the actual output file (yt-dlp may change extension)
            base_path = output_path.replace(".mp3", "")
            actual_path = None
            for ext in [".m4a", ".opus", ".webm", ".mp3"]:
                if os.path.exists(base_path + ext):
                    actual_path = base_path + ext
                    break
            
            # If not MP3, convert it
            if actual_path and not actual_path.endswith('.mp3'):
                import subprocess
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", actual_path,
                        "-acodec", "libmp3lame", "-ab", "128k",
                        "-threads", "4", "-preset", "fast",
                        output_path
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=120
                )
                # Remove original file
                try:
                    os.remove(actual_path)
                except:
                    pass
                actual_path = output_path
            elif actual_path:
                output_path = actual_path
            
            # Verify file exists and is not empty
            if not os.path.exists(output_path):
                # Try to find with any extension
                base_path = output_path.replace(".mp3", "")
                found = False
                for ext in [".m4a", ".opus", ".webm", ".mp3"]:
                    if os.path.exists(base_path + ext):
                        output_path = base_path + ext
                        found = True
                        break
                if not found:
                    raise Exception(f"Downloaded file not found: {output_path}")
            
            # Check file size
            file_size = os.path.getsize(output_path)
            if file_size == 0:
                raise Exception(f"Downloaded file is empty: {output_path}")
            
            return SocialMediaResult(
                platform=platform,
                video_id=video_id,
                title=title,
                audio_path=output_path,
                thumbnail=thumbnail
            )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error extracting audio from {url}: {e}", exc_info=True)
        return None


def extract_video_id(url: str, platform: str) -> Optional[str]:
    """Extract video ID from URL"""
    if platform == "youtube":
        # YouTube: extract v= parameter or from youtu.be
        match = re.search(r'(?:v=|/)([a-zA-Z0-9_-]{11})', url)
        return match.group(1) if match else None
    elif platform == "tiktok":
        # TikTok: extract from URL path
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)
        # Try to get from shortened links
        match = re.search(r'/([a-zA-Z0-9]+)', url.split('?')[0])
        return match.group(1) if match else None
    elif platform == "instagram":
        # Instagram: extract post/reel ID
        match = re.search(r'/(p|reel|tv)/([a-zA-Z0-9_-]+)', url)
        return match.group(2) if match else None
    return None

