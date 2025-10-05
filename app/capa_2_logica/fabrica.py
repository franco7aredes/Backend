from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.capa_0_definicion_bd.base_datos_sqlalchemy import get_async_db
from app.capa_1_acceso_datos.repositorios.partida_sqlalchemy import RepositorioPartidaSQLAlchemy
from .servicio_juego import ServicioJuego


def obtener_servicio_juego(db: AsyncSession = Depends(get_async_db)) -> ServicioJuego:
    """Factory para construir el ServicioJuego con sus dependencias reales.

    - Inyecta la sesión asíncrona
    - Arma el repositorio concreto
    """
    repo = RepositorioPartidaSQLAlchemy(db)
    return ServicioJuego(repo)
