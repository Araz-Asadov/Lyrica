from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
import os
import subprocess
import tempfile

from db import SessionLocal
from models import User, Song, Favorite
from keyboards import song_actions
from i18n import _load, t

router = Router()

# ============================================================
# 🌐 Language loader
# ============================================================
def _lang(code: str):
    return _load(code)


# ============================================================
# ℹ️ /help 
# ============================================================
@router.message(Command("help"))
async def cmd_help(m: Message):
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    
    lang = user.language if user else "az"
    
    # Modern və gözəl help mesajı
    help_texts = {
        "az": (
            "📘 <b>Kömək və İstifadə Qaydası</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📋 <b>Komandalar:</b>\n\n"
            "🚀 /start — Botu başlat və menyunu aç\n"
            "🔍 Mahnı adı yazın — Axtarış et\n"
            "⭐ /favorites — Sevimli mahnılarınızı görün\n"
            "🎼 /not — Musiqi notlarını çıxar\n"
            "🌐 /lang — Dili dəyiş\n"
            "ℹ️ /help — Bu kömək mesajı\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎵 <b>Mahnı tapmaq:</b>\n\n"
            "1️⃣ <b>Link göndərin:</b>\n"
            "   • TikTok linki\n"
            "   • Instagram Reels linki\n"
            "   • YouTube linki\n\n"
            "2️⃣ <b>Video göndərin:</b>\n"
            "   • Video faylı göndərin\n"
            "   • Audio avtomatik çıxarılacaq\n"
            "   • Mahnı tanınacaq (Shazam efekti)\n\n"
            "3️⃣ <b>Səs mesajı:</b>\n"
            "   • Zümzümə edin və göndərin\n"
            "   • Mahnı tapılacaq\n\n"
            "4️⃣ <b>Musiqi notları:</b>\n"
            "   • /not yazın\n"
            "   • Musiqi faylı göndərin\n"
            "   • Notlar çıxarılacaq\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <b>İpucu:</b> Sadəcə mahnı adı yazın və mən onu tapacağam! 🎵"
        ),
        "ru": (
            "📘 <b>Помощь и Руководство</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📋 <b>Команды:</b>\n\n"
            "🚀 /start — Запустить бота и открыть меню\n"
            "🔍 Введите название песни — Поиск\n"
            "⭐ /favorites — Просмотреть избранные песни\n"
            "🎼 /not — Извлечь ноты музыки\n"
            "🌐 /lang — Изменить язык\n"
            "ℹ️ /help — Это сообщение помощи\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎵 <b>Найти песню:</b>\n\n"
            "1️⃣ <b>Отправьте ссылку:</b>\n"
            "   • Ссылка TikTok\n"
            "   • Ссылка Instagram Reels\n"
            "   • Ссылка YouTube\n\n"
            "2️⃣ <b>Отправьте видео:</b>\n"
            "   • Отправьте видео файл\n"
            "   • Аудио будет извлечено автоматически\n"
            "   • Песня будет распознана (эффект Shazam)\n\n"
            "3️⃣ <b>Голосовое сообщение:</b>\n"
            "   • Напевайте и отправьте\n"
            "   • Песня будет найдена\n\n"
            "4️⃣ <b>Ноты музыки:</b>\n"
            "   • Введите /not\n"
            "   • Отправьте музыкальный файл\n"
            "   • Ноты будут извлечены\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <b>Совет:</b> Просто введите название песни, и я найду её! 🎵"
        ),
        "en": (
            "📘 <b>Help and Usage Guide</b>\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📋 <b>Commands:</b>\n\n"
            "🚀 /start — Start bot and open menu\n"
            "🔍 Type song name — Search\n"
            "⭐ /favorites — View your favorite songs\n"
            "🎼 /not — Extract music notes\n"
            "🌐 /lang — Change language\n"
            "ℹ️ /help — This help message\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "🎵 <b>Find songs:</b>\n\n"
            "1️⃣ <b>Send link:</b>\n"
            "   • TikTok link\n"
            "   • Instagram Reels link\n"
            "   • YouTube link\n\n"
            "2️⃣ <b>Send video:</b>\n"
            "   • Send video file\n"
            "   • Audio will be extracted automatically\n"
            "   • Song will be recognized (Shazam effect)\n\n"
            "3️⃣ <b>Voice message:</b>\n"
            "   • Hum and send\n"
            "   • Song will be found\n\n"
            "4️⃣ <b>Music notes:</b>\n"
            "   • Type /not\n"
            "   • Send music file\n"
            "   • Notes will be extracted\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "💡 <b>Tip:</b> Just type a song name and I will find it! 🎵"
        ),
    }

    help_text = help_texts.get(lang, help_texts["az"])
    
    await m.answer(help_text, parse_mode="HTML")


# ============================================================
# 🌐 /lang — language selection
# ============================================================
@router.message(Command("lang"))
async def cmd_lang(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇦🇿 Azərbaycan", callback_data="setlang:az"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang:en"),
            InlineKeyboardButton(text="🇷🇺 Russian", callback_data="setlang:ru"),
        ]
    ])
    await m.answer("🌍 Dil seçin / Choose language / Выберите язык:", reply_markup=kb)


