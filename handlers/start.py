from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from db import SessionLocal
from models import User
from i18n import t
from keyboards import main_menu
from config import settings

router = Router()


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
    )
    await c.answer()


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
