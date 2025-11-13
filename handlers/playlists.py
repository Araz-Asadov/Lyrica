from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select
from db import SessionLocal
from models import User, Playlist, Song, PlaylistItem
from i18n import t

router = Router()

@router.message(Command("newplaylist"))
async def new_playlist(m: Message):
    args = (m.text or "").split(maxsplit=1)
    name = args[1].strip() if len(args) > 1 else "My Playlist"
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
        if not u:
            await m.answer("User not found"); return
        p = Playlist(user_id=u.id, name=name)
        s.add(p); await s.commit()
        await m.answer(t(u.language, "pl_created", name=name))

@router.callback_query(F.data == "menu:playlists")
async def show_playlists(c: CallbackQuery):
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()
        pls = (await s.execute(select(Playlist).where(Playlist.user_id == u.id))).scalars().all()
    if not pls:
        await c.message.answer(t(u.language, "pl_empty")); await c.answer(); return
    text = "📻 Playlists:\n" + "\n".join([f"- {p.name} (id={p.id})" for p in pls[:25]])
    await c.message.answer(text)
    await c.answer()