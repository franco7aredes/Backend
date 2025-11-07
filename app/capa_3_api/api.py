from fastapi import APIRouter

from .routers.partidas import partida_router
from .routers.mazo import mazo_router
from .routers.secretos import secreto_router
from .routers.sets import set_router
from .routers.nsf import nsf_router


api_router = APIRouter()
api_router.include_router(partida_router)
api_router.include_router(mazo_router)
api_router.include_router(secreto_router)
api_router.include_router(set_router)
api_router.include_router(nsf_router)
