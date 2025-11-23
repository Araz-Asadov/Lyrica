from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
<<<<<<< HEAD

=======
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
from db import SessionLocal
from models import User
from i18n import t
from keyboards import main_menu
from config import settings

router = Router()


<<<<<<< HEAD
# -----------------------------
# DB user helpers
# -----------------------------
async def _get_user(tg_id: int) -> User | None:
    async with SessionLocal() as s:
        return (await s.execute(select(User).where(User.tg_id == tg_id))).scalars().first()


async def _create_user(tg_id: int, lang="az") -> User:
    async with SessionLocal() as s:
        user = User(tg_id=tg_id, language=lang)
        s.add(user)
        await s.commit()
        return user


async def _user_lang(tg_id: int) -> str:
    user = await _get_user(tg_id)
    return user.language if user else "az"


# -----------------------------
# Language keyboard
# -----------------------------
def language_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🇦🇿 Azərbaycan dili", callback_data="setlang:az"))
    builder.row(InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang:en"))
    builder.row(InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang:ru"))
    return builder.as_markup()


# -----------------------------
# START — always show language first time
# -----------------------------
@router.message(CommandStart())
async def on_start(m: Message):
    tg_id = m.from_user.id

    user = await _get_user(tg_id)

    # FIRST TIME → show language selector
    if not user:
        await m.answer(
            "🌐 Zəhmət olmasa dil seçin:\n"
            "Please choose a language:\n"
            "Пожалуйста, выберите язык:",
            reply_markup=language_keyboard()
        )
        return

    # If user exists → show normal start message
    lang = user.language
    is_admin = tg_id in settings.ADMIN_IDS

    await m.answer(
        t(lang, "start_message") + "\n\n" + t(lang, "start_menu"),
        reply_markup=main_menu(lang, is_admin=is_admin)
    )


# -----------------------------
# Language selection
# -----------------------------
@router.callback_query(F.data.startswith("setlang:"))
async def on_set_lang(c: CallbackQuery):
    tg_id = c.from_user.id
    lang = c.data.split(":")[1]

    user = await _get_user(tg_id)

    if not user:
        await _create_user(tg_id, lang)
    else:
        async with SessionLocal() as s:
            user.language = lang
            await s.commit()

    is_admin = tg_id in settings.ADMIN_IDS

    # AFTER SELECTING LANGUAGE → show START MESSAGE FIRST
    await c.message.edit_text(
        t(lang, "start_message") + "\n\n" + t(lang, "start_menu"),
        reply_markup=main_menu(lang, is_admin=is_admin)
=======
# ---------------------------------------------------------------
# 👤 İstifadəçi yarat və ya mövcud olanı gətir
# ---------------------------------------------------------------
async def _get_or_create_user(tg_id: int) -> User:
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            user = User(tg_id=tg_id, language="az")
            s.add(user)
            await s.commit()
        return user


# ---------------------------------------------------------------
# 🌐 İstifadəçi dilini götür
# ---------------------------------------------------------------
async def _user_lang(tg_id: int) -> str:
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        return u.language if u else "az"


# ---------------------------------------------------------------
# 🚀 /start
# ---------------------------------------------------------------
@router.message(CommandStart())
async def on_start(m: Message):
    user = await _get_or_create_user(m.from_user.id)
    lang = user.language or "az"

    is_admin = m.from_user.id in settings.ADMIN_IDS

    await m.answer(
        t(lang, "start_welcome", name=m.from_user.full_name) + "\n\n" +
        t(lang, "start_menu"),
        reply_markup=main_menu(_lang(lang), is_admin=is_admin)
    )


# ---------------------------------------------------------------
# ℹ️ /help — KÖMƏK
# ---------------------------------------------------------------
@router.message(Command("help"))
async def on_help(m: Message):
    lang = await _user_lang(m.from_user.id)

    await m.answer(
        "📘 Kömək:\n\n"
        "/start — Botu yenidən başlat\n"
        "/lang — Dil seçimi\n"
        "/favorites — Sevimlilər\n"
        "/help — Bu menyu\n\n"
        "Sadəcə mahnının adını yaz, dərhal tapım 🎵"
    )


# ---------------------------------------------------------------
# 🌐 /lang — Dil menyusu
# ---------------------------------------------------------------
@router.message(Command("lang"))
async def on_lang_command(m: Message):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🇦🇿 AZ", callback_data="setlang:az"),
        InlineKeyboardButton(text="🇬🇧 EN", callback_data="setlang:en"),
        InlineKeyboardButton(text="🇷🇺 RU", callback_data="setlang:ru"),
    )
    await m.answer("🌍 Dil seç:", reply_markup=b.as_markup())


# ---------------------------------------------------------------
# 🌍 Dil seçimi (callback)
# ---------------------------------------------------------------
@router.callback_query(F.data == "menu:lang")
async def on_lang_menu(c: CallbackQuery):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🇦🇿 AZ", callback_data="setlang:az"),
        InlineKeyboardButton(text="🇬🇧 EN", callback_data="setlang:en"),
        InlineKeyboardButton(text="🇷🇺 RU", callback_data="setlang:ru"),
    )
    lang = await _user_lang(c.from_user.id)
    await c.message.edit_text(t(lang, "set_language"), reply_markup=b.as_markup())
    await c.answer()


# ---------------------------------------------------------------
# 🌐 Dil seçildi → yaddaşa yaz + menyu yenilə
# ---------------------------------------------------------------
@router.callback_query(F.data.startswith("setlang:"))
async def on_set_lang(c: CallbackQuery):
    lang = c.data.split(":")[1]

    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()
        if u:
            u.language = lang
            await s.commit()

    flag = {"az": "🇦🇿", "en": "🇬🇧", "ru": "🇷🇺"}.get(lang, "🌐")
    is_admin = c.from_user.id in settings.ADMIN_IDS

    await c.message.edit_text(
        f"{flag} {t(lang, 'lang_set', lang_name=lang)} 🎉\n\n{t(lang, 'start_menu')}",
        reply_markup=main_menu(_lang(lang), is_admin=is_admin)
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
    )
    await c.answer()


<<<<<<< HEAD
# -----------------------------
# /help
# -----------------------------
@router.message(Command("help"))
async def on_help(m: Message):
    lang = await _user_lang(m.from_user.id)
    await m.answer(t(lang, "help_text"))


# -----------------------------
# /lang
# -----------------------------
@router.message(Command("lang"))
async def on_lang(m: Message):
    lang = await _user_lang(m.from_user.id)
    await m.answer(t(lang, "set_language"), reply_markup=language_keyboard())
=======
# ---------------------------------------------------------------
# 🔎 Axtarış menyusu
# ---------------------------------------------------------------
@router.callback_query(F.data == "menu:search")
async def on_menu_search(c: CallbackQuery):
    lang = await _user_lang(c.from_user.id)
    await c.message.edit_text(t(lang, "prompt_search"))
    await c.answer()


# ---------------------------------------------------------------
# Dil yükləyici
# ---------------------------------------------------------------
def _lang(lang: str):
    from i18n import _load
    return _load(lang)
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
