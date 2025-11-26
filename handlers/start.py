from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from db import SessionLocal
from models import User
from i18n import t
from i18n import _load as _lang     # <-- DİL JSON-u yükləmək üçün ƏLAVƏ OLDU
from keyboards import main_menu
from config import settings

router = Router()


# -----------------------------
# DB user helpers
# -----------------------------
async def _get_user(tg_id: int) -> User | None:
    async with SessionLocal() as s:
        return (
            await s.execute(select(User).where(User.tg_id == tg_id))
        ).scalars().first()


async def _create_user(tg_id: int, lang: str = "az") -> User:
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
    builder.row(
        InlineKeyboardButton(
            text="🇦🇿 Azərbaycan dili",
            callback_data="setlang:az"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🇬🇧 English",
            callback_data="setlang:en"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🇷🇺 Русский",
            callback_data="setlang:ru"
        )
    )
    return builder.as_markup()


# -----------------------------
# /start
# -----------------------------
@router.message(CommandStart())
async def on_start(m: Message):
    tg_id = m.from_user.id
    user = await _get_user(tg_id)

    if not user:
        await m.answer(
            "🌐 Zəhmət olmasa dil seçin:\n"
            "Please choose a language:\n"
            "Пожалуйста, выберите язык:",
            reply_markup=language_keyboard()
        )
        return

    lang = user.language or "az"
    is_admin = tg_id in settings.ADMIN_IDS

    await m.answer(
        t(lang, "start_message", name=m.from_user.full_name) + "\n\n" +
        t(lang, "start_menu"),
        reply_markup=main_menu(_lang(lang), is_admin=is_admin)     # <-- DÜZƏLDİLDİ
    )


# -----------------------------
# setlang:xx callback
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
            db_user = (
                await s.execute(select(User).where(User.tg_id == tg_id))
            ).scalars().first()
            if db_user:
                db_user.language = lang
                await s.commit()

    is_admin = tg_id in settings.ADMIN_IDS

    await c.message.edit_text(
        t(lang, "start_message", name=c.from_user.full_name) + "\n\n" +
        t(lang, "start_menu"),
        reply_markup=main_menu(_lang(lang), is_admin=is_admin)      # <-- DÜZƏLDİLDİ
    )
    await c.answer()


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
async def on_lang_command(m: Message):
    lang = await _user_lang(m.from_user.id)
    await m.answer(
        t(lang, "set_language"),
        reply_markup=language_keyboard()
    )


# -----------------------------
# menu:lang callback
# -----------------------------
@router.callback_query(F.data == "menu:lang")
async def on_lang_menu(c: CallbackQuery):
    lang = await _user_lang(c.from_user.id)
    await c.message.edit_text(
        t(lang, "set_language"),
        reply_markup=language_keyboard()
    )
    await c.answer()


# -----------------------------
# menu:search callback
# -----------------------------
@router.callback_query(F.data == "menu:search")
async def on_menu_search(c: CallbackQuery):
    lang = await _user_lang(c.from_user.id)
    await c.message.edit_text(t(lang, "prompt_search"))
    await c.answer()
