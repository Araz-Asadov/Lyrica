import os
import datetime
import asyncio
import inspect

# 📁 Log qovluğu
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "lyrica.log")

# Qovluğu yoxla/yarat
os.makedirs(LOG_DIR, exist_ok=True)


def _timestamp() -> str:
    """UTC formatında zaman möhürü"""
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def log_event(level: str, message: str):
    """
    Əsas log funksiyası.
    level: INFO / WARNING / ERROR / PERF
    message: hadisə mətni
    """
    frame = inspect.stack()[1]
    caller = os.path.basename(frame.filename)
    line = frame.lineno

    ts = _timestamp()
    entry = f"[{ts}] [{level.upper()}] ({caller}:{line}) {message}"

    # Konsolda da göstər
    print(entry)

    # Fayla yaz
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


async def log_perf(section: str, start_time: float):
    """
    Performans ölçümü üçün:
    await log_perf("lyrics_fetch", start_time)
    """
    elapsed = (asyncio.get_event_loop().time() - start_time) * 1000
    msg = f"{section} tamamlandı ({elapsed:.1f} ms)"
    log_event("PERF", msg)


def log_error(e: Exception, context: str = ""):
    """
    Xətaları yığmaq üçün.
    """
    msg = f"{context}: {type(e).__name__} - {e}"
    log_event("ERROR", msg)
