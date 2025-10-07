"""Punto de entrada de la aplicación FastAPI (fuera de las capas).

Acá se compone la app (routers, websockets, DB metadata y CORS).
"""

from typing import Union
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.capa_3_api.api import api_router
from app.capa_3_api.websockets.ApiWS import ws_router
from app.settings import settings

from app.capa_0_definicion_bd.base_datos_sqlalchemy import Base, async_engine
# Importa los modelos reales (capa 0) para registrar las tablas en el metadata
from app.capa_0_definicion_bd.models import (
    partidas_modelos,  # noqa: F401
    jugadores_modelos,  # noqa: F401
    cartas_modelos,  # noqa: F401
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Crear tablas usando el motor asíncrono
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

# Orígenes permitidos para CORS, centralizados en settings
origins = settings.CORS_ORIGINS


# Incluir routers HTTP y WebSocket
app.include_router(api_router)
app.include_router(ws_router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

__all__ = ["app"]

if __name__ == "__main__":

    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
