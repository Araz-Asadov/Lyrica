import shutil
from datetime import timedelta

def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None

def ensure_ffmpeg():
    if not has_ffmpeg():
        raise RuntimeError("FFmpeg not found")

def seconds_to_hms(s: int) -> str:
    td = timedelta(seconds=s or 0)
    return str(td)