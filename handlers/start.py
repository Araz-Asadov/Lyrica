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
# 👤 Create or get user
# ---------------------------------------------------------------
async def _get_or_create_user(tg_id: int) -> User:
    """Get or create user with cache update - optimized for performance"""
    from utils.cache import set_cached_lang, clear_user_cache
    
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if not user:
            user = User(tg_id=tg_id, language="az")   # DEFAULT = AZERBAIJANI
            s.add(user)
            await s.commit()
            set_cached_lang(tg_id, "az")  # Cache new user
        else:
            # Update last_seen only if it's been more than 5 minutes (reduce DB writes)
            from datetime import datetime, timedelta, timezone
            now = datetime.now(timezone.utc)
            if not user.last_seen:
                user.last_seen = now
                await s.commit()
            else:
                # Compare timezone-aware datetimes
                time_diff = now - user.last_seen
                if time_diff > timedelta(minutes=5):
                    user.last_seen = now
                    await s.commit()
            # Update cache if language changed
            set_cached_lang(tg_id, user.language)
        return user


# ---------------------------------------------------------------
# 🌐 Get user language
# ---------------------------------------------------------------
async def _user_lang(tg_id: int) -> str:
    """Get user language with cache"""
    from utils.cache import get_cached_lang, set_cached_lang
    
    # Check cache first
    cached_lang = get_cached_lang(tg_id)
    if cached_lang:
        return cached_lang
    
    # Query database
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        lang = u.language if u else "az"
        set_cached_lang(tg_id, lang)  # Cache it
        return lang


# ---------------------------------------------------------------
# 🚀 /start
# ---------------------------------------------------------------
@router.message(CommandStart())
async def on_start(m: Message):
    user = await _get_or_create_user(m.from_user.id)
    lang = user.language or "az"

    is_admin = m.from_user.id in settings.ADMIN_IDS

    # Modern və gözəl welcome mesajı
    welcome_texts = {
        "az": (
            "🎵 <b>LyricaBot-a xoş gəlmisiniz!</b>\n\n"
            "Mən sizin musiqi asistentinizəm. Mənimlə:\n\n"
            "🎯 <b>Mahnı tapmaq:</b>\n"
            "• Mahnı adı yazın\n"
            "• TikTok/Instagram/YouTube linki göndərin\n"
            "• Video və ya səs mesajı göndərin\n\n"
            "🎼 <b>Musiqi notları:</b>\n"
            "• /not əmrindən sonra musiqi göndərin\n\n"
            "⭐ <b>Sevimlilər:</b>\n"
            "• Tapdığınız mahnıları sevimlilərə əlavə edin\n\n"
            "Aşağıdakı düymələrdən istifadə edin və ya /help yazın:"
        ),
        "en": (
            "🎵 <b>Welcome to LyricaBot!</b>\n\n"
            "I'm your music assistant. With me you can:\n\n"
            "🎯 <b>Find songs:</b>\n"
            "• Type a song name\n"
            "• Send TikTok/Instagram/YouTube link\n"
            "• Send video or voice message\n\n"
            "🎼 <b>Music notes:</b>\n"
            "• Send /not then send music\n\n"
            "⭐ <b>Favorites:</b>\n"
            "• Add found songs to favorites\n\n"
            "Use the buttons below or type /help:"
        ),
        "ru": (
            "🎵 <b>Добро пожаловать в LyricaBot!</b>\n\n"
            "Я ваш музыкальный ассистент. Со мной вы можете:\n\n"
            "🎯 <b>Найти песни:</b>\n"
            "• Введите название песни\n"
            "• Отправьте ссылку TikTok/Instagram/YouTube\n"
            "• Отправьте видео или голосовое сообщение\n\n"
            "🎼 <b>Ноты музыки:</b>\n"
            "• Отправьте /not затем отправьте музыку\n\n"
            "⭐ <b>Избранное:</b>\n"
            "• Добавьте найденные песни в избранное\n\n"
            "Используйте кнопки ниже или введите /help:"
        ),
    }

    welcome_text = welcome_texts.get(lang, welcome_texts["az"])

    # Set bot commands for this user in their language
    from app import set_bot_commands
    await set_bot_commands(m.bot, user_id=m.from_user.id)

    await m.answer(
        welcome_text,
        reply_markup=main_menu(_lang(lang), is_admin=is_admin),
        parse_mode="HTML"
    )


