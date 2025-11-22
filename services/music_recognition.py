"""
Music Recognition Service (Shazam-like)
Uses AudD API for music recognition from audio files
"""
import httpx
import os
from typing import Optional, Dict
from config import settings


async def recognize_song(audio_path: str) -> Optional[Dict]:
    """
    Recognize song from audio file using AudD API
    Returns dict with song info: title, artist, album, etc.
    """
    api_token = os.getenv("AUDD_API_TOKEN", "")
    if not api_token:
        # Try alternative: use free AudD API (limited requests)
        api_token = None
    
    url = "https://api.audd.io/"
    
    try:
        with open(audio_path, "rb") as f:
            files = {"file": f}
            data = {
                "api_token": api_token,
                "return": "apple_music,spotify",
            } if api_token else {
                "return": "apple_music,spotify",
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success" and result.get("result"):
                        return result["result"]
                    elif result.get("status") == "error":
                        # Try without API token (free tier)
                        if not api_token:
                            return None
                        # Retry without token
                        async with httpx.AsyncClient(timeout=30.0) as client2:
                            response2 = await client2.post(
                                url, 
                                files={"file": open(audio_path, "rb")}, 
                                data={"return": "apple_music,spotify"}
                            )
                            if response2.status_code == 200:
                                result2 = response2.json()
                                if result2.get("status") == "success" and result2.get("result"):
                                    return result2["result"]
    except Exception as e:
        print(f"Error recognizing song: {e}")
    
    return None


def format_song_info(song_data: Dict) -> str:
    """Format recognized song info into readable string"""
    title = song_data.get("title", "Unknown")
    artist = song_data.get("artist", "Unknown")
    album = song_data.get("album", "")
    release_date = song_data.get("release_date", "")
    
    info = f"🎵 **{title}**\n👤 {artist}"
    if album:
        info += f"\n💿 {album}"
    if release_date:
        info += f"\n📅 {release_date}"
    
    # Add links if available
    apple_music = song_data.get("apple_music", {})
    spotify = song_data.get("spotify", {})
    
    if apple_music.get("url"):
        info += f"\n🍎 [Apple Music]({apple_music['url']})"
    if spotify.get("external_urls", {}).get("spotify"):
        info += f"\n🎧 [Spotify]({spotify['external_urls']['spotify']})"
    
    return info

