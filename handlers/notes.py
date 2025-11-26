"""
Music Notes Extraction Handler
Handles /not command for extracting musical notes and chords
"""
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from sqlalchemy import select
from db import SessionLocal
from models import User
from i18n import t
from services.notes_extraction_service import get_notes_service
from utils.audio_tools import convert_audio_format, extract_audio_from_video
import os
import tempfile
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("not"))
async def on_notes_command(m: Message):
    """Handle /not command for music notes extraction"""
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == m.from_user.id))
        ).scalars().first()
    
    lang = user.language if user and getattr(user, "language", None) else "az"
    
    # Check if replying to a message with audio/video/voice
    if m.reply_to_message:
        audio_source = None
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Check for voice
            if m.reply_to_message.voice:
                ogg_path = os.path.join(temp_dir, "voice.ogg")
                wav_path = os.path.join(temp_dir, "voice.wav")
                file = await m.bot.get_file(m.reply_to_message.voice.file_id)
                await m.bot.download_file(file.file_path, destination=ogg_path)
                audio_source = convert_audio_format(ogg_path, wav_path, "wav", 44100, 1)
            
            # Check for audio
            elif m.reply_to_message.audio:
                audio_path = os.path.join(temp_dir, "audio.wav")
                file = await m.bot.get_file(m.reply_to_message.audio.file_id)
                await m.bot.download_file(file.file_path, destination=audio_path)
                audio_source = convert_audio_format(audio_path, os.path.join(temp_dir, "converted.wav"), "wav", 44100, 1)
            
            # Check for video
            elif m.reply_to_message.video:
                video_path = os.path.join(temp_dir, "video.mp4")
                wav_path = os.path.join(temp_dir, "audio.wav")
                file = await m.bot.get_file(m.reply_to_message.video.file_id)
                await m.bot.download_file(file.file_path, destination=video_path)
                audio_source = extract_audio_from_video(video_path, wav_path, duration=30)
            
            if not audio_source:
                await m.answer(t(lang, "notes.no_audio_source"))
                return
            
            # Extract notes
            status_msg = await m.answer(t(lang, "notes.extracting"))
            notes_service = get_notes_service()
            notes = await notes_service.extract_notes(audio_source)
            
            # Cleanup
            try:
                for f in os.listdir(temp_dir):
                    os.unlink(os.path.join(temp_dir, f))
                os.rmdir(temp_dir)
            except:
                pass
            
            if not notes:
                await status_msg.edit_text(t(lang, "notes.extraction_failed"))
                return
            
            # Format result
            result_lines = [t(lang, "notes.title")]
            
            if notes.key:
                result_lines.append(t(lang, "notes.key", key=notes.key))
            
            if notes.bpm:
                result_lines.append(t(lang, "notes.bpm", bpm=notes.bpm))
            
            if notes.chords:
                chords_str = " – ".join(notes.chords)
                result_lines.append(t(lang, "notes.chords", chords=chords_str))
            
            if notes.notes:
                notes_str = " ".join(notes.notes[:10])
                result_lines.append(t(lang, "notes.notes", notes=notes_str))
            
            result_text = "\n".join(result_lines)
            await status_msg.edit_text(result_text)
        
        except Exception as e:
            logger.error(f"Notes extraction error: {e}", exc_info=True)
            await m.answer(t(lang, "notes.error"))
            # Cleanup on error
            try:
                for f in os.listdir(temp_dir):
                    os.unlink(os.path.join(temp_dir, f))
                os.rmdir(temp_dir)
            except:
                pass
    else:
        # No reply - ask user to send audio/video/voice
        await m.answer(t(lang, "notes.usage"))


@router.message(F.audio | F.voice | F.video)
async def on_media_for_notes(m: Message):
    """Handle audio/voice/video for notes extraction (if /not was used)"""
    # This will be handled by the /not command with reply
    pass

