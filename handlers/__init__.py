from aiogram import Dispatcher
from . import start, search, favorites, playlists, admin, voice, commands


def setup_routers(dp: Dispatcher):
    for r in (
        start.router,
        search.router,
        favorites.router,
        playlists.router,
        admin.router,
        voice.router,
        commands.router,
    ):
        dp.include_router(r)
from aiogram import Dispatcher
from . import start, search, favorites, playlists, admin, voice, commands


def setup_routers(dp: Dispatcher):
    for r in (
        start.router,
        search.router,
        favorites.router,
        playlists.router,
        admin.router,
        voice.router,
        commands.router,
    ):
        dp.include_router(r)