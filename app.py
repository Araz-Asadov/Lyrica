import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
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


# 🔧 BOT KOMANDALARINI TƏYİN ET — PLAYLISTS VƏ SEARCH SİLİNDİ
async def set_bot_commands(bot: Bot, user_id: int | None = None):
    lang = await get_user_lang(user_id) if user_id else "az"

    d = {
        "start": "🚀 Başlat",
        "favorites": "⭐ Sevimlilər",
        "lang": "🌐 Dili dəyiş",
        "help": "ℹ️ Kömək",
    }

    commands = [
        BotCommand(command="start", description=d["start"]),
        BotCommand(command="favorites", description=d["favorites"]),
        BotCommand(command="lang", description=d["lang"]),
        BotCommand(command="help", description=d["help"]),
    ]

    await bot.set_my_commands(commands)
    logging.info(f"✅ Telegram komanda list yeniləndi. Dil: {lang.upper()}")


# 🚀 BOT START
async def main():
    await init_db()

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher()
    setup_routers(dp)

    # Default komanda siyahısı (azərbaycan dili)
    await set_bot_commands(bot)

    logging.info("🤖 Bot işə salınır...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    if not settings.BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN .env faylında yoxdur!")
<<<<<<< HEAD
    asyncio.run(main())
=======
    asyncio.run(main())
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
