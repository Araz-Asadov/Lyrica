from __future__ import annotations

"""Playlist service layer.

Bu modul Playlist və PlaylistItem modelləri üzərindən bütün biznes məntiqini
idarə edir ki, handler-lər sadəcə bu funksiyaları çağırmaqla kifayətlənsin.

Bütün funksiyalar user_id ilə sahiblik yoxlaması aparır.
"""

from typing import Iterable, List, Dict, Any

from sqlalchemy import select, func

from db import SessionLocal
from models import Playlist, PlaylistItem, Song, User


class PlaylistNotFound(Exception):
    pass


class ForbiddenPlaylistAccess(Exception):
    pass


async def _ensure_owner(playlist_id: int, user_id: int, include_items: bool = False) -> Playlist:
    """Verilən playlist-in mövcudluğunu və sahibliyini yoxla.

    include_items=True olarsa, PlaylistItem-lər də yüklənir.
    """
    async with SessionLocal() as s:
        stmt = select(Playlist).where(Playlist.id == playlist_id, Playlist.user_id == user_id)
        result = await s.execute(stmt)
        playlist = result.scalars().first()
        if not playlist:
            raise PlaylistNotFound

        if include_items:
            # PlaylistItem-ləri ayrıca oxuyuruq (sadə üsul)
            items_stmt = (
                select(PlaylistItem, Song)
                .join(Song, PlaylistItem.song_id == Song.id)
                .where(PlaylistItem.playlist_id == playlist_id)
                .order_by(PlaylistItem.position.asc())
            )
            items_res = await s.execute(items_stmt)
            # Bu funksiyada playlist obyektini sadəcə qaytarırıq, item-ləri üst qat funksiyalar yükləyə bilər.
        return playlist


# =============================================================================
# CRUD
# =============================================================================


async def create_playlist(user_id: int, name: str) -> Playlist:
    async with SessionLocal() as s:
        p = Playlist(user_id=user_id, name=name)
        s.add(p)
        await s.commit()
        await s.refresh(p)
        return p


async def list_playlists(user_id: int) -> List[Playlist]:
    async with SessionLocal() as s:
        stmt = select(Playlist).where(Playlist.user_id == user_id).order_by(Playlist.created_at.desc())
        res = await s.execute(stmt)
        return list(res.scalars().all())


async def get_playlist(playlist_id: int, user_id: int) -> Dict[str, Any]:
    """Playlist-i və item-ləri ilə birlikdə qaytar.

    Nəticə dict strukturu şəklindədir ki, handler-lər rahat istifadə etsin.
    """
    async with SessionLocal() as s:
        stmt = select(Playlist).where(Playlist.id == playlist_id, Playlist.user_id == user_id)
        res = await s.execute(stmt)
        pl = res.scalars().first()
        if not pl:
            raise PlaylistNotFound

        items_stmt = (
            select(PlaylistItem, Song)
            .join(Song, PlaylistItem.song_id == Song.id)
            .where(PlaylistItem.playlist_id == playlist_id)
            .order_by(PlaylistItem.position.asc())
        )
        items_res = await s.execute(items_stmt)
        rows = items_res.all()

        items = [
            {
                "item_id": pi.id,
                "position": pi.position,
                "song_id": song.id,
                "youtube_id": song.youtube_id,
                "title": song.title,
                "artist": song.artist,
                "duration": song.duration,
            }
            for (pi, song) in rows
        ]

        return {
            "id": pl.id,
            "name": pl.name,
            "created_at": pl.created_at,
            "items": items,
        }


async def delete_playlist(playlist_id: int, user_id: int) -> None:
    async with SessionLocal() as s:
        stmt = select(Playlist).where(Playlist.id == playlist_id, Playlist.user_id == user_id)
        res = await s.execute(stmt)
        pl = res.scalars().first()
        if not pl:
            raise PlaylistNotFound

        await s.delete(pl)
        await s.commit()


async def rename_playlist(playlist_id: int, user_id: int, new_name: str) -> None:
    async with SessionLocal() as s:
        stmt = select(Playlist).where(Playlist.id == playlist_id, Playlist.user_id == user_id)
        res = await s.execute(stmt)
        pl = res.scalars().first()
        if not pl:
            raise PlaylistNotFound

        pl.name = new_name
        await s.commit()


