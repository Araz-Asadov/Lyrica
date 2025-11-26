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
from services.search_service import get_search_service, SearchResult
from services.lyrics import get_lyrics
from services.audio import apply_effects
from utils.common import has_ffmpeg
from deep_translator import GoogleTranslator
from datetime import datetime, timezone
import os
import logging

router = Router()
logger = logging.getLogger(__name__)

# 🔐 user+song əsaslı söz yaddaşı
user_lyrics_memory: dict[tuple[int, str], str] = {}

# Initialize search service
search_service = get_search_service()

# =================================================================
# 🔍 UNIFIED SEARCH HANDLER
# =================================================================
@router.message(F.text & ~F.via_bot & ~F.text.startswith("/"))
async def on_query(m: Message):
    """
    Unified search handler that processes:
    - YouTube search queries
    - YouTube/TikTok/Instagram links
    - General music search terms
    """
    text = m.text.strip()
    logger.info(f"[SEARCH] Processing query: {text[:100]}")
    
    # Get user language
    async with SessionLocal() as session:
        user = await session.get(User, m.from_user.id)
        lang = user.language if user else 'az'
    
    # Show typing action
    await m.bot.send_chat_action(m.chat.id, "typing")
    
    try:
        # Process the query using our unified search service
        results = await search_service.search_from_any_source(text)
        
        if not results:
            await m.answer(t(lang, "no_results"))
            return
            
        # If we have exactly one result, process it directly
        if len(results) == 1:
            await process_search_result(m, results[0], lang)
            return
            
        # If we have multiple results, show them to the user
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for i, result in enumerate(results[:5], 1):  # Show max 5 results
            title = f"{i}. {result.artist} - {result.title}" if result.artist else result.title
            callback_data = f"search_select:{result.source}:{getattr(result, f'{result.source}_id', '')}"
            keyboard.inline_keyboard.append([
                InlineKeyboardButton(text=title[:64], callback_data=callback_data)
            ])
            
        await m.answer("🔍 Aşağıdakı nəticələrdən birini seçin:", reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        await m.answer(t(lang, "error_occurred"))

async def process_search_result(m: Message, result: SearchResult, lang: str):
    """Process a single search result and send it to the user"""
    try:
        # If we have a file path, send the audio
        if result.file_path and os.path.exists(result.file_path):
            audio = FSInputFile(result.file_path)
            from i18n import _load as _lang
            await m.answer_audio(
                audio=audio,
                title=result.title,
                performer=result.artist,
                reply_markup=song_actions(_lang(lang), result.youtube_id)
            )
        else:
            # If no file path, download the song first
            await m.answer(t(lang, "downloading"))
            
            try:
                # Download the song
                if result.source == 'youtube' and result.youtube_id:
                    from services.youtube import search_and_download
                    
                    # Try to download using the search query or direct download
                    search_query = f"{result.artist} {result.title}".strip()
                    yt_result = await search_and_download(search_query)
                    
                    if yt_result and yt_result.file_path and os.path.exists(yt_result.file_path):
                        # Save to database
                        await save_song_to_db(yt_result, m.from_user.id, search_query)
                        
                        # Send the audio file
                        from i18n import _load as _lang
                        audio = FSInputFile(yt_result.file_path)
                        await m.answer_audio(
                            audio=audio,
                            title=yt_result.title,
                            performer=yt_result.artist,
                            reply_markup=song_actions(_lang(lang), yt_result.youtube_id)
                        )
                    else:
                        # If download failed, show info with download button
                        from i18n import _load as _lang
                        await m.answer(
                            f"🎵 {result.artist} - {result.title}",
                            reply_markup=song_actions(_lang(lang), result.youtube_id)
                        )
                else:
                    # For non-YouTube sources, show info with download button
                    from i18n import _load as _lang
                    await m.answer(
                        f"🎵 {result.artist} - {result.title}",
                        reply_markup=song_actions(_lang(lang), result.youtube_id)
                    )
                    
            except Exception as download_error:
                logger.error(f"Failed to download song: {download_error}")
                # Show info with download button as fallback
                from i18n import _load as _lang
                await m.answer(
                    f"🎵 {result.artist} - {result.title}",
                    reply_markup=song_actions(_lang(lang), result.youtube_id)
                )
            
        # Log the request
        await log_request(m, result)
        
    except Exception as e:
        logger.error(f"Error processing search result: {e}", exc_info=True)
        await m.answer(t(lang, "error_processing_media"))

async def save_song_to_db(yt_result, user_id: int, query: str):
    """Save downloaded song to database"""
    try:
        async with SessionLocal() as s:
            # Check if song already exists
            existing_song = (
                await s.execute(select(Song).where(Song.youtube_id == yt_result.youtube_id))
            ).scalars().first()
            
            if not existing_song:
                song = Song(
                    youtube_id=yt_result.youtube_id,
                    title=yt_result.title,
                    artist=yt_result.artist,
                    duration=yt_result.duration,
                    file_path=yt_result.file_path,
                    thumbnail=yt_result.thumbnail,
                )
                s.add(song)
                await s.commit()
                await s.refresh(song)
            else:
                # Update file path if it was missing
                if not existing_song.file_path and yt_result.file_path:
                    existing_song.file_path = yt_result.file_path
                    await s.commit()
                song = existing_song
            
            # Log the request
            user = await s.get(User, user_id)
            if user:
                s.add(
                    RequestLog(
                        user_id=user.id,
                        query=query,
                        via_voice=False,
                        matched_song_id=song.id,
                    )
                )
                await s.commit()
                
    except Exception as e:
        logger.error(f"Failed to save song to database: {e}")

async def log_request(m: Message, result: SearchResult):
    """Log the user's request to the database"""
    try:
        async with SessionLocal() as session:
            # Log the request
            request = RequestLog(
                user_id=m.from_user.id,
                query=m.text,
                source=result.source,
                title=result.title,
                artist=result.artist,
                duration=result.duration,
                created_at=datetime.now(timezone.utc)
            )
            session.add(request)
            await session.commit()
    except Exception as e:
        logger.error(f"Error logging request: {e}")
        # Don't fail the whole request if logging fails
    
    logger.info(f"[SEARCH] Processing search query")
    
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == m.from_user.id))
        ).scalars().first()

    lang = user.language if user and getattr(user, "language", None) else "az"

    if not has_ffmpeg():
        await m.answer(t(lang, "no_ffmpeg"))
        return

    # Send searching message
    search_msg = await m.answer("🔍 Axtarılır...")

    try:
        # Search for multiple results
        results = await search_multiple(m.text.strip(), max_results=5)
        
        if not results:
            await search_msg.edit_text("❌ Nəticə tapılmadı. Zəhmət olmasa başqa sorğu yazın.")
            return

        # Show results with inline keyboard
        from i18n import _load as _lang
        lang_texts = _lang(lang)
        
        results_text = f"🔍 <b>{len(results)} nəticə tapıldı:</b>\n\n"
        keyboard_buttons = []
        
        for idx, result in enumerate(results, 1):
            # Format duration as MM:SS
            if result.duration > 0:
                minutes = result.duration // 60
                seconds = result.duration % 60
                duration_str = f"{minutes}:{seconds:02d}"
            else:
                duration_str = "?"
            
            results_text += f"{idx}. <b>{result.title}</b>\n"
            results_text += f"   👤 {result.artist} | ⏱ {duration_str}\n\n"
            
            # Add button for each result (truncate title if too long)
            button_text = f"{idx}. {result.title[:35]}"
            if len(result.title) > 35:
                button_text += "..."
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"search:select:{result.youtube_id}"
                )
            ])
        
        await search_msg.edit_text(
            results_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard_buttons),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        await search_msg.edit_text("❌ Axtarış zamanı xəta baş verdi.")


