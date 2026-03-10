"""Сборка всех роутеров sources."""
from aiogram import Router

from . import add_channel
from . import destination_handlers
from . import finalize_handlers
from . import cancel_handlers
from . import list_handlers
from . import group_select_handlers

router = Router(name="sources")
router.include_router(add_channel.router)
router.include_router(destination_handlers.router)
router.include_router(finalize_handlers.router)
router.include_router(cancel_handlers.router)
router.include_router(list_handlers.router)
router.include_router(group_select_handlers.router)

__all__ = ["router"]
