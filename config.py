from pydantic import BaseModel, Field
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()


class Settings(BaseModel):
    # 🔑 Bot əsas parametrləri
    BOT_TOKEN: str = Field(default=os.getenv("BOT_TOKEN", "8540090917:AAE37twZtyK6CISJSxbNaq4bT40Ur9bo6e8"))
    ADMIN_IDS: list[int] = Field(
        default=[int(x.strip()) for x in os.getenv("ADMIN_IDS", "7787374541").split(",") if x.strip().isdigit()]
    )

    # 💾 PostgreSQL DATABASE
    DATABASE_URL: str = Field(
        default=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/lyrica_db"
        )
    )

    # 📂 Fayl yükləmə yolları
    DOWNLOAD_DIR: str = Field(default=os.getenv("DOWNLOAD_DIR", "./data/downloads"))
    GENIUS_API_TOKEN: str = Field(default=os.getenv("GENIUS_API_TOKEN", ""))
    VOSK_MODEL_PATH: str = Field(default=os.getenv("VOSK_MODEL_PATH", ""))

    # 🧪 Test və monitor parametrləri
    TEST_MODE: bool = Field(default=bool(int(os.getenv("TEST_MODE", "0"))))
    ENABLE_MONITOR: bool = Field(default=bool(int(os.getenv("ENABLE_MONITOR", "1"))))
    LOG_PATH: str = Field(default=os.getenv("LOG_PATH", "./logs/lyrica.log"))

    # 🚀 Performans parametrləri
    MAX_CONCURRENT_DOWNLOADS: int = Field(default=int(os.getenv("MAX_CONCURRENT_DOWNLOADS", "3")))
    CACHE_EXPIRATION_MINUTES: int = Field(default=int(os.getenv("CACHE_EXPIRATION_MINUTES", "30")))


settings = Settings()

# Ensure folders
Path(settings.DOWNLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path("./data").mkdir(parents=True, exist_ok=True)
Path("./logs").mkdir(parents=True, exist_ok=True)


# 🧩 Debug üçün qısa status
try:
    print(
        f"🟢 Lyrica Config Loaded | TEST_MODE={settings.TEST_MODE} | LOG={settings.LOG_PATH} | Monitor={'On' if settings.ENABLE_MONITOR else 'Off'}"
    )
except UnicodeEncodeError:
    print(
        f"[OK] Lyrica Config Loaded | TEST_MODE={settings.TEST_MODE} | LOG={settings.LOG_PATH} | Monitor={'On' if settings.ENABLE_MONITOR else 'Off'}"
    )
