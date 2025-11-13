from aiogram import Router, F
from aiogram.types import CallbackQuery, InputFile
from sqlalchemy import select
from db import SessionLocal
from models import User, Favorite, Song
router = Router()

@router.callback_query(F.data == "menu:favorites")
async def menu_favorites(c: CallbackQuery):
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()
        if not u:
            await c.answer("User not found", show_alert=True); return
        favs = (await s.execute(select(Favorite, Song).join(Song, Favorite.song_id == Song.id).where(Favorite.user_id == u.id))).all()
    if not favs:
        from i18n import t
        await c.message.answer(t(u.language, "fav_empty")); await c.answer(); return
    # send as list
    text = "⭐ Favorites:\n" + "\n".join([f"- {row[1].title}" for row in favs[:25]])
    await c.message.answer(text)
    await c.answer()