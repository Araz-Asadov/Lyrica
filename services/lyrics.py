import httpx
import re
from typing import Optional
import logging
from urllib.parse import quote

# 🧠 Cache
lyrics_cache: dict[str, str] = {}

logger = logging.getLogger(__name__)


# =====================================================
# 🔥 MAHNIN ADINI TƏMİZLƏYƏN FUNKSIYA
# =====================================================
def clean_title(title: str) -> str:
    # Remove brackets (Official Video), (4K), [Lyrics], etc.
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"\[.*?\]", "", title)
    # Remove common video tags
    title = re.sub(r"\b(Official|Video|Music|HD|4K|Audio|Clip|Lyrics|Lyric|MV|Remix|Cover|Version)\b", "", title, flags=re.I)
    # Normalize dashes
    title = re.sub(r"[–—]", "-", title)
    # Clean multiple spaces
    title = re.sub(r"\s+", " ", title)
    return title.strip()


def extract_artist_from_title(title: str) -> tuple[str, str]:
    """Extract artist and song title from combined string"""
    # Common patterns: "Artist - Song", "Artist: Song", "Artist | Song"
    patterns = [
        r"^(.+?)\s*[-–—]\s*(.+)$",
        r"^(.+?)\s*:\s*(.+)$",
        r"^(.+?)\s*\|\s*(.+)$",
    ]
    
    for pattern in patterns:
        match = re.match(pattern, title, re.IGNORECASE)
        if match:
            artist = match.group(1).strip()
            song = match.group(2).strip()
            return artist, song
    
    return "", title


async def get_lyrics(title: str, artist: str = "") -> Optional[str]:
    """
    Çoxlu mənbədən sözlər tapma - LRCLIB, Lyrics.ovh, YouTube Captions
    """
    original_title = title
    title = clean_title(title)  # 🔥 Təmizlənmiş ad
    
    # Əgər artist "Unknown" və ya boşdursa, title-dan çıxar
    if not artist or artist.lower() in ["unknown", "unknown artist", ""]:
        extracted_artist, extracted_title = extract_artist_from_title(title)
        if extracted_artist:
            artist = extracted_artist
            title = extracted_title
    
    key = (title + "|" + artist).lower().strip()

    if key in lyrics_cache:
        return lyrics_cache[key]

    # 1️⃣ LRCLIB (ən yaxşı mənbə)
    lyrics = await _lrclib_search(title, artist)
    if lyrics and len(lyrics.strip()) > 20:  # Minimum uzunluq yoxla
        lyrics_cache[key] = lyrics
        logger.info(f"✅ Lyrics tapıldı (LRCLIB): {title} - {artist}")
        return lyrics

    # 2️⃣ Lyrics.ovh (alternativ mənbə)
    lyrics = await _lyrics_ovh_search(title, artist)
    if lyrics and len(lyrics.strip()) > 20:
        lyrics_cache[key] = lyrics
        logger.info(f"✅ Lyrics tapıldı (Lyrics.ovh): {title} - {artist}")
        return lyrics

    # 3️⃣ YouTube captions (son çarə)
    lyrics = await _youtube_captions(original_title)
    if lyrics and len(lyrics.strip()) > 20:
        lyrics_cache[key] = lyrics
        logger.info(f"✅ Lyrics tapıldı (YouTube): {original_title}")
        return lyrics

    logger.warning(f"❌ Lyrics tapılmadı: {title} - {artist}")
    return None


# =====================================================
# 1️⃣ LRCLIB API — MÜKƏMMƏL
# =====================================================
async def _lrclib_search(title: str, artist: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # İlk cəhd: artist ilə
            if artist:
                r = await client.get(
                    "https://lrclib.net/api/search",
                    params={
                        "track_name": title,
                        "artist_name": artist
                    }
                )
                if r.status_code == 200:
                    data = r.json()
                    if data and isinstance(data, list) and len(data) > 0:
                        track = data[0]
                        lyrics = track.get("plainLyrics") or track.get("syncedLyrics")
                        if lyrics:
                            return _clean(lyrics)
            
            # İkinci cəhd: yalnız title ilə
            r = await client.get(
                "https://lrclib.net/api/search",
                params={
                    "track_name": title,
                    "artist_name": ""
                }
            )
            if r.status_code == 200:
                data = r.json()
                if data and isinstance(data, list) and len(data) > 0:
                    track = data[0]
                    lyrics = track.get("plainLyrics") or track.get("syncedLyrics")
                    if lyrics:
                        return _clean(lyrics)

    except Exception as e:
        logger.debug(f"LRCLIB xətası: {e}")
        return None

    return None


# =====================================================
# 2️⃣ Lyrics.ovh API — Alternativ mənbə
# =====================================================
async def _lyrics_ovh_search(title: str, artist: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            # Format: https://lyrics.ovh/v1/{artist}/{title}
            # URL encode properly
            if artist:
                artist_clean = quote(artist, safe='')
                title_clean = quote(title, safe='')
                url = f"https://lyrics.ovh/v1/{artist_clean}/{title_clean}"
            else:
                title_clean = quote(title, safe='')
                url = f"https://lyrics.ovh/v1/{title_clean}"
            
            r = await client.get(url)
            if r.status_code == 200:
                data = r.json()
                lyrics = data.get("lyrics")
                if lyrics and lyrics.strip() and lyrics.lower() != "not found":
                    return _clean(lyrics)
    except Exception as e:
        logger.debug(f"Lyrics.ovh xətası: {e}")
        return None
    
    return None


# =====================================================
# 3️⃣ YouTube Captions — Son çarə
# =====================================================
async def _youtube_captions(title: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                "https://yt.lemnoslife.com/search",
                params={"q": title}
            )

            if r.status_code != 200:
                return None

            data = r.json()
            items = data.get("items", [])
            if not items:
                return None

            video_id = items[0].get("id", {}).get("videoId")
            if not video_id:
                return None

            # captions
            cap = await client.get(f"https://yt.lemnoslife.com/videos?part=captions&id={video_id}")
            if cap.status_code != 200:
                return None
            
            cap_data = cap.json()
            if not cap_data.get("items"):
                return None
                
            captions = cap_data["items"][0].get("captions", {}).get("captionTracks", [])
            if not captions:
                return None

            track_url = captions[0].get("baseUrl")
            if not track_url:
                return None
                
            xml_data = await client.get(track_url)
            if xml_data.status_code != 200:
                return None

            text = _clean_xml(xml_data.text)
            return text.strip() if text else None

    except Exception as e:
        logger.debug(f"YouTube captions xətası: {e}")
        return None


# =====================================================
# 🔧 CLEANERS
# =====================================================
def _clean(text: str) -> str:
    text = re.sub(r"<.*?>", "", text)
    text = text.replace("&amp;", "&")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_xml(text: str) -> str:
    text = re.sub(r"</?[^>]+>", "", text)
    text = text.replace("&amp;", "&")
    text = text.replace("&#39;", "'")
    text = text.replace("&quot;", '"')
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()
