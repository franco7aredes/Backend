from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.partidas_models import Partida as PartidaModel, EstadoPartida
from .partida_abstract import IPartidaRepository


class PartidaRepositorySQLAlchemy(IPartidaRepository):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def crear(self, partida: PartidaModel) -> PartidaModel:
        self.db.add(partida)
        await self.db.flush()
        await self.db.refresh(partida)
        return partida

    async def obtener(self, partida_id: int) -> Optional[PartidaModel]:
        return await self.db.get(PartidaModel, partida_id)

    async def listar_en_espera(self) -> List[PartidaModel]:
        stmt = select(PartidaModel).where(PartidaModel.estado == EstadoPartida.en_espera)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def guardar(self, partida: PartidaModel) -> None:
        self.db.add(partida)
        await self.db.flush()
