"""
Unified Search Service
Handles all music search and recognition from various sources
"""
import asyncio
import logging
import os
import re
from typing import Optional, List, Dict, Any, Union, Tuple
from dataclasses import dataclass
from pathlib import Path

from .media_extractor import media_extractor, extract_media
from .youtube import search_multiple, YTSearchResult
from .music_recognition_service import get_recognition_service

logger = logging.getLogger(__name__)

# Ensure downloads directory exists
DOWNLOADS_DIR = Path("downloads")
DOWNLOADS_DIR.mkdir(exist_ok=True)

@dataclass
class SearchResult:
    """Unified search result from any source"""
    source: str  # 'youtube', 'tiktok', 'instagram', 'recognition'
    title: str
    artist: str
    duration: int
    thumbnail: str
    
    # Source-specific IDs
    youtube_id: Optional[str] = None
    tiktok_id: Optional[str] = None
    instagram_id: Optional[str] = None
    
    # Additional metadata
    metadata: Optional[Dict[str, Any]] = None
    
    # File path if downloaded
    file_path: Optional[str] = None

class SearchService:
    """Unified service for searching and recognizing music from various sources"""
    
    def __init__(self):
        self.recognition_service = get_recognition_service()
    
    def _clean_search_query(self, query: str) -> str:
        """Clean and normalize search query."""
        try:
            import emoji
        except ImportError:
            # If emoji package not available, skip emoji removal
            pass
        else:
            # Remove emojis
            query = emoji.replace_emoji(query, replace='')
        
        # Replace common separators with spaces but keep important punctuation
        clean = re.sub(r'[–—\-_]+', ' ', query)  # Replace dashes with spaces
        clean = re.sub(r'[^\w\s&\'\"]', ' ', clean)  # Keep letters, numbers, spaces, &, quotes
        
        # Remove extra whitespace
        clean = ' '.join(clean.split())
        
        return clean.strip()
    
    async def _youtube_api_fallback(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Fallback to YouTube API if direct search fails."""
        import aiohttp
        import json
        
        try:
            # Use yt.lemnoslife.com as a fallback API
            url = f"https://yt.lemnoslife.com/search?q={query}&maxResults={max_results}&type=video"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return []
                        
                    data = await response.json()
                    
                    results = []
                    for item in data.get('items', [])[:max_results]:
                        try:
                            video_id = item.get('id', {}).get('videoId')
                            if not video_id:
                                continue
                                
                            snippet = item.get('snippet', {})
                            
                            result = SearchResult(
                                source='youtube',
                                title=snippet.get('title', 'Unknown'),
                                artist=snippet.get('channelTitle', 'Unknown'),
                                duration=0,  # Not available in this API
                                thumbnail=snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                                youtube_id=video_id
                            )
                            results.append(result)
                        except Exception as e:
                            logger.error(f"Error processing API result: {e}")
                            continue
                            
                    return results
                    
        except Exception as e:
            logger.error(f"YouTube API fallback error: {e}")
            return []
    
    async def search_youtube(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """
        Search YouTube for music with improved query handling and fallbacks.
        
        Args:
            query: Search query (can be raw text or ytsearch: prefixed)
            max_results: Maximum number of results to return
            
        Returns:
            List of SearchResult objects
        """
        # Clean the query first
        clean_query = self._clean_search_query(query)
        if not clean_query:
            return []
            
        # Check if it's a direct video ID or URL
        from urllib.parse import urlparse, parse_qs
        
        # Handle ytsearch: prefix
        if clean_query.startswith('ytsearch:'):
            clean_query = clean_query[9:].strip()
        
        # Try direct search first
        try:
            logger.info(f"Searching YouTube with cleaned query: '{clean_query}'")
            results = await search_multiple(clean_query, max_results=max_results)
            
            # If no results and query was modified, try original query
            if not results and clean_query != query:
                logger.info(f"No results with cleaned query, trying original: '{query}'")
                results = await search_multiple(query, max_results=max_results)
                
            # If still no results, try API fallback
            if not results:
                logger.info("No results from direct search, trying API fallback...")
                return await self._youtube_api_fallback(clean_query, max_results)
                
            # Convert to SearchResult objects
            search_results = []
            for result in results[:max_results]:
                try:
                    search_result = SearchResult(
                        source='youtube',
                        title=result.title,
                        artist=result.artist or result.channel or 'Unknown',
                        duration=result.duration or 0,
                        thumbnail=result.thumbnail or '',
                        youtube_id=result.video_id,
                        metadata={
                            'view_count': result.views,
                            'upload_date': result.upload_date,
                            'channel': result.channel
                        }
                    )
                    search_results.append(search_result)
                except Exception as e:
                    logger.error(f"Error processing search result: {e}")
                    continue
                    
            logger.info(f"Successfully converted {len(search_results)} search results")
            return search_results
            
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
            # Try API fallback on error
            return await self._youtube_api_fallback(clean_query, max_results)
            
        except Exception as e:
            logger.error(f"YouTube search failed: {e}", exc_info=True)
            return []
    
    async def process_youtube_url(self, url: str) -> Optional[SearchResult]:
        """Process YouTube URL with enhanced metadata extraction"""
        try:
            # Use our media extractor for better handling
            result = await extract_media(url)
            if not result or not result.get('metadata'):
                return None
                
            meta = result['metadata']
            return SearchResult(
                source="youtube",
                title=meta.get('title', 'Unknown Track'),
                artist=meta.get('artist', 'Unknown Artist'),
                duration=meta.get('duration', 0),
                thumbnail=meta.get('thumbnail', ''),
                youtube_id=result.get('id') or extract_youtube_id(url),
                file_path=result.get('file_path'),
                metadata={"extracted": meta}
            )
        except Exception as e:
            logger.error(f"Failed to process YouTube URL {url}: {e}", exc_info=True)
            return None
    
    async def process_tiktok_url(self, url: str) -> Optional[SearchResult]:
        """Process TikTok URL with improved extraction"""
        try:
            # Clean up URL first (handle redirects)
            url = await self._resolve_tiktok_redirect(url)
            
            # Use our media extractor
            result = await extract_media(url)
            if not result or not result.get('metadata'):
                return None
                
            meta = result['metadata']
            return SearchResult(
                source="tiktok",
                title=meta.get('title', 'TikTok Video'),
                artist=meta.get('artist', 'Unknown Creator'),
                duration=meta.get('duration', 0),
                thumbnail=meta.get('thumbnail', ''),
                tiktok_id=result.get('id', ''),
                file_path=result.get('file_path'),
                metadata={"extracted": meta}
            )
        except Exception as e:
            logger.error(f"Failed to process TikTok URL {url}: {e}", exc_info=True)
            return None
            
    async def _resolve_tiktok_redirect(self, url: str) -> str:
        """Resolve TikTok redirects to get the final URL"""
        if 'vm.tiktok.com' in url or 'vt.tiktok.com' in url:
            import aiohttp
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.head(url, allow_redirects=True) as resp:
                        return str(resp.url)
            except Exception as e:
                logger.warning(f"Failed to resolve TikTok redirect: {e}")
        return url
    
    async def process_instagram_url(self, url: str) -> Optional[SearchResult]:
        """Process Instagram URL with improved extraction"""
        try:
            # Normalize URL
            url = self._normalize_instagram_url(url)
            
            # Use our media extractor
            result = await extract_media(url)
            if not result or not result.get('metadata'):
                return None
                
            meta = result['metadata']
            return SearchResult(
                source="instagram",
                title=meta.get('title', 'Instagram Reel'),
                artist=meta.get('artist', 'Instagram User'),
                duration=meta.get('duration', 0),
                thumbnail=meta.get('thumbnail', ''),
                instagram_id=result.get('id', ''),
                file_path=result.get('file_path'),
                metadata={"extracted": meta}
            )
        except Exception as e:
            logger.error(f"Failed to process Instagram URL {url}: {e}", exc_info=True)
            return None
            
    def _normalize_instagram_url(self, url: str) -> str:
        """Normalize Instagram URL to standard format"""
        url = url.strip()
        if '?' in url:
            url = url.split('?')[0]
        return url.rstrip('/')
    
    async def recognize_audio(self, audio_path: str) -> Optional[SearchResult]:
        """Recognize music from audio file with improved error handling"""
        try:
            if not os.path.exists(audio_path):
                logger.error(f"Audio file not found: {audio_path}")
                return None
                
            # Check file size and duration
            file_size = os.path.getsize(audio_path)
            if file_size < 1024:  # 1KB minimum
                logger.error(f"Audio file too small: {file_size} bytes")
                return None
                
            # Get duration using ffprobe
            duration = await self._get_audio_duration(audio_path)
            if duration and duration < 2:  # At least 2 seconds of audio needed
                logger.error(f"Audio too short: {duration} seconds")
                return None
                
            # Try recognition
            result = await self.recognition_service.recognize_from_file(audio_path)
            if not result:
                return None
                
            # Try to enhance with YouTube search
            if result.title and result.artist:
                search_query = f"{result.artist} {result.title}"
                youtube_results = await self.search_youtube(search_query, max_results=1)
                if youtube_results:
                    # Use the YouTube result for better metadata
                    yt_result = youtube_results[0]
                    return SearchResult(
                        source="recognition",
                        title=yt_result.title,
                        artist=yt_result.artist,
                        duration=yt_result.duration,
                        thumbnail=yt_result.thumbnail,
                        youtube_id=yt_result.youtube_id,
                        metadata={
                            "recognition": result,
                            "youtube": yt_result.metadata.get('youtube')
                        }
                    )
            
            # Fallback to basic recognition result
            return SearchResult(
                source="recognition",
                title=result.title,
                artist=result.artist,
                duration=result.duration or 0,
                thumbnail="",
                metadata={"recognition": result}
            )
            
        except Exception as e:
            logger.error(f"Audio recognition failed for {audio_path}: {e}", exc_info=True)
            return None
            
    async def _get_audio_duration(self, file_path: str) -> float:
        """Get audio duration using ffprobe"""
        try:
            cmd = [
                'ffprobe', 
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                file_path
            ]
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                return float(stdout.decode().strip())
            return 0
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}")
            return 0
    
    async def search_from_any_source(self, query: str) -> List[SearchResult]:
        """
        Unified search that handles all input types with improved fallbacks:
        - YouTube URLs
        - TikTok/Instagram URLs
        - Search queries (searches YouTube)
        - File paths for local files
        """
        # Check if it's a URL or search query
        query = query.strip()
        
        # Check for URLs first
        if any(domain in query.lower() for domain in ['youtube.com', 'youtu.be']):
            result = await self.process_youtube_url(query)
            return [result] if result else []
            
        if any(domain in query.lower() for domain in ['tiktok.com', 'vm.tiktok.com', 'vt.tiktok.com']):
            result = await self.process_tiktok_url(query)
            return [result] if result else []
            
        if 'instagram.com' in query.lower() and any(x in query.lower() for x in ['/reel/', '/p/', '/tv/']):
            result = await self.process_instagram_url(query)
            return [result] if result else []
        
        # Check if it's a local file path
        if os.path.exists(query) and os.path.isfile(query):
            result = await self.recognize_audio(query)
            return [result] if result else []
        
        # Default to YouTube search with improved query handling
        return await self._search_with_fallback(query)
    
    async def _search_with_fallback(self, query: str, max_attempts: int = 3) -> List[SearchResult]:
        """Search with multiple fallback strategies"""
        # Generate different search variations
        attempts = []
        
        # Original query
        attempts.append(query.strip())
        
        # Clean version
        clean_query = self._clean_search_query(query)
        if clean_query and clean_query != query.strip():
            attempts.append(clean_query)
        
        # Replace dashes and special chars with spaces
        dash_replaced = re.sub(r'[–—\-_]+', ' ', query).strip()
        if dash_replaced and dash_replaced not in attempts:
            attempts.append(dash_replaced)
        
        # Add "music" or "song" if not present (helps with music search)
        if not any(word in query.lower() for word in ['music', 'song', 'audio', 'track']):
            attempts.append(f"{query.strip()} music")
        
        seen_queries = set()
        seen_ids = set()
        results = []
        
        for i, attempt in enumerate(attempts[:max_attempts]):
            if not attempt or attempt in seen_queries:
                continue
                
            seen_queries.add(attempt)
            try:
                logger.info(f"Search attempt {i+1}/{max_attempts}: '{attempt}'")
                search_results = await self.search_youtube(attempt, max_results=5)
                
                if search_results:
                    # Filter out duplicates by YouTube ID
                    for result in search_results:
                        if result.youtube_id and result.youtube_id not in seen_ids:
                            results.append(result)
                            seen_ids.add(result.youtube_id)
                            
                            if len(results) >= 5:  # Limit results
                                return results[:5]
                                
                    # If we got good results, don't try more variations
                    if len(results) >= 2:
                        break
                        
            except Exception as e:
                logger.warning(f"Search attempt failed for '{attempt}': {e}")
        
        logger.info(f"Fallback search completed with {len(results)} results")
        return results[:5]  # Return max 5 results

# Global instance
_search_service = None

def get_search_service() -> SearchService:
    """Get or create global search service instance"""
    global _search_service
    if _search_service is None:
        _search_service = SearchService()
    return _search_service
