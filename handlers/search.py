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

# 🔐 user+song əsaslı söz yaddaşı
# açar: (telegram_id, youtube_id) -> lyrics
user_lyrics_memory: dict[tuple[int, str], str] = {}


# =================================================================
# 🔍 MAHNİ AXTARIŞI (Komanda olmayan bütün textlər üçün)
# =================================================================
@router.message(F.text & ~F.via_bot & ~F.text.startswith("/"))
async def on_query(m: Message):
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == m.from_user.id))
        ).scalars().first()

    lang = user.language if user and getattr(user, "language", None) else "az"

    if not has_ffmpeg():
        await m.answer(t(lang, "no_ffmpeg"))
        return

    await m.answer(t(lang, "downloading"))

    try:
        # 🔹 Sürətli yükləmə üçün fast_mode istifadə oluna bilər
        yt: YTResult = await search_and_download(m.text.strip())
    except Exception:
        await m.answer("❌ Axtarış/yükləmə zamanı xəta baş verdi.")
        return

    # DB-yə yaz
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

        s.add(
            RequestLog(
                user_id=(user.id if user else None),
                query=m.text.strip(),
                via_voice=False,
                matched_song_id=song.id,
            )
        )
        await s.commit()

    msg = t(
        lang,
        "search_result",
        title=yt.title,
        artist=yt.artist,
        duration=yt.duration,
    )
    await m.answer(msg, reply_markup=socket_song_actions(lang, yt.youtube_id))


# =================================================================
# 🎵 MAHNINI ENDİR
# =================================================================
@router.callback_query(F.data.startswith("song:dl:"))
async def on_download(c: CallbackQuery):
    yt_id = c.data.split(":")[-1]

    async with SessionLocal() as s:
        song = (
            await s.execute(select(Song).where(Song.youtube_id == yt_id))
        ).scalars().first()

        if song:
            song.play_count += 1
            song.last_played = datetime.utcnow()
            await s.commit()

    if not song:
        await c.answer("Song not found", show_alert=True)
        return

    try:
        file = FSInputFile(song.file_path, filename=f"{song.title}.mp3")
        await c.message.answer_document(file)
    except Exception as e:
        await c.message.answer(f"❌ Göndərmə xətası: {e}")

    await c.answer()


# =================================================================
# 💬 MAHNININ SÖZLƏRİ
# =================================================================
@router.callback_query(F.data.startswith("song:ly:"))
async def on_lyrics(c: CallbackQuery):
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
        await c.answer("Song not found", show_alert=True)
        return

    lyrics = await get_lyrics(song.title, song.artist)

    if lyrics:
        user_lyrics_memory[(c.from_user.id, yt_id)] = lyrics
        await c.message.answer(lyrics)
        await c.message.answer(
            "🔁 Tərcümə etmək üçün:",
            reply_markup=_translate_button(yt_id),
        )
    else:
        await c.message.answer(t(lang, "lyrics_not_found"))

    await c.answer()


# =================================================================
# 🌐 TƏRCÜMƏ
# =================================================================
@router.callback_query(F.data.startswith("song:tr:"))
async def on_translate(c: CallbackQuery):
    yt_id = c.data.split(":")[-1]
    text = user_lyrics_memory.get((c.from_user.id, yt_id))

    # İstifadəçi dilini götürək
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()
    lang = user.language if user and getattr(user, "language", None) else "az"

    if not text:
        await c.message.answer("❗ Əvvəl sözləri aç (Sözlər düyməsi).")
        await c.answer()
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
            await c.answer(_lang(user.language)["fav_removed"])
        else:
            s.add(Favorite(user_id=user.id, song_id=song.id))
            await s.commit()
            await c.answer(_lang(user.language)["fav_added"])


# =================================================================
# 🎚️ EFFEKT MENYUSU
# =================================================================
@router.callback_query(F.data.startswith("song:fx:"))
async def on_effects_menu(c: CallbackQuery):
    # İstifadəçi dilini götürüb, çoxdilli efekt menyusu açaq
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()
    lang = user.language if user and getattr(user, "language", None) else "az"

    await c.message.answer(
        t(lang, "choose_effect"),
        reply_markup=effects_menu(_lang(lang)),
    )
    await c.answer()


# =================================================================
# 🎚️ EFFEKT TƏTBİQİ
# =================================================================
@router.callback_query(F.data.startswith("fx:"))
async def on_effect_apply(c: CallbackQuery):
    parts = c.data.split(":")
    kind, val = parts[1], parts[2]

    async with SessionLocal() as s:
        song = (
            await s.execute(select(Song).order_by(Song.last_played.desc()))
        ).scalars().first()
        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()

    lang = user.language if user and getattr(user, "language", None) else "az"

    if not song:
        await c.answer("No context song", show_alert=True)
        return

    if not has_ffmpeg():
        await c.message.answer(t(lang, "no_ffmpeg"))
        await c.answer()
        return

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

    # ⚠️ DIQQƏT: Option B – apply_effects özü unikal fayl yaradır və yol qaytarır
    try:
        new_path = apply_effects(song.file_path, None, effects)
    except Exception as e:
        await c.message.answer(f"❌ Effekt tətbiq xətası: {e}")
        await c.answer()
        return

    if not os.path.exists(new_path):
        await c.message.answer("❌ Effekt faylı yaradılmadı.")
        await c.answer()
        return

    file = FSInputFile(new_path, filename=os.path.basename(new_path))
    await c.message.answer_document(file)
    await c.answer()


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


def socket_song_actions(lang_code: str, yt_id: str):
    """song_actions üçün helper — birbaşa lang_code verib dict yükləyirik."""
<<<<<<< HEAD
    return song_actions(_lang(lang_code), yt_id)
=======
    return song_actions(_lang(lang_code), yt_id)
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
