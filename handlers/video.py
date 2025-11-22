"""
Handler for video messages
Extracts audio and identifies the song
"""
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from sqlalchemy import select
from db import SessionLocal
from models import User, Song
from i18n import t
from services.music_recognition import recognize_song, format_song_info
from services.youtube import search_and_download
from keyboards import song_actions
import os
import tempfile
import subprocess
import asyncio

router = Router()


@router.message(F.video | F.video_note)
async def on_video(m: Message):
    """Handle video messages - extract audio and identify song"""
    # Skip if user is waiting for /not command (handled by commands.py)
    from handlers.commands import user_waiting_for_audio
    if m.from_user.id in user_waiting_for_audio:
        return  # Let commands handler process it
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    
    lang = user.language if user else "az"
    
    await m.answer(t(lang, "video_analyzing"))
    
    # Download video
    with tempfile.TemporaryDirectory() as td:
        video_path = os.path.join(td, "video.mp4")
        audio_path = os.path.join(td, "audio.mp3")
        
        try:
            # Download video file
            if m.video:
                file_info = await m.bot.get_file(m.video.file_id)
            elif m.video_note:
                file_info = await m.bot.get_file(m.video_note.file_id)
            else:
                await m.answer(t(lang, "video_not_found"))
                return
            
            await m.bot.download(file_info.file_id, destination=video_path)
            
            # Extract audio using FFmpeg
            await m.answer(t(lang, "audio_extracting"))
            subprocess.run(
                [
                    "ffmpeg", "-y", "-i", video_path,
                    "-vn", "-acodec", "libmp3lame",
                    "-ab", "192k", audio_path
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60
            )
            
            if not os.path.exists(audio_path):
                await m.answer(t(lang, "audio_extract_failed_video"))
                return
            
            # Send extracted audio
            audio_file = FSInputFile(audio_path, filename="extracted_audio.mp3")
            await m.answer_audio(audio_file, caption=t(lang, "audio_extracted"))
            
            # Try to recognize the song
            await m.answer(t(lang, "song_recognizing"))
            song_data = await recognize_song(audio_path)
            
            if song_data:
                song_info = format_song_info(song_data)
                await m.answer(song_info, parse_mode="Markdown")
                
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
                            
                            from i18n import _load
                            _lang = _load(lang)
                            msg = f"🎵 **{yt_result.title}**\n👤 {yt_result.artist}"
                            await m.answer(
                                msg,
                                reply_markup=song_actions(_lang, yt_result.youtube_id),
                                parse_mode="Markdown"
                            )
                    except Exception as e:
                        print(f"Error searching YouTube: {e}")
            else:
                await m.answer(t(lang, "song_not_recognized_video"))
                
        except Exception as e:
            await m.answer(t(lang, "error", error=str(e)))

