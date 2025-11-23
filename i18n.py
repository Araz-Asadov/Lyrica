import orjson
from pathlib import Path
<<<<<<< HEAD
=======
from functools import lru_cache
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a

LOCALES_DIR = Path("./locales")
DEFAULT_LANG = "az"

<<<<<<< HEAD

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

=======
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
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
<<<<<<< HEAD

    return text
=======
    return text
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
