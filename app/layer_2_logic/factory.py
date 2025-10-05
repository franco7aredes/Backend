from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.layer_0_db_definition.database_sqlalchemy import get_async_db
from app.layer_1_data_access.repositories.partida_sqlalchemy import PartidaRepositorySQLAlchemy
from .juego_service import JuegoService


def get_juego_service(db: AsyncSession = Depends(get_async_db)) -> JuegoService:
    repo = PartidaRepositorySQLAlchemy(db)
    return JuegoService(repo)
