from fastapi import APIRouter

from .routers.partidas import partida_router
from .routers.mazo import mazo_router


api_router = APIRouter()
api_router.include_router(partida_router)
api_router.include_router(mazo_router)
