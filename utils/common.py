import shutil
from datetime import timedelta, datetime
from sqlalchemy import select
from db import SessionLocal
from models import User

def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def ensure_ffmpeg():
    if not has_ffmpeg():
        raise RuntimeError("FFmpeg not found")

def seconds_to_hms(s: int) -> str:
    td = timedelta(seconds=s or 0)
    return str(td)


async def update_user_last_seen(tg_id: int):
    """Update user's last_seen timestamp"""
    async with SessionLocal() as s:
        user = (await s.execute(select(User).where(User.tg_id == tg_id))).scalars().first()
        if user:
            user.last_seen = datetime.utcnow()
            await s.commit()