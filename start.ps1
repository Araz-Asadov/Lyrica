# PowerShell script for starting LyricaBot

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   🎵 LyricaBot - Başlatılıyor..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Python yüklənibmi yoxlamaq
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python tapıldı: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Xəta: Python tapılmadı!" -ForegroundColor Red
    Write-Host "Zəhmət olmasa Python 3.11+ quraşdırın." -ForegroundColor Yellow
    Read-Host "Davam etmək üçün Enter düyməsini basın"
    exit 1
}

# Virtual environment yoxlamaq
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "📦 Virtual environment aktivləşdirilir..." -ForegroundColor Yellow
    & .\venv\Scripts\Activate.ps1
}

# Kitabxanaları yoxlamaq
Write-Host "📚 Kitabxanalar yoxlanılır..." -ForegroundColor Yellow
$aiogramInstalled = pip show aiogram 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "📥 Lazım olan kitabxanalar quraşdırılır..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Xəta: Kitabxanalar quraşdırıla bilmədi!" -ForegroundColor Red
        Read-Host "Davam etmək üçün Enter düyməsini basın"
        exit 1
    }
}

# FFmpeg yoxlamaq
$ffmpegInstalled = ffmpeg -version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Xəbərdarlıq: FFmpeg PATH-də tapılmadı." -ForegroundColor Yellow
    Write-Host "Botun bəzi funksiyaları işləməyə bilər." -ForegroundColor Yellow
    Write-Host ""
}

# .env faylını yoxlamaq
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  Xəbərdarlıq: .env faylı tapılmadı." -ForegroundColor Yellow
    Write-Host "Bot config.py-dəki default token ilə işləyəcək." -ForegroundColor Yellow
    Write-Host ""
}

# Botu başlatmaq
Write-Host "✅ Bütün yoxlamalar tamamlandı!" -ForegroundColor Green
Write-Host ""
Write-Host "🤖 Bot işə salınır..." -ForegroundColor Cyan
Write-Host ""
Write-Host "════════════════════════════════════====" -ForegroundColor Cyan
Write-Host "   Botu dayandırmaq üçün Ctrl+C" -ForegroundColor Cyan
Write-Host "════════════════════════════════════====" -ForegroundColor Cyan
Write-Host ""

python app.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Xəta: Bot başladıla bilmədi!" -ForegroundColor Red
    Read-Host "Davam etmək üçün Enter düyməsini basın"
    exit 1
}



