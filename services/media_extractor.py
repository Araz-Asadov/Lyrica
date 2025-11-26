"""
Unified media extractor for handling YouTube, TikTok, and Instagram content.
"""
import asyncio
import hashlib
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union
from urllib.parse import urlparse

import aiohttp
import yt_dlp
from yt_dlp.utils import DownloadError

from utils.metadata_tools import clean_artist_title

logger = logging.getLogger(__name__)

# Base download directory
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Platform-specific extractor arguments
EXTRACTOR_ARGS = {
    "tiktok": {
        "player_client": ["android"],
        "app_id": ["1233", "1234"],
        "formats": ["mp4"],
        "extractor_args": {
            "tiktok": {
                "app_version": "25.1.3",
                "manifest_app_version": "25.1.3",
                "player_skip": ["webpage", "configs"],
            }
        },
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.tiktok.com/",
            "Origin": "https://www.tiktok.com"
        },
        "cookies": {
            "tt_chain_token": "1"
        },
        "redirect_resolver": True
    },
    "youtube": {
        "player_client": ["android"],
        "extractor_args": {
            "youtube": {
                "player_client": "android",
                "player_skip": ["webpage", "configs"],
            }
        },
        "http_headers": {
            "User-Agent": "com.google.android.youtube/17.36.4"
        }
    },
    "instagram": {
        "extractor_args": {
            "instagram": {
                "app_version": "238.0.0.16.120",
                "manifest_app_version": "238.0.0.16.120"
            }
        },
        "http_headers": {
            "User-Agent": "Instagram 238.0.0.16.120"
        }
    }
}

