import subprocess
import os
import uuid
import time
from typing import Dict, Optional
from utils.common import ensure_ffmpeg

FFMPEG_PATH = r"C:\Users\user\OneDrive\Desktop\LyricaBot\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe"

if os.path.exists(FFMPEG_PATH):
    os.environ["PATH"] += os.pathsep + os.path.dirname(FFMPEG_PATH)
else:
    print("⚠️ FFmpeg tapılmadı, sistem PATH istifadə olunacaq.")


def build_filter(effects: Dict) -> str:
    filters = []

    bass_db = float(effects.get("bass_db", 0))
    treble_db = float(effects.get("treble_db", 0))

    if bass_db:
        filters.append(f"equalizer=f=60:t=q:w=1.0:g={bass_db}")
    if treble_db:
        filters.append(f"equalizer=f=10000:t=q:w=1.0:g={treble_db}")

    if effects.get("reverb"):
        filters.append("aecho=0.8:0.88:60:0.4")
    if effects.get("echo"):
        filters.append("aecho=0.6:0.6:100|180:0.25|0.15")

    pitch = float(effects.get("pitch_semitones", 0))
    if pitch:
        factor = 2 ** (pitch / 12.0)
        filters.append(f"asetrate=44100*{factor},aresample=44100")

    speed = float(effects.get("speed", 1.0))
    if speed and speed != 1.0:
        while speed < 0.5:
            filters.append("atempo=0.5")
            speed /= 0.5
        while speed > 2.0:
            filters.append("atempo=2.0")
            speed /= 2.0
        filters.append(f"atempo={speed:.2f}")

    return ",".join(filters)


def cleanup_old_fx_files(base_dir: str):
    now = time.time()
    for f in os.listdir(base_dir):
        if ".fx." in f and f.endswith(".mp3"):
            path = os.path.join(base_dir, f)
            if now - os.path.getmtime(path) > 3600:
                try:
                    os.remove(path)
                except:
                    pass


def apply_effects(input_path: str, output_path: Optional[str], effects: Dict) -> str:
    ensure_ffmpeg()
    base_dir = os.path.dirname(input_path)
    cleanup_old_fx_files(base_dir)

    filter_chain = build_filter(effects)

    name, ext = os.path.splitext(os.path.basename(input_path))
    effect_type = next(iter(effects.keys()), "fx")
    unique_id = str(uuid.uuid4())[:8]

    output_path = os.path.join(base_dir, f"{name}.fx.{effect_type}.{unique_id}.mp3")

    cmd = [
        "ffmpeg", "-y",
        "-i", input_path
    ]

    if filter_chain:
        cmd += ["-af", filter_chain]

    cmd += ["-vn", "-codec:a", "libmp3lame", "-q:a", "4", output_path]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error: {e}")
        return input_path

    return output_path
