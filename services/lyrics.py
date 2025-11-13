import httpx
import re
from typing import Optional

# 🧠 Cache
lyrics_cache: dict[str, str] = {}


# =====================================================
# 🔥 MAHNIN ADINI TƏMİZLƏYƏN FUNKSIYA
# =====================================================
def clean_title(title: str) -> str:
    # Remove brackets (Official Video), (4K), [Lyrics], etc.
    title = re.sub(r"\(.*?\)", "", title)
    title = re.sub(r"\[.*?\]", "", title)
    title = re.sub(r"Official|Video|Music|HD|4K|Audio|Clip", "", title, flags=re.I)
    title = re.sub(r"–|-", "-", title)
    title = re.sub(r"\s+", " ", title)
    return title.strip()


async def get_lyrics(title: str, artist: str = "") -> Optional[str]:
    """
    LRCLIB + YouTube Captions ilə super stabil söz tapma.
    """
    original_title = title
    title = clean_title(title)  # 🔥 Təmizlənmiş ad
    key = (title + artist).lower().strip()

    if key in lyrics_cache:
        return lyrics_cache[key]

    # 1️⃣ LRCLIB
    lyrics = await _lrclib_search(title, artist)
    if lyrics:
        lyrics_cache[key] = lyrics
        return lyrics

    # 2️⃣ YouTube captions
    lyrics = await _youtube_captions(original_title)
    if lyrics:
        lyrics_cache[key] = lyrics
        return lyrics

    return None


# =====================================================
# 1️⃣ NEW LRCLIB API — MÜKƏMMƏL
# =====================================================
async def _lrclib_search(title: str, artist: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(
                "https://lrclib.net/api/search",
                params={
                    "track_name": title,
                    "artist_name": artist
                }
            )
            if r.status_code != 200:
                return None

            data = r.json()
            if not data:
                return None

            # ən uyğun nəticə
            track = data[0]

            lyrics = track.get("plainLyrics") or track.get("syncedLyrics")
            if lyrics:
                return _clean(lyrics)

    except:
        return None

    return None


# =====================================================
# 2️⃣ YouTube Captions
# =====================================================
async def _youtube_captions(title: str) -> Optional[str]:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                "https://yt.lemnoslife.com/search",
                params={"q": title}
            )

            if r.status_code != 200:
                return None

            items = r.json().get("items", [])
            if not items:
                return None

            video_id = items[0]["id"]["videoId"]

            # captions
            cap = await client.get(f"https://yt.lemnoslife.com/videos?part=captions&id={video_id}")
            captions = cap.json()["items"][0].get("captions", [])

            if not captions:
                return None

            track = captions[0]["captionTracks"][0]["baseUrl"]
            xml_data = await client.get(track)

            text = _clean_xml(xml_data.text)
            return text.strip()

    except:
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