class MediaExtractor:
    """Handles media extraction from various platforms with caching and retries."""
    
    def __init__(self):
        self._cache = {}
        self._lock = asyncio.Lock()
        self._session = None
        self._ydl = None
        self._ydl_lock = asyncio.Lock()
        
    async def __aenter__(self):
        self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session:
            await self._session.close()
            self._session = None
            
    def _get_ydl_instance(self, ydl_opts: Dict[str, Any]) -> yt_dlp.YoutubeDL:
        """Get a yt-dlp instance with the given options."""
        if self._ydl is None:
            self._ydl = yt_dlp.YoutubeDL(ydl_opts)
        return self._ydl

    async def extract_media(self, url: str) -> Optional[Dict[str, Any]]:
        """Extract media from a URL with platform-specific settings."""
        platform = self._identify_platform(url)
        if not platform:
            logger.error(f"Unsupported URL: {url}")
            return None
            
        logger.info(f"Extracting {platform} media from {url}")
        
        # Resolve TikTok redirects if needed
        if platform == 'tiktok' and EXTRACTOR_ARGS['tiktok'].get('redirect_resolver', False):
            url = await self._resolve_tiktok_redirect(url)
            if not url:
                logger.error(f"Failed to resolve TikTok URL")
                return None
        
        # Get platform-specific options
        ydl_opts = self._get_ydl_options(platform)
        
        # Try to get from cache
        cache_key = self._get_cache_key(url, ydl_opts)
        async with self._lock:
            if cache_key in self._cache:
                logger.debug(f"Cache hit for {url}")
                return self._cache[cache_key]
        
        try:
            result = await self._download_with_retry(url, ydl_opts, platform)
            if result:
                async with self._lock:
                    self._cache[cache_key] = result
            return result
        except Exception as e:
            logger.error(f"Error extracting {platform} media: {e}", exc_info=True)
            return None

    async def _resolve_tiktok_redirect(self, url: str) -> Optional[str]:
        """Resolve TikTok short URLs to their final destination."""
        if not any(x in url for x in ['vm.tiktok.com', 'vt.tiktok.com']):
            return url
            
        cache_key = f"tiktok_redirect_{hashlib.md5(url.encode()).hexdigest()}"
        
        # Check cache first
        async with self._lock:
            if cache_key in self._cache:
                return self._cache[cache_key]
                
        # Resolve redirect
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
                
            async with self._session.head(
                url,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                resolved_url = str(resp.url)
                async with self._lock:
                    self._cache[cache_key] = resolved_url
                return resolved_url
        except Exception as e:
            logger.warning(f"Failed to resolve TikTok URL {url}: {e}")
            return url

    def _identify_platform(self, url: str) -> Optional[str]:
        """Identify the platform from the URL."""
        url_lower = url.lower()
        if 'tiktok.com' in url_lower or 'vm.tiktok.com' in url_lower or 'vt.tiktok.com' in url_lower:
            return 'tiktok'
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'instagram.com' in url_lower and ('/reel/' in url_lower or '/p/' in url_lower or '/tv/' in url_lower):
            return 'instagram'
        return None

    def _get_ydl_options(self, platform: str) -> Dict[str, Any]:
        """Get yt-dlp options for the specified platform."""
        base_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(DOWNLOAD_DIR / '%(id)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'force_generic_extractor': False,
            'nocheckcertificate': True,
            'ignoreerrors': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'postprocessor_args': [
                '-ar', '44100',
                '-ac', '2',
                '-b:a', '192k',
            ],
            'prefer_ffmpeg': True,
            'ffmpeg_location': 'ffmpeg',
            'keepvideo': False,
        }
        
        # Apply platform-specific options
        platform_opts = EXTRACTOR_ARGS.get(platform, {})
        
        # Update extractor arguments
        if 'extractor_args' in platform_opts:
            if 'extractor_args' not in base_opts:
                base_opts['extractor_args'] = {}
            base_opts['extractor_args'].update(platform_opts['extractor_args'])
        
        # Update HTTP headers
        if 'http_headers' in platform_opts:
            base_opts['http_headers'] = platform_opts['http_headers']
        
        return base_opts

    async def _download_with_retry(
        self, 
        url: str, 
        ydl_opts: Dict[str, Any],
        platform: str,
        max_retries: int = 2
    ) -> Optional[Dict[str, Any]]:
        """Download media with retry logic."""
        last_error = None
        tmp_path = None
        
        for attempt in range(max_retries):
            try:
                # Create temp file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                    tmp_path = tmp_file.name
                
                # Update output template
                ydl_opts = ydl_opts.copy()
                ydl_opts['outtmpl'] = tmp_path.replace('.mp3', '.%(ext)s')
                
                # Run yt-dlp in a thread
                loop = asyncio.get_running_loop()
                info = await loop.run_in_executor(
                    None, 
                    lambda: self._download_media(url, ydl_opts)
                )
                
                if info and os.path.exists(tmp_path):
                    # Process metadata
                    metadata = self._extract_metadata(info, platform)
                    return {
                        'file_path': tmp_path,
                        'metadata': metadata,
                        'platform': platform,
                        'url': url
                    }
                
            except Exception as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(1)  # Short delay before retry
            finally:
                # Clean up if we failed
                if tmp_path and os.path.exists(tmp_path) and (not info or not os.path.exists(tmp_path)):
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
        
        logger.error(f"Failed to download {url} after {max_retries} attempts: {last_error}")
        return None
    
    def _download_media(self, url: str, ydl_opts: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Synchronous download using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=True)
        except DownloadError as e:
            logger.error(f"Download error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {e}", exc_info=True)
            return None
    
    def _extract_metadata(self, info: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """Extract and clean metadata from download info."""
        # Extract basic info
        title = info.get('title', '')
        uploader = info.get('uploader', '')
        
        # Try to get track and artist from metadata
        track = info.get('track')
        artist = info.get('artist')
        
        # Platform-specific metadata extraction
        if platform == 'youtube':
            # For YouTube, use uploader as artist if no artist is found
            if not artist and uploader and ' - Topic' not in uploader:
                artist = uploader
        elif platform == 'tiktok':
            # For TikTok, clean up the title
            if title and 'TikTok' in title:
                title = re.sub(r'\s*on TikTok$', '', title, flags=re.IGNORECASE).strip()
        
        # Clean and merge metadata
        metadata = {
            'title': title,
            'artist': artist,
            'track': track,
            'uploader': uploader,
            'duration': info.get('duration'),
            'thumbnail': info.get('thumbnail'),
            'platform': platform
        }
        
        # Clean artist and title
        metadata['artist'], metadata['title'] = clean_artist_title(
            metadata.get('artist', ''),
            metadata.get('title', title)
        )
        
        return metadata
    
    def _get_cache_key(self, url: str, ydl_opts: Dict[str, Any]) -> str:
        """Generate a cache key for the request."""
        key_data = {
            'url': url,
            'format': ydl_opts.get('format'),
            'extractor_args': ydl_opts.get('extractor_args', {})
        }
        return hashlib.md5(str(key_data).encode()).hexdigest()

# Global instance
media_extractor = MediaExtractor()

async def extract_media(url: str) -> Optional[Dict[str, Any]]:
    """Extract media from a URL using the global extractor."""
    async with MediaExtractor() as extractor:
        return await extractor.extract_media(url)