"""
Music Recognition Service
Unified interface for music recognition from various sources.
"""
import os
import tempfile
import asyncio
import logging
import re
import hashlib
from typing import Optional, Literal, Dict, Any
from dataclasses import dataclass
import httpx

logger = logging.getLogger(__name__)


@dataclass
class RecognitionResult:
    """Music recognition result"""
    title: str
    artist: str
    album: Optional[str] = None
    confidence: float = 0.0
    duration: Optional[int] = None
    isrc: Optional[str] = None
    spotify_id: Optional[str] = None
    youtube_id: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.artist} — {self.title}"


class MusicRecognitionService:
    """Unified music recognition service with caching and metadata fallback"""

    def __init__(self):
        from config import settings
        self.acrcloud_api_key = os.getenv("ACRCLOUD_ACCESS_KEY", "")
        self.acrcloud_secret = os.getenv("ACRCLOUD_SECRET_KEY", "")
        self.audd_api_token = os.getenv("AUDD_API_TOKEN", "") or getattr(
            settings, "AUDD_API_TOKEN", ""
        )
        self._cache: Dict[str, RecognitionResult] = {}
        self._lock = asyncio.Lock()

        if self.audd_api_token:
            logger.info("✅ AudD API token loaded")
        else:
            logger.warning(
                "⚠️ AudD API token not found - recognition may not work"
            )

    def _get_file_hash(self, file_path: str) -> str:
        """Generate a hash of the file for caching"""
        h = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                h.update(chunk)
        return h.hexdigest()

    async def recognize_from_file(
        self,
        file_path: str,
        mode: Literal["default", "humming"] = "default",
        video_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[RecognitionResult]:
        """Recognize music from an audio file with caching and fallback."""
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return None

        # Try cache first
        file_hash = self._get_file_hash(file_path)
        cache_key = f"{file_hash}_{mode}"

        async with self._lock:
            if cache_key in self._cache:
                logger.debug("Cache hit for audio file")
                return self._cache[cache_key]

        # Try AudD first
        result: Optional[RecognitionResult] = None
        if self.audd_api_token:
            result = await self._recognize_audd(file_path, mode)

        # Fallback to ACRCloud if enabled (placeholder)
        if not result and self.acrcloud_api_key and self.acrcloud_secret:
            result = await self._recognize_acrcloud(file_path, mode)

        # Final fallback to video metadata
        if not result and video_info:
            result = self._get_metadata_fallback(video_info)
            if result:
                logger.info(f"Using metadata fallback: {result}")

        # Cache the result
        if result:
            async with self._lock:
                self._cache[cache_key] = result

        return result

    async def recognize_from_bytes(
        self,
        audio_data: bytes,
        mode: Literal["default", "humming"] = "default",
        video_info: Optional[Dict[str, Any]] = None,
    ) -> Optional[RecognitionResult]:
        """Recognize music from audio bytes with temp file handling."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            return await self.recognize_from_file(tmp_path, mode, video_info)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _get_metadata_fallback(
        self, video_info: Dict[str, Any]
    ) -> Optional[RecognitionResult]:
        """Fallback to yt-dlp metadata when recognition fails."""
        if not video_info:
            return None

        # Try different metadata fields
        title = (
            video_info.get("track")
            or video_info.get("alt_title")
            or video_info.get("title", "")
        )

        artist = video_info.get("artist") or video_info.get("uploader", "")

        # Clean up title
        if title:
            title = self._clean_title(title)

        # If we have both title and artist, use them
        if title and artist:
            return RecognitionResult(
                title=title,
                artist=artist,
                duration=video_info.get("duration"),
                youtube_id=video_info.get("id"),
                confidence=0.5,
            )

        # Try to parse from title if it contains a separator
        if " - " in (title or ""):
            parts = title.split(" - ", 1)
            if len(parts) == 2:
                artist, title = parts[0].strip(), parts[1].strip()
                return RecognitionResult(
                    title=title,
                    artist=artist,
                    duration=video_info.get("duration"),
                    youtube_id=video_info.get("id"),
                    confidence=0.4,
                )

        # Last resort - use uploader as artist
        if title:
            return RecognitionResult(
                title=title,
                artist=video_info.get("uploader", "Unknown Artist"),
                duration=video_info.get("duration"),
                youtube_id=video_info.get("id"),
                confidence=0.3,
            )

        return None

    def _clean_title(self, title: str) -> str:
        """Clean up video title by removing common suffixes and junk."""
        if not title:
            return ""

        # Common patterns to remove
        patterns = [
            r"\s*[-–—]?\s*(?:official.*(?:video|audio)|lyrics?|lyric video|audio|video|clip|1080p|720p|4k|hd|hdr?|full album|live|cover|remix|remastered?|explicit|clean|version|prod\.? by .+?)(?:\s*[\(\[]).*?[\)\]]|\s*$",
            r"[\(\[]\s*(?:of+icial\s*)?(?:music\s*)?(?:video|audio|lyrics?|lyric video|clip|1080p|720p|4k|hd|hdr?|full album|live|cover|remix|remastered?|explicit|clean|version|prod\.? by .+?)\s*[\)\]]",
            r"[\(\[]\s*\d{4}\s*[\)\]]",
            r"[\(\[]\s*(?:HD|HQ|4K|1080p|720p|480p)\s*[\)\]]",
            r"\s*ft\.?\s+([^)]+)",
            r"\s*feat\.?\s+([^)]+)",
        ]

        # Apply patterns
        for pattern in patterns:
            title = re.sub(pattern, "", title, flags=re.IGNORECASE)

        # Clean up any remaining special characters and extra spaces
        title = re.sub(r"\s+", " ", title).strip()
        title = re.sub(r"^\W+|\W+$", "", title)

        return title

    async def _recognize_audd(
        self,
        file_path: str,
        mode: str,
    ) -> Optional[RecognitionResult]:
        """Recognize using AudD.io API with multipart/form-data (correct fix)."""
        if not self.audd_api_token:
            logger.error("❌ No AudD token found")
            return None

        if not os.path.exists(file_path):
            logger.error(f"AudD: file not found: {file_path}")
            return None

        try:
            file_name = os.path.basename(file_path)
            logger.info(f"🎧 Sending audio to AudD (multipart): {file_name}")

            data = {
                "api_token": self.audd_api_token,
                "return": "spotify,youtube",
            }

            if mode == "humming":
                data["method"] = "recognize_with_offset"

            async with httpx.AsyncClient(timeout=30.0) as client:
                # open file inside context so it's open while request is sent
                with open(file_path, "rb") as f:
                    files = {
                        "file": (
                            file_name,  # filename
                            f,          # binary data
                            "audio/wav" # MIME type
                        )
                    }

                    response = await client.post(
                        "https://api.audd.io/",
                        data=data,
                        files=files,
                    )

            response.raise_for_status()
            result = response.json()

            if not isinstance(result, dict):
                logger.error("❌ Invalid AudD JSON response")
                return None

            status = result.get("status")
            track = result.get("result")

            # SUCCESS
            if status == "success" and track:
                title = (track.get("title") or "").strip() or "Unknown"
                artist = (track.get("artist") or "").strip() or "Unknown"

                # AudD score is usually 0–100
                try:
                    score_raw = track.get("score", 0)
                    score = float(score_raw) / 100.0
                except Exception:
                    score = 0.0

                logger.info(
                    f"🎶 Recognized by AudD: {artist} — {title} | confidence={score}"
                )

                spotify = track.get("spotify") or {}
                youtube = track.get("youtube") or {}

                return RecognitionResult(
                    title=title,
                    artist=artist,
                    album=track.get("album"),
                    confidence=score,
                    duration=track.get("duration"),
                    isrc=track.get("isrc"),
                    spotify_id=spotify.get("id"),
                    youtube_id=youtube.get("id"),
                )

            # FAIL (AudD gave an error)
            err_msg = (
                result.get("error", {}) or {}
            ).get("error_message", "Unknown error")
            logger.warning(f"⚠️ AudD recognition failed: {err_msg}")
            return None

        except Exception as e:
            logger.error(f"❌ AudD recognition exception: {e}", exc_info=True)
            return None

    def _read_file_chunk(self, file_path: str, size: int) -> bytes:
        """Helper to read a chunk of a file synchronously."""
        with open(file_path, "rb") as f:
            return f.read(size)

    async def _recognize_acrcloud(
        self,
        file_path: str,
        mode: str,
    ) -> Optional[RecognitionResult]:
        """ACRCloud recognition placeholder."""
        return None


# Singleton instance
_recognition_service: Optional[MusicRecognitionService] = None


def get_recognition_service() -> MusicRecognitionService:
    """Get global recognition service instance."""
    global _recognition_service
    if _recognition_service is None:
        _recognition_service = MusicRecognitionService()
    return _recognition_service
