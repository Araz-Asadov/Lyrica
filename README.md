# 🎵 LyricaBot

**LyricaBot** is a multilingual Telegram bot designed for searching, downloading, and enhancing songs with effects and lyrics translation.  
Built with **Python 3.11+** and **Aiogram 3**, it provides a simple yet powerful music assistant with YouTube integration, lyrics fetching, favorites, playlists, and smart audio effects.

---

## 🚀 Features

- 🔎 **YouTube Song Search** — Find songs by title, artist, or YouTube link  
- 🎧 **Download MP3** — Download high-quality audio from YouTube  
- 📝 **Lyrics Fetch & Translate** — Automatically retrieve lyrics and translate them  
- ⭐ **Favorites System** — Save your favorite songs for quick access  
- 📻 **Playlists** — Create, manage, and play your own playlists  
- 🎚️ **Audio Effects** — Apply Bass, Reverb, Echo, Speed, and Pitch effects using FFmpeg  
- 🌐 **Multilingual Interface** — Supports **Azerbaijani**, **English**, and **Russian**  
- ⚙️ **Admin Panel** — View statistics and broadcast messages  
- 🧠 **Smart Cache** — Keeps user lyrics and translations in memory for faster response

---

## 🧩 Tech Stack
Backend

Python 3.11+

Aiogram 3 — Asynchronous Telegram Bot Framework

AsyncIO — Asynchronous architecture for high-performance message processing

Database

SQLite — Lightweight embedded database

SQLAlchemy ORM (Async) — Database models & async queries

Alembic (optional) — Database migrations (əlavə etmək istəyinə görə)

Music & Media Processing

FFmpeg — Audio processing (Bass, Pitch, Reverb, Echo, Speed, Trim, Merge və s.)

ffmpeg-python — FFmpeg komandalarını Python içindən idarə edən wrapper

yt-dlp — YouTube musiqi və video yükləmə üçün ən stabil kitabxana

External APIs

Genius API — Lyrics axtarışı

Lrclib API — Alternativ lyrics provayderi (AZ, TR, RU daha stabil)

Deep Translator (Google Translator) — Lyrics tərcüməsi

Machine Learning / Voice

Vosk Speech Recognition (opsional) — Səs mesajlarını mətnə çevirir

Internationalization

Custom JSON i18n system — Azərbaycan, İngilis, Rus dilləri üçün JSON faylları

Dynamic language loader — DB-yə əsasən istifadəçi dilini avtomatik seçir

Architecture

Modular Handlers — start, search, playlists, favorites, admin, voice

Service Layer — youtube.py, lyrics.py, audio.py (təmiz arxitektura)

Router-based structure — Aiogram 3 Router sistemi ilə idarə olunan modullar

Caching layer — User lyrics memory (smart RAM cache)

Other Libraries

Pydantic — Settings/config validation

python-dotenv — .env konfiqurasiya faylı

httpx — Asynchronous HTTP client

pathlib — File paths and directory handling

logging — Bot loglama sistemi