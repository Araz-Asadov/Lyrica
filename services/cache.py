"""
Smart Cache Service (RAM-based)
Provides in-memory caching with TTL, hit/miss tracking for lyrics & translations.
"""

import time
from typing import Optional, Tuple
from config import settings


class SmartCache:
    """
    In-memory cache with TTL and hit/miss statistics.
    """

    def __init__(self, default_ttl_seconds: int = 3600):
        self._cache: dict[str, Tuple[float, any]] = {}  # key -> (expires_at, value)
        self._hits: int = 0
        self._misses: int = 0
        self.default_ttl = default_ttl_seconds

    def get(self, key: str) -> Optional[any]:
        """
        Get value from cache if not expired.
        Returns None on miss or expiration.
        """
        if key not in self._cache:
            self._misses += 1
            return None

        expires_at, value = self._cache[key]
        if time.time() > expires_at:
            # Expired
            del self._cache[key]
            self._misses += 1
            return None

        self._hits += 1
        return value

    def set(self, key: str, value: any, ttl: Optional[int] = None) -> None:
        """
        Store value in cache with given TTL (seconds).
        If ttl is None, uses default_ttl.
        """
        ttl_to_use = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + ttl_to_use
        self._cache[key] = (expires_at, value)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def stats(self) -> dict:
        """Return current statistics."""
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
        }


# ========================================================
# Global Cache Instances
# ========================================================

# Lyrics cache: keyed by title+artist
lyrics_cache = SmartCache(default_ttl_seconds=settings.CACHE_EXPIRATION_MINUTES * 60)

# Translation cache: keyed by song_id+target_lang
translation_cache = SmartCache(default_ttl_seconds=settings.CACHE_EXPIRATION_MINUTES * 60)


# ========================================================
# Helper Functions
# ========================================================

def lyrics_key(title: str, artist: str) -> str:
    """Generate cache key for lyrics based on title+artist."""
    return f"lyrics:{title.lower().strip()}:{artist.lower().strip()}"


def translation_key(song_id: int, target_lang: str) -> str:
    """Generate cache key for lyrics translation."""
    return f"lyrics:{song_id}:{target_lang.lower()}"


def get_cache_stats() -> dict:
    """
    Aggregate statistics from all cache instances.
    Returns dict with combined hits, misses, and sizes.
    """
    lyrics_stats = lyrics_cache.stats()
    trans_stats = translation_cache.stats()

    return {
        "lyrics_hits": lyrics_stats["hits"],
        "lyrics_misses": lyrics_stats["misses"],
        "lyrics_size": lyrics_stats["size"],
        "translation_hits": trans_stats["hits"],
        "translation_misses": trans_stats["misses"],
        "translation_size": trans_stats["size"],
        "total_hits": lyrics_stats["hits"] + trans_stats["hits"],
        "total_misses": lyrics_stats["misses"] + trans_stats["misses"],
    }
