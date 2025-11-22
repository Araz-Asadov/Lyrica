from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from sqlalchemy import select, func
from db import SessionLocal
from models import User, Song, RequestLog
from config import settings
from i18n import t
from utils.logger import log_event

import os
from datetime import datetime, timedelta


async def _get_user_lang(user_id: int) -> str:
    """Get user language with cache"""
    from utils.cache import get_cached_lang, set_cached_lang
    
    # Check cache first
    cached_lang = get_cached_lang(user_id)
    if cached_lang:
        return cached_lang
    
    # Query database
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == user_id))).scalars().first()
        lang = user.language if user else "az"
        set_cached_lang(user_id, lang)  # Cache it
        return lang

router = Router()


# 🧠 Admin yoxlama funksiyası
def _is_admin(tg_id: int) -> bool:
    return tg_id in set(settings.ADMIN_IDS or [])


# ⚙️ Admin menyusu
@router.callback_query(F.data == "menu:admin")
async def menu_admin(c: CallbackQuery):
    if not _is_admin(c.from_user.id):
        await c.answer("⛔ Giriş icazəsi yoxdur.", show_alert=True)
        return

    # Get today's date (start of day)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async with SessionLocal() as s:
        # Total stats
        total_users = (await s.execute(select(func.count(User.id)))).scalar() or 0
        songs = (await s.execute(select(func.count(Song.id)))).scalar() or 0
        reqs = (await s.execute(select(func.count(RequestLog.id)))).scalar() or 0
        
        # Daily active users (users who logged in today)
        # Compare dates properly - last_seen should be >= today_start
        daily_active = (
            await s.execute(
                select(func.count(User.id)).where(
                    User.last_seen >= today_start
                )
            )
        ).scalar() or 0
        
        # Top songs
        pops = (
            (await s.execute(select(Song).order_by(Song.play_count.desc()).limit(5)))
            .scalars()
            .all()
        )

    top_songs = "\n".join([f"🎵 {s.title} ({s.play_count})" for s in pops]) or "—"
    
    # Create inline keyboard with buttons
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Günlük istifadəçilər", callback_data="admin:daily_users")],
        [InlineKeyboardButton(text="🔄 Yenilə", callback_data="menu:admin")]
    ])
    
    stats = (
        f"📊 <b>Lyrica Bot Statistikası</b>\n\n"
        f"👥 Ümumi istifadəçilər: {total_users}\n"
        f"📅 Günlük aktiv istifadəçilər: <b>{daily_active}</b>\n"
        f"🎶 Mahnılar: {songs}\n"
        f"🧾 Sorğular: {reqs}\n\n"
        f"🔥 Ən çox dinlənənlər:\n{top_songs}"
    )

    await c.message.answer(stats, parse_mode="HTML", reply_markup=kb)
    await c.answer()

    log_event("INFO", f"Admin panel açıldı ({c.from_user.id})")


# 📋 Günlük aktiv istifadəçilərin siyahısı
@router.callback_query(F.data == "admin:daily_users")
async def show_daily_users(c: CallbackQuery):
    if not _is_admin(c.from_user.id):
        await c.answer("⛔ Giriş icazəsi yoxdur.", show_alert=True)
        return
    
    # Get today's date (start of day)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async with SessionLocal() as s:
        # Get all users who were active today
        daily_users = (
            await s.execute(
                select(User).where(
                    User.last_seen >= today_start
                ).order_by(User.last_seen.desc())
            )
        ).scalars().all()
    
    if not daily_users:
        lang = await _get_user_lang(c.from_user.id)
        await c.message.answer(t(lang, "no_daily_users"))
        await c.answer()
        return
    
    # Format user list
    user_list = []
    for idx, user in enumerate(daily_users, 1):
        # Get user info from Telegram
        lang = await _get_user_lang(c.from_user.id)
        try:
            member = await c.bot.get_chat(user.tg_id)
            username = f"@{member.username}" if member.username else t(lang, "username_not_found")
            full_name = member.full_name or t(lang, "unknown")
        except:
            username = t(lang, "not_found")
            full_name = f"ID: {user.tg_id}"
        
        # Format last_seen time
        last_seen_time = user.last_seen.strftime("%H:%M:%S") if user.last_seen else t(lang, "unknown")
        user_list.append(
            t(lang, "user_info", 
              num=str(idx), 
              name=full_name, 
              username=username, 
              time=last_seen_time, 
              lang=user.language.upper())
        )
    
    lang = await _get_user_lang(c.from_user.id)
    # Split into chunks if too long (Telegram limit is 4096 chars)
    message_text = t(lang, "daily_users_title", count=len(daily_users)) + "\n\n" + "\n\n".join(user_list)
    
    if len(message_text) > 4000:
        # Send in chunks
        chunks = [message_text[i:i+4000] for i in range(0, len(message_text), 4000)]
        for chunk in chunks:
            await c.message.answer(chunk, parse_mode="HTML")
    else:
        await c.message.answer(message_text, parse_mode="HTML")
    
    await c.answer()


