# Aqui se define la API del juego

from fastapi import APIRouter

from .routers.partidas import partida_router
from .routers.mazo import mazo_router

api_router=APIRouter()
# Nota: la linea de abajo es sujeta a modificaciones: evaluar el manejo de
# ese router cuando se lo este implementando, y revisar aca
api_router.include_router(partida_router)
api_router.include_router(mazo_router)
