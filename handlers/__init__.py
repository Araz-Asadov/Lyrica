from aiogram import Dispatcher
from . import start, search, favorites, playlists, admin, voice, commands, links, video


def setup_routers(dp: Dispatcher):
    # Order matters: links should be checked before search
    for r in (
        start.router,
        links.router,  # Handle links first
        video.router,  # Handle videos
        voice.router,  # Handle voice messages
        search.router,  # Handle text queries
        favorites.router,
        playlists.router,
        admin.router,
        commands.router,
    ):
        dp.include_router(r)
