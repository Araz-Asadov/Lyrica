from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from db import SessionLocal
from models import User, Song, Favorite
from keyboards import song_actions
<<<<<<< HEAD
from i18n import t

router = Router()


# ============================================================
# ℹ️ /help — kömək
# ============================================================
@router.message(Command("help"))
async def cmd_help(m: Message):
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == m.from_user.id))
        ).scalars().first()

    lang = user.language if user else "az"

    await m.answer(t(lang, "help_text"))
=======
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
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a


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
<<<<<<< HEAD
# ⭐ /favorites — sevimlilər
# ============================================================
@router.message(Command("favorites"))
async def show_favorites(m: Message):
=======
# 🎵 /favorites + “⭐ Sevimlilər”
# ============================================================
@router.message(Command("favorites"))
@router.message(F.text.in_(["⭐ Sevimlilər"]))
async def show_favorites(m: Message):

>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == m.from_user.id))
        ).scalars().first()

        if not user:
            await m.answer("⚠️ Zəhmət olmasa əvvəl /start yaz.")
            return

<<<<<<< HEAD
        lang = user.language
=======
        lang = user.language or "az"
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a

        fav_songs = (
            await s.execute(
                select(Song)
                .join(Favorite)
                .where(Favorite.user_id == user.id)
                .order_by(Song.title.asc())
            )
        ).scalars().all()

    if not fav_songs:
<<<<<<< HEAD
        await m.answer(t(lang, "favorites_empty"))
=======
        await m.answer("⭐ Sevimlilərə heç nə əlavə olunmayıb.")
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
        return

    btns = [
        [InlineKeyboardButton(text=f"🎧 {song.title}", callback_data=f"favopen:{song.youtube_id}")]
        for song in fav_songs
    ]

<<<<<<< HEAD
    await m.answer(t(lang, "favorites_list"), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


# ============================================================
# ⭐ Menü → Sevimlilər
# ============================================================
@router.callback_query(F.data == "menu:favorites")
async def menu_favorites(c: CallbackQuery):
=======
    await m.answer("🎶 Sevimli mahnıların:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))


# ============================================================
# 🎵 Start menyusu → menu:favorites
# ============================================================
@router.callback_query(F.data == "menu:favorites")
async def menu_fav(c: CallbackQuery):

>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
    async with SessionLocal() as s:
        user = (
            await s.execute(select(User).where(User.tg_id == c.from_user.id))
        ).scalars().first()

<<<<<<< HEAD
        lang = user.language
=======
        lang = user.language if user else "az"
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a

        fav_songs = (
            await s.execute(
                select(Song)
                .join(Favorite)
                .where(Favorite.user_id == user.id)
                .order_by(Song.title.asc())
            )
        ).scalars().all()

    if not fav_songs:
<<<<<<< HEAD
        await c.message.edit_text(t(lang, "favorites_empty"))
=======
        await c.message.answer("⭐ Sevimlilərdə mahnı yoxdur.")
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
        await c.answer()
        return

    btns = [
        [InlineKeyboardButton(text=f"🎧 {song.title}", callback_data=f"favopen:{song.youtube_id}")]
        for song in fav_songs
    ]

<<<<<<< HEAD
    await c.message.edit_text(t(lang, "favorites_list"), reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
=======
    await c.message.edit_text("🎶 Sevimli mahnıların:", reply_markup=InlineKeyboardMarkup(inline_keyboard=btns))
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
    await c.answer()


# ============================================================
<<<<<<< HEAD
# 🎧 Sevimlilər → Mahnı seçildi
=======
# 🎧 Sevimlilər → mahnı seçildi
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
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

<<<<<<< HEAD
    lang = user.language

    await c.message.answer(
        f"🎧 {song.title}\n👤 {song.artist}",
        reply_markup=song_actions(lang, song.youtube_id)
=======
    lang = user.language or "az"

    await c.message.answer(
        f"🎧 {song.title}\n👤 {song.artist}",
        reply_markup=song_actions(_lang(lang), song.youtube_id)
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
    )
    await c.answer()