# =============================================================================
# Items
# =============================================================================


async def add_item(playlist_id: int, user_id: int, youtube_id: str) -> PlaylistItem:
    """Verilən playlist-ə mövcud mahnını əlavə et.

    Burada song artıq DB-də olmalıdır (search zamanı yaradılır).
    """
    async with SessionLocal() as s:
        # Playlist sahiblik yoxlaması
        stmt_pl = select(Playlist).where(Playlist.id == playlist_id, Playlist.user_id == user_id)
        res_pl = await s.execute(stmt_pl)
        pl = res_pl.scalars().first()
        if not pl:
            raise PlaylistNotFound

        # Mahnı tap
        stmt_song = select(Song).where(Song.youtube_id == youtube_id)
        res_song = await s.execute(stmt_song)
        song = res_song.scalars().first()
        if not song:
            raise ValueError("SONG_NOT_FOUND")

        # Son position
        stmt_last = (
            select(func.max(PlaylistItem.position)).where(PlaylistItem.playlist_id == playlist_id)
        )
        last_pos = (await s.execute(stmt_last)).scalar() or 0
        next_pos = int(last_pos) + 1

        item = PlaylistItem(
            playlist_id=playlist_id,
            song_id=song.id,
            position=next_pos,
        )
        s.add(item)
        await s.commit()
        await s.refresh(item)
        return item


async def remove_item(playlist_id: int, user_id: int, item_id: int) -> None:
    async with SessionLocal() as s:
        # Playlist sahiblik yoxlaması
        stmt_pl = select(Playlist).where(Playlist.id == playlist_id, Playlist.user_id == user_id)
        res_pl = await s.execute(stmt_pl)
        pl = res_pl.scalars().first()
        if not pl:
            raise PlaylistNotFound

        stmt_item = select(PlaylistItem).where(
            PlaylistItem.id == item_id,
            PlaylistItem.playlist_id == playlist_id,
        )
        res_item = await s.execute(stmt_item)
        item = res_item.scalars().first()
        if not item:
            raise PlaylistNotFound

        await s.delete(item)
        await s.commit()


async def reorder_items(
    playlist_id: int,
    user_id: int,
    items_positions: Dict[int, int],  # item_id -> new_position
) -> None:
    async with SessionLocal() as s:
        stmt_pl = select(Playlist).where(Playlist.id == playlist_id, Playlist.user_id == user_id)
        res_pl = await s.execute(stmt_pl)
        pl = res_pl.scalars().first()
        if not pl:
            raise PlaylistNotFound

        stmt_items = select(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id)
        res_items = await s.execute(stmt_items)
        items = res_items.scalars().all()

        for it in items:
            if it.id in items_positions:
                it.position = int(items_positions[it.id])

        await s.commit()


async def get_play_queue(playlist_id: int, user_id: int) -> List[Dict[str, Any]]:
    """Sıralanmış mahnı siyahısını qaytar.

    Hər element dict:
    {
        "song_id", "youtube_id", "title", "artist", "duration", "file_path"
    }
    """
    async with SessionLocal() as s:
        stmt_pl = select(Playlist).where(Playlist.id == playlist_id, Playlist.user_id == user_id)
        res_pl = await s.execute(stmt_pl)
        pl = res_pl.scalars().first()
        if not pl:
            raise PlaylistNotFound

        stmt = (
            select(PlaylistItem, Song)
            .join(Song, PlaylistItem.song_id == Song.id)
            .where(PlaylistItem.playlist_id == playlist_id)
            .order_by(PlaylistItem.position.asc())
        )
        res = await s.execute(stmt)
        rows = res.all()

        queue: List[Dict[str, Any]] = []
        for pi, song in rows:
            queue.append(
                {
                    "song_id": song.id,
                    "youtube_id": song.youtube_id,
                    "title": song.title,
                    "artist": song.artist,
                    "duration": song.duration,
                    "file_path": song.file_path,
                }
            )
        return queue
