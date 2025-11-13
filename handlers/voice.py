from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from db import SessionLocal
from models import User
from i18n import t
import os
import tempfile
router = Router()

@router.message(F.voice)
async def on_voice(m: Message):
    async with SessionLocal() as s:
        u = (await s.execute(select(User).where(User.tg_id == m.from_user.id))).scalars().first()
    lang = u.language if u else "az"
    await m.answer(t(lang, "voice_prompt"))
    # Try transcription with Vosk if configured
    model_path = os.getenv("VOSK_MODEL_PATH", "")
    if not model_path:
        return
    # download ogg
    with tempfile.TemporaryDirectory() as td:
        ogg_path = os.path.join(td, "voice.ogg")
        wav_path = os.path.join(td, "voice.wav")
        await m.bot.download(m.voice.file_id, destination=ogg_path)
        # convert to wav 16k mono
        import subprocess
        subprocess.run(["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path], check=True)
        try:
            import vosk, json
            rec = vosk.KaldiRecognizer(vosk.Model(model_path), 16000)
            with open(wav_path, "rb") as f:
                while True:
                    data = f.read(4000)
                    if len(data) == 0:
                        break
                    if rec.AcceptWaveform(data):
                        pass
            res = json.loads(rec.FinalResult()).get("text", "").strip()
            if res:
                await m.answer(f"🔎 {res}")
            else:
                await m.answer("Tanınmadı.")
        except Exception as e:
            await m.answer("Transkripsiya alınmadı.")