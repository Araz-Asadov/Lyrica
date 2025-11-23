from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
<<<<<<< HEAD
from i18n import t


# -----------------------------------------------------------
# 🌍 Əsas menyu — JSON-dan gələn dilə uyğun
# -----------------------------------------------------------
def main_menu(lang: str, is_admin: bool = False):
    kb = InlineKeyboardBuilder()

    kb.row(
        InlineKeyboardButton(
            text=t(lang, "btn_search"),
            callback_data="menu:search"
        ),
        InlineKeyboardButton(
            text=t(lang, "btn_favorites"),
=======


def main_menu(lang_texts: dict, is_admin: bool = False):
    """
    Əsas menyu — Playlist tamamilə çıxarılıb.
    """
    kb = InlineKeyboardBuilder()

    # 🔍 Axtarış + ⭐ Sevimlilər
    kb.row(
        InlineKeyboardButton(
            text=lang_texts.get("btn_search", "🔍 Axtarış"),
            callback_data="menu:search"
        ),
        InlineKeyboardButton(
            text=lang_texts.get("btn_favorites", "⭐ Sevimlilər"),
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
            callback_data="menu:favorites"
        )
    )

<<<<<<< HEAD
    kb.row(
        InlineKeyboardButton(
            text=t(lang, "btn_lang"),
=======
    # 🌐 Dil seçimi
    kb.row(
        InlineKeyboardButton(
            text=lang_texts.get("btn_lang", "🌐 Dil"),
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
            callback_data="menu:lang"
        )
    )

<<<<<<< HEAD
    if is_admin:
        kb.row(
            InlineKeyboardButton(
                text=t(lang, "btn_admin"),
=======
    # ⚙️ Admin yalnız icazəli user üçün
    if is_admin:
        kb.row(
            InlineKeyboardButton(
                text=lang_texts.get("btn_admin", "⚙️ Admin Panel"),
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
                callback_data="menu:admin"
            )
        )

    return kb.as_markup()


<<<<<<< HEAD
# -----------------------------------------------------------
# 🎵 Mahnı əməliyyatları — Dilə uyğun
# -----------------------------------------------------------
def song_actions(lang: str, yt_id: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=t(lang, "download"),
                callback_data=f"song:dl:{yt_id}"
            ),
            InlineKeyboardButton(
                text=t(lang, "lyrics"),
=======
def song_actions(lang_dict: dict, yt_id: str):
    """
    Mahnı üçün əməliyyat düymələri:
    - Yüklə
    - Sözlər
    - Tərcümə et
    - Favoritə əlavə et
    - Effektlər
    ❌ Playlist yoxdur
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=lang_dict.get("download", "⬇️ Yüklə"),
                callback_data=f"song:dl:{yt_id}"
            ),
            InlineKeyboardButton(
                text=lang_dict.get("lyrics", "📝 Sözlər"),
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
                callback_data=f"song:ly:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
<<<<<<< HEAD
                text=t(lang, "translate"),
=======
                text=lang_dict.get("translate", "🇦🇿 Tərcümə et"),
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
                callback_data=f"song:tr:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
<<<<<<< HEAD
                text=t(lang, "favorite"),
=======
                text=lang_dict.get("favorite", "⭐ Favoritə əlavə et"),
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
                callback_data=f"song:fav:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
<<<<<<< HEAD
                text=t(lang, "effects"),
=======
                text=lang_dict.get("effects", "🎚️ Effektlər"),
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
                callback_data=f"song:fx:{yt_id}"
            )
        ]
    ])


<<<<<<< HEAD
# -----------------------------------------------------------
# 🎚️ Effekt menyusu – çoxdilli
# -----------------------------------------------------------
def effects_menu(lang: str):
    kb = InlineKeyboardBuilder()

    kb.row(
        InlineKeyboardButton(text=t(lang, "bass_plus6"), callback_data="fx:bass:6"),
        InlineKeyboardButton(text=t(lang, "treble_plus4"), callback_data="fx:treble:4")
    )
    kb.row(
        InlineKeyboardButton(text=t(lang, "reverb"), callback_data="fx:reverb:1"),
        InlineKeyboardButton(text=t(lang, "echo"), callback_data="fx:echo:1")
    )
    kb.row(
        InlineKeyboardButton(text=t(lang, "pitch_up"), callback_data="fx:pitch:2"),
        InlineKeyboardButton(text=t(lang, "pitch_down"), callback_data="fx:pitch:-2")
    )
    kb.row(
        InlineKeyboardButton(text=t(lang, "speed_up"), callback_data="fx:speed:1.25"),
        InlineKeyboardButton(text=t(lang, "speed_down"), callback_data="fx:speed:0.9")
=======
def effects_menu(lang_texts: dict | None = None):
    """
    Effekt seçimi menyusu — çoxdilli.
    """
    kb = InlineKeyboardBuilder()
    get = (lang_texts or {}).get

    kb.row(
        InlineKeyboardButton(text=get("bass_plus6", "Bass +6dB"), callback_data="fx:bass:6"),
        InlineKeyboardButton(text=get("treble_plus4", "Treble +4dB"), callback_data="fx:treble:4")
    )
    kb.row(
        InlineKeyboardButton(text=get("reverb", "Reverb"), callback_data="fx:reverb:1"),
        InlineKeyboardButton(text=get("echo", "Echo"), callback_data="fx:echo:1")
    )
    kb.row(
        InlineKeyboardButton(text=get("pitch_up", "Pitch +2"), callback_data="fx:pitch:2"),
        InlineKeyboardButton(text=get("pitch_down", "Pitch -2"), callback_data="fx:pitch:-2")
    )
    kb.row(
        InlineKeyboardButton(text=get("speed_up", "Speed 1.25x"), callback_data="fx:speed:1.25"),
        InlineKeyboardButton(text=get("speed_down", "Speed 0.9x"), callback_data="fx:speed:0.9")
>>>>>>> c534cb30237cc1881397949d2f3e9d910c1a269a
    )

    return kb.as_markup()
