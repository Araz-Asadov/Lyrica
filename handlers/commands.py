from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from db import SessionLocal
from models import User, Song, Favorite
from keyboards import song_actions
from i18n import _load, t

router = Router()

# ============================================================
# 🧩 Dil yükləyici
# ============================================================
def _lang(code: str):
    return _load(code)


# ============================================================
# ℹ️ /help — kömək komandası
# ============================================================
@router.message(Command("help"))
async def cmd_help(m: Message):
    await m.answer(
        "📘 Kömək\n\n"
        "/start – Başlat\n"
        "/lang – Dil seçimi\n"
        "/favorites – Sevimlilər\n"
        "/help – Bu menyu\n\n"
        "Sadəcə mahnının adını yaz və endir!"
    )


# ============================================================
# 🌐 /lang — dil seçimi
# ============================================================
@router.message(Command("lang"))
async def cmd_lang(m: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇦🇿 AZ", callback_data="setlang:az"),
            InlineKeyboardButton(text="🇬🇧 EN", callback_data="setlang:en"),
            InlineKeyboardButton(text="🇷🇺 RU", callback_data="setlang:ru"),
        ]
    ])
    await m.answer("🌍 Dil seç:", reply_markup=kb)


# ============================================================
# 🎵 /favorites + “⭐ Sevimlilər”
# ============================================================
@router.message(Command("favorites"))
@router.message(F.text.in_(["⭐ Sevimlilər"]))
async def show_favorites(m: Message):

    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == m.from_user.id))
        ).scalars().first()

        if not user:
            await m.answer("⚠️ Zəhmət olmasa əvvəl /start yaz.")
            return

        lang = user.language or "az"

        fav_songs = (
            await s.execute(
                select(Song)
                .join(Favorite)
                .where(Favorite.user_id == user.id)
                .order_by(Song.title.asc())
            )
        ).scalars().all()

    if not fav_songs:
        await m.answer("⭐ Sevimlilərə heç nə əlavə olunmayıb.")
        return

    btns = [
        [InlineKeyboardButton(text=f"🎧 {song.title}", callback_data=f"favopen:{song.youtube_id}")]
        for song in fav_songs
    ]

    await m.answer("🎶 Sevimli mahnıların:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


# ============================================================
# 🎵 Start menyusu → menu:favorites
# ============================================================
@router.callback_query(F.data == "menu:favorites")
async def menu_fav(c: CallbackQuery):

    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()

        lang = user.language if user else "az"

        fav_songs = (
            await s.execute(
                select(Song)
                .join(Favorite)
                .where(Favorite.user_id == user.id)
                .order_by(Song.title.asc())
            )
        ).scalars().all()

    if not fav_songs:
        await c.message.answer("⭐ Sevimlilərdə mahnı yoxdur.")
        await c.answer()
        return

    btns = [
        [InlineKeyboardButton(text=f"🎧 {song.title}", callback_data=f"favopen:{song.youtube_id}")]
        for song in fav_songs
    ]

    await c.message.edit_text("🎶 Sevimli mahnıların:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
    await c.answer()


# ============================================================
# 🎧 Sevimlilər → mahnı seçildi
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
        await c.answer("⚠️ Mahnı tapılmadı.", show_alert=True)
        return

    lang = user.language or "az"

    await c.message.answer(
        f"🎧 {song.title}\n👤 {song.artist}",
        reply_markup=song_actions(_lang(lang), song.youtube_id)
    )
    await c.answer()
