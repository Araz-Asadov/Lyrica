@echo off
chcp 65001 >nul
echo.
echo ========================================
echo    🎵 LyricaBot - Başlatılıyor...
echo ========================================
echo.

REM Python yüklənibmi yoxlamaq
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Xəta: Python tapılmadı!
    echo Zəhmət olmasa Python 3.11+ quraşdırın.
    pause
    exit /b 1
)

REM Virtual environment yoxlamaq (əgər varsa)
if exist "venv\Scripts\activate.bat" (
    echo 📦 Virtual environment aktivləşdirilir...
    call venv\Scripts\activate.bat
)

REM Kitabxanaları yoxlamaq və quraşdırmaq
echo 📚 Kitabxanalar yoxlanılır...
pip show aiogram >nul 2>&1
if errorlevel 1 (
    echo 📥 Lazım olan kitabxanalar quraşdırılır...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Xəta: Kitabxanalar quraşdırıla bilmədi!
        pause
        exit /b 1
    )
)

REM FFmpeg yüklənibmi yoxlamaq
ffmpeg -version >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Xəbərdarlıq: FFmpeg PATH-də tapılmadı.
    echo Botun bəzi funksiyaları işləməyə bilər.
    echo.
)

REM Bot token yoxlamaq
if not exist ".env" (
    echo ⚠️  Xəbərdarlıq: .env faylı tapılmadı.
    echo Bot config.py-dəki default token ilə işləyəcək.
    echo.
)

REM Botu başlatmaq
echo ✅ Bütün yoxlamalar tamamlandı!
echo.
echo 🤖 Bot işə salınır...
echo.
echo ════════════════════════════════════
echo    Botu dayandırmaq üçün Ctrl+C
echo ════════════════════════════════════
echo.

python app.py

if errorlevel 1 (
    echo.
    echo ❌ Xəta: Bot başladıla bilmədi!
    pause
    exit /b 1
)



