from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=10,         # PostgreSQL-də işləyir
    max_overflow=20,      # əlavə bağlantılar
    pool_pre_ping=True,   # ölü bağlantıları yoxlayır
    pool_recycle=1800     # 30 dəqiqədən bir yenilə
)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

class Base(DeclarativeBase):
    pass

async def init_db():
    from models import User, Song, Favorite, Playlist, PlaylistItem, RequestLog  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