# 📈 /stats – eyni funksiyanı mesajla çağırmaq
@router.message(Command("stats"))
async def cmd_stats(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("⛔ Yalnız adminlər üçün.")
        return
    await menu_admin(await _mock_callback(m))


# 📅 /daily – günlük istifadəçiləri göstər
@router.message(Command("daily"))
async def cmd_daily(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("⛔ Yalnız adminlər üçün.")
        return
    
    # Get today's date (start of day)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    async with SessionLocal() as s:
        # Get all users who were active today
        daily_users = (
            await s.execute(
                select(User).where(
                    User.last_seen >= today_start
                ).order_by(User.last_seen.desc())
            )
        ).scalars().all()
    
    if not daily_users:
        lang = await _get_user_lang(m.from_user.id)
        await m.answer(t(lang, "no_daily_users"))
        return
    
    # Format user list
    user_list = []
    for idx, user in enumerate(daily_users, 1):
        lang = await _get_user_lang(m.from_user.id)
        try:
            member = await m.bot.get_chat(user.tg_id)
            username = f"@{member.username}" if member.username else t(lang, "username_not_found")
            full_name = member.full_name or t(lang, "unknown")
        except:
            username = t(lang, "not_found")
            full_name = f"ID: {user.tg_id}"
        
        last_seen_time = user.last_seen.strftime("%H:%M:%S") if user.last_seen else t(lang, "unknown")
        
        lang = await _get_user_lang(m.from_user.id)
        user_list.append(
            t(lang, "user_info", 
              num=str(idx), 
              name=full_name, 
              username=username, 
              time=last_seen_time, 
              lang=user.language.upper())
        )
    
    lang = await _get_user_lang(m.from_user.id)
    message_text = t(lang, "daily_users_title", count=len(daily_users)) + "\n\n" + "\n\n".join(user_list)
    
    if len(message_text) > 4000:
        chunks = [message_text[i:i+4000] for i in range(0, len(message_text), 4000)]
        for chunk in chunks:
            await m.answer(chunk, parse_mode="HTML")
    else:
        await m.answer(message_text, parse_mode="HTML")


# ⚠️ /errors – log faylından son 10 xəta
@router.message(Command("errors"))
async def cmd_errors(m: Message):
    if not _is_admin(m.from_user.id):
        lang = await _get_user_lang(m.from_user.id)
        return await m.answer(t(lang, "admin_only"))

    lang = await _get_user_lang(m.from_user.id)
    log_path = settings.LOG_PATH
    if not os.path.exists(log_path):
        await m.answer(t(lang, "no_log_file"))
        return

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if "[ERROR]" in l][-10:]
        if not lines:
            await m.answer(t(lang, "no_errors"))
            return
        msg = "<b>Son 10 xəta:</b>\n\n" + "\n".join(lines)
        await m.answer(msg[-4000:], parse_mode="HTML")  # Telegram limit
    except Exception as e:
        await m.answer(t(lang, "log_read_error", error=str(e)))


# 🧪 /perf – performans loglarından son 10 ölçüm
@router.message(Command("perf"))
async def cmd_perf(m: Message):
    if not _is_admin(m.from_user.id):
        lang = await _get_user_lang(m.from_user.id)
        return await m.answer(t(lang, "admin_only"))
    lang = await _get_user_lang(m.from_user.id)
    log_path = settings.LOG_PATH
    if not os.path.exists(log_path):
        return await m.answer(t(lang, "log_file_not_found"))

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if "[PERF]" in l][-10:]
        if not lines:
            return await m.answer(t(lang, "no_perf_data"))
        msg = "<b>Son 10 Performans Qeydi:</b>\n\n" + "\n".join(lines)
        await m.answer(msg[-4000:], parse_mode="HTML")
    except Exception as e:
        await m.answer(t(lang, "error", error=str(e)))


# 📨 Broadcast (mass message)
@router.message(Command("broadcast"))
async def broadcast(m: Message):
    if not _is_admin(m.from_user.id):
        return

    lang = await _get_user_lang(m.from_user.id)
    msg = (m.text or "").split(" ", 1)
    if len(msg) < 2:
        await m.answer(t(lang, "broadcast_usage"))
        return

    text = msg[1]
    await m.answer(t(lang, "broadcast_starting"))

    from aiogram import Bot
    bot = m.bot
    sent = 0

    async with SessionLocal() as s:
        users = (
            await s.execute(select(User.tg_id).where(User.is_banned == False))
        ).scalars().all()

    for uid in users:
        try:
            await bot.send_message(uid, text)
            sent += 1
        except Exception:
            pass

    lang = await _get_user_lang(m.from_user.id)
    await m.answer(t(lang, "broadcast_completed", sent=sent))
    log_event("INFO", f"Broadcast tamamlandı: {sent} mesaj")


# 🔧 Daxili köməkçi funksiya – callback əvəzinə mesaj üçün saxta obyekt
async def _mock_callback(m: Message):
    class DummyCallback:
        from_user = m.from_user
        message = m
        async def answer(self, *a, **kw): pass
    return DummyCallback()
