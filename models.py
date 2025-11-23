from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, ForeignKey, DateTime, Text, UniqueConstraint
from sqlalchemy.sql import func
from db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    language: Mapped[str] = mapped_column(String(5), default="az")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Song(Base):
    __tablename__ = "songs"
    id: Mapped[int] = mapped_column(primary_key=True)
    youtube_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    artist: Mapped[str] = mapped_column(String(200), default="")
    duration: Mapped[int] = mapped_column(Integer, default=0)
    file_path: Mapped[str] = mapped_column(String(500))
    thumbnail: Mapped[str] = mapped_column(String(500), default="")
    views: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    last_played: Mapped[str] = mapped_column(DateTime(timezone=True), nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="")
    genre: Mapped[str] = mapped_column(String(50), default="")
    mood: Mapped[str] = mapped_column(String(50), default="")

class Favorite(Base):
    __tablename__ = "favorites"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"))
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("user_id", "song_id", name="uq_user_song"),)

class Playlist(Base):
    __tablename__ = "playlists"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100))
    is_for_you: Mapped[bool] = mapped_column(Boolean, default=False)
    mood: Mapped[str] = mapped_column(String(50), default="")
    genre: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())

class PlaylistItem(Base):
    __tablename__ = "playlist_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    playlist_id: Mapped[int] = mapped_column(ForeignKey("playlists.id"))
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id"))
    ord: Mapped[int] = mapped_column(Integer, default=0)

class RequestLog(Base):
    __tablename__ = "request_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    query: Mapped[str] = mapped_column(Text)
    via_voice: Mapped[bool] = mapped_column(Boolean, default=False)
    matched_song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id"), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
