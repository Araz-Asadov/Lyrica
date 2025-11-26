from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select
from db import SessionLocal
from models import User, Playlist
from i18n import t
from services import playlists_service

router = Router()


# ============================================================
# 🆕 /newplaylist - Yeni playlist yarat
# ============================================================
@router.message(Command("newplaylist"))
async def new_playlist(m: Message):
    args = (m.text or "").split(maxsplit=1)
    name = args[1].strip() if len(args) > 1 else "My Playlist"

    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    if not u:
        await m.answer("User not found")
        return

    pl = await playlists_service.create_playlist(u.id, name)
    await m.answer(t(u.language, "pl_created", name=pl.name))


# ============================================================
# 📻 /playlists və menyudakı Playlists düyməsi
# ============================================================
@router.message(Command("playlists"))
async def cmd_playlists(m: Message):
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    if not u:
        await m.answer("User not found")
        return

    lang = u.language
    pls = await playlists_service.list_playlists(u.id)
    if not pls:
        await m.answer(t(lang, "pl_empty"))
        return

    lines = [f"📻 <b>{p.name}</b> (id={p.id})" for p in pls[:25]]
    await m.answer("\n".join(lines), parse_mode="HTML")


@router.callback_query(F.data == "menu:playlists")
async def show_playlists(c: CallbackQuery):
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()
    if not u:
        await c.answer("User not found", show_alert=True)
        return

    lang = u.language
    pls = await playlists_service.list_playlists(u.id)
    if not pls:
        await c.message.answer(t(lang, "pl_empty"))
        await c.answer()
        return

    text = "📻 Playlists:\n" + "\n".join([f"- {p.name} (id={p.id})" for p in pls[:25]])
    await c.message.answer(text)
    await c.answer()


