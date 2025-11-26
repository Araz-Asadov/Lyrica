from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from i18n import t


# -----------------------------------------------------------
# 🌍 Əsas menyu
# -----------------------------------------------------------
def main_menu(lang_texts: dict, is_admin: bool = False):
    """
    Əsas menyu — çoxdilli, playlist yoxdur.
    """
    kb = InlineKeyboardBuilder()

    kb.row(
        InlineKeyboardButton(
            text=lang_texts.get("btn_search", "🔍 Axtarış"),
            callback_data="menu:search"
        ),
        InlineKeyboardButton(
            text=lang_texts.get("btn_favorites", "⭐ Sevimlilər"),
            callback_data="menu:favorites"
        )
    )

    kb.row(
        InlineKeyboardButton(
            text=lang_texts.get("btn_lang", "🌍 Dil"),
            callback_data="menu:lang"
        )
    )

    if is_admin:
        kb.row(
            InlineKeyboardButton(
                text=lang_texts.get("btn_admin", "⚙️ Admin Panel"),
                callback_data="menu:admin"
            )
        )

    return kb.as_markup()


# -----------------------------------------------------------
# 🎵 Mahnı əməliyyatları
# -----------------------------------------------------------
def song_actions(lang_texts: dict, yt_id: str):
    """
    Mahnı əməliyyatları üçün düymələr.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=lang_texts.get("download", "⬇️ Yüklə"),
                callback_data=f"song:dl:{yt_id}"
            ),
            InlineKeyboardButton(
                text=lang_texts.get("lyrics", "📝 Sözlər"),
                callback_data=f"song:ly:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text=lang_texts.get("translate", "🇦🇿 Tərcümə et"),
                callback_data=f"song:tr:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text=lang_texts.get("favorite", "⭐ Favoritə əlavə et"),
                callback_data=f"song:fav:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text=lang_texts.get("btn.add_to_playlist", "➕ Playlist"),
                callback_data=f"song:pl:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text=lang_texts.get("effects", "🎚️ Effektlər"),
                callback_data=f"song:fx:{yt_id}"
            )
        ]
    ])


# -----------------------------------------------------------
# 🎚️ Effekt menyusu
# -----------------------------------------------------------
def effects_menu(lang_texts: dict | None = None, yt_id: str | None = None):
    """
    Effekt seçimləri — çoxdilli.
    yt_id: YouTube video ID to include in callback data
    """
    kb = InlineKeyboardBuilder()
    get = (lang_texts or {}).get
    
    # Include yt_id in callback data if provided
    suffix = f":{yt_id}" if yt_id else ""

    kb.row(
        InlineKeyboardButton(text=get("bass_plus6", "Bass +6dB"), callback_data=f"fx:bass:6{suffix}"),
        InlineKeyboardButton(text=get("treble_plus4", "Treble +4dB"), callback_data=f"fx:treble:4{suffix}")
    )
    kb.row(
        InlineKeyboardButton(text=get("reverb", "Reverb"), callback_data=f"fx:reverb:1{suffix}"),
        InlineKeyboardButton(text=get("echo", "Echo"), callback_data=f"fx:echo:1{suffix}")
    )
    kb.row(
        InlineKeyboardButton(text=get("pitch_up", "Pitch +2"), callback_data=f"fx:pitch:2{suffix}"),
        InlineKeyboardButton(text=get("pitch_down", "Pitch -2"), callback_data=f"fx:pitch:-2{suffix}")
    )
    kb.row(
        InlineKeyboardButton(text=get("speed_up", "Speed 1.25x"), callback_data=f"fx:speed:1.25{suffix}"),
        InlineKeyboardButton(text=get("speed_down", "Speed 0.9x"), callback_data=f"fx:speed:0.9{suffix}")
    )

    return kb.as_markup()
