from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.jugadores_models import Jugador as JugadorModelo
from .jugador_contrato import IRepositorioJugador


class RepositorioJugadorSQLAlchemy(IRepositorioJugador):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def listar_por_partida(self, partida_id: int) -> List[JugadorModelo]:
        stmt = select(JugadorModelo).where(JugadorModelo.id_partida == partida_id)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def crear(self, jugador: JugadorModelo) -> JugadorModelo:
        self.db.add(jugador)
        await self.db.flush()
        await self.db.refresh(jugador)
        return jugador

    async def obtener(self, jugador_id: int) -> Optional[JugadorModelo]:
        return await self.db.get(JugadorModelo, jugador_id)
