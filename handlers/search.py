from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from sqlalchemy import select
from db import SessionLocal
from models import User, Song, Favorite, RequestLog
from i18n import t
from keyboards import song_actions, effects_menu
from services.youtube import search_and_download, YTResult
from services.lyrics import get_lyrics
from services.audio import apply_effects
from utils.common import has_ffmpeg
from deep_translator import GoogleTranslator
from datetime import datetime
import os

router = Router()

# 🔐 User → Song lyrics memory
user_lyrics_memory: dict[tuple[int, str], str] = {}


async def _get_user_lang(user_id: int) -> str:
    """Get user language from database with cache"""
    from utils.cache import get_cached_lang, set_cached_lang
    
    # Check cache first
    cached_lang = get_cached_lang(user_id)
    if cached_lang:
        return cached_lang
    
    # Query database
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == user_id))).scalars().first()
        lang = user.language if user else "az"
        set_cached_lang(user_id, lang)  # Cache it
        return lang


# =================================================================
# 🔍 SONG SEARCH
# =================================================================
@router.message(F.text & ~F.via_bot & ~F.text.startswith("/"))
async def on_query(m: Message):
    # Skip if it's a link (handled by links.py)
    from services.social_media import is_tiktok_link, is_instagram_link, is_youtube_link
    text = m.text.strip()
    if is_tiktok_link(text) or is_instagram_link(text) or is_youtube_link(text):
        return  # Let links handler process it
    
    # Get user language (cached)
    lang = await _get_user_lang(m.from_user.id)

    if not has_ffmpeg():
        await m.answer(t(lang, "no_ffmpeg"))
        return

    await m.answer(t(lang, "downloading"))

    try:
        yt: YTResult = await search_and_download(m.text.strip())
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Search error for query '{m.text.strip()}': {e}", exc_info=True)
        
        error_msg = str(e)
        # Provide user-friendly error messages
        if "tapılmadı" in error_msg.lower() or "not found" in error_msg.lower():
            await m.answer(f"❌ {t(lang, 'song_not_found')}\n\n🔍 Sorğu: {m.text.strip()}")
        else:
            await m.answer(f"❌ {t(lang, 'error_search_download')}\n\n{error_msg}")
        return

    # Optimized: Single database session for all operations
    async with SessionLocal() as s:
        # Get user (don't create if not exists - lazy creation)
        user = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
        user_id = user.id if user else None
        
        # Get or create song
        song = (await s.execute(select(Song).where(Song.youtube_id == yt.youtube_id))).scalars().first()
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
            await s.flush()  # Flush to get song.id without commit

        # Add request log (only if user exists - skip if not to avoid errors)
        if user_id:
            s.add(RequestLog(
                user_id=user_id,
                query=m.text.strip(),
                via_voice=False,
                matched_song_id=song.id,
            ))
        await s.commit()  # Single commit for all operations

    msg = t(lang, "search_result", title=yt.title, artist=yt.artist, duration=yt.duration)
    await m.answer(msg, reply_markup=song_actions(_lang(lang), yt.youtube_id))



# =================================================================
# 🎵 DOWNLOAD SONG
# =================================================================
@router.callback_query(F.data.startswith("song:dl:"))
async def on_download(c: CallbackQuery):
    lang = await _get_user_lang(c.from_user.id)
    await c.answer(t(lang, "sending"))

    yt_id = c.data.split(":")[-1]

    async with SessionLocal() as s:
        song = (await s.execute(select(Song).where(Song.youtube_id == yt_id))).scalars().first()

        if song:
            song.play_count += 1
            song.last_played = datetime.utcnow()
            await s.commit()

    if not song:
        await c.message.answer("❌ Song not found.")
        return

    try:
        file = FSInputFile(song.file_path, filename=f"{song.title}.mp3")
        await c.message.answer_document(file)
    except Exception as e:
        lang = await _get_user_lang(c.from_user.id)
        await c.message.answer(t(lang, "sending_error", error=str(e)))



# =================================================================
# 💬 LYRICS
# =================================================================
@router.callback_query(F.data.startswith("song:ly:"))
async def on_lyrics(c: CallbackQuery):
    await c.answer()

    yt_id = c.data.split(":")[-1]

    async with SessionLocal() as s:
        song = (await s.execute(select(Song).where(Song.youtube_id == yt_id))).scalars().first()
        user = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()

    lang = user.language if user else "en"

    if not song:
        await c.message.answer(t(lang, "song_not_found"))
        return

    lyrics = await get_lyrics(song.title, song.artist)

    if lyrics:
        user_lyrics_memory[(c.from_user.id, yt_id)] = lyrics

        await c.message.answer(lyrics)
        translate_prompts = {
            "az": "🌍 Sözləri tərcümə et:",
            "en": "🌍 Translate the lyrics:",
            "ru": "🌍 Перевести текст:"
        }
        await c.message.answer(
            translate_prompts.get(lang, translate_prompts["en"]),
            reply_markup=_translate_button(yt_id)
        )
    else:
        await c.message.answer(t(lang, "lyrics_not_found"))



