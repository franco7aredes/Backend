from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.capa_0_definicion_bd.models.jugadores_modelos import Jugador as JugadorModelo


class RepositorioJugadorSQLAlchemy:
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

    async def guardar_muchos(self, jugadores: List[JugadorModelo]) -> None:
        self.db.add_all(jugadores)
        await self.db.flush()
