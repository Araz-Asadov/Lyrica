from aiogram import Dispatcher
from . import start, search, favorites, playlists, admin, voice, commands, links, recognition, notes


def setup_routers(dp: Dispatcher):
    for r in (
        start.router,
        recognition.router,  # Recognition FIRST - TikTok/Instagram are more specific
        links.router,  # YouTube links SECOND - more specific than general search
        search.router,  # General search THIRD - catches all other text
        notes.router,  # Notes extraction
        favorites.router,
        playlists.router,
        admin.router,
        voice.router,
        commands.router,
    ):
        dp.include_router(r)
