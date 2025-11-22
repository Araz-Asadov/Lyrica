import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeChat
from config import settings
from db import init_db
from handlers import setup_routers
from models import User
from sqlalchemy import select
from db import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


# 🔍 İstifadəçinin dili
async def get_user_lang(user_id: int) -> str:
    async with SessionLocal() as s:
        u = (
            await s.execute(select(User).where(User.tg_id == user_id))
        ).scalars().first()
        return u.language if u and u.language else "az"


# 🔧 BOT KOMANDALARINI TƏYİN ET — TAM FORMAT
async def set_bot_commands(bot: Bot, user_id: int | None = None):
    lang = await get_user_lang(user_id) if user_id else "az"

    # Çoxdilli komanda siyahısı
    commands_dict = {
        "az": [
            ("start", "🚀 Botu başlat"),
            ("help", "ℹ️ Kömək və istifadə qaydası"),
            ("favorites", "⭐ Sevimli mahnılarım"),
            ("not", "🎼 Musiqi notlarını çıxar"),
            ("note", "🎼 Musiqi notlarını çıxar"),
            ("lang", "🌐 Dili dəyiş"),
        ],
        "en": [
            ("start", "🚀 Start the bot"),
            ("help", "ℹ️ Help and usage guide"),
            ("favorites", "⭐ My favorite songs"),
            ("not", "🎼 Extract music notes"),
            ("note", "🎼 Extract music notes"),
            ("lang", "🌐 Change language"),
        ],
        "ru": [
            ("start", "🚀 Запустить бота"),
            ("help", "ℹ️ Помощь и руководство"),
            ("favorites", "⭐ Мои любимые песни"),
            ("not", "🎼 Извлечь ноты музыки"),
            ("note", "🎼 Извлечь ноты музыки"),
            ("lang", "🌐 Изменить язык"),
        ],
    }

    commands_list = commands_dict.get(lang, commands_dict["az"])
    commands = [BotCommand(command=cmd, description=desc) for cmd, desc in commands_list]

    if user_id:
        # Set commands for specific user
        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=user_id))
        logging.info(f"✅ Telegram komanda list yeniləndi. İstifadəçi: {user_id}, Dil: {lang.upper()}")
    else:
        # Set default commands for all users
        await bot.set_my_commands(commands)
        logging.info(f"✅ Telegram komanda list yeniləndi. Dil: {lang.upper()}")


# 🚀 BOT START
async def main():
    await init_db()

    # Start cache cleanup task for better memory management
    from utils.cache import start_cache_cleanup_task
    start_cache_cleanup_task()
    logging.info("✅ Cache cleanup task başladıldı")

    # Bot with timeout settings to prevent network errors
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()
    setup_routers(dp)

    # Default komanda siyahısı (azərbaycan dili)
    await set_bot_commands(bot)

    logging.info("🤖 Bot işə salınır...")
    
    # Start polling with better error handling
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            close_bot_session=False
        )
    except Exception as e:
        logging.error(f"❌ Bot xətası: {e}")
        raise


if __name__ == "__main__":
    if not settings.BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN .env faylında yoxdur!")
    asyncio.run(main())