# =================================================================
# 🔍 SEARCH RESULT SELECTION
# =================================================================
@router.callback_query(F.data.startswith("search:select:"))
async def on_search_select(c: CallbackQuery):
    """Handle selection of a search result"""
    await c.answer()
    
    yt_id = c.data.split(":")[-1]
    
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()
    
    lang = user.language if user and getattr(user, "language", None) else "az"
    
    # Check if song already exists in DB
    async with SessionLocal() as s:
        song = (
            await s.execute(select(Song).where(Song.youtube_id == yt_id))
        ).scalars().first()
    
    if not song:
        # Download the selected song
        await c.message.answer(t(lang, "downloading"))
        
        try:
            from services.youtube import download_from_url
            yt_url = f"https://www.youtube.com/watch?v={yt_id}"
            yt_result = await download_from_url(yt_url)
            
            # Save to database
            async with SessionLocal() as s:
                # Check if song already exists
                existing_song = (
                    await s.execute(select(Song).where(Song.youtube_id == yt_result.youtube_id))
                ).scalars().first()
                
                if existing_song:
                    song = existing_song
                    # Update file path if it was missing
                    if not existing_song.file_path and yt_result.file_path:
                        existing_song.file_path = yt_result.file_path
                        await s.commit()
                else:
                    song = Song(
                        youtube_id=yt_result.youtube_id,
                        title=yt_result.title,
                        artist=yt_result.artist,
                        duration=yt_result.duration,
                        file_path=yt_result.file_path,
                        thumbnail=yt_result.thumbnail,
                    )
                    s.add(song)
                    await s.commit()
                    await s.refresh(song)
                
                # Log request
                if user:
                    s.add(
                        RequestLog(
                            user_id=user.id,
                            query=yt_result.title,
                            via_voice=False,
                            matched_song_id=song.id,
                        )
                    )
                    await s.commit()
            
            # Send result
            from i18n import _load as _lang
            result_text = t(
                lang,
                "search_result",
                title=yt_result.title,
                artist=yt_result.artist,
                duration=yt_result.duration,
            )
            
            await c.message.answer(result_text)
            await c.message.answer(
                t(lang, "recognition.song_info"),
                reply_markup=song_actions(_lang(lang), song.youtube_id)
            )
        except Exception as e:
            logger.error(f"Error downloading selected song: {e}", exc_info=True)
            await c.message.answer("❌ Mahnı yüklənə bilmədi.")
    else:
        # Song already exists, just show it
        from i18n import _load as _lang
        result_text = t(
            lang,
            "search_result",
            title=song.title,
            artist=song.artist,
            duration=song.duration,
        )
        
        await c.message.answer(result_text)
        await c.message.answer(
            t(lang, "recognition.song_info"),
            reply_markup=song_actions(_lang(lang), song.youtube_id)
        )


