# This file was auto-generated to fix a circular import error.
# The original file could not be read, so this is a reconstruction based on usage in other files.

import logging
import asyncio
import os
from dataclasses import dataclass
from typing import Optional, List
import yt_dlp
from config import settings

logger = logging.getLogger(__name__)

@dataclass
class YTSearchResult:
    """Dataclass for a single YouTube search result."""
    video_id: str
    title: str
    artist: Optional[str]
    channel: Optional[str]
    duration: int
    thumbnail: str
    views: int
    upload_date: str

@dataclass
class YTResult:
    """Dataclass for a downloaded YouTube video."""
    file_path: str
    title: str
    artist: str
    duration: int
    thumbnail: str
    youtube_id: str

def is_youtube_link(url: str) -> bool:
    """Check if URL is a YouTube link"""
    if not isinstance(url, str):
        return False
    return "youtube.com/" in url or "youtu.be/" in url

def clean_youtube_url(url: str) -> str:
    """Clean YouTube URL by removing problematic query parameters and normalizing format"""
    if not url:
        return url
    
    import re
    
    # More flexible video ID pattern (YouTube IDs are typically 11 chars but can vary)
    video_id_pattern = r'([a-zA-Z0-9_-]{10,12})'
    
    # Handle youtu.be short URLs
    if "youtu.be/" in url:
        match = re.search(rf'youtu\.be/{video_id_pattern}', url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"
    
    # Handle youtube.com/watch URLs
    if "youtube.com/watch" in url:
        match = re.search(rf'[?&]v={video_id_pattern}', url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"
    
    # Handle youtube.com/shorts URLs
    if "youtube.com/shorts/" in url:
        match = re.search(rf'youtube\.com/shorts/{video_id_pattern}', url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"
    
    # Handle youtube.com/embed URLs
    if "youtube.com/embed/" in url:
        match = re.search(rf'youtube\.com/embed/{video_id_pattern}', url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/watch?v={video_id}"
    
    # If no pattern matches, return original URL
    return url

def _get_ydl_opts(template: str, download: bool = True):
    """Get yt-dlp options with latest YouTube compatibility settings."""
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio/best[height<=720]',
        'outtmpl': template,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'logtostderr': False,
        'extract_flat': False if download else 'in_playlist',
        'skip_download': not download,
        'ignoreerrors': True,
        'no_check_certificate': True,
        'prefer_ffmpeg': True,
        # Enhanced options for latest YouTube compatibility
        'extractor_retries': 5,
        'fragment_retries': 5,
        'retries': 5,
        'http_chunk_size': 10485760,  # 10MB chunks
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        # Additional YouTube-specific options
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['webpage'],
                'skip': ['hls', 'dash']
            }
        },
        # Network optimization
        'socket_timeout': 30,
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    }
    
    if download:
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    
    return opts

async def search_multiple(query: str, max_results: int = 5) -> List[YTSearchResult]:
    """Search YouTube for multiple results."""
    loop = asyncio.get_running_loop()
    
    def _search():
        # Ensure downloads directory exists
        os.makedirs("downloads", exist_ok=True)
        
        ydl_opts = _get_ydl_opts('%(id)s.%(ext)s', download=False)
        ydl_opts['extract_flat'] = True
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Clean the query - remove excessive whitespace and special chars that break search
                clean_query = ' '.join(query.strip().split())
                search_query = f"ytsearch{max_results}:{clean_query}"
                
                logger.info(f"Searching YouTube with query: {search_query}")
                result = ydl.extract_info(search_query, download=False)
                
                if result and 'entries' in result and result['entries']:
                    valid_entries = [entry for entry in result['entries'] if entry and entry.get('id')]
                    logger.info(f"Found {len(valid_entries)} valid results")
                    return valid_entries
                else:
                    logger.warning(f"No entries found for query: {clean_query}")
                    return []
                    
            except Exception as e:
                logger.error(f"yt-dlp search error for query '{query}': {e}")
                return []

    entries = await loop.run_in_executor(None, _search)
    
    results = []
    for entry in entries:
        if not entry or not entry.get('id'):
            continue
            
        # Extract thumbnail - prefer higher quality
        thumbnail = entry.get('thumbnail')
        if not thumbnail and entry.get('thumbnails'):
            # Get the best quality thumbnail
            thumbnails = entry.get('thumbnails', [])
            if thumbnails:
                thumbnail = thumbnails[-1].get('url', '')
        
        results.append(
            YTSearchResult(
                video_id=entry.get('id', ''),
                title=entry.get('title', 'Unknown Title'),
                artist=entry.get('artist') or entry.get('uploader') or entry.get('channel'),
                channel=entry.get('uploader') or entry.get('channel'),
                duration=entry.get('duration', 0),
                thumbnail=thumbnail or '',
                views=entry.get('view_count', 0),
                upload_date=entry.get('upload_date', '')
            )
        )
    return results

async def search_and_download(query: str) -> Optional[YTResult]:
    """Search on YouTube and download the first result."""
    loop = asyncio.get_running_loop()
    
    def _search_and_download():
        # Ensure downloads directory exists
        os.makedirs("downloads", exist_ok=True)
        
        template = os.path.join("downloads", "%(id)s.%(ext)s")
        ydl_opts = _get_ydl_opts(template, download=True)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                # Clean the query
                clean_query = ' '.join(query.strip().split())
                search_query = f"ytsearch1:{clean_query}"
                
                logger.info(f"Searching and downloading with query: {search_query}")
                result = ydl.extract_info(search_query, download=True)
                
                if result and 'entries' in result and result['entries']:
                    entry = result['entries'][0]
                    
                    if not entry or not entry.get('id'):
                        logger.error("No valid entry found in search results")
                        return None
                    
                    # Get the actual downloaded file path
                    # yt-dlp with FFmpegExtractAudio will create .mp3 files
                    video_id = entry.get('id', '')
                    expected_mp3_path = os.path.join("downloads", f"{video_id}.mp3")
                    
                    # Check multiple possible file paths
                    possible_paths = [
                        expected_mp3_path,
                        os.path.join("downloads", f"{video_id}.m4a"),
                        os.path.join("downloads", f"{video_id}.webm"),
                        ydl.prepare_filename(entry)
                    ]
                    
                    downloaded_file = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            downloaded_file = path
                            break
                    
                    if not downloaded_file:
                        logger.error(f"Downloaded file not found. Checked paths: {possible_paths}")
                        return None
                    
                    # Extract thumbnail - prefer higher quality
                    thumbnail = entry.get('thumbnail')
                    if not thumbnail and entry.get('thumbnails'):
                        thumbnails = entry.get('thumbnails', [])
                        if thumbnails:
                            thumbnail = thumbnails[-1].get('url', '')
                    
                    return YTResult(
                        file_path=downloaded_file,
                        title=entry.get('title', 'Unknown Title'),
                        artist=entry.get('artist') or entry.get('uploader') or entry.get('channel'),
                        duration=entry.get('duration', 0),
                        thumbnail=thumbnail or '',
                        youtube_id=video_id
                    )
                else:
                    logger.error(f"No search results found for query: {clean_query}")
                    return None
                    
            except Exception as e:
                logger.error(f"yt-dlp search and download error for query '{query}': {e}")
                return None

    return await loop.run_in_executor(None, _search_and_download)

async def download_from_url(url: str) -> Optional[YTResult]:
    """Download a song from a YouTube URL with improved error handling and retries."""
    loop = asyncio.get_running_loop()
    max_retries = 3
    retry_delay = 2  # seconds

    async def _download_with_retry():
        # Ensure downloads directory exists
        os.makedirs("downloads", exist_ok=True)
        
        # Clean the URL to remove problematic parameters
        clean_url = clean_youtube_url(url)
        logger.info(f"Original URL: {url}")
        logger.info(f"Cleaned URL: {clean_url}")
        
        template = os.path.join("downloads", "%(id)s.%(ext)s")
        ydl_opts = _get_ydl_opts(template, download=True)
        
        # Add more robust error handling and retries
        for attempt in range(max_retries):
            try:
                logger.info(f"Download attempt {attempt + 1}/{max_retries} for URL: {clean_url}")
                
                # Try with different extractor settings based on attempt
                if attempt > 0:
                    ydl_opts = _get_ydl_opts(template, download=True)
                    if attempt % 2 == 0:
                        ydl_opts['extractor_args'] = {
                            'youtube': {
                                'player_client': ['android'],
                                'player_skip': ['configs', 'webpage'],
                            }
                        }
                    else:
                        ydl_opts['extractor_args'] = {
                            'youtube': {
                                'player_client': ['ios', 'android'],
                                'player_skip': ['webpage'],
                            }
                        }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    entry = await loop.run_in_executor(
                        None, 
                        lambda: ydl.extract_info(clean_url, download=True)
                    )
                
                if not entry or not entry.get('id'):
                    logger.error("No valid entry extracted from URL")
                    continue
                
                # Get the actual downloaded file path
                video_id = entry.get('id', '')
                
                # Check multiple possible file paths and extensions
                possible_paths = [
                    os.path.join("downloads", f"{video_id}.mp3"),
                    os.path.join("downloads", f"{video_id}.m4a"),
                    os.path.join("downloads", f"{video_id}.webm"),
                    os.path.join("downloads", f"{video_id}.mp4"),
                    os.path.join("downloads", f"{video_id}.mkv")
                ]
                
                # Also check the filename that yt-dlp might have used
                if 'requested_downloads' in entry:
                    for download in entry['requested_downloads']:
                        if os.path.exists(download['filepath']):
                            downloaded_file = download['filepath']
                            break
                else:
                    downloaded_file = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            downloaded_file = path
                            break
                
                if not downloaded_file or not os.path.exists(downloaded_file):
                    logger.error(f"Downloaded file not found. Checked paths: {possible_paths}")
                    continue
                
                # Extract thumbnail - prefer higher quality
                thumbnail = entry.get('thumbnail', '')
                if not thumbnail and entry.get('thumbnails'):
                    thumbnails = entry['thumbnails']
                    if thumbnails:
                        # Get the highest resolution thumbnail
                        thumbnails.sort(key=lambda x: x.get('width', 0) * x.get('height', 0), reverse=True)
                        thumbnail = thumbnails[0].get('url', '')
                
                # Get artist from uploader if not available
                artist = entry.get('artist') or entry.get('uploader') or entry.get('channel') or 'Unknown Artist'
                
                # Clean up title (remove [MUSIC] or other common prefixes)
                title = entry.get('title', 'Unknown Title')
                title = title.replace('[MUSIC]', '').replace('(Official Video)', '').strip()
                
                return YTResult(
                    file_path=downleted_file,
                    title=title,
                    artist=artist,
                    duration=int(entry.get('duration', 0)),
                    thumbnail=thumbnail,
                    youtube_id=video_id
                )
                
            except (yt_dlp.DownloadError, yt_dlp.utils.DownloadError) as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"All download attempts failed for URL: {clean_url}")
                    return None
                await asyncio.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                
            except Exception as e:
                logger.error(f"Unexpected error during download: {str(e)}", exc_info=True)
                if attempt == max_retries - 1:
                    return None
                await asyncio.sleep(retry_delay * (attempt + 1))
        
        return None
    
    return await _download_with_retry()

    return await loop.run_in_executor(None, _download)
