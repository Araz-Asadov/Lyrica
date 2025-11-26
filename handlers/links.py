from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from db import SessionLocal
from models import User, Song, RequestLog
from i18n import t
from i18n import _load as _lang
from keyboards import song_actions
from services.youtube import is_youtube_link, download_from_url, YTResult
from datetime import datetime, timezone
import logging
import os

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text & ~F.via_bot & ~F.text.startswith("/"))
async def on_link(m: Message):
    """Handle YouTube links"""
    text = m.text.strip()
    
    logger.info(f"[LINKS] Handler called with text: {text[:100]}")
    
    # Skip TikTok and Instagram links - they are handled by recognition.py
    if "tiktok.com" in text.lower() or "vm.tiktok.com" in text.lower() or "instagram.com" in text.lower():
        logger.info(f"[LINKS] Skipping TikTok/Instagram link")
        return
    
    if not is_youtube_link(text):
        logger.info(f"[LINKS] Not YouTube link, returning")
        # Not a YouTube link, let search handler process it
        return
    
    logger.info(f"🔗 YouTube link handler processing: {text[:50]}")
    
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == m.from_user.id))
        ).scalars().first()
    
    lang = user.language if user and getattr(user, "language", None) else "az"
    
    await m.answer(t(lang, "downloading"))
    
    try:
        yt: YTResult = await download_from_url(text)
        
        # Verify file exists
        if not yt.file_path or not os.path.exists(yt.file_path):
            logger.error(f"Downloaded file not found: {yt.file_path}")
            await m.answer("❌ Yüklənmiş fayl tapılmadı. Zəhmət olmasa yenidən cəhd edin.")
            return
        
    except Exception as e:
        logger.error(f"Error downloading from YouTube URL: {e}", exc_info=True)
        await m.answer("❌ Yükləmə xətası baş verdi.")
        return
    
    # Save to database
    async with SessionLocal() as s:
        song = (
            await s.execute(select(Song).where(Song.youtube_id == yt.youtube_id))
        ).scalars().first()
        
        if not song:
            song = Song(
                youtube_id=yt.youtube_id,
                title=yt.title,
                artist=yt.artist,
                duration=yt.duration,
                file_path=yt.file_path,
                thumbnail=yt.thumbnail,
            )
            s.add(song)
            await s.commit()
            await s.refresh(song)
        
        # Log request
        if user:
            s.add(
                RequestLog(
                    user_id=user.id,
                    query=text,
                    via_voice=False,
                    matched_song_id=song.id,
                )
            )
            await s.commit()
    
    # Send result
    msg = t(
        lang,
        "search_result",
        title=yt.title,
        artist=yt.artist,
        duration=yt.duration,
    )

    # ✅ FIXED: Send song.id (DB ID), not YouTube ID
    await m.answer(msg, reply_markup=song_actions(_lang(lang), str(song.id)))
