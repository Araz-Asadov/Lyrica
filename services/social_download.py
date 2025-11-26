"""
Social Media Download Service
Downloads videos from TikTok, Instagram and extracts metadata
"""
import os
import asyncio
import yt_dlp
from dataclasses import dataclass
from typing import Optional
from config import settings
from utils.common import ensure_ffmpeg
import re


@dataclass
class SocialMediaResult:
    """Result from social media download"""
    platform: str  # "tiktok", "instagram"
    video_id: str
    title: str
    artist: str
    duration: int
    file_path: str
    thumbnail: str


def sanitize(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


def clean_social_media_title(title: str) -> str:
    """Clean TikTok/Instagram title from hashtags, usernames, emojis, etc."""
    # Remove hashtags
    title = re.sub(r'#\w+', '', title)
    # Remove @mentions/usernames
    title = re.sub(r'@\w+', '', title)
    # Remove common TikTok/Instagram patterns
    title = re.sub(r'#fyp|#foryoupage|#viral|#trending|#recommendations|#рекомендации', '', title, flags=re.IGNORECASE)
    # Remove "плейлист в профиле" and similar
    title = re.sub(r'плейлист в профиле|playlist in profile', '', title, flags=re.IGNORECASE)
    # Remove multiple spaces
    title = re.sub(r'\s+', ' ', title)
    # Remove leading/trailing spaces and special chars
    title = title.strip('.,!?-_ ')
    return title.strip()


def extract_artist_from_title(title: str) -> tuple[str, str]:
    """Extract artist and clean title from video title"""
    # First clean the title
    title = clean_social_media_title(title)
    
    patterns = [
        r'^(.+?)\s*-\s*(.+)$',  # "Artist - Title"
        r'^(.+?)\s*:\s*(.+)$',  # "Artist: Title"
    ]
    
    for pattern in patterns:
        match = re.match(pattern, title)
        if match:
            artist, clean_title = match.groups()
            artist = clean_social_media_title(artist)
            clean_title = clean_social_media_title(clean_title)
            return artist.strip(), clean_title.strip()
    
    # If no pattern matches, try to extract from common TikTok formats
    # Often TikTok titles are just descriptions, not artist-title format
    return "Unknown", title


async def download_from_tiktok(url: str) -> Optional[SocialMediaResult]:
    """Download TikTok video and extract metadata"""
    return await _download_social_media(url, "tiktok")


async def download_from_instagram(url: str) -> Optional[SocialMediaResult]:
    """Download Instagram Reels video and extract metadata"""
    return await _download_social_media(url, "instagram")


async def _download_social_media(url: str, platform: str) -> Optional[SocialMediaResult]:
    """Download video from social media platform"""
    import logging
    logger = logging.getLogger(__name__)
    
    ensure_ffmpeg()
    os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)
    
    template = os.path.join(settings.DOWNLOAD_DIR, f"{platform}_%(id)s.%(ext)s")
    
    # Use optimized yt-dlp settings from youtube.py
    from services.youtube import _get_ydl_opts
    ydl_opts = _get_ydl_opts(template, download=True)
    
    # Override for social media (keep some debug logging)
    ydl_opts["quiet"] = False
    ydl_opts["no_warnings"] = False
    
    try:
        logger.info(f"Starting {platform} download: {url[:100]}")
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(
            None,
            lambda: _blocking_extract(url, ydl_opts)
        )
        
        if not info:
            logger.error(f"No info extracted from {platform} URL")
            return None
        
        # Check if info is None or not a dict
        if not isinstance(info, dict):
            logger.error(f"Info is not a dict: {type(info)}")
            return None
        
        if "entries" in info:
            if not info["entries"]:
                logger.error(f"No entries in {platform} info")
                return None
            info = info["entries"][0]
            # Check again if entry is None
            if info is None:
                logger.error(f"First entry is None in {platform} result")
                return None
        
        video_id = info.get("id") or f"{platform}_{abs(hash(url)) % 1000000}"
        raw_title = info.get("title") or "Unknown"
        
        # Clean title from hashtags, usernames, etc.
        cleaned_title = clean_social_media_title(raw_title)
        title = sanitize(cleaned_title)
        
        # Extract artist from title
        artist, clean_title = extract_artist_from_title(title)
        title = clean_title if clean_title and clean_title != "Unknown" else title
        
        duration = int(info.get("duration") or 0)
        
        thumb = ""
        if info.get("thumbnails"):
            thumb = info["thumbnails"][-1]["url"]
        elif info.get("thumbnail"):
            thumb = info["thumbnail"]
        
        # Find actual downloaded file
        file_path = os.path.join(settings.DOWNLOAD_DIR, f"{platform}_{video_id}.mp3")
        
        # Check if file exists, if not try to find it
        if not os.path.exists(file_path):
            # Try to find the actual downloaded file
            for f in os.listdir(settings.DOWNLOAD_DIR):
                if f.startswith(f"{platform}_") and f.endswith(".mp3"):
                    file_path = os.path.join(settings.DOWNLOAD_DIR, f)
                    break
        
        logger.info(f"✅ {platform} download success: {title} - {artist}, duration: {duration}s")
        
        return SocialMediaResult(
            platform=platform,
            video_id=video_id,
            title=title,
            artist=artist,
            duration=duration,
            file_path=file_path,
            thumbnail=thumb,
        )
    except Exception as e:
        logger.error(f"❌ Error downloading {platform} video: {e}", exc_info=True)
        return None


def _blocking_extract(url: str, opts: dict):
    """
    Blocking extract for executor (used by social_download).
    Uses optimized opts from _get_ydl_opts().
    """
    max_retries = 3
    last_error = None
    logger = __import__("logging").getLogger(__name__)
    
    for attempt in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                result = ydl.extract_info(url, download=True)
                if result:
                    # Check if result is None or empty
                    if result is None:
                        logger.warning(f"yt-dlp returned None on attempt {attempt + 1}")
                        if attempt < max_retries - 1:
                            continue
                        raise RuntimeError("yt-dlp returned None")
                    return result
                else:
                    logger.warning(f"yt-dlp returned empty result on attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        continue
                    raise RuntimeError("yt-dlp returned empty result")
        except Exception as e:
            last_error = e
            logger.warning(f"Social media download attempt {attempt + 1}/{max_retries} failed: {e}")
            
            if attempt < max_retries - 1:
                # Try with different format on retry
                if attempt == 1:
                    opts["format"] = "worstaudio/worst"
                elif attempt == 2:
                    opts["format"] = "best"
                import time
                time.sleep(1)
            else:
                logger.error(f"All social media download attempts failed: {e}")
                raise RuntimeError(f"Download failed after {max_retries} attempts: {e}") from last_error
    
    raise RuntimeError(f"Download failed: {last_error}") if last_error else RuntimeError("Unknown error")

