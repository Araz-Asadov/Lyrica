"""
Music Recognition Handlers
Handles TikTok, Instagram, YouTube links, videos, and voice messages
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import Command
from sqlalchemy import select
from db import SessionLocal
from models import User, Song, RequestLog
from i18n import t
from i18n import _load as _lang
from keyboards import song_actions
from services.music_recognition_service import get_recognition_service, RecognitionResult
from services.youtube import is_youtube_link, download_from_url, YTResult
from utils.audio_tools import extract_audio_from_video, convert_audio_format
from typing import Optional
import os
import tempfile
import logging
import yt_dlp

logger = logging.getLogger(__name__)
router = Router()


def is_tiktok_link(url: str) -> bool:
    """Check if URL is a TikTok link"""
    if not url:
        return False
    
    url_lower = url.lower().strip()
    
    # Check all possible TikTok link patterns
    tiktok_patterns = [
        "tiktok.com",
        "vm.tiktok.com",
        "vt.tiktok.com",
        "www.tiktok.com",
        "m.tiktok.com",
    ]
    
    for pattern in tiktok_patterns:
        if pattern in url_lower:
            logger.debug(f"TikTok pattern '{pattern}' matched in URL: {url_lower[:100]}")
            return True
    
    return False


def is_instagram_link(url: str) -> bool:
    """Check if URL is an Instagram Reels link"""
    return "instagram.com/reel" in url.lower() or "instagram.com/p/" in url.lower()


def is_social_media_link(text: str) -> bool:
    """Check if text is a TikTok, Instagram, or YouTube link"""
    if not text or not isinstance(text, str):
        return False
    text = text.strip().lower()
    return (
        "tiktok.com" in text or
        "vm.tiktok.com" in text or
        "vt.tiktok.com" in text or
        ("instagram.com" in text and ("/reel" in text or "/p/" in text)) or
        "youtube.com/watch" in text or
        "youtu.be/" in text or
        "youtube.com/shorts/" in text
    )


async def download_video_audio(url: str, platform: str) -> tuple[Optional[str], Optional[dict]]:
    """
    Download video and extract audio for recognition.
    
    Args:
        url: Video URL
        platform: "tiktok", "instagram", or "youtube"
    
    Returns:
        Tuple of (audio_path, video_info_dict) or (None, None)
        video_info contains: duration, title, uploader, thumbnail
    """
    temp_dir = tempfile.mkdtemp()
    video_file = None
    audio_path = os.path.join(temp_dir, f"audio_{platform}.wav")
    
    try:
        # Use optimized yt-dlp settings
        from services.youtube import _get_ydl_opts
        import asyncio
        
        template = os.path.join(temp_dir, "%(id)s.%(ext)s")
        ydl_opts = _get_ydl_opts(template, download=True)
        
        # Override format for video download (not audio-only)
        ydl_opts["format"] = "best[height<=720]/best"
        # Remove audio postprocessor - we want video
        ydl_opts.pop("postprocessors", None)
        
        # Add more aggressive retry settings
        ydl_opts["retries"] = 5
        ydl_opts["fragment_retries"] = 5
        ydl_opts["skip_unavailable_fragments"] = True
        
        # Run in executor to avoid blocking
        loop = asyncio.get_running_loop()
        
        def _blocking_download():
            try:
                # Clean YouTube URLs to avoid 404 errors
                download_url = url
                if platform == "youtube":
                    from services.youtube import clean_youtube_url
                    download_url = clean_youtube_url(url)
                    logger.info(f"📥 Cleaned YouTube URL: {download_url}")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    logger.info(f"📥 Downloading {platform} video from: {download_url}")
                    info = ydl.extract_info(download_url, download=True)
                    
                    # Check if info is None
                    if info is None:
                        logger.error(f"yt-dlp returned None for {platform} URL: {url}")
                        return None, None
                    
                    # Check if it's a playlist/entries
                    if isinstance(info, dict) and "entries" in info:
                        if not info["entries"]:
                            logger.error(f"No entries in {platform} result")
                            return None, None
                        info = info["entries"][0]
                        # Check again if entry is None
                        if info is None:
                            logger.error(f"First entry is None in {platform} result")
                            return None, None
                    
                    # Extract video info
                    video_info = {
                        "duration": int(info.get("duration") or 0),
                        "title": info.get("title") or "Unknown",
                        "uploader": info.get("uploader") or info.get("channel") or "Unknown",
                        "thumbnail": info.get("thumbnail") or (info.get("thumbnails", [{}])[-1].get("url") if info.get("thumbnails") else ""),
                        "id": info.get("id") or "",
                    }
                    
                    video_file = ydl.prepare_filename(info)
                    logger.info(f"📁 Expected video file: {video_file}")
                    
                    if not os.path.exists(video_file):
                        # Try to find downloaded file
                        logger.warning(f"Expected file not found, searching in {temp_dir}")
                        for ext in ["mp4", "webm", "mkv", "m4a", "mp3"]:
                            # Try with video ID
                            alt_file = os.path.join(temp_dir, f"{info.get('id')}.{ext}")
                            if os.path.exists(alt_file):
                                video_file = alt_file
                                logger.info(f"✅ Found alternative file: {video_file}")
                                break
                        
                        # If still not found, search all files in temp_dir
                        if not os.path.exists(video_file):
                            files = os.listdir(temp_dir)
                            logger.info(f"Files in temp_dir: {files}")
                            if files:
                                # Get the newest file
                                video_file = os.path.join(temp_dir, max(files, key=lambda f: os.path.getctime(os.path.join(temp_dir, f))))
                                logger.info(f"✅ Using newest file: {video_file}")
                    
                    # Final check if file exists
                    if not os.path.exists(video_file):
                        logger.error(f"❌ Downloaded file not found: {video_file}")
                        # Still return video_info even if file not found
                        return None, video_info
                    
                    logger.info(f"✅ Video downloaded successfully: {video_file}")
                    return video_file, video_info
            except Exception as e:
                logger.error(f"Error in _blocking_download for {platform}: {e}", exc_info=True)
                return None, None
        
        video_file, video_info = await loop.run_in_executor(None, _blocking_download)
        
        if not video_file or not video_info:
            logger.error(f"Failed to download {platform} video")
            return None, video_info
        
        if not os.path.exists(video_file):
            logger.error(f"Video file does not exist: {video_file}")
            return None, video_info
        
        # Extract audio (first 30 seconds for recognition)
        logger.info(f"🎵 Extracting audio from: {video_file}")
        extracted = extract_audio_from_video(
            video_file,
            output_path=audio_path,
            duration=30,
            start_time=0
        )
        
        if extracted and os.path.exists(extracted):
            logger.info(f"✅ Audio extracted successfully: {extracted}")
            return extracted, video_info
        else:
            logger.error(f"❌ Audio extraction failed")
            return None, video_info
            
    except Exception as e:
        logger.error(f"Error downloading {platform} video: {e}", exc_info=True)
        return None, None
    finally:
        # Cleanup video file but keep audio
        if video_file and os.path.exists(video_file):
            try:
                os.unlink(video_file)
                logger.debug(f"🗑️ Cleaned up video file: {video_file}")
            except:
                pass


async def _process_social_media(m: Message, text: str, platform: str):
    """Generic handler for social media links (TikTok, Instagram)"""
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == m.from_user.id))
        ).scalars().first()
    
    lang = user.language if user and getattr(user, "language", None) else "az"
    
    # Send processing message
    platform_names = {"tiktok": "TikTok", "instagram": "Instagram"}
    status_msg = await m.answer(t(lang, "recognition.processing", platform=platform_names.get(platform, platform)))
    
    logger.info(f"Processing {platform} link for user {m.from_user.id}")
    
    try:
        # Step 1: Download video and extract audio for recognition
        logger.info(f"Step 1: Downloading {platform} video and extracting audio")
        audio_path, video_info = await download_video_audio(text, platform)
        
        if not audio_path:
            logger.error(f"Failed to extract audio from {platform} video")
            if video_info and video_info.get("title") and video_info.get("title") != "Unknown":
                logger.info(f"Video download failed, but we have video info. Trying to search YouTube directly...")
                from services.social_download import clean_social_media_title
                raw_title = video_info.get("title", "Unknown")
                cleaned_title = clean_social_media_title(raw_title) if raw_title != "Unknown" else "Unknown"
                
                if cleaned_title and cleaned_title != "Unknown":
                    try:
                        from services.youtube import search_and_download, YTResult
                        await status_msg.edit_text(t(lang, "recognition.searching_original"))
                        original_yt: YTResult = await search_and_download(cleaned_title)
                        
                        if original_yt and original_yt.file_path and os.path.exists(original_yt.file_path):
                            final_title = original_yt.title
                            final_artist = original_yt.artist
                            final_duration = original_yt.duration
                            final_file_path = original_yt.file_path
                            final_thumbnail = original_yt.thumbnail
                            final_youtube_id = original_yt.youtube_id
                            
                            async with SessionLocal() as s:
                                song = (
                                    await s.execute(select(Song).where(Song.youtube_id == final_youtube_id))
                                ).scalars().first()
                                
                                if not song:
                                    song = Song(
                                        youtube_id=final_youtube_id,
                                        title=final_title,
                                        artist=final_artist,
                                        duration=final_duration,
                                        file_path=final_file_path,
                                        thumbnail=final_thumbnail,
                                    )
                                    s.add(song)
                                    await s.commit()
                                    await s.refresh(song)
                                
                                if user and song:
                                    s.add(
                                        RequestLog(
                                            user_id=user.id,
                                            query=text,
                                            via_voice=False,
                                            matched_song_id=song.id,
                                        )
                                    )
                                    await s.commit()
                            
                            result_text = t(
                                lang,
                                "search_result",
                                title=final_title,
                                artist=final_artist,
                                duration=final_duration,
                            )
                            
                            await status_msg.edit_text(result_text)
                            await m.answer(
                                t(lang, "recognition.song_info"),
                                reply_markup=song_actions(_lang(lang), str(song.id))

                            )
                            return
                    except Exception as search_error:
                        logger.error(f"Failed to search YouTube directly: {search_error}")
            
            await status_msg.edit_text(t(lang, "recognition.audio_extraction_failed"))
            return
        
        logger.info(f"Audio extracted: {audio_path}")
        
        # Step 2: Recognize music using API
        logger.info(f"Step 2: Recognizing music from audio")
        await status_msg.edit_text(t(lang, "recognition.recognizing"))
        
        recognition_service = get_recognition_service()
        recognition_result = await recognition_service.recognize_from_file(audio_path)
        
        # Cleanup temp audio file
        try:
            if os.path.exists(audio_path):
                os.unlink(audio_path)
            temp_dir = os.path.dirname(audio_path)
            if os.path.exists(temp_dir):
                for f in os.listdir(temp_dir):
                    try:
                        os.unlink(os.path.join(temp_dir, f))
                    except:
                        pass
                os.rmdir(temp_dir)
        except:
            pass
        
        # Step 3: If recognition successful, search for original on YouTube
        if recognition_result and recognition_result.title and recognition_result.artist and recognition_result.title != "Unknown":
            logger.info(f"✅ Recognition successful: {recognition_result.title} - {recognition_result.artist}")
            await status_msg.edit_text(t(lang, "recognition.searching_original"))
            from services.youtube import search_and_download, YTResult
            search_query = f"{recognition_result.artist} {recognition_result.title}"
            logger.info(f"Searching YouTube for: {search_query}")
            
            try:
                logger.info(f"Calling search_and_download with query: {search_query}")
                original_yt: YTResult = await search_and_download(search_query)
                logger.info(f"✅ Original found: {original_yt.title} - {original_yt.artist}, file: {original_yt.file_path}")
                
                if not original_yt.file_path or not os.path.exists(original_yt.file_path):
                    logger.warning(f"Downloaded file not found: {original_yt.file_path}, using recognition result")
                    raise FileNotFoundError(f"Downloaded file not found: {original_yt.file_path}")
                
                final_title = original_yt.title
                final_artist = original_yt.artist
                final_duration = original_yt.duration
                final_file_path = original_yt.file_path
                final_thumbnail = original_yt.thumbnail
                final_youtube_id = original_yt.youtube_id
                
                logger.info(f"✅ Using YouTube result: {final_title} - {final_artist}")
                
            except Exception as e:
                logger.error(f"Failed to find original on YouTube: {e}", exc_info=True)
                logger.info(f"Falling back to recognition result: {recognition_result.title} - {recognition_result.artist}")
                final_title = recognition_result.title
                final_artist = recognition_result.artist
                final_duration = recognition_result.duration or (video_info.get("duration") if video_info else 0)
                final_file_path = ""
                final_thumbnail = video_info.get("thumbnail", "") if video_info else ""
                final_youtube_id = recognition_result.youtube_id or f"rec_{platform}_{m.from_user.id}_{m.message_id}"
        else:
            logger.warning(f"Recognition failed or returned Unknown, using video info")
            from services.social_download import clean_social_media_title
            raw_title = video_info.get("title", "Unknown") if video_info else "Unknown"
            cleaned_title = clean_social_media_title(raw_title) if raw_title != "Unknown" else "Unknown"
            
            final_title = cleaned_title if cleaned_title else "Unknown"
            final_artist = video_info.get("uploader", "Unknown") if video_info else "Unknown"
            final_duration = video_info.get("duration", 0) if video_info else 0
            final_file_path = ""
            final_thumbnail = video_info.get("thumbnail", "") if video_info else ""
            final_youtube_id = f"{platform}_{video_info.get('id', f'{m.from_user.id}_{m.message_id}')}" if video_info else f"{platform}_{m.from_user.id}_{m.message_id}"
        
        # Save to database
        async with SessionLocal() as s:
            song = (
                await s.execute(select(Song).where(Song.youtube_id == final_youtube_id))
            ).scalars().first()
            
            if not song:
                song = Song(
                    youtube_id=final_youtube_id,
                    title=final_title,
                    artist=final_artist,
                    duration=final_duration,
                    file_path=final_file_path,
                    thumbnail=final_thumbnail,
                )
                s.add(song)
                await s.commit()
                await s.refresh(song)
            else:
                if not song.file_path and final_file_path:
                    song.file_path = final_file_path
                    await s.commit()
            
            if user and song:
                s.add(
                    RequestLog(
                        user_id=user.id,
                        query=text,
                        via_voice=False,
                        matched_song_id=song.id,
                    )
                )
                await s.commit()
        
        if recognition_result and recognition_result.confidence > 0:
            result_key = f"recognition.{platform}_found"
            result_text = t(
                lang,
                result_key,
                title=final_title,
                artist=final_artist,
                confidence=f"{recognition_result.confidence * 100:.0f}%"
            )
        else:
            result_text = t(
                lang,
                "search_result",
                title=final_title,
                artist=final_artist,
                duration=final_duration,
            )
        
        await status_msg.edit_text(result_text)
        
        if song:
            await m.answer(
                t(lang, "recognition.song_info"),
                reply_markup=song_actions(_lang(lang), str(song.id))
            )
    
    except Exception as e:
        logger.error(f"Social media download error: {e}", exc_info=True)
        await status_msg.edit_text(t(lang, "recognition.error"))


async def process_tiktok(m: Message, text: str):
    """Handler for TikTok links"""
    await _process_social_media(m, text, "tiktok")


async def process_instagram(m: Message, text: str):
    """Handler for Instagram links"""
    await _process_social_media(m, text, "instagram")


@router.message(F.text & ~F.via_bot & ~F.text.startswith("/"))
async def on_social_media_link(m: Message):
    """Handle TikTok, Instagram, and YouTube links ONLY"""
    text = m.text.strip()
    
    # CRITICAL: Check if it's a social media link first
    if not is_social_media_link(text):
        # Not a social media link - let other handlers process it
        # DO NOT return here - let the handler chain continue
        return
    
    logger.info(f"[RECOGNITION] Processing social media link: {text[:100]}")
    
    # Route based on platform
    if is_tiktok_link(text):
        await process_tiktok(m, text)
    elif is_instagram_link(text):
        await process_instagram(m, text)
    elif is_youtube_link(text):
        await process_youtube_link(m, text)
    
    # Mark the event as handled to prevent other handlers from processing it
    return True


async def process_youtube_link(m: Message, url: str):
    """Process YouTube links for music recognition"""
    logger.info(f"🔵 Processing YouTube link: {url}")
    
    # Get user language
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    lang = user.language if user and getattr(user, "language", None) else "az"
    
    # Send processing message
    status_msg = await m.answer(t(lang, "recognition.processing", platform="YouTube"))
    
    try:
        # Download video and extract audio
        audio_path, video_info = await download_video_audio(url, "youtube")
        if not audio_path or not os.path.exists(audio_path):
            await status_msg.edit_text(t(lang, "recognition.audio_extraction_failed"))
            return
            
        # Get recognition service and recognize
        recognition_service = get_recognition_service()
        result = await recognition_service.recognize_from_file(audio_path)
        
        # Clean up audio file
        try:
            os.remove(audio_path)
            temp_dir = os.path.dirname(audio_path)
            if os.path.exists(temp_dir):
                for f in os.listdir(temp_dir):
                    try:
                        os.unlink(os.path.join(temp_dir, f))
                    except:
                        pass
                os.rmdir(temp_dir)
        except:
            pass
            
        if not result or not result.title:
            await status_msg.edit_text(t(lang, "recognition.recognition_failed"))
            return
            
        # Save to database
        async with SessionLocal() as s:
            final_youtube_id = result.youtube_id or f"rec_youtube_{m.from_user.id}_{m.message_id}"
            song = (
                await s.execute(select(Song).where(Song.youtube_id == final_youtube_id))
            ).scalars().first()
            
            if not song and result.title:
                song = Song(
                    youtube_id=final_youtube_id,
                    title=result.title,
                    artist=result.artist,
                    duration=result.duration or 0,
                    file_path="",
                    thumbnail=video_info.get("thumbnail", "") if video_info else "",
                )
                s.add(song)
                await s.commit()
                await s.refresh(song)
        
        # Send result
        result_text = t(
            lang,
            "recognition.from_video",
            title=result.title,
            artist=result.artist,
        )
        
        await status_msg.edit_text(result_text)
        
        if song:
            await m.answer(
                t(lang, "recognition.song_info"),
                reply_markup=song_actions(_lang(lang), str(song.id))
            )
        
    except Exception as e:
        logger.error(f"Error processing YouTube link: {e}", exc_info=True)
        await status_msg.edit_text(t(lang, "recognition.error_occurred"))


@router.message(F.video | F.video_note)
async def on_video_for_recognition(m: Message):
    """Handle video files for music recognition"""
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == m.from_user.id))
        ).scalars().first()
    
    lang = user.language if user and getattr(user, "language", None) else "az"
    
    status_msg = await m.answer(t(lang, "recognition.processing_video"))
    
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, "video.mp4")
    audio_path = os.path.join(temp_dir, "audio.wav")
    
    try:
        # Download video
        if m.video:
            file = await m.bot.get_file(m.video.file_id)
        else:  # video_note
            file = await m.bot.get_file(m.video_note.file_id)
        
        await m.bot.download_file(file.file_path, destination=video_path)
        
        # Extract audio (first 30 seconds)
        extracted = extract_audio_from_video(
            video_path,
            output_path=audio_path,
            duration=30,
            start_time=0
        )
        
        if not extracted:
            await status_msg.edit_text(t(lang, "recognition.audio_extraction_failed"))
            return
        
        # Recognize
        recognition_service = get_recognition_service()
        result = await recognition_service.recognize_from_file(extracted)
        
        # Cleanup
        try:
            for f in [video_path, audio_path]:
                if os.path.exists(f):
                    os.unlink(f)
            os.rmdir(temp_dir)
        except:
            pass
        
        if not result:
            await status_msg.edit_text(t(lang, "recognition.not_found"))
            return
        
        # Save to database
        async with SessionLocal() as s:
            final_youtube_id = result.youtube_id or f"rec_video_{m.from_user.id}_{m.message_id}"
            song = (
                await s.execute(select(Song).where(Song.youtube_id == final_youtube_id))
            ).scalars().first()
            
            if not song and result.title:
                song = Song(
                    youtube_id=final_youtube_id,
                    title=result.title,
                    artist=result.artist,
                    duration=result.duration or 0,
                    file_path="",
                    thumbnail="",
                )
                s.add(song)
                await s.commit()
                await s.refresh(song)
        
        # Send result
        result_text = t(
            lang,
            "recognition.from_video",
            title=result.title,
            artist=result.artist,
        )
        
        await status_msg.edit_text(result_text)
        
        if song:
            await m.answer(
                t(lang, "recognition.song_info"),
                reply_markup=song_actions(_lang(lang), str(song.id))
            )
    
    except Exception as e:
        logger.error(f"Video recognition error: {e}", exc_info=True)
        await status_msg.edit_text(t(lang, "recognition.error"))
        # Cleanup on error
        try:
            for f in [video_path, audio_path]:
                if os.path.exists(f):
                    os.unlink(f)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except:
            pass


@router.message(F.voice)
async def on_voice_for_recognition(m: Message):
    """Handle voice messages for humming/whistling recognition"""
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == m.from_user.id))
        ).scalars().first()
    
    lang = user.language if user and getattr(user, "language", None) else "az"
    
    status_msg = await m.answer(t(lang, "recognition.processing_voice"))
    
    temp_dir = tempfile.mkdtemp()
    ogg_path = os.path.join(temp_dir, "voice.ogg")
    wav_path = os.path.join(temp_dir, "voice.wav")
    
    try:
        # Download voice
        file = await m.bot.get_file(m.voice.file_id)
        await m.bot.download_file(file.file_path, destination=ogg_path)
        
        # Convert to WAV (mono, 16-bit, 44.1 kHz)
        converted = convert_audio_format(
            ogg_path,
            output_path=wav_path,
            format="wav",
            sample_rate=44100,
            channels=1
        )
        
        if not converted:
            await status_msg.edit_text(t(lang, "recognition.audio_conversion_failed"))
            return
        
        # Recognize with humming mode
        recognition_service = get_recognition_service()
        result = await recognition_service.recognize_from_file(wav_path, mode="humming")
        
        # Cleanup
        try:
            for f in [ogg_path, wav_path]:
                if os.path.exists(f):
                    os.unlink(f)
            os.rmdir(temp_dir)
        except:
            pass
        
        if not result:
            await status_msg.edit_text(t(lang, "recognition.not_found"))
            return
        
        # Save to database
        async with SessionLocal() as s:
            final_youtube_id = result.youtube_id or f"rec_voice_{m.from_user.id}_{m.message_id}"
            song = (
                await s.execute(select(Song).where(Song.youtube_id == final_youtube_id))
            ).scalars().first()
            
            if not song and result.title:
                song = Song(
                    youtube_id=final_youtube_id,
                    title=result.title,
                    artist=result.artist,
                    duration=result.duration or 0,
                    file_path="",
                    thumbnail="",
                )
                s.add(song)
                await s.commit()
                await s.refresh(song)
        
        # Send result
        result_text = t(
            lang,
            "recognition.from_voice",
            title=result.title,
            artist=result.artist,
        )
        
        await status_msg.edit_text(result_text)
        
        if song:
            await m.answer(
                t(lang, "recognition.song_info"),
                reply_markup=song_actions(_lang(lang), str(song.id))
            )
    
    except Exception as e:
        logger.error(f"Voice recognition error: {e}", exc_info=True)
        await status_msg.edit_text(t(lang, "recognition.error"))
        # Cleanup on error
        try:
            for f in [ogg_path, wav_path]:
                if os.path.exists(f):
                    os.unlink(f)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except:
            pass