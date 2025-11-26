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

    try:
        return orjson.loads(file.read_bytes())
    except Exception:
        return {}


def t(lang: str, key: str, **kwargs) -> str:
    data = _load(lang)
    
    # Support nested keys like "recognition.processing"
    keys = key.split(".")
    text = data
    for k in keys:
        if isinstance(text, dict):
            text = text.get(k, key)
        else:
            text = key
            break
    
    if not isinstance(text, str):
        text = key

    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text

    return text