# ---------------------------------------------------------------
# 🌐 /lang
# ---------------------------------------------------------------
@router.message(Command("lang"))
async def on_lang_command(m: Message):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🇦🇿 Azərbaycan", callback_data="setlang:az"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang:en"),
        InlineKeyboardButton(text="🇷🇺 Russian", callback_data="setlang:ru"),
    )
    lang = await _user_lang(m.from_user.id)
    await m.answer(t(lang, "set_language"), reply_markup=b.as_markup())


# ---------------------------------------------------------------
# 🌍 Language menu (settings)
# ---------------------------------------------------------------
@router.callback_query(F.data == "menu:lang")
async def on_lang_menu(c: CallbackQuery):
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="🇦🇿 Azərbaycan", callback_data="setlang:az"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="setlang:en"),
        InlineKeyboardButton(text="🇷🇺 Russian", callback_data="setlang:ru"),
    )
    lang = await _user_lang(c.from_user.id)

    await c.message.edit_text(t(lang, "set_language"), reply_markup=b.as_markup())
    await c.answer()


# ---------------------------------------------------------------
# 🌐 Language selected → save
# ---------------------------------------------------------------
@router.callback_query(F.data.startswith("setlang:"))
async def on_set_lang(c: CallbackQuery):
    lang = c.data.split(":")[1]

    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()
        if u:
            u.language = lang
            await s.commit()

    # Clear cache for this user to ensure all handlers use new language
    from utils.cache import clear_user_cache, set_cached_lang
    clear_user_cache(c.from_user.id)
    set_cached_lang(c.from_user.id, lang)

    # Update bot commands for this user in their language
    from app import set_bot_commands
    await set_bot_commands(c.bot, user_id=c.from_user.id)

    flag = {"az": "🇦🇿", "en": "🇬🇧", "ru": "🇷🇺"}.get(lang, "🌐")
    is_admin = c.from_user.id in settings.ADMIN_IDS

    # Format lang_set message with language name
    lang_names = {"az": "Azərbaycan", "en": "English", "ru": "Русский"}
    lang_name = lang_names.get(lang, lang.upper())
    
    await c.message.edit_text(
        f"{flag} {t(lang, 'lang_set', lang_name=lang_name)} 🎉\n\n{t(lang, 'start_menu')}",
        reply_markup=main_menu(_lang(lang), is_admin=is_admin)
    )
    await c.answer()


# ---------------------------------------------------------------
# 🔎 Search menu open
# ---------------------------------------------------------------
@router.callback_query(F.data == "menu:search")
async def on_menu_search(c: CallbackQuery):
    lang = await _user_lang(c.from_user.id)
    
    search_prompts = {
        "az": (
            "🔍 <b>Axtarış</b>\n\n"
            "Mahnı tapmaq üçün:\n\n"
            "• Mahnı adı yazın\n"
            "• TikTok/Instagram/YouTube linki göndərin\n"
            "• Video və ya səs mesajı göndərin\n\n"
            "Məsələn: <code>Billie Eilish bad guy</code>"
        ),
        "en": (
            "🔍 <b>Search</b>\n\n"
            "To find songs:\n\n"
            "• Type song name\n"
            "• Send TikTok/Instagram/YouTube link\n"
            "• Send video or voice message\n\n"
            "Example: <code>Billie Eilish bad guy</code>"
        ),
        "ru": (
            "🔍 <b>Поиск</b>\n\n"
            "Чтобы найти песни:\n\n"
            "• Введите название песни\n"
            "• Отправьте ссылку TikTok/Instagram/YouTube\n"
            "• Отправьте видео или голосовое сообщение\n\n"
            "Пример: <code>Billie Eilish bad guy</code>"
        ),
    }
    
    prompt = search_prompts.get(lang, search_prompts["az"])
    await c.message.edit_text(prompt, parse_mode="HTML")
    await c.answer()


# ---------------------------------------------------------------
# ℹ️ Help menu (callback)
# ---------------------------------------------------------------
@router.callback_query(F.data == "menu:help")
async def on_menu_help(c: CallbackQuery):
    from handlers.commands import cmd_help
    
    lang = await _user_lang(c.from_user.id)
    
    # Use the same help text from commands.py
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
    await c.message.edit_text(help_text, parse_mode="HTML")
    await c.answer()


# ---------------------------------------------------------------
# Language loader helper
# ---------------------------------------------------------------
def _lang(lang: str):
    from i18n import _load
    return _load(lang)

