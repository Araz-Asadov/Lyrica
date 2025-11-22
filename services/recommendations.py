from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from models import Song, Favorite, RequestLog, Playlist
from typing import List

async def popular_songs(session: AsyncSession, limit: int = 10) -> list[Song]:
    q = select(Song).order_by(desc(Song.play_count), desc(Song.views)).limit(limit)
    res = await session.execute(q)
    return res.scalars().all()

async def for_you(session: AsyncSession, user_id: int, limit: int = 10) -> list[Song]:
    # simple: songs favored by others but not yet favored by user
    sub_user_favs = select(Favorite.song_id).where(Favorite.user_id == user_id)
    q = (
        select(Song)
        .where(Song.id.not_in(sub_user_favs))
        .order_by(desc(Song.play_count), desc(Song.views))
        .limit(limit)
    )
    res = await session.execute(q)
    return res.scalars().all()

async def mood_based(session: AsyncSession, mood: str, limit: int = 10) -> list[Song]:
    q = select(Song).where(Song.mood == mood).order_by(desc(Song.play_count)).limit(limit)
    res = await session.execute(q)
    return res.scalars().all()

async def genre_based(session: AsyncSession, genre: str, limit: int = 10) -> list[Song]:
    q = select(Song).where(Song.genre == genre).order_by(desc(Song.play_count)).limit(limit)
    res = await session.execute(q)
    return res.scalars().all()