# ============================================================
# 🗑 /delplaylist <id> - Playlist sil
# ============================================================
@router.message(Command("delplaylist"))
async def delete_playlist_cmd(m: Message):
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    if not u:
        await m.answer("User not found")
        return

    parts = (m.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await m.answer("İstifadə: /delplaylist <id>")
        return

    pl_id = int(parts[1])
    try:
        await playlists_service.delete_playlist(pl_id, u.id)
    except playlists_service.PlaylistNotFound:
        await m.answer(t(u.language, "pl_not_found"))
        return

    await m.answer(t(u.language, "pl_deleted", id=pl_id))


# ============================================================
# ✏ /renameplaylist <id> <yeni ad>
# ============================================================
@router.message(Command("renameplaylist"))
async def rename_playlist_cmd(m: Message):
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    if not u:
        await m.answer("User not found")
        return

    parts = (m.text or "").split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        await m.answer("İstifadə: /renameplaylist <id> <yeni_ad>")
        return

    pl_id = int(parts[1])
    new_name = parts[2].strip()
    try:
        await playlists_service.rename_playlist(pl_id, u.id, new_name)
    except playlists_service.PlaylistNotFound:
        await m.answer(t(u.language, "pl_not_found"))
        return

    await m.answer(t(u.language, "pl_renamed", id=pl_id, name=new_name))


# ============================================================
# ➕ /playlist_add <playlist_id> <youtube_id>
# ============================================================
@router.message(Command("playlist_add"))
async def playlist_add_cmd(m: Message):
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    if not u:
        await m.answer("User not found")
        return

    parts = (m.text or "").split(maxsplit=2)
    if len(parts) < 3 or not parts[1].isdigit():
        await m.answer("İstifadə: /playlist_add <playlist_id> <youtube_id>")
        return

    pl_id = int(parts[1])
    yt_id = parts[2].strip()

    try:
        item = await playlists_service.add_item(pl_id, u.id, yt_id)
    except playlists_service.PlaylistNotFound:
        await m.answer(t(u.language, "pl_not_found"))
        return
    except ValueError:
        await m.answer(t(u.language, "song_not_found"))
        return

    await m.answer(t(u.language, "pl_item_added", id=pl_id))


# ============================================================
# ❌ /playlist_remove <playlist_id> <item_id>
# ============================================================
@router.message(Command("playlist_remove"))
async def playlist_remove_cmd(m: Message):
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    if not u:
        await m.answer("User not found")
        return

    parts = (m.text or "").split(maxsplit=2)
    if len(parts) < 3 or not (parts[1].isdigit() and parts[2].isdigit()):
        await m.answer("İstifadə: /playlist_remove <playlist_id> <item_id>")
        return

    pl_id = int(parts[1])
    item_id = int(parts[2])

    try:
        await playlists_service.remove_item(pl_id, u.id, item_id)
    except playlists_service.PlaylistNotFound:
        await m.answer(t(u.language, "pl_not_found"))
        return

    await m.answer(t(u.language, "pl_item_removed", id=pl_id))


# ============================================================
# 🔁 /playlist_reorder <playlist_id> <item_id> <new_pos>
# ============================================================
@router.message(Command("playlist_reorder"))
async def playlist_reorder_cmd(m: Message):
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    if not u:
        await m.answer("User not found")
        return

    parts = (m.text or "").split(maxsplit=3)
    if len(parts) < 4 or not (parts[1].isdigit() and parts[2].isdigit() and parts[3].isdigit()):
        await m.answer("İstifadə: /playlist_reorder <playlist_id> <item_id> <new_position>")
        return

    pl_id = int(parts[1])
    item_id = int(parts[2])
    new_pos = int(parts[3])

    try:
        await playlists_service.reorder_items(pl_id, u.id, {item_id: new_pos})
    except playlists_service.PlaylistNotFound:
        await m.answer(t(u.language, "pl_not_found"))
        return

    await m.answer(t(u.language, "pl_reordered", id=pl_id))


# ============================================================
# ▶ /playlist_play <playlist_id>
# ============================================================
@router.message(Command("playlist_play"))
async def playlist_play_cmd(m: Message):
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    if not u:
        await m.answer("User not found")
        return

    parts = (m.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await m.answer("İstifadə: /playlist_play <playlist_id>")
        return

    pl_id = int(parts[1])

    try:
        queue = await playlists_service.get_play_queue(pl_id, u.id)
    except playlists_service.PlaylistNotFound:
        await m.answer(t(u.language, "pl_not_found"))
        return

    if not queue:
        await m.answer(t(u.language, "pl_empty"))
        return

    await m.answer(t(u.language, "pl_playing", id=pl_id))

    # Sadə ardıcıl göndərmə (hazırda delay yoxdur, Telegram özü sıraya qoyur)
    from aiogram.types import FSInputFile
    for item in queue:
        if not item["file_path"]:
            continue
        try:
            file = FSInputFile(item["file_path"], filename=f"{item['title']}.mp3")
            await m.answer_document(file)
        except Exception:
            continue


# ============================================================
# 🎵 Inline: song_actions → "➕ Playlist" düyməsi
# ============================================================
@router.callback_query(F.data.startswith("song:pl:"))
async def cb_choose_playlist_for_song(c: CallbackQuery):
    """Mahnını playlist-ə əlavə etmək üçün playlist seçimi.

    callback_data: song:pl:<yt_id>
    """
    parts = c.data.split(":", 2)
    if len(parts) != 3:
        await c.answer("Invalid data", show_alert=True)
        return

    yt_id = parts[2]

    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()
    if not u:
        await c.answer("User not found", show_alert=True)
        return

    lang = u.language
    pls = await playlists_service.list_playlists(u.id)

    if not pls:
        # Heç bir playlist yoxdur
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=t(lang, "playlist.create_new"),
                        callback_data=f"pl:new:{yt_id}",
                    )
                ]
            ]
        )
        await c.message.answer(t(lang, "playlist.none_for_user"), reply_markup=kb)
        await c.answer()
        return

    builder = InlineKeyboardBuilder()
    for p in pls:
        builder.row(
            InlineKeyboardButton(
                text=p.name,
                callback_data=f"pl:add:{p.id}:{yt_id}",
            )
        )

    # Yeni playlist yaratmaq üçün köməkçi düymə
    builder.row(
        InlineKeyboardButton(
            text=t(lang, "playlist.create_new"),
            callback_data=f"pl:new:{yt_id}",
        )
    )

    await c.message.answer(
        t(lang, "playlist.choose_for_song"),
        reply_markup=builder.as_markup(),
    )
    await c.answer()


@router.callback_query(F.data.startswith("pl:add:"))
async def cb_add_to_playlist(c: CallbackQuery):
    """Seçilmiş playlist-ə mahnı əlavə et.

    callback_data: pl:add:<playlist_id>:<yt_id>
    """
    parts = c.data.split(":", 3)
    if len(parts) != 4 or not parts[2].isdigit():
        await c.answer("Invalid data", show_alert=True)
        return

    _pl, _add, pl_id_str, yt_id = parts
    pl_id = int(pl_id_str)

    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()
    if not u:
        await c.answer("User not found", show_alert=True)
        return

    lang = u.language

    try:
        await playlists_service.add_item(pl_id, u.id, yt_id)
    except playlists_service.PlaylistNotFound:
        await c.message.answer(t(lang, "pl_not_found"))
        await c.answer()
        return
    except ValueError:
        await c.message.answer(t(lang, "song_not_found"))
        await c.answer()
        return

    await c.message.answer(t(lang, "playlist.added_to_playlist"))
    await c.answer()


@router.callback_query(F.data.startswith("pl:new:"))
async def cb_playlist_new_hint(c: CallbackQuery):
    """Yeni playlist yaratmaq üçün sadə köməkçi.

    Hazırda inline FSM istifadə etmirik, istifadəçiyə /newplaylist
    əmrindən istifadə etməyi tövsiyə edirik.
    """
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == c.from_user.id))).scalars().first()
    if not u:
        await c.answer("User not found", show_alert=True)
        return

    lang = u.language
    await c.message.answer(t(lang, "playlist.use_newplaylist_cmd"))
    await c.answer()