# =================================================================
# 🌐 TRANSLATE
# =================================================================
@router.callback_query(F.data.startswith("song:tr:"))
async def on_translate(c: CallbackQuery):
    await c.answer()

    yt_id = c.data.split(":")[-1]
    text = user_lyrics_memory.get((c.from_user.id, yt_id))

    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()

    lang = user.language if user else "en"

    if not text:
        await c.message.answer(t(lang, "open_lyrics_first"))
        return

    await c.message.answer(t(lang, "translating"))

    try:
        translated = GoogleTranslator(source="auto", target=lang).translate(text)
    except Exception as e:
        await c.message.answer(t(lang, "translation_error", error=str(e)))
        return

    await c.message.answer(t(lang, "translation", text=translated))



# =================================================================
# ⭐ FAVORITES
# =================================================================
@router.callback_query(F.data.startswith("song:fav:"))
async def on_fav(c: CallbackQuery):
    await c.answer()

    yt_id = c.data.split(":")[-1]

    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()
        song = (await s.execute(select(Song).where(Song.youtube_id == yt_id))).scalars().first()

        if not (user and song):
            lang = await _get_user_lang(c.from_user.id)
            await c.message.answer(t(lang, "error_occurred"))
            return

        existing = (
            await s.execute(
                select(Favorite).where(
                    Favorite.user_id == user.id,
                    Favorite.song_id == song.id,
                )
            )
        ).scalars().first()

        if existing:
            await s.delete(existing)
            await s.commit()
            lang = await _get_user_lang(c.from_user.id)
            await c.message.answer(t(lang, "fav_removed"))
        else:
            s.add(Favorite(user_id=user.id, song_id=song.id))
            await s.commit()
            lang = await _get_user_lang(c.from_user.id)
            await c.message.answer(t(lang, "fav_added"))



# =================================================================
# 🎚️ EFFECTS MENU
# =================================================================
@router.callback_query(F.data.startswith("song:fx:"))
async def on_effects_menu(c: CallbackQuery):
    await c.answer()

    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()

    lang = user.language if user else "en"

    await c.message.answer(
        t(lang, "choose_effect"),
        reply_markup=effects_menu(_lang(lang))
    )



# =================================================================
# 🎚 APPLY EFFECT
# =================================================================
@router.callback_query(F.data.startswith("fx:"))
async def on_effect_apply(c: CallbackQuery):
    lang = await _get_user_lang(c.from_user.id)
    await c.answer(t(lang, "processing"))

    parts = c.data.split(":")
    kind, val = parts[1], parts[2]

    async with SessionLocal() as s:
        song = (await s.execute(select(Song).order_by(Song.last_played.desc()))).scalars().first()
        user = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()

    lang = await _get_user_lang(c.from_user.id)
    if not song:
        await c.message.answer(t(lang, "no_recent_song"))
        return

    if not has_ffmpeg():
        await c.message.answer(t(lang, "no_ffmpeg"))
        return

    effects = {}

    if kind == "bass": effects["bass_db"] = float(val)
    if kind == "treble": effects["treble_db"] = float(val)
    if kind == "reverb": effects["reverb"] = True
    if kind == "echo": effects["echo"] = True
    if kind == "pitch": effects["pitch_semitones"] = float(val)
    if kind == "speed": effects["speed"] = float(val)

    new_path = apply_effects(song.file_path, None, effects)

    if not os.path.exists(new_path):
        lang = await _get_user_lang(c.from_user.id)
        await c.message.answer(t(lang, "failed_generate"))
        return

    file = FSInputFile(new_path, filename=os.path.basename(new_path))
    await c.message.answer_document(file)



# =================================================================
# 🌍 UNIVERSAL TRANSLATE BUTTON
# =================================================================
def _translate_button(yt_id: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Translate", callback_data=f"song:tr:{yt_id}")]
        ]
    )



# =================================================================
# LANGUAGE LOADER
# =================================================================
def _lang(code: str):
    from i18n import _load
    return _load(code)
