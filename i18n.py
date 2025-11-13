import orjson
from pathlib import Path
from functools import lru_cache

LOCALES_DIR = Path("./locales")
DEFAULT_LANG = "az"

@lru_cache(maxsize=16)
def _load(lang: str) -> dict:
    lang = (lang or DEFAULT_LANG).lower()
    file = LOCALES_DIR / f"{lang}.json"
    if not file.exists():
        file = LOCALES_DIR / f"{DEFAULT_LANG}.json"
    return orjson.loads(file.read_bytes())

def t(lang: str, key: str, **kwargs) -> str:
    data = _load(lang)
    text = data.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text