# ============================================================
# 🎵 /favorites
# ============================================================
@router.message(Command("favorites"))
async def show_favorites(m: Message):

    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == m.from_user.id))
        ).scalars().first()

        if not user:
            lang = "az"
            await m.answer(t(lang, "please_start"))
            return

        lang = user.language or "en"

        fav_songs = (
            await s.execute(
                select(Song)
                .join(Favorite)
                .where(Favorite.user_id == user.id)
                .order_by(Song.title.asc())
            )
        ).scalars().all()

    if not fav_songs:
        await m.answer(t(lang, "no_favorites_yet"))
        return

    btns = [
        [InlineKeyboardButton(text=f"🎧 {song.title}", callback_data=f"favopen:{song.youtube_id}")]
        for song in fav_songs
    ]

    await m.answer(t(lang, "your_favorites"), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


# ============================================================
# 🎵 Start menu → menu:favorites
# ============================================================
@router.callback_query(F.data == "menu:favorites")
async def menu_fav(c: CallbackQuery):

    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()

        lang = user.language if user else "en"

        fav_songs = (
            await s.execute(
                select(Song)
                .join(Favorite)
                .where(Favorite.user_id == user.id)
                .order_by(Song.title.asc())
            )
        ).scalars().all()

    if not fav_songs:
        await c.message.answer(t(lang, "no_songs_favorites"))
        await c.answer()
        return

    btns = [
        [InlineKeyboardButton(text=f"🎧 {song.title}", callback_data=f"favopen:{song.youtube_id}")]
        for song in fav_songs
    ]

    await c.message.edit_text("🎶 Your favorite songs:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await c.answer()


# ============================================================
# 🎧 Favorite song selected
# ============================================================
@router.callback_query(F.data.startswith("favopen:"))
async def open_favorite_song(c: CallbackQuery):
    yt_id = c.data.split(":")[1]

    async with SessionLocal() as s:
        song = (
            await s.execute(select(Song).where(Song.youtube_id == yt_id))
        ).scalars().first()

        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()

    if not song:
        lang = user.language or "az"
        await c.answer(t(lang, "song_not_found"), show_alert=True)
        return

    lang = user.language or "en"

    await c.message.answer(
        f"🎧 {song.title}\n👤 {song.artist}",
        reply_markup=song_actions(_lang(lang), song.youtube_id)
    )
    await c.answer()


# Store user state for /not command
user_waiting_for_audio = set()


# ============================================================
# 🎼 /not — Extract music notes from audio
# ============================================================
@router.message(Command("not", "note"))
async def cmd_not_handler(m: Message):
    """Set user to waiting state for audio file"""
    user_waiting_for_audio.add(m.from_user.id)
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    lang = user.language if user else "az"
    await m.answer(t(lang, "notes_send_file"))


@router.message(F.audio | F.voice | F.video | F.video_note)
async def on_audio_for_notes(m: Message):
    """Handle audio/voice/video for note extraction"""
    if m.from_user.id not in user_waiting_for_audio:
        return  # Not waiting for notes
    
    user_waiting_for_audio.discard(m.from_user.id)
    
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    
    lang = user.language if user else "az"
    
    await m.answer(t(lang, "notes_extracting"))
    
    from services.music_notes import extract_notes, extract_notes_simple
    
    with tempfile.TemporaryDirectory() as td:
        input_path = os.path.join(td, "input")
        audio_path = os.path.join(td, "audio.mp3")
        
        try:
            # Download file
            if m.audio:
                file_info = await m.bot.get_file(m.audio.file_id)
                await m.bot.download(file_info.file_id, destination=input_path)
                # Audio files might need conversion
                if not input_path.endswith('.mp3'):
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", input_path, "-acodec", "libmp3lame", audio_path],
                        check=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=30
                    )
                else:
                    audio_path = input_path
            elif m.voice:
                file_info = await m.bot.get_file(m.voice.file_id)
                ogg_path = os.path.join(td, "voice.ogg")
                await m.bot.download(file_info.file_id, destination=ogg_path)
                # Convert OGG to MP3
                subprocess.run(
                    ["ffmpeg", "-y", "-i", ogg_path, "-acodec", "libmp3lame", audio_path],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=30
                )
            elif m.video or m.video_note:
                file_info = await m.bot.get_file(m.video.file_id if m.video else m.video_note.file_id)
                video_path = os.path.join(td, "video.mp4")
                await m.bot.download(file_info.file_id, destination=video_path)
                # Extract audio from video
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
            else:
                await m.answer(t(lang, "file_not_found"))
                return
            
            if not os.path.exists(audio_path):
                await m.answer(t(lang, "audio_file_not_created"))
                return
            
            # Extract notes
            notes_result = extract_notes(audio_path)
            
            if notes_result:
                await m.answer(notes_result, parse_mode="Markdown")
            else:
                # Fallback to simple extraction
                notes_result = extract_notes_simple(audio_path)
                await m.answer(notes_result)
                
        except subprocess.TimeoutExpired:
            await m.answer(t(lang, "timeout_error"))
        except subprocess.CalledProcessError as e:
            await m.answer(t(lang, "ffmpeg_error"))
        except Exception as e:
            await m.answer(t(lang, "error", error=str(e)))