import orjson
from pathlib import Path

LOCALES_DIR = Path("./locales")
DEFAULT_LANG = "az"


def _load(lang: str) -> dict:
    """JSON dil faylını oxuyur, cache İSTİFADƏ ETMİR."""
    lang = (lang or DEFAULT_LANG).lower()
    file = LOCALES_DIR / f"{lang}.json"

    if not file.exists():
        file = LOCALES_DIR / f"{DEFAULT_LANG}.json"

    try:
        return orjson.loads(file.read_bytes())
    except Exception:
        return {}
    

def t(lang: str, key: str, **kwargs) -> str:
    """
    i18n tərcümə funksiyası.
    Dil JSON-da açar yoxdursa → key qaytarır.
    Formatlama üçün .format(**kwargs) istifadə edir.
    """
    data = _load(lang)
    text = data.get(key, key)

    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text

    return text