# =================================================================
# 🎵 MAHNINI ENDİR
# =================================================================
@router.callback_query(F.data.startswith("song:dl:"))
async def on_download(c: CallbackQuery):
    # Immediately answer the callback query to prevent timeout
    await c.answer()

    yt_id = c.data.split(":")[-1]

    async with SessionLocal() as s:
        song = (
            await s.execute(select(Song).where(Song.youtube_id == yt_id))
        ).scalars().first()

        if song:
            song.play_count += 1
            song.last_played = datetime.now(timezone.utc)
            await s.commit()

    if not song:
        await c.message.answer("Song not found")
        return

    # Inform the user if the file needs to be downloaded
    if not song.file_path or not os.path.exists(song.file_path):
        await c.message.answer("⏳ Fayl yüklənir...")
        
        try:
            from services.youtube import download_from_url, search_and_download
            
            # If it's a YouTube ID, try to download
            if song.youtube_id and len(song.youtube_id) == 11 and not song.youtube_id.startswith(("tiktok_", "instagram_", "rec_")):
                yt_url = f"https://www.youtube.com/watch?v={song.youtube_id}"
                yt_result = await download_from_url(yt_url)
                song.file_path = yt_result.file_path
            else:
                search_query = f"{song.artist} {song.title}"
                yt_result = await search_and_download(search_query)
                song.file_path = yt_result.file_path
                song.youtube_id = yt_result.youtube_id
            
            # Update database
            async with SessionLocal() as s:
                db_song = (await s.execute(select(Song).where(Song.id == song.id))).scalars().first()
                if db_song:
                    db_song.file_path = song.file_path
                    db_song.youtube_id = song.youtube_id
                    await s.commit()

        except Exception as download_error:
            logger.error(f"Failed to download song: {download_error}")
            await c.message.answer("❌ Mahnı yüklənə bilmədi. Zəhmət olmasa yenidən cəhd edin.")
            return

    # Check file again
    if not os.path.exists(song.file_path):
        await c.message.answer("❌ Fayl tapılmadı.")
        return

    try:
        # Check file size (Telegram limit is 50MB)
        file_size = os.path.getsize(song.file_path)
        if file_size > 50 * 1024 * 1024:  # 50MB
            await c.message.answer("❌ Fayl çox böyükdür (50MB limit).")
            return
        
        file = FSInputFile(song.file_path, filename=f"{song.title[:50]}.mp3")
        await c.message.answer_document(file)
    except Exception as e:
        logger.error(f"Error sending file: {e}", exc_info=True)
        await c.message.answer(f"❌ Göndərmə xətası: {str(e)[:100]}")


# =================================================================
# 💬 MAHNININ SÖZLƏRİ
# =================================================================
@router.callback_query(F.data.startswith("song:ly:"))
async def on_lyrics(c: CallbackQuery):
    await c.answer()  # Dərhal callback cavabı ver

    yt_id = c.data.split(":")[-1]

    async with SessionLocal() as s:
        song = (
            await s.execute(select(Song).where(Song.youtube_id == yt_id))
        ).scalars().first()
        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()

    lang = user.language if user and getattr(user, "language", None) else "az"

    if not song:
        await c.message.answer("❌ Mahnı tapılmadı.")
        return

    # Loading mesajı
    loading_msg = await c.message.answer("⏳ Sözlər axtarılır...")

    try:
        lyrics = await get_lyrics(song.title, song.artist)

        if lyrics:
            user_lyrics_memory[(c.from_user.id, yt_id)] = lyrics
            await loading_msg.delete()
            await c.message.answer(lyrics)
            await c.message.answer(
                "🔁 Tərcümə etmək üçün:",
                reply_markup=_translate_button(yt_id),
            )
        else:
            await loading_msg.edit_text(t(lang, "lyrics_not_found"))
    except Exception as e:
        await loading_msg.edit_text(f"❌ Xəta: {e}")


