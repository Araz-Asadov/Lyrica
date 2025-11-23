import asyncio
import os
import re
from dataclasses import dataclass
from typing import Optional
import yt_dlp
from config import settings
from utils.common import ensure_ffmpeg


@dataclass
class YTResult:
    youtube_id: str
    title: str
    artist: str
    duration: int
    file_path: str
    thumbnail: str


def sanitize(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()


# --------------------------------------------------
#  🔥 SUPER OPTIMIZED SETTINGS — FIXED VERSION
# --------------------------------------------------
def _ydl_opts(template: str):
    return {
        "format": "bestaudio/best",                     # FIXED
        "outtmpl": template,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "cachedir": False,
        "ignoreerrors": True,
        "nopart": True,  
        "concurrent_fragment_downloads": 3,
        "retries": 3,
        "fragment_retries": 3,
        "extract_flat": False,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"               # FIXED
            }
        ],
    }


async def search_and_download(query: str) -> YTResult:
    ensure_ffmpeg()
    os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)

    # --------------------------------------------------
    # TikTok / Instagram / YouTube link recognition
    # --------------------------------------------------
    if "tiktok.com" in query or "instagram.com" in query:
        search_term = query  # link birbaşa işləyir
    elif query.startswith("http"):
        search_term = query
    else:
        search_term = f"ytsearch10:{query}"            # FIXED

    template = os.path.join(settings.DOWNLOAD_DIR, "%(id)s.%(ext)s")

    for attempt in range(3):
        try:
            info = await _async_extract(search_term, template)
            if info:
                break
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(1)
            else:
                raise RuntimeError(f"YouTube download error: {e}")

    if not info:
        raise RuntimeError("Video tapılmadı və ya yükləmə mümkün olmadı.")

    if "entries" in info:
        info = info["entries"][0]

    youtube_id = info.get("id")
    title = sanitize(info.get("title") or "Unknown")
    artist = info.get("artist") or info.get("uploader") or "Unknown"
    duration = int(info.get("duration") or 0)

    thumb = ""
    if info.get("thumbnails"):
        thumb = info["thumbnails"][-1]["url"]

    file_path = os.path.join(settings.DOWNLOAD_DIR, f"{youtube_id}.mp3")

    return YTResult(
        youtube_id=youtube_id,
        title=title,
        artist=artist,
        duration=duration,
        file_path=file_path,
        thumbnail=thumb,
    )


async def _async_extract(query: str, template: str):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _blocking_extract, query, template)


def _blocking_extract(query: str, template: str):
    opts = _ydl_opts(template)
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(query, download=True)
