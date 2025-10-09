from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.capa_0_definicion_bd.models.partidas_modelos import Partida as PartidaModelo, EstadoPartida


class RepositorioPartidaSQLAlchemy:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear(self, partida: PartidaModelo) -> PartidaModelo:
        self.db.add(partida)
        await self.db.flush()
        await self.db.refresh(partida)
        return partida

    async def obtener(self, partida_id: int) -> Optional[PartidaModelo]:
        return await self.db.get(PartidaModelo, partida_id)

    async def listar_en_espera(self) -> List[PartidaModelo]:
        stmt = select(PartidaModelo).where(PartidaModelo.estado == EstadoPartida.en_espera)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def guardar(self, partida: PartidaModelo) -> None:
        self.db.add(partida)
        await self.db.flush()

    async def confirmar(self) -> None:
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
