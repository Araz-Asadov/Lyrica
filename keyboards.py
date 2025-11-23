from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
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
            callback_data="menu:favorites"
        )
    )

    kb.row(
        InlineKeyboardButton(
            text=t(lang, "btn_lang"),
            callback_data="menu:lang"
        )
    )

    if is_admin:
        kb.row(
            InlineKeyboardButton(
                text=t(lang, "btn_admin"),
                callback_data="menu:admin"
            )
        )

    return kb.as_markup()


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
                callback_data=f"song:ly:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text=t(lang, "translate"),
                callback_data=f"song:tr:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text=t(lang, "favorite"),
                callback_data=f"song:fav:{yt_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text=t(lang, "effects"),
                callback_data=f"song:fx:{yt_id}"
            )
        ]
    ])


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
    )

    return kb.as_markup()
