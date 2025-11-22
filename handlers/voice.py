from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from db import SessionLocal
from models import User
from i18n import t
from services.music_recognition import recognize_song, format_song_info
from services.youtube import search_and_download
from keyboards import song_actions
import os
import tempfile
import subprocess
import asyncio

router = Router()


@router.message(F.voice)
async def on_voice(m: Message):
    """Handle voice messages - Shazam-like music recognition"""
    # Skip if user is waiting for /not command (handled by commands.py)
    from handlers.commands import user_waiting_for_audio
    if m.from_user.id in user_waiting_for_audio:
        return  # Let commands handler process it
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    lang = u.language if u else "az"
    
    await m.answer(t(lang, "voice_analyzing"))
    
    # Download voice message
    with tempfile.TemporaryDirectory() as td:
        ogg_path = os.path.join(td, "voice.ogg")
        mp3_path = os.path.join(td, "voice.mp3")
        
        try:
            await m.bot.download(m.voice.file_id, destination=ogg_path)
            
            # Convert to MP3 for recognition
            subprocess.run(
                ["ffmpeg", "-y", "-i", ogg_path, "-acodec", "libmp3lame", mp3_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=30
            )
            
            # Try music recognition (Shazam-like)
            await m.answer(t(lang, "song_recognizing_shazam"))
            song_data = await recognize_song(mp3_path)
            
            if song_data:
                song_info = format_song_info(song_data)
                await m.answer(song_info, parse_mode="Markdown")
                
                # Try to find on YouTube
                search_query = f"{song_data.get('artist', '')} {song_data.get('title', '')}"
                if search_query.strip():
                    try:
                        yt_result = await search_and_download(search_query)
                        if yt_result:
                            from models import Song
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
                # Fallback: Try transcription with Vosk if configured
                model_path = os.getenv("VOSK_MODEL_PATH", "")
                if model_path:
                    wav_path = os.path.join(td, "voice.wav")
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    try:
                        import vosk
                        import json
                        rec = vosk.KaldiRecognizer(vosk.Model(model_path), 16000)
                        with open(wav_path, "rb") as f:
                            while True:
                                data = f.read(4000)
                                if len(data) == 0:
                                    break
                                if rec.AcceptWaveform(data):
                                    pass
                        res = json.loads(rec.FinalResult()).get("text", "").strip()
                        if res:
                            await m.answer(t(lang, "recognized_text", text=res))
                        else:
                            await m.answer(t(lang, "song_not_recognized_voice"))
                    except Exception as e:
                        await m.answer(t(lang, "song_not_recognized_simple"))
                else:
                    await m.answer(t(lang, "song_not_recognized_api"))
                    
        except Exception as e:
            await m.answer(t(lang, "error", error=str(e)))