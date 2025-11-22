"""
Handler for social media links (TikTok, Instagram, YouTube)
Extracts audio and identifies the song
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from db import SessionLocal
from models import User, Song
from i18n import t
from services.social_media import (
    is_tiktok_link,
    is_instagram_link,
    is_youtube_link,
    extract_audio_from_url
)
from services.music_recognition import recognize_song, format_song_info
from services.youtube import search_and_download, YTResult
from keyboards import song_actions
import asyncio
import os

router = Router()


async def delete_message_safe(bot: Bot, chat_id: int, message_id: int):
    """Safely delete a message, ignoring errors"""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass  # Ignore deletion errors


@router.message(F.text & ~F.via_bot & ~F.text.startswith("/"))
async def on_link(m: Message, bot: Bot):
    """Handle TikTok, Instagram, or YouTube links"""
    text = m.text.strip()
    
    # Check if it's a link
    is_link = (
        is_tiktok_link(text) or 
        is_instagram_link(text) or 
        is_youtube_link(text)
    )
    
    if not is_link:
        # Not a link, let search handler process it
        return
    
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    
    lang = user.language if user else "az"
    
    # Determine platform
    is_instagram = is_instagram_link(text)
    if is_tiktok_link(text):
        platform_emoji = "🎵"
        platform_name = "TikTok"
    elif is_instagram:
        platform_emoji = "📸"
        platform_name = "Instagram"
    else:
        platform_emoji = "▶️"
        platform_name = "YouTube"
    
    platform_names = {
        "az": {"TikTok": "TikTok", "Instagram": "Instagram", "YouTube": "YouTube"},
        "en": {"TikTok": "TikTok", "Instagram": "Instagram", "YouTube": "YouTube"},
        "ru": {"TikTok": "TikTok", "Instagram": "Instagram", "YouTube": "YouTube"},
    }
    platform_display = platform_names.get(lang, platform_names["az"]).get(platform_name, platform_name)
    
    # Store message IDs to delete later
    messages_to_delete = []
    
    # For Instagram: skip intermediate messages, go directly to main song
    if is_instagram:
        # Only send extracting message, will delete it later
        extracting_msg = await m.answer(t(lang, "link_extracting", emoji=platform_emoji, platform=platform_display))
        messages_to_delete.append(extracting_msg.message_id)
    else:
        # For TikTok/YouTube: show extracting message
        extracting_msg = await m.answer(t(lang, "link_extracting", emoji=platform_emoji, platform=platform_display))
        messages_to_delete.append(extracting_msg.message_id)
    
    try:
        # Extract audio from link (run in thread to avoid blocking)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, extract_audio_from_url, text)
        
        if not result:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to extract audio from link: {text}")
            
            await m.answer(f"❌ {t(lang, 'audio_extract_failed')}\n\n🔗 Link: {text[:50]}...")
            # Delete extracting message
            await delete_message_safe(bot, m.chat.id, extracting_msg.message_id)
            return
        
        # For Instagram: skip sending extracted audio, go directly to recognition
        if not is_instagram:
            # Send the extracted audio (only for TikTok/YouTube)
            if os.path.exists(result.audio_path):
                audio_file = FSInputFile(result.audio_path, filename=f"{result.title}.mp3")
                audio_msg = await m.answer_audio(
                    audio_file,
                    title=result.title,
                    caption=f"🎵 {result.title}\n📱 {platform_name}"
                )
                messages_to_delete.append(audio_msg.message_id)
        
        # Try to recognize the song (Shazam-like)
        if not is_instagram:
            recognizing_msg = await m.answer(t(lang, "song_recognizing"))
            messages_to_delete.append(recognizing_msg.message_id)
        
        song_data = await recognize_song(result.audio_path)
        
        if song_data:
            # For Instagram: skip recognition info message
            if not is_instagram:
                song_info = format_song_info(song_data)
                info_msg = await m.answer(song_info, parse_mode="Markdown")
                messages_to_delete.append(info_msg.message_id)
            
            # Try to find on YouTube
            search_query = f"{song_data.get('artist', '')} {song_data.get('title', '')}"
            if search_query.strip():
                try:
                    yt_result = await search_and_download(search_query)
                    if yt_result:
                        async with SessionLocal() as s:
                            song = (await s.execute(
                                select(Song).where(Song.youtube_id == yt_result.youtube_id)
                            )).scalars().first()
                            
                            if not song:
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
                        
                        msg = f"🎵 **{yt_result.title}**\n👤 {yt_result.artist}"
                        await m.answer(
                            msg,
                            reply_markup=song_actions(_lang(lang), yt_result.youtube_id),
                            parse_mode="Markdown"
                        )
                        
                        # Delete all intermediate messages after posting main song
                        for msg_id in messages_to_delete:
                            await delete_message_safe(bot, m.chat.id, msg_id)
                except Exception as e:
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Error searching YouTube after recognition: {e}", exc_info=True)
                    
                    # Show user-friendly error
                    await m.answer(f"❌ YouTube-da mahnı tapılmadı.\n\n🎵 Tanınan mahnı: {song_data.get('title', 'Unknown')}")
                    # Delete intermediate messages even on error
                    for msg_id in messages_to_delete:
                        await delete_message_safe(bot, m.chat.id, msg_id)
        else:
            if not is_instagram:
                await m.answer(t(lang, "song_not_recognized"))
            # Delete intermediate messages
            for msg_id in messages_to_delete:
                await delete_message_safe(bot, m.chat.id, msg_id)
            
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error processing link {text}: {e}", exc_info=True)
        
        await m.answer(f"❌ {t(lang, 'error', error=str(e)[:200])}")
        # Delete intermediate messages on error
        for msg_id in messages_to_delete:
            await delete_message_safe(bot, m.chat.id, msg_id)


def _lang(code: str):
    from i18n import _load
    return _load(code)