# =================================================================
# 🌐 TƏRCÜMƏ
# =================================================================
@router.callback_query(F.data.startswith("song:tr:"))
async def on_translate(c: CallbackQuery):
    yt_id = c.data.split(":")[-1]
    text = user_lyrics_memory.get((c.from_user.id, yt_id))

    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()
    lang = user.language if user and getattr(user, "language", None) else "az"

    if not text:
        await c.message.answer("❗ Əvvəl sözləri aç (Sözlər düyməsi).")
        return

    await c.message.answer("🔄 Tərcümə olunur...")

    try:
        translated = GoogleTranslator(source="auto", target=lang).translate(text)
    except Exception as e:
        await c.message.answer(f"❌ Tərcümə xətası: {e}")
        return

    await c.message.answer(f"🇬🇧 ➜ {lang.upper()}\n\n{translated}")
    await c.answer()


# =================================================================
# ⭐ FAVORİTLƏR
# =================================================================
@router.callback_query(F.data.startswith("song:fav:"))
async def on_fav(c: CallbackQuery):
    yt_id = c.data.split(":")[-1]

    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()
        song = (
            await s.execute(select(Song).where(Song.youtube_id == yt_id))
        ).scalars().first()

        if not (user and song):
            await c.answer("⚠️ Error")
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
            await c.answer(_lang(user.language).get("fav_removed", "❌ Silindi"))
        else:
            s.add(Favorite(user_id=user.id, song_id=song.id))
            await s.commit()
            await c.answer(_lang(user.language).get("fav_added", "⭐ Əlavə edildi"))


# =================================================================
# 🎚️ EFFEKT MENYUSU
# =================================================================
@router.callback_query(F.data.startswith("song:fx:"))
async def on_effects_menu(c: CallbackQuery):
    yt_id = c.data.split(":")[-1]
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()
    lang = user.language if user and getattr(user, "language", None) else "az"

    await c.message.answer(
        t(lang, "choose_effect"),
        reply_markup=effects_menu(_lang(lang), yt_id),
    )
    await c.answer()


# =================================================================
# 🎚️ EFFEKT TƏTBİQİ
# =================================================================
@router.callback_query(F.data.startswith("fx:"))
async def on_effect_apply(c: CallbackQuery):
    await c.answer()

    parts = c.data.split(":")
    kind, val = parts[1], parts[2]
    
    # Extract yt_id from callback data if present (format: fx:kind:val:yt_id)
    yt_id = None
    if len(parts) > 3:
        yt_id = parts[3]

    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()
        
        # Try to get song by yt_id first, fallback to last played
        if yt_id:
            song = (
                await s.execute(select(Song).where(Song.youtube_id == yt_id))
            ).scalars().first()
        else:
            song = (
                await s.execute(select(Song).order_by(Song.last_played.desc()))
            ).scalars().first()

    lang = user.language if user and getattr(user, "language", None) else "az"

    if not song:
        await c.message.answer("No context song", show_alert=True)
        return

    if not has_ffmpeg():
        await c.message.answer(t(lang, "no_ffmpeg"))
        return

    await c.message.answer(t(lang, "applying_effect"))

    effects: dict = {}

    if kind == "bass":
        effects["bass_db"] = float(val)
    if kind == "treble":
        effects["treble_db"] = float(val)
    if kind == "reverb":
        effects["reverb"] = True
    if kind == "echo":
        effects["echo"] = True
    if kind == "pitch":
        effects["pitch_semitones"] = float(val)
    if kind == "speed":
        effects["speed"] = float(val)

    try:
        new_path = apply_effects(song.file_path, None, effects)
    except Exception as e:
        await c.message.answer(f"❌ Effekt tətbiq xətası: {e}")
        return

    if not os.path.exists(new_path):
        await c.message.answer("❌ Effekt faylı yaradılmadı.")
        return

    file = FSInputFile(new_path, filename=os.path.basename(new_path))
    await c.message.answer_document(file)


# =================================================================
# 🔘 Tərcümə düyməsi
# =================================================================
def _translate_button(yt_id: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🇦🇿 Tərcümə et",
                    callback_data=f"song:tr:{yt_id}",
                )
            ]
        ]
    )


# =================================================================
# 🌍 Dil funksiyaları + helper
# =================================================================
def _lang(code: str) -> dict:
    from i18n import _load
    return _load(code)


