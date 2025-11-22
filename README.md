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

### 🎵 New Music Recognition Features

- 🎵 **TikTok/Instagram/YouTube Link Recognition** — Send a link from TikTok, Instagram Reels, or YouTube, and the bot will extract the audio and identify the song
- 📹 **Video to Music** — Send a video file, and the bot will extract audio and identify the song (Shazam-like)
- 🎤 **Voice Message Recognition** — Send a voice message (humming/whistling), and the bot will identify the song using music recognition (Shazam effect)
- 🎼 **Music Notes Extraction** — Use `/not` command and send music (audio, voice, or video) to extract musical notes and chords

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

AudD API — Music recognition (Shazam-like functionality)

Machine Learning / Voice

Vosk Speech Recognition (opsional) — Səs mesajlarını mətnə çevirir

librosa (opsional) — Music notes extraction from audio files

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

---

## 📦 Quraşdırma və Başlatma

### 1️⃣ Lazım olan şeylər

- **Python 3.11+** — [Python.org](https://www.python.org/downloads/) üzərindən yükləyin
- **FFmpeg** — Audio emalı üçün lazımdır
  - Windows: [FFmpeg yükləyin](https://ffmpeg.org/download.html) və PATH-ə əlavə edin
  - Və ya proyektdəki `ffmpeg-8.0-essentials_build/bin/ffmpeg.exe` işlədilə bilər

### 2️⃣ Kitabxanaları quraşdırmaq

```bash
pip install -r requirements.txt
```

### 3️⃣ Bot Token almaq

1. Telegram-da [@BotFather](https://t.me/botfather) ilə əlaqə saxlayın
2. `/newbot` komandasını göndərin
3. Botun adını və username-ini seçin
4. Verilən token-i kopyalayın

### 4️⃣ Konfiqurasiya

**Variant 1: .env faylı yaratmaq (tövsiyə olunur)**

Proyekt kökündə `.env` faylı yaradın:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
DATABASE_URL=sqlite+aiosqlite:///./data/bot.db
DOWNLOAD_DIR=./data/downloads
GENIUS_API_TOKEN=your_genius_token_optional
VOSK_MODEL_PATH=path/to/vosk/model_optional
```

**Variant 2: Config.py-də default dəyərlər**

`config.py` faylında `BOT_TOKEN` dəyərini dəyişdirin (yalnız test üçün).

### 5️⃣ Botu başlatmaq

**Windows (Command Prompt):**
```bash
start.bat
```

**Windows (PowerShell):**
```powershell
.\start.ps1
```

**Və ya birbaşa Python:**
```bash
python app.py
```

**Linux/Mac:**
```bash
python3 app.py
```

### ✅ Yoxlama

Bot işə düşdükdən sonra Telegram-da botunuzu açın və `/start` komandasını göndərin.  
Əgər bot cavab verirsə, deməli hər şey işləyir! 🎉

---

## 📝 İstifadə

### Əsas komandalar

- `/start` — Botu başlat və menyunu aç
- `/help` — Kömək və istifadə qaydası
- `/favorites` — Sevimli mahnılarınızı görün
- `/not` — Musiqi notlarını çıxar
- `/lang` — Dili dəyiş

### Mahnı tapmaq

1. **Link göndərin:** TikTok, Instagram Reels, və ya YouTube linki
2. **Mahnı adı yazın:** Məsələn: `Billie Eilish bad guy`
3. **Video göndərin:** Video faylından audio çıxarılacaq və mahnı tanınacaq
4. **Səs mesajı göndərin:** Zümzümə edin, bot mahnını tapacaq

### Musiqi notlarını çıxartmaq

1. `/not` və ya `/note` komandasını göndərin
2. Musiqi faylı göndərin (audio, voice, və ya video)
3. Bot notları avtomatik çıxaracaq

---

## ⚙️ Tənzimləmələr

### Environment dəyişənləri

| Dəyişən | Təsvir | Default |
|---------|--------|---------|
| `BOT_TOKEN` | Telegram bot token | `config.py`-də |
| `ADMIN_IDS` | Admin istifadəçi ID-ləri (vergüllə ayrılmış) | `7787374541` |
| `DATABASE_URL` | Verilənlər bazası URL | `sqlite+aiosqlite:///./data/bot.db` |
| `DOWNLOAD_DIR` | Yükləmə qovluğu | `./data/downloads` |
| `GENIUS_API_TOKEN` | Genius API token (opsional) | - |
| `VOSK_MODEL_PATH` | Vosk model yolu (opsional) | - |
| `MAX_CONCURRENT_DOWNLOADS` | Eyni vaxtda maksimum yükləmə | `3` |
| `CACHE_EXPIRATION_MINUTES` | Cache müddəti (dəqiqə) | `30` |

---

## 🐛 Problem həlli

### Bot işləmir

1. Python versiyasını yoxlayın: `python --version` (3.11+ olmalıdır)
2. Kitabxanaları yeniləyin: `pip install -r requirements.txt --upgrade`
3. Bot token-in düzgün olduğunu yoxlayın
4. Log faylına baxın: `logs/lyrica.log`

### FFmpeg tapılmır

- FFmpeg PATH-ə əlavə edilməlidir
- Və ya `ffmpeg-8.0-essentials_build/bin/` qovluğunu PATH-ə əlavə edin
- Windows-da: Environment Variables → Path → Add

### Database xətası

- `data/` qovluğunun yaradılıb-yaradılmadığını yoxlayın
- `data/bot.db` faylının silinməsi ilə verilənlər bazası yenilənəcək

### Mahnı tapılmır

- İnternet əlaqəsini yoxlayın
- YouTube API limitlərinə diqqət edin
- Log faylına xəta mesajlarını yoxlayın

---

## 📞 Dəstək

Probleminiz varsa:
- Log faylına baxın: `logs/lyrica.log`
- GitHub Issues-da sual qoyun
- Admin panel vasitəsilə statistika yoxlayın: `/admin`