from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from sqlalchemy import select, func
from db import SessionLocal
from models import User, Song, RequestLog
from config import settings
from i18n import t
from utils.logger import log_event

import os
from datetime import datetime

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

    async with SessionLocal() as s:
        users = (await s.execute(select(func.count(User.id)))).scalar() or 0
        songs = (await s.execute(select(func.count(Song.id)))).scalar() or 0
        reqs = (await s.execute(select(func.count(RequestLog.id)))).scalar() or 0
        pops = (
            (await s.execute(select(Song).order_by(Song.play_count.desc()).limit(5)))
            .scalars()
            .all()
        )

    top_songs = "\n".join([f"🎵 {s.title} ({s.play_count})" for s in pops]) or "—"
    stats = f"📊 <b>Lyrica Bot Statistikası</b>\n\n👥 İstifadəçilər: {users}\n🎶 Mahnılar: {songs}\n🧾 Sorğular: {reqs}\n\n🔥 Ən çox dinlənənlər:\n{top_songs}"

    await c.message.answer(stats, parse_mode="HTML")
    await c.answer()

    log_event("INFO", f"Admin panel açıldı ({c.from_user.id})")


# 📈 /stats – eyni funksiyanı mesajla çağırmaq
@router.message(Command("stats"))
async def cmd_stats(m: Message):
    if not _is_admin(m.from_user.id):
        await m.answer("⛔ Yalnız adminlər üçün.")
        return
    await menu_admin(await _mock_callback(m))


# ⚠️ /errors – log faylından son 10 xəta
@router.message(Command("errors"))
async def cmd_errors(m: Message):
    if not _is_admin(m.from_user.id):
        return await m.answer("⛔ Yalnız adminlər üçün.")

    log_path = settings.LOG_PATH
    if not os.path.exists(log_path):
        await m.answer("Heç bir log faylı tapılmadı.")
        return

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if "[ERROR]" in l][-10:]
        if not lines:
            await m.answer("Heç bir xəta tapılmadı.")
            return
        msg = "<b>Son 10 xəta:</b>\n\n" + "\n".join(lines)
        await m.answer(msg[-4000:], parse_mode="HTML")  # Telegram limit
    except Exception as e:
        await m.answer(f"Log oxunarkən xəta: {e}")


# 🧪 /perf – performans loglarından son 10 ölçüm
@router.message(Command("perf"))
async def cmd_perf(m: Message):
    if not _is_admin(m.from_user.id):
        return await m.answer("⛔ Yalnız adminlər üçün.")
    log_path = settings.LOG_PATH
    if not os.path.exists(log_path):
        return await m.answer("Log faylı tapılmadı.")

    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if "[PERF]" in l][-10:]
        if not lines:
            return await m.answer("Performans məlumatı tapılmadı.")
        msg = "<b>Son 10 Performans Qeydi:</b>\n\n" + "\n".join(lines)
        await m.answer(msg[-4000:], parse_mode="HTML")
    except Exception as e:
        await m.answer(f"Xəta: {e}")


# 📨 Broadcast (mass message)
@router.message(Command("broadcast"))
async def broadcast(m: Message):
    if not _is_admin(m.from_user.id):
        return

    msg = (m.text or "").split(" ", 1)
    if len(msg) < 2:
        await m.answer("İstifadə: /broadcast <mətn>")
        return

    text = msg[1]
    await m.answer("📢 Yayım başlayır...")

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

    await m.answer(f"✅ Yayım tamamlandı. Göndərildi: {sent}")
    log_event("INFO", f"Broadcast tamamlandı: {sent} mesaj")


# 🔧 Daxili köməkçi funksiya – callback əvəzinə mesaj üçün saxta obyekt
async def _mock_callback(m: Message):
    class DummyCallback:
        from_user = m.from_user
        message = m
        async def answer(self, *a, **kw): pass
    return DummyCallback()
