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
async def on_lang(m: Message):
    lang = await _user_lang(m.from_user.id)
    await m.answer(t(lang, "set_language"), reply_markup=language_keyboard())
