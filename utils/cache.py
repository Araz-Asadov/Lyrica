"""
🚀 User Language Cache - Sürət optimizasiyası
"""
from typing import Optional
from datetime import datetime, timedelta
import asyncio

# User language cache with TTL
_user_lang_cache: dict[int, tuple[str, datetime]] = {}
_cache_ttl = timedelta(minutes=30)  # 30 dəqiqə cache (artırıldı performans üçün)
_max_cache_size = 10000  # Maksimum cache ölçüsü (memory limit)

# Background task for cache cleanup
_cleanup_task = None


def get_cached_lang(user_id: int) -> Optional[str]:
    """Get cached user language"""
    if user_id in _user_lang_cache:
        lang, cached_time = _user_lang_cache[user_id]
        if datetime.now() - cached_time < _cache_ttl:
            return lang
        else:
            del _user_lang_cache[user_id]
    return None


def set_cached_lang(user_id: int, lang: str):
    """Cache user language"""
    # Auto-cleanup if cache is too large
    if len(_user_lang_cache) >= _max_cache_size:
        _cleanup_expired_cache()
    
    _user_lang_cache[user_id] = (lang, datetime.now())


def _cleanup_expired_cache():
    """Remove expired cache entries"""
    now = datetime.now()
    expired_keys = [
        user_id for user_id, (_, cached_time) in _user_lang_cache.items()
        if now - cached_time >= _cache_ttl
    ]
    for key in expired_keys:
        _user_lang_cache.pop(key, None)
    
    # If still too large, remove oldest entries
    if len(_user_lang_cache) >= _max_cache_size:
        sorted_items = sorted(
            _user_lang_cache.items(),
            key=lambda x: x[1][1]  # Sort by cached_time
        )
        # Remove oldest 20% of entries
        remove_count = len(sorted_items) // 5
        for user_id, _ in sorted_items[:remove_count]:
            _user_lang_cache.pop(user_id, None)


def clear_user_cache(user_id: int):
    """Clear cache for specific user"""
    _user_lang_cache.pop(user_id, None)


def clear_all_cache():
    """Clear all cache"""
    _user_lang_cache.clear()


async def periodic_cache_cleanup():
    """Periodic cleanup task for cache"""
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        _cleanup_expired_cache()


def start_cache_cleanup_task():
    """Start background cache cleanup task"""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        loop = asyncio.get_event_loop()
        _cleanup_task = loop.create_task(periodic_cache_cleanup())

