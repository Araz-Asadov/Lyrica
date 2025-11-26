"""
Metadata processing utilities for audio files and media content.
"""
import re
from typing import Optional, Tuple, Dict, Any
import logging

logger = logging.getLogger(__name__)

def clean_artist_title(artist: str, title: str) -> Tuple[str, str]:
    """Clean and standardize artist and title information."""
    def clean(text: str) -> str:
        if not text:
            return ""
        # Remove common social media tags and mentions
        text = re.sub(r'[@#]\w+', '', text)
        # Remove special characters but keep letters, numbers, and basic punctuation
        text = re.sub(r'[^\w\s\-&,.()\[\]\'\"]', ' ', text)
        # Normalize whitespace
        text = ' '.join(text.split())
        return text.strip()

    artist = clean(artist)
    title = clean(title)
    
    # If title contains artist, try to extract a cleaner title
    if artist and artist.lower() in title.lower():
        # Try to remove artist from the beginning of title
        if title.lower().startswith(artist.lower()):
            new_title = title[len(artist):].lstrip(' -:,')
            if new_title:
                title = new_title
        # Try to remove artist from the end of title
        elif title.lower().endswith(artist.lower()):
            new_title = title[:-len(artist)].rstrip(' -:,')
            if new_title:
                title = new_title
    
    return artist or "Unknown Artist", title or "Unknown Track"

def extract_metadata_from_title(title: str) -> Tuple[str, str]:
    """Extract artist and title from a combined string."""
    if not title:
        return "Unknown Artist", "Unknown Track"
    
    # Common patterns for artist - title separation
    patterns = [
        r'^(.*?)\s*[-~–—]\s*(.+)$',  # Artist - Title
        r'^(.*?)\s*[\[\(]\s*(.+?)\s*[\]\)]\s*$',  # Artist (Title)
        r'^(.*?)\s*[\|]\s*(.+)$',  # Artist | Title
    ]
    
    for pattern in patterns:
        match = re.match(pattern, title, re.IGNORECASE)
        if match:
            artist, track = match.groups()
            return clean_artist_title(artist, track)
    
    # If no pattern matches, try to clean the title
    _, cleaned_title = clean_artist_title("", title)
    return "Unknown Artist", cleaned_title

def merge_metadata(
    primary: Dict[str, Any], 
    fallback: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge primary metadata with fallback metadata."""
    result = primary.copy()
    
    for key, value in fallback.items():
        if key not in result or not result[key]:
            result[key] = value
    
    # Ensure we have at least basic metadata
    if not result.get('title'):
        result['title'] = fallback.get('title', 'Unknown Track')
    if not result.get('artist'):
        result['artist'] = fallback.get('artist', 'Unknown Artist')
    
    # Clean artist and title
    result['artist'], result['title'] = clean_artist_title(
        result.get('artist', ''), 
        result.get('title', '')
    )
    
    return result
