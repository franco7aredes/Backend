from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.capa_0_definicion_bd.base_datos_sqlalchemy import get_async_db
from app.capa_1_acceso_datos.repositorios.partida_sqlalchemy import RepositorioPartidaSQLAlchemy
from app.capa_1_acceso_datos.repositorios.jugador_sqlalchemy import RepositorioJugadorSQLAlchemy
from app.capa_1_acceso_datos.repositorios.carta_sqlalchemy import RepositorioCartaSQLAlchemy
from app.capa_1_acceso_datos.repositorios.secreto_sqlalchemy import RepositorioSecretoSQLAlchemy

from .servicio_juego import ServicioJuego


def obtener_servicio_juego(db: AsyncSession = Depends(get_async_db)) -> ServicioJuego:
    """Factory para construir el ServicioJuego con sus dependencias reales.

    - Inyecta la sesión asíncrona
    - Arma el repositorio concreto
    """
    repo_partidas = RepositorioPartidaSQLAlchemy(db)
    repo_jugadores = RepositorioJugadorSQLAlchemy(db)
    repo_cartas = RepositorioCartaSQLAlchemy(db)
    repo_secretos = RepositorioSecretoSQLAlchemy(db)
    return ServicioJuego(repo_partidas, jugadores=repo_jugadores, cartas=repo_cartas, secretos=repo_secretos)
