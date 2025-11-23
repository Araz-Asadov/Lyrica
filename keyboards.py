from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


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
            callback_data="menu:favorites"
        )
    )

    # 🌐 Dil seçimi
    kb.row(
        InlineKeyboardButton(
            text=lang_texts.get("btn_lang", "🌐 Dil"),
            callback_data="menu:lang"
        )
    )

    # ⚙️ Admin yalnız icazəli user üçün
    if is_admin:
        kb.row(
            InlineKeyboardButton(
                text=lang_texts.get("btn_admin", "⚙️ Admin Panel"),
                callback_data="menu:admin"
            )
        )

    return kb.as_markup()


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
                callback_data=f"song:ly:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text=lang_dict.get("translate", "🇦🇿 Tərcümə et"),
                callback_data=f"song:tr:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text=lang_dict.get("favorite", "⭐ Favoritə əlavə et"),
                callback_data=f"song:fav:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text=lang_dict.get("effects", "🎚️ Effektlər"),
                callback_data=f"song:fx:{yt_id}"
            )
        ]
    ])


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
    )

    return kb.as_markup()